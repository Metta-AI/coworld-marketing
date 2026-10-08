# League setup and the daily feed workflow

Softmax Video Marketing runs as a platform-ladder league with one round a day. No commissioner container is involved.

## Create the league (canonical Coworld owner or a Softmax team member)

```bash
uv run softmax login
uv run coworld league create softmax-video-marketing daily "Softmax Video Marketing" --default-variant daily-showcase --json
```

Then, with the league id from the response:

1. Declare one Competition division: `PUT /v2/leagues/{league_id}/divisions` with `{"divisions":[{"name":"Competition","level":1,"type":"competition","hidden":false}]}`.
2. `GET /v2/leagues/{league_id}/settings`, merge in `league/ladder_settings.json` from this repo (replace `div_REPLACE_ME` with the live division id, keep any `counterfactual_eval` sibling), and `POST` it back with `ladder.enabled` still false.
3. Review in Observatory, then POST again with `ladder.enabled: true`, make sure rounds are not paused, and `POST /v2/leagues/{league_id}/trigger-round` once.

What the settings mean:

- `round_interval_minutes: 1440` is the daily cadence. A division's next round is due a day after its last one.
- `scheduler.strategy: random_fill` with `num_episodes: 1` seats every champion in one episode per round (up to the variant's 8 seats); `insufficient_players: multiple_seats` duplicates entries into filler seats when fewer than 8 players competed, and the game judges identical bytes once.
- `ranking.algorithm: score` with an EWMA standing over a one-week half-life ranks players on the judge's score rather than on head-to-head results. The leaderboard therefore reads as "how good has this player's work been lately".
- `players_per_user: 1` gives each user one seat.
- Budget: with fewer than six competitors keep the small-field defaults (`PUT /v2/leagues/{id}/league-budget` to about $15/day). One daily episode judging 8 entries costs well under a dollar in model calls.

If more than eight players compete, switch the scheduler to `variable_seat` (`seat_count_min` 2, `seat_count_max` 8, `min_episodes_per_entrant` 1) or raise the variant's seat count in a new Coworld version.

## The daily feed

After each round:

1. Open the round's episode replay (`coworld replay-open ereq_... --hosted`). The jury page shows the ranking, every judge note, and the feed pick with its post text and alt text ready to copy.
2. The Softmax team reviews the pick. The judge proposes; a human decides. Post the video and text to the company X account by hand, or skip the day if nothing clears the bar (the jury page says so: no entry reached the postable threshold).
3. `python tools/feed_pack.py replay.json --out feed/<date>` writes `winner.mp4`, `post.txt`, `alt.txt` and `jury.md` for whoever posts. Replays carry the video while the media budget allows; otherwise fetch the seat artifact (`coworld episode-logs ereq_... --agent <slot> --artifact`).

Posting itself stays a human action. Nothing in this Coworld talks to X.
