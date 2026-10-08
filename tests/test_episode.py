from __future__ import annotations

import json
import re
from pathlib import Path

import jsonschema
import pytest

from videomarketing.config import GameConfig
from videomarketing.io import decode_replay_bytes
from videomarketing.server import Runtime


def _seats_doc(tmp: Path, files: list[Path]) -> dict:
    seats = []
    for slot, f in enumerate(files):
        seats.append(
            {
                "slot": slot,
                "file_uri": f"file://{f}",
                "content_hash": "sha256:" + "0" * 64,
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
    monkeypatch.delenv("COWORLD_LLM_ENDPOINT", raising=False)
    monkeypatch.delenv("JUDGE_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    return tmp_path


async def test_certification_shaped_episode(root: Path, template: dict, episode_env: Path) -> None:
    tmp = episode_env
    cert = template["certification"]["game_config"]
    config = GameConfig.model_validate({**cert, "tokens": ["a", "b"], "linger_seconds": 0})
    files = [root / "players/the-wall", root / "players/read-the-room"]
    # the runner stages a directory as a zip named "file"
    from videomarketing.check import pack_directory

    staged = [pack_directory(f) for f in files]
    runtime = Runtime(config, seats_doc=_seats_doc(tmp, staged))
    await runtime.run_episode()

    results = json.loads((tmp / "results.json").read_text())
    jsonschema.validate(results, template["game"]["results_schema"])
    assert results["judge_mode"] == "technical"
    assert all(results["eligible"])
    assert results["titles"] == ["The Wall", "Read the Room"]
    assert results["formats"] == ["narrated-fable", "kinetic-music-video"]
    assert results["feed_pick"] is None  # technical-only scores are capped at 25
    for slot in range(2):
        log = (tmp / "logs" / f"policy_agent_{slot}.log").read_text()
        assert "measurement" in log and "score" in log
        assert (tmp / f"policy_artifact_{slot}.zip").stat().st_size > 1_000_000
    status = json.loads((tmp / "player_status.json").read_text())
    assert [p["state"] for p in status["players"]] == ["exited", "exited"]

    replay = decode_replay_bytes((tmp / "replay").read_bytes())
    assert replay["game"] == "softmax-video-marketing"
    assert len(replay["entries"]) == 2 and replay["results"] == results
    assert set(replay["media"]) == {"0", "1"}
    assert "tokens" not in replay["config"]
    assert replay["entries"][0]["poster"] and replay["entries"][0]["sheet"]


async def test_missing_and_duplicate_seats(root: Path, template: dict, episode_env: Path) -> None:
    tmp = episode_env
    from videomarketing.check import pack_directory

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
