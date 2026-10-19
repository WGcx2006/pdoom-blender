# v1.0.0 — Blender reconstruction

The first public release of a Blender-rendered reconstruction of
[mexicat/pdoom-video](https://github.com/mexicat/pdoom-video).

## Assets

- `pdoom-blender-1080p.mp4` — the full film, 1920×1080 / 30 fps / 156.73 s, H.264 + AAC,
  ~172 MB. Non-commercial demonstration; song and lyrics remain with their authors.
- `pdoom-preview-540p.mp4` — 960×540 preview with audio, ~20 MB.
- `poster.jpg` — 1920×1080 poster / social card.
- `docs/highlight.mp4` — 31 s silent highlight, in the repository.

## What is in the repository

- A small Python toolkit for Blender 5.2 / EEVEE: deterministic scenes, typography with
  measured kerning, line art, hatching, cameras, compositing.
- 17 scene modules producing the 22 plates of the edit, plus the timeline in
  `blender/pdoom/data.py`.
- Build, render, encode, QC and contact-sheet tools.
- Documentation of the pipeline, the 22 plates and the review passes.

## Reproduce

    python scripts/fetch_source.py
    python scripts/check_env.py
    python tools/render_all.py --workers 3
    python tools/assemble.py

Requires Blender 5.2, ffmpeg/ffprobe, Python 3.10+ and Pillow.

## Known issues

- 30 fps; the original is 60 fps.
- Some engraved surfaces are approximate planar hatching, not a raymarched shader.
- A few plates run warmer/busier than the reference.
- The end card returns to the opening imagery, but is not a pixel-perfect loop.

## Credits

Original project and edit: mexicat/pdoom-video (MIT).
Song: "I'm Upping My P(doom)" — lyrics by osmarks, opening verse/chorus by MusicPerson;
Claude-Pop Suno version posted by deckard. Not covered by this repository's license.
Fonts: Archivo, IBM Plex Mono, Cormorant Garamond (SIL OFL), loaded from the original project.
Code, Blender scenes, renders and documentation: MIT, 2026 WGcx2006 and contributors.
