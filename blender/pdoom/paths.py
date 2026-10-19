"""Locate external executables without requiring a specific shell setup."""
import glob, os, shutil


def find_blender():
    p = os.environ.get("BLENDER")
    if p and os.path.exists(p):
        return p
    p = shutil.which("blender")
    if p:
        return p
    # common Windows installs, newest first
    hits = glob.glob(r"C:\Program Files\Blender Foundation\Blender *\blender.exe")
    hits += glob.glob(r"C:\Program Files\Blender Foundation\Blender\blender.exe")
    hits.sort(reverse=True)
    if hits:
        return hits[0]
    mac = "/Applications/Blender.app/Contents/MacOS/Blender"
    if os.path.exists(mac):
        return mac
    for cand in ("/usr/bin/blender", "/usr/local/bin/blender"):
        if os.path.exists(cand):
            return cand
    return None


def find_ffmpeg():
    return os.environ.get("FFMPEG") or shutil.which("ffmpeg")
