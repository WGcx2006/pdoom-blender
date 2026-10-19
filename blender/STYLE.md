# P(doom) — Blender rebuild style & toolkit

We are rebuilding the music video "I'm Upping My P(doom)" (github.com/mexicat/pdoom-video) as a
Blender-modelled, Blender-rendered film. The original is a deterministic WebGL music video; ours is
real 3D geometry, cameras, lights and materials, composited in Blender, at 1920x1080 / 30 fps.

Read these first:
- pdoom-video/docs/TREATMENT.md — the style bible and plate-by-plate treatment (authoritative).
- ref/plates_contact.jpg — 14 stills from the original, for look only. Do not copy compositions literally;
  translate the ideas into Blender.
- pdoom-video/app/src/scenes/<plate>.ts — the original implementation. Read it for exact lyric choices,
  timings, and graphic ideas (it is TypeScript/WebGL; do not port code blindly).

## The look

- Palette only: ink #0A0A0B, bone #EEE9DF, signal #FF4D12, ember #FF8A3D, blood #C21D0B,
  graphite #5E5B57, ash #9C978F, and acid #D8FF3C only for the shrooms moment.
- Mostly black frames with hairline bone linework, precise typography, and a single orange accent that glows.
  Some plates invert to bone paper with ink lines (bureaucracy, blueprints, charts, forms).
- Engraving, not "AI art": dense thin lines, hatching, technical-drawing idioms, restrained colour, strong
  blacks, real depth. No neon, no purple/cyan, no lens-flare soup, no particles-for-particles'-sake.
- Type is huge and confident or tiny and deadpan; avoid centred subtitle stacks. Every plate uses the
  fonts in the repo: Archivo (display), IBM Plex Mono (machine), Cormorant Garamond (sacred/prophetic).
- Lyrics are integrated into the image and word-synced: a word is dim before its start and becomes
  bone or signal exactly at its start (never early beyond ~0.35 s). Each plate integrates the line differently.

## Coordinates (orthographic 2D plates)

Use core.add_camera_ortho(sc, 19.2). Then:

- Frame: x in [-9.6, 9.6], y in [-5.4, 5.4]; 1 world unit = 100 px.
- Title-safe: x in [-8.64, 8.64], y in [-4.44, 4.44] (>= 96 px margins).
- core.add_polyline widths are world units: 1.5 px = 0.015, a hairline = 0.007–0.012.
- Archivo cap height is about 0.47 * size units; size 4 is ~188 px caps. Measure, never guess:
  core.measure(sc, text, font, size) returns width, and fit() = target_width / measure(...,1.0).
- Use baseline placement: add_text(..., align_y="BOTTOM_BASELINE") (default). For right alignment use
  align_x="RIGHT" and the right margin as x.

## The toolkit (blender/pdoom/core.py, motifs.py)

Create a scene (this also configures EEVEE, post, colour management, output):

    from pdoom import core, data, motifs
    from pdoom.core import PAL, clamp, lerp, smoothstep, ease_out_expo, hash01

    sc = core.new_scene("loss", samples=32, motion_blur=True)   # scene name = timeline id
    core.add_bg(sc)
    cam = core.add_camera_ortho(sc, 19.2)
    sc.frame_set(1)
    ...
    return sc

new_scene sets frame range 1..N, 1920x1080, 30 fps, EEVEE, Standard view transform, motion blur,
and the standard compositor (bloom + halation + 0.005 lens dispersion). Do not change these unless the plate
needs a special look (if you do, say so in your report).

Geometry / drawing:

- add_text(sc, body, font_key, size, color, (x,y,z), align_x="LEFT", align_y="BOTTOM_BASELINE", hot=False, spacing=1.0)
  — emission text. color is one of PAL (linear). hot=True uses a 3x emission material for glowing accents.
- add_polyline(sc, points, width, color, z=0.0, cyclic=False, hot=False) — world-space stroke.
- add_segments(sc, [((x0,y0),(x1,y1)), ...], width, color, z=0.0) — many hairlines in one object.
- add_rect(sc, x, y, w, h, color, z=0.0) — flat fill (corner at x,y); add_outline_rect.
- add_disc(sc, x, y, r, color, z=0.0), add_uv_sphere, add_cylinder, add_box, add_torus.
- measure(sc, text, font, size), space_width, layout_chars(sc, text, font, size, x, y),
  add_lyric(sc, "sudden drop", x, y, font_key, size) + sync_words(sc, objs) for a full line.
- core.frame_of(sc, song_t), core.time_of(sc, frame) convert song seconds to scene frames.
- core.show_at(ob, frame, visible) — hard on/off (most slams).
- core.color_at(ob, frame, color) — keyframe object colour (dim -> sung).
- core.key(ob, "scale"/"location"/"rotation_euler", frame, value) + core.set_interp(ob, "BEZIER"/"LINEAR").
- core.bake(ob, "location", fn, f0, f1) for per-frame motion.
- core.ease_* and core.keys(t, [(t,v,ease), ...]); hash01 for deterministic randomness.
- motifs.mono, motifs.rule, motifs.crop_marks, motifs.readout, motifs.mask2d, motifs.spark, motifs.ring,
  motifs.stage3d, motifs.perspective.

Font keys: archivo (900), archivo700/500/300, archivo_w62_900 (condensed), archivo_w75_900,
archivo_w87_900, archivo_w112_900, archivo_w125_900, archivo_italic, mono, mono_med,
mono_light, mono_semi, mono_bold, mono_italic, serif, serif600, serif_italic, serif_italic600.

3D plates:

- core.add_camera_persp(sc, loc, target, lens=55), cam.data.dof.use_dof=True; focus_distance, aperture_fstop.
- core.mat_hatch_lit(base, line, scale=25, angle=0, distortion=1.6, rough=.55, rim=.6, rim_color=PAL["ember"])
  — engraved surfaces under real area lights (use motifs.stage3d).
- core.mat_lit(color, rough, metal) for plain shaded surfaces.
- core.mat_hatch(...) is self-lit (emission) hatching; use for graphic surfaces that must not shade.
- EEVEE motion blur is on; animated geometry leaves streaks. Keep the shutter at 0.32.

## Timing and sync

- Scene windows: each scene is its own Blender scene named like loss, hook1, prompt2; frames 1..N.
  sc.frame_end is already correct; t = data.frame_to_time(sc.name, frame) gives song seconds.
- Lyric data: data.line("There was a sudden drop"), data.words(...), data.word_start(...). Word
  dicts have w, start, end. Never hardcode lyric times; use the data.
- Beats: data.BEATS, data.DOWNBEATS, data.beats_between(t0,t1), data.env("vocal", t),
  data.hit("kick", t). Cut/move on beats, land big changes on downbeats.
- P(doom): data.pdoom(t) -> float, data.pdoom_text(t) -> "0.15"/"0.42"/"0.81"/"0.99". Stage it in-world.
- The scene ends where the timeline cuts; do not animate past sc.frame_end.

## Build & preview

    "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup --python blender/build.py -- loss --stills 1,60,120,200

    ... -- loss --stills 1,60,120 --scale 0.5      # half-res preview

    python tools\sheet.py out\wip\loss out\wip\loss_sheet.jpg

    blender -b out\blend\loss.blend -a            # full animation (only if you really need motion)
    ffmpeg -y -framerate 30 -i out\frames\loss\%04d.png -c:v libx264 -crf 18 -pix_fmt yuv420p out\clips\loss.mp4

build.py saves out/blend/<scene>.blend and renders stills to out/wip/<scene>/f####.png.
Look at the PNGs yourself (read_image) after every build. Check at 100% zoom for clipped type,
overlaps, unreadable lyrics, incorrect colours, empty frames, and black frames.

## Rules

1. Only create/edit your own scene module and helper files named scenes/<yourplate>-*.py.
   Do not edit blender/pdoom/*.py, build.py, or another agent's scenes. If the toolkit needs a fix,
   work around it locally or report it; do not modify shared code.
2. Deterministic: no Math.random/random.random; use hash01/fixed seeds. Animations must be a pure
   function of song time so re-renders match.
3. Performance: target < 1.2 s/frame at 1080p / 32 samples. Avoid > 150k curve segments, > 200 text objects,
   or huge particle counts. Prefer instancing/merged curves.
4. No new fonts, no external images, no texture downloads. Everything procedural.
5. Keep lyrics readable: each sung line must appear in full and in the safe area. No lyric may be clipped
   by the frame or hidden behind geometry at the moment it is sung.
6. Use the signal orange sparingly; bone type must stay crisp (emission 1.0, bloom threshold 1.0).
7. A plate should have one strong idea, executed precisely, not five weak ones. Read the treatment's
   paragraph for your plate and pick the most cinematic expression of it.

## Deliverable

A working scenes/<plate>.py with build(name), out/blend/<plate>.blend, and at least 6 representative
full-res stills in out/wip/<plate>/ (one per key beat / lyric line). A short report: what you built,
what you'd fix next, and any toolkit limitations.