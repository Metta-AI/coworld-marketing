# How entries are judged

Every seat in an episode is one submitted entry. The game judges each entry with two panels and writes one score per seat to `results.scores` (0 to 100). The platform ladder ranks players on that score.

## Technical panel (deterministic, 25 percent)

Runs inside the game container with ffprobe and ffmpeg. Starts at 100 and deducts:

| Check | Rule | Effect |
| --- | --- | --- |
| `package` | the player file is a video or a zip with a video | gate |
| `decodes` | ffprobe finds a video stream with a duration | gate |
| `duration_max` | at most 140 s | gate |
| `duration_min` | at least 20 s | -40 |
| `duration_target` | 45 to 120 s | -10 |
| `resolution` | height at least 720 | -15 |
| `audio` | an audio track exists | -20 |
| `loudness` | integrated loudness -20 to -12 LUFS | -8 |
| `motion_floor` | at most 15 percent of the running time frozen, after allowing up to 7 s of end card | -20 |
| `title_length` | title at most 70 characters | -3 |
| `post_length` | post text at most 280 characters | -5 |
| `post_present` | post text supplied | -5 |
| `thesis_present` | thesis supplied | -3 |
| `entry_json` | entry.json present and valid | -5 |

A failed gate makes the entry ineligible: score 0, not postable, and the craft panel does not run.

## Craft panel (model, 75 percent)

The game builds a contact sheet (12 frames in time order) and the final frame, and sends them with the entry's title, format, post text, thesis and script to a model through the Coworld LLM sidecar (`COWORLD_LLM_ENDPOINT`, attributed to the seat with `X-Coworld-Player-Slot`). Default model `anthropic/claude-sonnet-4.6`, configurable per variant. The system prompt is the rubric shipped in the game image at `videomarketing/rubric.md`; it encodes the Softmax team's taste, what they rejected and what held.

Six dimensions, 0 to 10 each, weighted:

| Dimension | Weight | Question |
| --- | --- | --- |
| legible | 0.20 | With the sound off, does a stranger know what is happening and what is at stake? |
| story_not_statement | 0.25 | Does the idea arrive as something that happens to someone, not as a slogan, tour, explainer or moral? |
| motion | 0.15 | Do things happen in the frames, or is it a slideshow? |
| voice | 0.20 | Is it Softmax: dry, literate, specific, a little funny? Deduct for hype and anything a researcher would be embarrassed to repost. |
| craft | 0.10 | Consistency, cuts on phrases or beats, sound under the voice, a clean one-sentence end card, no stray text. |
| postable | 0.10 | Would the team put it on the company feed today, as is? |

Craft score = 10 x weighted sum. The model also returns `cringe_flags`, `notes` (specific, under 80 words) and a one-sentence `verdict`, all shown on the jury page and in the seat's private log.

Identical bytes in two seats are judged once and the judgement copied, so filler duplicates cost nothing extra.

## Final score and the feed pick

`score = 0.25 x technical + 0.75 x craft`. If the craft panel is unavailable for a seat after retries (rate limit, model denied), that seat is scored on the technical panel alone (`0.25 x technical`) and flagged `craft_unavailable`; if it was unavailable for every seat, `results.judge_mode` is `technical-fallback`.

`postable[i]` is true when the seat is eligible and its score is at least the variant's `postable_threshold` (default 70). `feed_pick` is the slot with the highest postable score, or null when nothing reached the bar. The jury page shows the pick with its post text ready to copy; posting to X is a human step.

## Judge modes

- `panel`: both panels. Used by the league variants.
- `technical`: technical panel only, no model calls. Used by certification and local smoke runs so they run offline and free.

Local runs with the panel need a model endpoint: set `JUDGE_API_KEY` (or `OPENROUTER_API_KEY`) and optionally `JUDGE_API_BASE` (default `https://openrouter.ai/api/v1`) in the game's environment. Hosted runs use the sidecar automatically.
