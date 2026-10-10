# STYLE.md — "Read the Room" (disco-pop music video, animated 3D) — the law

## Concept
A 2:14 disco-pop music video. Four human+agent duos (MIA & VESPER lead; ROB & ECHO, KAI & ONYX, ANA & QUILL) play the
games of the Softmax universe together and learn to read the room together. The comedy is physical: wrong moves done
beautifully. The humans are learning too. Softmax is the rooms (the game night, the dinner, the campfire, the arena bench,
the dance floor) and one spoken tag at the end. NO product UI. No HUD frame. No subtitle track.

## Footage rules
All footage is generated 3D of the cast (fal.ai: GPT Image 2 edit style frames from the four character sheets, Seedance 1.5
pro image-to-video 1080p, silent) in `assets/video/<clip>/` (24 fps frames, `m_*.png` Apple Vision mattes, track.json
with box/c/top and MediaPipe pose for humans). Footage is the film: shown clean, full-frame or near, never filtered.
Graphics are sparse and physical: hook words that hit on the beat, a count, a sticker label, a hand-drawn arrow, a
spotlight iris, confetti. Never a frozen frame. Mattes on busy sets are people-only: use them for type-behind only where
they are clean; otherwise type in the negative space the frames were composed with.

## Looks
| look | ground | ink | accent | rule |
| --- | --- | --- | --- | --- |
| **GREY** (alone) | the grey room plate | white | none | intro only; cold, static |
| **ROOM** (the games) | the plate's own cream rooms, backdrop → paper #fffdf4 via matte where clean | `fg` #111827 | `navy` #1a3875, `terracotta` #945637 | IBM Plex Mono hero words, hand-drawn arrows, sticker labels; hierarchy by type and whitespace |
| **DISCO** (the floor) | the plate's mirror-ball floor | paper #fffdf4 | `goldBright` #f4cf7a, pink #ff6fa3 | big Archivo 125% chant words, light sweeps drawn in code, confetti; glow allowed on the floor |
| **DAWN** (the street) | the plate | `fg` | `terracotta` | the end card: the official wordmark on paper, one spoken tag |

## Type roles
- **CHANT** `Archivo` 900 at 125% width, UPPERCASE: READ THE ROOM, MAKE A MOVE, the counts.
- **HERO** `IBM Plex Mono` 700: one or two words per verse line (TWENTY HANDS, ALL YOUR CARDS, CENTREPIECE, THE PEOPLE…).
- **STICKER** `IBM Plex Mono` 700 on a paper rectangle with a 6 px rim and a slight rotation, pinned to a character via matte box / pose.
- **SYSTEM** `JetBrains Mono` 600 UPPERCASE for counts and tiny labels. `Instrument Serif` never (no print inserts in this film).
- Brand only on the end card: `assets/brand/softmax_wordmark.png` (never recoloured) + `softmax.com` in mono.

## Lyric display
Hero words only, on their onsets; not every word. Chorus chant words land on every "Read the room" and "make a move".
The spoken intro and tag are typed in mono as spoken. Never the same treatment twice in a row.

## Motion grammar
130.4 BPM, bar 1.84 s. Cuts on downbeats or just before the pickup. Verse: one gag per line, one cut per line, a beat event
inside (the gag's impact frame gets a 1-frame punch 0.04). Chorus: the dance move IS the sync layer: the clip's moves
beat-warped to the kicks (`tools/beatwarp.py`), chant words on the onsets, light sweeps on the snares. Breakdown: held
spotlight shots, one new light per line. Final chorus: biggest, confetti, the whole cast. ≤ 3 full-frame flips/s.
Springs: stickers outBack s=2.6; chant slams from 1.6× k=300 z=.45; arrows stroke-draw 12 fr.

## HUD
`E.hud.alpha = 0` in every scene (no frame, no counters, no subtitles). The film is the acting.

## Bans
Product UI of any kind; filters on footage; invented numbers; emoji icons; cyan/magenta; decorative cards; Cogs vs Clips
characters; any text baked into generated frames.
