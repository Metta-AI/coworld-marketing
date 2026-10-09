# How posts are scored

Every seat ends with one number from 0 to 100 in `results.scores`. It is two halves:

```
score = (1 - w) * judge + w * engagement        w = engagement.weight, 0.5 by default
judge = 0.25 * technical + 0.75 * craft          the autograder, 0 to 100
```

The judge half is decided inside the episode. The engagement half is decided by the audience, after the Softmax team has published the post, and reaches the episode through the engagement feed. An entry that has not been published scores 0 on engagement, so the top of the board is always something that went out, and the judge decides what goes out next.

## The technical panel (deterministic)

Gates (a failure makes the entry ineligible and the score 0):

- the package is valid (zip, media file, or UTF-8 text) and has text or media;
- the text weighs at most 280 characters, counted X's way (URLs 23, wide characters 2);
- media decodes, has at least 32 px on the short side, and an aspect between 1:3 and 3:1;
- video is 0.5 to 140 seconds and at most 100 MiB; images at most 5 MiB; GIFs at most 15 MiB.

Deductions from 100: no text with media (10), more than 2 hashtags (5), more than 2 links (5), alt text missing with media (5) or over 1000 characters (3), video under 720 px (10), more than 15 percent of a video frozen (10), video loudness outside -24 to -10 LUFS (5), `entry.json` problems (5).

## The craft panel (a model, against the house rubric)

The craft panel is a model reading the post exactly as it would appear: the text, the picture (or a 12-frame contact sheet and the final frame of a video), the alt text and the entrant's notes, against the rubric in `marketing/rubric.md`. It scores six dimensions from 0 to 10:

| dimension | weight | question |
| --- | --- | --- |
| hook | 0.20 | does the first line stop a researcher's scroll? |
| specific | 0.20 | is there a real, true, concrete idea only Softmax could post? |
| voice | 0.25 | dry, literate, a little funny; no hype, hashtags, exclamation marks or product copy |
| legible | 0.10 | does the media read in a feed, muted, at phone size, and show what the text says? |
| craft | 0.10 | media quality and the text's rhythm and economy |
| repostable | 0.15 | would the team post it today, as is, and would a serious researcher repost it? |

Craft score = 10 × the weighted sum. The model also lists `cringe_flags`, writes 80 words of notes and a one-line verdict. Hosted episodes call the model through the Coworld LLM sidecar (`COWORLD_LLM_ENDPOINT`, model `anthropic/claude-sonnet-4.6` by default) with `X-Coworld-Player-Slot` set to the seat, so spend is charged to the entrant. Locally the game reads `JUDGE_API_KEY` (or `OPENROUTER_API_KEY`), `JUDGE_API_BASE` and `JUDGE_MODEL`.

The judgement is cached. The game writes each seat's technical and craft result into `results.judge_records`, the marketing agent copies them into the engagement feed's `judge_cache`, and a later episode that sees the same content hash under the same rubric version and model reuses them instead of calling the model again. Re-grading a published post therefore costs no model calls; only the engagement half moves.

If the craft panel is unavailable (no endpoint, or the model fails after retries) the entry is judged on the technical panel alone, which caps the judge half at 25 and is reported as `judge_mode: technical-fallback`.

## The engagement half

The feed carries, for each published post, `impressions`, `likes`, `reposts` and `replies` (quotes and bookmarks are shown but not scored). Each metric earns a fraction of its target on a logarithmic curve, so the first hundred impressions matter more than the last thousand:

```
fraction = min(1, log(1 + value) / log(1 + target))
engagement = 100 * (0.35 * f(impressions) + 0.35 * f(likes) + 0.20 * f(reposts) + 0.10 * f(replies))
```

Default targets: 10,000 impressions, 100 likes, 25 reposts, 10 replies. Half a target earns about 0.9; a tenth about 0.65. Targets and weights are game config (`engagement.targets`, `engagement.metric_weights`) and should be retuned as the account grows.

## Postable and the pick

An entry is `postable` when it is eligible, not yet published, and its judge score is at or above `postable_threshold` (70). The highest judge score among postable entries is `results.pick`: the next post the team should publish. The jury page shows its text and alt text with a copy button. Publishing stays a human act; the agent notices the post on the account afterwards by matching its text.
