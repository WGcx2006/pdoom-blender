#!/usr/bin/env python3
"""Fetch the source assets used by this reconstruction.

This project does not redistribute the song, the fonts or the original timing data.
It reads them from a local checkout of mexicat/pdoom-video, pinned to the commit the
reconstruction was built against:

    python scripts/fetch_source.py

Creates ./pdoom-video/ with data/, audio/ and app/public/fonts/.
"""
import argparse, os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = "https://github.com/mexicat/pdoom-video.git"
PIN = "fa164b74fd0b26a99375715b619c55b4a0fb3d05"


def run(cmd, cwd=None):
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default=os.path.join(ROOT, "pdoom-video"))
    ap.add_argument("--commit", default=PIN)
    a = ap.parse_args()
    if not shutil.which("git"):
        raise SystemExit("git is required")
    dest = os.path.abspath(a.dest)
    if not os.path.isdir(os.path.join(dest, ".git")):
        if os.path.isdir(dest):
            raise SystemExit(f"{dest} exists but is not a git checkout; move it away first")
        run(["git", "clone", SRC, dest])
    run(["git", "fetch", "--all", "--tags"], cwd=dest)
    run(["git", "checkout", a.commit], cwd=dest)
    need = [
        os.path.join(dest, "data", "lyrics.json"),
        os.path.join(dest, "data", "audio.json"),
        os.path.join(dest, "app", "public", "fonts"),
        os.path.join(dest, "audio", "pdoom.mp3"),
    ]
    missing = [p for p in need if not os.path.exists(p)]
    if missing:
        raise SystemExit("source checkout is incomplete: " + ", ".join(missing))
    print("\nOK:", dest)
    print("The song and lyrics are not covered by this project's MIT license.")


if __name__ == "__main__":
    main()
