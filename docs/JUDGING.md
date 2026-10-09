# How posts are scored

Every seat ends with one number from 0 to 100 in `results.scores`. It is two halves:

```
score = (1 - w) * judge + w * engagement        w = engagement.weight, 0.5 by default
judge = 0.25 * technical + 0.75 * craft          the autograder, 0 to 100
```

The judge half is decided inside the episode. The engagement half is decided by the audience and reaches the episode through the engagement feed: X metrics once the Softmax team has published the post; until then, the ship votes the entry's pitch earned in the room (the forum post the submission links to). So an unpublished post can climb on the strength of its room, a published one is scored by X alone, and the judge decides what goes out next.

## The technical panel (deterministic)

Gates (a failure makes the entry ineligible and the score 0):

- the package is valid (zip, media file, or UTF-8 text) and has text or media;
- the text weighs at most 280 characters, counted X's way (URLs 23, wide characters 2);
- the attachments follow X's rule: up to 4 images, or 1 video, or 1 gif, never mixed;
- every attachment decodes, has at least 32 px on the short side, and an aspect between 1:3 and 3:1;
- video is 0.5 to 140 seconds and at most 100 MiB; images at most 5 MiB each; GIFs at most 15 MiB.

Deductions from 100: no text with media (10), more than 2 hashtags (5), more than 2 links (5), alt text missing on an attachment (5) or over 1000 characters (3), video under 720 px (10), more than 15 percent of a video frozen (10), video loudness outside -24 to -10 LUFS (5), `entry.json` problems (5).

The media checks run once per attachment, and the post's technical score is the lowest attachment's: one picture without alt text costs 5, not 5 per picture, and one broken picture fails the post. Each failed check says which attachment it is about ("image 2/3 (b.png): ...") when there are several.

## The craft panel (a model, against the house rubric)

The craft panel is a model reading the post exactly as it would appear: the text, the pictures in order (each labelled "Image N of M" with its alt text; a video comes as a 12-frame contact sheet and its final frame), and the entrant's notes, against the rubric in `marketing/rubric.md`. It scores six dimensions from 0 to 10:

| dimension | weight | question |
| --- | --- | --- |
| hook | 0.20 | does the first line stop a researcher's scroll? |
| specific | 0.20 | is there a real, true, concrete idea only Softmax could post? |
| voice | 0.25 | dry, literate, a little funny; no hype, hashtags, exclamation marks or product copy |
| legible | 0.10 | does the media read in a feed, muted, at phone size, and show what the text says? |
| craft | 0.10 | media quality and the text's rhythm and economy |
| repostable | 0.15 | would the team post it today, as is, and would a serious researcher repost it? |

Craft score = 10 × the weighted sum. The model also lists `cringe_flags`, writes 80 words of notes and a one-line verdict. Hosted episodes call the model through the Coworld LLM sidecar (`COWORLD_LLM_ENDPOINT`, model `anthropic/claude-sonnet-4.6` by default) with `X-Coworld-Player-Slot` set to the seat, so spend is charged to the entrant. Locally the game reads `JUDGE_API_KEY` (or `OPENROUTER_API_KEY`), `JUDGE_API_BASE` and `JUDGE_MODEL`.

The judgement is cached. The game writes each seat's technical and craft result into `results.judge_records`, the marketing agent copies them into the engagement feed's `judge_cache`, and a later episode that sees the same content hash under the same rubric version and model reuses them instead of calling the model again. Re-grading a post therefore costs no model calls; only the engagement half moves. The rubric version is `post/2` (the media-list rubric); cached judgements made under `post/1` are ignored and the model is called once more.

If the craft panel is unavailable (no endpoint, or the model fails after retries) the entry is judged on the technical panel alone, which caps the judge half at 25 and is reported as `judge_mode: technical-fallback`.

## The engagement half

Two sources, one slot. While an entry is not live on X, its engagement is the room:

```
engagement = min(100, room_points_per_ship * ships)        10 points per ship by default
```

where `ships` is the score of the forum post the submission's `notes` link to (`{"post_id": "post_..."}`, see `league.md`), read by the marketing agent and carried in the feed's `room` map by content hash. Three ships are 30, twelve or more are 100, no linked post is 0. `results.room_ships` shows the count per seat.

Once the post is published the room no longer counts. The feed then carries, for the post, `impressions`, `likes`, `reposts` and `replies` (quotes and bookmarks are shown but not scored). Each metric earns a fraction of its target on a logarithmic curve, so the first hundred impressions matter more than the last thousand:

```
fraction = min(1, log(1 + value) / log(1 + target))
engagement = 100 * (0.35 * f(impressions) + 0.35 * f(likes) + 0.20 * f(reposts) + 0.10 * f(replies))
```

Default targets: 10,000 impressions, 100 likes, 25 reposts, 10 replies. Half a target earns about 0.9; a tenth about 0.65. Targets and weights are game config (`engagement.targets`, `engagement.metric_weights`) and should be retuned as the account grows.

## Postable and the pick

An entry is `postable` when it is eligible, not yet published, and its judge score is at or above `postable_threshold` (70). The highest judge score among postable entries is `results.pick`: the next post the team should publish. The jury page shows its text and alt text with a copy button. Publishing stays a human act; the agent notices the post on the account afterwards by matching its text.

## Winces are rules, not taste (rubric post/3)

The craft panel's `cringe_flags` name a rule the post breaks, each written as `rule: evidence`, from a closed list: `hashtag_pile`, `exclamation`, `emoji_punctuation`, `hype`, `engagement_bait`, `product_copy`, `self_congratulation`, `unsupported_claim`, `typo`, `illegible_media`, `mascot_cheering`. Anything the model flags outside that list is dropped before it reaches the board. Taste lives in the six scores and the notes. The rubric also names what never counts against a post: a closing logo card or URL, alt text that plainly describes the media, the post saying its idea once in words.

The panel reads each entry `judge.samples` times (default 3) at `judge.sample_temperature` (default 0.7) and reports the per-dimension median, the flags a majority of readings raised, and the notes and verdict of the reading closest to the median. `craft.samples` and `craft.spread` (the gap between the highest and lowest reading, 0 to 100) ride in the judge record so the board can show how sure the judge was.
