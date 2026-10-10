# The Wall: every clip prompt, as sent
Source: `softmax-fifth-player/wall/*/plan*.json` (Seedance 2.5 image-to-video via Scenario, `model_bytedance-seedance-2-5`, `image` = the still, 720p, `generateAudio: false`). Asset ids removed; prompts verbatim, with the requested duration and the CU each cost.
Read the v1 rows and the v3 `wall/action` rows side by side. The v1 brief ("gentle and precise, low motion blur ... Camera: very slow push-in") produced the version the team called "a reel of photos". The v3 brief ("a real ACTION shot ... things happen; the camera moves. This is not a still with a slow push-in") is what shipped.

## wall/video/plan.json  (first pass, briefed as living stills (v1-v2; rejected as "a reel of photos"))

### s01_line  (7 s, 324 CU)

```
Animate this exact frame. Keep every character design, material and the paper set exactly as shown; no new characters enter; no text appears; stop-motion-style animation, gentle and precise, low motion blur. Quiet before the start. The five stand on the line; Flint shifts its weight forward, ready; Pip tilts its head back to look up the wall; the flags stir in a light wind; the sand in the timer has not started. Camera: very slow push-in.
```

### s02_pip_looks_up  (5 s, 232 CU)

```
Animate this exact frame. Keep every character design, material and the paper set exactly as shown; no new characters enter; no text appears; stop-motion-style animation, gentle and precise, low motion blur. Pip's head tilts slowly further back looking up the wall, then a small swallow and a nod to itself. The flags move gently. Camera: holds, slight slow tilt up along the wall.
```

### s03_gun  (6 s, 278 CU)

```
Animate this exact frame. Keep every character design, material and the paper set exactly as shown; no new characters enter; no text appears; stop-motion-style animation, gentle and precise, low motion blur. The start: Flint vaults over the top of the wall in a burst of dust and disappears over it; Ollie and Marrow haul themselves up and over; Tam scrambles up; Pip jumps and falls back, jumps again, nowhere near the top. The sand in the timer runs. Camera: holds wide.
```

### s04_from_above  (5 s, 232 CU)

```
Animate this exact frame. Keep every character design, material and the paper set exactly as shown; no new characters enter; no text appears; stop-motion-style animation, gentle and precise, low motion blur. Pip looks up at the four faces along the top of the wall; Flint's head twitches impatiently, Ollie is still, Marrow's lantern sways, Tam's antenna wobbles. The last grains of sand fall. Camera: slow push-in on Pip.
```

### s05_hands  (6 s, 278 CU)

```
Animate this exact frame. Keep every character design, material and the paper set exactly as shown; no new characters enter; no text appears; stop-motion-style animation, gentle and precise, low motion blur. Three hands reach down over the edge and stretch; Pip's hand reaches up from below, straining, the gap never closes; the sand timer empties; the hands withdraw. Camera: holds.
```

### s06_practice  (8 s, 370 CU)

```
Animate this exact frame. Keep every character design, material and the paper set exactly as shown; no new characters enter; no text appears; stop-motion-style animation, gentle and precise, low motion blur. Night. Flint drops down, runs back and vaults the wall again, and again, each time faster, dust rising and settling, the moon steady. Camera: holds wide, lets the repetition play.
```

### s07_flint_watches  (9 s, 418 CU)

```
Animate this exact frame. Keep every character design, material and the paper set exactly as shown; no new characters enter; no text appears; stop-motion-style animation, gentle and precise, low motion blur. Flint stands completely still at the foot of the wall, body ready to run but head turned, watching. Ollie braces its back against the wall; Marrow climbs onto Ollie's shoulders and pulls itself over the top, lantern swinging. Tam follows up the same way. Pip edges into frame. Camera: very slow push-in on Flint.
```

### s08_step  (5 s, 232 CU)

```
Animate this exact frame. Keep every character design, material and the paper set exactly as shown; no new characters enter; no text appears; stop-motion-style animation, gentle and precise, low motion blur. Flint kneels, hands cupped into a step; Pip steps up onto the hands, grips Flint's shoulder, and Flint lifts, raising Pip up toward the top of the wall. Camera: low angle, tilts up with the lift.
```

### s09_pip_top  (5 s, 232 CU)

```
Animate this exact frame. Keep every character design, material and the paper set exactly as shown; no new characters enter; no text appears; stop-motion-style animation, gentle and precise, low motion blur. From the top of the wall: Pip's hands grip the edge; the view opens across the field to the flag and the low sun; below, the four look up, Marrow lifting the lantern, Tam waving. A flag ripples. Camera: slow rise and settle, as if Pip is pulling itself up.
```

### s10_over  (9 s, 418 CU)

```
Animate this exact frame. Keep every character design, material and the paper set exactly as shown; no new characters enter; no text appears; stop-motion-style animation, gentle and precise, low motion blur. Flint drops down off the top of the wall and lands last among the four; Pip bounces, Marrow raises the lantern, Ollie's eyes close in a smile, Tam claps. The sand timer at the right still holds sand in its upper bulb; the circle flag flutters. Camera: holds, slight slow push-in.
```

### s11_walk  (8 s, 370 CU)

```
Animate this exact frame. Keep every character design, material and the paper set exactly as shown; no new characters enter; no text appears; stop-motion-style animation, gentle and precise, low motion blur. The five walk away from the wall together toward the flag, Flint walking slowly at Pip's pace in the middle, their long shadows stretching ahead; the flags move; the sun lowers. Camera: holds wide, then a very slow rise.
```

## wall/video2/plan.json  (close-up variant (v2))

### s07b_flint_close  (6 s, 278 CU)

```
Animate this exact frame. Keep every character design, material and the paper set exactly as shown; no new characters enter; no text appears; stop-motion-style animation, gentle and precise. Flint's head stays almost perfectly still, watching; only its dash eyes narrow slightly and its shoulders settle. In the soft background Ollie braces against the wall while Marrow climbs up over Ollie's shoulders and disappears over the top, lantern light swinging across the wall. Dust drifts. Camera: holds, very slow push-in on Flint's face.
```

## wall/reroll/plan_video_a.json  (stillness re-roll A, three-quarter angle (failed))

### s07_v2  (9 s, 418 CU)

```
Animate this exact frame. Keep every character design, material and the paper set exactly as shown; no new characters enter; no text appears; stop-motion-style animation, gentle and precise. IMPORTANT: the charcoal angular figure FLINT in the foreground does NOT move its feet or body at all for the entire clip; it stands frozen in place, only its head turns slowly to watch. In the background OLLIE braces its back against the wall; MARROW climbs onto Ollie's shoulders and pulls itself up over the top edge, lantern swinging; TAM follows the same way. Pip edges into frame at the edge. Dust drifts. Camera: very slow push-in on Flint.
```

## wall/reroll/plan_video_b.json  (stillness re-roll B, from behind, locked off (worked) + timer insert)

### s07c  (9 s, 418 CU)

```
Animate this exact frame. Keep every character design, material and the paper set exactly as shown; no new characters enter; no text appears; stop-motion-style animation, gentle and precise. IMPORTANT: the charcoal angular figure FLINT in the foreground, seen from behind, stays completely frozen: feet planted, arms at its sides, body does not move at all; only its head turns a few degrees as it watches. Ollie braces against the wall; Marrow climbs up from Ollie's shoulders and hauls itself over the top edge, lantern swinging; then Tam climbs up Ollie the same way. Pip watches from the edge. Dust drifts in the warm light. Camera: locked off, no movement.
```

### s12_timer  (5 s, 232 CU)

```
Animate this exact frame. Keep every character design, material and the paper set exactly as shown; no new characters enter; no text appears; stop-motion-style animation, gentle and precise. Extreme close-up of the sand-timer. A thin stream of sand falls through the neck for the first two seconds; then the stream thins and stops completely, leaving a clear heap of sand still in the upper bulb. Nothing else moves except the flags swaying softly out of focus and the warm light. Camera: locked off, very slight slow push-in.
```

## wall/action/plan.json  (action-first re-brief (v3; the shots that shipped))

### s01_start  (10 s, 464 CU)

```
Animate this frame into a real ACTION shot: characters move with full-body, physical, fast motion; things happen; the camera moves. This is not a still with a slow push-in. Keep every character design, material and the paper set exactly as shown; no new characters; no text. Stop-motion feel with real momentum: running, jumping, falling, climbing, dust. The five crouch on the start line, tense. A beat. Then the start: all five burst forward toward the wall at once, Flint exploding ahead in a cloud of dust, Ollie and Marrow lumbering, Tam scrambling, Pip pumping its short legs at the back. The flags whip. Camera: starts low and wide, then tracks fast alongside them toward the wall.
```

### s03_scramble  (10 s, 464 CU)

```
Animate this frame into a real ACTION shot: characters move with full-body, physical, fast motion; things happen; the camera moves. This is not a still with a slow push-in. Keep every character design, material and the paper set exactly as shown; no new characters; no text. Stop-motion feel with real momentum: running, jumping, falling, climbing, dust. Flint vaults clean over the top of the wall and vanishes over it in a burst of dust. Ollie hauls itself up the leaf motifs and rolls over the edge; Marrow heaves itself up and over; Tam scrambles up and over. Pip jumps for the top, misses by a mile, slides back down the wall, lands in the dust, gets up, jumps again, slides down again. The sand in the timer runs. Camera: pans across the wall following the climbers, then drops down to Pip.
```

### s05_hands  (8 s, 370 CU)

```
Animate this frame into a real ACTION shot: characters move with full-body, physical, fast motion; things happen; the camera moves. This is not a still with a slow push-in. Keep every character design, material and the paper set exactly as shown; no new characters; no text. Stop-motion feel with real momentum: running, jumping, falling, climbing, dust. Pip jumps repeatedly from below, its sage hand shooting up toward the three hands straining down over the edge, each jump a little short, the gap never closing; the three hands stretch further; the sand timer's last grains fall and the sand runs out; the three hands slowly pull back out of sight. Camera: low angle tilts up and down with Pip's jumps.
```

### s06_practice  (10 s, 464 CU)

```
Animate this frame into a real ACTION shot: characters move with full-body, physical, fast motion; things happen; the camera moves. This is not a still with a slow push-in. Keep every character design, material and the paper set exactly as shown; no new characters; no text. Stop-motion feel with real momentum: running, jumping, falling, climbing, dust. Night practice montage in one shot: Flint drops down off the wall, sprints back across the frame, turns, sprints at the wall, leaps, catches the top and vaults over in a spray of dust; drops down again, runs back, goes again, faster, more dust each time; footprints and skid marks multiply on the paper. The moon holds. Camera: whip-pans to follow each run, then holds on the wall as dust settles.
```

### s08_lift  (8 s, 370 CU)

```
Animate this frame into a real ACTION shot: characters move with full-body, physical, fast motion; things happen; the camera moves. This is not a still with a slow push-in. Keep every character design, material and the paper set exactly as shown; no new characters; no text. Stop-motion feel with real momentum: running, jumping, falling, climbing, dust. Flint kneels fast and cups its two hands into a step. Pip plants one foot in the hands and grips Flint's shoulder; Flint stands up in one strong motion, hoisting Pip high up the face of the wall; Pip's hands slap onto the top edge and it scrambles, kicking, and hauls itself up over the top. Dust falls. Camera: low angle, cranes up with the lift all the way to the top edge.
```

### s09_top  (6 s, 278 CU)

```
Animate this frame into a real ACTION shot: characters move with full-body, physical, fast motion; things happen; the camera moves. This is not a still with a slow push-in. Keep every character design, material and the paper set exactly as shown; no new characters; no text. Stop-motion feel with real momentum: running, jumping, falling, climbing, dust. First-person from Pip: the hands on the edge heave, the view lurches up over the wall and the whole field opens out, the flag and the low sun; Pip turns to look back down and the four below jump and wave, Marrow swinging the lantern, Tam leaping. Camera: handheld rise over the edge, then a swing down to look at the others.
```

### s10_last  (8 s, 370 CU)

```
Animate this frame into a real ACTION shot: characters move with full-body, physical, fast motion; things happen; the camera moves. This is not a still with a slow push-in. Keep every character design, material and the paper set exactly as shown; no new characters; no text. Stop-motion feel with real momentum: running, jumping, falling, climbing, dust. Flint comes flying over the top of the wall last, somersaults in the air, and lands hard in a burst of dust in front of the four. Pip bounces up and down, Marrow thrusts the lantern into the air, Ollie's eyes close in a smile, Tam runs in a circle. The circle flag flips and flutters; the timer still holds sand. Camera: fast tilt down from the top of the wall with Flint's landing, then holds on the group.
```

### s11_walk  (8 s, 370 CU)

```
Animate this frame into a real ACTION shot: characters move with full-body, physical, fast motion; things happen; the camera moves. This is not a still with a slow push-in. Keep every character design, material and the paper set exactly as shown; no new characters; no text. Stop-motion feel with real momentum: running, jumping, falling, climbing, dust. The five turn from the wall and walk away toward the distant flag, Flint deliberately slowing to match Pip's short steps in the middle, Marrow swinging the lantern, Tam skipping ahead and running back. Their long shadows stretch ahead and the sun drops. Camera: cranes slowly up and back as they walk away, the wall growing small.
```

## wall/open/plan_video.json  (new opening (v4; shipped))

### o1_wall  (5 s, 232 CU)

```
Animate this frame. Keep every character design, material and the paper set exactly as shown; no new characters; no text. Stop-motion feel with real momentum. Establishing shot, no characters. The camera starts low at the foot of the wall and tilts and cranes slowly up the enormous face of the wall to its top edge, the flags along the top snapping in the wind against the dusk sky, the sand-timer passing at the right. The wall is the subject. Camera: slow crane up.
```

### o2_timer_flip  (5 s, 232 CU)

```
Animate this frame. Keep every character design, material and the paper set exactly as shown; no new characters; no text. Stop-motion feel with real momentum. The sand-timer, mounted on its wooden pivot, turns over: the rope pull tightens, the whole timer rotates a half turn, the heap of sand slides inside the glass and then begins to fall through the neck in a thin stream. The flags sway softly out of focus. Camera: holds close, tiny push-in.
```

### o3_line_to_pip  (5 s, 232 CU)

```
Animate this frame. Keep every character design, material and the paper set exactly as shown; no new characters; no text. Stop-motion feel with real momentum. Camera dollies low along the start line from left to right: past Flint's crouched angular legs, past Ollie, past Marrow's lantern, past Tam, and comes to rest on Pip at the end of the line, small, backpack too big, who tilts its head all the way back to look up the wall and swallows. Camera: slow lateral dolly, settles on Pip.
```

### o4_flint_vs_pip  (6 s, 278 CU)

```
Animate this frame. Keep every character design, material and the paper set exactly as shown; no new characters; no text. Stop-motion feel with real momentum. Flint swings over the top edge of the wall and vanishes in a trail of dust in the first second. Pip, in the foreground, hangs at the top of its jump with both arms up, then falls back down to the ground in a puff of dust, lands on its feet, looks up at the empty top of the wall. Ollie, Marrow and Tam keep climbing between them. Camera: holds, slight tilt down with Pip's fall.
```

### o5_flint_lands  (5 s, 232 CU)

```
Animate this frame. Keep every character design, material and the paper set exactly as shown; no new characters; no text. Stop-motion feel with real momentum. Flint slides to a stop in a spray of dust, one hand down, then springs upright, dusts itself off with one flick, and turns to look back up at the wall with its arms loose, waiting, impatient, tapping one foot. Dust drifts in the light. Camera: low, tracks a little to the side as Flint stands.
```
