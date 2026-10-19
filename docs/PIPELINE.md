# Pipeline

## Data flow

    pdoom-video/                  # fetched, not committed (original project, MIT)
      data/lyrics.json            # word-level lyric times
      data/audio.json             # 132.007 BPM grid, sections, envelopes, onsets
      app/public/fonts/           # Archivo / IBM Plex Mono / Cormorant (OFL)
      audio/pdoom.mp3             # song (not covered by MIT)

    blender/pdoom/data.py         # loads the JSON, exposes SCENES, line(), beats, pdoom()
    blender/pdoom/core.py         # scene setup, palette, text, curves, camera, post, baking
    blender/pdoom/motifs.py       # spark / mask / HUD / rails
    blender/scenes/*.py           # 17 modules -> 22 timeline scenes
    blender/build.py              # builds one scene -> out/blend/<scene>.blend
    tools/render_all.py           # builds + renders frames -> out/frames/<scene>/####.png
    tools/assemble.py             # clips -> concat -> audio -> grain/vignette -> mp4
    tools/qa.py, cuts.py          # review sheets and per-scene luminance stats

## Scene contract

Every module exports `build(name)` and starts with:

    sc = core.new_scene(name, samples=..., motion_blur=True)

`new_scene` sets 1920×1080, 30 fps, EEVEE, Standard view transform, the timeline frame
range, motion blur, and a compositor with Bloom + Fog Glow halation + 0.005 lens dispersion.
Scenes then build objects on a 19.2-unit-wide orthographic stage (100 px/unit) or a real
perspective camera.

Animation is baked keyframes. The only sources of time are:

- `data.frame_to_time(scene, frame)`
- lyric word starts/ends from `data.line()`
- `data.BEATS`, `data.DOWNBEATS`, `data.env()`, `data.hit()`
- `data.pdoom(t)`

No scene uses wall-clock time or unseeded randomness. `core.hash01` provides deterministic
jitter. Rebuilding a scene reproduces the same frames.

## Typography and line art

Text is real Blender font objects (the repo's static Archivo/Plex/Cormorant instances), placed
on measured baselines. Word objects are laid out by prefix advance so the font's kerning is
preserved; `core.add_lyric` fits long lines to a maximum width. Type and line art share one
emission material driven by object colour, so per-word karaoke is an object-colour curve.

Line art is beveled curves. Thin hairlines are 0.006–0.015 world units (0.6–1.5 px). Engraved
3D surfaces use `core.mat_hatch_lit`: a near-black Principled base modulated by a wave-texture
hatch, plus a fresnel rim. The 2D plates use `core.mat_hatch` (self-lit hatching).

## Post

- In Blender: Bloom (threshold 1.0, so bone type stays crisp and only the signal/cores bloom),
  Fog Glow halation tinted orange, lens dispersion 0.005.
- In ffmpeg: uniform 4/255 film grain (`noise=alls=4:allf=t+u`) and a PI/7 vignette, applied
  once to the concatenated film.

## Rendering and performance

- 1920×1080, EEVEE, 16–40 TAA samples depending on the plate. Motion blur shutter 0.32.
- Most plates render at ~0.8–1.4 s/frame on an RTX 5060 laptop; heavy 3D plates at 2–5 s.
- `tools/render_all.py` builds each .blend, then renders scenes with N parallel Blender
  processes, each writing a PNG sequence. `tools/assemble.py` encodes per-scene H.264 clips,
  concatenates them losslessly, then applies audio and the final grade in one pass.
- The final film is 4702 frames / 156.73 s / H.264 High / AAC 192 kbps.

## Reproducing the exact cut

The edit is fixed by `data.SCENES`. Rendering all frames and running `tools/assemble.py`
reproduces the release film (modulo ffmpeg/x264 version and GPU rendering differences).
