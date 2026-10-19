"""Build one plate and optionally render preview stills.

Usage:
  blender -b --factory-startup --python blender/build.py -- hook1 --stills 1,20,41
  blender -b --factory-startup --python blender/build.py -- open --times 1.4,4.2,8.0
"""
import bpy, sys, os, argparse, importlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pdoom import core, data  # noqa: E402

MODULES = {
    "loss": "loss", "open": "open", "hook1": "hook", "hook2": "hook", "hook3": "hook", "hook4": "hook",
    "prompt1": "prompt", "prompt2": "prompt", "prompt3": "prompt",
    "room": "room", "shoggoth": "shoggoth", "spacetime": "spacetime", "ascent": "ascent",
    "bureau": "bureau", "leftturn": "leftturn", "paperclips": "paperclips", "fuse": "fuse",
    "stack": "stack", "dense": "dense", "loom": "loom", "ilya": "ilya", "outro": "outro",
}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    name = argv[0]
    p = argparse.ArgumentParser()
    p.add_argument("name")
    p.add_argument("--stills", default="")
    p.add_argument("--times", default="")
    p.add_argument("--samples", type=int, default=0)
    p.add_argument("--scale", type=float, default=1.0)
    p.add_argument("--no-save", action="store_true")
    a = p.parse_args(argv)

    mod_name = MODULES[a.name]
    if not os.path.exists(os.path.join(HERE, "scenes", mod_name + ".py")):
        print("FALLBACK", a.name)
        mod_name = "_fallback"
    mod = importlib.import_module(f"scenes.{mod_name}")
    sc = mod.build(a.name)
    if a.samples:
        sc.eevee.taa_render_samples = a.samples
    if a.scale != 1.0:
        sc.render.resolution_percentage = int(round(100 * a.scale))
    if not a.no_save:
        core.save_blend(sc, os.path.join(core.OUT, "blend", a.name + ".blend"))

    frames = []
    if a.stills:
        frames += [int(x) for x in a.stills.split(",") if x.strip()]
    if a.times:
        frames += [data.time_to_frame(a.name, float(x)) for x in a.times.split(",") if x.strip()]
    if frames:
        outdir = os.path.join(core.OUT, "wip", a.name)
        core.render_stills(sc, frames, outdir)
        print("STILLS", outdir, frames)
    print("BUILD_OK", a.name, "frames", sc.frame_start, sc.frame_end)


main()