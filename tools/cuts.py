"""Make a contact sheet of all 45 scene in/out boundaries from the final film.

    python tools/cuts.py
"""
import os, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/blender")
from pdoom import data
from pdoom.paths import find_ffmpeg
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FF = find_ffmpeg()


def main():
    if not FF:
        raise SystemExit("ffmpeg not found")
    video = os.path.join(ROOT, "out", "pdoom_blender.mp4")
    if not os.path.exists(video):
        raise SystemExit("render the film first: python tools/assemble.py")
    tmp = os.path.join(ROOT, "out", "cuts")
    os.makedirs(tmp, exist_ok=True)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    times = []
    for s in data.SCENE_ORDER:
        st = data.SCENES[s]["start"]
        en = data.SCENES[s]["end"]
        times.append((s, "in", max(0, st + 0.05)))
        times.append((s, "out", max(0, en - 0.06)))
    for i, (s, tag, t) in enumerate(times):
        subprocess.run([FF, "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", video,
                        "-frames:v", "1", os.path.join(tmp, f"{i:02d}.jpg")], check=True)
    files = sorted(os.listdir(tmp))
    ims = [Image.open(os.path.join(tmp, f)).convert("RGB") for f in files]
    tw, cols = 320, 6
    th = int(tw * ims[0].height / ims[0].width)
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * (th + 18)), (8, 8, 8))
    d = ImageDraw.Draw(sheet)
    for i, im in enumerate(ims):
        r, c = divmod(i, cols)
        sheet.paste(im.resize((tw, th), Image.LANCZOS), (c * tw, r * (th + 18) + 18))
        s, tag, t = times[i]
        d.text((c * tw + 4, r * (th + 18) + 3), f"{s} {tag} {t:.1f}s", fill=(255, 120, 40))
    out = os.path.join(ROOT, "out", "cuts_sheet.jpg")
    sheet.save(out, quality=90)
    print(out, sheet.size)


if __name__ == "__main__":
    main()