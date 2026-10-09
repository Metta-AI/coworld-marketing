from __future__ import annotations

import json
from pathlib import Path

from marketing.config import EngagementConfig, JudgeConfig, Limits
from marketing.engagement import blend, engagement_score, metric_fraction, parse_feed
from marketing.entry import EntryMeta, load_entry
from marketing.judge import (
    RUBRIC_VERSION,
    CraftReview,
    TechnicalReview,
    cache_record,
    from_cache,
    judge_score,
    technical_review,
)
from marketing.probe import contact_sheet, frame_at, measure, still_image


def test_measure_video_and_image(tiny_video: Path, tiny_image: Path) -> None:
    m = measure(tiny_video, "video")
    assert m.ok and 2.5 < m.duration < 3.5 and m.width == 1280 and m.height == 720 and m.has_audio
    assert m.loudness_lufs is not None
    i = measure(tiny_image, "image")
    assert i.ok and i.kind == "image" and i.width == 640 and i.height == 360 and i.duration == 0


def test_the_wall_passes_the_technical_panel(root: Path, tmp_path: Path) -> None:
    from marketing.check import pack_directory

    package = pack_directory(root / "players/the-wall")
    entry = load_entry(package, tmp_path / "w", Limits(), default_title="The Wall")
    assert entry.media_path is not None
    m = measure(entry.media_path, "video")
    review = technical_review(entry, m, Limits())
    assert review.eligible
    assert {c.id for c in review.failures} <= {"video_loudness"}
    assert review.score >= 90
    assert contact_sheet(entry.media_path, m.duration, 12, tmp_path / "sheet.jpg")
    assert frame_at(entry.media_path, m.duration - 1, tmp_path / "end.jpg")


def test_text_only_post_is_judged_on_text_rules(tmp_path: Path) -> None:
    post = tmp_path / "file"
    post.write_text("One true thing about the work. softmax.com #alignment #ai #agents", encoding="utf-8")
    entry = load_entry(post, tmp_path / "w", Limits(), default_title="t")
    review = technical_review(entry, None, Limits())
    assert review.eligible
    assert {c.id for c in review.failures} == {"hashtags"}
    assert review.score == 95


def test_overlong_text_fails_the_gate(tmp_path: Path) -> None:
    post = tmp_path / "file"
    post.write_text("x" * 281, encoding="utf-8")
    entry = load_entry(post, tmp_path / "w", Limits(), default_title="t")
    review = technical_review(entry, None, Limits())
    assert not review.eligible and review.score == 0
    assert any(c.id == "text_length" and not c.ok for c in review.checks)


def test_image_post_without_alt_text_is_penalised_not_gated(tiny_image: Path, tmp_path: Path) -> None:
    entry = load_entry(tiny_image, tmp_path / "w", Limits(), default_title="t")
    review = technical_review(entry, measure(tiny_image, "image"), Limits())
    assert review.eligible
    assert {c.id for c in review.failures} == {"text_present", "alt_text"}
    assert still_image(tiny_image, tmp_path / "still.jpg")


def test_video_gates(tiny_video: Path, tmp_path: Path) -> None:
    entry = load_entry(tiny_video, tmp_path / "w", Limits(), default_title="t")
    review = technical_review(entry, measure(tiny_video, "video"), Limits(video_max_seconds=2))
    assert not review.eligible and review.score == 0


def test_judge_score_and_blend() -> None:
    cfg = JudgeConfig()
    tech = TechnicalReview(score=90, eligible=True)
    craft = CraftReview(
        scores={"hook": 8, "specific": 9, "voice": 7, "legible": 8, "craft": 8, "repostable": 8},
        cringe_flags=[],
        notes="",
        verdict="",
        model="m",
        attempts=1,
    )
    assert abs(craft.score - 79.5) < 1e-6
    assert judge_score(tech, craft, cfg) == round(0.25 * 90 + 0.75 * 79.5, 2)
    assert judge_score(tech, None, cfg) == 22.5
    assert judge_score(TechnicalReview(score=0, eligible=False), craft, cfg) == 0.0
    eng = EngagementConfig()
    assert blend(80.0, 0.0, eng) == 40.0
    assert blend(80.0, 60.0, eng) == 70.0


def test_engagement_curve_and_feed() -> None:
    cfg = EngagementConfig()
    assert metric_fraction(0, 100) == 0.0
    assert metric_fraction(100, 100) == 1.0
    assert 0.85 < metric_fraction(50, 100) < 0.95
    assert metric_fraction(10_000, 100) == 1.0
    assert engagement_score(None, cfg) == 0.0
    full = engagement_score({"impressions": 10_000, "likes": 100, "reposts": 25, "replies": 10}, cfg)
    assert full == 100.0
    partial = engagement_score({"impressions": 1_000, "likes": 10, "reposts": 0, "replies": 0}, cfg)
    assert 40 < partial < 70

    feed = parse_feed(
        json.dumps(
            {
                "schema": "softmax-engagement-feed/1",
                "account": "softmaxresearch",
                "generated_at": "2026-10-09T00:00:00Z",
                "posts": {
                    "sha256:abc": {
                        "tweet_id": "1",
                        "url": "https://x.com/softmaxresearch/status/1",
                        "posted_at": "2026-10-08T00:00:00Z",
                        "fetched_at": "2026-10-09T00:00:00Z",
                        "metrics": {"impressions": "1200", "likes": 31, "reposts": 4, "replies": 2, "quotes": 1},
                    }
                },
                "judge_cache": {
                    "sha256:abc": {
                        "rubric": RUBRIC_VERSION,
                        "model": "m",
                        "technical": {"score": 95, "eligible": True, "checks": []},
                        "craft": None,
                    }
                },
            }
        ),
        source="test",
    )
    assert feed.available and feed.post_for("sha256:abc") is not None
    assert (
        feed.post_for("sha256:abc").metrics["impressions"] == 1200
        and feed.post_for("sha256:abc").metrics["quotes"] == 1
    )
    assert parse_feed(b"not json", source="t").available is False
    assert parse_feed(json.dumps({"schema": "other/1"}), source="t").available is False


def test_judge_cache_round_trip() -> None:
    tech = TechnicalReview(score=95, eligible=True)
    craft = CraftReview(
        scores={"hook": 7, "specific": 7, "voice": 7, "legible": 7, "craft": 7, "repostable": 7},
        cringe_flags=["a flag"],
        notes="n",
        verdict="v",
        model="m",
        attempts=1,
    )
    record = cache_record(tech, craft, "m")
    assert record["rubric"] == RUBRIC_VERSION
    restored = from_cache(record, "m")
    assert restored is not None
    r_tech, r_craft = restored
    assert r_tech.score == 95 and r_tech.eligible and r_craft is not None and r_craft.cached
    assert r_craft.score == craft.score and r_craft.cringe_flags == ["a flag"]
    assert from_cache(record, "other-model") is None
    assert from_cache({**record, "rubric": "post/0"}, "m") is None
    assert EntryMeta(text="hello").label == "hello"
