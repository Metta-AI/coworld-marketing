"""Pre-flight for players: validate an entry directory, zip or video the way the game will, and print the report."""

from __future__ import annotations

import argparse
import io
import json
import sys
import tempfile
import zipfile
from pathlib import Path

from videomarketing.config import Limits
from videomarketing.entry import load_entry
from videomarketing.judge import technical_review
from videomarketing.probe import measure


def pack_directory(directory: Path) -> Path:
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as out:
        for path in sorted(p for p in directory.rglob("*") if p.is_file()):
            out.writestr(path.relative_to(directory).as_posix(), path.read_bytes())
    target = Path(tempfile.mkdtemp(prefix="svm-check-")) / "file"
    target.write_bytes(archive.getvalue())
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a Softmax Video Marketing entry before uploading it.")
    parser.add_argument("path", type=Path, help="entry directory, zip, or video file")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    args = parser.parse_args(argv)

    source = args.path
    if source.is_dir():
        source = pack_directory(source)
    limits = Limits()
    workdir = Path(tempfile.mkdtemp(prefix="svm-check-work-"))
    entry = load_entry(source, workdir, limits, default_title=args.path.name)
    measurement = measure(entry.video_path) if entry.video_path else None
    review = technical_review(entry, measurement, limits) if measurement else None

    report = {
        "kind": entry.kind,
        "title": entry.meta.title,
        "format": entry.meta.format,
        "problems": entry.problems,
        "measurement": measurement.to_dict() if measurement else None,
        "technical": review.to_dict() if review else None,
    }
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"{entry.meta.title}  [{entry.meta.format}]  package: {entry.kind}")
        for problem in entry.problems:
            print(f"  - {problem}")
        if measurement:
            m = measurement
            print(f"  {m.duration:.1f} s  {m.width}x{m.height}  audio={'yes' if m.has_audio else 'no'}  "
                  f"loudness={m.loudness_lufs}  frozen={m.frozen_seconds:.1f}s")
        if review:
            print(f"  technical score {review.score:.0f}/100  eligible={review.eligible}")
            for check in review.checks:
                mark = "ok " if check.ok else ("GATE" if check.gate else f"-{check.penalty:.0f}")
                print(f"    {mark:5} {check.id}: {check.detail}")
        if entry.meta.post:
            print(f"  post ({len(entry.meta.post)} chars): {entry.meta.post}")
    ok = bool(review and review.eligible)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
