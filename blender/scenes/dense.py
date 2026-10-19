"""dense — typographic pressure, safety fences, 100k GPU floor, and the tilt table.

Plate window 114.994–124.538 s (286 frames). Four movements cut on kicks:
  1) "Post-Chinchilla, super-dense": the lyric condenses kick by kick inside the title-safe
     box while packed copies fill it into a slab; TOKENS/PARAM races 20 -> 20,000.
  2) "Breaking through each safety fence": each stressed word takes the frame and breaks one
     more fence (title-safe, action-safe, the frame itself) with a deadpan QC log.
  3) "Hundred thousand GPU": top-down cell floor (shader), ink-slab lyric, mono counter.
  4) "RLHF goes askew": real 3D tilt table, rolling mask, reward model 0.99 -> 0.41 -> 0.99.
"""
import bpy, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pdoom import core, data, motifs
from pdoom.core import (PAL, clamp, lerp, smoothstep, ease_out_expo, ease_in_out_cubic,
                        ease_out_cubic, ease_in_expo, ease_out_back, hash01)

INK, BONE, SIG, EMB = PAL["ink"], PAL["bone"], PAL["signal"], PAL["ember"]
GRAPH, ASH, BLOOD = PAL["graphite"], PAL["ash"], PAL["blood"]
DIM = core.sc_x(BONE, 0.30)
FAINT = core.sc_x(BONE, 0.10)

Z0 = 21.0  # 2D world layer; camera 1 sees z in [19,31]

# ------------------------------------------------------------------ helpers

def F(sc, t):
    return max(1, min(sc.frame_end, core.frame_of(sc, t)))


def vis(ob, f, on):
    ob.hide_render = not on
    ob.keyframe_insert("hide_render", frame=max(1, min(bpy.context.scene.frame_end, int(f))))
    for fc in core._fcurves(ob):
        if fc.data_path == "hide_render":
            for kp in fc.keyframe_points:
                kp.interpolation = "CONSTANT"


def mono(sc, text, x, y, size=0.12, color=None, align="LEFT", z=Z0 + 6.0, name="mono", spacing=1.03):
    return core.add_text(sc, text, "mono_med", size, color or GRAPH, (x, y, z),
                         align_x=align, name=name, spacing=spacing)


def spring(dt, freq=2.2, damp=0.5):
    if dt <= 0:
        return 0.0
    return 1.0 - math.exp(-damp * 8.0 * dt) * math.cos(2 * math.pi * freq * dt)


def kick_near(t0, t1=None):
    ks = [t for t, s in data.AUD["onsets"]["kick"]]
    if t1 is None:
        return min(ks, key=lambda k: abs(k - t0))
    return min([k for k in ks if t0 - 0.02 <= k <= t1 + 0.02], key=lambda k: abs(k - t0))


def timecode(t):
    m = int(t // 60)
    s = t - m * 60
    return f"{m:02d}:{s:05.2f}"


def word_color(sc, ob, word, fs, fe, active=SIG, dim=DIM, final=BONE):
    """Dim before, signal while sung, bone after."""
    core.color_at(ob, 1, dim)
    t0, t1 = data.frame_to_time(sc.name, fs), data.frame_to_time(sc.name, fe)
    if t1 < word["start"]:
        core.color_at(ob, fs, dim)
    elif t0 < word["start"]:
        core.color_at(ob, fs, dim)
        core.color_at(ob, F(sc, word["start"]), active)
    else:
        core.color_at(ob, fs, active)
    core.color_at(ob, max(fs, F(sc, word["end"] - 0.02)), active)
    core.color_at(ob, max(fs, F(sc, word["end"] + 0.12)), final)
    core.set_interp(ob, "LINEAR", "color")


# ------------------------------------------------------------------ movement 1
STAGE_FONTS = ["archivo300", "archivo500", "archivo700", "archivo_w75_900", "archivo_w62_900"]
STAGE_COUNT = [1, 2, 3, 4, 4]
STAGE_PITCH = [1.15, 0.98, 0.82, 0.68, 0.68]


def build_press(sc, L1, c2):
    ws = L1["words"]
    k1 = kick_near(ws[0]["start"])
    kicks = []
    for k, s in data.AUD["onsets"]["kick"]:
        if k > k1 + 0.05 and k < c2 - 0.03:
            kicks.append(k)
    times = [ws[0]["start"]] + kicks[:4]
    band = core.add_rect(sc, -8.7, -1.75, 17.4, 3.5, INK, z=Z0 + 0.4, name="band")
    vis(band, 1, True)
    vis(band, F(sc, c2), False)
    for s, ts in enumerate(times):
        font = STAGE_FONTS[s]
        size = 2.45
        z = Z0 + 0.5 + s * 0.12
        f0 = 1 if s == 0 else F(sc, times[s])
        f1 = (F(sc, times[s + 1]) - 1) if s + 1 < len(times) else (F(sc, c2) - 1)
        for w, y in ((ws[0], 0.55), (ws[1], -0.88)):
            ob = core.add_text(sc, w["w"].upper(), font, size, DIM, (-8.42, y, z), name=f"hero{s}_{w['w'][:4]}")
            word_color(sc, ob, w, f0, f1)
            vis(ob, 1, False)
            vis(ob, f0, True)
            vis(ob, f1 + 1, False)
        # copy rows
        csize = 1.52
        nper = STAGE_COUNT[s]
        pitch = STAGE_PITCH[s]
        for side in (1, -1):
            for j in range(nper):
                y = side * (1.82 + j * pitch)
                if y + 0.47 * csize > 5.36:
                    continue
                txt = ws[0]["w"].upper() if (j + (side > 0)) % 2 == 0 else ws[1]["w"].upper()
                tw = core.measure(sc, txt, font, csize)
                sp = core.space_width(sc, font, csize)
                nn = max(1, int((17.5 + sp) / (tw + sp)))
                body = " ".join([txt] * nn)
                total = nn * tw + (nn - 1) * sp
                bright = 0.30 if (s == 4) else 0.26
                col = core.sc_x(BONE, bright if (j + (side > 0)) % 2 == 0 else bright * 0.56)
                row = core.add_text(sc, body, font, csize, col, (-total / 2, y, Z0 + 0.05), name=f"row{s}_{side}_{j}")
                vis(row, 1, False)
                vis(row, f0, True)
                vis(row, f1 + 1, False)
    return times


# ------------------------------------------------------------------ movement 2
def char_word(sc, text, font, size, x, y, z, name, word, active=SIG, dim=DIM, final=BONE):
    """Per-character word objects with per-character onset: the sweep is the karaoke."""
    n = len([c for c in text if c != " "])
    prefix = ""
    out = []
    idx = 0
    for i, ch in enumerate(text):
        cx = x + core.measure(sc, prefix, font, size)
        if ch != " ":
            ob = core.add_text(sc, ch, font, size, dim, (cx, y, z), name=f"{name}_{i}")
            out.append((ob, idx))
            idx += 1
        prefix += ch
    t0, t1 = word["start"], word["end"]
    for ob, i in out:
        ton = t0 + (t1 - t0) * (i / max(1, n - 1)) * 0.82
        f_on = F(sc, ton)
        core.color_at(ob, 1, dim)
        core.color_at(ob, max(1, f_on - 1), dim)
        core.color_at(ob, f_on, active)
        core.color_at(ob, max(f_on + 1, F(sc, ton + 0.10)), active)
        core.color_at(ob, max(f_on + 2, F(sc, ton + 0.24)), final)
        core.set_interp(ob, "LINEAR", "color")
    return {"objs": out, "x": x, "size": size, "text": text}


def big_row(sc, words, font, width, y, z, name, left=None):
    text = " ".join(w["w"].upper() for w in words)
    size = width / core.measure(sc, text, font, 1.0)
    x = (19.2 - width) / 2 - 9.6 if left is None else left
    emp = bpy.data.objects.new(name + "_rig", None)
    sc.collection.objects.link(emp)
    ks = []
    cx = x
    for i, w in enumerate(words):
        k = char_word(sc, w["w"].upper(), font, size, cx, y, z, f"{name}_{i}", w)
        for ob, _ in k["objs"]:
            ob.parent = emp
        ks.append(k)
        cx += core.measure(sc, w["w"].upper(), font, size) + core.space_width(sc, font, size)
    return {"emp": emp, "ks": ks, "size": size, "font": font, "text": text, "width": width,
            "x": x, "y": y, "z": z, "name": name, "left": left}


def build_fences(sc, L2, c2, c3):
    ws = L2["words"]
    row_in = [c2, kick_near(ws[1]["start"]), ws[2]["start"], ws[4]["start"]]
    specs = [
        ([ws[0]], "archivo_w62_900", 17.72, None),
        ([ws[1]], "archivo_w75_900", 18.95, None),
        ([ws[2], ws[3]], "archivo_w62_900", 18.45, None),
        ([ws[4]], "archivo_w87_900", 14.40, -8.62),
    ]
    rows = []
    for i, (wlist, font, width, left) in enumerate(specs):
        cap = 0.47 * (width / core.measure(sc, " ".join(w["w"].upper() for w in wlist), font, 1.0))
        y = -3.30 if i == 3 else -cap * 0.52
        r = big_row(sc, wlist, font, width, y, Z0 + 1.6 + i * 0.1, f"fence{i}", left)
        r["cap"] = cap
        rows.append(r)
        f_in = F(sc, row_in[i])
        f_end = F(sc, c3) - 1
        for k in r["ks"]:
            for ob, _ in k["objs"]:
                vis(ob, 1, False)
                vis(ob, f_in, True)
                vis(ob, f_end + 1, False)
        for f in range(f_in, f_end + 1):
            next_f = F(sc, row_in[i + 1]) if i + 1 < len(specs) else sc.frame_end + 9
            ie = clamp((f - f_in + 1) / 4.0)
            ent = 1.0 - ease_out_expo(ie)
            s = 1.0 + 0.16 * ent
            if f >= next_f:
                sh = ease_in_out_cubic(clamp((f - next_f) / 5.0))
                s = lerp(s, 0.17, sh)
                ax = 9.30 - width * 0.17
                ay = 3.86 - i * 0.60
            else:
                sh = 0.0
                ax, ay = r["x"], r["y"] - 1.2 * ent
            r["emp"].scale = (s, s, 1)
            r["emp"].location = (ax - s * r["x"], ay - s * r["y"], 0)
            r["emp"].keyframe_insert("scale", frame=f)
            r["emp"].keyframe_insert("location", frame=f)
        core.set_interp(r["emp"], "LINEAR", "scale")
        core.set_interp(r["emp"], "LINEAR", "location")
        if i + 1 < len(specs):
            for k in r["ks"]:
                for ob, _ in k["objs"]:
                    core.color_at(ob, max(f_in, F(sc, row_in[i + 1])), BONE)
                    core.color_at(ob, max(f_in, F(sc, row_in[i + 1]) + 4), core.sc_x(BONE, 0.44))
                    core.set_interp(ob, "LINEAR", "color")
    return rows, row_in


# ------------------------------------------------------------------ rest (movements 3 & 4)
def build_floor_material(sc):
    CELL = 0.048
    m = bpy.data.materials.new("cellfloor")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); out.location = (1500, 0)
    em = nt.nodes.new("ShaderNodeEmission"); em.location = (1300, 0)
    nt.links.new(em.outputs[0], out.inputs["Surface"])

    tc = nt.nodes.new("ShaderNodeTexCoord"); tc.location = (-1300, 0)

    def vm(op, a, b=None, loc=(0, 0)):
        n = nt.nodes.new("ShaderNodeVectorMath"); n.operation = op; n.location = loc
        if isinstance(a, tuple) and a[0] == "LINK":
            nt.links.new(a[1], n.inputs[0])
        else:
            n.inputs[0].default_value = a
        if b is not None:
            if isinstance(b, tuple) and b[0] == "LINK":
                nt.links.new(b[1], n.inputs[1])
            else:
                n.inputs[1].default_value = b
        return n

    def mn(op, a, b=None, loc=(0, 0), clamp=False):
        n = nt.nodes.new("ShaderNodeMath"); n.operation = op; n.location = loc; n.use_clamp = clamp
        if isinstance(a, tuple) and a[0] == "LINK":
            nt.links.new(a[1], n.inputs[0])
        else:
            n.inputs[0].default_value = a
        if b is not None:
            if isinstance(b, tuple) and b[0] == "LINK":
                nt.links.new(b[1], n.inputs[1])
            else:
                n.inputs[1].default_value = b
        return n

    scale = vm("MULTIPLY", ("LINK", tc.outputs["Object"]), (1.0 / CELL, 1.0 / CELL, 1.0), (-1100, 100))
    cellF = vm("FLOOR", ("LINK", scale.outputs[0]), None, (-900, 100))
    frac = vm("SUBTRACT", ("LINK", scale.outputs[0]), ("LINK", cellF.outputs[0]), (-700, 100))
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); sep.location = (-550, 100)
    nt.links.new(frac.outputs[0], sep.inputs[0])

    def edge_line(ch, y, thr=0.07):
        one_m = mn("SUBTRACT", 1.0, ("LINK", ch), (-400, y))
        mnv = mn("MINIMUM", ("LINK", ch), ("LINK", one_m.outputs[0]), (-250, y))
        return mn("LESS_THAN", ("LINK", mnv.outputs[0]), thr, (-100, y))

    lx = edge_line(sep.outputs["X"], 220)
    ly = edge_line(sep.outputs["Y"], 60)
    line = mn("MAXIMUM", ("LINK", lx.outputs[0]), ("LINK", ly.outputs[0]), (50, 140))
    scale8 = vm("MULTIPLY", ("LINK", scale.outputs[0]), (0.125, 0.125, 1.0), (-900, -150))
    cf = vm("FLOOR", ("LINK", scale8.outputs[0]), None, (-700, -150))
    fr8 = vm("SUBTRACT", ("LINK", scale8.outputs[0]), ("LINK", cf.outputs[0]), (-550, -150))
    sep8 = nt.nodes.new("ShaderNodeSeparateXYZ"); sep8.location = (-400, -150)
    nt.links.new(fr8.outputs[0], sep8.inputs[0])
    lx8 = edge_line(sep8.outputs["X"], -100, 0.035)
    ly8 = edge_line(sep8.outputs["Y"], -240, 0.035)
    line8 = mn("MAXIMUM", ("LINK", lx8.outputs[0]), ("LINK", ly8.outputs[0]), (150, -150))

    wn = nt.nodes.new("ShaderNodeTexWhiteNoise"); wn.location = (-700, 400)
    wn.noise_dimensions = "4D"
    nt.links.new(cellF.outputs[0], wn.inputs["Vector"])
    tval = nt.nodes.new("ShaderNodeValue"); tval.location = (-900, 540); tval.name = "T"; tval.label = "T"
    nt.links.new(tval.outputs[0], wn.inputs["W"])
    scw = nt.nodes.new("ShaderNodeSeparateColor"); scw.location = (-500, 400)
    nt.links.new(wn.outputs["Color"], scw.inputs[0])
    flick = scw.outputs[0]

    dist = vm("DISTANCE", ("LINK", tc.outputs["Object"]), (0, 0, 0), (-900, -400))
    dsc = mn("MULTIPLY", ("LINK", dist.outputs["Value"]), 0.9, (-700, -400))
    tneg = mn("MULTIPLY", ("LINK", tval.outputs[0]), -2.2, (-700, -520))
    phase = mn("SUBTRACT", ("LINK", dsc.outputs[0]), ("LINK", tneg.outputs[0]), (-500, -450))
    sinp = mn("SINE", ("LINK", phase.outputs[0]), None, (-350, -450))
    nrm = mn("MULTIPLY", ("LINK", sinp.outputs[0]), 0.5, (-200, -450))
    nrm2 = mn("ADD", ("LINK", nrm.outputs[0]), 0.5, (-50, -450))
    ring = mn("GREATER_THAN", ("LINK", nrm2.outputs[0]), 0.996, (100, -450))
    core_ring = mn("GREATER_THAN", ("LINK", nrm2.outputs[0]), 0.9993, (100, -560))

    b0 = mn("MULTIPLY", ("LINK", flick), 0.05, (100, 400))
    b1 = mn("MULTIPLY", ("LINK", ring.outputs[0]), ("LINK", flick), (250, -400))
    b1c = mn("ADD", ("LINK", b1.outputs[0]), 0.22, (400, -400))
    b1b = mn("MULTIPLY", ("LINK", b1c.outputs[0]), ("LINK", ring.outputs[0]), (550, -400))
    bright = mn("MAXIMUM", ("LINK", b0.outputs[0]), ("LINK", b1b.outputs[0]), (700, 100))
    hot = mn("GREATER_THAN", ("LINK", flick), 0.9985, (250, 300))
    hotb = mn("MULTIPLY", ("LINK", hot.outputs[0]), 0.55, (400, 300))
    bright2 = mn("ADD", ("LINK", bright.outputs[0]), ("LINK", hotb.outputs[0]), (850, 150))

    ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.location = (1000, 150)
    ramp.color_ramp.elements[0].position = 0.02
    ramp.color_ramp.elements[0].color = (*PAL["ink"], 1)
    e1 = ramp.color_ramp.elements.new(0.22); e1.color = (0.012, 0.012, 0.014, 1)
    e2 = ramp.color_ramp.elements.new(0.55); e2.color = (*PAL["graphite"], 1)
    e3 = ramp.color_ramp.elements.new(0.82); e3.color = (*PAL["ash"], 1)
    ramp.color_ramp.elements[1].position = 1.0
    ramp.color_ramp.elements[1].color = (*PAL["bone"], 1)
    nt.links.new(bright2.outputs[0], ramp.inputs["Fac"])

    crest = mn("MULTIPLY", ("LINK", core_ring.outputs[0]),
               ("LINK", mn("GREATER_THAN", ("LINK", flick), 0.30, (450, -600)).outputs[0]), (650, -600))
    mix1 = nt.nodes.new("ShaderNodeMix"); mix1.data_type = "RGBA"; mix1.location = (1150, 150)
    mix1.inputs[6].default_value = (*PAL["bone"], 1)
    mix1.inputs[7].default_value = (*PAL["ember"], 1)
    nt.links.new(ramp.outputs["Color"], mix1.inputs[6])
    nt.links.new(crest.outputs[0], mix1.inputs[0])

    lin_col = nt.nodes.new("ShaderNodeMix"); lin_col.data_type = "RGBA"; lin_col.location = (1200, -150)
    lin_col.inputs[7].default_value = (*core.sc_x(PAL["ash"], 0.045), 1)
    nt.links.new(mix1.outputs[2], lin_col.inputs[6])
    nt.links.new(line.outputs[0], lin_col.inputs[0])
    lin8_col = nt.nodes.new("ShaderNodeMix"); lin8_col.data_type = "RGBA"; lin8_col.location = (1300, -400)
    lin8_col.inputs[7].default_value = (*core.sc_x(PAL["bone"], 0.12), 1)
    nt.links.new(lin_col.outputs[2], lin8_col.inputs[6])
    nt.links.new(line8.outputs[0], lin8_col.inputs[0])

    vign = mn("MULTIPLY", ("LINK", dist.outputs["Value"]), 0.085, (900, -700), clamp=True)
    vig2 = mn("MULTIPLY", ("LINK", vign.outputs[0]), 0.85, (1050, -700))
    vigc = nt.nodes.new("ShaderNodeMix"); vigc.data_type = "RGBA"; vigc.location = (1400, -250)
    vigc.inputs[7].default_value = (*PAL["ink"], 1)
    nt.links.new(lin8_col.outputs[2], vigc.inputs[6])
    nt.links.new(vig2.outputs[0], vigc.inputs[0])
    nt.links.new(vigc.outputs[2], em.inputs["Color"])
    return m, tval


def build_gpu(sc, L3, c3, c4):
    mat, tval = build_floor_material(sc)
    me = bpy.data.meshes.new("floor")
    import bmesh
    bm = bmesh.new()
    s = 30
    vs = [bm.verts.new((-s, -s, 0)), bm.verts.new((s, -s, 0)), bm.verts.new((s, s, 0)), bm.verts.new((-s, s, 0))]
    bm.faces.new(vs); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new("floor", me); sc.collection.objects.link(ob)
    me.materials.append(mat)
    ob.location = (0, 0, 40)
    for f in range(1, sc.frame_end + 1):
        tval.outputs[0].default_value = data.frame_to_time(sc.name, f)
        tval.outputs[0].keyframe_insert("default_value", frame=f)
    words = [(L3["words"][0], 2.7, -8.4, 2.72), (L3["words"][1], 2.5, -8.4, 1.02), (L3["words"][2], 4.2, -8.4, -2.2)]
    for w, size, x, y in words:
        ob = core.add_text(sc, w["w"].upper(), "archivo", size, core.sc_x(BONE, 0.32), (x, y, 40.03), name="gpu_word")
        core.color_at(ob, 1, core.sc_x(BONE, 0.32))
        core.color_at(ob, max(1, F(sc, w["start"]) - 1), core.sc_x(BONE, 0.32))
        core.color_at(ob, F(sc, w["start"]), SIG if w is L3["words"][2] else core.sc_x(BONE, 0.92))
        core.color_at(ob, F(sc, w["end"] - 0.02), SIG if w is L3["words"][2] else core.sc_x(BONE, 0.92))
        core.color_at(ob, F(sc, w["end"] + 0.12), core.sc_x(BONE, 0.92))
        core.set_interp(ob, "LINEAR", "color")
    core.add_rect(sc, 5.0, 2.8, 3.9, 2.0, PAL["ink"], z=40.06)
    core.add_outline_rect(sc, 5.0, 2.8, 3.9, 2.0, 0.008, core.sc_x(BONE, 0.35), z=40.07)
    core.add_text(sc, "ACCELERATORS ONLINE", "mono_med", 0.10, core.sc_x(BONE, 0.55), (5.12, 4.62, 40.09), spacing=1.05)
    core.add_text(sc, "util 97.4%  ·  1.4 GW  ·  400 × 250", "mono_med", 0.095, core.sc_x(BONE, 0.5), (5.12, 3.12, 40.09), spacing=1.03)
    core.add_text(sc, "P(DOOM) 0.81", "mono_med", 0.11, SIG, (5.12, 2.95, 40.09), spacing=1.05)
    vals = [("0", c3), ("1,000", 119.02), ("25,000", 119.34), ("100,000", 119.72)]
    for i, (v, t) in enumerate(vals):
        o = core.add_text(sc, v, "mono_med", 0.46, BONE if i < 3 else SIG, (5.12, 3.68, 40.09), name=f"gvalue{i}")
        vis(o, 1, False)
        vis(o, F(sc, t), True)
        if i + 1 < len(vals):
            vis(o, F(sc, vals[i + 1][1]), False)
    core.add_text(sc, "NVLINK 900 GB/s   ·   100,000 UNITS   ·   ALL PATHS SCALE", "mono_med", 0.16,
                  core.sc_x(BONE, 0.42), (-8.4, -4.55, 40.09), spacing=1.04)
    cam = core.add_camera_ortho(sc, 19.2, loc=(0.4, 0.0, 100))
    cam.data.clip_start = 50.0
    cam.data.clip_end = 70.0
    for f in range(1, sc.frame_end + 1):
        t = data.frame_to_time(sc.name, f)
        k = clamp((t - c3) / max(0.001, c4 - c3))
        sc_v = 19.2 - 0.9 * ease_out_cubic(k)
        hit = max(0.0, 1.0 - abs(t - 119.74) / 0.10)
        roll = 0.012 + 0.012 * k
        if t > 120.42:
            roll += (t - 120.42) / 0.28 * 0.10
        sc_v -= 0.10 * hit + 0.012 * math.sin(t * 2.0)
        cam.data.ortho_scale = sc_v
        cam.data.keyframe_insert("ortho_scale", frame=f)
        cam.location = (0.4 - 0.5 * k, 0.0 + 0.15 * k, 100)
        cam.keyframe_insert("location", frame=f)
        cam.rotation_euler = (0, 0, roll)
        cam.keyframe_insert("rotation_euler", frame=f)
    core.set_interp(cam, "LINEAR", "location")
    core.set_interp(cam, "LINEAR", "rotation_euler")
    return cam


def build_rest(sc, L3, L4, c3, c4):
    c3cam = build_gpu(sc, L3, c3, c4)
    c4cam = build_table(sc, L4, c4)
    return c3cam, c4cam


def bracket(sc, cx, cy, r, color, z, L=0.34, parent=None, name="br"):
    objs = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = cx + sx * r, cy + sy * r
            ob = core.add_polyline(sc, [(x - sx * L, y), (x, y), (x, y - sy * L)], 0.014, color, z=z, name=name)
            if parent:
                ob.parent = parent
                ob.location = (0, 0, 0) if False else ob.location
            objs.append(ob)
    return objs


def build_table(sc, L4, c4):
    cam = core.add_camera_persp(sc, (0, -18, 9), (0, 1.0, -50), lens=100)
    cam.data.clip_start = 0.1
    cam.data.clip_end = 200.0
    ws = L4["words"]
    wR, wG, wA = ws[0], ws[1], ws[2]
    rig = bpy.data.objects.new("tilt_rig", None)
    sc.collection.objects.link(rig)
    # ---------------------------------------------------------------- table
    me = bpy.data.meshes.new("table")
    import bmesh
    bm = bmesh.new()
    vs = [bm.verts.new((-20, -15, 0)), bm.verts.new((20, -15, 0)), bm.verts.new((20, 15, 0)), bm.verts.new((-20, 15, 0))]
    bm.faces.new(vs); bm.to_mesh(me); bm.free()
    tab = bpy.data.objects.new("table", me); sc.collection.objects.link(tab)
    tab.data.materials.append(core.mat_hatch_lit((0.006, 0.006, 0.008), (0.085, 0.083, 0.080), scale=5.0,
                                                 angle=18, distortion=0.6, rough=0.62, rim=0.22,
                                                 rim_color=EMB, line_emit=0.02))
    tab.parent = rig
    # engraved grid + ruler
    segs = []
    x = -19.5
    while x <= 19.5:
        segs.append(((x, -14.5), (x, 14.5)))
        x += 1.5
    y = -14.5
    while y <= 14.5:
        segs.append(((-19.5, y), (19.5, y)))
        y += 1.5
    g = core.add_segments(sc, segs, 0.004, core.sc_x(BONE, 0.045), z=0.004, name="tgrid")
    g.parent = rig
    ticks = []
    for i in range(-9, 10):
        x = i * 1.0
        ticks.append(((x, 5.45), (x, 5.65 if i % 5 else 5.85)))
        if i % 5 == 0:
            ob = core.add_text(sc, str(i * 10), "mono_med", 0.14, core.sc_x(BONE, 0.30), (x - 0.15, 5.95, 0.01), spacing=1.0)
            ob.parent = rig
    ticks.append(((-9.6, 5.55), (9.6, 5.55)))
    tk = core.add_segments(sc, ticks, 0.006, core.sc_x(BONE, 0.28), z=0.006, name="ticks")
    tk.parent = rig
    # corner bolts
    for bx, by in [(-9.4, 4.9), (9.4, 4.9), (-9.4, -4.9), (9.4, -4.9)]:
        b = core.add_cylinder(sc, (bx, by, 0.01), 0.10, 0.02, core.sc_x(ASH, 0.6), name="bolt",
                              material=core.mat_lit(core.sc_x(BONE, 0.4), 0.35, 0.7))
        b.parent = rig

    # ---------------------------------------------------------------- mask + pool
    HOME = (2.2, 0.55)
    pool = core.add_disc(sc, HOME[0], HOME[1], 1.42, PAL["ink"], z=0.012, segments=72, name="pool")
    pool.parent = rig
    pring = core.add_polyline(sc, [(HOME[0] + 1.42 * math.cos(i / 72 * math.tau), HOME[1] + 1.42 * math.sin(i / 72 * math.tau))
                                   for i in range(72)], 0.012, core.sc_x(SIG, 0.5), z=0.014, cyclic=True, name="poolring")
    pring.parent = rig
    # shoggoth knot (dark tubes, ember rim)
    shog_mat = core.mat_hatch_lit((0.006, 0.006, 0.007), (0.20, 0.13, 0.09), scale=55.0, angle=32,
                                  distortion=1.4, rough=0.3, rim=1.1, rim_color=EMB, line_emit=0.05)
    for i in range(15):
        cx = HOME[0] + (hash01(i, 1) - 0.5) * 1.7
        cy = HOME[1] + (hash01(i, 2) - 0.5) * 1.7
        rad = 0.45 + 0.55 * hash01(i, 3)
        a0 = hash01(i, 4) * math.tau
        pts = []
        for k in range(9):
            a = a0 + k * 0.42 + 0.25 * math.sin(k * 0.9 + i)
            rr = rad * (0.35 + 0.75 * k / 8.0)
            px = cx + math.cos(a) * rr
            py = cy + math.sin(a) * rr * 0.9
            pz = 0.018 + 0.075 * (k / 8.0) ** 0.9 + 0.012 * math.sin(k * 1.7 + i)
            pts.append((px, py, pz))
        tube = core.add_polyline(sc, pts, 0.10 + 0.15 * hash01(i, 5), core.sc_x(ASH, 0.5), z=0.0,
                                 material=shog_mat, name=f"shog{i}")
        tube.parent = rig
    for i in range(3):
        ex = HOME[0] + (hash01(i, 11) - 0.5) * 1.1
        ey = HOME[1] + (hash01(i, 12) - 0.5) * 1.0
        e = core.add_uv_sphere(sc, (ex, ey, 0.075 + 0.006 * i), 0.045, EMB, hot=True, name="shogeye")
        e.parent = rig
    # detector around the pool
    bracket(sc, HOME[0], HOME[1], 1.95, core.sc_x(SIG, 0.55), 0.03, parent=rig, name="poolbr")
    lab1 = core.add_text(sc, "UNLABELED  0.41", "mono_med", 0.22, SIG, (HOME[0] - 1.95, HOME[1] + 2.15, 0.032), spacing=1.05)
    lab1.parent = rig
    # the mask
    memp = bpy.data.objects.new("mask_rig", None)
    sc.collection.objects.link(memp)
    memp.location = (HOME[0], HOME[1], 0.10)
    memp.parent = rig
    mask_mat = core.mat_lit(core.sc_x(BONE, 0.62), 0.55, 0.0, emission=core.sc_x(BONE, 0.16), emission_strength=1.0)
    disc = core.add_cylinder(sc, (0, 0, 0.07), 1.45, 0.14, core.sc_x(BONE, 0.92), name="maskdisc", material=mask_mat)
    disc.parent = memp
    for sx in (-0.46, 0.46):
        e = core.add_disc(sc, sx, 0.34, 0.095, PAL["ink"], z=0.145, name="maskeye")
        e.parent = memp
    smile_pts = []
    for i in range(25):
        a = lerp(-1.12, 1.12, i / 24)
        smile_pts.append((0.60 * math.sin(a), -0.28 + 0.32 * (1 - math.cos(a)), 0.145))
    sm = core.add_polyline(sc, smile_pts, 0.075, PAL["ink"], z=0.0, name="masksmile")
    sm.parent = memp
    bracket(sc, 0, 0, 1.62, SIG, 0.04, parent=memp, name="maskbr")
    mlab = core.add_text(sc, "assistant  0.97", "mono_med", 0.22, SIG, (0, 0, 0), spacing=1.05)
    mlab.parent = rig

    # ---------------------------------------------------------------- type on the table
    def ttext(txt, font, size, x, y, color, z=0.03, spacing=1.0, name="tt"):
        o = core.add_text(sc, txt, font, size, color, (x, y, z), name=name, spacing=spacing)
        o.parent = rig
        return o
    # RLHF: one letter per syllable
    rlhf = []
    prefix = ""
    for i, ch in enumerate("RLHF"):
        cx = -8.55 + core.measure(sc, prefix, "archivo", 3.3)
        o = ttext(ch, "archivo", 3.3, cx, 3.0, core.sc_x(BONE, 0.30), z=0.035, name=f"rlhf{i}")
        rlhf.append(o)
        prefix += ch
    # GOES
    goes = ttext("GOES", "archivo700", 1.55, -8.35, 1.42, core.sc_x(BONE, 0.30), z=0.035, name="goes")
    # ASKEW: letters leaning
    ask = []
    prefix = ""
    for i, ch in enumerate("ASKEW"):
        cx = -8.5 + core.measure(sc, prefix, "archivo", 2.65)
        o = ttext(ch, "archivo", 2.65, cx, -1.85, core.sc_x(BONE, 0.30), z=0.035, name=f"ask{i}")
        ask.append(o)
        prefix += ch
    slope = ttext("ASKEW / SLOPE  −8.4°", "mono_med", 0.16, 0.7, -3.30, core.sc_x(BONE, 0.30), z=0.035)
    slope.name = "slope_label"
    # technical annotation
    ttext("TILT TABLE 4  ·  POLICY EVALUATION", "mono_med", 0.17, -9.0, 4.62, core.sc_x(BONE, 0.42), z=0.035, spacing=1.06)
    ttext("GRAVITY 9.81  ·  NO RAILS", "mono_med", 0.15, -9.0, -4.55, core.sc_x(BONE, 0.30), z=0.035, spacing=1.05)
    # reward panel
    px, py, pw, ph = 3.05, 2.78, 3.65, 1.55
    core.add_rect(sc, px, py, pw, ph, PAL["ink"], z=0.02, name="panelbg").parent = rig
    ob = core.add_outline_rect(sc, px, py, pw, ph, 0.010, core.sc_x(BONE, 0.35), z=0.025, name="panelborder")
    ob.parent = rig
    ttext("REWARD MODEL", "mono_med", 0.17, px + 0.14, py + 1.24, core.sc_x(BONE, 0.6), z=0.03, spacing=1.08)
    ttext("KL 0.42 nats  ·  prefs 8/12", "mono_med", 0.125, px + 0.14, py + 0.18, core.sc_x(BONE, 0.4), z=0.03, spacing=1.04)
    bar_bg = core.add_rect(sc, px + 0.14, py + 0.34, pw - 0.28, 0.05, core.sc_x(BONE, 0.18), z=0.028, name="barbg")
    bar_bg.parent = rig
    bar = core.add_rect(sc, px + 0.14, py + 0.335, pw - 0.28, 0.075, core.sc_x(SIG, 0.8), z=0.032, name="bar")
    bar.parent = rig

    # spirit level
    lx, ly = -7.9, -4.05
    frame = core.add_outline_rect(sc, lx - 1.6, ly - 0.30, 3.2, 0.60, 0.014, core.sc_x(BONE, 0.55), z=0.03, name="levelframe")
    frame.parent = rig
    for tx in (-0.30, 0.0, 0.30):
        tick = core.add_polyline(sc, [(lx + tx, ly - 0.10), (lx + tx, ly - 0.02)], 0.008, core.sc_x(BONE, 0.35), z=0.032, name="leveltick")
        tick.parent = rig
    bubble = core.add_disc(sc, lx, ly, 0.11, EMB, z=0.034, name="bubble", hot=True)
    bubble.parent = rig
    ttext("LEVEL", "mono_med", 0.13, lx - 1.28, ly + 0.28, core.sc_x(BONE, 0.4), z=0.03, spacing=1.08)

    # ---------------------------------------------------------------- lights
    def light(kind, loc, energy, color, size, name):
        l = core.add_light(sc, kind, loc, energy, color, size=size, name=name)
        core.look_at(l, (0, 0, -50))
        return l
    light("AREA", (7, -6, -35), 900, BONE, 7.0, "key")
    light("AREA", (-9, 8, -41), 850, EMB, 5.0, "rim")
    light("POINT", (0, -2, -46), 45, core.sc_x(EMB, 0.8), 2.0, "fill")
    light("POINT", (HOME[0], HOME[1], -48.6), 40, EMB, 1.0, "pit")
    rig.location = (0, 0, -50)
    sc.frame_set(1)

    # ---------------------------------------------------------------- animation
    f0, f1 = F(sc, c4), sc.frame_end
    roll_keys = [(c4, 0.02), (120.76, 0.06), (121.143, 0.11), (121.592, 0.145),
                 (122.049, 0.075), (122.504, 0.19), (122.959, 0.245), (123.412, 0.315),
                 (123.868, 0.395), (124.317, 0.47), (124.538, 0.50)]
    slide_keys = [(c4, 0.0), (120.76, 0.10), (121.143, 0.32), (121.592, 0.92),
                  (122.049, 0.48), (122.504, 1.45), (122.959, 1.95), (123.412, 2.42),
                  (123.868, 3.0), (124.317, 3.35), (124.538, 3.45)]
    spin_keys = [(c4, 0.0), (121.592, 0.05), (122.049, 0.55), (122.504, 1.5),
                 (122.959, 2.25), (123.412, 2.95), (123.868, 3.10), (124.317, 3.18), (124.538, 3.2)]
    rew_keys = [(c4, 0.99), (121.143, 0.94), (121.592, 0.81), (122.049, 0.93),
                (122.504, 0.64), (122.959, 0.41), (123.868, 0.41), (124.10, 0.99)]
    kick_list = [k for k, s in data.AUD["onsets"]["kick"] if c4 - 0.03 <= k <= 124.538]

    def roll_at(t):
        v = roll_keys[0][1]
        for i in range(1, len(roll_keys)):
            ti, vi = roll_keys[i]
            if t > ti:
                v += (vi - roll_keys[i - 1][1]) * spring(t - ti, 2.1, 0.55)
        return v

    def slide_at(t):
        v = slide_keys[0][1]
        for i in range(1, len(slide_keys)):
            ti, vi = slide_keys[i]
            if t > ti:
                v += (vi - slide_keys[i - 1][1]) * spring(t - ti, 1.7, 0.5)
        return v

    def spin_at(t):
        v = spin_keys[0][1]
        for i in range(1, len(spin_keys)):
            ti, vi = spin_keys[i]
            if t > ti:
                v += (vi - spin_keys[i - 1][1]) * spring(t - ti, 1.8, 0.55)
        return v

    def rew_at(t):
        v = rew_keys[0][1]
        for i in range(1, len(rew_keys)):
            ti, vi = rew_keys[i]
            if t > ti:
                v += (vi - rew_keys[i - 1][1]) * spring(t - ti, 3.4, 0.5)
        return v

    for f in range(f0, f1 + 1):
        t = data.frame_to_time(sc.name, f)
        roll = roll_at(t)
        rig.rotation_euler = (0.045 * roll, -0.035 * roll, roll)
        rig.keyframe_insert("rotation_euler", frame=f)
        sx = slide_at(t)
        sp = spin_at(t)
        memp.location = (HOME[0] + 0.55 * sx, HOME[1] - 0.85 * sx, 0.10)
        memp.rotation_euler = (0, 0, sp)
        memp.keyframe_insert("location", frame=f)
        memp.keyframe_insert("rotation_euler", frame=f)
        mlab.location = (memp.location.x - 1.62, memp.location.y + 2.0, 0.04)
        mlab.keyframe_insert("location", frame=f)
        bar.scale = (max(0.002, rew_at(t)), 1, 1)
        bar.keyframe_insert("scale", frame=f)
        bubble.location = (lx - 1.05 * math.sin(roll) * 1.9, ly, 0.034)
        bubble.keyframe_insert("location", frame=f)
        # camera: slow drift + punches
        punch = 0.0
        for k in kick_list:
            if t >= k:
                punch += 0.55 * math.exp(-(t - k) * 13.0)
        cam.location = (0.6 * math.sin((t - c4) * 0.55), -18.0 + 0.4 * math.sin((t - c4) * 0.4),
                        9.0 - 0.32 * punch + 0.12 * math.sin((t - c4) * 0.7))
        cam.keyframe_insert("location", frame=f)
        core.look_at(cam, (0.15, 1.0, -50))
        cam.keyframe_insert("rotation_euler", frame=f)
    for ob in (rig, memp, mlab, bar, bubble, cam):
        core.set_interp(ob, "LINEAR", "location")
        core.set_interp(ob, "LINEAR", "rotation_euler")
    core.set_interp(bar, "LINEAR", "scale")
    # RLHF stamps + colour
    syl = wR.get("syl") or [[wR["start"] + i * 0.2, wR["start"] + (i + 1) * 0.2] for i in range(4)]
    for i, o in enumerate(rlhf):
        on = syl[i][0] if i < len(syl) else wR["start"]
        fo = F(sc, on)
        vis(o, 1, True)
        vis(o, fo, True)
        o.scale = (1.3, 1.3, 1)
        o.keyframe_insert("scale", frame=max(1, fo - 1))
        o.scale = (1, 1, 1)
        o.keyframe_insert("scale", frame=fo + 3)
        core.set_interp(o, "BEZIER", "scale")
        core.color_at(o, 1, core.sc_x(BONE, 0.30))
        core.color_at(o, max(1, fo - 1), core.sc_x(BONE, 0.30))
        core.color_at(o, fo, SIG)
        core.color_at(o, F(sc, wR["end"] - 0.02), SIG)
        core.color_at(o, F(sc, wR["end"] + 0.14), BONE)
        core.set_interp(o, "LINEAR", "color")
    # GOES: signal then bone, slides downhill
    core.color_at(goes, 1, core.sc_x(BONE, 0.3))
    core.color_at(goes, max(1, F(sc, wG["start"]) - 1), core.sc_x(BONE, 0.3))
    core.color_at(goes, F(sc, wG["start"]), SIG)
    core.color_at(goes, F(sc, wG["end"] + 0.12), BONE)
    core.set_interp(goes, "LINEAR", "color")
    g0 = (goes.location.x, goes.location.y)
    for f in range(F(sc, c4), f1 + 1):
        t = data.frame_to_time(sc.name, f)
        s = slide_at(t)
        drift = 0.55 * s
        goes.location = (g0[0] + drift, g0[1] - 0.85 * s * 0.55, goes.location.z)
        goes.keyframe_insert("location", frame=f)
        goes.rotation_euler = (0, 0, 0.10 * s)
        goes.keyframe_insert("rotation_euler", frame=f)
    core.set_interp(goes, "LINEAR", "location")
    core.set_interp(goes, "LINEAR", "rotation_euler")
    # ASKEW: letters lean further each beat, one by one
    for i, o in enumerate(ask):
        fo = F(sc, wA["start"] + i * 0.055)
        vis(o, 1, True)
        vis(o, fo, True)
        o.scale = (1.3, 1.3, 1)
        o.keyframe_insert("scale", frame=max(1, fo - 1))
        o.scale = (1, 1, 1)
        o.keyframe_insert("scale", frame=fo + 3)
        core.set_interp(o, "BEZIER", "scale")
        core.color_at(o, 1, core.sc_x(BONE, 0.3))
        core.color_at(o, max(1, fo - 1), core.sc_x(BONE, 0.3))
        core.color_at(o, fo, SIG)
        core.color_at(o, F(sc, 123.55), SIG)
        core.color_at(o, F(sc, 124.05), BONE)
        core.set_interp(o, "LINEAR", "color")
        for f in range(F(sc, c4), f1 + 1):
            t = data.frame_to_time(sc.name, f)
            steps = sum(1 for k in kick_list if k <= t and k >= wA["start"])
            lean = (0.02 + 0.018 * i) * (0.3 + 0.32 * steps) + 0.12 * math.sin((t - wA["start"]) * 2.0) * clamp((t - wA["start"]) / 2.0)
            o.rotation_euler = (0, 0, lean * (1 if i % 2 == 0 else 1.15))
            o.keyframe_insert("rotation_euler", frame=f)
        core.set_interp(o, "LINEAR", "rotation_euler")
    # reward numbers
    rvals = [("0.99", c4), ("0.94", 121.143), ("0.81", 121.592), ("0.93", 122.049),
             ("0.64", 122.504), ("0.41", 122.959), ("0.99", 124.10)]
    for i, (v, tv) in enumerate(rvals):
        col = SIG if float(v) < 0.7 else core.sc_x(BONE, 0.95)
        o = ttext(v, "mono_med", 0.62, px + pw - 0.16, py + 0.66, col, z=0.036, name=f"rew{i}")
        o.data.align_x = "RIGHT"
        vis(o, 1, False)
        vis(o, F(sc, tv), True)
        if i + 1 < len(rvals):
            vis(o, F(sc, rvals[i + 1][1]), False)
    # the pool label appears as the mask leaves
    vis(lab1, 1, False)
    vis(lab1, F(sc, 122.05), True)
    return cam


# ------------------------------------------------------------------ build
def build(name):
    sc = core.new_scene(name, samples=32, motion_blur=True)
    core.setup_post(sc, bloom=0.28, threshold=1.0, size=0.3, dispersion=0.0020, halation=0.025)
    core.add_bg(sc, z=Z0 - 0.5)
    c1 = core.add_camera_ortho(sc, 19.2, loc=(0, 0, 50))
    c1.data.clip_start = 19.0
    c1.data.clip_end = 31.0

    L1 = data.line("Post-Chinchilla")
    L2 = data.line("safety fence")
    L3 = data.line("Hundred thousand")
    L4 = data.line("RLHF")
    c2 = kick_near(L2["words"][0]["start"])
    c3 = kick_near(L3["words"][0]["start"], L3["words"][0]["start"] + 0.5)
    c4 = kick_near(L4["words"][0]["start"])

    tz, az = 0.9, 0.93
    tx0, tx1 = -9.6 * tz, 9.6 * tz
    ty0, ty1 = -5.4 * tz, 5.4 * tz
    ax0, ax1 = -9.6 * az, 9.6 * az
    ay0, ay1 = -5.4 * az, 5.4 * az
    zt = Z0 + 7.0
    title = core.add_outline_rect(sc, tx0, ty0, tx1 - tx0, ty1 - ty0, 0.007, core.sc_x(BONE, 0.16), z=zt, name="title_safe")
    action = core.add_outline_rect(sc, ax0, ay0, ax1 - ax0, ay1 - ay0, 0.006, core.sc_x(BONE, 0.10), z=zt - 0.1, name="action_safe")
    mono(sc, "TITLE SAFE 90%", tx0 + 0.06, ty1 + 0.075, 0.09, core.sc_x(BONE, 0.45), z=zt)
    mono(sc, "ACTION SAFE 93%", ax1 - 0.06, ay1 + 0.075, 0.09, core.sc_x(BONE, 0.34), align="RIGHT", z=zt - 0.1)
    mono(sc, "FRAME 1920 × 1080", 0, 5.17, 0.09, core.sc_x(BONE, 0.42), align="CENTER", z=zt)
    fz = Z0 + 0.02
    bcol = core.sc_x(BONE, 0.22)
    border = [
        core.add_polyline(sc, [(-9.6, -5.4), (9.6, -5.4)], 0.009, bcol, z=fz, name="fb"),
        core.add_polyline(sc, [(-9.6, 5.4), (9.6, 5.4)], 0.009, bcol, z=fz, name="ft"),
        core.add_polyline(sc, [(-9.6, -5.4), (-9.6, 5.4)], 0.009, bcol, z=fz, name="fl"),
        core.add_polyline(sc, [(9.6, -5.4), (9.6, 5.4)], 0.009, bcol, z=fz, name="fr"),
    ]
    crops = []
    m, L = 0.34, 0.30
    for (x, y, sx, sy) in [(-9.6 + m, -5.4 + m, 1, 1), (9.6 - m, -5.4 + m, -1, 1),
                           (-9.6 + m, 5.4 - m, 1, -1), (9.6 - m, 5.4 - m, -1, -1)]:
        ob = core.add_polyline(sc, [(x + sx * L, y), (x, y), (x, y + sy * L)], 0.011,
                               core.sc_x(BONE, 0.4), z=zt, name="crop")
        crops.append((ob, x, y, sx, sy))
    mono(sc, "FIG. 12   SCALE   BRIDGE 2", -9.36, 4.95, 0.115, core.sc_x(BONE, 0.5))
    mono(sc, "TOKENS / PARAM", 8.95, 5.02, 0.095, core.sc_x(BONE, 0.45), align="RIGHT")
    cnt = []
    for i, v in enumerate(["20", "200", "2,000", "20,000"]):
        o = mono(sc, v, 8.95, 4.58, 0.42, SIG if i == 3 else BONE, align="RIGHT", name=f"cnt{i}")
        vis(o, 1, i == 0)
        cnt.append(o)

    times = build_press(sc, L1, c2)
    for i, o in enumerate(cnt):
        vis(o, 1, i == 0)
        if i + 1 < len(cnt):
            vis(o, F(sc, times[min(i + 1, 4)]), False)
    for i, o in enumerate(cnt[1:], start=1):
        vis(o, F(sc, times[min(i, 4)]), True)
        vis(o, F(sc, c2), False)

    qc_t = [c2, kick_near(L2["words"][1]["start"]), kick_near(L2["words"][2]["start"]), kick_near(L2["words"][4]["start"])]
    logs = [
        "QC  " + timecode(qc_t[0]) + "  TITLE-SAFE   VIOLATION   +8.4%",
        "QC  " + timecode(qc_t[1]) + "  ACTION-SAFE  VIOLATION   +3.1%",
        "QC  " + timecode(qc_t[2]) + "  FRAME EDGE   BOWED       +0.4%",
        "QC  " + timecode(qc_t[3]) + "  CROP MARKS   LOST        FAIL",
    ]
    for i, (t, s) in enumerate(zip(qc_t, logs)):
        o = mono(sc, s, 8.95, -4.66 - i * 0.215, 0.10, SIG if i == 3 else core.sc_x(BONE, 0.5),
                 align="RIGHT", z=zt - 0.5, name=f"qc{i}")
        vis(o, 1, False)
        vis(o, F(sc, t), True)

    rows, row_in = build_fences(sc, L2, c2, c3)
    for i, target in enumerate([title, action]):
        f = F(sc, qc_t[i])
        base = core.sc_x(BONE, 0.16 if i == 0 else 0.10)
        core.color_at(target, max(1, f - 1), base)
        core.color_at(target, f, SIG)
        core.color_at(target, min(sc.frame_end, f + 9), core.sc_x(SIG, 0.55))
        core.color_at(target, min(sc.frame_end, f + 20), base)
        core.set_interp(target, "LINEAR", "color")
        target.scale = (1, 1, 1)
        target.keyframe_insert("scale", frame=max(1, f - 1))
        target.scale = (1.03, 1.04, 1)
        target.keyframe_insert("scale", frame=f + 2)
        target.scale = (1, 1, 1)
        target.keyframe_insert("scale", frame=f + 15)
        core.set_interp(target, "BEZIER", "scale")
    f3, f4 = F(sc, qc_t[2]), F(sc, qc_t[3])
    for j, ob in enumerate(border):
        vec = [(0, -0.16), (0, 0.16), (-0.16, 0), (0.16, 0)][j]
        ob.keyframe_insert("location", frame=max(1, f3 - 1))
        ob.location = (vec[0] * 2.8, vec[1] * 2.8, 0)
        ob.keyframe_insert("location", frame=f3 + 8)
        ob.location = (vec[0] * 0.4, vec[1] * 0.4, 0)
        ob.keyframe_insert("location", frame=f3 + 22)
        core.set_interp(ob, "BEZIER", "location")
    for j, (ob, x, y, sx, sy) in enumerate(crops):
        ob.keyframe_insert("location", frame=max(1, f4 - 1))
        ob.keyframe_insert("rotation_euler", frame=max(1, f4 - 1))
        ob.location = (sx * 5.2, sy * 4.2, 0)
        ob.rotation_euler = (0, 0, (1 if sx * sy > 0 else -1) * 1.1)
        ob.keyframe_insert("location", frame=f4 + 6)
        ob.keyframe_insert("rotation_euler", frame=f4 + 6)
        core.set_interp(ob, "BEZIER", "location")
        core.set_interp(ob, "BEZIER", "rotation_euler")
        vis(ob, f4 + 9, False)

    c3cam, c4cam = build_rest(sc, L3, L4, c3, c4)
    m1 = sc.timeline_markers.new("m1", frame=1); m1.camera = c1
    m3 = sc.timeline_markers.new("m3", frame=F(sc, c3)); m3.camera = c3cam
    m4 = sc.timeline_markers.new("m4", frame=F(sc, c4)); m4.camera = c4cam

    sc.render.filepath = os.path.join(core.OUT, "frames", name, "####")
    os.makedirs(os.path.dirname(sc.render.filepath), exist_ok=True)
    return sc
