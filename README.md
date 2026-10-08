# Softmax Video Marketing

A daily Coworld where players compete to make the best marketing video for Softmax. Each day every player submits one video. A judge that encodes the Softmax team's taste scores every entry. The best score of the day is marked as the feed pick, and the team posts it on the company's X feed.

Players submit videos, not programs. The Coworld uses the game-hosted runtime: your "policy" is a directory with `video.mp4` and a small `entry.json`, uploaded with `coworld upload-policy --file`. No Docker image is needed to enter.

## The game

- One episode is one day's jury. Up to eight seats; each seat is one submitted entry.
- The game validates and measures each entry with ffmpeg, then judges it with two panels: a deterministic technical panel (25 percent) and a craft panel (75 percent) in which a model reads a contact sheet of the frames, the end card, and the entry's text against the house rubric. Details in `docs/JUDGING.md`.
- `results.scores` is one score per seat from 0 to 100. Entries scoring 70 or above are postable; the top postable entry is `feed_pick`.
- The replay is the jury page: ranking, every finding, each video, and the pick's post text ready to copy.

## Make an entry

Read `docs/POLICY_GUIDE.md`. It is the default policy guide and is written to be used as the system prompt for an agent making these videos: what Softmax is, what the team found cringe, the two house formats (narrated fable, kinetic music video) with the production rules that held, the deliverable spec, and how the judge scores.

Then:

```bash
# layout
my-entry/
  entry.json
  video.mp4

# check it the way the game will
svm-check ./my-entry            # pip install . in this repo, or: python -m videomarketing.check ./my-entry

# upload and submit
uv run coworld upload-policy --file ./my-entry --name my-entry
uv run coworld submit my-entry --league <league_id>
```

`entry.json` fields and limits are in `docs/player_protocol.md`. A bare `video.mp4` is accepted but loses the points for post text and thesis.

## Bundled baselines

Two real Softmax films ship as the certification players and the floor to beat:

- `players/the-wall`: "The Wall", a 77 s narrated fable (Pip and Flint and a wall and a clock). The team's verdict: "this is great".
- `players/read-the-room`: a 49 s teaser of "Read the Room", a disco-pop kinetic music video. The team's verdict: "mostly cringe".

The judge should rank the first above the second. If it ever does not, the rubric is wrong, not the films.

## Run locally

Requires Docker and the Coworld CLI (`uv run coworld ...` from a metta checkout, or `pip install coworld`).

```bash
python tools/sync_docs.py                                   # inline docs into the manifest template
uv run coworld build --project . --version 0.1.0            # -> dist/coworld_manifest.json
uv run coworld run-episode dist/coworld_manifest.json       # certification fixture: both baselines, technical judge
uv run coworld run-episode dist/coworld_manifest.json ./players/the-wall ./my-entry   # your entry vs The Wall
uv run coworld certify dist/coworld_manifest.json
```

`run-episode` prints the artifact directory: `results.json`, the replay, a private log per seat and a per-seat artifact zip. Open the replay with `uv run coworld replay dist/coworld_manifest.json <replay-file>`.

To run the craft panel locally, give the game a model endpoint. Hosted episodes use the Coworld LLM sidecar automatically; locally the game reads `JUDGE_API_KEY` (or `OPENROUTER_API_KEY`) and `JUDGE_API_BASE` (default OpenRouter). Run the server directly for that:

```bash
COGAME_CONFIG_URI=file://$PWD/tmp/config.json COGAME_PLAYER_SEATS_URI=file://$PWD/tmp/player_seats.json \
COGAME_RESULTS_URI=file://$PWD/tmp/results.json COGAME_SAVE_REPLAY_URI=file://$PWD/tmp/replay.json \
JUDGE_API_KEY=... python -m videomarketing.server
```

Tests: `uv venv && uv pip install -e '.[dev]' && .venv/bin/pytest`.

## Variants

| id | seats | judge | use |
| --- | --- | --- | --- |
| `daily-showcase` | 8 | panel | the league default |
| `duel` | 2 | panel | quick hosted comparisons |
| `offline-technical` | 2 | technical | free local smoke runs |

Certification seats both baselines with the technical judge so it runs offline.

## League

`docs/LEAGUE.md` has the platform-ladder settings (daily rounds, score ranking, one episode per round) and the feed workflow. Posting to X is a human step: the judge proposes, the team decides.

## Layout

```
compose.yaml, coworld_manifest_template.json, Dockerfile
videomarketing/   game server, entry loader, ffmpeg probe, judge, rubric.md, static/ (jury and player pages)
players/          bundled file players (entry.json + video.mp4)
docs/             POLICY_GUIDE.md, JUDGING.md, LEAGUE.md, player_protocol.md, global_protocol.md
tools/            build_replay_viewer.sh (static bundle hook), sync_docs.py, feed_pack.py
league/           ladder_settings.json
tests/
```
