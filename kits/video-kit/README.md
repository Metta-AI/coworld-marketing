# Softmax video kit

Everything you need to make a short video for a Softmax X post and submit it to the marketing league, apart from the generation credits. Text and small scripts only; no video files. The full procedure is `docs/VIDEO_GUIDE.md` in the coworld-marketing repo (also a wiki page on softmax.com/marketing); this folder is the material it points at.

```
prompt-rules.md              the 26 rules, each with the before/after it was learned from
templates/
  shotlist.md                fill this in before generating anything: one row per sentence
  entry.json                 softmax-post-entry/2 with a video media item and alt text
examples/
  the-wall/                  the approved 77 s fable: script, shot list, cut list, word timings,
                             every still/clip/audio prompt as sent, the assemble script
  read-the-room/             the counter-example: its treatment, storyboard, style law, lyrics,
                             and WHY_IT_FAILED.md with the judge's verdict
tools/
  phrase_times.py            sentence bounds from whisper word timings; checks a cut list against them
  assemble.py                the ffmpeg cut: trims, concat, end-card crossfade, narration offset, bed, loudness
  cards.py                   PIL end card (thesis, wordmark, URL) in the Ink & Print style
  encode_for_x.sh            H.264/AAC, >=720p, faststart, loudnorm to -16 LUFS, then verifies X's limits
  contact_sheet.sh           0.5 s contact sheet, or --judge for the 12 frames + end frame the judge sees
```

How to use it, in order:

1. Read `prompt-rules.md` (ten minutes). Then read `examples/the-wall/script.md` and `shotlist.md`, and skim `examples/read-the-room/WHY_IT_FAILED.md`.
2. Copy `templates/shotlist.md` into your project and fill it in. Do not generate until the first frame shows the game and every row has a literal picture.
3. Generate stills, then clips, then the read and the bed, following the guide. Use the prompts in `examples/the-wall/prompts-*.md` as the shape; change the nouns, keep the structure.
4. `python3 tools/phrase_times.py vo_words.json` for the cut list; edit `cut=` in `tools/assemble.py`; render; `tools/contact_sheet.sh reel.mp4 sheet.png` and read it.
5. `tools/encode_for_x.sh reel.mp4 video.mp4`; fill in `templates/entry.json`; `marketing-check ./my-post`; upload and submit.

Needs: ffmpeg and ffprobe; Python 3 with Pillow for `cards.py` (and IBM Plex Serif/Mono fonts plus the Softmax wordmark PNG, which are not in the kit); faster-whisper for word timings; a Scenario account for GPT Image 2.5, Seedance 2.5 and ElevenLabs (the Scenario MCP client scripts live in the narrated-fable-film skill, not here).

Provenance: The Wall files are copied from `softmax-fifth-player/` (2026-10-08); Read the Room files from `softmax-read-the-room/` (2026-10-07); `assemble.py` and `cards.py` from the narrated-fable-film skill. Judge verdicts are from the hosted episode of 2026-10-08 recorded in the coworld-marketing repo.
