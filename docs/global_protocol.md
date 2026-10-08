# Global viewer protocol

`GET /client/global` serves the jury page. It connects to the `/global` WebSocket and renders the episode live; the same page renders a finished replay (`/client/replay`, `/replay.json`) and is shipped as the static replay viewer bundle.

## `/global` messages (server to viewer)

All messages are JSON objects with a `type`.

- `snapshot`: sent once on connect. `{type, phase, started, done, brief, entries: [entry], results}`. Judge notes are included only when `done` is true.
- `phase`: `{type:"phase", phase:"intake"|"judging"|"complete"}`.
- `seat`: `{type:"seat", seat: entry}` whenever a seat's status changes.
- `final`: `{type:"final", results}` when results are written.

An `entry` object: `slot, name, status (waiting|intake|judging|judged|failed), title, format, post, alt_text, thesis, credits, made_with, kind (zip|video|invalid), duration, width, height, size_bytes, content_hash, poster (base64 JPEG), score, eligible`, and once judged: `technical {score, eligible, checks[]}`, `craft {score, scores{}, cringe_flags[], notes, verdict, model, attempts} | null`, `craft_unavailable, problems[], measurement{}, sheet (base64 JPEG contact sheet)`.

Viewers send nothing. The server answers WebSocket pings with pongs.

## Media

`GET /media/{slot}.mp4` serves the seat's video while the game is running and in replay mode. The replay JSON embeds videos as base64 under `media[slot]` while the total stays under `replay_media_budget_bytes`, ranked by score, so the static viewer needs no game container.

## Replay

`/replay.json` returns the replay document: `{version, game:"softmax-video-marketing", game_version, config (without tokens), brief, entries[], results, events[], media{}}`. The `/replay` WebSocket sends the same document without `media` as `{type:"replay", ...}` on connect and on every message received.
