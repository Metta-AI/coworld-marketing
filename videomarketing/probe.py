"""ffprobe/ffmpeg measurements and judge imagery for one video."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
FFPROBE = shutil.which("ffprobe") or "ffprobe"


@dataclass
class Measurement:
    ok: bool
    error: str = ""
    duration: float = 0.0
    width: int = 0
    height: int = 0
    fps: float = 0.0
    video_codec: str = ""
    has_audio: bool = False
    size_bytes: int = 0
    frozen_seconds: float = 0.0
    frozen_tail_seconds: float = 0.0
    loudness_lufs: float | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "error": self.error,
            "duration": round(self.duration, 3),
            "width": self.width,
            "height": self.height,
            "fps": round(self.fps, 3),
            "video_codec": self.video_codec,
            "has_audio": self.has_audio,
            "size_bytes": self.size_bytes,
            "frozen_seconds": round(self.frozen_seconds, 2),
            "frozen_tail_seconds": round(self.frozen_tail_seconds, 2),
            "loudness_lufs": None if self.loudness_lufs is None else round(self.loudness_lufs, 1),
            "warnings": self.warnings,
        }


def _run(args: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)


def _parse_fps(rate: str) -> float:
    try:
        num, _, den = rate.partition("/")
        return float(num) / float(den or 1)
    except (ValueError, ZeroDivisionError):
        return 0.0


def measure(path: Path, *, timeout: float = 240) -> Measurement:
    try:
        probe = _run(
            [FFPROBE, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return Measurement(ok=False, error=f"ffprobe failed: {error}")
    if probe.returncode != 0:
        return Measurement(ok=False, error="ffprobe: " + (probe.stderr.strip().splitlines() or ["unknown error"])[-1])
    try:
        info = json.loads(probe.stdout)
    except json.JSONDecodeError:
        return Measurement(ok=False, error="ffprobe returned no JSON")
    streams = info.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video is None:
        return Measurement(ok=False, error="no video stream")
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    fmt = info.get("format", {})
    m = Measurement(
        ok=True,
        duration=float(fmt.get("duration") or video.get("duration") or 0.0),
        width=int(video.get("width") or 0),
        height=int(video.get("height") or 0),
        fps=_parse_fps(video.get("avg_frame_rate") or video.get("r_frame_rate") or "0/1"),
        video_codec=str(video.get("codec_name") or ""),
        has_audio=audio is not None,
        size_bytes=int(fmt.get("size") or path.stat().st_size),
    )
    if m.duration <= 0:
        return Measurement(ok=False, error="zero duration")

    # One decode pass: frozen frames + integrated loudness.
    args = [FFMPEG, "-hide_banner", "-nostats", "-i", str(path), "-vf", "freezedetect=n=-55dB:d=1.0"]
    if m.has_audio:
        args += ["-af", "ebur128=peak=none"]
    else:
        args += ["-an"]
    args += ["-f", "null", "-"]
    try:
        run = _run(args, timeout=timeout)
    except subprocess.TimeoutExpired:
        m.warnings.append("analysis pass timed out; freeze and loudness not measured")
        return m
    if run.returncode != 0:
        m.warnings.append("analysis pass failed; the file may be partly corrupt")
    err = run.stderr
    starts = [float(x) for x in re.findall(r"freeze_start: ([0-9.]+)", err)]
    durations = [float(x) for x in re.findall(r"freeze_duration: ([0-9.]+)", err)]
    m.frozen_seconds = sum(durations)
    # A freeze that runs to the end of the file is reported with a start and no end; treat it as the tail.
    ends = [float(x) for x in re.findall(r"freeze_end: ([0-9.]+)", err)]
    if len(starts) > len(ends) and starts:
        tail = m.duration - starts[-1]
        m.frozen_tail_seconds = max(0.0, tail)
        m.frozen_seconds += m.frozen_tail_seconds
    elif starts and ends and m.duration - ends[-1] < 0.5:
        m.frozen_tail_seconds = durations[-1] if durations else 0.0
    if m.has_audio:
        integrated = re.findall(r"I:\s*(-?[0-9.]+) LUFS", err)
        if integrated:
            m.loudness_lufs = float(integrated[-1])
    return m


def contact_sheet(path: Path, duration: float, frames: int, out: Path, *, columns: int = 4, tile_w: int = 400) -> bool:
    rows = max(1, -(-frames // columns))
    step = max(duration / frames, 0.05)
    vf = f"fps=1/{step:.4f},scale={tile_w}:-2,tile={columns}x{rows}:padding=4:color=0xfffdf4"
    run = _run(
        [FFMPEG, "-hide_banner", "-v", "error", "-y", "-i", str(path), "-vf", vf, "-frames:v", "1", "-q:v", "4",
         str(out)],
        timeout=240,
    )
    return run.returncode == 0 and out.exists()


def frame_at(path: Path, t: float, out: Path, *, width: int = 640) -> bool:
    run = _run(
        [
            FFMPEG, "-hide_banner", "-v", "error", "-y", "-ss", f"{max(t, 0):.3f}", "-i", str(path),
            "-frames:v", "1", "-vf", f"scale={width}:-2", "-q:v", "5", str(out),
        ],
        timeout=60,
    )
    return run.returncode == 0 and out.exists()
