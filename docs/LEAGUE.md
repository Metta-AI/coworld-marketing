# League setup and the posting loop

Softmax Marketing runs as a **continuous platform ladder**: there is no round interval. Every new champion is graded on arrival in an episode of its own, and published posts are re-graded whenever the marketing agent refreshes their engagement. No commissioner container is involved.

The continuous mode (`settings.ladder.continuous`) ships with the metta platform change in spec 0139 ("Continuous grading leagues"). Until that is deployed, the same settings file works with the interval ladder: set `round_interval_minutes` and have the agent call `trigger-round` instead of `grade`.

## Create the league (canonical Coworld owner or a Softmax team member)

```bash
uv run softmax login
uv run coworld league create marketing main "Softmax Marketing" --default-variant grade --json
```

Then apply the topology and settings with elevated privileges (divisions and ladder settings are team-only):

```bash
cd metta && uv run python ../coworld-marketing/tools/league_setup.py league_... --enable --trigger
```

The script declares one Competition division, merges `league/ladder_settings.json` into the league settings (keeping siblings such as `counterfactual_eval`), sets the small-field budget, enables the ladder, unpauses rounds and asks for every champion to be graded. By hand, with the league id:

1. `PUT /v2/leagues/{league_id}/divisions` with `{"divisions":[{"name":"Competition","level":1,"type":"competition","hidden":false}]}`.
2. `GET /v2/leagues/{league_id}/settings`, merge in `league/ladder_settings.json` (replace `div_REPLACE_ME` with the live division id), and `POST` it back with `ladder.enabled` still false.
3. Review in Observatory, then POST again with `ladder.enabled: true`, make sure rounds are not paused, and `POST /v2/leagues/{league_id}/grade` with `{"policy_version_ids": []}` once.

What the settings mean:

- `ladder.continuous.enabled: true` with `variant_id: "grade"`: each new champion policy version is graded in a one-seat `grade` episode within a ladder tick (about a minute). Bursts are graded in consecutive rounds, up to 32 posts per round.
- `ranking.algorithm: score` with `standing_aggregation: latest`: a player's standing is their current post's latest score. Nothing decays and nothing averages; when the audience moves the post, the next re-grade moves the board.
- `players_per_user: 1`: one seat per user. A new submission replaces the user's previous post on the board.
- No `round_interval_minutes`: inert on a continuous ladder and left unset.
- Budget: with fewer than six competitors keep the small-field defaults (`PUT /v2/leagues/{id}/league-budget` to about $15/day). A grading episode with the model judge costs a few cents; re-grades of published posts are free (the judgement is cached in the feed).

## The engagement feed and the agent

The game cannot reach X from inside a hosted episode. The marketing agent (`marketing-agent`, in `marketing/agent.py`) runs outside the platform and:

1. reads completed rounds and remembers every graded post (content hash, text, judgement, policy version);
2. reads @softmaxresearch's recent posts on X and matches them to graded entries by text;
3. pulls public metrics for the matched posts;
4. reads the room: the league's submissions, the forum post each one links to in its `notes`, and that post's score (see below);
5. writes the engagement feed (`softmax-engagement-feed/1`: posts by content hash with metrics, the `room` map of ships by content hash, plus the judge cache) and stores it as the Coworld secret `engagement_feed`, which hosted episodes receive as `ENGAGEMENT_FEED_URI`;
6. calls `POST /v2/leagues/{id}/grade` for the published posts, and for the entries whose ships moved since the last feed, so their engagement half is re-scored.

```bash
export X_BEARER_TOKEN=...            # or X_CONSUMER_KEY + X_CONSUMER_SECRET
uv run marketing-agent run --league league_... --coworld marketing --every 3600
```

It keeps its state in `~/.config/softmax-marketing/agent-state.json`. `marketing-agent once ...` runs one step; `show` prints the state. Run it from a team machine or a scheduled job; it needs a Softmax user credential (the Coworld owner, or a team member with `--elevated`) and the X app's bearer token. It reads X and never posts.

## Room votes: the notes convention

Before a post is live on X, its engagement half comes from the room: the forum post on the platform where the entry was pitched and people shipped or sank it. The link between an entry and its forum post is the league submission's `notes` field, which holds a JSON object:

```json
{"post_id": "post_01HZX..."}
```

`notes` is the submission's own note field (`LeagueSubmissionPublic.notes`), set on the submission after it is created; the `coworld submit` command and the public create request do not take a note today, so the link is made in Observatory or by the team. The agent reads `GET /v2/league-submissions?league_id=...` (following the `X-Next-Cursor` header), parses each submission's `notes`, fetches `GET /v2/posts/{post_id}` and takes `max(score, 0)` (the post's net vote score) as the ships. It maps the submission's `policy_version.id` to the content hash it saw graded in that policy version's episode; a policy version that has not been graded yet is skipped (its first grade is at 0 ships regardless, and the next cycle picks it up). Notes that are not JSON, or carry no `post_id`, mean no room score. Nothing else in `notes` is read.

The feed's `room` map is `{"sha256:<content hash>": {"ships": 3, "updated_at": "..."}}`. The game scores it as `min(100, engagement.room_points_per_ship * ships)`, 10 points per ship by default, and the agent remembers the last ships it published per policy version so a change earns a re-grade. Once the post goes out on X, its metrics replace the room.

## Posting

Publishing stays a human act. The jury page and the leaderboard show the next pick with its text and alt text ready to copy; a team member posts it from the company account. The agent notices it on the next run, matches it by text, and from then on the audience's half of the score moves with the post.
