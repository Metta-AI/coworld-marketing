#!/usr/bin/env bash
# Contact sheet of a cut, to read before you ship it (and after every clip swap).
#
# usage: tools/contact_sheet.sh in.mp4 out.png [--step 0.5] [--cols 8] [--width 384]
#        tools/contact_sheet.sh in.mp4 out.png --judge
#
# default: one frame every --step seconds, --cols per row, each --width px wide (The Wall was read at 0.5 s steps)
# --judge: what the craft panel sees: 12 frames evenly spaced over the film, 6 wide, plus the final frame as
#          out_end.png. If the story is not legible on this sheet with no sound, it is not legible in the feed.
#
# For a single generated clip, tile one frame per second and look for characters that wandered, extra characters,
# and actions that reverse the line ("he waited" while someone steps ahead):
#   ffmpeg -i clip.mp4 -vf "fps=1,scale=320:-1,tile=10x1" check.png

set -euo pipefail
in="${1:?usage: contact_sheet.sh in.mp4 out.png [--step 0.5] [--cols 8] [--width 384] | --judge}"
out="${2:?usage: contact_sheet.sh in.mp4 out.png [--step 0.5] [--cols 8] [--width 384] | --judge}"
shift 2
step=0.5; cols=8; width=384; judge=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --step) step="$2"; shift 2;;
    --cols) cols="$2"; shift 2;;
    --width) width="$2"; shift 2;;
    --judge) judge=1; shift;;
    *) echo "unknown option $1" >&2; exit 2;;
  esac
done
[[ -f "$in" ]] || { echo "no such file: $in" >&2; exit 1; }
dur="$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$in")"

if (( judge )); then
  # 12 frames at the centres of 12 equal slices, like the game's probe, then the last frame.
  fps="$(awk -v d="$dur" 'BEGIN{printf "%.6f", 12/d}')"
  ffmpeg -y -v error -i "$in" -vf "fps=${fps}:round=up,scale=${width}:-2,tile=6x2:padding=4:color=white" -frames:v 1 "$out"
  end="${out%.*}_end.${out##*.}"
  ffmpeg -y -v error -sseof -0.2 -i "$in" -frames:v 1 -update 1 -vf "scale=${width}:-2" "$end"
  echo "wrote $out (12 frames over ${dur%.*} s) and $end (final frame)"
  exit 0
fi

n="$(awk -v d="$dur" -v s="$step" 'BEGIN{printf "%d", (d/s)+1}')"
rows=$(( (n + cols - 1) / cols ))
fps="$(awk -v s="$step" 'BEGIN{printf "%.6f", 1/s}')"
ffmpeg -y -v error -i "$in" -vf "fps=${fps},scale=${width}:-2,tile=${cols}x${rows}:padding=2:color=white" -frames:v 1 "$out"
echo "wrote $out: ${n} frames, ${step} s apart, ${cols} per row (${dur%.*} s)"
