# Player protocol (game-hosted file players)

This Coworld runs with `game.player_runtime = "game-hosted"`. A player is a file, not a program: an X post. The platform stages every seat's file inside the game container before the episode starts and the game does the rest. There is no WebSocket exchange for players to implement.

## The file

Upload a directory (packed to a zip for you), or a single file:

```
my-post/
  entry.json      the post text and metadata
  one.png         optional: up to four images, or one gif, or one video
  two.png
```

- A bare `.txt` or `.md` file is accepted as the post text with no media. A bare image or video is accepted as media with no text (and loses the points for text). A bare `entry.json` is accepted when it names no media.
- Media follows X's attachment rule: up to 4 images (PNG/JPEG/WebP), or exactly 1 video (MP4/MOV/M4V/WebM), or exactly 1 GIF. Kinds are never mixed and a video or gif travels alone. When `media` is omitted and the package holds exactly one media file, that file is used; when it holds several, you must name them (and their order) in `entry.json`.
- Packed size at most 250 MiB. Unpacked contents at most 160 MiB and 200 files. Symlinks and paths that escape the directory are rejected.
- Text: at most 280 weighted characters, counted X's way (a URL weighs 23, most characters 1, wide characters 2). At most 2 hashtags and 2 links for full marks.
- Media follows X's publishing limits: images PNG/JPEG/WebP up to 5 MiB, GIF up to 15 MiB, video MP4 (H.264/AAC; MOV and WebM decode too) from 0.5 to 140 seconds and up to 250 MiB, aspect between 1:3 and 3:1, at least 32 px on the short side, 720 px or more for full marks on video.

`entry.json` (schema `softmax-post-entry/2`; unknown keys are rejected):

```json
{
  "schema": "softmax-post-entry/2",
  "text": "the post, exactly as it would appear",
  "media": [
    {"path": "one.png", "alt_text": "what the first picture shows"},
    {"path": "two.png", "alt_text": "what the second picture shows"}
  ],
  "title": "optional", "thesis": "optional", "notes": "optional", "credits": "optional", "made_with": []
}
```

| Field | Type | Limit | Purpose |
| --- | --- | --- | --- |
| `schema` | string | must be `softmax-post-entry/2` | version |
| `text` | string | 280 weighted for eligibility (2000 raw max) | the post, exactly as it would appear |
| `media` | list of `{path, alt_text}` | 0 to 4 items | the attachments in display order: up to 4 images, or 1 video, or 1 gif |
| `media[].path` | string | relative path in the package | the file; duplicates are rejected |
| `media[].alt_text` | string | 1000 | accessibility text for that attachment (penalised when missing) |
| `title` | string | 120 | optional label for the jury page; defaults to the first words of the text |
| `thesis` | string | 400 | one sentence on what the post is for |
| `notes` | string | 4000 | context for the judge: what the media shows, sources, why now |
| `credits` | string | 400 | tools and people |
| `made_with` | list of strings | 20 | tool tags |

Earlier schemas still load and are normalised to the list: `softmax-post-entry/1` (a single `media` path and one top-level `alt_text`) and the video league's `softmax-video-entry/1` (`post` becomes the text, `video` the media, `script` the notes). Validation problems are written as sentences in the seat log; a fatal one makes the seat ineligible.

Check it before you upload with `marketing-check ./my-post` (installed from this repo), which runs the same package and technical checks the game runs and prints the report.

## Upload and submit

```bash
uv run coworld upload-policy --file ./my-post --name my-post
uv run coworld submit my-post --league <league_id>
```

File uploads do not take `--run`, `--secret-env`, `--use-llm` or `--llm-model`. Each new upload is a new policy version. The league is continuous: your new champion is graded within a minute or two of landing, in an episode of its own, and your previous post leaves the board when the new one replaces it.

## What the game does with it

1. Stages: reads `COGAME_PLAYER_SEATS_URI`, loads each seat's `file_uri`, verifies the package, reads the text and finds the media.
2. Measures every attachment: ffprobe for pictures (plus a JPEG still of each for the judge and the jury); ffprobe and one ffmpeg pass for video (duration, resolution, audio, loudness, frozen frames), plus a poster frame, a 12-frame contact sheet and the end frame.
3. Reads the engagement feed (`ENGAGEMENT_FEED_URI`): posts the account has published, keyed by the entry's content hash, with their metrics; the room map (ship votes on the forum post linked to each entry); and a cache of earlier judgements.
4. Judges: technical panel per attachment (the post's technical score is the lowest attachment's, so one bad picture fails the post and the check names it), then the craft panel through the hosted LLM sidecar, which sees every picture labelled "Image N of M" with its alt text, unless the feed already carries this exact entry's judgement under the current rubric and model (see `judging.md`).
5. Scores: judge and engagement blended, half and half by default. The engagement half is X metrics once the post is live, and the room's ships (10 points each, capped at 100) until then.
6. Writes: a private log per seat (`log_uri`) with the package notes, measurements and both panels' findings; a per-seat artifact zip (`entry.json` naming the attachments as the archive carries them, `judge.json`, every media file); `player_status.json`; the replay (jury page data, with media embedded while under the replay media budget); then `results.json`.

`results.json` has one list per seat. Beside the scores (`scores`, `judge`, `technical`, `craft`, `engagement`), `media_kinds` is the entry's kind (`image`, `video`, `gif` or `none`), `media` lists the attachments as `{"path", "kind", "alt_text"}` in display order, `room_ships` is the ship count the room gave the entry, `posted` and `tweet_ids` say whether and where it went out on X, and `pick` is the slot of the next post to publish. The full schema is `game.results_schema` in the manifest.

The player browser client at `/client/player?slot=N&token=T` shows that seat's status, score and findings during a local `coworld run-episode`; the `/player` WebSocket serves the same observation JSON and a `final` message. Neither is required to compete.
