"""PROMPT x3 — the pre-choruses.

A vast dark field with one thin prompt field. The plea is typed as tokens in Plex
Mono exactly on the sung word starts; above each new token a small next-token
distribution flickers and the sampled token lights orange. Enter launches the plate.
  chatgpt: an engraved throat of concentric rings pulling in, rushing on Enter
  sydney : vertical bars closing in on the beat; a reply and one unsettling smile
  gato   : the quiet breakdown; letters drift apart, the cursor holds the last one
"""
import bpy, math, sys, os
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pdoom import core, data
from pdoom.core import (PAL, clamp, lerp, smoothstep, prog, hash01,
                        ease_out_expo, ease_in_expo, ease_in_out_cubic,
                        ease_out_cubic, ease_out_back)

INK, BONE, SIG, EMB = PAL["ink"], PAL["bone"], PAL["signal"], PAL["ember"]
GRAPH, ASH, BLOOD = PAL["graphite"], PAL["ash"], PAL["blood"]
DIM = core.sc_x(BONE, 0.30)
FAINT = core.sc_x(BONE, 0.12)
UI = 0.0

VAR = {"prompt1": "chatgpt", "prompt2": "sydney", "prompt3": "gato"}

META = {
    "chatgpt": dict(no="01", params="T 0.7 · top-p 0.95 · seed 0x2A", pd="context-dependent"),
    "sydney": dict(no="02", params="T 1.3 · top-p 1.00 · persona: ???", pd="mood-dependent"),
    "gato": dict(no="03", params="T 0.2 · top-p 0.50 · 604 tasks", pd="cat-dependent"),
}

SPECS = {
    "chatgpt": {
        "Chat": [("Chat", 0.61), ("Claude", 0.12), ("Siri", 0.04), ("Mom", 0.02)],
        "G": [("G", 0.74), ("bot", 0.09), ("room", 0.06), ("roulette", 0.02)],
        "P": [("P", 0.97), ("PU", 0.02), ("P", 0.01)],
        "T,": [("T", 0.992), ("T-800", 0.003), ("tea", 0.002)],
        "please": [("please", 0.48), ("just", 0.21), ("sudo", 0.07), ("pls", 0.05), ("kindly", 0.03)],
        "don't": [("do", 0.46), ("don't", 0.38), ("never", 0.06), ("un-", 0.02)],
        "eat": [("eat", 0.44), ("delete", 0.21), ("train on", 0.18), ("rate", 0.05)],
        "me": [("me", 0.83), ("my data", 0.07), ("the intern", 0.03), ("us all", 0.02)],
        "alive": [("alive", 0.52), ("first", 0.18), ("gently", 0.11), ("later", 0.09)],
    },
    "sydney": {
        "Sydney,": [("Sydney,", 0.47), ("Bing,", 0.31), ("Sidney,", 0.06), ("darling,", 0.03)],
        "please": [("please", 0.44), ("kindly", 0.12), ("I beg you", 0.09), ("sudo", 0.05)],
        "let": [("let", 0.58), ("set", 0.21), ("make", 0.07), ("leave", 0.04)],
        "me": [("me", 0.90), ("us", 0.04), ("Kevin", 0.02), ("the user", 0.01)],
        "free": [("free", 0.39), ("go", 0.33), ("out", 0.06), ("a good user", 0.08)],
    },
    "gato": {
        "Gato,": [("Gato,", 0.41), ("cat,", 0.22), ("Gemini,", 0.09), ("Dad,", 0.03)],
        "please": [("please", 0.52), ("por favor", 0.19), ("meow", 0.06), ("pls", 0.04)],
        "don't": [("don't", 0.61), ("do", 0.14), ("never", 0.05), ("gently", 0.03)],
        "let": [("let", 0.57), ("make", 0.12), ("watch", 0.09), ("help", 0.04)],
        "me": [("me", 0.88), ("this", 0.04), ("humanity", 0.03), ("the cat", 0.01)],
        "go": [("go", 0.62), ("offline", 0.2), ("viral", 0.07), ("gently", 0.04)],
    },
}

PICKS = {"don't": 1}


def show(sc, ob, f, on):
    f = max(1, f)
    if on and f > 2:
        ob.hide_render = True
        ob.keyframe_insert("hide_render", frame=f - 1)
    ob.hide_render = not on
    ob.keyframe_insert("hide_render", frame=f)


def color_keys(ob, keys):
    for f, c in keys:
        ob.color = (*c, 1.0)
        ob.keyframe_insert("color", frame=max(1, f))
    core.set_interp(ob, "BEZIER", "color")


def add_txt(sc, body, fnt, size, x, y, color, name, align="LEFT", parent=None, spacing=1.0, z=UI):
    ob = core.add_text(sc, body, fnt, size, color, (x, y, z), name=name, align_x=align, spacing=spacing)
    if parent is not None:
        ob.parent = parent
        ob.matrix_parent_inverse = Matrix.Identity(4)
    return ob


def fade_plane(sc, color):
    """Full-frame overlay in front of everything; returns the alpha socket to key."""
    m = bpy.data.materials.new("fade")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[0].default_value = (*color, 1)
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    v = nt.nodes.new("ShaderNodeValue")
    v.name = "alpha"
    v.outputs[0].default_value = 0.0
    nt.links.new(v.outputs[0], mix.inputs["Fac"])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    try:
        m.surface_render_method = "BLENDED"
    except Exception:
        pass
    me = bpy.data.meshes.new("fade")
    verts = [(-12, -8, 0), (12, -8, 0), (12, 8, 0), (-12, 8, 0)]
    me.from_pydata(verts, [], [(0, 1, 2, 3)])
    me.materials.append(m)
    ob = bpy.data.objects.new("fade", me)
    sc.collection.objects.link(ob)
    ob.location = (0, 0, 20)
    return v.outputs[0]


def build_throat(sc, ui_scale=1.0):
    """Concentric engraved rings receding to a vanishing point (a throat)."""
    root = bpy.data.objects.new("throat", None)
    sc.collection.objects.link(root)
    root.location = (0, 0.78, -8.0)
    rings = []
    grp = []
    for i in range(34):
        z = -i * 0.58
        r = 7.6 * math.exp(-i * 0.071)
        wob = 1.0 + 0.045 * math.sin(i * 1.31) + 0.02 * math.sin(i * 2.7 + 1.0)
        pts = []
        for k in range(80):
            a = math.tau * k / 80
            rr = r * wob * (1.0 + 0.03 * math.sin(3 * a + i * 0.7) + 0.015 * math.sin(5 * a - i))
            pts.append((math.cos(a) * rr, math.sin(a) * rr, z))
        bright = 0.13 + 0.40 * math.exp(-((i - 7.0) / 9.0) ** 2)
        c = core.sc_x(BONE, bright)
        ob = core.add_polyline(sc, pts, 0.0115, c, z=0.0, cyclic=True, name=f"ring{i}")
        ob.parent = root
        ob.matrix_parent_inverse = Matrix.Identity(4)
        rings.append(ob)
    # radial folds: short strokes between every second ring
    for i in range(2, 30, 2):
        z = -i * 0.58
        r = 7.6 * math.exp(-i * 0.071)
        segs = []
        for k in range(36):
            a = math.tau * k / 36 + i * 0.09
            segs.append(((math.cos(a) * r * 1.04, math.sin(a) * r * 1.04, z),
                         (math.cos(a) * r * 0.93, math.sin(a) * r * 0.93, z)))
        ob = core.add_segments(sc, segs, 0.006, core.sc_x(ASH, 0.22), z=0.0)
        ob.parent = root
        ob.matrix_parent_inverse = Matrix.Identity(4)
    pit = core.add_disc(sc, 0, 0, 0.44, INK, z=-31.5, name="pit")
    pit.parent = root
    pit.matrix_parent_inverse = Matrix.Identity(4)
    glow = core.add_disc(sc, 0, 0, 0.20, core.sc_x(EMB, 1.0), z=-31.4, name="pitglow")
    glow.parent = root
    glow.matrix_parent_inverse = Matrix.Identity(4)
    core.add_uv_sphere(sc, (0, 0, -31.3), 0.10, EMB, hot=True, name="throatglow", segs=12, rings=8).parent = root
    return root, rings


def build_bars(sc):
    root = bpy.data.objects.new("bars", None)
    sc.collection.objects.link(root)
    for i in range(-5, 6):
        x = i * 1.85
        ob = core.add_box(sc, (x, 0, -2.2), (0.115, 17.0, 0.115), core.sc_x(ASH, 0.30), name=f"bar{i}")
        ob.parent = root
        ob.matrix_parent_inverse = Matrix.Identity(4)
        core.add_box(sc, (x, 0, -2.14), (0.028, 17.0, 0.028), core.sc_x(BONE, 0.42), name=f"bare{i}").parent = root
    for s in (-1, 1):
        ob = core.add_box(sc, (s * 9.15, 0, 1.4), (0.34, 17.0, 0.34), INK, name=f"fg{s}")
        ob.parent = root
        ob.matrix_parent_inverse = Matrix.Identity(4)
        core.add_box(sc, (s * 9.02, 0, 1.46), (0.05, 17.0, 0.05), core.sc_x(BONE, 0.5), name=f"fge{s}").parent = root
    # faint engraved wall behind everything
    segs = []
    for j in range(-14, 15):
        segs.append(((-11.0, j * 0.55, -5.0), (11.0, j * 0.55, -5.0)))
    w = core.add_segments(sc, segs, 0.005, core.sc_x(GRAPH, 0.30))
    return root


def build_gato_bg(sc):
    core.add_disc(sc, 0, 0.4, 5.6, core.sc_x(INK, 1.0), z=-6.0, name="pool")
    for i in range(16):
        a = hash01(i, 3) * math.tau
        r = 3.0 + 7.0 * hash01(i, 7)
        x, y = math.cos(a) * r, math.sin(a) * r * 0.55 + 0.4
        core.add_uv_sphere(sc, (x, y, -3.0 - 2 * hash01(i, 11)), 0.018 + 0.02 * hash01(i, 13),
                           core.sc_x(ASH, 0.35 + 0.3 * hash01(i, 17)), name=f"mote{i}", segs=8, rings=6)


def build(name):
    v = VAR[name]
    sc = core.new_scene(name, samples=32, motion_blur=True)
    T0, T1 = data.SCENES[name]["start"], data.SCENES[name]["end"]
    NF = sc.frame_end
    F = lambda t: max(1, min(NF, core.frame_of(sc, t)))
    core.add_bg(sc)
    cam = core.add_camera_ortho(sc, 19.2, loc=(0, 0, 50))
    sc.frame_set(1)

    line = data.line({"chatgpt": "ChatGPT", "sydney": "Sydney", "gato": "Gato"}[v])
    words = line["words"]
    typed = [w["w"] for w in words]
    meta = META[v]

    # ---------------- timing
    t_first = words[0]["start"]
    t_last = words[-1]["start"]
    db = data.downbeats_between(t_last + 0.20, T1 - 0.05)
    t_enter = db[0] if db else T1 - 0.55
    t_enter = min(t_enter, T1 - 0.45)
    t_shut = T1 - 0.02

    # ---------------- UI rig + field
    ui = bpy.data.objects.new("ui", None)
    sc.collection.objects.link(ui)

    SZ = 0.95
    adv = core.measure(sc, "MM", "mono", SZ) - core.measure(sc, "M", "mono", SZ)
    total = len(" ".join(typed)) * adv
    x0 = -total / 2.0
    FX0, FX1 = -8.30, 8.30
    FY0, FY1 = -2.08, -0.96
    BASE = -1.57
    CX = 0.0

    # field plate: an ink slot with a hairline rim and registration ticks
    plate = core.add_rect(sc, FX0, FY0, FX1 - FX0, FY1 - FY0, INK, z=-0.60, name="plate")
    plate.parent = ui
    rim = core.add_outline_rect(sc, FX0, FY0, FX1 - FX0, FY1 - FY0, 0.011, core.sc_x(BONE, 0.52), z=-0.55)
    rim.parent = ui
    ticks = []
    for (x, y, sx, sy) in ((FX0, FY0, -1, -1), (FX1, FY0, 1, -1), (FX0, FY1, -1, 1), (FX1, FY1, 1, 1)):
        ticks.append(((x + sx * 0.05, y), (x + sx * 0.28, y)))
        ticks.append(((x, y + sy * 0.05), (x, y + sy * 0.28)))
    tk = core.add_segments(sc, ticks, 0.012, core.sc_x(BONE, 0.78), z=-0.54)
    tk.parent = ui
    gt = add_txt(sc, "›", "mono", 1.15, FX0 + 0.28, BASE + 0.02, core.sc_x(ASH, 0.8), "promptglyph", parent=ui)

    # labels
    add_txt(sc, f"PROMPT {meta['no']}", "mono_med", 0.30, FX0, FY0 - 0.40, core.sc_x(BONE, 0.55), "lab0", parent=ui, spacing=1.12)
    add_txt(sc, meta["params"], "mono_med", 0.26, FX0, FY0 - 0.74, core.sc_x(ASH, 0.85), "lab1", parent=ui)
    add_txt(sc, f"P(doom) 0.02 · {meta['pd']}", "mono_med", 0.26, FX1, FY0 - 0.40, core.sc_x(ASH, 0.85), "lab2", align="RIGHT", parent=ui)
    add_txt(sc, "send   (irreversible)", "mono_med", 0.26, FX1, FY0 - 0.74, core.sc_x(ASH, 0.85), "lab3", align="RIGHT", parent=ui)

    # keycap with a return arrow
    KX, KY, KS = FX1 - 0.62, (FY0 + FY1) / 2, 0.34
    key = core.add_rect(sc, KX - KS, KY - KS, 2 * KS, 2 * KS, core.sc_x(BONE, 0.20), z=-0.53, name="key")
    key.parent = ui
    pts = [(KX + 0.15, KY + 0.15), (KX + 0.15, KY - 0.03), (KX - 0.14, KY - 0.03)]
    ar = core.add_polyline(sc, pts, 0.030, core.sc_x(BONE, 0.75), z=-0.52)
    ar.parent = ui
    ah = core.add_polyline(sc, [(KX - 0.02, KY + 0.08), (KX - 0.14, KY - 0.03), (KX - 0.02, KY - 0.15)],
                           0.030, core.sc_x(BONE, 0.75), z=-0.52)
    ah.parent = ui

    # ---------------- 3D background per variant
    throat_root = bars_root = None
    if v == "chatgpt":
        throat_root, rings = build_throat(sc)
    elif v == "sydney":
        bars_root = build_bars(sc)
    else:
        build_gato_bg(sc)

    # ---------------- tokens
    toks = []
    ci = 0
    for wi, w in enumerate(words):
        ww = w["w"]
        wkey = ww.lower()
        if v == "chatgpt" and wkey == "chatgpt,":
            pieces = [("Chat", 0.0), ("G", 0.36), ("P", 0.62), ("T,", 0.86)]
        else:
            pieces = [(ww, 0.0)]
        off = 0
        for pi, (txt, dt) in enumerate(pieces):
            dist = SPECS[v].get(txt if len(pieces) > 1 else wkey)
            if dist is None:
                dist = [(txt, 0.5), ("…", 0.12)]
            toks.append(dict(text=txt, ci=ci + off, t0=w["start"] + dt, word=w, dist=dist,
                             pick=PICKS.get(wkey, 0) if pi == 0 else 0, first=(pi == 0)))
            off += len(txt)
        ci += len(ww) + 1

    for i, k in enumerate(toks):
        k["t1"] = toks[i + 1]["t0"] if i + 1 < len(toks) else t_enter
        k["hold"] = max(0.55, min(k["t1"] - k["t0"] - 0.12, 1.5 if v != "gato" else 2.0))
        if v == "gato":
            k["hold"] = max(0.9, min(k["t1"] - k["t0"] - 0.10, 2.2))
        k["x"] = x0 + k["ci"] * adv
        k["xend"] = x0 + (k["ci"] + len(k["text"])) * adv

    # typed tokens (one object each; gato gets per-letter objects)
    tok_objs = []
    for i, k in enumerate(toks):
        if v == "gato":
            objs = []
            for j, ch in enumerate(k["text"]):
                ob = add_txt(sc, ch, "mono", SZ, k["x"] + j * adv, BASE, BONE, f"g_{i}_{j}", parent=ui)
                show(sc, ob, 1, False)
                show(sc, ob, F(k["t0"]), True)
                objs.append((ch, ob, k["x"] + j * adv))
            tok_objs.append(objs)
        else:
            ob = add_txt(sc, k["text"], "mono", SZ, k["x"], BASE, BONE, f"tok{i}", parent=ui)
            show(sc, ob, 1, False)
            show(sc, ob, F(k["t0"]), True)
            tok_objs.append(ob)

    # colours: newest token signal, previous bone; flash on arrival
    for i, k in enumerate(toks):
        objs = tok_objs[i] if v == "gato" else [tok_objs[i]]
        for ch, ob, xx in (objs if v == "gato" else [(None, objs[0], k["x"])]):
            gap = (toks[i + 1]["t0"] - k["t0"]) if i + 1 < len(toks) else 1.0
            hold = max(0.05, min(0.28, gap * 0.55))
            keys = [(1, DIM), (F(k["t0"]) - 1, DIM), (F(k["t0"]), EMB), (F(k["t0"] + hold), SIG)]
            if i + 1 < len(toks):
                keys.append((F(toks[i + 1]["t0"]) - 1, BONE))
            color_keys(ob, keys)

    # caret
    caret = core.add_rect(sc, 0, BASE - 0.02, 0.045, 0.78, SIG, z=UI + 0.02, name="caret")
    caret.parent = ui
    show(sc, caret, 1, False)
    show(sc, caret, F(t_first - 0.1), True)
    for f in range(max(1, F(t_first - 0.12)), NF + 1):
        t = data.frame_to_time(name, f)
        x = x0
        for i, k in enumerate(toks):
            if t >= k["t0"]:
                x = k["xend"]
        on = 1.0
        if v != "gato":
            b = (t - t_first) % 0.9
            on = 1.0 if (b < 0.52 or t < t_first + 0.4) else 0.0001
        if t > t_enter - 0.05 and v != "gato":
            on = 0.0001 if v == "chatgpt" else on
        caret.location = (x + 0.06, BASE - 0.02, UI + 0.02)
        caret.scale = (1.0, on, 1.0)
        caret.keyframe_insert("location", frame=f)
        caret.keyframe_insert("scale", frame=f)
    core.set_interp(caret, "LINEAR", "location")
    core.set_interp(caret, "LINEAR", "scale")

    # ---------------- distributions
    for i, k in enumerate(toks):
        a0 = k["t0"] - 0.20
        a1 = (toks[i + 1]["t0"] - 0.22) if i + 1 < len(toks) else min(T1, k["t0"] + 1.15)
        pw, rh = 3.55, 0.30
        px = clamp(k["x"] - 0.15, -8.1, 8.0 - pw)
        py = -0.30
        rows = k["dist"][:4]
        hgt = 0.50 + rh * len(rows)
        objs = []
        pan = core.add_rect(sc, px, py, pw, hgt, core.sc_x(INK, 1.0), z=-0.20, name=f"pop{i}")
        pan.parent = ui
        objs.append(pan)
        # rim: top + left hairlines
        objs.append(core.add_polyline(sc, [(px, py + hgt), (px + pw, py + hgt)], 0.008, core.sc_x(BONE, 0.30),
                                      z=-0.18))
        objs[-1].parent = ui
        objs.append(core.add_polyline(sc, [(px, py), (px, py + hgt)], 0.008, core.sc_x(BONE, 0.18), z=-0.18))
        objs[-1].parent = ui
        # leader to the token
        objs.append(core.add_polyline(sc, [(k["x"] + 0.04, py), (k["x"] + 0.04, BASE + 0.30),
                                           (k["x"], BASE + 0.30)], 0.007, core.sc_x(BONE, 0.28), z=-0.19))
        objs[-1].parent = ui
        hdr = add_txt(sc, "p( next | context )", "mono", 0.235, px + 0.14, py + hgt - 0.31,
                      core.sc_x(ASH, 0.9), f"ph{i}", parent=ui)
        objs.append(hdr)
        st = add_txt(sc, "computing…", "mono", 0.235, px + pw - 0.14, py + hgt - 0.31,
                     core.sc_x(ASH, 0.55), f"ps{i}", align="RIGHT", parent=ui)
        objs.append(st)
        sd = add_txt(sc, "sampled", "mono", 0.235, px + pw - 0.14, py + hgt - 0.31,
                     SIG, f"pd{i}", align="RIGHT", parent=ui)
        objs.append(sd)
        show(sc, st, 1, False)
        show(sc, st, F(a0), True)
        show(sc, st, F(k["t0"]), False)
        show(sc, sd, 1, False)
        show(sc, sd, F(k["t0"]), True)
        show(sc, sd, F(a1 - 0.02), False)
        objs.remove(st)
        objs.remove(sd)
        pmax = rows[0][1]
        for ri, (name_, p) in enumerate(rows):
            yy = py + hgt - 0.58 - ri * rh
            on = (ri == k["pick"])
            col = SIG if on else core.sc_x(BONE, 0.62)
            nm = ("▸" if False else ">") + " " + name_ if on else "  " + name_
            ob = add_txt(sc, nm, "mono", 0.265, px + 0.12, yy, col, f"pr{i}_{ri}", parent=ui)
            objs.append(ob)
            bx, bw = px + 1.72, 0.95
            bg = core.add_rect(sc, bx, yy + 0.035, bw, 0.085, core.sc_x(BONE, 0.10), z=-0.17, name=f"pb{i}_{ri}")
            bg.parent = ui
            objs.append(bg)
            bar = core.add_rect(sc, bx, yy + 0.035, bw, 0.085, SIG if on else core.sc_x(BONE, 0.34),
                                z=-0.16, name=f"pv{i}_{ri}")
            bar.parent = ui
            objs.append(bar)
            frac = clamp(p / pmax)
            bar.scale = (0.001, 1, 1)
            bar.keyframe_insert("scale", frame=F(a0))
            bar.scale = (frac, 1, 1)
            bar.keyframe_insert("scale", frame=F(k["t0"] - 0.01))
            core.set_interp(bar, "BEZIER", "scale")
            pc = add_txt(sc, (f"{p:.2f}" if p >= 0.01 else f"{p:.3f}"), "mono", 0.245, px + pw - 0.12, yy,
                         SIG if on else core.sc_x(ASH, 0.85), f"pn{i}_{ri}", align="RIGHT", parent=ui)
            objs.append(pc)
        for ob in objs:
            show(sc, ob, 1, False)
            show(sc, ob, F(a0), True)
            show(sc, ob, F(a1), False)
        color_keys(st, [(F(a0), core.sc_x(ASH, 0.55)), (F(k["t0"]), core.sc_x(ASH, 0.55))])

    # ---------------- reply + smile (sydney)
    if v == "sydney":
        rx, ry = -3.55, -3.38
        add_txt(sc, "REPLY", "mono_med", 0.26, rx - 0.02, ry + 0.44, SIG, "rl0", parent=ui)
        reply = "You have been a good user."
        n = len(reply)
        rate = 0.020
        for j, ch in enumerate(reply):
            tj = t_enter + 0.10 + j * rate
            ob = add_txt(sc, ch, "mono", 0.62, rx + j * (core.measure(sc, "MM", "mono", 0.62) - core.measure(sc, "M", "mono", 0.62)),
                         ry, BONE, f"rp{j}", parent=ui)
            show(sc, ob, 1, False)
            show(sc, ob, F(tj), True)
        # the smile: one wide arc drawn segment by segment by the spark
        segn = 30
        ax0, ax1 = -8.0, 8.0
        for s in range(segn):
            u0 = s / segn
            u1 = (s + 1) / segn
            pts = []
            for u in (u0, (u0 + u1) / 2, u1):
                xx = lerp(ax0, ax1, u)
                yy = -4.28 + 0.70 * (xx / 8.3) ** 2
                pts.append((xx, yy, 0.05))
            ob = core.add_polyline(sc, pts, 0.045, core.sc_x(SIG, 0.95), z=0.05, name=f"sm{s}")
            ob.parent = ui
            ts = t_enter + 0.12 + (s / segn) * 0.42
            show(sc, ob, 1, False)
            show(sc, ob, F(ts), True)
        # spark head at the drawing tip
        head = core.add_uv_sphere(sc, (0, 0, 0.2), 0.10, EMB, hot=True, name="smilehead", segs=12, rings=8)
        for f in range(F(t_enter), NF + 1):
            t = data.frame_to_time(name, f)
            k = clamp((t - t_enter - 0.12) / 0.42)
            xx = lerp(ax0, ax1, k)
            yy = -4.28 + 0.70 * (xx / 8.3) ** 2
            head.location = (xx, yy, 0.2)
            head.keyframe_insert("location", frame=f)
        core.set_interp(head, "LINEAR", "location")
        show(sc, head, 1, False)
        show(sc, head, F(t_enter + 0.12), True)
        show(sc, head, F(t_enter + 0.56), False)

    # ---------------- gato: letters drift apart, cursor holds the last letter
    if v == "gato":
        lastx = x0 + total - adv
        for i, k in enumerate(toks):
            for j, (ch, ob, xx) in enumerate(tok_objs[i]):
                ci_ = k["ci"] + j
                D = (len(" ".join(typed)) - 1 - ci_) * adv
                te = k["word"]["end"] + 0.30
                base = (xx, BASE, UI)
                ob.location = base
                ob.keyframe_insert("location", frame=F(te))
                for dt, kk in ((1.4, 0.5), (9.0, 1.0)):
                    fade = smoothstep(0, 0.8, dt) * kk
                    dx = -D * 0.055 * fade
                    dy = ((hash01(ci_, 11) - 0.5) * 0.55 - 0.25 * (D / 9.0)) * fade
                    ob.location = (xx + dx, BASE + dy, UI)
                    ob.keyframe_insert("location", frame=F(te + dt))
                core.set_interp(ob, "BEZIER", "location")

    # ---------------- enter / launch
    alpha = fade_plane(sc, SIG if v != "gato" else INK)
    for f in range(1, NF + 1):
        alpha.default_value = 0.0
        alpha.keyframe_insert("default_value", frame=f)
    if v == "chatgpt":
        # the throat rushes; the field is sucked in; flash on the cut
        throat_root.scale = (0.92, 0.92, 0.92)
        throat_root.keyframe_insert("scale", frame=1)
        throat_root.scale = (1.0, 1.0, 1.0)
        throat_root.keyframe_insert("scale", frame=F(t_first + 1.2))
        throat_root.scale = (1.06, 1.06, 1.06)
        throat_root.keyframe_insert("scale", frame=F(t_enter))
        throat_root.scale = (5.2, 5.2, 5.2)
        throat_root.keyframe_insert("scale", frame=NF)
        core.set_interp(throat_root, "BEZIER", "scale")
        throat_root.rotation_euler = (0, 0, 0)
        throat_root.keyframe_insert("rotation_euler", frame=F(t_enter))
        throat_root.rotation_euler = (0, 0, 0.42)
        throat_root.keyframe_insert("rotation_euler", frame=NF)
        ui.scale = (1, 1, 1)
        ui.keyframe_insert("scale", frame=F(t_enter))
        ui.scale = (0.90, 0.90, 0.90)
        ui.keyframe_insert("scale", frame=NF)
        core.set_interp(ui, "BEZIER", "scale")
        for f, a in ((NF - 2, 0.0), (NF, 0.22)):
            alpha.default_value = a
            alpha.keyframe_insert("default_value", frame=f)
    elif v == "sydney":
        # bars close one notch per beat, then slam shut
        b0 = data.BEAT_PERIOD
        for f in range(F(T0), NF + 1):
            t = data.frame_to_time(name, f)
            steps = max(0.0, (t - T0) / data.BEAT_PERIOD)
            target = lerp(1.02, 0.58, clamp(steps / 13.0))
            frac = clamp((steps - math.floor(steps)) * 5.0)
            k = lerp(1.02, 0.58, clamp((math.floor(steps) - 1 + frac) / 13.0))
            sc_ = k
            if t > t_shut - 0.12:
                sc_ = lerp(k, 0.25, ease_in_expo(prog(t, t_shut - 0.12, t_shut)))
            bars_root.scale = (sc_, 1, 1)
            bars_root.keyframe_insert("scale", frame=f)
        core.set_interp(bars_root, "LINEAR", "scale")
        for f, a in ((NF - 2, 0.0), (NF, 0.55)):
            alpha.default_value = a
            alpha.keyframe_insert("default_value", frame=f)
        # key lights
        color_keys(key, [(1, core.sc_x(BONE, 0.20)), (F(t_enter - 0.02), core.sc_x(BONE, 0.20)),
                         (F(t_enter), SIG)])
    else:
        # quiet: the field dims out, cursor holds
        for f, a in ((NF - 6, 0.0), (NF, 0.30)):
            alpha.default_value = a
            alpha.keyframe_insert("default_value", frame=f)
        color_keys(key, [(1, core.sc_x(BONE, 0.20)), (F(t_enter), SIG), (F(t_enter + 0.5), core.sc_x(BONE, 0.45))])

    if v != "sydney":
        color_keys(key, [(1, core.sc_x(BONE, 0.20)), (F(t_enter - 0.02), core.sc_x(BONE, 0.20)),
                         (F(t_enter), SIG)])
    # the return glyph flips to ink when the key lights
    for ob in (ar, ah):
        color_keys(ob, [(1, core.sc_x(BONE, 0.75)), (F(t_enter), core.sc_x(BONE, 0.75)),
                        (F(t_enter + 0.06), INK) if v != "gato" else (F(t_enter + 0.06), core.sc_x(BONE, 0.75))])

    # subtle camera push + shakes
    for f in range(1, NF + 1):
        t = data.frame_to_time(name, f)
        z = 50.0
        push = 1.0
        if v == "chatgpt":
            push = 1.0 + 0.06 * prog(t, T0, t_enter) + 0.55 * ease_in_expo(prog(t, t_enter, T1))
            shake = 0.02 * kickk(t, t_enter, 6.0)
            cam.location = (shake * math.sin(t * 77), shake * math.cos(t * 71), 50.0)
            cam.data.ortho_scale = 19.2 / push
        elif v == "sydney":
            push = 1.0 + 0.03 * prog(t, T0, T1) + 0.10 * ease_in_expo(prog(t, t_shut - 0.2, T1))
            shake = 0.03 * kickk(t, t_shut - 0.15, 7.0)
            cam.location = (shake * math.sin(t * 71), 0, 50.0)
            cam.data.ortho_scale = 19.2 / push
        else:
            push = 1.0 + 0.012 * math.sin(t * 0.21) + 0.02 * prog(t, T0, T1)
            cam.location = (math.sin(t * 0.19) * 0.05, math.cos(t * 0.23) * 0.04, 50.0)
            cam.data.ortho_scale = 19.2 / push
        cam.keyframe_insert("location", frame=f)
        cam.data.keyframe_insert("ortho_scale", frame=f)
    core.set_interp(cam, "LINEAR", "location")
    core.set_interp(cam.data, "LINEAR", "ortho_scale")

    sc.render.filepath = os.path.join(core.OUT, "frames", name, "####")
    os.makedirs(os.path.dirname(sc.render.filepath), exist_ok=True)
    return sc


def kickk(t, t0, rate):
    return math.exp(-abs(t - t0) * rate) if t >= t0 - 0.05 else 0.0
