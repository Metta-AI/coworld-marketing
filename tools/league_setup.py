#!/usr/bin/env python3
"""Apply the daily-league topology and ladder settings. Team-only: divisions and ladder settings are platform-owned.

Run as a Softmax team member (the call sends X-Use-Elevated-Privileges):

    cd metta && uv run python ../coworld-video-marketing/tools/league_setup.py league_... [--enable] [--trigger]

Steps: declare one Competition division, merge league/ladder_settings.json into the league settings (preserving
siblings such as counterfactual_eval), optionally enable the ladder and trigger the first round.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://softmax.com/api/observatory/v2"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("league_id")
    parser.add_argument("--enable", action="store_true", help="set ladder.enabled true after writing the document")
    parser.add_argument("--trigger", action="store_true", help="trigger the first round after enabling")
    parser.add_argument("--daily-budget-usd", type=float, default=15.0, help="small-field daily budget; 0 to skip")
    args = parser.parse_args()

    from softmax.auth import load_user_token  # provided by the metta checkout / softmax package

    token = load_user_token(server="https://softmax.com/api")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "coworld-video-marketing-setup/0.1",
        "X-Use-Elevated-Privileges": "true",
    }

    def call(method: str, path: str, body: dict | None = None):
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(f"{BASE}{path}", data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read().decode()
                return response.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as error:
            return error.code, error.read().decode()[:600]

    league = args.league_id
    status, body = call(
        "PUT",
        f"/leagues/{league}/divisions",
        {"divisions": [{"name": "Competition", "level": 1, "type": "competition", "hidden": False}]},
    )
    print("divisions:", status, str(body)[:300])
    if status >= 300:
        return 1
    status, divisions = call("GET", f"/divisions?league_id={league}")
    competition = next((d for d in divisions if d.get("name") == "Competition"), divisions[0])
    division_id = competition["id"]
    print("competition division:", division_id)

    status, current = call("GET", f"/leagues/{league}/settings")
    if status != 200:
        print("settings GET failed:", status, current)
        return 1
    settings = current["settings"]
    desired = json.loads((ROOT / "league/ladder_settings.json").read_text())
    ladder = desired["ladder"]
    ladder["divisions"] = [{**d, "division_id": division_id} for d in ladder["divisions"]]
    ladder["enabled"] = bool(args.enable)
    settings["ladder"] = ladder
    settings["round_interval_minutes"] = desired["round_interval_minutes"]
    status, body = call("POST", f"/leagues/{league}/settings", settings)
    print("settings:", status, str(body)[:300])
    if status >= 300:
        return 1

    if args.daily_budget_usd > 0:
        status, body = call(
            "PUT",
            f"/leagues/{league}/league-budget",
            {"daily_budget_usd": args.daily_budget_usd, "note": "small-field policy: <6 players"},
        )
        print("budget:", status, str(body)[:200])

    if args.enable:
        status, body = call("POST", f"/leagues/{league}/rounds-paused", {"paused": False})
        print("unpause:", status, str(body)[:200])
        if args.trigger:
            status, body = call("POST", f"/leagues/{league}/trigger-round", {})
            print("trigger-round:", status, str(body)[:300])
    status, after = call("GET", f"/leagues/{league}/settings")
    print("effective ladder:", json.dumps(after.get("effective_ladder_config"))[:500] if status == 200 else after)
    return 0


if __name__ == "__main__":
    sys.exit(main())
