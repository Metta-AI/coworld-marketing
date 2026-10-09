"""Pre-flight for entrants: validate a post package the way the game will, and print the technical report.

marketing-check ./my-post            # a directory with entry.json and optional media
marketing-check ./post.txt           # bare text
marketing-check ./clip.mp4           # bare media
marketing-check --pack ./my-post out.zip   # also write the zip the platform would stage
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import tempfile
import zipfile
from pathlib import Path

from marketing.config import Limits
from marketing.entry import load_entry, weighted_length
from marketing.judge import technical_review
from marketing.probe import measure


def pack_directory(directory: Path) -> Path:
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as out:
        for path in sorted(p for p in directory.rglob("*") if p.is_file()):
            out.writestr(path.relative_to(directory).as_posix(), path.read_bytes())
    target = Path(tempfile.mkdtemp(prefix="mkt-check-")) / "file"
    target.write_bytes(archive.getvalue())
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a Softmax Marketing post before uploading it.")
    parser.add_argument("path", type=Path, help="entry directory, zip, media file, or text file")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    parser.add_argument("--pack", type=Path, default=None, help="write the staged zip to this path")
    args = parser.parse_args(argv)

    source = args.path
    if source.is_dir():
        source = pack_directory(source)
        if args.pack is not None:
            args.pack.write_bytes(source.read_bytes())
    limits = Limits()
    workdir = Path(tempfile.mkdtemp(prefix="mkt-check-work-"))
    entry = load_entry(source, workdir, limits, default_title=args.path.name)
    measurement = measure(entry.media_path, entry.media_kind) if entry.media_path else None
    review = technical_review(entry, measurement, limits)

    report = {
        "kind": entry.kind,
        "label": entry.meta.label,
        "text": entry.meta.text,
        "weighted_length": weighted_length(entry.meta.text),
        "media_kind": entry.media_kind,
        "problems": entry.problems,
        "measurement": measurement.to_dict() if measurement else None,
        "technical": review.to_dict(),
    }
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"{entry.meta.label}  package: {entry.kind}  media: {entry.media_kind}")
        for problem in entry.problems:
            print(f"  - {problem}")
        if entry.meta.text:
            print(f"  text ({weighted_length(entry.meta.text)}/280 weighted):")
            for line in entry.meta.text.splitlines():
                print(f"    | {line}")
        if measurement:
            m = measurement
            extra = f"  {m.duration:.1f} s  audio={'yes' if m.has_audio else 'no'}" if m.kind == "video" else ""
            print(f"  {m.kind} {m.width}x{m.height}{extra}  {m.size_bytes / 1048576:.2f} MiB")
        print(f"  technical score {review.score:.0f}/100  eligible={review.eligible}")
        for check in review.checks:
            mark = "ok " if check.ok else ("GATE" if check.gate else f"-{check.penalty:.0f}")
            print(f"    {mark:5} {check.id}: {check.detail}")
    return 0 if review.eligible else 1


if __name__ == "__main__":
    sys.exit(main())
