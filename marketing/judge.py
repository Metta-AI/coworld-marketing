"""The autograder: a deterministic technical panel and an LLM craft review against the house rubric."""

from __future__ import annotations

import base64
import json
import logging
import os
import re
import time
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import asdict, dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from marketing.config import JudgeConfig, Limits
from marketing.entry import Entry, MediaItem, count_hashtags, count_links, weighted_length
from marketing.probe import Measurement

logger = logging.getLogger("marketing.judge")

RUBRIC_VERSION = "post/2"
CRAFT_KEYS = ("hook", "specific", "voice", "legible", "craft", "repostable")
CRAFT_WEIGHTS = {
    "hook": 0.20,
    "specific": 0.20,
    "voice": 0.25,
    "legible": 0.10,
    "craft": 0.10,
    "repostable": 0.15,
}


def rubric_text() -> str:
    return resources.files("marketing").joinpath("rubric.md").read_text(encoding="utf-8")


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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TechnicalReview:
        checks = [
            Check(**{k: c.get(k) for k in ("id", "ok", "detail", "penalty", "gate")}) for c in data.get("checks", [])
        ]
        return cls(float(data.get("score", 0.0)), bool(data.get("eligible", False)), checks)

    @property
    def failures(self) -> list[Check]:
        return [c for c in self.checks if not c.ok]


def as_measurements(m: Sequence[Measurement] | Measurement | None) -> list[Measurement]:
    """Callers written for one attachment pass a Measurement or None; the review works on a list, one per item."""
    if m is None:
        return []
    if isinstance(m, Measurement):
        return [m]
    return list(m)


def item_label(item: MediaItem, index: int, count: int) -> str:
    """How the checks name an attachment: silent for a lone item, "image 2/3 (b.jpg)" when there are several."""
    return "" if count < 2 else f"{item.kind} {index + 1}/{count} ({item.display_name})"


def technical_review(entry: Entry, m: Sequence[Measurement] | Measurement | None, limits: Limits) -> TechnicalReview:
    """The deterministic panel. Text checks run once; media checks run per attachment and the entry's score is the
    minimum across attachments, so one bad image fails the post and its check names the item that failed."""
    measurements = as_measurements(m)
    checks: list[Check] = []

    def add(id_: str, ok: bool, detail: str, penalty: float = 0.0, gate: bool = False) -> None:
        checks.append(Check(id_, ok, detail, penalty if not ok else 0.0, gate))

    fatal = [p for p in entry.problems if p.startswith("fatal:")]
    add("package", not fatal, fatal[0] if fatal else f"{entry.kind} package accepted", gate=True)
    if fatal:
        return TechnicalReview(0.0, False, checks)

    text = entry.meta.text
    has_text = bool(text.strip())
    has_media = bool(entry.media)
    add(
        "content",
        has_text or has_media,
        "post has text or media" if (has_text or has_media) else "empty post",
        gate=True,
    )
    if not (has_text or has_media):
        return TechnicalReview(0.0, False, checks)

    weighted = weighted_length(text)
    add(
        "text_length",
        weighted <= limits.text_max_weighted_chars,
        f"text weighs {weighted} of {limits.text_max_weighted_chars} characters (URLs count 23)",
        gate=True,
    )
    add("text_present", has_text, "post text present" if has_text else "media with no post text", penalty=10)
    hashtags = count_hashtags(text)
    add("hashtags", hashtags <= limits.max_hashtags, f"{hashtags} hashtags (limit {limits.max_hashtags})", penalty=5)
    links = count_links(text)
    add("links", links <= limits.max_links, f"{links} links (limit {limits.max_links})", penalty=5)
    if has_media:
        add(
            "media_count",
            len(entry.media) <= limits.max_media_items,
            f"{len(entry.media)} attachment{'s' if len(entry.media) != 1 else ''} (limit {limits.max_media_items})",
            gate=True,
        )

    item_penalties: list[float] = []
    for index, item in enumerate(entry.media):
        measurement = measurements[index] if index < len(measurements) else None
        item_checks = _media_checks(item, item_label(item, index, len(entry.media)), measurement, limits)
        checks.extend(item_checks)
        item_penalties.append(sum(c.penalty for c in item_checks))

    json_problems = [p for p in entry.problems if p.startswith(("entry.json", "no entry.json", "media ", "legacy"))]
    add("entry_json", not json_problems, "; ".join(json_problems) or "entry.json valid", penalty=5)

    eligible = all(c.ok for c in checks if c.gate)
    if not eligible:
        return TechnicalReview(0.0, False, checks)
    common = sum(c.penalty for c in checks) - sum(item_penalties)
    worst_item = max(item_penalties, default=0.0)
    return TechnicalReview(max(0.0, 100.0 - common - worst_item), True, checks)


def _media_checks(item: MediaItem, label: str, m: Measurement | None, limits: Limits) -> list[Check]:
    checks: list[Check] = []
    prefix = f"{label}: " if label else ""

    def add(id_: str, ok: bool, detail: str, penalty: float = 0.0, gate: bool = False) -> None:
        checks.append(Check(id_, ok, prefix + detail, penalty if not ok else 0.0, gate))

    if m is None:
        add("decodes", False, "not measured", gate=True)
        return checks
    add("decodes", m.ok, m.error or f"{m.kind} {m.codec} {m.width}x{m.height}", gate=True)
    if not m.ok:
        return checks
    alt_text = item.alt_text.strip()
    add("alt_text", bool(alt_text), "alt text present" if alt_text else "media without alt text", penalty=5)
    add(
        "alt_text_length",
        len(item.alt_text) <= limits.alt_text_max_chars,
        f"alt text {len(item.alt_text)} chars (limit {limits.alt_text_max_chars})",
        penalty=3,
    )
    small = min(m.width, m.height) >= limits.min_dimension
    add("dimensions", small, f"{m.width}x{m.height} (minimum side {limits.min_dimension})", gate=True)
    aspect_ok = limits.aspect_min <= m.aspect <= limits.aspect_max
    add(
        "aspect",
        aspect_ok,
        f"aspect {m.aspect:.2f} (X accepts {limits.aspect_min:.2f} to {limits.aspect_max:.2f})",
        gate=True,
    )
    if item.kind == "video":
        add(
            "video_duration_max",
            m.duration <= limits.video_max_seconds,
            f"{m.duration:.1f} s (X limit {limits.video_max_seconds:.0f} s)",
            gate=True,
        )
        add(
            "video_duration_min",
            m.duration >= limits.video_min_seconds,
            f"{m.duration:.2f} s (minimum {limits.video_min_seconds} s)",
            gate=True,
        )
        add(
            "video_size",
            m.size_bytes <= limits.video_max_bytes,
            f"{m.size_bytes / 1048576:.1f} MiB (limit {limits.video_max_bytes / 1048576:.0f} MiB)",
            gate=True,
        )
        add(
            "video_resolution",
            m.height >= limits.video_min_height or m.width >= limits.video_min_height,
            f"{m.width}x{m.height} (minimum {limits.video_min_height} on the short side for landscape)",
            penalty=10,
        )
        frozen_body = max(0.0, m.frozen_seconds - min(m.frozen_tail_seconds, 7.0))
        frozen_fraction = frozen_body / m.duration if m.duration else 0.0
        add(
            "video_motion",
            frozen_fraction <= limits.video_max_frozen_fraction,
            f"{frozen_body:.1f} s frozen ({frozen_fraction:.0%}; limit {limits.video_max_frozen_fraction:.0%})",
            penalty=10,
        )
        if m.loudness_lufs is not None:
            in_range = limits.loudness_lufs_min <= m.loudness_lufs <= limits.loudness_lufs_max
            add(
                "video_loudness",
                in_range,
                f"{m.loudness_lufs:.1f} LUFS (range {limits.loudness_lufs_min:.0f} to {limits.loudness_lufs_max:.0f})",
                penalty=5,
            )
    elif item.kind == "gif":
        add(
            "gif_size",
            m.size_bytes <= limits.gif_max_bytes,
            f"{m.size_bytes / 1048576:.1f} MiB (X limit {limits.gif_max_bytes / 1048576:.0f} MiB)",
            gate=True,
        )
    else:
        add(
            "image_size",
            m.size_bytes <= limits.image_max_bytes,
            f"{m.size_bytes / 1048576:.2f} MiB (X limit {limits.image_max_bytes / 1048576:.0f} MiB)",
            gate=True,
        )
    return checks


@dataclass
class CraftReview:
    scores: dict[str, int]
    cringe_flags: list[str]
    notes: str
    verdict: str
    model: str
    attempts: int
    raw: str = ""
    cached: bool = False

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
            "cached": self.cached,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CraftReview:
        scores = {k: _clamp_score((data.get("scores") or {}).get(k)) for k in CRAFT_KEYS}
        return cls(
            scores=scores,
            cringe_flags=[str(f)[:120] for f in (data.get("cringe_flags") or [])][:12],
            notes=str(data.get("notes", ""))[:800],
            verdict=str(data.get("verdict", ""))[:280],
            model=str(data.get("model", "")),
            attempts=int(data.get("attempts", 0) or 0),
            cached=True,
        )


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
        headers = {"Content-Type": "application/json", "User-Agent": "coworld-marketing/0.3"}
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


def _data_uri(image: Path | bytes) -> str:
    data = image if isinstance(image, bytes) else image.read_bytes()
    return "data:image/jpeg;base64," + base64.b64encode(data).decode()


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


@dataclass
class JudgeImagery:
    """What the craft panel sees. Pictures come as `stills`, one JPEG per attachment in order; a video comes as its
    contact sheet and final frame. `still` remains as the single-picture fallback for older callers."""

    stills: list[bytes] = field(default_factory=list)  # one rendering per image or gif, in entry order
    still: Path | None = None  # the image, or the video's poster frame (fallback when stills is empty)
    sheet: Path | None = None  # contact sheet for video
    end: Path | None = None  # final frame for video


def build_messages(
    entry: Entry,
    m: Sequence[Measurement] | Measurement | None,
    imagery: JudgeImagery,
    brief: str,
    account: str,
) -> list[dict[str, Any]]:
    meta = entry.meta
    measurements = as_measurements(m)
    count = len(entry.media)
    if not entry.media:
        media_line = "Media: none (text-only post)"
    elif entry.media_kind == "image":
        media_line = f"Media: {count} image{'s' if count != 1 else ''}"
    else:
        media_line = f"Media: {entry.media_kind}"
    facts = [
        f"Brief: {brief}",
        f"Account: @{account}",
        f"Post text ({weighted_length(meta.text)} of 280 weighted characters):",
        meta.text.strip() or "(no text; media only)",
        "",
        media_line,
    ]
    for index, item in enumerate(entry.media):
        measurement = measurements[index] if index < len(measurements) else None
        label = item_label(item, index, count) or item.kind.capitalize()
        if measurement is not None and measurement.ok:
            if item.kind == "video":
                facts.append(
                    f"Video: {measurement.duration:.0f} s, {measurement.width}x{measurement.height}, "
                    f"audio: {'yes' if measurement.has_audio else 'no'}"
                )
            else:
                facts.append(f"{label}: {measurement.width}x{measurement.height}")
        facts.append(f"Alt text{'' if count < 2 else f' for {label}'}: {item.alt_text.strip() or '(none)'}")
    facts += [
        f"Entrant's thesis: {meta.thesis.strip() or '(none)'}",
        f"Entrant's notes: {meta.notes.strip() or '(none)'}",
    ]
    content: list[dict[str, Any]] = [{"type": "text", "text": "\n".join(facts)}]
    if entry.media_kind == "video" and imagery.sheet is not None and imagery.sheet.exists():
        content.append(
            {"type": "text", "text": "Contact sheet, frames in time order, left to right then top to bottom:"}
        )
        content.append({"type": "image_url", "image_url": {"url": _data_uri(imagery.sheet)}})
        if imagery.end is not None and imagery.end.exists():
            content.append({"type": "text", "text": "The final frame:"})
            content.append({"type": "image_url", "image_url": {"url": _data_uri(imagery.end)}})
    elif imagery.stills:
        total = len(imagery.stills)
        for index, still in enumerate(imagery.stills):
            alt = entry.media[index].alt_text.strip() if index < len(entry.media) else ""
            caption = f"Image {index + 1} of {total}" + (f". Alt text: {alt}" if alt else "")
            content.append({"type": "text", "text": caption})
            content.append({"type": "image_url", "image_url": {"url": _data_uri(still)}})
    elif imagery.still is not None and imagery.still.exists():
        content.append({"type": "text", "text": "The attached picture:"})
        content.append({"type": "image_url", "image_url": {"url": _data_uri(imagery.still)}})
    content.append({"type": "text", "text": "Score it. Return only the JSON object."})
    return [{"role": "system", "content": rubric_text()}, {"role": "user", "content": content}]


def craft_review(
    client: ModelClient,
    entry: Entry,
    m: Sequence[Measurement] | Measurement | None,
    imagery: JudgeImagery,
    brief: str,
    account: str,
    *,
    slot: int,
) -> CraftReview | None:
    if not client.available:
        return None
    messages = build_messages(entry, m, imagery, brief, account)
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
                break
        except (URLError, TimeoutError, OSError, ValueError, KeyError, RuntimeError, json.JSONDecodeError) as error:
            last_error = f"{type(error).__name__}: {error}"
        logger.warning("craft review attempt %d failed for slot %d: %s", attempt, slot, last_error)
        time.sleep(min(2.0 * attempt, 6.0))
    logger.warning("craft review unavailable for slot %d: %s", slot, last_error)
    return None


def judge_score(technical: TechnicalReview, craft: CraftReview | None, cfg: JudgeConfig) -> float:
    """The autograder's 0 to 100: technical and craft panels blended; ineligible entries score 0."""
    if not technical.eligible:
        return 0.0
    if craft is None:
        return round(cfg.technical_weight * technical.score, 2)
    return round(cfg.technical_weight * technical.score + cfg.craft_weight * craft.score, 2)


def cache_record(technical: TechnicalReview, craft: CraftReview | None, model: str) -> dict[str, Any]:
    return {
        "rubric": RUBRIC_VERSION,
        "model": model,
        "technical": technical.to_dict(),
        "craft": craft.to_dict() if craft else None,
    }


def from_cache(record: dict[str, Any], model: str) -> tuple[TechnicalReview, CraftReview | None] | None:
    """A cached judgement is reusable when it was made with the same rubric version and model."""
    if record.get("rubric") != RUBRIC_VERSION or record.get("model") != model:
        return None
    technical = record.get("technical")
    if not isinstance(technical, dict):
        return None
    craft = record.get("craft")
    return TechnicalReview.from_dict(technical), (CraftReview.from_dict(craft) if isinstance(craft, dict) else None)
