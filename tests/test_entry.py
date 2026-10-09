from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from marketing.config import Limits
from marketing.entry import ENTRY_SCHEMA, EntryMeta, count_hashtags, count_links, load_entry, weighted_length


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


# --------------------------------------------------------------------------- schema v2: a media list


def _v2(text: str = "look", **extra) -> dict:
    return {"schema": ENTRY_SCHEMA, "text": text, **extra}


def _images(tiny_image: Path, names: list[str]) -> dict[str, bytes]:
    return {name: tiny_image.read_bytes() for name in names}


def test_v2_four_images_in_order_with_alt_text(tiny_image: Path, tmp_path: Path) -> None:
    names = ["d.png", "a.png", "c.png", "b.png"]
    meta = _v2(media=[{"path": n, "alt_text": f"alt {n}"} for n in names])
    package = _zip(tmp_path / "file", {"entry.json": json.dumps(meta).encode(), **_images(tiny_image, names)})
    entry = load_entry(package, tmp_path / "w", Limits(), default_title="x")
    assert entry.valid and entry.kind == "zip" and entry.media_kind == "image"
    assert [m.name for m in entry.media] == names  # entry.json order, not alphabetical
    assert [m.alt_text for m in entry.media] == [f"alt {n}" for n in names]
    assert all(m.kind == "image" for m in entry.media)
    assert entry.media_path == entry.media[0].path and entry.meta.alt_text == "alt d.png"
    assert not any(p.startswith("fatal") for p in entry.problems)


def test_v2_five_images_rejected_readably(tiny_image: Path, tmp_path: Path) -> None:
    names = [f"{i}.png" for i in range(5)]
    meta = _v2(media=[{"path": n} for n in names])
    package = _zip(tmp_path / "file", {"entry.json": json.dumps(meta).encode(), **_images(tiny_image, names)})
    entry = load_entry(package, tmp_path / "w", Limits(), default_title="x")
    assert not entry.valid and entry.kind == "invalid"
    assert any("lists 5 media files" in p and "up to 4 images" in p for p in entry.problems)


def test_v2_video_and_image_mix_rejected(tiny_video: Path, tiny_image: Path, tmp_path: Path) -> None:
    meta = _v2(media=[{"path": "clip.mp4", "alt_text": "a"}, {"path": "pic.png", "alt_text": "b"}])
    files = {"entry.json": json.dumps(meta).encode(), "clip.mp4": tiny_video.read_bytes()}
    files["pic.png"] = tiny_image.read_bytes()
    entry = load_entry(_zip(tmp_path / "file", files), tmp_path / "w", Limits(), default_title="x")
    assert not entry.valid
    assert any("cannot be mixed" in p and "clip.mp4 (video)" in p and "pic.png (image)" in p for p in entry.problems)


def test_v2_two_videos_rejected(tiny_video: Path, tmp_path: Path) -> None:
    meta = _v2(media=[{"path": "a.mp4"}, {"path": "b.mp4"}])
    files = {"entry.json": json.dumps(meta).encode(), "a.mp4": tiny_video.read_bytes()}
    files["b.mp4"] = tiny_video.read_bytes()
    entry = load_entry(_zip(tmp_path / "file", files), tmp_path / "w", Limits(), default_title="x")
    assert not entry.valid and any("a video must be the only attachment" in p for p in entry.problems)


def test_v2_duplicate_path_rejected(tiny_image: Path, tmp_path: Path) -> None:
    meta = _v2(media=[{"path": "pic.png"}, {"path": "./pic.png"}])
    files = {"entry.json": json.dumps(meta).encode(), "pic.png": tiny_image.read_bytes()}
    entry = load_entry(_zip(tmp_path / "file", files), tmp_path / "w", Limits(), default_title="x")
    assert not entry.valid and any("listed twice" in p for p in entry.problems)


def test_v2_missing_named_media_is_fatal(tiny_image: Path, tmp_path: Path) -> None:
    meta = _v2(media=[{"path": "a.png"}, {"path": "missing.png"}])
    files = {"entry.json": json.dumps(meta).encode(), "a.png": tiny_image.read_bytes()}
    entry = load_entry(_zip(tmp_path / "file", files), tmp_path / "w", Limits(), default_title="x")
    assert not entry.valid
    assert any("'missing.png' is named in entry.json but is not in the package" in p for p in entry.problems)


def test_unnamed_multiple_media_is_an_error_not_a_text_post(tiny_image: Path, tmp_path: Path) -> None:
    meta = _v2(text="two pictures, no names")
    files = {"entry.json": json.dumps(meta).encode(), **_images(tiny_image, ["a.png", "b.png"])}
    entry = load_entry(_zip(tmp_path / "file", files), tmp_path / "w", Limits(), default_title="x")
    assert not entry.valid and entry.media == []
    assert any("contains 2 media files" in p and "name the media files in entry.json" in p for p in entry.problems)


def test_v2_top_level_alt_text_is_rejected_with_a_readable_sentence(tiny_image: Path, tmp_path: Path) -> None:
    meta = _v2(media=[{"path": "pic.png"}], alt_text="belongs on the item")
    files = {"entry.json": json.dumps(meta).encode(), "pic.png": tiny_image.read_bytes()}
    entry = load_entry(_zip(tmp_path / "file", files), tmp_path / "w", Limits(), default_title="x")
    # Validation fell back to the text, the lone picture was still found, and the problem reads as a sentence.
    expected = "entry.json failed validation (alt_text: Extra inputs are not permitted"
    assert any(p.startswith(expected) for p in entry.problems)
    assert entry.media_kind == "image"


def test_v1_single_media_still_parses_into_the_list(tiny_image: Path, tmp_path: Path) -> None:
    meta = {"schema": "softmax-post-entry/1", "text": "p", "media": "pic.png", "alt_text": "a picture"}
    files = {"entry.json": json.dumps(meta).encode(), "pic.png": tiny_image.read_bytes()}
    entry = load_entry(_zip(tmp_path / "file", files), tmp_path / "w", Limits(), default_title="x")
    assert entry.valid and len(entry.media) == 1 and entry.media[0].alt_text == "a picture"
    assert entry.meta.schema_ == ENTRY_SCHEMA and entry.meta.alt_text == "a picture"
    assert not any(p.startswith("fatal") or p.startswith("entry.json") for p in entry.problems)


def test_v1_text_only_with_null_media(tmp_path: Path) -> None:
    text = tmp_path / "file"
    text.write_text(json.dumps({"schema": "softmax-post-entry/1", "text": "dry", "media": None, "alt_text": ""}))
    entry = load_entry(text, tmp_path / "w", Limits(), default_title="x")
    assert entry.valid and entry.kind == "text" and entry.media == [] and entry.media_kind == "none"


def test_bare_gif_is_media_kind_gif(tmp_path: Path) -> None:
    gif = tmp_path / "file"
    gif.write_bytes(b"GIF89a" + bytes(40))
    entry = load_entry(gif, tmp_path / "w", Limits(), default_title="x")
    assert entry.kind == "media" and entry.media_kind == "gif" and entry.media[0].kind == "gif"


@pytest.mark.parametrize("bad", [{"media": "pic.png"}, {"media": [{"path": "pic.png", "caption": "x"}]}])
def test_v2_media_must_be_a_list_of_objects(bad: dict) -> None:
    with pytest.raises(ValidationError):
        EntryMeta.model_validate(_v2(**bad))
