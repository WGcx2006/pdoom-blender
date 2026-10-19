"""Build and render every plate.

    python tools/render_all.py --workers 3 [--only open,hook1] [--skip-existing]

Set BLENDER to the Blender executable if it is not on PATH.
"""
import argparse, os, shutil, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "blender"))
from pdoom import data
from pdoom.paths import find_blender

BLENDER = find_blender()

MODULES = {
    "open": "open", "loss": "loss",
    "prompt1": "prompt", "prompt2": "prompt", "prompt3": "prompt",
    "hook1": "hook", "hook2": "hook", "hook3": "hook", "hook4": "hook",
    "room": "room", "shoggoth": "shoggoth", "spacetime": "spacetime", "ascent": "ascent",
    "bureau": "bureau", "leftturn": "leftturn", "paperclips": "paperclips", "fuse": "fuse",
    "stack": "stack", "dense": "dense", "loom": "loom", "ilya": "ilya", "outro": "outro",
}


def build(scene):
    blend = os.path.join(ROOT, "out", "blend", scene + ".blend")
    modfile = os.path.join(ROOT, "blender", "scenes", MODULES[scene] + ".py")
    if os.path.exists(blend) and os.path.exists(modfile) and os.path.getmtime(blend) > os.path.getmtime(modfile):
        return blend
    cmd = [BLENDER, "-b", "--factory-startup", "--python", os.path.join(ROOT, "blender", "build.py"), "--", scene]
    print("BUILD", scene, flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-3000:], r.stderr[-3000:], flush=True)
        raise SystemExit(f"build failed: {scene}")
    return blend


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--only", default="")
    ap.add_argument("--skip-existing", action="store_true")
    a = ap.parse_args()
    if not BLENDER:
        raise SystemExit("Blender not found. Install Blender 5.2 and put it on PATH, or set BLENDER=/path/to/blender.")
    if not os.path.isdir(os.path.join(ROOT, "pdoom-video")):
        raise SystemExit("pdoom-video/ is missing. Run: python scripts/fetch_source.py")
    scenes = a.only.split(",") if a.only else data.SCENE_ORDER
    todo = []
    for s in scenes:
        blend = build(s)
        n = data.SCENES[s]["frames"]
        d = os.path.join(ROOT, "out", "frames", s)
        have = len([f for f in os.listdir(d) if f.endswith(".png")]) if os.path.isdir(d) else 0
        if a.skip_existing and have >= n:
            print("SKIP", s, have, flush=True)
            continue
        todo.append((s, blend, n))
    print("TO RENDER", [(s, n) for s, _, n in todo], flush=True)
    running = []
    t0 = time.time()
    while todo or running:
        while todo and len(running) < a.workers:
            s, blend, n = todo.pop(0)
            log = open(os.path.join(ROOT, "out", f"render_{s}.log"), "w")
            p = subprocess.Popen([BLENDER, "-b", blend, "-a"], stdout=log, stderr=subprocess.STDOUT)
            print("START", s, n, flush=True)
            running.append((s, p, log, time.time()))
        time.sleep(2)
        for item in list(running):
            s, p, log, st = item
            if p.poll() is not None:
                log.close()
                print("DONE", s, "rc", p.returncode, "sec", round(time.time() - st), flush=True)
                running.remove(item)
    print("ALL RENDERED", round(time.time() - t0), "s", flush=True)


if __name__ == "__main__":
    main()