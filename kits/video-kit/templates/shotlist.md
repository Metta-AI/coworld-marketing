# Shot list: <title>

Fill this in before you generate anything. One row per sentence of the script. If a row has no literal picture, cut the sentence. If the game needs a row to explain its rules, change the game.

**Thesis** (end card, verbatim, one sentence):
**Game** (one the viewer already knows; its failure drawn in one frame with no caption):
**Narrator** (the weakest player, first person):
**Set** (one; its key frame is the first reference of every still):
**Cast** (4-5; material = personality; one clause each for the reference key):
**Voice** (house voice: ElevenLabs "Lily", stability 0.45) and **bed** (felt piano, cello, no drums, under the voice):
**Style line** (reused verbatim in every image prompt):

| # | line (as read) | the literal picture | camera | what happens in the clip (2-4 verbs) | clip length | words | est. s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | | | | | 5-10 s | | |
| 2 | | | | | | | |
| 3 | | | | | | | |

Column notes:

- **the literal picture**: what the frame shows, frozen mid-action, every character named. "There's a wall" is a wall. "They learned to trust each other" has no picture; cut it.
- **camera**: state it. Low behind the weak one for weakness; first person for a reveal; from behind, locked off, for someone who must stay still; a crane up an empty set for a quiet line.
- **what happens**: a sequence of events, not adjectives. Every clip gets at least one event and a camera move, even the quiet ones. Never "gentle, precise, slow push-in".
- **clip length**: 2-3 s more than the cut needs so the action completes; 5 s for an insert, 8-10 s for anything with a sequence.
- **est. s**: words / 2.5 (the Lily read) + 0.4 s lead. Total under 90 s; the post caps at 140 s.

After the read: replace **est. s** with the real sentence bounds from `tools/phrase_times.py`, and derive the `cut=` list from them, never from the still durations.

Checks before paying for clips: a contact sheet of the stills, read with the sound off. Does the first frame show the game? Can you point at the loser? Is there any text in any frame?
