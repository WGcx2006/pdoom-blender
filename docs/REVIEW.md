# Review log

The film was made plate by plate by seven sub-agents, with a single reviewer (the lead) doing
the toolkit, the opening, the four hooks, the edit, and every review pass. This is a summary of
what the review actually caught and changed.

## The loop

1. Each agent built a plate module and rendered 6–20 full-resolution stills at the key lyric
   beats.
2. The reviewer looked at the stills at 100%, plus the original treatment and reference plates,
   and sent back concrete blockers: palette, clipped type, unreadable lyrics, empty frames,
   missing story beats, render cost.
3. The agent rebuilt, re-rendered, and reported. Plates that were structurally wrong were
   rebuilt rather than polished.
4. After all 22 plates existed, the whole film was assembled and checked again with 60-frame
   and cut-boundary contact sheets, frame extraction around lyric onsets, and per-scene
   luminance statistics.

## Examples of what changed

**loss** — the first 3D landscape was flooded with warm light and read brown; the singer's line
was clipped at "sudden". Rebuilt to ink/bone contour lines with the orange spark as the only
strong colour, the full two-row lyric fitted to the frame, and the plunge cut on the drop.

**shoggoth** — the first creature was smooth grey/olive tubes with large cartoon holes and no
mask. Rebuilt around the friendly mask → x-ray dissolve → 31 engraved tubes → ten eyes →
shinigami tags → flatline. Hatching is a 16% bone hairline with a thin orange fresnel rim.

**spacetime** — the lyric was 3D-extruded into unreadable blocks, a full-frame brown rectangle
appeared at one cut, and the black hole was an orange fill. Fixed to flat Archivo on a baseline,
removed the flash planes, and made the hole an ink field with a thin ember photon ring.

**ilya** — the first pass was an orange close-up slab. Rebuilt with a real 3D laptop, stickers,
a dark REDACTED screen, a word-by-word lid close, and a proscenium theatre with a light cone.

**paperclips** — the clip material read as copper jewellery. Moved to low-metallic bone/ash,
kept one warm rim, and put the closing lyric on an ink band so it stays readable over the clips.

**outro** — the paper equation card let the old giant readout and ∞ trace show through it; a
leftover "13 / Loom" card sat near the end. Added an opaque table behind the sheet, hard-cleared
the earlier phases at frame 300, replaced the leftover with three rewind cards, and enlarged the
Regenerate button.

**open / hooks** — AGI was clipped on the right when it slammed in, a ghost number collided with
UPPING, and the lyric word spacing was too tight. Fitted AGI, removed the ghost, widened the
space advance globally, and re-rendered the opening and all four hooks consistently.

## Final QA

- `tools/check_counts.py`: all 22 scenes have exactly their timeline frame count (4702 total).
- `tools/qa.py`: per-scene min/mean/max luminance over sampled frames; no fully black scene.
- `tools/cuts.py`: 44 in/out frames at every boundary, checked for clipping and dark gaps.
- 60-frame sheet across the film (`docs/contact-sheet.jpg`).
- `ffprobe`: 1920×1080, 30 fps, 156.733 s, H.264 + AAC stereo.
- Audio levels: mean −17.6 dB, peak −4.2 dB.

## Known limits

- 30 fps vs the original's 60 fps; fast whips show more stepped motion blur.
- The original's raymarched engraving is shader-level; here it is real 3D geometry plus planar
  object-space hatching. Close up, the hatch flow does not follow the surface as precisely.
- A few plates remain warmer or busier than the original (paperclips, fuse's chart, spacetime's
  vortex, the shoggoth's grey).
- The final loop is an image-level return to the opening sheet, not a pixel-identical loop.
- The repository does not include the song, fonts or original timing data. The fetch script
  obtains them from the original project; see `NOTICE.md`.
