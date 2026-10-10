# How to make a video for a Softmax post

This is the procedure behind the one video the team approved (The Wall, 77 s, judged 89.9) and the one it did not (Read the Room, 49 s, judged 59.5, "mostly cringe"). It agrees with `docs/POLICY_GUIDE.md` and the judge's rubric; where it is more specific, it is because a version was made and rejected. The starter kit (`kits/video-kit/`, zipped as `dist/video-kit.zip`) carries the rules, the templates, both examples with their real prompts and cut lists, and the scripts named below.

## 1. Three shapes that work

**A narrated fable from a game the reader knows.** 60-90 s. Small characters play a game the viewer understands from one frame (a wall and a clock; a boat that spins when one rower pulls harder; a runner who crosses the line still holding the baton). The weakest player narrates in first person, one quiet voice over a quiet bed, no text in the frames, and the thesis appears once, on the end card. Use it when there is an idea to leave behind and time to make fifteen shots. Cost of The Wall: about 9,500 Scenario CU over six versions in one day.

**A muted clip from a real game or replay.** 15-60 s. A real Coworld episode, replay or film cut to one moment, legible with the sound off, with one line of text that says what the reader is looking at and does not repeat it. Use it when something true and specific happened in the work. No voice, no music needed; leave it silent rather than padding a silent track (a silent track measures -70 LUFS and is deducted; no audio stream is not). The rule is the same as for pictures: the clip explains itself, or it is cut.

**A one-idea kinetic text piece.** 8-20 s. One observation, typeset on cream paper in the house type (IBM Plex), words arriving on a timing you set, silent or with room tone, ending on `softmax.com`. This is the "one observation" post made to move; it works only when the sentence would hold as a text-only post. It fails the moment it becomes lyric cards for a thesis or a slogan with a beat under it, which is what Read the Room's chorus was. If you need music to make it land, it is not landing.

Whatever the shape: the first frame is the hook, it autoplays muted, and the judge sees twelve frames and the last one. If the story is not on that sheet, it is not in the feed.

## 2. The pipeline (narrated fable; the other shapes use steps 6-9)

Each step is approved cheaply before the next is paid for. Scenario prices: a 2048x1152 GPT Image 2.5 still about 15 CU; a 5 s 720p Seedance 2.5 clip about 232 CU, 8 s 370, 10 s 418; an ElevenLabs read 16 CU; a 90 s bed 60 CU.

1. **Thesis, then game.** Write the thesis as the client's own sentence; it becomes the end card verbatim. Pick three or four candidate games and generate one frame per game showing its failure (about 15 CU each). Reject any game that needs its rules explained. Do not write a script until the game is picked.
2. **Script.** 9-15 sentences, first person, the weakest player, under 180 words (the house voice reads 2.5 words a second). Every sentence names something that can be filmed. The last spoken line is a dry result. Fill in `templates/shotlist.md`: one row per sentence with its literal picture, camera and what happens in the clip.
3. **Cast sheet and set.** One GPT Image 2.5 still for the cast (three poses each, "clean sheet layout, full bodies visible"), one still of the empty set. Crop single characters from the sheet and upload the crops; they anchor far better than the whole sheet. The set frame is the first reference of every shot; one set is what kept fifteen stills consistent.
4. **Stills.** One GPT Image 2.5 call per sentence, `referenceImages = [set frame, character crops]`, the style line verbatim, a reference key naming each character, then the shot as a frozen moment of an action with the camera stated. Launch in parallel, contact-sheet them, read the sheet with the sound off. Fix compositions here: a bad still is 15 CU, a bad clip 400.
5. **Clips.** Seedance 2.5 image-to-video from each still, 720p, `generateAudio: false`, 5-10 s (2-3 s more than the cut needs). Brief a sequence of verbs and a camera move; the exact brief that shipped is in `kits/video-kit/prompt-rules.md`, rule 14. Tile every clip at 1 fps (`ffmpeg -i clip.mp4 -vf "fps=1,scale=320:-1,tile=10x1" check.png`) and read it before cutting.
6. **Voice.** ElevenLabs v4 on Scenario, house voice "Lily", stability 0.45, `wav_48000`, `[pause]` between sentences. Then word timings with faster-whisper (`small`, int8, `word_timestamps=True`) saved as `vo_<voice>_words.json`. For a muted clip or a text piece, skip to 8.
7. **Bed.** ElevenLabs Music v2.5, `forceInstrumental`, length = film + 15 s. Prompt the register: felt piano, cello drone, no drums, soft under a voice. The Wall's prompt is in `examples/the-wall/prompts-audio.md`.
8. **Cut from word timings.** `python3 tools/phrase_times.py vo_words.json` prints each sentence's start and end with the 1.0 s narration offset. Each shot starts about 0.4 s before its sentence and ends when the sentence ends plus the time the action needs. Put the numbers in `cut=` in `tools/assemble.py` (hard cuts, one 0.8 s crossfade into the end card held 5.5 s, bed at 0.16, `loudnorm I=-17`) and render. Re-run `phrase_times.py --cuts` after every clip swap; it flags shots that start late or run long.
9. **End card.** `tools/cards.py`: cream paper, the thesis in IBM Plex Serif, the wordmark, the URL. Print `softmax.com` once; the judge flagged The Wall for printing it twice.
10. **Verify.** `tools/contact_sheet.sh reel.mp4 sheet.png` (0.5 s steps) and read the whole thing, then `--judge` for the twelve frames the panel sees. `ffmpeg -af ebur128` around -17 LUFS; `freezedetect` should fire only on the end card.
11. **Encode for X.** `tools/encode_for_x.sh reel.mp4 video.mp4`: H.264 high profile, yuv420p, AAC 48 kHz, at least 720 px tall, `+faststart`, two-pass loudnorm to -16 LUFS, then it prints duration, size, aspect and loudness against X's limits: 0.5 to 140 s, under 250 MiB, aspect between 1:3 and 3:1, loudness within -24 to -10 LUFS (the game deducts outside that), 720 px or more (deducts below), under 15 percent frozen frames (deducts above). A silent source is encoded video-only.

## 3. Prompt rules, with the before and after

The full list is `kits/video-kit/prompt-rules.md`; these are the ones that changed the verdict.

**Brief clips as action, never as living stills.** Before (The Wall v1, the version called "a reel of photos"): "stop-motion-style animation, gentle and precise, low motion blur. Quiet before the start. The five stand on the line; Flint shifts its weight forward ... Camera: very slow push-in." After (v3, shipped): "Animate this frame into a real ACTION shot: characters move with full-body, physical, fast motion; things happen; the camera moves. This is not a still with a slow push-in. ... Pip jumps for the top, misses by a mile, slides back down the wall, lands in the dust, gets up, jumps again, slides down again. Camera: pans across the wall following the climbers, then drops down to Pip."

**One literal picture per phrase.** Before (v1 opening): a wide still of five agents on a line, pushed in slowly, under "The game's simple. There's a wall. The clock stops when the last of us is over." The note: "the storyline is good but the illustrations don't fit." After (v4): five shots for five phrases: an empty wall, a timer flipping, a dolly down the line to the smallest one, Flint already over while Pip hangs at the top of a hopeless jump, Flint landing.

**Stillness needs the camera to say so.** "Flint does NOT move" from a three-quarter angle was ignored twice. Restaged from behind, feet planted, "Camera: locked off", it worked first time.

**The thesis is never printed or sung.** Before (Read the Room, 0:01, typed on the wall as spoken): "Okay. First rule. Nobody dances alone." Then a chorus of "Read the room, before you make a move ... it's a groove", and "Train, eval, test, repeat. Softmax dot com." After (The Wall): no Softmax copy for 72 s; the last line is "He's still the fastest over the wall. He's just not finished until I am."; the card says "Alignment is something you learn with others."

**State the camera in the still.** "Ground-level tracking view along the ink start line, very shallow focus: in the near foreground, out of focus, the angular charcoal legs of FLINT crouched to sprint ... and at the end of the line, in sharp focus, PIP, the smallest, its backpack too big, head tilted all the way back looking up the wall." The first-person frames (hands on the top edge, the field opening) were the best images produced.

## 4. What the team rejected, and why

From Read the Room, in the judge's words: "Warm concept, but it commits every sin on the rejection list in the first ten seconds and then keeps going." The thesis printed large in the first five seconds; a lyric-card barrage ("READ THE ROOM", "BODIES", "INTO THE"); an origami robot with a smiley face that "tips into the mascot-cheering category"; a hand-drawn arrow that "looks like a pitch deck"; an end card with a lyric fragment and no wordmark; disco-pop that "tips into earnest branded pop, the first thing the team rejected"; four diverse humans plus a cute robot, "a well-worn formula"; motion that "reads as pose-to-pose 3D render, not genuine camera movement". The planning documents were thorough (`examples/read-the-room/`); the shape was wrong before the first frame was generated.

From the versions of The Wall that did not ship: three humans at a kitchen table watching a laptop ("contrived": reactions without actions, nobody knew why they were there); an invented lantern game ("I don't understand the game immediately"); clips briefed as slow push-ins ("a reel of photos"); exposition over unrelated action ("the illustrations don't fit"); a cut that drifted two seconds after clip swaps ("drawn out in places"); a timer insert and a walk-away that were each one number too short ("timer a bit longer, an extra second at the end", fixed in the cut list without regenerating).

And from the rubric, the rules that are flags rather than taste: hashtag piles, exclamation marks, emoji punctuation, hype, engagement bait, product copy, self-congratulation, unsupported claims, typos, media that does not read muted at phone size, a mascot cheering.

## 5. Checklist before you submit

- Muted, one frame: can a stranger tell what the game is and who is losing? Is there any text in any frame other than the end card?
- Twelve frames (`contact_sheet.sh --judge`): is the story on the sheet? Does something happen in every frame, with the camera moving in most?
- Is the thesis absent until the card, and on the card exactly once? Wordmark once, URL once?
- Is the last spoken line dry? Is the warmth in the pictures?
- Re-derived the cut from word timings after the last clip swap? Does any shot start after its line, or run more than a second past it without a reason?
- Encode: H.264/AAC, 720 px or more, 0.5-140 s, under 250 MiB, aspect within 1:3 to 3:1, loudness between -24 and -10 LUFS, frozen frames under 15 percent (only the end card).
- Post text: one or two lines, under 280 weighted, no hashtags, no exclamation marks, does not repeat the film, ends in `softmax.com`.
- Alt text: describes what is in the clip for someone who cannot see it; names who narrates.
- Would a researcher repost this under their own name today?

## 6. Package and submit

Directory with `entry.json` (schema `softmax-post-entry/2`) and the one video it names; `kits/video-kit/templates/entry.json` is the shape. `text` is the post as it would appear; `media` is one item with `path` and `alt_text`; `thesis` is the end card; `notes` carries the full narration and what the frames show, for the judge; `credits` and `made_with` name the tools.

```bash
marketing-check ./my-post                      # the same gates and deductions the game runs
uv run coworld upload-policy --file ./my-post --name my-post
uv run coworld submit my-post --league <league_id>
```

Or file it from the form at `softmax.com/marketing`. Your newest submission replaces your previous one on the board; three an hour at most, and the third is usually a guess.
