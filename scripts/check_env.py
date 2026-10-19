#!/usr/bin/env python3
"""Check the tools and assets needed to build the film."""
import importlib.util, os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "blender"))
from pdoom.paths import find_blender, find_ffmpeg
BLENDER = find_blender()
FFMPEG = find_ffmpeg()
FFPROBE = shutil.which("ffprobe")


def ok(name, value):
    print(("  OK   " if value else "  MISS ") + name)


def main():
    print("Python", sys.version.split()[0])
    ok("Pillow", importlib.util.find_spec("Pillow") is not None)
    ok(f"Blender ({BLENDER or 'not on PATH'})", bool(BLENDER))
    ok(f"ffmpeg ({FFMPEG or 'not on PATH'})", bool(FFMPEG))
    ok("ffprobe", bool(FFPROBE))
    vendor = os.path.join(ROOT, "pdoom-video")
    data = os.path.join(vendor, "data", "lyrics.json")
    fonts = os.path.join(vendor, "app", "public", "fonts")
    audio = os.path.join(vendor, "audio", "pdoom.mp3")
    ok("pdoom-video/data/lyrics.json", os.path.exists(data))
    ok("pdoom-video/data/audio.json", os.path.exists(os.path.join(vendor, "data", "audio.json")))
    ok("pdoom-video/app/public/fonts", os.path.exists(fonts))
    ok("pdoom-video/audio/pdoom.mp3", os.path.exists(audio))
    if BLENDER:
        try:
            r = subprocess.run([BLENDER, "--version"], capture_output=True, text=True, timeout=20)
            print("  Blender:", (r.stdout or r.stderr).splitlines()[0])
        except Exception as e:
            print("  Blender check failed:", e)
    print("\nNext:")
    print("  python scripts/fetch_source.py          # if pdoom-video/ is missing")
    print("  python tools/render_all.py --workers 3  # all frames")
    print("  python tools/assemble.py                # mp4 with audio")


if __name__ == "__main__":
    main()