#!/usr/bin/env python3
"""Zip kits/video-kit/ into dist/video-kit.zip deterministically (sorted names, fixed timestamps, fixed modes).

Usage: python tools/build_video_kit.py [--check]

The zip's bytes depend only on the kit's file contents, so two builds of the same tree are identical.
--check builds to memory and reports whether dist/video-kit.zip matches, without writing.
"""

from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KIT = ROOT / "kits" / "video-kit"
OUT = ROOT / "dist" / "video-kit.zip"
PREFIX = "video-kit/"
FIXED_TIME = (1980, 1, 1, 0, 0, 0)  # the earliest timestamp zip can store
SKIP_NAMES = {".DS_Store", "__pycache__", "Thumbs.db"}
SIZE_LIMIT = 2 * 1024 * 1024


def kit_files() -> list[Path]:
    files = []
    for path in sorted(KIT.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_NAMES or part.endswith(".pyc") for part in path.relative_to(KIT).parts):
            continue
        files.append(path)
    return files


def build() -> bytes:
    buffer = io.BytesIO()
    total = 0
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as out:
        for path in kit_files():
            rel = path.relative_to(KIT).as_posix()
            data = path.read_bytes()
            total += len(data)
            info = zipfile.ZipInfo(PREFIX + rel, date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3  # unix, so the mode bits are honoured
            mode = 0o755 if (path.suffix in {".sh", ".py"} and path.stat().st_mode & 0o100) else 0o644
            info.external_attr = (0o100000 | mode) << 16
            out.writestr(info, data)
    if total > SIZE_LIMIT:
        raise SystemExit(f"kit is {total / 1048576:.2f} MiB unpacked; the limit is 2 MiB")
    return buffer.getvalue()


def main() -> int:
    data = build()
    names = [p.relative_to(KIT).as_posix() for p in kit_files()]
    if "--check" in sys.argv:
        if OUT.exists() and OUT.read_bytes() == data:
            print(f"{OUT.relative_to(ROOT)} is up to date ({len(data)} bytes, {len(names)} files)")
            return 0
        print(f"{OUT.relative_to(ROOT)} is missing or stale; run tools/build_video_kit.py", file=sys.stderr)
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(data)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(data)} bytes, {len(names)} files")
    for name in names:
        print(f"  {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
