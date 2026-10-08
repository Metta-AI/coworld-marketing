# Player protocol (game-hosted file players)

This Coworld runs with `game.player_runtime = "game-hosted"`. A player is a file, not a program. The platform stages every seat's file inside the game container before the episode starts and the game does the rest. There is no WebSocket exchange for players to implement.

## The file

Upload a directory (packed to a zip for you) or a bare video:

```
my-entry/
  entry.json      optional but strongly recommended
  video.mp4       the entry (name it in entry.json; any name works)
```

- Packed size at most 100 MiB. Unpacked contents at most 160 MiB and 200 files. Symlinks and paths that escape the directory are rejected.
- Video: H.264/AAC MP4 preferred (MOV, M4V and WebM decode too). 16:9. At least 720 px tall, 1080 preferred. 20 to 140 seconds, target 45 to 120. Integrated loudness -20 to -12 LUFS.
- A bare `.mp4`, `.mov` or `.webm` is accepted as the whole entry with default metadata.

`entry.json` (schema `softmax-video-entry/1`; unknown keys are rejected):

| Field | Type | Limit | Purpose |
| --- | --- | --- | --- |
| `schema` | string | must be `softmax-video-entry/1` | version |
| `title` | string | 1 to 200 chars (70 for full marks) | shown on the jury page |
| `format` | `narrated-fable`, `kinetic-music-video`, `other` | | tells the judge which house format you chose |
| `video` | string | relative path in the package | which file is the entry |
| `post` | string | 280 for full marks (1000 max) | the X post text used when the entry is the feed pick |
| `alt_text` | string | 1000 | accessibility text for the post |
| `thesis` | string | 400 | the one sentence on the end card |
| `script` | string | 6000 | narration or lyrics, shown to the judge |
| `credits` | string | 400 | tools and people |
| `made_with` | list of strings | 20 | tool tags |

Validate locally before uploading with `svm-check ./my-entry` (installed from this repo) or, with Docker, run the certification episode described in the README.

## Upload and submit

```bash
uv run coworld upload-policy --file ./my-entry --name my-entry
uv run coworld submit my-entry --league <league_id>
```

File uploads do not take `--run`, `--secret-env`, `--use-llm` or `--llm-model`. Each new upload is a new policy version; the ladder seats one champion version per player per round.

## What the game does with it

1. Stages: reads `COGAME_PLAYER_SEATS_URI`, loads each seat's `file_uri`, verifies the package and finds the video.
2. Measures: ffprobe and one ffmpeg pass (duration, resolution, audio, loudness, frozen frames), a poster frame, a 12-frame contact sheet and the end frame.
3. Judges: technical panel, then the craft panel through the hosted LLM sidecar (see `judging.md`).
4. Writes: a private log per seat (`log_uri`) with the package notes, measurements and both panels' findings; a per-seat artifact zip (`entry.json`, `judge.json`, `video.mp4`); `player_status.json`; the replay (jury page data, with the videos embedded while under the replay media budget); then `results.json`.

The player browser client at `/client/player?slot=N&token=T` shows that seat's status, score and findings during a local `coworld run-episode` or a hosted replay; the `/player` WebSocket serves the same observation JSON and a `final` message. Neither is required to compete.
