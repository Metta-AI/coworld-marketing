#!/usr/bin/env python3
"""Turn a finished episode (its replay JSON) into a feed-ready folder for whoever posts to X.

Usage: python tools/feed_pack.py path/to/replay.json [--out feed/2026-10-08]

Writes winner.mp4 (when the replay carries the media), post.txt, alt.txt and jury.md. Posting stays a human step.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from videomarketing.io import decode_replay_bytes  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("replay", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    replay = decode_replay_bytes(args.replay.read_bytes())
    results = replay.get("results") or {}
    entries = {e["slot"]: e for e in replay.get("entries", [])}
    out = args.out or Path("feed") / dt.date.today().isoformat()
    out.mkdir(parents=True, exist_ok=True)

    pick = results.get("feed_pick")
    ranking = sorted(entries.values(), key=lambda e: (-e.get("score", 0), e["slot"]))
    judge_line = f"Judge: {results.get('judge_mode')} {results.get('judge_model', '')}".rstrip()
    lines = ["# Jury", "", f"Brief: {replay.get('brief', '')}", judge_line, ""]
    for rank, e in enumerate(ranking, 1):
        mark = " (feed pick)" if e["slot"] == pick else ""
        lines.append(f"{rank}. {e['title']} by {e['name']} — {e.get('score', 0):.1f}{mark}")
        verdict = (results.get("verdicts") or [""] * (e["slot"] + 1))[e["slot"]] if results.get("verdicts") else ""
        if verdict:
            lines.append(f"   {verdict}")
    (out / "jury.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    if pick is None:
        print(f"no entry reached the postable threshold; jury written to {out / 'jury.md'}")
        return 0
    entry = entries[pick]
    (out / "post.txt").write_text((entry.get("post") or "") + "\n", encoding="utf-8")
    (out / "alt.txt").write_text((entry.get("alt_text") or "") + "\n", encoding="utf-8")
    media = (replay.get("media") or {}).get(str(pick))
    if media:
        (out / "winner.mp4").write_bytes(base64.b64decode(media))
        print(f"wrote {out / 'winner.mp4'}")
    else:
        print("replay carries no media for the pick; fetch the seat artifact (policy_artifact_<slot>.zip) for the file")
    print(f"pick: slot {pick} — {entry['title']} by {entry['name']} ({entry.get('score', 0):.1f})")
    print(f"post text in {out / 'post.txt'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
