"""Fallback plate: a precise lyric card for any timeline window (safety net)."""
import bpy, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pdoom import core, data, motifs
from pdoom.core import PAL, clamp, lerp, smoothstep, ease_out_expo

INK, BONE, SIG, EMB, GRAPH, ASH, BLOOD = PAL["ink"], PAL["bone"], PAL["signal"], PAL["ember"], PAL["graphite"], PAL["ash"], PAL["blood"]


def build(name):
    info = data.SCENES[name]
    sc = core.new_scene(name, samples=24, motion_blur=True)
    core.add_bg(sc)
    cam = core.add_camera_ortho(sc, 19.2)
    sc.frame_set(1)
    # graph paper
    segs = []
    for i in range(-16, 17):
        x = i * 1.2
        segs.append(((x, -5.3), (x, 5.3)))
    for j in range(-8, 9):
        y = j * 1.2
        segs.append(((-9.5, y), (9.5, y)))
    core.add_segments(sc, segs, 0.005, core.sc_x(BONE, 0.035), z=-2)
    motifs.mono(sc, f"PLATE {name.upper()}  ·  P(DOOM) {data.pdoom_text(info['start'] + 0.5)}", -9.2, 4.8, 0.14, core.sc_x(BONE, 0.5))
    core.add_polyline(sc, [(-9.25, 4.6), (9.25, 4.6)], 0.008, core.sc_x(BONE, 0.2))
    # a large quiet figure
    for k in range(7):
        motifs.ring(sc, -4.5, 0.2, 1.2 + k * 0.55, core.sc_x(SIG, 0.22 - k * 0.02), 0.007, z=-1)
    motifs.mono(sc, "SIGNAL ACQUIRED", -9.2, -4.75, 0.11, core.sc_x(BONE, 0.3))
    # lyrics whose lines fall in this window
    lines = [l for l in data.LINES if info["start"] - 0.3 <= l["start"] < info["end"]]
    y = -2.2
    for l in lines[:2]:
        objl, objs, w = core.add_lyric(sc, l["text"][:36], -8.95, y, "archivo", 0.9, color=BONE, max_width=17.2, name=f"f{l['i']}")
        core.sync_words(sc, objs)
        y -= 1.1
    motifs.readout(sc, -9.2, -2.9, data.pdoom_text(info["start"] + 1), data.pdoom(info["start"] + 1), 1.0)
    def path(t):
        k = clamp((t - info["start"]) / max(0.5, (info["end"] - info["start"])))
        return (lerp(-8.0, 7.0, k), lerp(2.6, -3.6, k))
    motifs.spark(sc, path, info["start"], info["end"] - 0.1, 0.10)
    return sc
