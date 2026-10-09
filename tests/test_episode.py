from __future__ import annotations

import json
import re
from pathlib import Path

import jsonschema
import pytest

from marketing.check import pack_directory
from marketing.config import GameConfig
from marketing.engagement import FEED_SCHEMA
from marketing.io import decode_replay_bytes
from marketing.judge import RUBRIC_VERSION
from marketing.server import Runtime


def _seats_doc(tmp: Path, files: list[Path], *, hashes: list[str] | None = None) -> dict:
    seats = []
    for slot, f in enumerate(files):
        seats.append(
            {
                "slot": slot,
                "file_uri": f"file://{f}",
                "content_hash": (hashes[slot] if hashes else "sha256:" + f"{slot:064d}"),
                "size_bytes": f.stat().st_size if f.exists() else 0,
                "log_uri": f"file://{tmp}/logs/policy_agent_{slot}.log",
                "artifact_uri": f"file://{tmp}/policy_artifact_{slot}.zip",
            }
        )
    return {"schema": "coworld-player-seats/1", "seats": seats, "player_status_uri": f"file://{tmp}/player_status.json"}


@pytest.fixture
def episode_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("COGAME_RESULTS_URI", f"file://{tmp_path}/results.json")
    monkeypatch.setenv("COGAME_SAVE_REPLAY_URI", f"file://{tmp_path}/replay")
    for var in ("COWORLD_LLM_ENDPOINT", "JUDGE_API_KEY", "OPENROUTER_API_KEY", "ENGAGEMENT_FEED_URI"):
        monkeypatch.delenv(var, raising=False)
    return tmp_path


async def test_certification_shaped_episode(root: Path, template: dict, episode_env: Path) -> None:
    tmp = episode_env
    cert = template["certification"]["game_config"]
    config = GameConfig.model_validate({**cert, "tokens": ["a", "b", "c"], "linger_seconds": 0})
    files = [root / "players/the-wall", root / "players/read-the-room", root / "players/plain-post"]
    staged = [pack_directory(f) for f in files]
    runtime = Runtime(config, seats_doc=_seats_doc(tmp, staged))
    await runtime.run_episode()

    results = json.loads((tmp / "results.json").read_text())
    jsonschema.validate(results, template["game"]["results_schema"])
    assert results["judge_mode"] == "technical"
    assert all(results["eligible"])
    assert results["labels"] == ["The Wall", "Read the Room", "The boat goes straight"]
    assert results["media_kinds"] == ["video", "video", "none"]
    assert results["posted"] == [False, False, False]
    assert results["engagement"] == [0.0, 0.0, 0.0]
    assert results["engagement_feed"]["available"] is False
    # Technical-only judge scores are capped at 25, so nothing is postable and the blend halves them.
    assert results["pick"] is None
    assert all(score == round(0.5 * judge, 2) for score, judge in zip(results["scores"], results["judge"], strict=True))
    assert all(record and record["rubric"] == RUBRIC_VERSION for record in results["judge_records"])
    for slot in range(3):
        log = (tmp / "logs" / f"policy_agent_{slot}.log").read_text()
        assert "score" in log
        assert (tmp / f"policy_artifact_{slot}.zip").exists()
    assert (tmp / "policy_artifact_0.zip").stat().st_size > 1_000_000
    status = json.loads((tmp / "player_status.json").read_text())
    assert [p["state"] for p in status["players"]] == ["exited"] * 3

    replay = decode_replay_bytes((tmp / "replay").read_bytes())
    assert replay["game"] == "marketing" and replay["version"] == 2
    assert len(replay["entries"]) == 3 and replay["results"] == results
    assert set(replay["media"]) == {"0", "1"}
    assert "tokens" not in replay["config"]
    assert replay["entries"][0]["poster"] and replay["entries"][0]["sheet"]
    assert replay["entries"][2]["text"].startswith("We measure alignment")


async def test_engagement_feed_blends_and_caches(
    root: Path, template: dict, episode_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tmp = episode_env
    wall = pack_directory(root / "players/the-wall")
    plain = pack_directory(root / "players/plain-post")
    wall_hash, plain_hash = "sha256:" + "a" * 64, "sha256:" + "b" * 64
    feed = {
        "schema": FEED_SCHEMA,
        "account": "softmaxresearch",
        "generated_at": "2026-10-09T01:00:00Z",
        "posts": {
            wall_hash: {
                "tweet_id": "1",
                "url": "https://x.com/softmaxresearch/status/1",
                "posted_at": "2026-10-08T17:20:00Z",
                "fetched_at": "2026-10-09T01:00:00Z",
                "metrics": {"impressions": 10_000, "likes": 100, "reposts": 25, "replies": 10},
            }
        },
        "judge_cache": {
            plain_hash: {
                "rubric": RUBRIC_VERSION,
                "model": "anthropic/claude-sonnet-4.6",
                "technical": {"score": 100, "eligible": True, "checks": []},
                "craft": {
                    "score": 80,
                    "scores": {"hook": 8, "specific": 8, "voice": 8, "legible": 8, "craft": 8, "repostable": 8},
                    "cringe_flags": [],
                    "notes": "cached notes",
                    "verdict": "cached verdict",
                    "model": "anthropic/claude-sonnet-4.6",
                    "attempts": 1,
                },
            }
        },
    }
    (tmp / "feed.json").write_text(json.dumps(feed))
    monkeypatch.setenv("ENGAGEMENT_FEED_URI", f"file://{tmp}/feed.json")
    # Panel mode with no model endpoint: the cache is the only way a craft score can appear.
    config = GameConfig.model_validate(
        {
            **template["variants"][1]["game_config"],
            "tokens": ["a", "b"],
            "players": [{"name": "A"}, {"name": "B"}],
            "linger_seconds": 0,
        }
    )
    runtime = Runtime(config, seats_doc=_seats_doc(tmp, [wall, plain], hashes=[wall_hash, plain_hash]))
    await runtime.run_episode()
    results = json.loads((tmp / "results.json").read_text())
    jsonschema.validate(results, template["game"]["results_schema"])
    assert results["engagement_feed"]["available"] is True and results["engagement_feed"]["posts"] == 1
    assert results["posted"] == [True, False] and results["tweet_ids"] == ["1", ""]
    assert results["engagement"][0] == 100.0 and results["engagement"][1] == 0.0
    # The Wall: technical only (no model) -> judge <= 25, plus the full engagement half.
    assert results["scores"][0] == round(0.5 * results["judge"][0] + 50.0, 2)
    # Plain post: judged from the cache -> craft 80 present without any model call.
    assert results["craft"][1] == 80.0 and results["judge"][1] == 85.0
    assert results["verdicts"][1] == "cached verdict"
    assert results["judge_mode"] == "panel"
    # A posted entry is never the next pick, even with the top score; the unposted cached one qualifies.
    assert results["pick"] == 1
    log = (tmp / "logs/policy_agent_1.log").read_text()
    assert "judge cache" in log


async def test_missing_and_duplicate_seats(root: Path, template: dict, episode_env: Path) -> None:
    tmp = episode_env
    wall = pack_directory(root / "players/the-wall")
    config = GameConfig.model_validate(
        {
            **template["variants"][2]["game_config"],
            "tokens": ["a", "b", "c"],
            "players": [{"name": "A"}, {"name": "B"}, {"name": "C"}],
            "linger_seconds": 0,
        }
    )
    doc = _seats_doc(tmp, [wall, wall, tmp / "nope"])
    doc["seats"][0]["content_hash"] = doc["seats"][1]["content_hash"] = "sha256:" + "1" * 64
    runtime = Runtime(config, seats_doc=doc)
    await runtime.run_episode()
    results = json.loads((tmp / "results.json").read_text())
    jsonschema.validate(results, template["game"]["results_schema"])
    assert results["eligible"] == [True, True, False]
    assert results["scores"][0] == results["scores"][1] > 0 == results["scores"][2]
    assert re.search(r"identical bytes", (tmp / "logs/policy_agent_1.log").read_text())
    assert (tmp / "logs/policy_agent_2.log").exists()


async def test_single_seat_grade_variant(root: Path, template: dict, episode_env: Path) -> None:
    """The continuous league's grading episode: one seat, one post."""
    tmp = episode_env
    grade = next(v for v in template["variants"] if v["id"] == "grade")
    config = GameConfig.model_validate(
        {**grade["game_config"], "tokens": ["a"], "judge": {"mode": "technical"}, "linger_seconds": 0}
    )
    runtime = Runtime(config, seats_doc=_seats_doc(tmp, [pack_directory(root / "players/plain-post")]))
    await runtime.run_episode()
    results = json.loads((tmp / "results.json").read_text())
    jsonschema.validate(results, template["game"]["results_schema"])
    assert results["eligible"] == [True] and results["technical"] == [100.0]
