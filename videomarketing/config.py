from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MIB = 1024 * 1024

JudgeMode = Literal["panel", "technical"]
EntryFormat = Literal["narrated-fable", "kinetic-music-video", "other"]


class PlayerName(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)


class JudgeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: JudgeMode = "panel"
    model: str = Field(default="anthropic/claude-sonnet-4.6", min_length=1)
    frames: int = Field(default=12, ge=4, le=24, description="Frames in the contact sheet shown to the craft panel.")
    max_tokens: int = Field(default=900, ge=200, le=4000)
    timeout_seconds: float = Field(default=90, gt=0, le=300)
    retries: int = Field(default=2, ge=0, le=5)
    technical_weight: float = Field(default=0.25, ge=0, le=1)
    craft_weight: float = Field(default=0.75, ge=0, le=1)
    postable_threshold: float = Field(default=70, ge=0, le=100)


class Limits(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min_duration_seconds: float = Field(default=20, ge=1)
    max_duration_seconds: float = Field(default=140, ge=1)
    target_min_seconds: float = Field(default=45, ge=1)
    target_max_seconds: float = Field(default=120, ge=1)
    min_height: int = Field(default=720, ge=240)
    max_file_bytes: int = Field(default=100 * MIB, ge=MIB)
    max_frozen_fraction: float = Field(default=0.15, ge=0, le=1)
    loudness_lufs_min: float = Field(default=-20)
    loudness_lufs_max: float = Field(default=-12)
    title_max_chars: int = Field(default=70, ge=1)
    post_max_chars: int = Field(default=280, ge=1)


class GameConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tokens: list[str] = Field(min_length=1, max_length=8)
    players: list[PlayerName] = Field(min_length=1, max_length=8)
    seed: int | None = None
    brief: str = Field(min_length=1, max_length=2000)
    judge: JudgeConfig = Field(default_factory=JudgeConfig)
    limits: Limits = Field(default_factory=Limits)
    linger_seconds: float = Field(default=15, ge=0, le=600)
    replay_media_budget_bytes: int = Field(default=48 * MIB, ge=0)
