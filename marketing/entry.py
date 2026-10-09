"""Load one submitted player file: a zip with entry.json and optional media, a bare media file, or bare text."""

from __future__ import annotations

import json
import re
import stat
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from marketing.config import Limits, MediaKind

ENTRY_SCHEMA = "softmax-post-entry/1"
LEGACY_VIDEO_SCHEMA = "softmax-video-entry/1"
MAX_ZIP_MEMBERS = 200
MAX_UNPACKED_BYTES = 160 * 1024 * 1024
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
GIF_SUFFIXES = {".gif"}
MEDIA_SUFFIXES = VIDEO_SUFFIXES | IMAGE_SUFFIXES | GIF_SUFFIXES
URL_RE = re.compile(r"https?://\S+|(?<![\w@])(?:[a-z0-9-]+\.)+[a-z]{2,}(?:/\S*)?", re.IGNORECASE)
HASHTAG_RE = re.compile(r"(?<!\w)#\w+")


class EntryMeta(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_: str = Field(default=ENTRY_SCHEMA, alias="schema")
    text: str = Field(default="", max_length=2000, description="The post text as it would appear on X.")
    media: str | None = Field(default=None, description="Media file inside the package, or null for a text-only post.")
    alt_text: str = Field(default="", max_length=1500, description="Alt text for the media.")
    title: str = Field(
        default="", max_length=120, description="Optional label for the jury page; defaults to the text."
    )
    thesis: str = Field(default="", max_length=400, description="One sentence on what this post is for.")
    notes: str = Field(default="", max_length=4000, description="Context for the judge: what the media shows, sources.")
    credits: str = Field(default="", max_length=400)
    made_with: list[str] = Field(default_factory=list, max_length=20)

    @property
    def label(self) -> str:
        if self.title.strip():
            return self.title.strip()
        first = " ".join(self.text.strip().split())
        return (first[:57] + "...") if len(first) > 60 else first or "Untitled post"


@dataclass
class Entry:
    meta: EntryMeta
    media_path: Path | None
    media_kind: MediaKind
    kind: str  # "zip" | "media" | "text" | "invalid"
    problems: list[str] = field(default_factory=list)

    @property
    def fatal(self) -> bool:
        return any(p.startswith("fatal:") for p in self.problems)

    @property
    def valid(self) -> bool:
        return not self.fatal and (bool(self.meta.text.strip()) or self.media_path is not None)


def weighted_length(text: str) -> int:
    """X's counting: URLs weigh 23, most characters 1, wide (CJK, emoji) characters 2."""
    total = 0
    last = 0
    for match in URL_RE.finditer(text):
        total += _weigh(text[last : match.start()])
        total += 23
        last = match.end()
    total += _weigh(text[last:])
    return total


def _weigh(segment: str) -> int:
    weight = 0
    for ch in segment:
        code = ord(ch)
        if code < 0x1100:
            weight += 1
        elif (
            0x1100 <= code <= 0x115F
            or 0x2E80 <= code <= 0xA4CF
            or 0xAC00 <= code <= 0xD7A3
            or 0xF900 <= code <= 0xFAFF
            or 0xFE30 <= code <= 0xFE4F
            or 0xFF00 <= code <= 0xFF60
            or 0xFFE0 <= code <= 0xFFE6
            or code >= 0x1F000
        ):
            weight += 2
        else:
            weight += 1
    return weight


def count_hashtags(text: str) -> int:
    return len(HASHTAG_RE.findall(text))


def count_links(text: str) -> int:
    return len(URL_RE.findall(text))


def media_kind_for(path: Path) -> MediaKind:
    suffix = path.suffix.lower()
    if suffix in VIDEO_SUFFIXES:
        return "video"
    if suffix in GIF_SUFFIXES:
        return "gif"
    if suffix in IMAGE_SUFFIXES:
        return "image"
    return "none"


def sniff_media(head: bytes) -> MediaKind:
    if len(head) >= 12 and head[4:8] == b"ftyp":
        return "video"
    if head[:4] == b"\x1a\x45\xdf\xa3":
        return "video"
    if head[:8] == b"\x89PNG\r\n\x1a\n" or head[:3] == b"\xff\xd8\xff":
        return "image"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    return "none"


def _safe_extract(zip_path: Path, dest: Path) -> list[str]:
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
    return []


def _find_entry_root(dest: Path) -> Path:
    if (dest / "entry.json").exists():
        return dest
    children = [c for c in dest.iterdir() if c.is_dir() and not c.name.startswith("__MACOSX")]
    if len(children) == 1 and (children[0] / "entry.json").exists():
        return children[0]
    return dest


def _single_media(root: Path) -> Path | None:
    files = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in MEDIA_SUFFIXES)
    return files[0] if len(files) == 1 else None


def _parse_meta(raw: str, problems: list[str]) -> EntryMeta:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as error:
        problems.append(f"entry.json is not valid JSON ({error}); using defaults")
        return EntryMeta()
    if not isinstance(data, dict):
        problems.append("entry.json is not an object; using defaults")
        return EntryMeta()
    if data.get("schema") == LEGACY_VIDEO_SCHEMA:
        # A video-era package: the post text is the tweet, the video is the media.
        data = {
            "schema": ENTRY_SCHEMA,
            "text": data.get("post", ""),
            "media": data.get("video", "video.mp4"),
            "alt_text": data.get("alt_text", ""),
            "title": data.get("title", ""),
            "thesis": data.get("thesis", ""),
            "notes": data.get("script", ""),
            "credits": data.get("credits", ""),
            "made_with": data.get("made_with", []),
        }
        problems.append("legacy softmax-video-entry/1 package read as a video post")
    try:
        meta = EntryMeta.model_validate(data)
    except ValidationError as error:
        problems.append("entry.json failed validation: " + "; ".join(e["msg"] for e in error.errors()[:5]))
        return EntryMeta(text=str(data.get("text", ""))[:2000]) if isinstance(data.get("text"), str) else EntryMeta()
    if meta.schema_ != ENTRY_SCHEMA:
        problems.append(f"entry.json schema is {meta.schema_!r}; expected {ENTRY_SCHEMA!r}")
    return meta


def load_entry(file_path: Path, workdir: Path, limits: Limits, *, default_title: str) -> Entry:
    """Interpret the staged player bytes. Never raises for bad input: problems are recorded on the Entry."""
    workdir.mkdir(parents=True, exist_ok=True)
    try:
        size = file_path.stat().st_size
    except OSError as error:
        return Entry(
            EntryMeta(title=default_title), None, "none", "invalid", [f"fatal: cannot stat player file ({error})"]
        )
    if size == 0:
        return Entry(EntryMeta(title=default_title), None, "none", "invalid", ["fatal: player file is empty"])
    if size > limits.max_file_bytes:
        return Entry(
            EntryMeta(title=default_title),
            None,
            "none",
            "invalid",
            [f"fatal: player file is {size} bytes (limit {limits.max_file_bytes})"],
        )
    with file_path.open("rb") as handle:
        head = handle.read(16)

    kind = sniff_media(head)
    if kind != "none":
        return Entry(EntryMeta(title=default_title), file_path, kind, "media", ["note: bare media file, no post text"])

    if head[:2] == b"PK":
        return _load_zip(file_path, workdir, default_title)

    # Bare text: entry.json on its own, or the post text as a plain file.
    try:
        text = file_path.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        return Entry(
            EntryMeta(title=default_title),
            None,
            "none",
            "invalid",
            ["fatal: player file is neither media (mp4/mov/webm/png/jpg/webp/gif), a zip package, nor UTF-8 text"],
        )
    problems: list[str] = []
    stripped = text.strip()
    if stripped.startswith("{"):
        meta = _parse_meta(stripped, problems)
        if meta.media:
            problems.append(f"fatal: entry.json names media {meta.media!r} but was uploaded without a package")
            return Entry(meta, None, "none", "invalid", problems)
        return Entry(meta, None, "none", "text", problems)
    if len(stripped) > 2000:
        return Entry(
            EntryMeta(title=default_title), None, "none", "invalid", ["fatal: text file is longer than 2000 characters"]
        )
    return Entry(EntryMeta(text=stripped), None, "none", "text", ["note: bare text file read as the post text"])


def _load_zip(file_path: Path, workdir: Path, default_title: str) -> Entry:
    dest = workdir / "unpacked"
    try:
        problems = _safe_extract(file_path, dest)
    except zipfile.BadZipFile as error:
        return Entry(EntryMeta(title=default_title), None, "none", "invalid", [f"fatal: bad zip ({error})"])
    if any(p.startswith("fatal:") for p in problems):
        return Entry(EntryMeta(title=default_title), None, "none", "invalid", problems)

    root = _find_entry_root(dest)
    entry_json = root / "entry.json"
    if entry_json.exists():
        try:
            meta = _parse_meta(entry_json.read_text(encoding="utf-8"), problems)
        except UnicodeDecodeError as error:
            problems.append(f"entry.json is not UTF-8 ({error}); using defaults")
            meta = EntryMeta()
    else:
        problems.append("no entry.json in package; using defaults")
        meta = EntryMeta()

    media_path: Path | None = None
    if meta.media:
        candidate = (root / meta.media).resolve()
        if candidate.is_relative_to(root.resolve()) and candidate.is_file():
            media_path = candidate
        else:
            fallback = _single_media(root)
            if fallback is None:
                problems.append(f"fatal: media {meta.media!r} not found in package")
                return Entry(meta, None, "none", "invalid", problems)
            problems.append(
                f"media {meta.media!r} not found; using the only media file in the package ({fallback.name})"
            )
            media_path = fallback
    else:
        fallback = _single_media(root)
        if fallback is not None:
            problems.append(f"entry.json names no media; using the only media file in the package ({fallback.name})")
            media_path = fallback

    media_kind: MediaKind = "none"
    if media_path is not None:
        with media_path.open("rb") as handle:
            sniffed = sniff_media(handle.read(16))
        media_kind = sniffed if sniffed != "none" else media_kind_for(media_path)
        if media_kind == "none":
            problems.append(f"fatal: media {media_path.name!r} is not a recognised image, gif or video")
            return Entry(meta, None, "none", "invalid", problems)
    if not meta.text.strip() and media_path is None:
        problems.append("fatal: package has neither post text nor media")
        return Entry(meta, None, "none", "invalid", problems)
    return Entry(meta, media_path, media_kind, "zip", problems)
