from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

from marketing.config import GameConfig


def _with_tokens(config: dict) -> dict:
    return {**config, "tokens": [f"tok-{i}" for i in range(len(config["players"]))]}


def test_variants_and_certification_validate(template: dict) -> None:
    schema = template["game"]["config_schema"]
    for variant in template["variants"]:
        concrete = _with_tokens(variant["game_config"])
        jsonschema.validate(concrete, schema)
        GameConfig.model_validate(concrete)
    cert = _with_tokens(template["certification"]["game_config"])
    jsonschema.validate(cert, schema)
    GameConfig.model_validate(cert)
    assert len(template["certification"]["players"]) == len(template["certification"]["game_config"]["players"])
    # The continuous league grades one post per episode; the manifest must accept a single seat.
    grade = next(v for v in template["variants"] if v["id"] == "grade")
    assert len(grade["game_config"]["players"]) == 1
    assert schema["properties"]["tokens"]["minItems"] == 1


def test_every_player_is_certified_and_exists(template: dict, root: Path) -> None:
    ids = {p["id"] for p in template["player"]}
    seated = {p["player_id"] for p in template["certification"]["players"]}
    assert ids == seated == {"the-wall", "read-the-room", "plain-post"}
    for player in template["player"]:
        assert player["name"] and player["type"] == "player"
        assert "image" not in player and (root / player["file"]).is_dir()
        assert (root / player["file"] / "entry.json").exists()
    assert template["game"]["player_runtime"] == "game-hosted"
    assert template["game"]["name"] == "marketing"
    assert template["game"]["runnable"]["env"]["ENGAGEMENT_FEED_URI"].startswith("secret://coworld/marketing/")
    assert len(template["tags"]) >= 3
    assert "commissioner" not in template


def test_docs_are_synced(root: Path) -> None:
    run = subprocess.run([sys.executable, str(root / "tools/sync_docs.py"), "--check"], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr


def test_replay_viewer_hook(root: Path, tmp_path: Path) -> None:
    out = tmp_path / "bundle"
    out.mkdir()
    (out / "stale.txt").write_text("old")
    subprocess.run([str(root / "tools/build_replay_viewer.sh"), str(out)], check=True, capture_output=True)
    assert (out / "index.html").exists() and not (out / "stale.txt").exists()
    html = (out / "index.html").read_text()
    assert "coworld-replay" in html and "replay" in html


def test_entry_json_files_parse(root: Path) -> None:
    from marketing.entry import EntryMeta, weighted_length

    for player in ("the-wall", "read-the-room", "plain-post"):
        meta = EntryMeta.model_validate(json.loads((root / "players" / player / "entry.json").read_text()))
        assert meta.schema_ == "softmax-post-entry/1"
        assert weighted_length(meta.text) <= 280 and meta.label
        if meta.media:
            assert (root / "players" / player / meta.media).exists()


def test_ladder_settings_are_continuous(root: Path) -> None:
    settings = json.loads((root / "league/ladder_settings.json").read_text())
    ladder = settings["ladder"]
    assert ladder["continuous"]["enabled"] is True and ladder["continuous"]["variant_id"] == "grade"
    assert ladder["ranking"] == {
        "algorithm": "score",
        "round_scoring_rule": "mean",
        "standing_aggregation": "latest",
        "initial_standing": 0.0,
    }
    assert "round_interval_minutes" not in settings
