# Contributing

This is a small, deterministic renderer. Contributions are welcome, but keep the look and
the reproducibility intact.

## Setup

    python scripts/fetch_source.py
    python scripts/check_env.py

You need Blender 5.2 (EEVEE), ffmpeg/ffprobe, Python 3.10+ and Pillow.
Set `BLENDER` and `FFMPEG` if they are not on PATH.

## Adding or changing a plate

- One scene module in `blender/scenes/`, exporting `build(name)`.
- Use `pdoom.core.new_scene(name)`; it sets 1920x1080, 30 fps, EEVEE, motion blur and the
  standard compositor.
- Read `blender/STYLE.md` first. Palette, typography, safe margins and the word-sync rules
  are not optional.
- Times come from `pdoom.data` (lyrics, beats, sections); never hardcode lyric times.
- Keep animation a pure function of song time. Use `hash01`, never `random`/`time`.
- Render stills at key beats, inspect them at 100%, then open a PR with 4-8 stills and the
  scene window.

## Checklist

- [ ] `python -m compileall -q blender tools scripts` passes.
- [ ] `python tools/render_all.py --only <plate> --workers 1` completes.
- [ ] No text leaves the title-safe area at the moment it is sung.
- [ ] No new fonts, images, textures or external downloads.
- [ ] No audio, lyric data or font files added to git.
- [ ] The scene renders under ~2 s/frame at 1080p on the contributor's machine.

## Licensing

By contributing you agree that your code is MIT-licensed. Do not contribute the song,
lyrics, original project code, fonts or other third-party assets. See `NOTICE.md`.
