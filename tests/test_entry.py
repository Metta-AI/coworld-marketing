from __future__ import annotations

import json
import zipfile
from pathlib import Path

from marketing.config import Limits
from marketing.entry import count_hashtags, count_links, load_entry, weighted_length


def _zip(path: Path, files: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return path


def test_bare_video_is_accepted_as_media_only(tiny_video: Path, tmp_path: Path) -> None:
    entry = load_entry(tiny_video, tmp_path / "w", Limits(), default_title="seat-0")
    assert entry.kind == "media" and entry.media_kind == "video"
    assert entry.media_path == tiny_video
    assert entry.meta.text == "" and entry.valid


def test_bare_image_is_accepted(tiny_image: Path, tmp_path: Path) -> None:
    entry = load_entry(tiny_image, tmp_path / "w", Limits(), default_title="seat-0")
    assert entry.kind == "media" and entry.media_kind == "image" and entry.valid


def test_bare_text_file_is_the_post(tmp_path: Path) -> None:
    text = tmp_path / "file"
    text.write_text("Five agents, one wall. The clock stops when the last one is over. softmax.com", encoding="utf-8")
    entry = load_entry(text, tmp_path / "w", Limits(), default_title="seat-0")
    assert entry.kind == "text" and entry.media_path is None and entry.valid
    assert entry.meta.text.startswith("Five agents")
    assert entry.meta.label.startswith("Five agents")


def test_bare_entry_json_without_media(tmp_path: Path) -> None:
    text = tmp_path / "file"
    text.write_text(json.dumps({"schema": "softmax-post-entry/1", "text": "Dry line. softmax.com", "title": "Dry"}))
    entry = load_entry(text, tmp_path / "w", Limits(), default_title="x")
    assert entry.kind == "text" and entry.valid and entry.meta.label == "Dry"
    naming_media = tmp_path / "file2"
    naming_media.write_text(json.dumps({"schema": "softmax-post-entry/1", "text": "t", "media": "clip.mp4"}))
    assert not load_entry(naming_media, tmp_path / "w2", Limits(), default_title="x").valid


def test_zip_with_entry_json_and_video(tiny_video: Path, tmp_path: Path) -> None:
    meta = {"schema": "softmax-post-entry/1", "text": "p", "media": "clip.mp4", "alt_text": "a", "thesis": "t"}
    package = _zip(tmp_path / "file", {"entry.json": json.dumps(meta).encode(), "clip.mp4": tiny_video.read_bytes()})
    entry = load_entry(package, tmp_path / "w", Limits(), default_title="x")
    assert entry.kind == "zip" and entry.valid and entry.media_kind == "video"
    assert entry.media_path is not None and entry.media_path.name == "clip.mp4"
    assert not any(p.startswith("fatal") for p in entry.problems)


def test_zip_with_image_and_no_media_field(tiny_image: Path, tmp_path: Path) -> None:
    meta = {"schema": "softmax-post-entry/1", "text": "look"}
    package = _zip(tmp_path / "file", {"entry.json": json.dumps(meta).encode(), "pic.png": tiny_image.read_bytes()})
    entry = load_entry(package, tmp_path / "w", Limits(), default_title="x")
    assert entry.valid and entry.media_kind == "image"
    assert any("names no media" in p for p in entry.problems)


def test_legacy_video_entry_is_read_as_a_video_post(tiny_video: Path, tmp_path: Path) -> None:
    legacy = {
        "schema": "softmax-video-entry/1",
        "title": "The Wall",
        "format": "narrated-fable",
        "video": "video.mp4",
        "post": "the tweet",
        "thesis": "t",
        "script": "narration",
    }
    package = _zip(tmp_path / "file", {"entry.json": json.dumps(legacy).encode(), "video.mp4": tiny_video.read_bytes()})
    entry = load_entry(package, tmp_path / "w", Limits(), default_title="x")
    assert entry.valid and entry.meta.text == "the tweet" and entry.meta.notes == "narration"
    assert entry.meta.label == "The Wall" and entry.media_kind == "video"
    assert any("legacy" in p for p in entry.problems)


def test_zip_nested_directory_and_missing_entry_json(tiny_video: Path, tmp_path: Path) -> None:
    package = _zip(tmp_path / "file", {"my-entry/video.mp4": tiny_video.read_bytes()})
    entry = load_entry(package, tmp_path / "w", Limits(), default_title="seat-3")
    assert entry.valid and entry.media_kind == "video"
    assert any("no entry.json" in p for p in entry.problems)


def test_zip_escape_rejected(tiny_video: Path, tmp_path: Path) -> None:
    package = _zip(tmp_path / "file", {"../evil.mp4": tiny_video.read_bytes()})
    entry = load_entry(package, tmp_path / "w", Limits(), default_title="x")
    assert not entry.valid and any("escapes" in p for p in entry.problems)


def test_binary_garbage_rejected(tmp_path: Path) -> None:
    junk = tmp_path / "file"
    junk.write_bytes(b"\xff\xfe\x00garbage" * 50)
    entry = load_entry(junk, tmp_path / "w", Limits(), default_title="x")
    assert not entry.valid and entry.kind == "invalid"


def test_empty_zip_package_is_invalid(tmp_path: Path) -> None:
    package = _zip(tmp_path / "file", {"entry.json": json.dumps({"schema": "softmax-post-entry/1"}).encode()})
    entry = load_entry(package, tmp_path / "w", Limits(), default_title="x")
    assert not entry.valid and any("neither post text nor media" in p for p in entry.problems)


def test_weighted_length_counts_urls_as_23_and_wide_chars_as_2() -> None:
    assert weighted_length("hello") == 5
    assert weighted_length("see https://softmax.com/some/very/long/path/that/goes/on") == 4 + 23
    assert weighted_length("softmax.com") == 23
    assert weighted_length("日本語") == 6
    assert weighted_length("ok 🙂") == 5
    assert count_hashtags("no tags here, #one #two, not#three") == 2
    assert count_links("a https://x.com/y and softmax.com") == 2
