"""The two judging panels: a deterministic technical review and an LLM craft review against the house rubric."""

from __future__ import annotations

import base64
import json
import logging
import os
import re
import time
from contextlib import suppress
from dataclasses import asdict, dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from videomarketing.config import JudgeConfig, Limits
from videomarketing.entry import Entry
from videomarketing.probe import Measurement

logger = logging.getLogger("videomarketing.judge")

CRAFT_KEYS = ("legible", "story_not_statement", "motion", "voice", "craft", "postable")
CRAFT_WEIGHTS = {
    "legible": 0.20,
    "story_not_statement": 0.25,
    "motion": 0.15,
    "voice": 0.20,
    "craft": 0.10,
    "postable": 0.10,
}


def rubric_text() -> str:
    return resources.files("videomarketing").joinpath("rubric.md").read_text(encoding="utf-8")


@dataclass
class Check:
    id: str
    ok: bool
    detail: str
    penalty: float = 0.0  # points deducted from 100 when not ok
    gate: bool = False  # a failed gate makes the entry ineligible


@dataclass
class TechnicalReview:
    score: float
    eligible: bool
    checks: list[Check] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"score": round(self.score, 1), "eligible": self.eligible, "checks": [asdict(c) for c in self.checks]}

    @property
    def failures(self) -> list[Check]:
        return [c for c in self.checks if not c.ok]


def technical_review(entry: Entry, m: Measurement, limits: Limits) -> TechnicalReview:
    checks: list[Check] = []

    def add(id_: str, ok: bool, detail: str, penalty: float = 0.0, gate: bool = False) -> None:
        checks.append(Check(id_, ok, detail, penalty if not ok else 0.0, gate))

    fatal = [p for p in entry.problems if p.startswith("fatal:")]
    add("package", not fatal, fatal[0] if fatal else f"{entry.kind} package accepted", gate=True)
    if fatal or entry.video_path is None:
        return TechnicalReview(0.0, False, checks)

    add("decodes", m.ok, m.error or f"{m.video_codec} {m.width}x{m.height} @ {m.fps:.3g} fps", gate=True)
    if not m.ok:
        return TechnicalReview(0.0, False, checks)

    add(
        "duration_max",
        m.duration <= limits.max_duration_seconds,
        f"{m.duration:.1f} s (hard limit {limits.max_duration_seconds:.0f} s)",
        gate=True,
    )
    add(
        "duration_min",
        m.duration >= limits.min_duration_seconds,
        f"{m.duration:.1f} s (minimum {limits.min_duration_seconds:.0f} s)",
        penalty=40,
    )
    in_target = limits.target_min_seconds <= m.duration <= limits.target_max_seconds
    add(
        "duration_target",
        in_target,
        f"{m.duration:.1f} s (target {limits.target_min_seconds:.0f}-{limits.target_max_seconds:.0f} s)",
        penalty=10,
    )
    add(
        "resolution",
        m.height >= limits.min_height,
        f"{m.width}x{m.height} (minimum height {limits.min_height})",
        penalty=15,
    )
    add("audio", m.has_audio, "audio track present" if m.has_audio else "no audio track", penalty=20)
    if m.loudness_lufs is not None:
        in_range = limits.loudness_lufs_min <= m.loudness_lufs <= limits.loudness_lufs_max
        add(
            "loudness",
            in_range,
            f"{m.loudness_lufs:.1f} LUFS (target {limits.loudness_lufs_min:.0f} to {limits.loudness_lufs_max:.0f})",
            penalty=8,
        )
    # An end card may legitimately hold for ~6 s; count only freezes beyond that allowance.
    frozen_body = max(0.0, m.frozen_seconds - min(m.frozen_tail_seconds, 7.0))
    frozen_fraction = frozen_body / m.duration if m.duration else 0.0
    add(
        "motion_floor",
        frozen_fraction <= limits.max_frozen_fraction,
        f"{frozen_body:.1f} s frozen outside the end card "
        f"({frozen_fraction:.0%}; limit {limits.max_frozen_fraction:.0%})",
        penalty=20,
    )
    add(
        "title_length",
        len(entry.meta.title) <= limits.title_max_chars,
        f"title {len(entry.meta.title)} chars (limit {limits.title_max_chars})",
        penalty=3,
    )
    add(
        "post_length",
        len(entry.meta.post) <= limits.post_max_chars,
        f"post {len(entry.meta.post)} chars (limit {limits.post_max_chars})",
        penalty=5,
    )
    has_post, has_thesis = bool(entry.meta.post.strip()), bool(entry.meta.thesis.strip())
    add("post_present", has_post, "post text present" if has_post else "no post text", penalty=5)
    add("thesis_present", has_thesis, "thesis present" if has_thesis else "no thesis", penalty=3)
    json_problems = [p for p in entry.problems if p.startswith(("entry.json", "no entry.json"))]
    add("entry_json", not json_problems, "; ".join(json_problems) or "entry.json valid", penalty=5)

    eligible = all(c.ok for c in checks if c.gate)
    score = max(0.0, 100.0 - sum(c.penalty for c in checks))
    if not eligible:
        score = 0.0
    return TechnicalReview(score, eligible, checks)


@dataclass
class CraftReview:
    scores: dict[str, int]
    cringe_flags: list[str]
    notes: str
    verdict: str
    model: str
    attempts: int
    raw: str = ""

    @property
    def score(self) -> float:
        return 10.0 * sum(CRAFT_WEIGHTS[k] * self.scores.get(k, 0) for k in CRAFT_KEYS)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": round(self.score, 1),
            "scores": self.scores,
            "cringe_flags": self.cringe_flags,
            "notes": self.notes,
            "verdict": self.verdict,
            "model": self.model,
            "attempts": self.attempts,
        }


class ModelClient:
    """OpenAI-chat-shaped client. Hosted: the Coworld LLM sidecar. Local: an OpenRouter-compatible endpoint + key."""

    def __init__(self, cfg: JudgeConfig) -> None:
        self.cfg = cfg
        sidecar = os.environ.get("COWORLD_LLM_ENDPOINT", "").rstrip("/")
        if sidecar:
            self.base = f"{sidecar}/v1/chat/completions"
            self.key = ""
            self.source = "sidecar"
        else:
            base = os.environ.get("JUDGE_API_BASE", "https://openrouter.ai/api/v1").rstrip("/")
            self.base = f"{base}/chat/completions"
            self.key = os.environ.get("JUDGE_API_KEY") or os.environ.get("OPENROUTER_API_KEY") or ""
            self.source = "local" if self.key else "none"
        # Local runs may point at a provider that names models differently from the OpenRouter slugs the sidecar uses.
        self.model = os.environ.get("JUDGE_MODEL") or cfg.model

    @property
    def available(self) -> bool:
        return self.source != "none"

    def complete(self, messages: list[dict[str, Any]], *, slot: int | None) -> str:
        body = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.cfg.max_tokens,
            "temperature": 0.2,
        }
        headers = {"Content-Type": "application/json", "User-Agent": "coworld-video-marketing/0.1"}
        if self.key:
            headers["Authorization"] = f"Bearer {self.key}"
        if slot is not None and self.source == "sidecar":
            headers["X-Coworld-Player-Slot"] = str(slot)
        request = Request(self.base, data=json.dumps(body).encode(), headers=headers, method="POST")
        with urlopen(request, timeout=self.cfg.timeout_seconds) as response:
            payload = json.loads(response.read())
        choice = payload["choices"][0]
        if choice.get("finish_reason") == "error":
            raise RuntimeError("model returned finish_reason=error")
        content = choice["message"]["content"]
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        return str(content)


def _data_uri(path: Path) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode()


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in model output")
    return json.loads(text[start : end + 1])


def _clamp_score(value: Any) -> int:
    try:
        return max(0, min(10, int(round(float(value)))))
    except (TypeError, ValueError):
        return 0


def build_messages(
    entry: Entry, m: Measurement, sheet: Path, end_frame: Path | None, brief: str
) -> list[dict[str, Any]]:
    meta = entry.meta
    facts = [
        f"Brief for today: {brief}",
        f"Title: {meta.title}",
        f"Declared format: {meta.format}",
        f"Duration: {m.duration:.0f} s, {m.width}x{m.height}, audio: {'yes' if m.has_audio else 'no'}",
        f"Proposed post text: {meta.post or '(none)'}",
        f"Thesis / end card line: {meta.thesis or '(none)'}",
        f"Script (narration or lyrics): {meta.script or '(not provided)'}",
    ]
    content: list[dict[str, Any]] = [
        {"type": "text", "text": "\n".join(facts)},
        {"type": "text", "text": "Contact sheet, frames in time order, left to right then top to bottom:"},
        {"type": "image_url", "image_url": {"url": _data_uri(sheet)}},
    ]
    if end_frame is not None and end_frame.exists():
        content.append({"type": "text", "text": "The final frame (end card):"})
        content.append({"type": "image_url", "image_url": {"url": _data_uri(end_frame)}})
    content.append({"type": "text", "text": "Score it. Return only the JSON object."})
    return [{"role": "system", "content": rubric_text()}, {"role": "user", "content": content}]


def craft_review(
    client: ModelClient,
    entry: Entry,
    m: Measurement,
    sheet: Path,
    end_frame: Path | None,
    brief: str,
    *,
    slot: int,
) -> CraftReview | None:
    if not client.available:
        return None
    messages = build_messages(entry, m, sheet, end_frame, brief)
    last_error = ""
    for attempt in range(1, client.cfg.retries + 2):
        try:
            raw = client.complete(messages, slot=slot)
            data = _extract_json(raw)
            scores = {k: _clamp_score(data.get(k)) for k in CRAFT_KEYS}
            flags = data.get("cringe_flags") or []
            if not isinstance(flags, list):
                flags = [str(flags)]
            return CraftReview(
                scores=scores,
                cringe_flags=[str(f)[:120] for f in flags][:12],
                notes=str(data.get("notes", ""))[:800],
                verdict=str(data.get("verdict", ""))[:280],
                model=client.model,
                attempts=attempt,
                raw=raw[:4000],
            )
        except HTTPError as error:
            body = ""
            with suppress(Exception):
                body = error.read().decode(errors="replace")[:300]
            last_error = f"HTTP {error.code} {body}"
            retry_after = error.headers.get("Retry-After-Ms") or error.headers.get("Retry-After")
            if error.code == 429 and retry_after:
                try:
                    wait = float(retry_after) / (1000.0 if "Ms" in str(error.headers.keys()) else 1.0)
                except ValueError:
                    wait = 5.0
                time.sleep(min(max(wait, 1.0), 30.0))
            elif error.code in {400, 403}:
                break  # not retryable: bad request shape or model denied
        except (URLError, TimeoutError, OSError, ValueError, KeyError, RuntimeError, json.JSONDecodeError) as error:
            last_error = f"{type(error).__name__}: {error}"
        logger.warning("craft review attempt %d failed for slot %d: %s", attempt, slot, last_error)
        time.sleep(min(2.0 * attempt, 6.0))
    logger.warning("craft review unavailable for slot %d: %s", slot, last_error)
    return None


def combine(technical: TechnicalReview, craft: CraftReview | None, cfg: JudgeConfig) -> float:
    if not technical.eligible:
        return 0.0
    if craft is None:
        return round(cfg.technical_weight * technical.score, 2)
    return round(cfg.technical_weight * technical.score + cfg.craft_weight * craft.score, 2)
