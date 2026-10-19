"""QA: sample frames per scene, flag black/flat frames, make review contact sheets."""
import os, sys, subprocess, shutil, json
from PIL import Image, ImageDraw, ImageStat

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "blender"))
from pdoom import data
from pdoom.paths import find_ffmpeg
FF = find_ffmpeg()


def scene_stats():
    rows = []
    for s in data.SCENE_ORDER:
        d = os.path.join(ROOT, "out", "frames", s)
        n = data.SCENES[s]["frames"]
        if not os.path.isdir(d):
            rows.append((s, 0, n, None, None, None))
            continue
        files = sorted(f for f in os.listdir(d) if f.endswith(".png"))
        sample = files[:: max(1, len(files) // 8)][:8] if files else []
        means = []
        for f in sample:
            im = Image.open(os.path.join(d, f)).convert("L")
            means.append(ImageStat.Stat(im).mean[0])
        rows.append((s, len(files), n, min(means) if means else None, max(means) if means else None,
                     sum(means) / len(means) if means else None))
    print(f"{'scene':12} {'have':>5} {'want':>5} {'min':>6} {'max':>6} {'mean':>6}")
    for r in rows:
        print(f"{r[0]:12} {r[1]:5d} {r[2]:5d} " + (f"{r[3]:6.1f} {r[4]:6.1f} {r[5]:6.1f}" if r[3] is not None else "   -      -      -"))
    return rows


def video_sheet(video, out, n=24, cols=4):
    tmp = os.path.join(ROOT, "out", "qa_frames")
    os.makedirs(tmp, exist_ok=True)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    dur = data.DURATION
    for i in range(n):
        t = (i + 0.5) / n * dur
        subprocess.run([FF, "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1",
                        os.path.join(tmp, f"{i:02d}.jpg")], check=True)
    files = sorted(os.listdir(tmp))
    ims = [Image.open(os.path.join(tmp, f)).convert("RGB") for f in files]
    w, h = ims[0].size
    tw = 480
    th = int(tw * h / w)
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * (th + 20)), (8, 8, 8))
    d = ImageDraw.Draw(sheet)
    for i, im in enumerate(ims):
        r, c = divmod(i, cols)
        sheet.paste(im.resize((tw, th), Image.LANCZOS), (c * tw, r * (th + 20) + 20))
        d.text((c * tw + 4, r * (th + 20) + 4), f"{(i + 0.5) / n * dur:.1f}s", fill=(255, 120, 40))
    sheet.save(out, quality=90)
    print("SHEET", out, sheet.size)


if __name__ == "__main__":
    scene_stats()
    p = os.path.join(ROOT, "out", "pdoom_preview.mp4")
    if os.path.exists(p):
        video_sheet(p, os.path.join(ROOT, "out", "qa_sheet.jpg"))