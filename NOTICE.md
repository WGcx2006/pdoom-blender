# Notices and third-party credits

## Original project

This is an independent **Blender reconstruction** of
[mexicat/pdoom-video](https://github.com/mexicat/pdoom-video) (MIT), pinned at commit
`fa164b74fd0b26a99375715b619c55b4a0fb3d05`.

The original is a TypeScript + three.js WebGL music video. This repository does not
vendor that codebase; `scripts/fetch_source.py` checks it out locally so this project can
read its timing data, fonts and audio. The treatment and the edit were studied closely;
the Blender scenes, toolkit and renders here are new work.

Original project license: MIT. Copyright its authors.

## Song and lyrics

**"I'm Upping My P(doom)"** — lyrics by [osmarks](https://docs.osmarks.net/hypha/p%28doom%29_song_objectively_correct_interpretation),
built on an opening verse and chorus by [MusicPerson](https://www.udio.com/creators/MusicPerson),
with lines suggested on the EleutherAI Discord. The original was made with Udio (November 2024);
this film uses the "Claude-Pop" Suno version posted by deckard (@slimer48484).

The song and lyrics are **not** covered by this repository's MIT license. They belong to
their authors. This repository does not contain the audio or the aligned lyric data; the
fetch script obtains them from the original project for local rendering. The demonstration
video attached to the GitHub Release is non-commercial and exists to show the renderer;
all rights remain with the rights holders. Takedown requests will be honoured.

## Fonts

Archivo, IBM Plex Mono and Cormorant Garamond, licensed under the SIL Open Font License.
The static instances are loaded from the original project's `app/public/fonts/` by the
fetch script; they are not redistributed here. See the original repository for the OFL text.

## Our license

The Blender toolkit, scene modules, tools and documentation in this repository are
released under the MIT License (see `LICENSE`). Render stills and the silent highlight in
`docs/` are our own renders and are covered by the same license, subject to the note above
about the underlying song and lyrics.
