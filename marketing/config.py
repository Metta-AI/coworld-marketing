from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MIB = 1024 * 1024

JudgeMode = Literal["panel", "technical"]
MediaKind = Literal["video", "image", "gif", "none"]


class PlayerName(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)


class JudgeConfig(BaseModel):
    """The autograder: a deterministic technical panel plus a model craft panel, blended into one judge score."""

    model_config = ConfigDict(extra="forbid")

    mode: JudgeMode = "panel"
    model: str = Field(default="anthropic/claude-sonnet-4.6", min_length=1)
    frames: int = Field(default=12, ge=4, le=24, description="Frames in the contact sheet shown to the craft panel.")
    max_tokens: int = Field(default=900, ge=200, le=4000)
    timeout_seconds: float = Field(default=90, gt=0, le=300)
    retries: int = Field(default=2, ge=0, le=5)
    technical_weight: float = Field(default=0.25, ge=0, le=1)
    craft_weight: float = Field(default=0.75, ge=0, le=1)
    postable_threshold: float = Field(
        default=70, ge=0, le=100, description="Judge score at or above which an entry is worth posting."
    )
    use_cache: bool = Field(default=True, description="Reuse judge results from the engagement feed's judge_cache.")


class EngagementTargets(BaseModel):
    """Metric values that earn full marks on their dimension; the curve is logarithmic below them."""

    model_config = ConfigDict(extra="forbid")

    impressions: int = Field(default=10_000, ge=1)
    likes: int = Field(default=100, ge=1)
    reposts: int = Field(default=25, ge=1)
    replies: int = Field(default=10, ge=1)


class EngagementWeights(BaseModel):
    model_config = ConfigDict(extra="forbid")

    impressions: float = Field(default=0.35, ge=0, le=1)
    likes: float = Field(default=0.35, ge=0, le=1)
    reposts: float = Field(default=0.20, ge=0, le=1)
    replies: float = Field(default=0.10, ge=0, le=1)


class EngagementConfig(BaseModel):
    """How real X engagement enters the score. The feed is written outside the game by the marketing agent."""

    model_config = ConfigDict(extra="forbid")

    weight: float = Field(default=0.5, ge=0, le=1, description="Share of the final score that comes from engagement.")
    targets: EngagementTargets = Field(default_factory=EngagementTargets)
    metric_weights: EngagementWeights = Field(default_factory=EngagementWeights)
    feed_uri: str | None = Field(
        default=None,
        description="Where to read the engagement feed. Null means the ENGAGEMENT_FEED_URI environment variable.",
    )


class Limits(BaseModel):
    """X's own publishing limits, plus the house ceilings."""

    model_config = ConfigDict(extra="forbid")

    max_file_bytes: int = Field(default=100 * MIB, ge=MIB, description="Uploaded player file ceiling.")
    text_max_weighted_chars: int = Field(default=280, ge=1)
    alt_text_max_chars: int = Field(default=1000, ge=1)
    max_hashtags: int = Field(default=2, ge=0)
    max_links: int = Field(default=2, ge=0)
    video_min_seconds: float = Field(default=0.5, gt=0)
    video_max_seconds: float = Field(default=140, gt=0)
    video_min_height: int = Field(default=720, ge=32)
    video_max_frozen_fraction: float = Field(default=0.15, ge=0, le=1)
    video_max_bytes: int = Field(default=100 * MIB, ge=MIB)
    image_max_bytes: int = Field(default=5 * MIB, ge=1)
    gif_max_bytes: int = Field(default=15 * MIB, ge=1)
    min_dimension: int = Field(default=32, ge=1)
    aspect_min: float = Field(default=1 / 3, gt=0)
    aspect_max: float = Field(default=3.0, gt=0)
    loudness_lufs_min: float = Field(default=-24)
    loudness_lufs_max: float = Field(default=-10)


class GameConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tokens: list[str] = Field(min_length=1, max_length=32)
    players: list[PlayerName] = Field(min_length=1, max_length=32)
    seed: int | None = None
    brief: str = Field(min_length=1, max_length=2000)
    account: str = Field(
        default="softmaxresearch", min_length=1, max_length=40, description="The X handle posts go out on."
    )
    judge: JudgeConfig = Field(default_factory=JudgeConfig)
    engagement: EngagementConfig = Field(default_factory=EngagementConfig)
    limits: Limits = Field(default_factory=Limits)
    linger_seconds: float = Field(default=15, ge=0, le=600)
    replay_media_budget_bytes: int = Field(default=48 * MIB, ge=0)
