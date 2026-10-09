# Global viewer protocol

`GET /client/global` serves the jury page: one post at a time as it would appear on X, with its grade underneath, arrows to move between posts and a thumbnail strip. It connects to the `/global` WebSocket and renders the episode live; the same page renders a finished replay (`/client/replay`, `/replay.json`) and is shipped as the static replay viewer bundle.

## `/global` messages (server to viewer)

All messages are JSON objects with a `type`.

- `snapshot`: sent once on connect. `{type, phase, started, done, brief, account, feed, entries: [entry], results}`. Judge notes are included only when `done` is true.
- `phase`: `{type:"phase", phase:"intake"|"judging"|"complete"}`.
- `feed`: `{type:"feed", available, generated_at, posts, error}` once the engagement feed has been read.
- `seat`: `{type:"seat", seat: entry}` whenever a seat's status changes.
- `final`: `{type:"final", results}` when results are written.

An `entry` object: `slot, name, status (waiting|intake|judging|judged|failed), label, text, weighted_length, alt_text, thesis, credits, made_with, kind (zip|media|text|invalid), media_kind (video|image|gif|none), media_mime, duration, width, height, size_bytes, content_hash, poster (base64 JPEG), score, judge, engagement, posted, post ({tweet_id, url, posted_at, fetched_at, metrics} or null), eligible`, and once judged: `notes, technical {score, eligible, checks[]}, craft {score, scores{}, cringe_flags[], notes, verdict, model, attempts, cached} | null, craft_unavailable, problems[], measurement{}, sheet, end (base64 JPEGs)`.

Viewers send nothing. The server answers WebSocket pings with pongs.

## Media

`GET /media/{slot}` serves the seat's media (with its own content type) while the game is running and in replay mode. The replay JSON embeds media as base64 under `media[slot]` while the total stays under `replay_media_budget_bytes`, best scores first, so the static viewer needs no game container.

## Replay

`/replay.json` returns the replay document: `{version: 2, game: "marketing", game_version, config (without tokens), brief, account, feed, entries[], results, events[], media{}}`. The `/replay` WebSocket sends the same document without `media` as `{type:"replay", ...}` on connect and on every message received.
