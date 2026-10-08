from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

from videomarketing.config import GameConfig


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


def test_every_player_is_certified_and_exists(template: dict, root: Path) -> None:
    ids = {p["id"] for p in template["player"]}
    seated = {p["player_id"] for p in template["certification"]["players"]}
    assert ids == seated
    for player in template["player"]:
        assert "image" not in player and (root / player["file"]).is_dir()
        assert (root / player["file"] / "entry.json").exists() and (root / player["file"] / "video.mp4").exists()
    assert template["game"]["player_runtime"] == "game-hosted"
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
    from videomarketing.entry import EntryMeta

    for player in ("the-wall", "read-the-room"):
        meta = EntryMeta.model_validate(json.loads((root / "players" / player / "entry.json").read_text()))
        assert len(meta.post) <= 280 and meta.thesis and meta.script
