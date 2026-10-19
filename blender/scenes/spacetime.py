"""spacetime — four movements of one idea (plate 7)."""
import bpy, math, os, sys
from mathutils import Vector, Quaternion, Matrix
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pdoom import core, data, motifs
from pdoom.core import (PAL, clamp, lerp, smoothstep, ease_out_expo, ease_in_expo,
                        ease_in_out_cubic, ease_out_cubic, ease_out_back, hash01, sc_x)

INK, BONE, SIG, EMB, GRAPH, ASH, BLOOD, ACID = (
    PAL["ink"], PAL["bone"], PAL["signal"], PAL["ember"], PAL["graphite"], PAL["ash"],
    PAL["blood"], PAL["acid"])
TAU = math.tau
SCN = "spacetime"
T0 = data.SCENES[SCN]["start"]
FEND = data.SCENES[SCN]["frames"]
sc = None


def D(k):
    return core.sc_x(BONE, k)


def txt(body, font, size, color, x, y, z=0.0, align="LEFT", ay="BOTTOM_BASELINE",
        rot=0.0, hot=False, name=None, spacing=1.0):
    return core.add_text(sc, body, font, size, color, (x, y, z), rot=(0, 0, rot),
                         align_x=align, align_y=ay, hot=hot, name=name, spacing=spacing)


def multi_curve(splines, width, color, name, z=0.0, hot=False, res=0, mat=None, cyclic=False):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = max(width / 2.0, 0.0002)
    cu.bevel_resolution = res
    cu.resolution_u = 2
    n = 0
    for item in splines:
        if isinstance(item, tuple) and len(item) == 2 and isinstance(item[1], bool):
            pts, cyc = item
        else:
            pts, cyc = item, cyclic
        if len(pts) < 2:
            continue
        sp = cu.splines.new("POLY")
        sp.points.add(len(pts) - 1)
        for i, p in enumerate(pts):
            sp.points[i].co = (p[0], p[1], p[2] if len(p) > 2 else z, 1)
        sp.use_cyclic_u = bool(cyc)
        n += 1
    cu.materials.append(mat or (core.mat_hot() if hot else core.mat_type()))
    ob = bpy.data.objects.new(name, cu)
    sc.collection.objects.link(ob)
    ob.color = (*color, 1.0)
    return ob


VIS = {}
VIS0 = {}


def fit(body, font, width):
    m = core.measure(sc, body, font, 1.0)
    return width / m if m > 0 else 1.0


def show(ob, f, on=True):
    VIS.setdefault(ob, {})[max(1, int(f))] = bool(on)


def initial(ob, hidden=True):
    VIS0[ob] = bool(hidden)


def apply_vis():
    for ob, m in VIS.items():
        fs = sorted(m.items())
        ob.hide_render = VIS0.get(ob, True)
        ob.keyframe_insert("hide_render", frame=1)
        for f, on in fs:
            ob.hide_render = not on
            ob.keyframe_insert("hide_render", frame=f)


def fade_col(ob, f0, f1, c0=None, c1=(0, 0, 0)):
    core.color_at(ob, max(1, f0), c0 if c0 is not None else tuple(ob.color)[:3])
    core.color_at(ob, max(1, f1), c1)
    core.set_interp(ob, "BEZIER", "color")


def bake_curve(ob, fn, f0, f1, step=2):
    cu = ob.data
    sp = cu.splines[0]
    for f in range(max(1, f0), min(FEND, f1) + 1, step):
        t = data.frame_to_time(SCN, f)
        for i, p in enumerate(sp.points):
            p.co.y = fn(p.co.x, t)
        for i in range(len(sp.points)):
            cu.keyframe_insert('splines[0].points[%d].co' % i, frame=f)
    for fc in _fcurves_cu(cu):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"


def _fcurves_cu(cu):
    ad = cu.animation_data
    if not ad or not ad.action:
        return []
    act = ad.action
    if hasattr(act, "layers") and len(act.layers):
        fcs = []
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    fcs.extend(bag.fcurves)
        return fcs
    return list(act.fcurves)


def bake_cam(cam, fn, f0, f1, step=1):
    for f in range(max(1, f0), min(FEND, f1) + 1, step):
        loc, tgt, roll = fn(f)
        cam.location = loc
        d = Vector(tgt) - Vector(loc)
        q = d.to_track_quat("-Z", "Y")
        if roll:
            q = q @ Quaternion((0, 0, 1), roll)
        cam.rotation_euler = q.to_euler()
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
    core.set_interp(cam, "LINEAR", "location")
    core.set_interp(cam, "LINEAR", "rotation_euler")


# ------------------------------------------------------------------ lens maths
RE = 1.55
RS = 1.20
PH = 1.30


def lensed_grid(step=1.0, ext=17.0, n=112, bmin=0.16):
    outer, inner = [], []
    m = int(ext / step)
    for g in range(-m, m + 1):
        c = g * step
        for axis in (0, 1):
            po, pi = [], []
            for i in range(n + 1):
                t = -ext + 2 * ext * i / n
                x, y = (t, c) if axis == 0 else (c, t)
                b = math.hypot(x, y)
                if b < bmin:
                    if len(po) > 1:
                        outer.append(po)
                    if len(pi) > 1:
                        inner.append(pi)
                    po, pi = [], []
                    continue
                ro = 0.5 * (b + math.sqrt(b * b + 4 * RE * RE))
                ri = 0.5 * (math.sqrt(b * b + 4 * RE * RE) - b)
                ang = math.atan2(y, x) + 0.55 * min(1.0, RE * RE / (b * b))
                ca, sa = math.cos(ang), math.sin(ang)
                po.append((ca * ro, sa * ro))
                pi.append((-ca * ri, -sa * ri))
            if len(po) > 1:
                outer.append(po)
            if len(pi) > 1:
                inner.append(pi)
    return outer, inner


def phase(t):
    return -TAU * data.beat_at(t) / 16.0


def amp(t):
    on = smoothstep(T0, T0 + 0.9, t)
    return 1.14 * on * (1.0 + 0.05 * data.env("kick", t))


WAVE_C = -0.98
WAVE_K = 0.72


def wfun(x, t):
    return (WAVE_C + amp(t) * math.sin(WAVE_K * x + phase(t))
            * (1.0 + 0.05 * math.sin(0.37 * x + 1.7 * phase(t))))


# ------------------------------------------------------------------ movement I
def build_scope(cam):
    world_z = -1.0
    dx, dy = 1.92, 1.80
    segs_major, segs_axis, ticks = [], [], []
    for i in range(11):
        x = -9.6 + i * dx
        (segs_axis if abs(x) < 0.01 else segs_major).append(((x, -5.4), (x, 5.4)))
    for j in range(7):
        y = -5.4 + j * dy
        (segs_axis if abs(y) < 0.01 else segs_major).append(((-9.6, y), (9.6, y)))
    for i in range(-48, 49):
        x = i * dx / 5.0
        if abs(x) > 0.05:
            ticks.append(((x, -0.055), (x, 0.055)))
    for j in range(-26, 27):
        y = j * dy / 5.0
        if abs(y) > 0.05:
            ticks.append(((-0.055, y), (0.055, y)))
    gm = multi_curve(segs_major, 0.010, D(0.15), "grat_major", z=world_z)
    ga = multi_curve(segs_axis, 0.014, D(0.26), "grat_axis", z=world_z)
    gt = multi_curve(ticks, 0.010, D(0.17), "grat_ticks", z=world_z)
    dotsegs = []
    for i in range(-40, 41):
        for j in range(-22, 23):
            x, y = i * dx / 5.0, j * dy / 5.0
            if abs(x) < 0.08 or abs(y) < 0.08:
                continue
            if i % 2 == 0 and j % 2 == 0:
                dotsegs.append(((x - 0.006, y), (x + 0.006, y)))
    gd = multi_curve(dotsegs, 0.012, D(0.115), "grat_dots", z=world_z)

    # CRT faceplate
    bz = 0.20
    bez = []
    for inset, wd, col in ((0.0, 0.016, D(0.30)), (0.16, 0.008, D(0.16))):
        x0, x1 = -9.6 + bz + inset, 9.6 - bz - inset
        y0, y1 = -5.4 + bz + inset, 5.4 - bz - inset
        bez.append(multi_curve([[(x0, y0), (x1, y0), (x1, y1), (x0, y1)]], wd, col,
                               "bezel%d" % inset, z=2.0, cyclic=True))

    hud = [txt("CH1   0.2 V/div   DC", "mono_med", 0.135, D(0.55), -8.9, 4.74),
           txt("f = 1.600 Hz   ·   TRIG'D", "mono_med", 0.135, D(0.38), -8.9, 4.44),
           txt("TRIG'D   CH1", "mono_med", 0.135, D(0.55), 8.9, 4.74, align="RIGHT"),
           txt("M 41.7 ms/div", "mono_med", 0.135, D(0.38), 8.9, 4.44, align="RIGHT"),
           txt("CH2   P(doom)", "mono_med", 0.13, D(0.45), -8.9, -4.62),
           txt("%.2f" % data.pdoom(T0 + 1.2), "mono_med", 0.13, SIG, -6.62, -4.62),
           txt("(muted)", "mono_med", 0.13, D(0.3), -5.92, -4.62),
           txt("loss 0.0213   ·   stable", "mono_med", 0.13, D(0.42), 8.9, -4.62, align="RIGHT")]
    flat = [(-8.9 + 3.2 * i / 40.0, -5.18 + 0.012 * math.sin(i * 1.7)) for i in range(41)]
    hud.append(multi_curve([flat], 0.012, D(0.22), "ch2trace", z=world_z + 0.01))

    # ---- phosphor trace + persistence echoes
    N = 220
    xs = [-10.6 + 21.2 * i / (N - 1) for i in range(N)]
    main = multi_curve([[(x, wfun(x, T0 + 1.2)) for x in xs]], 0.032, (1.0, 0.44, 0.24),
                       "trace", z=0.0, hot=True)
    halo = multi_curve([[(x, wfun(x, T0 + 1.2)) for x in xs]], 0.11, (1.0, 0.30, 0.12),
                       "trace_halo", z=-0.04, hot=False)
    echoes = []
    for k, (dp, dk) in enumerate([(0.55, 0.30), (1.15, 0.15), (1.8, 0.07)]):
        e = multi_curve([[(x, WAVE_C + 1.14 * math.sin(WAVE_K * x + phase(T0 + 1.2) - dp))
                          for x in xs]], 0.020, core.sc_x(SIG, dk), "echo%d" % k, z=-0.02)
        echoes.append(e)
    bake_curve(main, wfun, 1, 92, 2)
    bake_curve(halo, wfun, 1, 92, 2)

    beam = core.add_uv_sphere(sc, (0, 0, 0.12), 0.050, (1.0, 0.72, 0.5), hot=True, name="beam")
    for f in range(1, 82):
        t = data.frame_to_time(SCN, f)
        ph = (data.beat_at(t) % 1.0)
        bx = -8.9 + 17.8 * ph
        beam.location = (bx, wfun(bx, t) + 0.03, 0.12)
        beam.keyframe_insert("location", frame=f)
        beam.hide_render = ph < 0.02 or ph > 0.985
        beam.keyframe_insert("hide_render", frame=f)
    core.set_interp(beam, "LINEAR", "location")

    # ---- lyric: one clean line, tethered to the trace
    l1 = data.line("stable training run")
    ws = l1["words"]
    fnt, size = "archivo", 1.05
    widths = [core.measure(sc, w["w"], fnt, size) for w in ws]
    sw = core.space_width(sc, fnt, size)
    gap = 0.12
    total = sum(widths) + (sw + gap) * (len(ws) - 1)
    k = min(1.0, 16.7 / total)
    size *= k
    widths = [v * k for v in widths]
    sw *= k
    x = -8.45
    base_y = 0.96
    words = []
    for i, w in enumerate(ws):
        cx = x + widths[i] * 0.5
        ob = txt(w["w"], fnt, size, D(0.30), x, base_y, 0.4, align="LEFT", name="l1_%d" % i)
        words.append((w, ob, cx, widths[i]))
        x += widths[i] + sw + gap
    core.sync_words(sc, [(w, ob) for w, ob, cx, wd in words], sung=BONE, pre=0.30)

    probes = [core.add_uv_sphere(sc, (cx, base_y, 0.45), 0.048, SIG, hot=True, name="probe%d" % i)
              for i, (w, ob, cx, wd) in enumerate(words)]
    tethers = [multi_curve([[(cx, base_y), (cx, base_y)]], 0.009, D(0.30), "tether%d" % i, z=0.42)
               for i, (w, ob, cx, wd) in enumerate(words)]

    for f in range(1, 81):
        t = data.frame_to_time(SCN, f)
        for i, (w, ob, cx, wd) in enumerate(words):
            wy = wfun(cx, t)
            bob = 0.085 * math.sin(WAVE_K * cx + phase(t)) + 0.02
            ob.location = (ob.location.x, base_y + bob, 0.4)
            ob.rotation_euler = (0, 0, 0)
            ob.keyframe_insert("location", frame=f)
            pr = probes[i]
            pr.location = (cx, wy + 0.03, 0.45)
            pr.keyframe_insert("location", frame=f)
            cu = tethers[i].data
            sp = cu.splines[0]
            sp.points[1].co = (cx, wy + 0.03, 0.42, 1)
            cu.keyframe_insert('splines[0].points[1].co', frame=f)
        for ob in [o for w, o, c, wd in words] + probes + tethers:
            core.set_interp(ob, "LINEAR", "location")
    for i, tb in enumerate(tethers):
        for fc in _fcurves_cu(tb.data):
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"

    # ---- shutdown on "But": the beam collapses to a vertical white-hot line, then a point
    f_but = core.frame_of(sc, data.word("singularity", 0)["start"])

    def squeeze(ob):
        cu = ob.data
        sp = cu.splines[0]
        xs = [p.co.x for p in sp.points]
        t_but = data.frame_to_time(SCN, f_but)
        ys = [wfun(x, t_but) for x in xs]
        seq = [(1.0, 1.0), (0.55, 1.0), (0.20, 0.99), (0.055, 0.95),
               (0.012, 0.72), (0.006, 0.30), (0.004, 0.02)]
        # shrink everything toward the centre so the tube cannot fold onto itself
        for k in range(len(seq)):
            u = [0.0, 0.30, 0.62, 0.84, 0.94, 0.985, 1.0][k]
            seq[k] = (1.0 - u, 1.0 - u)
        for k, (sx, sy) in enumerate(seq):
            f = f_but + k
            for i, p in enumerate(sp.points):
                p.co.x = xs[i] * sx
                p.co.y = WAVE_C + (ys[i] - WAVE_C) * sy
            for i in range(len(sp.points)):
                cu.keyframe_insert('splines[0].points[%d].co' % i, frame=f)

    squeeze(main)
    squeeze(halo)
    for e in echoes:
        squeeze(e)
    core.color_at(main, f_but, (1.0, 0.44, 0.24))
    core.color_at(main, f_but + 4, (1.0, 0.88, 0.72))
    core.color_at(halo, f_but, (1.0, 0.30, 0.12))
    core.color_at(halo, f_but + 4, (1.0, 0.64, 0.40))
    for e in echoes:
        c0 = tuple(e.color)[:3]
        core.color_at(e, f_but, c0)
        core.color_at(e, f_but + 4, sc_x(c0, 0.3))
    for ob in [main, halo] + echoes:
        show(ob, f_but + 7, False)
    for w, ob, cx, wd in words:
        core.color_at(ob, f_but - 3, BONE)
        core.color_at(ob, f_but + 2, (0, 0, 0))
        show(ob, f_but + 4, False)
        core.set_interp(ob, "BEZIER", "color")
    for pr in probes:
        core.color_at(pr, f_but - 2, SIG)
        core.color_at(pr, f_but + 2, (0, 0, 0))
        show(pr, f_but + 4, False)
        core.set_interp(pr, "BEZIER", "color")
    for tb in tethers:
        c0 = tuple(tb.color)[:3]
        core.color_at(tb, f_but - 2, c0)
        core.color_at(tb, f_but + 2, (0, 0, 0))
        show(tb, f_but + 4, False)
        core.set_interp(tb, "BEZIER", "color")
    for ob in [gm, ga, gt, gd, main, halo] + echoes + [o for w, o, c, wd in words] + probes + tethers:
        initial(ob, False)
    beam.hide_render = True
    beam.keyframe_insert("hide_render", frame=93)
    return dict(grat=[gm, ga, gt, gd], main=main, halo=halo, echoes=echoes, beam=beam,
                words=words, probes=probes, tethers=tethers, hud=hud, bez=bez)


# ------------------------------------------------------------------ movement II
def build_hole():
    zt = 2.5
    outer, inner = lensed_grid()
    g = multi_curve(outer, 0.010, D(0.30), "lens_grid", z=-1.2)
    gi = multi_curve(inner, 0.008, core.sc_x(EMB, 0.32), "lens_grid_in", z=-1.25)
    # photon ring + secondary
    ring_splines = []
    for rr in (PH, PH * 1.06):
        ring_splines.append(([(rr * math.cos(i / 160 * TAU), rr * math.sin(i / 160 * TAU))
                              for i in range(160)], True))
    rings = multi_curve(ring_splines, 0.009, (1.0, 0.34, 0.12), "photon_ring", z=0.05, hot=False)
    glow = multi_curve([([((RS + 0.012) * math.cos(i / 120 * TAU),
                           (RS + 0.012) * math.sin(i / 120 * TAU)) for i in range(120)], True)],
                       0.014, core.sc_x(EMB, 0.42), "horizon_rim", z=0.02)
    dial = []
    for i in range(96):
        a = i / 96 * TAU
        r0 = 1.66 + (0.10 if i % 8 == 0 else 0.05)
        dial.append(((r0 * math.cos(a), r0 * math.sin(a)), (1.86 * math.cos(a), 1.86 * math.sin(a))))
    dial_ob = multi_curve(dial, 0.007, D(0.28), "dial", z=-0.1)
    for ob in (g, gi, rings, glow, dial_ob):
        show(ob, 1, False)

    hole = core.add_uv_sphere(sc, (0, 0, 0), RS, (0, 0, 0), name="hole", segs=64, rings=32)
    hole.data.materials[0] = core.mat_emit((0, 0, 0), 1.0)
    show(hole, 1, False)

    disk_rig = bpy.data.objects.new("disk_rig", None)
    sc.collection.objects.link(disk_rig)
    disk_rig.rotation_euler = (math.radians(11), 0, 0)

    def spirals(n, r0, r1, turns, seed):
        out = []
        for i in range(n):
            a0 = hash01(seed, i, 1) * TAU
            rr = r0 + (r1 - r0) * hash01(seed, i, 2)
            pts = []
            for k in range(31):
                u = k / 30.0
                rad = rr * (1 - u) + r0 * u
                ang = a0 + turns * u + 0.16 * math.sin(u * 9 + i)
                pts.append((rad * math.cos(ang), rad * math.sin(ang), 0.0))
            out.append(pts)
        return out

    layers = []
    specs = [
        ("disk_out", 0, 62, 2.9, 8.4, 2.2, core.sc_x(BONE, 0.13), 0.007, False),
        ("disk_mid", 1, 80, 1.6, 4.2, 2.8, core.sc_x(BONE, 0.21), 0.008, False),
        ("disk_in", 2, 46, 1.31, 1.95, 3.2, core.sc_x(EMB, 0.34), 0.008, False),
    ]
    for nm, seed, n, r0, r1, turns, col, wd, hot in specs:
        ob = multi_curve(spirals(n, r0, r1, turns, seed), wd, col, nm, z=0.0, hot=hot)
        ob.parent = disk_rig
        ob.matrix_parent_inverse = Matrix.Identity(4)
        show(ob, 1, False)
        layers.append(ob)
    arcs = []
    for a0, a1, rr in [(-2.4, -1.2, 1.34), (0.55, 1.55, 1.325),
                       (2.1, 2.8, 1.335)]:
        arcs.append([(rr * math.cos(a0 + (a1 - a0) * i / 30),
                      rr * math.sin(a0 + (a1 - a0) * i / 30)) for i in range(31)])
    arc_ob = multi_curve(arcs, 0.012, (1.0, 0.46, 0.22), "disk_arcs", z=0.08, hot=True)
    arc_ob.parent = disk_rig
    arc_ob.matrix_parent_inverse = Matrix.Identity(4)
    show(arc_ob, 1, False)

    # ---- NOW: the hole is the O
    now_size = 4.5
    n_ob = txt("N", "archivo", now_size, BONE, -1.30, -1.06, zt, align="RIGHT", name="N")
    w_ob = txt("W", "archivo", now_size, BONE, 1.30, -1.06, zt, align="LEFT", name="W")
    but_ob = txt("BUT", "archivo", 2.05, BONE, 0.0, 2.60, zt, align="CENTER", name="but")
    the_ob = txt("the", "archivo300", 0.86, D(0.60), -4.55, 0.16, zt, rot=-0.08, name="the")
    for ob in (n_ob, w_ob, but_ob, the_ob):
        show(ob, 1, False)

    # ---- SINGULARITY'S wraps the photon ring
    word = data.words("singularity", 0)[3]
    fnt_r, size_r, R = "archivo", 1.26, 2.62
    body = "SINGULARITY’S"
    adv = [core.measure(sc, ch, fnt_r, size_r) + 0.05 for ch in body]
    span = sum(adv) / R
    a = math.radians(90) + span / 2.0
    prog_span = (word["end"] - word["start"]) * 0.85
    glyphs = []
    for i, ch in enumerate(body):
        a -= adv[i] / 2.0 / R
        px, py = R * math.cos(a), R * math.sin(a)
        ob = txt(ch, fnt_r, size_r, D(0.16), px, py, zt,
                 align="CENTER", ay="CENTER", rot=(a - math.pi / 2), name="ring_%d" % i)
        show(ob, 1, False)
        t_i = word["start"] + (i / len(body)) * prog_span
        glyphs.append((ob, t_i))
        a -= adv[i] / 2.0 / R

    # ---- BEGUN, bent into a smile
    word_b = data.words("singularity", 0)[4]
    sizeb, Rb = 1.40, 2.16
    body_b = "BEGUN"
    advb = [core.measure(sc, ch, "archivo", sizeb) + 0.07 for ch in body_b]
    spanb = sum(advb) / Rb
    ab = math.radians(270) - spanb / 2.0
    begun = []
    for i, ch in enumerate(body_b):
        ad = advb[i] / Rb
        ab += ad / 2.0
        px, py = Rb * math.cos(ab), Rb * math.sin(ab)
        ob = txt(ch, "archivo", sizeb, D(0.18), px, py, zt,
                 align="CENTER", ay="CENTER", rot=(ab - math.pi * 1.5), name="begun_%d" % i)
        show(ob, 1, False)
        begun.append(ob)
        ab += ad / 2.0

    shocks = []
    ob = multi_curve([([(1.30 * math.cos(i / 90 * TAU), 1.30 * math.sin(i / 90 * TAU))
                       for i in range(90)], True)], 0.010, (1.0, 0.72, 0.5),
                     "shock0", z=0.1, hot=True)
    show(ob, 1, False)
    shocks.append(ob)
    return dict(hole=hole, rings=rings, glow=glow, grid=g, grid_in=gi, dial=dial_ob,
                disk=layers, arcs=arc_ob, rig=disk_rig, n=n_ob, w=w_ob, but=but_ob,
                the=the_ob, glyphs=glyphs, begun=begun, shocks=shocks, zt=zt)


def animate_hole(H, S, cam):
    f_but = core.frame_of(sc, data.word("singularity", 0)["start"])
    f_now = core.frame_of(sc, data.word("singularity", 1)["start"])
    f_the = core.frame_of(sc, data.word("singularity", 2)["start"])
    f_sing = core.frame_of(sc, data.word("singularity", 3)["start"])
    f_sing_end = core.frame_of(sc, data.word("singularity", 3)["end"])
    f_begun = core.frame_of(sc, data.word("singularity", 4)["start"])
    f_end = core.frame_of(sc, data.word("singularity", 4)["end"])
    f_down = core.frame_of(sc, data.downbeats_between(41.9, 42.2)[0])

    for ob, f in ((H["but"], f_but), (H["n"], f_now), (H["w"], f_now), (H["the"], f_the)):
        show(ob, f, True)
    for ob in (H["hole"], H["rings"], H["glow"], H["grid"], H["grid_in"], H["dial"],
               H["disk"][0], H["disk"][1], H["disk"][2], H["arcs"]):
        show(ob, f_now, True)
    for k, ob in enumerate(H["shocks"]):
        show(ob, f_now, True)
        for f in range(f_now, f_now + 14):
            u = (f - f_now) / 13.0
            sc_ = 1.0 + 0.9 * ease_out_expo(u)
            ob.scale = (sc_, sc_, 1)
            ob.keyframe_insert("scale", frame=f)
            ob.data.bevel_depth = 0.005 / sc_
            ob.data.keyframe_insert("bevel_depth", frame=f)
            c = max(0.0, 1.0 - u) ** 1.6
            ob.color = (c, c * 0.42, c * 0.20, 1)
            ob.keyframe_insert("color", frame=f)
        show(ob, f_now + 13, False)
    for f in range(f_now, f_now + 10):
        u = (f - f_now) / 9.0
        s = max(0.001, ease_out_back(u, 2.0))
        H["hole"].scale = (s, s, s)
        H["hole"].keyframe_insert("scale", frame=f)
    H["hole"].scale = (1, 1, 1)
    H["hole"].keyframe_insert("scale", frame=f_now + 10)
    for ob in (H["rings"], H["glow"]):
        for f, s in ((f_now, 0.15), (f_now + 4, 1.12), (f_now + 9, 1.0)):
            ob.scale = (s, s, 1)
            ob.keyframe_insert("scale", frame=f)
        core.set_interp(ob, "BEZIER", "scale")
    for ob in (H["grid"], H["grid_in"]):
        c0 = tuple(ob.color)[:3]
        core.color_at(ob, f_now, (0, 0, 0))
        core.color_at(ob, f_now + 8, c0)
        core.set_interp(ob, "BEZIER", "color")
    # the scope graticule dissolves into the lensed one
    for ob in S["grat"]:
        c0 = tuple(ob.color)[:3]
        core.color_at(ob, f_now - 1, c0)
        core.color_at(ob, f_now + 10, (0, 0, 0))
        show(ob, f_now + 11, False)
        core.set_interp(ob, "BEZIER", "color")
    for ob in S["hud"]:
        show(ob, f_now, False)
    for ob in S["bez"]:
        show(ob, f_now + 8, False)
    for k, ob in enumerate(H["disk"] + [H["arcs"]]):
        rate = [0.30, 0.48, 0.85, 0.85][k]
        for f in range(f_now, f_end + 2, 2):
            t = data.frame_to_time(SCN, f)
            ob.rotation_euler = (0, 0, -rate * (t - data.frame_to_time(SCN, f_now)))
            ob.keyframe_insert("rotation_euler", frame=f)
        core.set_interp(ob, "LINEAR", "rotation_euler")
    for ob, f, sc0 in ((H["but"], f_but, 1.18), (H["n"], f_now, 1.10), (H["w"], f_now, 1.10)):
        ob.scale = (sc0, sc0, 1)
        ob.keyframe_insert("scale", frame=max(1, f - 1))
        ob.scale = (1, 1, 1)
        ob.keyframe_insert("scale", frame=f + 3)
        core.set_interp(ob, "BEZIER", "scale")
    for ob, dx, dy in ((H["n"], -3.2, 0.0), (H["w"], 3.2, 0.0), (H["but"], 0.0, 1.6)):
        base = ob.location.copy()
        ob.keyframe_insert("location", frame=f_down - 1)
        ob.location = (base.x + dx, base.y + dy, base.z)
        ob.keyframe_insert("location", frame=f_down + 7)
        core.set_interp(ob, "BEZIER", "location")
        fade_col(ob, f_down + 1, f_down + 7, None)
        show(ob, f_down + 8, False)
    fade_col(H["the"], 111, 118)

    for ob, t_i in H["glyphs"]:
        f_i = core.frame_of(sc, t_i)
        show(ob, f_sing - 4, True)
        core.color_at(ob, f_sing - 4, D(0.16))
        core.color_at(ob, max(f_sing - 3, f_i - 2), D(0.16))
        core.color_at(ob, f_i, BONE)
        core.set_interp(ob, "BEZIER", "color")
    for i, ob in enumerate(H["begun"]):
        show(ob, f_begun, True)
        core.color_at(ob, f_begun, D(0.10))
        core.color_at(ob, f_begun + 2 + i * 2, BONE)
        core.set_interp(ob, "BEZIER", "color")

    # annotations
    ann = [txt("EVENT HORIZON   ·   OBSERVATION 1", "mono_med", 0.125, D(0.34), -6.25, 3.30),
           txt("r_s = 1.20    M = 6.5 × 10⁹ M☉    a = 0.94", "mono_med", 0.125, D(0.34), -6.25, -3.28),
           txt("NO SIGNAL", "mono_med", 0.125, D(0.34), 6.25, 3.30, align="RIGHT")]
    for ob in ann:
        show(ob, f_now, True)


    for f in range(1, FEND + 1):
        t = data.frame_to_time(SCN, f)
        if f <= f_but:
            s = lerp(19.2, 18.9, smoothstep(T0, data.frame_to_time(SCN, f_but), t))
        elif f <= f_down:
            s = lerp(18.9, 18.4, (f - f_but) / float(f_down - f_but))
        elif f <= f_sing_end:
            s = lerp(18.4, 14.6, ease_in_out_cubic((f - f_down) / float(f_sing_end - f_down)))
        elif f <= 188:
            s = lerp(14.6, 14.0, (f - f_sing_end) / 24.0)
        else:
            s = lerp(14.0, 3.0, ease_in_expo(clamp((f - 188) / 6.0)))
        cam.data.ortho_scale = s
        cam.data.keyframe_insert("ortho_scale", frame=f)
        dx = dy = 0.0
        for k, ht in enumerate([data.frame_to_time(SCN, f_now)] + data.downbeats_between(42.0, 52.8)):
            if t >= ht:
                aq = 0.10 * math.exp(-(t - ht) * 9.0)
                dx += (hash01(3, k, f) - 0.5) * 2 * aq
                dy += (hash01(7, k, f * 3 + 1) - 0.5) * 2 * aq
        cam.location = (dx, dy, 50)
        cam.keyframe_insert("location", frame=f)
    core.set_interp(cam, "LINEAR", "ortho_scale")
    core.set_interp(cam, "LINEAR", "location")

    # (no full-frame flash: the fall-through ends on the black of the shadow itself)
    for ob in ([H["hole"], H["rings"], H["glow"], H["grid"], H["grid_in"], H["dial"],
                H["arcs"], H["the"]] + H["disk"] + [o for o, t in H["glyphs"]]
               + H["begun"] + H["shocks"] + ann):
        show(ob, 194, False)


# ------------------------------------------------------------------ movement III
V_A, V_S = 5.4, 1.75


def well(r):
    return -V_A / (1.0 + (r / V_S) ** 2)


def build_vortex():
    rings = []
    radii = [0.35 * (14.0 / 0.35) ** (i / 29.0) for i in range(30)]
    for r in radii:
        n = max(28, int(40 + r * 5))
        rings.append(([(r * math.cos(i / n * TAU), r * math.sin(i / n * TAU), well(r))
                       for i in range(n)], True))
    ring_ob = multi_curve(rings, 0.010, D(0.13), "v_rings", z=0.0)
    spokes = []
    for k in range(36):
        a = k / 36.0 * TAU
        pts = [(r * math.cos(a), r * math.sin(a), well(r))
               for r in [0.3 + (14.0 - 0.3) * (i / 47.0) ** 1.4 for i in range(48)]]
        spokes.append(pts)
    spoke_ob = multi_curve(spokes, 0.008, D(0.10), "v_spokes", z=0.0)
    inner_rings = []
    for r in [0.55, 0.8, 1.1, 1.5, 2.0, 2.7, 3.6, 4.8]:
        n = max(40, int(50 + r * 10))
        inner_rings.append(([(r * math.cos(i / n * TAU), r * math.sin(i / n * TAU), well(r))
                             for i in range(n)], True))
    inner_ob = multi_curve(inner_rings, 0.011, D(0.30), "v_inner_rings", z=0.0)

    def stream(n, seed, r0, r1):
        out = []
        for i in range(n):
            a0 = hash01(seed, i, 1) * TAU
            rr = r0 + (r1 - r0) * hash01(seed, i, 2)
            pts = []
            for k in range(26):
                u = k / 25.0
                r = rr + (0.45 - rr) * u
                a = a0 + 2.35 * math.log(rr / r) + 0.10 * math.sin(u * 7.0 + i)
                pts.append((r * math.cos(a), r * math.sin(a), well(r) + 0.03))
            out.append(pts)
        return out

    groups = []
    for nm, seed, n, r0, r1, col, wd in [
        ("v_out", 11, 30, 5.0, 13.5, D(0.085), 0.008),
        ("v_mid", 12, 40, 2.2, 6.0, D(0.16), 0.009),
        ("v_in", 13, 38, 0.7, 2.8, core.sc_x(EMB, 0.44), 0.010),
    ]:
        ob = multi_curve(stream(n, seed, r0, r1), wd, col, nm, z=0.0)
        groups.append(ob)
    core_hot = core.add_uv_sphere(sc, (0, 0, well(0) + 0.10), 0.10, (1.0, 0.55, 0.32),
                                  hot=True, name="throat")
    throat_ring = multi_curve([([(0.22 * math.cos(i / 64 * TAU), 0.22 * math.sin(i / 64 * TAU),
                                 well(0.22) + 0.06) for i in range(64)], True)],
                              0.012, core.sc_x(EMB, 0.8), "throat_ring", z=0.0)
    for ob in [ring_ob, spoke_ob, inner_ob] + groups + [core_hot, throat_ring]:
        show(ob, 194, True)
    return dict(rings=ring_ob, spokes=spoke_ob, inner=inner_ob, groups=groups, core=core_hot,
                throat=throat_ring)


def build_vortex_cam():
    cam = core.add_camera_persp(sc, (0, 0, 10), (0, 0, 0), lens=30)
    cam.data.dof.use_dof = True
    cam.data.dof.aperture_fstop = 4.0
    keys = [
        (194, -1.95, 0.42, 9.4, -2.6, 30.0, -0.20),
        (232, -1.10, 0.72, 12.0, -2.4, 30.0, -0.08),
        (267, 0.35, 0.80, 12.5, -2.2, 30.0, 0.06),
        (329, 1.25, 1.16, 13.0, -1.9, 30.0, 0.0),
    ]

    def val(f, i):
        if f <= keys[0][0]:
            return keys[0][i]
        for a, b in zip(keys, keys[1:]):
            if f <= b[0]:
                u = ease_in_out_cubic((f - a[0]) / float(b[0] - a[0]))
                return lerp(a[i], b[i], u)
        return keys[-1][i]

    def fn(f):
        t = data.frame_to_time(SCN, f)
        az, el, rad, tz, lens, roll = (val(f, i) for i in range(1, 7))
        # a slow corkscrew on top of the crane + a beat punch
        az += 0.10 * math.sin((f - 194) / 26.0)
        pb = 0.0
        for b in data.beats_between(45.0, 52.8):
            fb = core.frame_of(sc, b)
            if 194 <= f and f >= fb:
                pb = max(pb, math.exp(-(f - fb) / 3.0))
        lens -= 1.2 * pb
        tgt = (0, 0, tz)
        pos = (math.cos(el) * math.cos(az) * rad,
               math.cos(el) * math.sin(az) * rad,
               tz + math.sin(el) * rad)
        return pos, tgt, roll + 0.015 * math.sin(f * 0.11)
    return cam, fn


def build_type_rig(cam):
    rig = bpy.data.objects.new("type_rig", None)
    sc.collection.objects.link(rig)
    rig.parent = cam
    rig.matrix_parent_inverse = Matrix.Identity(4)
    rig.location = (0, 0, -3.0)
    l3 = data.line("optimizing")
    ws = l3["words"]                       # And / you're / optimizing, / accelerating,
    size_s = 0.245
    size_b = fit("ACCELERATING,", "archivo", 2.72)
    txt_and = core.add_text(sc, "AND", "archivo", size_s, D(0.9), (-1.70, 0.66, 0.0),
                            name="m3_and")
    adv = core.measure(sc, "AND", "archivo", size_s) + core.space_width(sc, "archivo", size_s) + 0.01
    txt_you = core.add_text(sc, "YOU'RE", "archivo", size_s, D(0.9), (-1.70 + adv, 0.66, 0.0),
                            name="m3_youre")
    txt_opt = core.add_text(sc, "OPTIMIZING,", "archivo", size_b, D(0.75), (-1.70, 0.10, 0.0),
                            name="m3_opt")
    txt_acc = core.add_text(sc, "ACCELERATING,", "archivo", size_b, D(0.75), (-1.62, -0.66, 0.0),
                            name="m3_acc")
    for ob in (txt_and, txt_you, txt_opt, txt_acc):
        ob.parent = rig
        ob.matrix_parent_inverse = Matrix.Identity(4)
        show(ob, 194, True)
        show(ob, 330, False)
    # a hairline under the two long words, like a rule on a plotter sheet
    rules = []
    for y, x0, x1 in ((0.02, -1.70, 1.22), (-0.74, -1.62, 1.22)):
        r = core.add_polyline(sc, [(x0, y, 0.0), (x1, y, 0.0)], 0.006, D(0.25), name="m3_rule")
        r.parent = rig
        r.matrix_parent_inverse = Matrix.Identity(4)
        show(r, 194, True)
        show(r, 330, False)
        rules.append(r)
    pairs = [(txt_and, ws[0]), (txt_you, ws[1]), (txt_opt, ws[2]), (txt_acc, ws[3])]
    for ob, w in pairs:
        core.color_at(ob, 194, D(0.42))
        core.color_at(ob, max(194, core.frame_of(sc, w["start"]) - 3), D(0.42))
        core.color_at(ob, core.frame_of(sc, w["start"]), BONE)
        core.set_interp(ob, "BEZIER", "color")
    # stretch the two long words as they are sung
    for ob, w in ((txt_opt, ws[2]), (txt_acc, ws[3])):
        f0 = core.frame_of(sc, w["start"])
        for f, sx in ((f0, 1.0), (f0 + 10, 1.10), (f0 + 20, 1.0)):
            ob.scale = (sx, 1, 1)
            ob.keyframe_insert("scale", frame=f)
        core.set_interp(ob, "BEZIER", "scale")
    rig.scale = (1, 1, 1)
    return dict(rig=rig, objs=[txt_and, txt_you, txt_opt, txt_acc] + rules)


def animate_vortex(V, VC, camB, TR):
    f194 = 194
    # spin the streamline groups; keep spinning into movement IV
    rates = [0.22, 0.36, 0.58]
    for k, ob in enumerate(V["groups"]):
        for f in range(f194, FEND + 1, 2):
            t = data.frame_to_time(SCN, f)
            ob.rotation_euler = (0, 0, -rates[k] * (t - data.frame_to_time(SCN, f194)))
            ob.keyframe_insert("rotation_euler", frame=f)
        core.set_interp(ob, "LINEAR", "rotation_euler")
    # the throat pulses on the beat
    for f in range(f194, FEND + 1):
        t = data.frame_to_time(SCN, f)
        p = 1.0 + 0.5 * data.hit("kick", t)
        V["core"].scale = (p, p, p)
        V["core"].keyframe_insert("scale", frame=f)
    # camera B
    bake_cam(camB, VC, f194, 329)
    camB.data.dof.use_dof = True
    camB.data.dof.focus_distance = 4.0
    camB.data.dof.aperture_fstop = 4.0
    # focal punch on the beat, with the type rig compensated so the lyric never changes size
    beats = [core.frame_of(sc, b) for b in data.beats_between(45.0, 52.8)]
    for f in range(f194, 330):
        pb = 0.0
        for fb in beats:
            if f >= fb:
                pb = max(pb, math.exp(-(f - fb) / 3.0))
        lens = 30.0 - 1.1 * pb
        camB.data.lens = lens
        camB.data.keyframe_insert("lens", frame=f)
        k = 30.0 / lens
        TR["rig"].scale = (k, k, k)
        TR["rig"].keyframe_insert("scale", frame=f)
    core.set_interp(camB, "LINEAR", "lens")
    core.set_interp(TR["rig"], "LINEAR", "scale")
    return


# ------------------------------------------------------------------ movement IV
CLIP_PTS_RAW = None


def clip_outline(n=260):
    """Gem-clip outline in local units, long axis x in [-0.73, 0.64], y in [-0.36, 0.36]."""
    P = []

    def line(a, b, k=20):
        for i in range(k):
            P.append((lerp(a[0], b[0], i / k), lerp(a[1], b[1], i / k)))

    def arc(cx, cy, r, a0, a1, k=44):
        for i in range(k):
            a = lerp(a0, a1, i / k)
            P.append((cx + math.cos(a) * r, cy + math.sin(a) * r))

    line((-0.42, -0.18), (0.40, -0.18))
    arc(0.40, 0.0, 0.18, -math.pi / 2, math.pi / 2)
    line((0.40, 0.18), (-0.73, 0.18))
    arc(-0.73, -0.09, 0.27, math.pi / 2, math.pi * 1.5)
    line((-0.73, -0.36), (0.64, -0.36))
    arc(0.64, 0.0, 0.36, -math.pi / 2, math.pi / 2)
    line((0.64, 0.36), (-0.22, 0.36))
    P.append((-0.22, 0.36))
    # resample evenly
    L = [0.0]
    for i in range(1, len(P)):
        L.append(L[-1] + math.hypot(P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1]))
    tot = L[-1]
    out = []
    for k in range(n):
        d = tot * k / (n - 1)
        j = 0
        while j < len(L) - 2 and L[j + 1] < d:
            j += 1
        u = (d - L[j]) / max(1e-6, L[j + 1] - L[j])
        out.append((lerp(P[j][0], P[j + 1][0], u), lerp(P[j][1], P[j + 1][1], u)))
    return out


def sample_text_points(body, font, size, x, y, z, n, seed):
    ob = core.add_text(sc, body, font, size, PAL["bone"], (x, y, z),
                       align_x="LEFT", align_y="BOTTOM_BASELINE", name="sampler")
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    verts = [v.co.copy() for v in me.vertices]
    tris = []
    for p in me.polygons:
        vs = list(p.vertices)
        for i in range(1, len(vs) - 1):
            tris.append((vs[0], vs[i], vs[i + 1]))
    pts = []
    if tris:
        for k in range(n):
            idx = min(len(tris) - 1, int(hash01(seed, k, 1) * len(tris)))
            a, b, c = tris[idx]
            u = hash01(seed, k, 2)
            v = hash01(seed, k, 3)
            if u + v > 1.0:
                u, v = 1.0 - u, 1.0 - v
            p = verts[a] * (1.0 - u - v) + verts[b] * u + verts[c] * v
            pts.append((x + p.x, y + p.y, z))
    ev.to_mesh_clear()
    bpy.data.objects.remove(ob, do_unlink=True)
    return pts


def build_atoms(camC):
    l4 = data.line("atoms")
    ws = l4["words"]        # I / feel / my / atoms / rearranging
    row_y = 3.30
    size = 1.06
    words = []
    x = -8.45
    for i, w in enumerate(ws[:4]):
        ob = txt(w["w"].upper() if len(w["w"]) > 1 else "I", "archivo", size, D(0.30),
                 x, row_y, 1.0, name="l4_%d" % i)
        wd = core.measure(sc, ob.data.body, "archivo", size)
        words.append((w, ob, wd))
        x += wd + core.space_width(sc, "archivo", size) + 0.12
    core.sync_words(sc, [(w, ob) for w, ob, wd in words], sung=BONE, pre=0.30)
    for w, ob, wd in words:
        show(ob, 329, True)
    # rearranging, huge on its own line
    w_r = ws[4]
    sz_r = fit("REARRANGING", "archivo", 9.6)
    r_ob = txt("REARRANGING", "archivo", sz_r, D(0.30), -8.45, 1.10, 1.0, name="l4_r")
    show(r_ob, 329, True)
    core.color_at(r_ob, 1, D(0.30))
    core.color_at(r_ob, core.frame_of(sc, w_r["start"]) - 3, D(0.30))
    core.color_at(r_ob, core.frame_of(sc, w_r["start"]), SIG)
    core.set_interp(r_ob, "BEZIER", "color")

    # the lyric dims as its atoms leave, but stays fully readable
    for w, ob, wd in words:
        core.color_at(ob, core.frame_of(sc, w_r["start"]), tuple(ob.color)[:3])
        core.color_at(ob, core.frame_of(sc, w_r["start"]) + 20, D(0.52))
        core.set_interp(ob, "BEZIER", "color")

    # --- the paperclip, bottom right, drawn in 24 chunks
    S, ROT = 3.15, math.radians(-12)
    CX, CY = 3.9, -2.95
    raw = clip_outline(240)
    clip = []
    for q in raw:
        xx, yy = q[0] * S, q[1] * S
        clip.append((CX + xx * math.cos(ROT) - yy * math.sin(ROT),
                     CY + xx * math.sin(ROT) + yy * math.cos(ROT)))
    chunks = 24
    seg_objs = []
    f_draw0, f_draw1 = 380, 417
    for k in range(chunks):
        i0 = int(k * (len(clip) - 1) / chunks)
        i1 = int((k + 1) * (len(clip) - 1) / chunks) + 1
        pts3 = [(p[0], p[1], 1.4) for p in clip[i0:i1]]
        ob = multi_curve([pts3], 0.024, (1.0, 0.42, 0.16), "clipseg%d" % k, z=1.4)
        show(ob, 1, False)
        show(ob, int(f_draw0 + (f_draw1 - f_draw0) * (k + 1) / chunks), True)
        seg_objs.append(ob)
    # static ghost wire so the clip is legible before it is fully drawn
    ghost = multi_curve([[(p[0], p[1], 1.38) for p in clip]], 0.007, D(0.16), "clipghost", z=1.38)
    show(ghost, 340, True)

    # --- atoms: sample the row-1 glyphs, detach, spiral into the clip
    tot_w = sum(wd for w, ob, wd in words)
    pts = []
    for wi, (w, ob, wd) in enumerate(words):
        nw = max(10, int(round(108 * wd / tot_w)))
        pts += sample_text_points(ob.data.body, "archivo", size, ob.location.x, row_y, 1.0, nw, 77 + wi)
    dots = []
    t_atoms = core.frame_of(sc, ws[3]["start"])
    t_re = core.frame_of(sc, w_r["start"])
    for i, p0 in enumerate(pts):
        ob = core.add_uv_sphere(sc, p0, 0.034, D(0.85), hot=False, name="atom%d" % i)
        seg = clip[int((i + 0.5) / len(pts) * (len(clip) - 1))]
        dots.append((ob, p0, (seg[0], seg[1], 1.42), i))
        show(ob, 1, False)
    for ob, p0, p1, i in dots:
        td = t_atoms + 8 + 20 * hash01(5, i)          # detach during "atoms"
        ta = t_re + 6 + 26 * hash01(6, i)             # arrive during "rearranging"
        show(ob, int(td), True)
        core.color_at(ob, int(td), D(0.9))
        core.color_at(ob, int(td) + 3, (1.0, 0.55, 0.3))
        core.color_at(ob, int(ta) - 2, (1.0, 0.62, 0.36))
        core.color_at(ob, int(ta) + 4, D(0.85))
        core.set_interp(ob, "BEZIER", "color")
        for f in range(int(td), min(FEND, int(ta) + 24)):
            u = clamp((f - td) / max(1.0, ta - td))
            e = ease_in_out_cubic(u)
            ang = 0.9 * math.sin(math.pi * e)
            xx = lerp(p0[0], p1[0], e)
            yy = lerp(p0[1], p1[1], e)
            ca, sa = math.cos(ang), math.sin(ang)
            x2 = xx * ca - yy * sa
            y2 = xx * sa + yy * ca
            z2 = 1.0 - 1.35 * math.sin(math.pi * e) + 0.42 * e
            ob.location = (x2, y2, z2)
            ob.keyframe_insert("location", frame=f)
        core.set_interp(ob, "LINEAR", "location")

    # --- spark draws the clip
    spark = core.add_uv_sphere(sc, (0, 0, 1.6), 0.075, (1.0, 0.55, 0.28), hot=True, name="clipspark")
    show(spark, 1, False)
    for f in range(f_draw0 - 2, FEND + 1):
        u = clamp((f - f_draw0) / float(f_draw1 - f_draw0))
        idx = int(u * (len(clip) - 1))
        p = clip[idx]
        spark.location = (p[0], p[1], 1.62)
        spark.keyframe_insert("location", frame=f)
    core.set_interp(spark, "LINEAR", "location")
    show(spark, f_draw0 - 2, True)

    # annotations
    ann = [txt("ATOMIC ARRANGEMENT   1.0 × 10²³   ·   ΔS = +1.1 k_B", "mono_med", 0.125,
               D(0.34), -8.45, -4.55),
           txt("TRACE  IV   ·   REARRANGING", "mono_med", 0.125, D(0.34), 8.45, 4.55,
               align="RIGHT")]
    for ob in ann:
        show(ob, 334, True)
    return dict(words=words, r=r_ob, dots=dots, segs=seg_objs, spark=spark, ann=ann,
                clip=clip)


def animate_atoms(camC):
    for f in range(329, FEND + 1):
        u = (f - 329) / float(FEND - 329)
        camC.data.ortho_scale = 19.2 - 0.5 * u
        camC.data.keyframe_insert("ortho_scale", frame=f)
        camC.location = (0, 0, 30)
        camC.keyframe_insert("location", frame=f)
    core.set_interp(camC, "LINEAR", "ortho_scale")


def build(name):
    global sc
    sc = core.new_scene(name, samples=32, motion_blur=True)
    core.add_bg(sc, color=INK, gradient=True, size=90.0, z=-30.0)
    cam = core.add_camera_ortho(sc, 19.2)
    sc.frame_set(1)
    S = build_scope(cam)
    H = build_hole()
    animate_hole(H, S, cam)
    camB, VC = build_vortex_cam()
    V = build_vortex()
    TR = build_type_rig(camB)
    animate_vortex(V, VC, camB, TR)
    camC = core.add_camera_ortho(sc, 19.2)
    camC.location = (0, 0, 30)
    A = build_atoms(camC)
    animate_atoms(camC)
    for nm, fr, c in (("mA", 1, cam), ("mB", 194, camB), ("mC", 329, camC)):
        m = sc.timeline_markers.new(nm, frame=fr)
        m.camera = c
    sc.camera = cam
    apply_vis()
    sc.render.filepath = os.path.join(core.OUT, "frames", name, "####")
    os.makedirs(os.path.dirname(sc.render.filepath), exist_ok=True)
    print("SPACETIME_BUILT", sc.frame_end)
    return sc