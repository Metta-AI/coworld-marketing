"""The marketing agent: the long-running process that connects the league to X.

The game container cannot reach X (hosted episodes have no public egress), so this agent does the outside work and
hands the result to episodes through the Coworld secret the game reads as ENGAGEMENT_FEED_URI:

1. Reads completed rounds of the league and remembers every graded entry (content hash, post text, judge record).
2. Reads the company account's recent posts on X and matches them to graded entries by exact text, so a human who
   copies the pick's text and posts it needs to tell nobody.
3. Pulls public metrics for every matched post (impressions, likes, reposts, replies, quotes, bookmarks).
4. Writes the engagement feed (posts + judge cache) and stores it as the Coworld secret `engagement_feed`.
5. Asks the continuous ladder to re-grade the posted entries (POST /v2/leagues/{id}/grade), so the engagement half
   of their score moves with the audience.

Run it on a loop:

    marketing-agent run --league league_... --coworld marketing --every 3600

or one step at a time (`sync`, `feed`, `publish`, `regrade`). Credentials come from the environment: a Softmax user
token (the Coworld owner or a team member; `softmax login` stores one the CLI's auth module can load) and an X app
bearer token (`X_BEARER_TOKEN`, or `X_CONSUMER_KEY` + `X_CONSUMER_SECRET` to mint one). Posting itself stays a human
action: this agent reads X, it never writes to it.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from marketing.engagement import FEED_SCHEMA

logger = logging.getLogger("marketing.agent")

OBSERVATORY = os.environ.get("SOFTMAX_API", "https://softmax.com/api")
X_API = "https://api.x.com/2"
USER_AGENT = "coworld-marketing-agent/0.2"
STATE_VERSION = 1


# --------------------------------------------------------------------------- state


@dataclass
class GradedEntry:
    content_hash: str
    text: str
    label: str
    player_name: str
    policy_version_id: str
    first_seen_round: str
    judge_record: dict[str, Any] | None = None
    judge: float = 0.0
    tweet_id: str = ""
    posted_at: str = ""
    url: str = ""


@dataclass
class AgentState:
    version: int = STATE_VERSION
    league_id: str = ""
    account: str = ""
    account_user_id: str = ""
    entries: dict[str, GradedEntry] = field(default_factory=dict)  # by content hash
    seen_rounds: list[str] = field(default_factory=list)
    metrics: dict[str, dict[str, Any]] = field(default_factory=dict)  # by tweet id
    last_feed_at: str = ""
    last_regrade_at: str = ""

    @classmethod
    def load(cls, path: Path) -> AgentState:
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = {k: GradedEntry(**v) for k, v in data.get("entries", {}).items()}
        return cls(**{**{k: v for k, v in data.items() if k != "entries"}, "entries": entries})

    def save(self, path: Path) -> None:
        payload = {**asdict(self), "entries": {k: asdict(v) for k, v in self.entries.items()}}
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)


def now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------- clients


class Softmax:
    def __init__(self, token: str, *, elevated: bool = False) -> None:
        headers = {"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT}
        if elevated:
            headers["X-Use-Elevated-Privileges"] = "true"
        self.http = httpx.Client(base_url=OBSERVATORY, headers=headers, timeout=60)

    def get(self, path: str, **params: Any) -> Any:
        response = self.http.get(path, params={k: v for k, v in params.items() if v is not None})
        response.raise_for_status()
        return response.json()

    def post(self, path: str, body: Any) -> Any:
        response = self.http.post(path, json=body)
        response.raise_for_status()
        return response.json() if response.content else None

    def put_secret(self, coworld: str, name: str, payload: bytes) -> Any:
        response = self.http.put(
            f"/observatory/v2/coworlds/secrets/{coworld}/{name}",
            content=payload,
            headers={"Content-Type": "application/octet-stream"},
        )
        response.raise_for_status()
        return response.json()

    def completed_rounds(self, league_id: str, *, limit: int = 200) -> list[dict[str, Any]]:
        rounds: list[dict[str, Any]] = []
        cursor = None
        while True:
            page = self.get("/observatory/v2/rounds", league_id=league_id, status="completed", limit=100, cursor=cursor)
            items = page if isinstance(page, list) else page.get("items", page.get("rounds", []))
            rounds.extend(items)
            cursor = page.get("next_cursor") if isinstance(page, dict) else None
            if not cursor or len(rounds) >= limit:
                break
        return rounds

    def round_episodes(self, round_id: str) -> list[dict[str, Any]]:
        page = self.get(f"/observatory/v2/rounds/{round_id}/episodes")
        return page if isinstance(page, list) else page.get("items", page.get("episodes", []))

    def episode_results(self, episode: dict[str, Any]) -> dict[str, Any] | None:
        results = episode.get("results") or episode.get("game_results")
        if isinstance(results, dict):
            return results
        url = episode.get("results_url") or episode.get("results_uri")
        if url:
            response = httpx.get(url, timeout=60, headers={"User-Agent": USER_AGENT})
            if response.status_code == 200:
                return response.json()
        return None


class X:
    def __init__(self, bearer: str) -> None:
        self.http = httpx.Client(
            base_url=X_API, headers={"Authorization": f"Bearer {bearer}", "User-Agent": USER_AGENT}, timeout=60
        )

    @staticmethod
    def mint_bearer(consumer_key: str, consumer_secret: str) -> str:
        response = httpx.post(
            "https://api.x.com/oauth2/token",
            auth=(consumer_key, consumer_secret),
            data={"grant_type": "client_credentials"},
            timeout=60,
        )
        response.raise_for_status()
        return str(response.json()["access_token"])

    def user_id(self, handle: str) -> str:
        response = self.http.get(f"/users/by/username/{handle}")
        response.raise_for_status()
        return str(response.json()["data"]["id"])

    def recent_posts(self, user_id: str, *, max_results: int = 50) -> list[dict[str, Any]]:
        response = self.http.get(
            f"/users/{user_id}/tweets",
            params={
                "max_results": min(max(5, max_results), 100),
                "tweet.fields": "created_at,public_metrics,text,referenced_tweets",
                "exclude": "retweets,replies",
            },
        )
        response.raise_for_status()
        return list(response.json().get("data", []))

    def metrics(self, tweet_ids: list[str]) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for start in range(0, len(tweet_ids), 100):
            chunk = tweet_ids[start : start + 100]
            response = self.http.get(
                "/tweets", params={"ids": ",".join(chunk), "tweet.fields": "public_metrics,created_at"}
            )
            response.raise_for_status()
            for item in response.json().get("data", []):
                out[str(item["id"])] = {
                    "public_metrics": item.get("public_metrics", {}),
                    "created_at": item.get("created_at", ""),
                }
        return out


# --------------------------------------------------------------------------- steps


def normalise(text: str) -> str:
    """X rewrites links to t.co and trims whitespace; compare on words only, links stripped."""
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"(?<![\w@])(?:[a-z0-9-]+\.)+[a-z]{2,}(?:/\S*)?", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"&amp;", "&", text)
    return " ".join(text.lower().split())


def sync_rounds(state: AgentState, softmax: Softmax, league_id: str) -> int:
    """Remember every graded entry from completed rounds not seen before."""
    added = 0
    for round_row in softmax.completed_rounds(league_id):
        round_id = str(round_row.get("id") or round_row.get("round_id"))
        if round_id in state.seen_rounds:
            continue
        for episode in softmax.round_episodes(round_id):
            results = softmax.episode_results(episode)
            if not results or "content_hashes" not in results:
                continue
            seats = episode.get("policy_versions") or episode.get("seats") or []
            for slot, content_hash in enumerate(results["content_hashes"]):
                if not content_hash:
                    continue
                policy_version_id = ""
                if slot < len(seats):
                    seat = seats[slot]
                    policy_version_id = (
                        str(seat.get("policy_version_id") or seat.get("id") or "")
                        if isinstance(seat, dict)
                        else str(seat)
                    )
                existing = state.entries.get(content_hash)
                record = (results.get("judge_records") or [None] * len(results["content_hashes"]))[slot]
                if existing is None:
                    state.entries[content_hash] = GradedEntry(
                        content_hash=content_hash,
                        text=results["texts"][slot],
                        label=results["labels"][slot],
                        player_name=results["player_names"][slot],
                        policy_version_id=policy_version_id,
                        first_seen_round=round_id,
                        judge_record=record,
                        judge=float(results["judge"][slot]),
                    )
                    added += 1
                else:
                    if record is not None:
                        existing.judge_record = record
                    existing.judge = float(results["judge"][slot])
                    if policy_version_id:
                        existing.policy_version_id = policy_version_id
        state.seen_rounds.append(round_id)
    state.seen_rounds = state.seen_rounds[-2000:]
    return added


def match_posts(state: AgentState, x: X) -> int:
    """Attach tweet ids to graded entries whose text the account has published."""
    if not state.account_user_id:
        state.account_user_id = x.user_id(state.account)
    by_text = {
        normalise(entry.text): entry for entry in state.entries.values() if entry.text.strip() and not entry.tweet_id
    }
    if not by_text:
        return 0
    matched = 0
    for post in x.recent_posts(state.account_user_id):
        key = normalise(post.get("text", ""))
        entry = by_text.get(key)
        if entry is None:
            continue
        entry.tweet_id = str(post["id"])
        entry.posted_at = str(post.get("created_at", ""))
        entry.url = f"https://x.com/{state.account}/status/{entry.tweet_id}"
        state.metrics[entry.tweet_id] = {"public_metrics": post.get("public_metrics", {}), "fetched_at": now_iso()}
        matched += 1
        logger.info("matched %s to post %s", entry.label, entry.tweet_id)
    return matched


def refresh_metrics(state: AgentState, x: X) -> int:
    ids = sorted({entry.tweet_id for entry in state.entries.values() if entry.tweet_id})
    if not ids:
        return 0
    fetched = x.metrics(ids)
    stamp = now_iso()
    for tweet_id, data in fetched.items():
        state.metrics[tweet_id] = {"public_metrics": data["public_metrics"], "fetched_at": stamp}
    return len(fetched)


def build_feed(state: AgentState) -> dict[str, Any]:
    posts: dict[str, Any] = {}
    cache: dict[str, Any] = {}
    for content_hash, entry in state.entries.items():
        if entry.judge_record is not None:
            cache[content_hash] = entry.judge_record
        if not entry.tweet_id:
            continue
        public = (state.metrics.get(entry.tweet_id) or {}).get("public_metrics", {})
        posts[content_hash] = {
            "tweet_id": entry.tweet_id,
            "url": entry.url,
            "posted_at": entry.posted_at,
            "fetched_at": (state.metrics.get(entry.tweet_id) or {}).get("fetched_at", ""),
            "metrics": {
                "impressions": int(public.get("impression_count", 0) or 0),
                "likes": int(public.get("like_count", 0) or 0),
                "reposts": int(public.get("retweet_count", 0) or 0),
                "replies": int(public.get("reply_count", 0) or 0),
                "quotes": int(public.get("quote_count", 0) or 0),
                "bookmarks": int(public.get("bookmark_count", 0) or 0),
            },
        }
    return {
        "schema": FEED_SCHEMA,
        "account": state.account,
        "generated_at": now_iso(),
        "posts": posts,
        "judge_cache": cache,
    }


def publish_feed(state: AgentState, softmax: Softmax, coworld: str, feed: dict[str, Any], *, out: Path | None) -> int:
    payload = json.dumps(feed, separators=(",", ":"), ensure_ascii=False).encode()
    if len(payload) > 1_000_000:
        # The secret store caps at 1 MiB: drop judge-cache entries for unposted, oldest-first, until it fits.
        unposted = [h for h, e in state.entries.items() if not e.tweet_id]
        while len(payload) > 1_000_000 and unposted:
            feed["judge_cache"].pop(unposted.pop(0), None)
            payload = json.dumps(feed, separators=(",", ":"), ensure_ascii=False).encode()
    if out is not None:
        out.write_bytes(payload)
    softmax.put_secret(coworld, "engagement_feed", payload)
    state.last_feed_at = feed["generated_at"]
    return len(payload)


def request_regrade(state: AgentState, softmax: Softmax, league_id: str, *, only_posted: bool = True) -> list[str]:
    ids = sorted(
        {e.policy_version_id for e in state.entries.values() if e.policy_version_id and (e.tweet_id or not only_posted)}
    )
    if not ids:
        return []
    softmax.post(f"/observatory/v2/leagues/{league_id}/grade", {"policy_version_ids": ids})
    state.last_regrade_at = now_iso()
    return ids


# --------------------------------------------------------------------------- cli


def _softmax_token() -> str:
    token = os.environ.get("SOFTMAX_TOKEN")
    if token:
        return token
    try:
        from softmax.auth import load_user_token  # type: ignore[import-not-found]

        return str(load_user_token(server=OBSERVATORY))
    except Exception as error:  # noqa: BLE001
        raise SystemExit(f"no Softmax credential: set SOFTMAX_TOKEN or run `softmax login` ({error})") from error


def _x_bearer() -> str:
    bearer = os.environ.get("X_BEARER_TOKEN")
    if bearer:
        return bearer
    key, secret = os.environ.get("X_CONSUMER_KEY"), os.environ.get("X_CONSUMER_SECRET")
    if key and secret:
        return X.mint_bearer(key, secret)
    raise SystemExit("no X credential: set X_BEARER_TOKEN, or X_CONSUMER_KEY and X_CONSUMER_SECRET")


def step(state: AgentState, softmax: Softmax, x: X, args: argparse.Namespace) -> None:
    added = sync_rounds(state, softmax, args.league)
    matched = match_posts(state, x)
    refreshed = refresh_metrics(state, x)
    feed = build_feed(state)
    size = publish_feed(state, softmax, args.coworld, feed, out=args.feed_out)
    regraded = request_regrade(state, softmax, args.league) if args.regrade else []
    logger.info(
        "sync: %d new entries, %d newly matched posts, %d metrics refreshed, feed %d bytes (%d posts), regrade %d",
        added,
        matched,
        refreshed,
        size,
        len(feed["posts"]),
        len(regraded),
    )


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Softmax Marketing agent: engagement feed and re-grades.")
    parser.add_argument(
        "command", choices=["run", "once", "show"], help="run forever, run one step, or print the state"
    )
    parser.add_argument("--league", required=True, help="league id (league_...)")
    parser.add_argument("--coworld", default="marketing", help="Coworld name that owns the engagement_feed secret")
    parser.add_argument("--account", default="softmaxresearch", help="X handle the posts go out on")
    parser.add_argument(
        "--state",
        type=Path,
        default=Path(
            os.environ.get("MARKETING_AGENT_STATE", "~/.config/softmax-marketing/agent-state.json")
        ).expanduser(),
    )
    parser.add_argument("--feed-out", type=Path, default=None, help="also write the feed JSON here")
    parser.add_argument("--every", type=int, default=3600, help="seconds between steps for `run`")
    parser.add_argument(
        "--no-regrade", dest="regrade", action="store_false", help="refresh the feed without asking for re-grades"
    )
    parser.add_argument("--elevated", action="store_true", help="send X-Use-Elevated-Privileges (team members)")
    args = parser.parse_args(argv)

    state = AgentState.load(args.state)
    state.league_id = args.league
    state.account = args.account
    if args.command == "show":
        print(
            json.dumps(
                {**asdict(state), "entries": {k: asdict(v) for k, v in state.entries.items()}},
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    softmax = Softmax(_softmax_token(), elevated=args.elevated)
    x = X(_x_bearer())
    while True:
        try:
            step(state, softmax, x, args)
        except httpx.HTTPStatusError as error:
            logger.error(
                "HTTP %s from %s: %s", error.response.status_code, error.request.url, error.response.text[:300]
            )
            if args.command == "once":
                state.save(args.state)
                return 1
        finally:
            state.save(args.state)
        if args.command == "once":
            return 0
        time.sleep(max(60, args.every))


if __name__ == "__main__":
    sys.exit(main())
