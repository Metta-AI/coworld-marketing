# The Wall: shot list and cut (v6, the version the team approved)

Provenance: the `cut=` list in `softmax-fifth-player/tools/assemble_wall.py` (copied here as `assemble_wall.py`; the list alone is `cuts_v6.json`), aligned to the Lily read's word timings (`vo_lily_words.json`, faster-whisper `small`, int8) with the 1.0 s narration offset. Times are seconds into the film. Produce this table yourself with:

```
python3 tools/phrase_times.py examples/the-wall/vo_lily_words.json --cuts examples/the-wall/cuts_v6.json
```

Fifteen shots, body 72.2 s, then a 0.8 s crossfade into a 5.5 s end card: 76.9 s total. Every shot but the inserts came from one GPT Image 2.5 still (prompts in `prompts-stills.md`) animated by Seedance 2.5 (prompts in `prompts-clips.md`). The folder each shot shipped from tells you which version fixed it: `open/` is the v4 opening, `action/` the v3 action re-brief, `reroll/` the v2 fixes, `video2/` a close-up variant.

| # | shot | in | out | lead | line(s) it illustrates | camera | from |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | o1_wall | 0.0 | 2.9 | 1.00 | The game's simple. There's a wall. | empty set, slow crane up the wall | open (v4) |
| 2 | o2_timer_flip | 2.9 | 6.1 | 0.62 | The clock stops when the last of us is over. | close, timer flips and starts | open (v4) |
| 3 | o3_line_to_pip | 6.1 | 9.6 | 0.86 | The last of us is me. | low dolly along the start line, settles on Pip | open (v4) |
| 4 | o4_flint_vs_pip | 9.6 | 12.6 | 0.58 | Flint was over before I'd finished jumping. | Pip at the top of a hopeless jump, Flint already over | open (v4) |
| 5 | o5_flint_lands | 12.6 | 15.6 | 0.22 | He's new. He's amazing. | Flint lands in dust, springs up, taps a foot | open (v4) |
| 6 | s03_scramble | 15.6 | 19.6 | 0.38 | He waited on the far side, where the clock was still running. | pan across the climbers, drop to Pip sliding down | action (v3) |
| 7 | s05_hands | 19.6 | 24.7 | 0.52 | We lose because of me. I know. Everyone's very nice about it. | low, tilts with Pip's jumps at three hands; sand runs out | action (v3) |
| 8 | s06_practice | 24.7 | 34.1 | 0.32 | Flint thought the problem was speed. He practised. He got over in 1.4 seconds. I got over in never. | night; whip-pans follow each run | action (v3) |
| 9 | s07c | 34.1 | 42.2 | 0.38 | On the fifth night, he didn't jump. He stood there and watched Ollie... | from behind Flint, locked off; Ollie braces, Marrow climbs | reroll (v2) |
| 10 | s07b_flint_close | 42.2 | 48.1 | 0.36 | I'd seen Ollie do that a hundred times. Flint had never been slow enough to see it. | close on Flint's still head; the climb soft behind | video2 (v2) |
| 11 | s08_lift | 48.1 | 52.9 | 0.42 | Then he put his hands together, like a step, for me. | low, cranes up with the lift to the top edge | action (v3) |
| 12 | s09_top | 52.9 | 56.2 | 0.26 | I'd never seen anything from the top of the wall. | first person: hands heave, the field opens, look back down | action (v3) |
| 13 | s12_timer | 56.2 | 59.6 | 0.38 | The clock stopped with sand still in it... | extreme close-up insert; the stream stops | reroll (v2) |
| 14 | s10_last | 59.6 | 65.1 | (1.78) | ...our best ever. Flint went last. He'd never gone last. | fast tilt down with Flint's landing, hold on the group | action (v3) |
| 15 | s11_walk | 65.1 | 72.2 | (-0.16) | He's still the fastest over the wall. He's just not finished until I am. | crane up and back as five walk away at Pip's pace | action (v3) |
| | end card | 71.4 | 76.9 | | Alignment is something you learn with others. (wordmark, softmax.com) | 0.8 s crossfade, held 5.5 s | cards.py |

Lead is how early the shot starts before its first word; the rule from v5 is about 0.4 s. The two bracketed leads are the deliberate exceptions: the timer insert hands "our best ever" to Flint's landing, and the walk starts on "He's" so the landing finishes first.

Shots that did not ship, and why:

- `s01_line`, `s02_pip_looks_up`, `s03_gun`, `s04_from_above` (v1): the opening played a calm explanation of the rules over a sprint. "The storyline is good but the illustrations don't fit." Replaced by shots 1-5, one literal picture per phrase.
- `s07_flint_watches` and `s07_v2`: Flint was told "does NOT move" from a three-quarter angle and moved twice. Restaged from behind with "camera: locked off" (`s07c`) worked first time.
- `s10_over`, `s11_walk` (v1): briefed as "gentle and precise ... slow push-in"; the whole v2 reel read as "a reel of photos". Re-briefed as action in v3.
- `s01_start` (v3): a good action shot with no line of its own; cut when the opening was rebuilt.

Media: the web copy that was judged (1280x720, 6.9 MB, -18.6 LUFS, 4.1 s frozen on the end card) is `players/the-wall/video.mp4` in the coworld-marketing repo. The 1080p master is `softmax-fifth-player/wall/out/the_wall_v6_1080p.mp4` on the production machine; no video travels in this kit.
