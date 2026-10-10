# The Wall (77 s, approved)

The narrated fable the Softmax team approved on 2026-10-08 and the baseline the marketing league's judge ranks first (89.9 of 100; craft 86.5). Made in one day in six versions, about 9,500 Scenario CU. Nothing here is a video; every file is text copied from the production project with its origin noted.

| file | what it is | from |
| --- | --- | --- |
| `script.md` | the 172-word narration as read, with notes on why it works, plus the post text and alt text | `wall/audio/plan_lily.json`, `players/the-wall/entry.json` |
| `shotlist.md` | the 15 shots with in/out times, the line each illustrates, camera, and which version fixed it; the shots that were cut and why | `tools/assemble_wall.py`, plan files, review notes |
| `cuts_v6.json` | the cut list alone: `[shot, seconds]` in order | `tools/assemble_wall.py` |
| `vo_lily_words.json` | word timings of the Lily read (faster-whisper small, int8): the numbers the cut was derived from | `wall/audio/vo_lily_words.json` |
| `assemble_wall.py` | the exact ffmpeg assembly that rendered v6 (paths are the production project's; the generalised version is `tools/assemble.py` in the kit root) | `tools/assemble_wall.py` |
| `prompts-stills.md` | every GPT Image 2.5 prompt sent, grouped by version, with CU | `wall/*/plan*.json` |
| `prompts-clips.md` | every Seedance 2.5 prompt sent, with duration and CU; v1 "living stills" next to v3 "action" | `wall/*/plan*.json` |
| `prompts-audio.md` | the ElevenLabs narration and music-bed requests, three voices tried | `wall/audio/plan*.json` |

Read the stills and clips prompts side by side with the shot list: the same frame, briefed two ways, is the clearest lesson in the kit.

Judge's notes on the finished film (hosted episode, 2026-10-08, rubric post/1): "Frame 1 hourglass establishes stakes immediately; wall game is legible silent. Frame 4 top-of-wall POV pays off the script's 'I'd never seen anything from the top.' Frame 9 Flint airborne mid-leap is the one pure motion beat. Frame 10 group walk into sunset risks Pixar-credits warmth but earns it. The double URL on the end card is the only visible sloppiness." The one flag: the end card printed softmax.com twice (in the wordmark and again as a URL line). Print it once.
