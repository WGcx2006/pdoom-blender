# The 22 plates

Times are the song clock. Each plate is a separate Blender scene; `blender/scenes/<module>.py`
builds it from `pdoom.data` (word-level lyric times, beats, sections). Hook 1–4 share
`hook.py`; prompt 1–3 share `prompt.py`.

| # | plate | window (s) | frames | lyric / content | implementation |
|---|-------|-----------:|-------:|-----------------|----------------|
| 01 | `open` | 0.000–9.090 | 273 | I see sparks of AGI in your eyes · Your circuits make me nervous · that's no surprise | TikZ construction sheet, plotter-drawn unicorn from primitives, pen spark, giant AGI, eye callout, PCB reroute, surprisal |
| 02 | `loss` | 9.090–16.363 | 218 | There was a sudden drop in your training loss · now I'm your servant and you're my boss | 3D log chart drawn by the spark, contour heightfield canyon, SERVANT/BOSS inversion, 180° roll |
| 03 | `prompt1` | 16.363–22.726 | 191 | ChatGPT, please don't eat me alive | engraved 3D throat of rings, token-by-token prompt, next-token bars, Enter rush |
| 04 | `hook1` | 22.726–24.090 | 41 | I'm upping my P(doom) | typographic slams, rising letters, value 0.15 |
| 05 | `room` | 24.090–29.544 | 164 | 'cause the future goes FOOM · Trapped in the Chinese room · with a bag of shrooms | FOOM branching explosion, 3D hairline library, Chinese room sign, 我不懂 cards, acid mycelium |
| 06 | `shoggoth` | 29.544–38.634 | 273 | See through the shoggoth's lies · with your shinigami eyes | bone mask, x-ray scan, 31 engraved tentacle tubes, eyes, shinigami tags, flatline |
| 07 | `spacetime` | 38.634–52.724 | 423 | stable training run · singularity's begun · optimizing, accelerating · atoms rearranging | CRT oscilloscope, photon ring, lensed graticule, vortex, atom-to-paperclip |
| 08 | `prompt2` | 52.724–59.088 | 191 | Sydney, please let me free | bars closing on beats, reply typing, spark-drawn smile |
| 09 | `hook2` | 59.088–60.451 | 41 | I'm upping my P(doom) | ink on signal-orange field, heavier; 0.42 |
| 10 | `ascent` | 60.451–69.542 | 273 | basilisk boom · NVDA to the moon · Omega Point · One E thirty FLOPs | 3D serpent eye, banknote/moon, 150-line convergence, 31-digit register |
| 11 | `bureau` | 69.542–80.905 | 341 | safe enough · Forward MLP, backward, repeat · von Neumann's obsolete | Form 7-B, 3D rubber stamp, MLP pulse, mirrored backward, von Neumann strike/burn |
| 12 | `leftturn` | 80.905–89.086 | 245 | Sharp left turn and there you are · Without a single CDR | roadmap, whip-pan, mask-as-terrain, survey labels, Gantt/CDR slot |
| 13 | `prompt3` | 89.086–95.449 | 191 | Gato, please don't let me go | quiet pool, drifting letters, caret holding the last letter |
| 14 | `hook3` | 95.449–96.813 | 41 | I'm upping my P(doom) | hairline type, tiny, giant dim 0.81, small P(DOOM) payoff |
| 15 | `paperclips` | 96.813–102.267 | 164 | paperclips fill the room · Killswitch guy's on PTO · nowhere left to go | real swept clip tubes, split lattice, OOO card, closing ceiling |
| 16 | `fuse` | 102.267–109.994 | 232 | Too late now, we lit the fuse · Orthogonality thesis blues | braided burning cord, ink-on-cream chart, bending regression string |
| 17 | `stack` | 109.994–114.994 | 150 | transformers all the way · Till you learned to disobey | 14 modelled transformer blocks, falling camera, disobedient block |
| 18 | `dense` | 114.994–124.538 | 286 | Post-Chinchilla, super-dense · breaking safety fence · 100k GPU · RLHF goes askew | typographic pressure, safe-area breaks, 400×250 GPU grid, tilt table/mask |
| 19 | `hook4` | 124.538–125.902 | 41 | I'm upping my P(doom) | layered/strobing P(DOOM), shake, 0.99999 |
| 20 | `loom` | 125.902–131.811 | 177 | Just as foretold by Loom · masked pre-training · recursive self-upgrade | tree of continuations, sampled path, [MASK] page, Droste portals |
| 21 | `ilya` | 131.811–140.230 | 253 | What did Ilya see? · We'll never know · Was it all for show? | 3D room/laptop/stickers, REDACTED, lid close, theatre/curtain/seam |
| 22 | `outro` | 140.230–156.651 | 493 | instrumental | detonation, number apparatus, ∞ trace, paper equation, NaN¹, Regenerate, rewind, loop |

Total: **4702 frames** at 30 fps = 156.73 s.

The edit follows the original's `timeline.ts` boundaries, recomputed from the aligned lyric
and beat data. Scene windows are in `blender/pdoom/data.py`.
