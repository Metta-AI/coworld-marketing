# Read the Room (49 s teaser of a 2:14 music video): why it failed

The counter-example. A disco-pop music video with sung branded lyrics, four human+agent duos, kinetic lyric cards and a spoken "Softmax dot com" tag, made with the kinetic-music-video skill on 2026-10-07 and shown to the Softmax team that day. The team's response, in the user's words: "it was good, but response was mostly cringe." It ships in the marketing league as the baseline the judge must rank below The Wall.

The planning documents are copied here as they were, so you can see that the failure was not a lack of planning: `TREATMENT.md` (song facts, downbeats, one gag per line), `STORYBOARD.md` (21 shots), `STYLE.md` (the law: looks, type roles, bans) and `lyrics.txt`. The craft was fine. The shape was wrong.

## The judge's verdict

Hosted episode of 2026-10-08 (model claude-sonnet-4.6 through the Coworld sidecar, rubric post/1), both baselines in one duel. Read the Room scored 59.5 of 100 (craft 46.0, technical 100) against The Wall's 89.9 (craft 86.5).

Verdict: "Warm concept, but it commits every sin on the rejection list in the first ten seconds and then keeps going."

Notes: "Frame 2 kills story_not_statement immediately — the thesis is printed large on screen in the first five seconds. Frames 9–11 are a lyric-card barrage the brief named as a rejection criterion. The origami mascot is charming but tips into the mascot-cheering category. End card drops the wordmark and replaces the thesis line with a lyric fragment. Frame 7's blue arrow annotation looks like a pitch deck. Motion exists but reads as pose-to-pose 3D render, not genuine camera movement."

Flags raised (post/1 let the model phrase them freely; under the current closed list they land as `mascot_cheering`, `illegible_media` and score deductions on voice and specific):

- thesis spoken aloud in frame 2 ("Nobody dances alone") before the end card
- large kinetic lyric cards mid-screen ("READ THE ROOM", "BODIES", "INTO THE", "HANDS")
- end card reads "INTO THE WORLD", not the thesis sentence; no wordmark visible
- mascot-adjacent origami robot with smiley face
- disco-pop tone tips into earnest branded pop, the first thing the team rejected
- arrow annotation drawn on frame 7 looks like a tutorial slide
- stock-Pixar feel: four diverse humans plus cute robot is a well-worn formula
- "it's a groove" and "yeah you'll get it wrong, that's cool" are product-explaining rhymes dressed as cool
- moral stated explicitly in narration before the end card

## What each failure teaches

| what was on screen | the rule it broke | what The Wall did instead |
| --- | --- | --- |
| "Okay. First rule. Nobody dances alone." typed in mono on the wall at 0:01 (TREATMENT, intro row) | the thesis is never printed or spoken before the end card | the first three sentences are the rules of the game, as pictures; the thesis appears once, on the card |
| chorus chant words as Archivo 125% slams on every "Read the room" (STYLE, type roles) | no text in the frames; the picture must carry the line | no readable text anywhere in 72 s of footage |
| "Train, eval, test, repeat. Softmax dot com." sung/spoken as the tag; breakdown lyrics paraphrase the homepage ("static problem sets", "minutes not months") | never sing, print or tweet the company's claims | a dry last line about a wall: "He's just not finished until I am." |
| a cheerful paper agent with a smiley monitor face, waving at dawn (STORYBOARD shot 21) | no mascot cheering, waving or smiling for the camera | glazed-ceramic figures with dash eyes; nobody looks at the camera |
| a hand-drawn arrow pointing at the liar (STORYBOARD shot 12, TREATMENT verse2) | no annotation; if the picture needs an arrow it is the wrong picture | camera position does the pointing (low behind the weak one; from behind the fast one) |
| 130 BPM disco pop, female lead, crowd answers | one quiet voice and a bed under it; the register is nature documentary, not pop | felt piano and cello at 0.16 under a slow, low read |
| twenty one-gag shots, 5 s each, cut on downbeats | one literal picture per sentence, cut from word timings | 15 shots, each starting 0.4 s before its sentence |
| four human+agent duos on six sets | one set, a cast of five, humans absent | the wall, its timer and flags in every frame |

The simplest test the team applied, and the one to apply first: mute it and look at one frame. If the frame is a lyric card, a mascot or a thesis, stop.

Media: the judged 720p teaser is `players/read-the-room/video.mp4` in the coworld-marketing repo. The full 2:14 render lives in `softmax-read-the-room/out/final/` on the production machine; no video travels in this kit.
