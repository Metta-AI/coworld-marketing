"""Load one submitted player file: a zip with entry.json and optional media, a bare media file, or bare text.

Three entry.json schemas load here and all normalise into one in-memory `Entry` whose `media` is a list:

- `softmax-post-entry/2` (current): `media` is a list of `{path, alt_text}` objects, so a post can carry up to four
  images the way X does. A video or a gif must be the only item; kinds are never mixed.
- `softmax-post-entry/1`: a single `media` path (or null) with one top-level `alt_text`.
- `softmax-video-entry/1`: the video league's package; `post` is the text, `video` the media, `script` the notes.

Validation problems are written as sentences because they surface to the submitter in the seat log and the jury.
"""

from __future__ import annotations

import json
import re
import stat
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from marketing.config import Limits, MediaKind

ENTRY_SCHEMA = "softmax-post-entry/2"
ENTRY_SCHEMA_V1 = "softmax-post-entry/1"
LEGACY_VIDEO_SCHEMA = "softmax-video-entry/1"
ACCEPTED_SCHEMAS = (ENTRY_SCHEMA, ENTRY_SCHEMA_V1, LEGACY_VIDEO_SCHEMA)
MAX_MEDIA_ITEMS = 4
MAX_ZIP_MEMBERS = 200
MAX_UNPACKED_BYTES = 160 * 1024 * 1024
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
GIF_SUFFIXES = {".gif"}
MEDIA_SUFFIXES = VIDEO_SUFFIXES | IMAGE_SUFFIXES | GIF_SUFFIXES
URL_RE = re.compile(r"https?://\S+|(?<![\w@])(?:[a-z0-9-]+\.)+[a-z]{2,}(?:/\S*)?", re.IGNORECASE)
HASHTAG_RE = re.compile(r"(?<!\w)#\w+")
MEDIA_RULE = (
    f"a post carries up to {MAX_MEDIA_ITEMS} images (png/jpg/jpeg/webp), or exactly one video, or exactly one gif"
)


class MediaMeta(BaseModel):
    """One attachment as named in entry.json."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, max_length=400, description="Relative path of the file inside the package.")
    alt_text: str = Field(default="", max_length=1500, description="Accessibility text for this attachment.")


class EntryMeta(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_: str = Field(default=ENTRY_SCHEMA, alias="schema")
    text: str = Field(default="", max_length=2000, description="The post text as it would appear on X.")
    media: list[MediaMeta] = Field(
        default_factory=list,
        max_length=32,
        description=f"Attachments inside the package, in display order; {MEDIA_RULE}.",
    )
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

    @property
    def alt_text(self) -> str:
        """The first attachment's alt text; kept for callers written against the single-media schema."""
        return self.media[0].alt_text if self.media else ""


class _EntryMetaV1(BaseModel):
    """The single-media schema, validated on its own terms before it is converted."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_: str = Field(alias="schema")
    text: str = Field(default="", max_length=2000)
    media: str | None = None
    alt_text: str = Field(default="", max_length=1500)
    title: str = Field(default="", max_length=120)
    thesis: str = Field(default="", max_length=400)
    notes: str = Field(default="", max_length=4000)
    credits: str = Field(default="", max_length=400)
    made_with: list[str] = Field(default_factory=list, max_length=20)

    def to_current(self) -> EntryMeta:
        media = [MediaMeta(path=self.media, alt_text=self.alt_text)] if self.media else []
        return EntryMeta(
            schema=ENTRY_SCHEMA,
            text=self.text,
            media=media,
            title=self.title,
            thesis=self.thesis,
            notes=self.notes,
            credits=self.credits,
            made_with=self.made_with,
        )


@dataclass(frozen=True)
class MediaItem:
    """One resolved attachment: where the bytes are, what they are, and how the entrant described them."""

    path: Path
    kind: MediaKind
    alt_text: str = ""
    name: str = ""  # the path as named in the package; the artifact zip writes the file under this name

    @property
    def display_name(self) -> str:
        return self.name or self.path.name


@dataclass
class Entry:
    meta: EntryMeta
    media: list[MediaItem]
    kind: str  # "zip" | "media" | "text" | "invalid"
    problems: list[str] = field(default_factory=list)

    @property
    def fatal(self) -> bool:
        return any(p.startswith("fatal:") for p in self.problems)

    @property
    def valid(self) -> bool:
        return not self.fatal and (bool(self.meta.text.strip()) or bool(self.media))

    @property
    def media_kind(self) -> MediaKind:
        """The kind shared by every attachment ("image" for one to four pictures), or "none"."""
        return self.media[0].kind if self.media else "none"

    @property
    def media_path(self) -> Path | None:
        """The first attachment's path; kept for callers written against the single-media schema."""
        return self.media[0].path if self.media else None


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


def _kind_of(path: Path) -> MediaKind:
    with path.open("rb") as handle:
        sniffed = sniff_media(handle.read(16))
    return sniffed if sniffed != "none" else media_kind_for(path)


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


def _package_media(root: Path) -> list[Path]:
    """Every file in the package whose suffix says media, in a stable order."""
    return sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in MEDIA_SUFFIXES)


def _describe(error: ValidationError) -> str:
    parts = []
    for item in error.errors()[:5]:
        where = ".".join(str(x) for x in item["loc"] if x != "schema_") or "entry.json"
        parts.append(f"{where}: {item['msg']}")
    return "; ".join(parts)


def _parse_meta(raw: str, problems: list[str]) -> EntryMeta:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as error:
        problems.append(f"entry.json is not valid JSON ({error}); using defaults")
        return EntryMeta()
    if not isinstance(data, dict):
        problems.append("entry.json is not an object; using defaults")
        return EntryMeta()
    schema = data.get("schema")
    if schema == LEGACY_VIDEO_SCHEMA:
        # A video-era package: the post text is the tweet, the video is the media.
        data = {
            "schema": ENTRY_SCHEMA_V1,
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
        schema = ENTRY_SCHEMA_V1
    elif schema not in ACCEPTED_SCHEMAS:
        problems.append(
            f"entry.json schema is {schema!r}; expected {ENTRY_SCHEMA!r} (or the older {ENTRY_SCHEMA_V1!r}); "
            f"reading it as {ENTRY_SCHEMA!r}"
        )
        data = {**data, "schema": ENTRY_SCHEMA}
    try:
        if schema == ENTRY_SCHEMA_V1:
            return _EntryMetaV1.model_validate(data).to_current()
        return EntryMeta.model_validate(data)
    except ValidationError as error:
        problems.append(f"entry.json failed validation ({_describe(error)}); using the text only")
        text = data.get("text")
        return EntryMeta(text=text[:2000]) if isinstance(text, str) else EntryMeta()


def _invalid(default_title: str, problem: str) -> Entry:
    return Entry(EntryMeta(title=default_title), [], "invalid", [problem])


def load_entry(file_path: Path, workdir: Path, limits: Limits, *, default_title: str) -> Entry:
    """Interpret the staged player bytes. Never raises for bad input: problems are recorded on the Entry."""
    workdir.mkdir(parents=True, exist_ok=True)
    try:
        size = file_path.stat().st_size
    except OSError as error:
        return _invalid(default_title, f"fatal: cannot stat player file ({error})")
    if size == 0:
        return _invalid(default_title, "fatal: player file is empty")
    if size > limits.max_file_bytes:
        return _invalid(default_title, f"fatal: player file is {size} bytes (limit {limits.max_file_bytes})")
    with file_path.open("rb") as handle:
        head = handle.read(16)

    kind = sniff_media(head)
    if kind != "none":
        item = MediaItem(file_path, kind, "", file_path.name)
        return Entry(EntryMeta(title=default_title), [item], "media", ["note: bare media file, no post text"])

    if head[:2] == b"PK":
        return _load_zip(file_path, workdir, limits, default_title)

    # Bare text: entry.json on its own, or the post text as a plain file.
    try:
        text = file_path.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        return _invalid(
            default_title,
            "fatal: player file is neither media (mp4/mov/webm/png/jpg/webp/gif), a zip package, nor UTF-8 text",
        )
    problems: list[str] = []
    stripped = text.strip()
    if stripped.startswith("{"):
        meta = _parse_meta(stripped, problems)
        if meta.media:
            named = ", ".join(repr(m.path) for m in meta.media)
            problems.append(f"fatal: entry.json names media {named} but was uploaded without a package")
            return Entry(meta, [], "invalid", problems)
        return Entry(meta, [], "text", problems)
    if len(stripped) > 2000:
        return _invalid(default_title, "fatal: text file is longer than 2000 characters")
    return Entry(EntryMeta(text=stripped), [], "text", ["note: bare text file read as the post text"])


def _load_zip(file_path: Path, workdir: Path, limits: Limits, default_title: str) -> Entry:
    dest = workdir / "unpacked"
    try:
        problems = _safe_extract(file_path, dest)
    except zipfile.BadZipFile as error:
        return _invalid(default_title, f"fatal: bad zip ({error})")
    if any(p.startswith("fatal:") for p in problems):
        return Entry(EntryMeta(title=default_title), [], "invalid", problems)

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

    media = _resolve_media(root, meta, limits, problems)
    if media is None:
        return Entry(meta, [], "invalid", problems)
    if not meta.text.strip() and not media:
        problems.append("fatal: package has neither post text nor media")
        return Entry(meta, [], "invalid", problems)
    return Entry(meta, media, "zip", problems)


def _resolve_media(root: Path, meta: EntryMeta, limits: Limits, problems: list[str]) -> list[MediaItem] | None:
    """Turn the names in entry.json into checked attachments; None (with a fatal problem) when the post cannot run."""
    root_resolved = root.resolve()
    present = _package_media(root)
    if not meta.media:
        if not present:
            return []
        if len(present) > 1:
            names = ", ".join(p.relative_to(root).as_posix() for p in present[:6])
            problems.append(
                f"fatal: the package contains {len(present)} media files ({names}) but entry.json names none; "
                "name the media files in entry.json, in the order they should appear"
            )
            return None
        only = present[0]
        name = only.relative_to(root).as_posix()
        problems.append(f"entry.json names no media; using the only media file in the package ({only.name})")
        item = MediaItem(only, _kind_of(only), "", name)
        return [item] if _check_kinds([(name, item.kind)], problems) else None

    limit = min(limits.max_media_items, MAX_MEDIA_ITEMS)
    if len(meta.media) > limit:
        problems.append(f"fatal: entry.json lists {len(meta.media)} media files; {MEDIA_RULE}")
        return None

    items: list[MediaItem] = []
    seen: dict[Path, str] = {}
    for spec in meta.media:
        candidate = (root / spec.path).resolve()
        if not (candidate.is_relative_to(root_resolved) and candidate.is_file()):
            if len(meta.media) == 1 and len(present) == 1:
                candidate = present[0]
                problems.append(
                    f"media {spec.path!r} not found; using the only media file in the package ({candidate.name})"
                )
            else:
                problems.append(f"fatal: media {spec.path!r} is named in entry.json but is not in the package")
                return None
        if candidate in seen:
            problems.append(f"fatal: media {spec.path!r} is listed twice in entry.json (also as {seen[candidate]!r})")
            return None
        seen[candidate] = spec.path
        name = candidate.relative_to(root_resolved).as_posix()
        items.append(MediaItem(candidate, _kind_of(candidate), spec.alt_text, name))

    if not _check_kinds([(item.name, item.kind) for item in items], problems):
        return None
    return items


def _check_kinds(named: list[tuple[str, MediaKind]], problems: list[str]) -> bool:
    """One to four images, or one video, or one gif; every file recognised."""
    for name, kind in named:
        if kind == "none":
            problems.append(f"fatal: media {name!r} is not a recognised image, gif or video")
            return False
    kinds = {kind for _, kind in named}
    if len(kinds) > 1:
        listing = ", ".join(f"{name} ({kind})" for name, kind in named)
        problems.append(f"fatal: media kinds cannot be mixed in one post ({listing}); {MEDIA_RULE}")
        return False
    if len(named) > 1 and kinds & {"video", "gif"}:
        kind = next(iter(kinds))
        problems.append(f"fatal: a {kind} must be the only attachment, but entry.json lists {len(named)}; {MEDIA_RULE}")
        return False
    return True
