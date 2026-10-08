from __future__ import annotations

import json
import zipfile
from pathlib import Path

from videomarketing.config import Limits
from videomarketing.entry import load_entry


def _zip(path: Path, files: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return path


def test_bare_video_is_accepted(tiny_video: Path, tmp_path: Path) -> None:
    entry = load_entry(tiny_video, tmp_path / "w", Limits(), default_title="seat-0")
    assert entry.kind == "video"
    assert entry.video_path == tiny_video
    assert entry.meta.title == "seat-0"
    assert entry.valid


def test_zip_with_entry_json(tiny_video: Path, tmp_path: Path) -> None:
    meta = {
        "schema": "softmax-video-entry/1", "title": "T", "format": "narrated-fable", "video": "clip.mp4",
        "post": "p", "thesis": "t",
    }
    package = _zip(tmp_path / "file", {"entry.json": json.dumps(meta).encode(), "clip.mp4": tiny_video.read_bytes()})
    entry = load_entry(package, tmp_path / "w", Limits(), default_title="x")
    assert entry.kind == "zip" and entry.valid
    assert entry.meta.title == "T" and entry.meta.format == "narrated-fable"
    assert entry.video_path is not None and entry.video_path.name == "clip.mp4"
    assert not any(p.startswith("fatal") for p in entry.problems)


def test_zip_nested_directory_and_missing_entry_json(tiny_video: Path, tmp_path: Path) -> None:
    package = _zip(tmp_path / "file", {"my-entry/video.mp4": tiny_video.read_bytes()})
    entry = load_entry(package, tmp_path / "w", Limits(), default_title="seat-3")
    assert entry.valid and entry.meta.title == "seat-3"
    assert any("no entry.json" in p for p in entry.problems)


def test_zip_escape_rejected(tiny_video: Path, tmp_path: Path) -> None:
    package = _zip(tmp_path / "file", {"../evil.mp4": tiny_video.read_bytes()})
    entry = load_entry(package, tmp_path / "w", Limits(), default_title="x")
    assert not entry.valid and any("escapes" in p for p in entry.problems)


def test_garbage_rejected(tmp_path: Path) -> None:
    junk = tmp_path / "file"
    junk.write_bytes(b"hello world this is not a video" * 10)
    entry = load_entry(junk, tmp_path / "w", Limits(), default_title="x")
    assert not entry.valid and entry.kind == "invalid"


def test_invalid_entry_json_falls_back(tiny_video: Path, tmp_path: Path) -> None:
    package = _zip(tmp_path / "file", {"entry.json": b"{not json", "video.mp4": tiny_video.read_bytes()})
    entry = load_entry(package, tmp_path / "w", Limits(), default_title="seat-1")
    assert entry.valid and entry.meta.title == "seat-1"
    assert any("not valid JSON" in p for p in entry.problems)
