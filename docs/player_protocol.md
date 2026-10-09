# Player protocol (game-hosted file players)

This Coworld runs with `game.player_runtime = "game-hosted"`. A player is a file, not a program: an X post. The platform stages every seat's file inside the game container before the episode starts and the game does the rest. There is no WebSocket exchange for players to implement.

## The file

Upload a directory (packed to a zip for you), or a single file:

```
my-post/
  entry.json      the post text and metadata
  picture.png     optional: one image, gif or video
```

- A bare `.txt` or `.md` file is accepted as the post text with no media. A bare image or video is accepted as media with no text (and loses the points for text). A bare `entry.json` is accepted when it names no media.
- Packed size at most 100 MiB. Unpacked contents at most 160 MiB and 200 files. Symlinks and paths that escape the directory are rejected.
- Text: at most 280 weighted characters, counted X's way (a URL weighs 23, most characters 1, wide characters 2). At most 2 hashtags and 2 links for full marks.
- Media follows X's publishing limits: images PNG/JPEG/WebP up to 5 MiB, GIF up to 15 MiB, video MP4 (H.264/AAC; MOV and WebM decode too) from 0.5 to 140 seconds and up to 100 MiB, aspect between 1:3 and 3:1, at least 32 px on the short side, 720 px or more for full marks on video.

`entry.json` (schema `softmax-post-entry/1`; unknown keys are rejected):

| Field | Type | Limit | Purpose |
| --- | --- | --- | --- |
| `schema` | string | must be `softmax-post-entry/1` | version |
| `text` | string | 280 weighted for eligibility (2000 raw max) | the post, exactly as it would appear |
| `media` | string or null | relative path in the package | the attached picture or video, if any |
| `alt_text` | string | 1000 | accessibility text for the media (penalised when missing) |
| `title` | string | 120 | optional label for the jury page; defaults to the first words of the text |
| `thesis` | string | 400 | one sentence on what the post is for |
| `notes` | string | 4000 | context for the judge: what the media shows, sources, why now |
| `credits` | string | 400 | tools and people |
| `made_with` | list of strings | 20 | tool tags |

Packages written for the earlier video league (`softmax-video-entry/1`) still load: `post` becomes the text, `video` the media, `script` the notes.

Check it before you upload with `marketing-check ./my-post` (installed from this repo), which runs the same package and technical checks the game runs and prints the report.

## Upload and submit

```bash
uv run coworld upload-policy --file ./my-post --name my-post
uv run coworld submit my-post --league <league_id>
```

File uploads do not take `--run`, `--secret-env`, `--use-llm` or `--llm-model`. Each new upload is a new policy version. The league is continuous: your new champion is graded within a minute or two of landing, in an episode of its own, and your previous post leaves the board when the new one replaces it.

## What the game does with it

1. Stages: reads `COGAME_PLAYER_SEATS_URI`, loads each seat's `file_uri`, verifies the package, reads the text and finds the media.
2. Measures: ffprobe for pictures; ffprobe and one ffmpeg pass for video (duration, resolution, audio, loudness, frozen frames), plus a poster frame, a 12-frame contact sheet and the end frame.
3. Reads the engagement feed (`ENGAGEMENT_FEED_URI`): posts the account has published, keyed by the entry's content hash, with their metrics, and a cache of earlier judgements.
4. Judges: technical panel, then the craft panel through the hosted LLM sidecar, unless the feed already carries this exact entry's judgement under the current rubric and model (see `judging.md`).
5. Scores: judge and engagement blended, half and half by default.
6. Writes: a private log per seat (`log_uri`) with the package notes, measurements and both panels' findings; a per-seat artifact zip (`entry.json`, `judge.json`, the media file); `player_status.json`; the replay (jury page data, with media embedded while under the replay media budget); then `results.json`.

The player browser client at `/client/player?slot=N&token=T` shows that seat's status, score and findings during a local `coworld run-episode`; the `/player` WebSocket serves the same observation JSON and a `final` message. Neither is required to compete.
