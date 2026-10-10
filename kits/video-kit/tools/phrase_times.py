#!/usr/bin/env python3
"""Print the narration's sentence bounds (the cut list) from whisper word timings.

usage: python3 phrase_times.py vo_words.json [--offset 1.0] [--cuts cuts.json] [--lead 0.4]

vo_words.json  a list of [word, start, end] as faster-whisper writes it (see examples/the-wall/vo_lily_words.json)
--offset       seconds the narration is delayed in the film (the first picture lands before the first word); default 1.0
--cuts         optional JSON list of [shot, seconds] in film order (the `cut=` list in assemble.py); when given, each
               sentence is matched to the shot playing when it starts, and late or early shots are flagged
--lead         how early a shot should start before its sentence; default 0.4 s

Sentences end at a word that ends with "." "?" or "!"; commas stay inside a sentence. Whisper splits numbers
("1" ".4") so a trailing ".4" is not a sentence end.

Rules this encodes (from The Wall, v5): a shot starts about `lead` seconds before its sentence and ends when the
sentence ends plus the time its action needs; after any clip swap, re-derive the whole list from these numbers
instead of nudging durations by eye. Drift of two seconds in the back half read as "drawn out".
"""

from __future__ import annotations

import json
import sys


def sentences(words: list[list], offset: float) -> list[dict]:
    out, cur = [], []
    for w, s, e in words:
        cur.append((w, s, e))
        ends = w.endswith((".", "?", "!")) and not (w.startswith(".") and w[1:].replace(".", "").isdigit())
        if ends:
            out.append(
                {
                    "n": len(out) + 1,
                    "start": round(cur[0][1] + offset, 2),
                    "end": round(cur[-1][2] + offset, 2),
                    "text": " ".join(x[0] for x in cur),
                }
            )
            cur = []
    if cur:
        out.append(
            {
                "n": len(out) + 1,
                "start": round(cur[0][1] + offset, 2),
                "end": round(cur[-1][2] + offset, 2),
                "text": " ".join(x[0] for x in cur),
            }
        )
    return out


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    with open(argv[0]) as f:
        words = json.load(f)
    offset = float(argv[argv.index("--offset") + 1]) if "--offset" in argv else 1.0
    lead = float(argv[argv.index("--lead") + 1]) if "--lead" in argv else 0.4
    cuts = None
    if "--cuts" in argv:
        with open(argv[argv.index("--cuts") + 1]) as f:
            cuts = json.load(f)

    sents = sentences(words, offset)
    last_end = sents[-1]["end"]
    print(f"{len(words)} words, {len(sents)} sentences, offset {offset:.2f} s, last word ends {last_end:.2f} s")
    print()
    if not cuts:
        for s in sents:
            print(f"{s['n']:>2}  {s['start']:6.2f} - {s['end']:6.2f}   {s['text']}")
        return 0

    shots, t = [], 0.0
    for shot, d in cuts:
        shots.append({"shot": shot, "start": t, "end": t + float(d), "sents": []})
        t += float(d)
    print(f"{len(cuts)} shots, body ends {t:.2f} s")
    # Each sentence belongs to the shot that covers most of it (a shot may carry several short sentences).
    for s in sents:
        best = max(shots, key=lambda sh: min(sh["end"], s["end"]) - max(sh["start"], s["start"]))
        best["sents"].append(s)
    print()
    print(f"{'shot':<18} {'span':>15}   lead   tail   lines")
    for sh in shots:
        if not sh["sents"]:
            span = f"{sh['start']:6.2f}-{sh['end']:6.2f}"
            print(f"{sh['shot']:<18} {span}   (no line: must earn its place as action)")
            continue
        first, last = sh["sents"][0], sh["sents"][-1]
        lead_actual = first["start"] - sh["start"]
        tail = sh["end"] - last["end"]
        notes = []
        if lead_actual < 0.15:
            notes.append("starts late: begin the shot earlier")
        elif lead_actual > lead + 1.0:
            notes.append("starts long before its line: trim")
        if tail < -0.3:
            notes.append(f"line runs {-tail:.1f} s past the cut")
        elif tail > 2.5 and sh is not shots[-1]:
            notes.append(f"{tail:.1f} s of picture after the line: reads as drawn out unless the action needs it")
        text = " / ".join(s["text"] for s in sh["sents"])
        print(f"{sh['shot']:<18} {sh['start']:6.2f}-{sh['end']:6.2f}   {lead_actual:4.2f}  {tail:5.2f}   {text}")
        for n in notes:
            print(f"{'':<18} {'':>15}   note: {n}")
    print()
    print(f"last word to end of body: {t - last_end:.2f} s", end=" ")
    print("(The Wall used about 2.6 s, then a 0.8 s crossfade to a 5.5 s end card)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
