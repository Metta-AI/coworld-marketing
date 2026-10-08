"""Load one submitted player file: a zip (directory) with entry.json + video, or a bare video file."""

from __future__ import annotations

import json
import stat
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from videomarketing.config import EntryFormat, Limits

ENTRY_SCHEMA = "softmax-video-entry/1"
MAX_ZIP_MEMBERS = 200
MAX_UNPACKED_BYTES = 160 * 1024 * 1024
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm"}


class EntryMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: str = Field(default=ENTRY_SCHEMA, alias="schema")
    title: str = Field(min_length=1, max_length=200)
    format: EntryFormat = "other"
    video: str = Field(default="video.mp4", min_length=1)
    post: str = Field(default="", max_length=1000, description="The X post text that would accompany the video.")
    alt_text: str = Field(default="", max_length=1000)
    thesis: str = Field(default="", max_length=400, description="The one sentence the end card shows.")
    script: str = Field(default="", max_length=6000, description="Narration or lyrics, for the judge.")
    credits: str = Field(default="", max_length=400)
    made_with: list[str] = Field(default_factory=list, max_length=20)


@dataclass
class Entry:
    meta: EntryMeta
    video_path: Path | None
    kind: str  # "zip" | "video" | "invalid"
    problems: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return self.video_path is not None and not any(p.startswith("fatal:") for p in self.problems)


def _is_video_header(head: bytes) -> bool:
    is_mp4 = len(head) >= 12 and head[4:8] == b"ftyp"
    is_ebml = head[:4] == b"\x1a\x45\xdf\xa3"  # webm / mkv
    return is_mp4 or is_ebml


def _safe_extract(zip_path: Path, dest: Path, limits: Limits) -> list[str]:
    problems: list[str] = []
    with zipfile.ZipFile(zip_path) as archive:
        members = archive.infolist()
        if len(members) > MAX_ZIP_MEMBERS:
            return [f"fatal: archive has {len(members)} members (limit {MAX_ZIP_MEMBERS})"]
        total = sum(m.file_size for m in members)
        if total > MAX_UNPACKED_BYTES:
            return [f"fatal: archive unpacks to {total} bytes (limit {MAX_UNPACKED_BYTES})"]
        dest_resolved = dest.resolve()
        for member in members:
            name = member.filename
            if member.is_dir():
                continue
            mode = (member.external_attr >> 16) & 0o170000
            if mode == stat.S_IFLNK:
                return [f"fatal: archive member {name!r} is a symlink"]
            target = (dest / name).resolve()
            if not target.is_relative_to(dest_resolved) or name.startswith("/") or ".." in Path(name).parts:
                return [f"fatal: archive member {name!r} escapes the package"]
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as src, target.open("wb") as out:
                remaining = member.file_size
                while True:
                    chunk = src.read(1024 * 1024)
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    if remaining < -1:
                        return [f"fatal: archive member {name!r} is larger than declared"]
                    out.write(chunk)
    return problems


def _find_entry_root(dest: Path) -> Path:
    if (dest / "entry.json").exists():
        return dest
    children = [c for c in dest.iterdir() if c.is_dir() and not c.name.startswith("__MACOSX")]
    if len(children) == 1 and (children[0] / "entry.json").exists():
        return children[0]
    return dest


def _single_video(root: Path) -> Path | None:
    videos = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in VIDEO_SUFFIXES)
    return videos[0] if len(videos) == 1 else None


def load_entry(file_path: Path, workdir: Path, limits: Limits, *, default_title: str) -> Entry:
    """Interpret the staged player bytes. Never raises for bad input: problems are recorded on the Entry."""
    workdir.mkdir(parents=True, exist_ok=True)
    try:
        size = file_path.stat().st_size
    except OSError as error:
        return Entry(EntryMeta(title=default_title), None, "invalid", [f"fatal: cannot stat player file ({error})"])
    if size == 0:
        return Entry(EntryMeta(title=default_title), None, "invalid", ["fatal: player file is empty"])
    if size > limits.max_file_bytes:
        return Entry(
            EntryMeta(title=default_title),
            None,
            "invalid",
            [f"fatal: player file is {size} bytes (limit {limits.max_file_bytes})"],
        )
    with file_path.open("rb") as handle:
        head = handle.read(16)

    if _is_video_header(head):
        return Entry(EntryMeta(title=default_title), file_path, "video", ["note: bare video, no entry.json"])

    if head[:2] != b"PK":
        return Entry(
            EntryMeta(title=default_title),
            None,
            "invalid",
            ["fatal: player file is neither a video (mp4/mov/webm) nor a zip package"],
        )

    dest = workdir / "unpacked"
    try:
        problems = _safe_extract(file_path, dest, limits)
    except zipfile.BadZipFile as error:
        return Entry(EntryMeta(title=default_title), None, "invalid", [f"fatal: bad zip ({error})"])
    if any(p.startswith("fatal:") for p in problems):
        return Entry(EntryMeta(title=default_title), None, "invalid", problems)

    root = _find_entry_root(dest)
    meta = EntryMeta(title=default_title)
    entry_json = root / "entry.json"
    if entry_json.exists():
        try:
            meta = EntryMeta.model_validate(json.loads(entry_json.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            problems.append(f"entry.json is not valid JSON ({error}); using defaults")
        except ValidationError as error:
            problems.append("entry.json failed validation: " + "; ".join(e["msg"] for e in error.errors()[:5]))
        if meta.schema_ != ENTRY_SCHEMA:
            problems.append(f"entry.json schema is {meta.schema_!r}; expected {ENTRY_SCHEMA!r}")
    else:
        problems.append("no entry.json in package; using defaults")

    video_path = (root / meta.video).resolve()
    if not video_path.is_relative_to(root.resolve()) or not video_path.is_file():
        fallback = _single_video(root)
        if fallback is None:
            problems.append(f"fatal: video {meta.video!r} not found in package")
            return Entry(meta, None, "invalid", problems)
        problems.append(f"video {meta.video!r} not found; using the only video in the package ({fallback.name})")
        video_path = fallback
    return Entry(meta, video_path, "zip", problems)
