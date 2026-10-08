from __future__ import annotations

from pathlib import Path

from videomarketing.config import JudgeConfig, Limits
from videomarketing.entry import load_entry
from videomarketing.judge import CraftReview, TechnicalReview, combine, technical_review
from videomarketing.probe import contact_sheet, frame_at, measure


def test_measure_tiny(tiny_video: Path) -> None:
    m = measure(tiny_video)
    assert m.ok and 2.5 < m.duration < 3.5 and m.width == 1280 and m.height == 720 and m.has_audio
    assert m.loudness_lufs is not None


def test_the_wall_passes_the_technical_panel(root: Path, tmp_path: Path) -> None:
    video = root / "players/the-wall/video.mp4"
    entry = load_entry(video, tmp_path / "w", Limits(), default_title="The Wall")
    m = measure(video)
    review = technical_review(entry, m, Limits())
    assert review.eligible
    # bare video: loses post/thesis/entry_json points only
    failed = {c.id for c in review.failures}
    assert failed <= {"post_present", "thesis_present", "entry_json", "loudness"}
    assert review.score >= 80
    assert contact_sheet(video, m.duration, 12, tmp_path / "sheet.jpg")
    assert frame_at(video, m.duration - 1, tmp_path / "end.jpg")


def test_tiny_clip_is_penalised_not_gated(tiny_video: Path, tmp_path: Path) -> None:
    entry = load_entry(tiny_video, tmp_path / "w", Limits(), default_title="t")
    review = technical_review(entry, measure(tiny_video), Limits())
    assert review.eligible
    ids = {c.id for c in review.failures}
    assert "duration_min" in ids and "duration_target" in ids
    assert review.score < 60


def test_gate_failure_zeroes(tiny_video: Path, tmp_path: Path) -> None:
    entry = load_entry(tiny_video, tmp_path / "w", Limits(), default_title="t")
    review = technical_review(entry, measure(tiny_video), Limits(max_duration_seconds=2))
    assert not review.eligible and review.score == 0


def test_combine() -> None:
    cfg = JudgeConfig()
    tech = TechnicalReview(score=90, eligible=True)
    craft = CraftReview(
        scores={"legible": 8, "story_not_statement": 9, "motion": 7, "voice": 8, "craft": 8, "postable": 8},
        cringe_flags=[], notes="", verdict="", model="m", attempts=1,
    )
    assert abs(craft.score - 81.0) < 1e-6
    assert combine(tech, craft, cfg) == round(0.25 * 90 + 0.75 * 81.0, 2)
    assert combine(tech, None, cfg) == 22.5
    assert combine(TechnicalReview(score=0, eligible=False), craft, cfg) == 0.0
