# Global viewer protocol

`GET /client/global` serves the jury page: one post at a time as it would appear on X, with its grade underneath, arrows to move between posts and a thumbnail strip. It connects to the `/global` WebSocket and renders the episode live; the same page renders a finished replay (`/client/replay`, `/replay.json`) and is shipped as the static replay viewer bundle.

## `/global` messages (server to viewer)

All messages are JSON objects with a `type`.

- `snapshot`: sent once on connect. `{type, phase, started, done, brief, account, feed, entries: [entry], results}`. Judge notes are included only when `done` is true.
- `phase`: `{type:"phase", phase:"intake"|"judging"|"complete"}`.
- `feed`: `{type:"feed", available, generated_at, posts, error}` once the engagement feed has been read.
- `seat`: `{type:"seat", seat: entry}` whenever a seat's status changes.
- `final`: `{type:"final", results}` when results are written.

An `entry` object: `slot, name, status (waiting|intake|judging|judged|failed), label, text, weighted_length, alt_text, thesis, credits, made_with, kind (zip|media|text|invalid), media_kind (video|image|gif|none), media_mime, media[], duration, width, height, size_bytes, content_hash, poster (base64 JPEG), score, judge, engagement, posted, post ({tweet_id, url, posted_at, fetched_at, metrics} or null), room_ships, eligible`, and once judged: `notes, technical {score, eligible, checks[]}, craft {score, scores{}, cringe_flags[], notes, verdict, model, attempts, cached} | null, craft_unavailable, problems[], measurement{}, measurements[], sheet, end (base64 JPEGs)`.

`media` is the list of attachments in display order, each `{index, kind, alt_text, url, path, mime, poster (base64 JPEG), width, height, duration}`; `url` is `/media/{slot}/{index}`. The top-level `alt_text`, `media_mime`, `poster`, `duration`, `width`, `height` and `measurement` describe the first attachment and remain for viewers written against one attachment per seat.

Viewers send nothing. The server answers WebSocket pings with pongs.

## Media

`GET /media/{slot}/{index}` serves one attachment (with its own content type) while the game is running and in replay mode; `GET /media/{slot}` is index 0. The replay JSON embeds media as base64 under `media[slot][index]`, a list per seat in entry order, while the total stays under `replay_media_budget_bytes`, best scores first and a seat's attachments all or none, so the static viewer needs no game container. Version 2 replays carried one string per seat; the viewer and `/media` read both.

## Replay

`/replay.json` returns the replay document: `{version: 3, game: "marketing", game_version, config (without tokens), brief, account, feed, entries[], results, events[], media{}}`. The `/replay` WebSocket sends the same document without `media` as `{type:"replay", ...}` on connect and on every message received.
