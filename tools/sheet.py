"""Contact sheet from a folder of PNG stills.

    python tools/sheet.py out/wip/open out/open_sheet.jpg
"""
import argparse, glob, os
from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("out")
    ap.add_argument("--cols", type=int, default=3)
    a = ap.parse_args()
    files = sorted(glob.glob(os.path.join(a.folder, "*.png")))
    if not files:
        raise SystemExit("no PNGs in " + a.folder)
    cols = min(a.cols, len(files))
    tw = 640
    ims = [Image.open(f).convert("RGB") for f in files]
    th = int(tw * ims[0].height / ims[0].width)
    rows = (len(files) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * (th + 22)), (10, 10, 10))
    dr = ImageDraw.Draw(sheet)
    for i, (f, im) in enumerate(zip(files, ims)):
        r, c = divmod(i, cols)
        sheet.paste(im.resize((tw, th), Image.LANCZOS), (c * tw, r * (th + 22) + 22))
        dr.text((c * tw + 6, r * (th + 22) + 4), os.path.basename(f), fill=(255, 120, 40))
    sheet.save(a.out, quality=90)
    print(a.out, sheet.size)


if __name__ == "__main__":
    main()
