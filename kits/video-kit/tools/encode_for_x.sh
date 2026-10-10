#!/usr/bin/env bash
# Encode a finished cut for an X post: H.264 (high, yuv420p) + AAC 48 kHz, at least 720 px tall, faststart,
# two-pass loudnorm to -16 LUFS (X accepts -24 to -10; the game deducts outside that range), then verify.
#
# usage: tools/encode_for_x.sh in.mp4 out.mp4 [--height 720|1080] [--lufs -16] [--crf 20]
#
# - keeps the source frame rate and aspect; scales only when the source is shorter than --height (default 720)
#   or taller than 1080; dimensions are forced even so yuv420p encodes
# - a silent source stays silent (no audio stream): X accepts it and the game skips the loudness check, whereas a
#   padded silent track measures -70 LUFS and is deducted
# - prints duration, size, codec, aspect and the measured integrated loudness, and flags anything X would reject
# Needs ffmpeg and ffprobe. Tested with ffmpeg 8.

set -euo pipefail

in="${1:?usage: encode_for_x.sh in.mp4 out.mp4 [--height 720] [--lufs -16] [--crf 20]}"
out="${2:?usage: encode_for_x.sh in.mp4 out.mp4 [--height 720] [--lufs -16] [--crf 20]}"
shift 2
height=720; lufs=-16; crf=20
while [[ $# -gt 0 ]]; do
  case "$1" in
    --height) height="$2"; shift 2;;
    --lufs) lufs="$2"; shift 2;;
    --crf) crf="$2"; shift 2;;
    *) echo "unknown option $1" >&2; exit 2;;
  esac
done
[[ -f "$in" ]] || { echo "no such file: $in" >&2; exit 1; }
[[ "$(cd "$(dirname "$in")" && pwd)/$(basename "$in")" != "$(cd "$(dirname "$out")" 2>/dev/null && pwd)/$(basename "$out")" ]] || { echo "in and out are the same file" >&2; exit 1; }

probe() { ffprobe -v error -select_streams "$1" -show_entries "$2" -of default=nw=1:nk=1 "$3" | head -n1; }
src_h="$(probe v:0 stream=height "$in")"
src_w="$(probe v:0 stream=width "$in")"
has_audio="$(ffprobe -v error -select_streams a -show_entries stream=codec_type -of csv=p=0 "$in" | head -n1 || true)"

# Scale: up to --height when short, down to 1080 when tall, else keep. Always even dimensions.
if (( src_h < height )); then
  vf="scale=-2:${height}"
elif (( src_h > 1080 )); then
  vf="scale=-2:1080"
else
  vf="scale=trunc(iw/2)*2:trunc(ih/2)*2"
fi
vf="${vf},format=yuv420p"

video_opts=(-c:v libx264 -preset slow -crf "$crf" -profile:v high -pix_fmt yuv420p -vf "$vf" -movflags +faststart)
audio_opts=(-c:a aac -b:a 160k -ar 48000 -ac 2)

if [[ -z "$has_audio" ]]; then
  echo "source has no audio: encoding video only (no loudness check applies)"
  ffmpeg -y -v error -stats -i "$in" -map 0:v:0 -an "${video_opts[@]}" "$out"
else
  # Pass 1: measure. Pass 2: linear loudnorm with the measured values (no limiter pumping).
  measured="$(ffmpeg -v info -nostats -i "$in" -af "loudnorm=I=${lufs}:TP=-1.5:LRA=11:print_format=json" -f null - 2>&1 \
    | awk '/^\{/{p=1} p{print} /^\}/{p=0}')"
  jget() { printf '%s' "$measured" | sed -n "s/.*\"$1\" *: *\"\([^\"]*\)\".*/\1/p" | head -n1; }
  mi="$(jget input_i)"; mtp="$(jget input_tp)"; mlra="$(jget input_lra)"; mth="$(jget input_thresh)"; moff="$(jget target_offset)"
  if [[ -z "$mi" ]]; then echo "loudnorm measurement failed; see ffmpeg output" >&2; exit 1; fi
  echo "measured: I=${mi} LUFS  TP=${mtp}  LRA=${mlra}  -> target ${lufs} LUFS"
  af="loudnorm=I=${lufs}:TP=-1.5:LRA=11:measured_I=${mi}:measured_TP=${mtp}:measured_LRA=${mlra}:measured_thresh=${mth}:offset=${moff}:linear=true:print_format=summary,aresample=48000"
  ffmpeg -y -v error -stats -i "$in" -map 0:v:0 -map 0:a:0 "${video_opts[@]}" -af "$af" "${audio_opts[@]}" "$out"
fi

# Verify the way the game's probe does.
dur="$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$out")"
size="$(stat -f %z "$out" 2>/dev/null || stat -c %s "$out")"
w="$(probe v:0 stream=width "$out")"; h="$(probe v:0 stream=height "$out")"
vcodec="$(probe v:0 stream=codec_name "$out")"; acodec="$(probe a:0 stream=codec_name "$out")"; acodec="${acodec:-silent}"
lufs_out=""
if [[ "$acodec" != "silent" ]]; then
  lufs_out="$(ffmpeg -v info -nostats -i "$out" -af ebur128=framelog=quiet -f null - 2>&1 | grep -E '^\s*I:' | tail -n1 | awk '{print $2}')"
fi
aspect="$(awk -v w="$w" -v h="$h" 'BEGIN{printf "%.3f", w/h}')"
mib="$(awk -v s="$size" 'BEGIN{printf "%.1f", s/1048576}')"

echo
echo "wrote $out"
echo "  ${w}x${h} ${vcodec}/${acodec}  ${dur%.*} s  ${mib} MiB  aspect ${aspect}  loudness ${lufs_out:-n/a} LUFS"
bad=0
awk -v d="$dur" 'BEGIN{exit !(d < 0.5 || d > 140)}' && { echo "  X rejects: duration must be 0.5 to 140 s"; bad=1; }
awk -v a="$aspect" 'BEGIN{exit !(a < 0.3333 || a > 3.0)}' && { echo "  X rejects: aspect must be between 1:3 and 3:1"; bad=1; }
(( size > 100*1048576 )) && { echo "  X rejects: over 250 MiB"; bad=1; }
(( h < 720 && w < 720 )) && { echo "  judge deducts: under 720 px"; bad=1; }
if [[ -n "${lufs_out:-}" ]]; then
  awk -v l="$lufs_out" 'BEGIN{exit !(l < -24 || l > -10)}' && { echo "  judge deducts: loudness outside -24 to -10 LUFS"; bad=1; }
fi
(( bad == 0 )) && echo "  within X's limits and the game's technical panel"
echo "next: tools/contact_sheet.sh $out sheet.png --judge   (read it muted, at phone size)"
exit $bad
