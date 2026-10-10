# TREATMENT.md — "Read the Room" (2:14, disco pop, animated 3D)

## Song facts
- `audio/master.mp3` 128.1 s, written for the film (ElevenLabs Music via fal.ai, disco candidate A, female lead, crowd answers).
- Measured 130.4 BPM, bar 1.84 s, 69 downbeats (0.02 1.88 3.72 5.56 7.40 9.26 11.10 12.94 14.80 16.64 18.48 20.32 22.18
  24.02 25.88 27.72 29.56 31.42 33.26 35.12 36.96 38.80 40.64 42.50 44.34 46.18 48.02 49.88 51.72 53.56 55.40 57.26 59.10
  60.96 62.80 64.64 66.48 68.34 70.18 72.02 73.88 75.72 77.56 79.42 81.26 83.10 84.96 86.80 88.64 90.50 92.32 94.18 96.02
  97.86 99.72 101.56 103.42 105.26 107.12 108.96 110.80 112.64 114.50 116.34 118.18 120.02 121.88 …), 265 kicks, 402 snares.
- Word onsets in `engine/data/lyrics.json` (spoken intro 1.1–5.5, verse 1 from 14.32, chorus 1 from 32.36, verse 2 from
  48.94, chorus 2 from 71.54, breakdown 90.0–104.1, final chorus 105.23–120.0, spoken tag 120.0–124.1; check the plots in
  analysis/plots/ before trusting a chant onset).
- Energy: spoken intro over a filter sweep and the kick → verse 1 → pre build → chorus (crowd answers "read the room") →
  verse 2 → pre → chorus 2 → half-time spoken breakdown with a drum fill → final chorus, key lift, call-and-response
  flipped → spoken tag, hard stop ~124, room tone to 128.

## Arc (the comedy)
Alone (an agent dancing in an empty room) → game night, dinner: four social fails, done beautifully (verse 1) → "look at
them", the head turned like a lamp, the lean too far (pre) → the dance: READ THE ROOM, the bump, the lamp, the conga out
the door (chorus) → the wins: the liar clocked, the pizza trade, the gracious loss, the saved chair (verse 2) → the human
sits back with popcorn while the agent runs the room (pre 2) → chorus 2 bigger, the human gets a step wrong → the
breakdown: a worksheet torn into confetti, the room fills one spotlight at a time → the final chorus: the agent leads, the
whole floor follows → dawn, the duo walks home with the lamp. Softmax appears once, spoken, at the end.

## First 3 seconds (muted autoplay)
`s01_alone`: Vesper dancing alone in a grey room, confident and perfectly wrong; "Okay. First rule." types in mono as
spoken (1.1); the door opens on "Nobody dances alone." (3.4–5.5) and warm light pours in.

## Sections (hard cuts on downbeats or just before the pickup)
| id | time | look | lyrics | must-have ideas (one gag per line) |
| --- | --- | --- | --- | --- |
| intro | 0.00–14.20 | GREY → ROOM | Okay. First rule. Nobody dances alone. (1.1–5.5), then 8 s instrumental disco build | `s01_alone` full-frame; the spoken words typed in mono on the wall as spoken; on "alone" the door opens (the clip's own move) and warm light spills; 5.6–14.2 the build: the clip's dance continues, a beat-counter of light sweeps (code) grows across the floor on each bar, and at 12.94 a hard cut to the game night table of `s03_handshake` held still-ish before the vocal (or `s07_lookatthem` as a window) |
| verse1 | 14.20–25.20 | ROOM | I took you to a table, you shook twenty hands too long (14.32) / …showed them all your cards (17.00) / …you ate the centrepiece (19.78) / Baby you can do the math, but you can't do the people (21.82) | `s03_handshake` (TWENTY HANDS as a Doto count that keeps counting past 20; both handshakes let go on the same beat) → `s04_cards` (ALL YOUR CARDS sticker on the fanned cards; Mia's dive on "showed") → `s05_centrepiece` (CENTREPIECE in mono; a petal sticker on Vesper's screen) → `s06_napkins` (THE MATH ✓ / THE PEOPLE ✗ as two paper tags; the late laugh on "people") |
| pre1 | 25.20–32.30 | ROOM | Don't look at me, look at them ×2 (25.26, 27.34) / Watch the hands, watch the eyes, watch the way they lean (29.24) | `s07_lookatthem` (an arrow from Mia's hands to the table re-drawn each time she turns Vesper's head; LOOK AT THEM stamps twice) → `s08_lean` on "lean" (the whole table leans; the type leans with them; Vesper topples: punch 0.05) ; 31.4–32.3 push into the dance floor |
| chorus1 | 32.30–48.85 | DISCO | Read the room, before you make a move (32.36) / Everybody's talking with their bodies, it's a groove (36.44) / Read the room, yeah you'll get it wrong, that's cool (39.84) / Then you carry what you learned out of the door and into the world (43.72) | `s09_readtheroom` beat-warped to the kicks: READ THE ROOM as an Archivo chant row that whips in on each head-sweep (the type follows the sweep direction), MAKE A MOVE on the point; `s10_lamp` on "make a move"/"get it wrong" (the bump, the bow, the lamp caught: a 1-frame punch on the catch; THAT'S COOL sticker); `s11_conga` on "out of the door" (the conga through the door, INTO THE WORLD stamps on the street wall) |
| verse2 | 48.85–63.80 | ROOM / campfire / bench | Now the quiet one is lying and you clocked it from the door (48.94) / …traded half your pizza… (52.80) / …lost the game on Friday… shook his hand (56.76) / …saving me a chair before I even asked (60.16) | `s12_campfire` (THE QUIET ONE arrow lands on the sweating agent; Kai's finger lowers on "clocked") → `s13_pizza` (HALF ↔ ONE THING as a two-way trade arrow; the crown on "more") → `s14_friday` (FRIDAY ✗ then the raised hand on "shook"; a tiny confetti pop) → `s15_chair` (the chair slides on "chair", BEFORE I EVEN ASKED typed small as Mia sits) |
| pre2 | 63.80–71.50 | ROOM | I don't tell you what to do ×2 (63.86, 65.74) / I just put you in the room and let the room do what it does (67.44) | `s16_popcorn`: Mia with popcorn; three little mono tags fire on the beats as Vesper does three things (POUR / SEPARATE / CATCH); "let the room do what it does" = the room's noise as rising hand-drawn lines; push to the floor at 71.4 |
| chorus2 | 71.50–88.64 | DISCO | same chorus (71.54 / 75.96 / 79.40 / 82.32) + instrumental 86.9–88.6 | `s17_linedance` beat-warped: four duos in a line, the chant words now as a scrolling row behind the line (via mattes where clean, otherwise above the heads); Mia's wrong step on "get it wrong" and Vesper turning her head on "that's cool"; "out of the door" = `s11_conga` again reversed (coming back in) or `s10_lamp`; 86.9–88.6 the lights drop one by one to black (the breakdown opens dark) |
| breakdown | 88.64–105.20 | BLACK + spotlights | Static problem sets never taught anybody to dance (90.02) / Twenty strangers, one night, minutes not months (93.84) / We lose in public, we learn in public (96.86) / Social, ever-changing, that's the test, that's the gift (99.46) / Now bring it back (102.60) | `s18_spotlight` held: Vesper alone with the worksheet, tears it on "dance" (confetti in code too); from 93.84 a new spotlight iris (code) opens on one more stranger per line using `s19_everyone` windowed (or cropped) so the room fills up: TWENTY in Doto counting the lights; "bring it back" = the drum fill: all spotlights snap to full, hard cut at 105.2 |
| chorus3 | 105.20–120.00 | DISCO finale | Read the room, I read the room… (105.23) / …it's a groove (109.04) / Read the room, we read the room… (112.35) / Then we carry what we learned… (115.52) | `s19_everyone` beat-warped, full-frame, held long: the chant as call-and-response rows (crowd row / Mia row), confetti in code; Mia's wrong step and Vesper turning her head (full circle) on "we got it wrong"; "out of the door and into the world" = the circle opens toward camera, type whips out |
| outro | 120.00–134.0 | DAWN end card | Nobody dances alone. Train, eval, test, repeat. Softmax dot com. (120.0–124.1) | `s20_dawn` (the walk home with the lamp): the three spoken lines typed in mono as spoken, bottom-left; the official wordmark builds slowly 125–128 with `softmax.com` in mono; silence 128–134 with the lamp's shade gag and a cursor blink; fade through paper → navy → black |

## Footage map (`assets/video/<clip>`, 24 fps, 720p; fill in key moments when prepped)
s01_alone · s03_handshake · s04_cards · s05_centrepiece · s06_napkins · s07_lookatthem · s08_lean · s09_readtheroom ·
s10_lamp · s11_conga · s12_campfire · s13_pizza · s14_friday · s15_chair · s16_popcorn · s17_linedance · s18_spotlight ·
s19_everyone · s20_dawn (19 clips; s02 and s21 cut for budget).

## Facts and copy
The only Softmax copy in the film is the spoken tag ("Train, eval, test, repeat. Softmax dot com.") and the breakdown's
paraphrase of the homepage ("static problem sets", "twenty strangers", "minutes not months", "social, ever-changing").
The games are the universe's real leagues in spirit (a poker night, a liars' campfire, a garden dinner, an arena
bench) but no league names or UI appear.
