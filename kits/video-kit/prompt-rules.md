# Prompt rules

Distilled from three projects: The Wall (approved, 89.9), Read the Room (mostly cringe, 59.5) and the kinetic-music-video skill the latter was built with. Every rule here was paid for by a version a real team rejected. "Before" is a real prompt or line that failed; "after" is the one that shipped.

## Concept and script

1. **Pick the game before the story.** The viewer must understand the game from one frame with no narration. Test: write its failure as a single image (one rower pulls harder, the boat spins; he crosses the line still holding the baton; the clock stops when the last one is over and the last one is the smallest). If the game needs its rules explained, change the game. A lantern-carry with a light radius failed this test; a wall and a clock passed.
2. **The weakest player narrates, in first person.** The fast character's change is only visible from someone it affects. Never show his face up close; never let him speak. An AI character narrating also makes a synthetic voice acceptable in-world.
3. **One picture per sentence, the literal one.** Every sentence names something that can be filmed. Under 180 words; 2.5 words a second in the house voice.
4. **The thesis is never spoken or printed before the end card.** The last spoken line is a dry, measured result.
   - Before (Read the Room, 0:01, typed on screen as spoken): "Okay. First rule. Nobody dances alone."
   - After (The Wall, last line): "He's still the fastest over the wall. He's just not finished until I am." Then the card: "Alignment is something you learn with others."
5. **Never sing, print or tweet the company's claims.** Product-explaining rhymes read as cringe regardless of craft.
   - Before (Read the Room, breakdown): "Static problem sets never taught anybody to dance / Twenty strangers, one night, minutes not months / ... Train, eval, test, repeat. Softmax dot com."
   - After (The Wall): no Softmax copy anywhere until the card.
6. **Comedy from character, not jokes.** A rule obeyed literally; a fast character standing still for the first time; "Everyone's very nice about it."
7. **Humans are explained by the picture or absent.** Three adults smiling at a laptop was "contrived". Agents only is the safe default.

## Stills (GPT Image 2.5, one per sentence)

8. **One style line, verbatim, in every prompt.** The one that held: *Stylized 3D animated feature film still, 16:9 cinematic, stop-motion warmth: glazed-ceramic knee-high agent figures, a tabletop game world built from cream paper and ink lines lit by one warm lamp, gentle Ink & Print palette (ink, navy, terracotta, sage, cream), shallow depth of field, no gloss, no neon, no readable text, no logos, no UI, no humans anywhere.*
9. **References: the set frame first, then single-character crops.** One set is what kept fifteen stills consistent. Crops anchor a character far better than a whole sheet. Add a reference key naming each character by material and one prop.
10. **Describe a frozen moment of an action, and state the camera.**
    - Before (v1 `s01_line`): "Five agents stand on an ink start line in front of it ... Quiet before the start."
    - After (v4 `o3_line_to_pip`): "Ground-level tracking view along the ink start line, very shallow focus: in the near foreground, out of focus, the angular charcoal legs of FLINT crouched to sprint, then OLLIE, MARROW with its lantern, TAM, and at the end of the line, in sharp focus, PIP, the smallest, its backpack too big, head tilted all the way back looking up the wall."
11. **Stills first, always.** 15 CU to learn a composition is wrong; 400 for a clip. Contact-sheet them and read the sheet before paying for clips.
12. **"No readable text" in every prompt.** Text baked into generated frames is never usable (kinetic-music-video lesson); in a fable it is a rule break.
13. **Redesigns are generated clean.** `referenceImages` anchor hard; a redesign that passes the old sheet comes back nearly identical.

## Clips (Seedance 2.5, image-to-video, 720p, no audio)

14. **Brief events and a camera move, never adjectives.** Seedance follows verbs.
    - Before (v1, the "reel of photos"): "Animate this exact frame ... stop-motion-style animation, gentle and precise, low motion blur. Quiet before the start. The five stand on the line; Flint shifts its weight forward ... Camera: very slow push-in."
    - After (v3, shipped): "Animate this frame into a real ACTION shot: characters move with full-body, physical, fast motion; things happen; the camera moves. This is not a still with a slow push-in. Keep every character design, material and the paper set exactly as shown; no new characters; no text. Stop-motion feel with real momentum: running, jumping, falling, climbing, dust. Flint vaults clean over the top of the wall and vanishes over it in a burst of dust. Ollie hauls itself up ... Pip jumps for the top, misses by a mile, slides back down the wall ... Camera: pans across the wall following the climbers, then drops down to Pip."
15. **Even quiet shots move.** A crane up an empty wall; a timer flipping. Something happens in every clip, or it is a still and says so.
16. **Stillness needs the camera to say so.**
    - Before (`s07_v2`, failed twice): three-quarter angle, "IMPORTANT: ... FLINT in the foreground does NOT move its feet or body at all ... Camera: very slow push-in on Flint."
    - After (`s07c`, first time): restaged from behind, "seen from behind, stays completely frozen: feet planted, arms at its sides ... Camera: locked off, no movement."
17. **Ask for 2-3 s more than the cut needs** so the action completes. 5 s for an insert, 8-10 s for a sequence. Clips return at 24 fps, about 0.04 s long.
18. **Tile every clip at 1 fps and read it before cutting.** Look for characters that wandered, extra characters, and actions that reverse the line (someone stepping ahead on "he waited").

## Voice, bed and cut

19. **House voice: ElevenLabs "Lily"** (stability 0.45, `[pause]` between sentences): slow, low, nature documentary. Record alternates once, pick, then stop.
20. **Bed under the voice, never over it.** Prompt the register ("felt piano, slow spacious chords, warm low cello drone ... never cinematic-epic, no drums, dynamics stay soft under a voice"), mix at about 0.16, normalise the mix to about -17 LUFS.
21. **Derive the cut from word timings, never from the still durations.** Each shot starts about 0.4 s before its sentence and ends when the sentence ends plus the time its action needs. Narration offset about 1.0 s. After any clip swap, re-derive the whole list; two seconds of drift read as "drawn out".
22. **Hard cuts only.** One crossfade (0.8 s) into the end card, held 5.5 s. No overlays or tags on the footage.
23. **The end card is the thesis once, the wordmark once, the URL once.** The Wall's only flag was printing softmax.com twice.

## For the post

24. **Legible muted at phone size.** The judge sees twelve frames and the last one, with no sound. If the story is not on that sheet, it is not in the feed.
25. **Alt text describes the media plainly** for someone who cannot see it; it is not the thesis or the mood.
26. **The post text does not repeat the film.** One or two lines, dry, with the one fact the film cannot show (its length, who narrates), and `softmax.com`.
