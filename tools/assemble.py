"""Encode scene clips, concatenate, add the song and the global grain/vignette.

    python tools/assemble.py [--force] [--only open,hook1] [--no-grain] [--no-audio]

Set FFMPEG to the ffmpeg executable if it is not on PATH.
"""
import argparse, os, shutil, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "blender"))
from pdoom import data
from pdoom.paths import find_ffmpeg

FF = find_ffmpeg()
FPS = data.FPS


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        print(" ".join(cmd)[:400])
        print(r.stdout[-1500:], r.stderr[-2500:])
        raise SystemExit(r.returncode)
    return r


def encode(scene, force=False):
    d = os.path.join(ROOT, "out", "frames", scene)
    outp = os.path.join(ROOT, "out", "clips", scene + ".mp4")
    n = data.SCENES[scene]["frames"]
    files = sorted(f for f in os.listdir(d) if f.endswith(".png")) if os.path.isdir(d) else []
    if len(files) < n:
        print("MISSING FRAMES", scene, len(files), "/", n)
        return False
    last = os.path.getmtime(os.path.join(d, files[-1]))
    if not force and os.path.exists(outp) and os.path.getmtime(outp) >= last:
        return True
    run([FF, "-y", "-hide_banner", "-loglevel", "error", "-framerate", str(FPS),
         "-start_number", "1", "-i", os.path.join(d, "%04d.png"),
         "-frames:v", str(n), "-c:v", "libx264", "-preset", "fast", "-crf", "14",
         "-pix_fmt", "yuv420p", outp])
    print("CLIP", scene, n)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--no-grain", action="store_true")
    a = ap.parse_args()
    if not FF:
        raise SystemExit("ffmpeg not found. Install ffmpeg and put it on PATH, or set FFMPEG=/path/to/ffmpeg.")
    scenes = a.only.split(",") if a.only else data.SCENE_ORDER
    os.makedirs(os.path.join(ROOT, "out", "clips"), exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as ex:
        results = list(ex.map(lambda s: encode(s, a.force), scenes))
    if not all(results):
        raise SystemExit("some scenes are incomplete")
    listing = os.path.join(ROOT, "out", "clips", "concat.txt")
    with open(listing, "w", encoding="utf-8") as f:
        for s in scenes:
            f.write(f"file '{os.path.join(ROOT, 'out', 'clips', s + '.mp4').replace(chr(92), '/')}'\n")
    silent = os.path.join(ROOT, "out", "pdoom_silent.mp4")
    run([FF, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", listing, "-c", "copy", silent])
    final = os.path.join(ROOT, "out", "pdoom_blender.mp4")
    vf = [] if a.no_grain else ["noise=alls=4:allf=t+u"]
    vf.append("vignette=PI/7")
    cmd = [FF, "-y", "-hide_banner", "-loglevel", "error", "-i", silent]
    if not a.no_audio:
        cmd += ["-i", os.path.join(ROOT, "pdoom-video", "audio", "pdoom.mp3")]
    cmd += ["-vf", ",".join(vf), "-c:v", "libx264", "-preset", "medium", "-crf", "17",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    if not a.no_audio:
        cmd += ["-c:a", "aac", "-b:a", "192k"]
    total = sum(data.SCENES[s]["frames"] for s in data.SCENE_ORDER) / FPS
    cmd += ["-t", f"{total:.3f}", final]
    run(cmd)
    proxy = os.path.join(ROOT, "out", "pdoom_preview.mp4")
    run([FF, "-y", "-hide_banner", "-loglevel", "error", "-i", final,
         "-vf", "scale=960:540", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
         "-c:a", "aac", "-b:a", "128k", proxy])
    print("FINAL", final)
    print("PREVIEW", proxy)


if __name__ == "__main__":
    main()