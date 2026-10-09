"""Real X engagement enters the score through a feed written outside the game by the marketing agent.

Feed schema `softmax-engagement-feed/1`:

{
  "schema": "softmax-engagement-feed/1",
  "account": "softmaxresearch",
  "generated_at": "2026-10-09T01:00:00Z",
  "posts": {
    "sha256:...": {                      # content hash of the player file that became this post
      "tweet_id": "2106986439141646560",
      "url": "https://x.com/softmaxresearch/status/2106986439141646560",
      "posted_at": "2026-10-08T17:20:00Z",
      "fetched_at": "2026-10-09T01:00:00Z",
      "metrics": {"impressions": 1200, "likes": 31, "reposts": 4, "replies": 2, "quotes": 1, "bookmarks": 5}
    }
  },
  "judge_cache": {
    "sha256:...": {"rubric": "post/1", "model": "anthropic/claude-sonnet-4.6", "technical": {...}, "craft": {...}}
  }
}
"""

from __future__ import annotations

import json
import logging
import math
import os
from dataclasses import dataclass, field
from typing import Any

from marketing.config import EngagementConfig
from marketing.io import read_data

logger = logging.getLogger("marketing.engagement")

FEED_SCHEMA = "softmax-engagement-feed/1"
METRICS = ("impressions", "likes", "reposts", "replies")
FEED_ENV = "ENGAGEMENT_FEED_URI"


@dataclass
class PostRecord:
    tweet_id: str
    url: str
    posted_at: str
    fetched_at: str
    metrics: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "tweet_id": self.tweet_id,
            "url": self.url,
            "posted_at": self.posted_at,
            "fetched_at": self.fetched_at,
            "metrics": dict(self.metrics),
        }


@dataclass
class Feed:
    available: bool
    source: str = ""
    generated_at: str = ""
    account: str = ""
    posts: dict[str, PostRecord] = field(default_factory=dict)
    judge_cache: dict[str, dict[str, Any]] = field(default_factory=dict)
    error: str = ""

    def post_for(self, content_hash: str) -> PostRecord | None:
        return self.posts.get(content_hash)


def _int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def parse_feed(raw: bytes | str, *, source: str) -> Feed:
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        return Feed(available=False, source=source, error=f"feed is not valid JSON ({error})")
    if not isinstance(data, dict):
        return Feed(available=False, source=source, error="feed is not an object")
    if data.get("schema") != FEED_SCHEMA:
        return Feed(
            available=False, source=source, error=f"feed schema is {data.get('schema')!r}; expected {FEED_SCHEMA!r}"
        )
    posts: dict[str, PostRecord] = {}
    for key, value in (data.get("posts") or {}).items():
        if not isinstance(value, dict):
            continue
        metrics = value.get("metrics") or {}
        posts[str(key)] = PostRecord(
            tweet_id=str(value.get("tweet_id", "")),
            url=str(value.get("url", "")),
            posted_at=str(value.get("posted_at", "")),
            fetched_at=str(value.get("fetched_at", "")),
            metrics={m: _int(metrics.get(m)) for m in METRICS}
            | {m: _int(metrics.get(m)) for m in ("quotes", "bookmarks") if m in metrics},
        )
    cache = {str(k): v for k, v in (data.get("judge_cache") or {}).items() if isinstance(v, dict)}
    return Feed(
        available=True,
        source=source,
        generated_at=str(data.get("generated_at", "")),
        account=str(data.get("account", "")),
        posts=posts,
        judge_cache=cache,
    )


def load_feed(cfg: EngagementConfig) -> Feed:
    uri = cfg.feed_uri or os.environ.get(FEED_ENV, "")
    if not uri:
        return Feed(available=False, error="no engagement feed configured")
    if uri.startswith("secret://"):
        return Feed(available=False, source=uri, error="engagement feed is an unresolved secret reference")
    try:
        raw = read_data(uri)
    except Exception as error:  # noqa: BLE001
        logger.warning("engagement feed unreadable at %s: %s", uri, error)
        return Feed(available=False, source=uri, error=f"feed unreadable ({type(error).__name__}: {error})")
    feed = parse_feed(raw, source=uri)
    if not feed.available:
        logger.warning("engagement feed rejected: %s", feed.error)
    return feed


def metric_fraction(value: int, target: int) -> float:
    """Logarithmic progress toward the target: half the target earns about 0.9, a tenth about 0.65, zero earns 0."""
    if value <= 0 or target <= 0:
        return 0.0
    return min(1.0, math.log1p(value) / math.log1p(target))


def engagement_score(metrics: dict[str, int] | None, cfg: EngagementConfig) -> float:
    """0 to 100 from the post's metrics; 0 when the entry has not been posted."""
    if not metrics:
        return 0.0
    weights = cfg.metric_weights.model_dump()
    targets = cfg.targets.model_dump()
    total_weight = sum(weights.values()) or 1.0
    score = sum(weights[m] * metric_fraction(metrics.get(m, 0), targets[m]) for m in METRICS) / total_weight
    return round(100.0 * score, 2)


def blend(judge: float, engagement: float, cfg: EngagementConfig) -> float:
    return round((1.0 - cfg.weight) * judge + cfg.weight * engagement, 2)
