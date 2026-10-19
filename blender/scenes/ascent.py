"""ascent — four quick movements (plate 9).

  A  "I hear the basilisk boom": an engraved serpent eye snaps open on "boom".
  B  "NVDA to the moon": a banknote — chart, guilloché moon, lettering — the spark as the price.
  C  "The Omega Point's coming soon": every line converges to one white-hot point.
  D  "One E thirty FLOPs a second": a 31-drum mechanical odometer rolling to 10^30.
"""
import bpy, bmesh, math, os, sys
from mathutils import Vector, Quaternion, Matrix
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pdoom import core, data, motifs
from pdoom.core import (PAL, clamp, lerp, smoothstep, ease_out_expo, ease_in_expo,
                        ease_in_out_cubic, ease_out_cubic, ease_out_back, hash01, sc_x)
from pdoom.core import _hex  # noqa

INK, BONE, SIG, EMB, GRAPH, ASH, BLOOD, ACID = (
    PAL["ink"], PAL["bone"], PAL["signal"], PAL["ember"], PAL["graphite"], PAL["ash"],
    PAL["blood"], PAL["acid"])
TAU = math.tau
SCN = "ascent"
T0 = data.SCENES[SCN]["start"]
FEND = data.SCENES[SCN]["frames"]
sc = None

INKD = lambda k: tuple(c * k for c in INK)
BONED = lambda k: core.sc_x(BONE, k)
D = lambda k: core.sc_x(BONE, k)
VIS = {}
VIS0 = {}


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
    cu.materials.append(mat or (core.mat_hot() if hot else core.mat_type()))
    ob = bpy.data.objects.new(name, cu)
    sc.collection.objects.link(ob)
    ob.color = (*color, 1.0)
    return ob


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


def fit(body, font, width):
    m = core.measure(sc, body, font, 1.0)
    return width / m if m > 0 else 1.0


def fade_col(ob, f0, f1, c0=None, c1=(0, 0, 0)):
    core.color_at(ob, max(1, f0), c0 if c0 is not None else tuple(ob.color)[:3])
    core.color_at(ob, max(1, f1), c1)
    core.set_interp(ob, "BEZIER", "color")


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


def shake_offsets(hits, amp, decay, seed, f):
    t = data.frame_to_time(SCN, f)
    dx = dy = 0.0
    for k, ht in enumerate(hits):
        if t >= ht:
            a = amp * math.exp(-(t - ht) * decay)
            dx += (hash01(seed, k, f) - 0.5) * 2 * a
            dy += (hash01(seed + 7, k, f * 3 + 1) - 0.5) * 2 * a
    return dx, dy


def dome_mesh(name, cx, cy, R, z0, sag, color, mat, segs=72, rings=10):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    vs = []
    centre = bm.verts.new((cx, cy, z0))
    for ri in range(1, rings + 1):
        rr = R * ri / rings
        for si in range(segs):
            a = si / segs * TAU
            vs.append(bm.verts.new((cx + rr * math.cos(a), cy + rr * math.sin(a),
                                    z0 - sag * (rr / R) ** 2)))
    for si in range(segs):
        bm.faces.new((centre, vs[si], vs[(si + 1) % segs]))
    for ri in range(rings - 1):
        for si in range(segs):
            a = ri * segs + si
            b = ri * segs + (si + 1) % segs
            c = (ri + 1) * segs + (si + 1) % segs
            d = (ri + 1) * segs + si
            bm.faces.new((vs[a], vs[b], vs[c], vs[d]))
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    sc.collection.objects.link(ob)
    me.materials.append(mat)
    ob.color = (*color, 1.0)
    return ob


def slit_mesh(name, cx, cy, w, h, z, color, mat, segs=28):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    left, right = [], []
    for i in range(segs):
        u = i / (segs - 1)
        y = lerp(-h, h, u)
        half = w * (1.0 - (y / h) ** 2) ** 0.55 + 0.004
        left.append(bm.verts.new((cx - half, cy + y, z)))
        right.append(bm.verts.new((cx + half, cy + y, z)))
    for i in range(segs - 1):
        bm.faces.new((left[i], right[i], right[i + 1], left[i + 1]))
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    sc.collection.objects.link(ob)
    me.materials.append(mat)
    ob.color = (*color, 1.0)
    return ob


def bez(p0, p1, p2, n):
    out = []
    for i in range(n):
        u = i / (n - 1.0)
        x = (1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * p1[0] + u * u * p2[0]
        y = (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * p1[1] + u * u * p2[1]
        out.append((x, y))
    return out


# ------------------------------------------------------------------ A: the basilisk eye
def build_eye():
    cx, cy = 0.30, 0.55
    lights = [core.add_light(sc, "AREA", (6.0, -6.0, 12.0), 420, BONE, size=8.0),
              core.add_light(sc, "AREA", (-7.0, 4.0, 7.0), 300, SIG, size=5.0),
              core.add_light(sc, "POINT", (0.3, 2.0, 8.0), 50, EMB, size=3.0)]
    # eyeball: engraved sphere
    eye = core.add_uv_sphere(sc, (cx, cy, 0.0), 4.35, INK, name="eyeball", segs=72, rings=44)
    eye.scale = (1.0, 0.96, 0.93)
    eye.data.materials[0] = core.mat_hatch_lit(INKD(0.6), (0.30, 0.285, 0.26), scale=17.0,
                                               angle=90, distortion=2.4, rough=0.55, rim=0.45,
                                               rim_color=EMB, line_emit=0.10)
    # iris: a shallow dome of dark glass with engraved fibres
    iris = dome_mesh("iris", cx, cy, 2.75, 3.90, 0.50, INK, core.mat_emit(INKD(1.15), 1.0),
                     segs=96, rings=12)
    rings = []
    for rr in (0.62, 1.15, 1.72, 2.22, 2.56, 2.70):
        rings.append(([(cx + rr * math.cos(i / 120 * TAU), cy + rr * math.sin(i / 120 * TAU),
                       3.915 - 0.50 * (rr / 2.75) ** 2) for i in range(120)], True))
    iris_rings = multi_curve(rings, 0.007, (0.30, 0.275, 0.24), "iris_rings", z=3.0)
    fib = []
    for k in range(84):
        a = k / 84.0 * TAU + 0.02 * math.sin(k * 7.3)
        r0, r1 = 0.62, 2.58 - 0.20 * hash01(3, k)
        fib.append(((cx + r0 * math.cos(a), cy + r0 * math.sin(a), 3.93 - 0.50 * (r0 / 2.75) ** 2),
                    (cx + r1 * math.cos(a), cy + r1 * math.sin(a), 3.93 - 0.50 * (r1 / 2.75) ** 2)))
    iris_fib = multi_curve(fib, 0.006, (0.34, 0.31, 0.27), "iris_fibres", z=3.0)
    hotf = []
    for k in range(6):
        a = 1.2 + k / 6.0 * 3.9
        hotf.append(((cx + 1.2 * math.cos(a), cy + 1.2 * math.sin(a), 3.96),
                     (cx + 2.45 * math.cos(a), cy + 2.45 * math.sin(a), 3.84)))
    iris_hot = multi_curve(hotf, 0.008, (1.0, 0.36, 0.12), "iris_hot", z=3.0, hot=True)
    # slit pupil
    pupil = slit_mesh("pupil", cx, cy, 0.30, 1.95, 4.02, (0, 0, 0),
                      core.mat_emit((0, 0, 0), 1.0), segs=44)
    pl = [(cx - 0.30 * (1 - (lerp(-1.95, 1.95, i / 43.0) / 1.95) ** 2) ** 0.55,
           cy + lerp(-1.95, 1.95, i / 43.0), 4.03) for i in range(44)]
    pr = [(cx + 0.30 * (1 - (lerp(-1.95, 1.95, i / 43.0) / 1.95) ** 2) ** 0.55,
           cy + lerp(-1.95, 1.95, i / 43.0), 4.03) for i in range(44)]
    pupil_rim = multi_curve([pl, pr], 0.014, (1.0, 0.40, 0.14), "pupil_rim", z=3.0, hot=True)
    # isis scales around the eye (on the eyeball, outside the iris)
    sc_rings = []
    for rr in (3.05, 3.45, 3.85, 4.2):
        sc_rings.append(([(cx + rr * math.cos(i / 90 * TAU), cy + rr * math.sin(i / 90 * TAU),
                           4.02 - 0.62 * (rr / 4.35) ** 2) for i in range(90)], True))
    scales = multi_curve(sc_rings, 0.006, (0.20, 0.19, 0.17), "sclera_rings", z=3.0)
    tick = []
    for k in range(48):
        a = k / 48.0 * TAU
        r0, r1 = 3.9, 4.25
        tick.append(((cx + r0 * math.cos(a), cy + r0 * math.sin(a), 4.02 - 0.62 * (r0 / 4.35) ** 2),
                     (cx + r1 * math.cos(a), cy + r1 * math.sin(a), 4.02 - 0.62 * (r1 / 4.35) ** 2)))
    sclera_ticks = multi_curve(tick, 0.005, (0.13, 0.125, 0.115), "sclera_ticks", z=3.0)
    # lids: two dark shutters with a bright seam
    lids = []
    for sgn in (1, -1):
        ccy = cy + sgn * 16.0
        lid = dome_mesh("lid%d" % sgn, cx, ccy, 16.0, 4.60, 0.9, INKD(1.02),
                        core.mat_hatch_lit(INKD(1.25), (0.06, 0.056, 0.052), scale=60.0,
                                           angle=90, distortion=1.0, rough=0.7, rim=0.35,
                                           rim_color=EMB, line_emit=0.0), segs=88, rings=6)
        rows = []
        for k in range(3):
            rr = 15.75 - 0.26 * k
            a0, a1 = (math.pi * 1.30, math.pi * 1.70) if sgn > 0 else (math.pi * 0.30, math.pi * 0.70)
            rows.append([(cx + rr * math.cos(lerp(a0, a1, i / 50.0)),
                          ccy + rr * math.sin(lerp(a0, a1, i / 50.0)), 4.61) for i in range(51)])
        lid_curves = multi_curve(rows, 0.007, (0.26, 0.24, 0.21), "lidrows%d" % sgn, z=3.0)
        # the seam highlight
        a0, a1 = (math.pi * 1.30, math.pi * 1.70) if sgn > 0 else (math.pi * 0.30, math.pi * 0.70)
        seam = multi_curve([[(cx + 15.99 * math.cos(lerp(a0, a1, i / 50.0)),
                              ccy + 15.99 * math.sin(lerp(a0, a1, i / 50.0)), 4.60)
                             for i in range(51)]], 0.012, (0.62, 0.56, 0.48),
                           "lidseam%d" % sgn, z=3.0)
        lids.append((sgn, lid, lid_curves, seam))
    # boom flash + shock rings (built around their own origin so scaling cannot drift them)
    glow = core.add_disc(sc, 0, 0, 0.32, (1.0, 0.55, 0.3), z=3.95, name="irisglow")
    glow.data.materials[0] = core.mat_hot()
    glow.location = (cx, cy, 0.0)
    show(glow, 1, False)
    shocks = []
    for k, rr in enumerate((2.2, 3.2)):
        ob = multi_curve([([(rr * math.cos(i / 90 * TAU), rr * math.sin(i / 90 * TAU))
                           for i in range(90)], True)], 0.012, (1.0, 0.55, 0.28),
                         "eyeshock%d" % k, z=4.3, hot=True)
        ob.location = (cx, cy, 0.0)
        show(ob, 1, False)
        shocks.append(ob)
    # ---- lyric, in front of everything
    l1 = data.line("basilisk")
    ws = l1["words"]
    hdr = txt("I HEAR THE", "mono_med", 0.32, D(0.42), -7.15, 4.40, 6.5, spacing=1.16)
    bsk = txt("BASILISK", "archivo", 1.32, D(0.28), -7.15, -2.95, 6.5)
    boom = txt("BOOM", "archivo", 2.55, D(0.25), 7.15, -4.65, 6.5, align="RIGHT")
    core.color_at(hdr, 1, D(0.30))
    core.color_at(hdr, core.frame_of(sc, ws[0]["start"]) - 3, D(0.30))
    core.color_at(hdr, core.frame_of(sc, ws[0]["start"]), BONE)
    core.set_interp(hdr, "BEZIER", "color")
    core.color_at(bsk, 1, D(0.30))
    core.color_at(bsk, core.frame_of(sc, ws[3]["start"]) - 3, D(0.30))
    core.color_at(bsk, core.frame_of(sc, ws[3]["start"]), BONE)
    core.set_interp(bsk, "BEZIER", "color")
    f_boom = core.frame_of(sc, ws[4]["start"])
    core.color_at(boom, 1, D(0.30))
    core.color_at(boom, f_boom - 3, D(0.30))
    core.color_at(boom, f_boom, SIG)
    core.set_interp(boom, "BEZIER", "color")
    return dict(eye=eye, iris=iris, rings=iris_rings, fib=iris_fib, hot=iris_hot,
                pupil=pupil, prim=pupil_rim, lids=lids, shocks=shocks, glow=glow,
                scales=scales, st= sclera_ticks, hdr=hdr, bsk=bsk, boom=boom, l1=l1,
                f_boom=f_boom, lights=lights, cx=cx, cy=cy)


def animate_eye(E, cam):
    ws = E["l1"]["words"]
    f_boom = E["f_boom"]
    f_open = core.frame_of(sc, ws[3]["start"])
    f_cut = 64
    for sgn, lid, cur, seam in E["lids"]:
        for f in range(1, f_cut + 1):
            base = 0.62 if sgn > 0 else 0.42
            if f >= f_boom:
                u = (f - f_boom) / 3.0
                target = (4.05 if sgn > 0 else -3.35)
                yv = lerp(base, target, ease_out_back(clamp(u), 1.3))
            elif f >= f_open - 2:
                u = clamp((f - (f_open - 2)) / 12.0)
                yv = base - sgn * 0.16 * ease_in_out_cubic(u)
            else:
                yv = base
            for ob in (lid, cur, seam):
                ob.location = (0, yv, 0.0)
                ob.keyframe_insert("location", frame=f)
            lid.keyframe_insert("location", frame=f)
        for ob in (lid, cur, seam):
            core.set_interp(ob, "LINEAR", "location")
    # pupil: dilates on boom then narrows to a hairline
    for f in range(1, f_cut + 1):
        if f < f_boom:
            sx, sy = 1.0, 1.0
        elif f < f_boom + 4:
            u = (f - f_boom) / 4.0
            sx = lerp(1.0, 2.3, math.sin(u * math.pi) * 0.6)
            sy = lerp(1.0, 0.72, math.sin(u * math.pi) * 0.5)
        else:
            u = clamp((f - (f_boom + 6)) / 12.0)
            sx = lerp(1.15, 0.06, ease_in_out_cubic(u))
            sy = lerp(1.0, 1.02, u)
        E["pupil"].scale = (sx, sy, 1)
        E["pupil"].keyframe_insert("scale", frame=f)
        E["prim"].scale = (sx, sy, 1)
        E["prim"].keyframe_insert("scale", frame=f)
    core.set_interp(E["pupil"], "BEZIER", "scale")
    core.set_interp(E["prim"], "BEZIER", "scale")
    # boom flash + shock
    show(E["glow"], f_boom, True)
    for f in range(f_boom, f_boom + 9):
        u = (f - f_boom) / 8.0
        s = 1.0 + 1.3 * ease_out_expo(u)
        E["glow"].scale = (s, s, 1)
        E["glow"].keyframe_insert("scale", frame=f)
        c = (1.0 - u) ** 2
        E["glow"].color = (c, c * 0.45, c * 0.2, 1)
        E["glow"].keyframe_insert("color", frame=f)
    show(E["glow"], f_boom + 9, False)
    for k, ob in enumerate(E["shocks"]):
        show(ob, f_boom, True)
        for f in range(f_boom, f_boom + 16):
            u = (f - f_boom) / 15.0
            s = 0.35 + 2.6 * ease_out_expo(u)
            ob.scale = (s, s, 1)
            ob.keyframe_insert("scale", frame=f)
            ob.data.bevel_depth = 0.006 / s
            ob.data.keyframe_insert("bevel_depth", frame=f)
            c = (1.0 - u) ** 2
            ob.color = (c, c * 0.5, c * 0.25, 1)
            ob.keyframe_insert("color", frame=f)
        show(ob, f_boom + 15, False)
    E["boom"].scale = (1.14, 1.14, 1)
    E["boom"].keyframe_insert("scale", frame=max(1, f_boom - 1))
    E["boom"].scale = (1, 1, 1)
    E["boom"].keyframe_insert("scale", frame=f_boom + 4)
    core.set_interp(E["boom"], "BEZIER", "scale")
    # camera: locked-off with a slow push; shake on boom
    for f in range(1, f_cut + 1):
        u = (f - 1) / float(f_cut - 1)
        d = lerp(35.8, 34.2, ease_in_out_cubic(u))
        dx, dy = shake_offsets([data.word("basilisk", 4)["start"]], 0.14, 12.0, 5, f)
        cam.location = (0.3 + dx, 0.55 + dy + 0.05 * u, d)
        cam.keyframe_insert("location", frame=f)
    core.set_interp(cam, "LINEAR", "location")
    for ob in [E["eye"], E["iris"], E["rings"], E["fib"], E["hot"], E["pupil"], E["prim"],
               E["scales"], E["st"]] + [l[1] for l in E["lids"]] + \
              [l[2] for l in E["lids"]] + [l[3] for l in E["lids"]]:
        initial(ob, False)
        show(ob, f_cut, False)
    for ob in (E["hdr"], E["bsk"], E["boom"]):
        initial(ob, False)
        show(ob, f_cut, False)


# ------------------------------------------------------------------ B: the banknote
def build_note(camP):
    paper = core.add_paper_bg(sc, z=-1.2, size=220.0)
    show(paper, 64, True)
    show(paper, 110, False)
    ink = (0.055, 0.052, 0.048)
    inkd = (0.10, 0.095, 0.088)
    els = []
    # border, double rule
    for inset, wd, col in ((0.0, 0.017, ink), (0.22, 0.008, inkd)):
        x0, x1 = -8.95 + inset, 8.95 - inset
        y0, y1 = -4.85 + inset, 4.85 - inset
        ob = multi_curve([[(x0, y0, 0.05), (x1, y0, 0.05), (x1, y1, 0.05), (x0, y1, 0.05)]],
                         wd, col, "noteborder", z=0.05, cyclic=True)
        show(ob, 64, True)
        show(ob, 110, False)
        els.append(ob)
    # corner denominations + header + serial
    heads = []
    for x, y, al in ((-8.55, 4.35, "LEFT"), (8.55, 4.35, "RIGHT"),
                     (-8.55, -4.55, "LEFT"), (8.55, -4.55, "RIGHT")):
        heads.append(txt("10³⁰", "mono_med", 0.30, ink, x, y, 0.06, align=al))
    heads.append(txt("LUNAR RESERVE NOTE", "mono_med", 0.17, ink, 0.0, 4.28, 0.06,
                     align="CENTER", spacing=1.5))
    heads.append(txt("NV 000 000 000 001", "mono_med", 0.115, inkd, -8.55, -4.05, 0.06))
    heads.append(txt("SERIES 10³⁰  ·  PAYABLE IN COMPUTE", "mono_med", 0.105, inkd,
                     -8.55, -4.28, 0.06))
    for ob in heads:
        core.color_at(ob, 1, ink)
        show(ob, 64, True)
        show(ob, 110, False)
    # NVDA lettering
    nv = txt("NVDA", "archivo", 3.55, ink, -8.25, 1.05, 0.07)
    show(nv, 64, True)
    show(nv, 110, False)
    core.color_at(nv, 1, INKD(0.55))
    core.color_at(nv, core.frame_of(sc, data.word("NVDA")["start"]) - 2, INKD(0.55))
    core.color_at(nv, core.frame_of(sc, data.word("NVDA")["start"]) + 2, INK)
    core.set_interp(nv, "BEZIER", "color")
    # the lyric rule under NVDA
    rule = multi_curve([[(x, 0.72, 0.07) for x in (-8.25, -8.25)]], 0.012, (1.0, 0.30, 0.08),
                       "nvarule", z=0.07, hot=True)
    show(rule, 64, True)
    show(rule, 110, False)
    f_nv = core.frame_of(sc, data.word("NVDA")["start"])
    for f, x in ((f_nv, -8.25), (f_nv + 8, 1.35)):
        rule.data.splines[0].points[1].co = (x, 0.72, 0.07, 1)
        rule.data.keyframe_insert('splines[0].points[1].co', frame=f)
    # TO THE MOON
    ws = data.line("to the moon")["words"][1:]
    tt = []
    x = -8.20
    size = 0.72
    for i, w in enumerate(ws):
        ob = txt(w["w"], "archivo700", size, inkd, x, -0.18, 0.07, spacing=1.12)
        wd = core.measure(sc, w["w"], "archivo700", size) * 1.12
        tt.append((w, ob))
        x += wd + 0.26
        core.color_at(ob, 1, INKD(0.55))
        core.color_at(ob, core.frame_of(sc, w["start"]) - 3, INKD(0.55))
        core.color_at(ob, core.frame_of(sc, w["start"]), SIG)
        core.set_interp(ob, "BEZIER", "color")
        show(ob, 64, True)
        show(ob, 110, False)
    # the moon medallion
    MX, MY, MR = 5.05, 1.55, 2.62
    moon_els = []
    g = []
    for gi in range(44):
        rr = 0.40 + (MR - 0.46) * (gi / 43.0) ** 1.02
        amp = 0.030
        n = 9
        ph = 0.55
        g.append(([(MX + (rr + amp * math.sin(n * i / 160 * TAU + ph)) * math.cos(i / 160 * TAU),
                    MY + (rr + amp * math.sin(n * i / 160 * TAU + ph)) * math.sin(i / 160 * TAU),
                    0.07) for i in range(160)], True))
    gu = multi_curve(g, 0.0060, (0.075, 0.070, 0.064), "guilloche", z=0.07)
    show(gu, 64, True)
    show(gu, 110, False)
    mdisc = core.add_disc(sc, MX, MY, MR * 0.94, (0.80, 0.785, 0.745), z=0.065, name="moondisc")
    mdisc.data.materials[0] = core.mat_emit((0.80, 0.785, 0.745), 1.0)
    show(mdisc, 64, True)
    show(mdisc, 110, False)
    # craters: hatched circles
    cr = []
    craters = [(-0.85, 0.62, 0.52), (0.55, -0.55, 0.72), (1.05, 0.85, 0.34),
               (-0.35, -1.05, 0.40), (-1.15, -0.25, 0.28), (0.10, 0.95, 0.20)]
    for (ax, ay, ar) in craters:
        cr.append(([(MX + ax + ar * math.cos(i / 48 * TAU), MY + ay + ar * math.sin(i / 48 * TAU),
                     0.075) for i in range(48)], True))
        for k in range(9):
            yy = -ar * 0.85 + 1.7 * ar * k / 8.0
            half = ar * math.sqrt(max(0.0, 1 - (yy / ar) ** 2)) * 0.85
            cr.append([(MX + ax - half, MY + ay + yy, 0.075), (MX + ax + half, MY + ay + yy, 0.075)])
        for k in range(5):
            a = k / 5.0 * TAU
            cr.append([(MX + ax + (ar * 0.25) * math.cos(a), MY + ay + (ar * 0.25) * math.sin(a), 0.075),
                       (MX + ax + (ar * 0.95) * math.cos(a), MY + ay + (ar * 0.95) * math.sin(a), 0.075)])
    crat = multi_curve(cr, 0.0055, (0.075, 0.070, 0.064), "craters", z=0.075)
    show(crat, 64, True)
    show(crat, 110, False)
    # radiating engraved rays from the medallion
    rays = []
    for k in range(48):
        a = k / 48.0 * TAU
        rr0 = MR + 0.08
        rr1 = MR + (0.35 if k % 4 else 0.62)
        rays.append([(MX + rr0 * math.cos(a), MY + rr0 * math.sin(a), 0.06),
                     (MX + rr1 * math.cos(a), MY + rr1 * math.sin(a), 0.06)])
    ry = multi_curve(rays, 0.005, inkd, "moonrays", z=0.06)
    show(ry, 64, True)
    show(ry, 110, False)
    # chart: log grid + hatched candles
    chart = []
    grid = []
    for i in range(7):
        y = -4.35 + i * 0.52
        grid.append([(-8.55, y, 0.04), (8.55, y, 0.04)])
    for i in range(13):
        x = -8.55 + i * 1.42
        grid.append([(x, -4.35, 0.04), (x, -1.25, 0.04)])
    gr = multi_curve(grid, 0.004, (0.16, 0.15, 0.14), "chartgrid", z=0.04)
    show(gr, 64, True)
    show(gr, 110, False)
    labels = []
    for i in range(7):
        y = -4.35 + i * 0.52
        labels.append(txt("%d" % i, "mono", 0.09, (0.35, 0.33, 0.3), -8.62, y + 0.02, 0.05,
                          align="RIGHT"))
    labels.append(txt("log₁₀ $", "mono", 0.09, (0.35, 0.33, 0.3), -8.62, -1.05, 0.05, align="RIGHT"))
    for ob in labels:
        show(ob, 64, True)
        show(ob, 110, False)
    # candles: deterministic hockey stick
    candles = []
    N = 34
    prev = 0.05
    for i in range(N):
        k = max(0.0, (i - 14) / (N - 15.0))
        level = 0.05 + 2.55 * k ** 2.2 + 0.10 * math.sin(i * 0.9) + 0.05 * hash01(9, i)
        o = prev
        c = level
        hi = max(o, c) + 0.05 + 0.04 * hash01(10, i)
        lo = min(o, c) - 0.05 - 0.04 * hash01(11, i)
        x = -8.30 + i * 0.485
        y0 = -4.30 + o * 1.15
        y1 = -4.30 + c * 1.15
        hy = -4.30 + hi * 1.15
        ly = -4.30 + lo * 1.15
        candles.append([(x, ly, 0.05), (x, hy, 0.05)])
        candles.append([(x - 0.095, y0, 0.05), (x - 0.095, y1, 0.05), (x + 0.095, y1, 0.05),
                        (x + 0.095, y0, 0.05), (x - 0.095, y0, 0.05)])
        prev = c
        # hatch lines inside the body
        steps = 4
        for hh in range(steps):
            yy = lerp(min(y0, y1), max(y0, y1), (hh + 0.5) / steps)
            if abs(y1 - y0) > 0.02:
                candles.append([(x - 0.07, yy, 0.051), (x + 0.07, yy - 0.03, 0.051)])
    cd = multi_curve(candles, 0.0065, (0.05, 0.047, 0.044), "candles", z=0.05)
    show(cd, 64, True)
    show(cd, 110, False)
    # price path + spark
    pts = []
    for i in range(N):
        k = max(0.0, (i - 14) / (N - 15.0))
        level = 0.05 + 2.55 * k ** 2.2 + 0.10 * math.sin(i * 0.9) + 0.05 * hash01(9, i)
        pts.append((-8.30 + i * 0.485, -4.30 + level * 1.15))
    path = multi_curve([[(p[0], p[1], 0.09) for p in pts]], 0.008, (0.05, 0.047, 0.044), "pricepath", z=0.09)
    show(path, 64, True)
    show(path, 110, False)
    spark = core.add_uv_sphere(sc, (0, 0, 0.12), 0.085, (1.0, 0.5, 0.2), hot=True, name="pricespark")
    show(spark, 64, True)
    show(spark, 110, False)
    f_moon = core.frame_of(sc, data.word("moon")["start"])
    f_nv = core.frame_of(sc, data.word("NVDA")["start"])
    for f in range(64, 111):
        u = clamp((f - f_nv) / float(max(1, f_moon + 6 - f_nv)))
        # follow the last candles, then fly up into the moon
        idx = u * (N - 1)
        i0 = int(idx)
        i1 = min(N - 1, i0 + 1)
        fr = idx - i0
        px = lerp(pts[i0][0], pts[i1][0], fr)
        py = lerp(pts[i0][1], pts[i1][1], fr)
        if u > 0.78:
            v = (u - 0.78) / 0.22
            px = lerp(px, MX + 0.2, ease_in_out_cubic(v))
            py = lerp(py, MY - 0.55, ease_in_out_cubic(v))
        spark.location = (px, py, 0.12)
        spark.keyframe_insert("location", frame=f)
    core.set_interp(spark, "LINEAR", "location")

    # camera: tilt up the note and push in
    for f in range(64, 111):
        u = (f - 64) / 46.0
        yy = lerp(-0.4, 0.55, ease_in_out_cubic(u))
        camP.location = (0.0, yy, lerp(32.0, 30.0, u))
        camP.keyframe_insert("location", frame=f)
        tgt = (0.0, lerp(0.1, 0.85, ease_in_out_cubic(u)), 0.0)
        d = Vector(tgt) - camP.location
        camP.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        camP.keyframe_insert("rotation_euler", frame=f)
    core.set_interp(camP, "LINEAR", "location")
    core.set_interp(camP, "LINEAR", "rotation_euler")
    return dict(spark=spark, els=els, nv=nv, tt=tt)


# ------------------------------------------------------------------ C: the Omega Point
def build_omega(camO):
    PX, PY = 2.55, 0.35
    lines = []
    for k in range(150):
        a = k / 150.0 * TAU + 0.7 * hash01(21, k)
        r0 = 13.0 + 8.0 * hash01(22, k)
        p0 = (PX + r0 * math.cos(a), PY + r0 * math.sin(a))
        mid = ((p0[0] + PX) * 0.5 - 1.6 * math.sin(a), (p0[1] + PY) * 0.5 + 1.6 * math.cos(a))
        lines.append(bez(p0, mid, (PX, PY), 26))
    field = multi_curve(lines, 0.0065, D(0.30), "omega_field", z=-0.5)
    field2 = multi_curve(lines, 0.026, D(0.05), "omega_glow", z=-0.55)
    # rings around the point
    rings = []
    for rr in (0.55, 0.95, 1.45, 2.1):
        rings.append(([(PX + rr * math.cos(i / 120 * TAU), PY + rr * math.sin(i / 120 * TAU), 0.0)
                       for i in range(120)], True))
    ring_ob = multi_curve(rings, 0.005, D(0.16), "omega_rings", z=0.0)
    hot = core.add_uv_sphere(sc, (PX, PY, 0.2), 0.075, (1.0, 0.62, 0.4), hot=True, name="omegapoint")
    hot.data.materials[0] = core.mat_hot()
    halo = core.add_disc(sc, 0, 0, 0.22, (0.9, 0.45, 0.25), z=0.1, name="omegahalo")
    halo.data.materials[0] = core.mat_hot()
    halo.location = (PX, PY, 0.0)
    show(halo, 1, False)
    # the converging field is parented to an empty at the point
    rig = bpy.data.objects.new("omega_rig", None)
    sc.collection.objects.link(rig)
    rig.location = (PX, PY, 0)
    for ob in (field, field2, ring_ob):
        ob.parent = rig
        ob.matrix_parent_inverse = Matrix.Identity(4)
        ob.location = (-PX, -PY, 0)
    # lyric in Cormorant italic
    l3 = data.line("Omega Point")
    ws = l3["words"]
    size = 1.62
    widths = [core.measure(sc, w["w"], "serif_italic", size) for w in ws]
    sw = core.space_width(sc, "serif_italic", size)
    total = sum(widths) + sw * (len(ws) - 1)
    kfit = min(1.0, 13.4 / total)
    size *= kfit
    widths = [w * kfit for w in widths]
    sw *= kfit
    x = -8.55
    lyric = []
    for i, w in enumerate(ws):
        ob = txt(w["w"], "serif_italic", size, D(0.26), x, 0.05, 0.2)
        lyric.append((w, ob))
        x += widths[i] + sw
    group = bpy.data.objects.new("lyric_rig", None)
    sc.collection.objects.link(group)
    for w, ob in lyric:
        ob.parent = group
        ob.matrix_parent_inverse = Matrix.Identity(4)
        ob.location = (ob.location.x + 8.55, ob.location.y - 0.05, ob.location.z)
    group.location = (-8.55, 0.05, 0.2)
    core.sync_words(sc, lyric, sung=BONE, pre=0.32)
    # caption
    cap = [txt("THE OMEGA POINT   ·   LIMIT", "mono_med", 0.13, D(0.4), -8.55, 4.3, 0.3),
           txt("t > ALL BOUNDS", "mono_med", 0.13, SIG, 8.55, 4.3, 0.3, align="RIGHT"),
           txt("ALL OPTIMISATION PATHS TERMINATE HERE", "mono_med", 0.11, D(0.3),
               -8.55, -4.6, 0.3)]
    return dict(field=field, field2=field2, rings=ring_ob, hot=hot, halo=halo, rig=rig,
                lyric=lyric, group=group, cap=cap, ws=ws, PX=PX, PY=PY)


def animate_omega(O, camO):
    f_cut = 174
    f_soon = core.frame_of(sc, O["ws"][4]["start"])
    # the field collapses into the point
    for f in range(110, 175):
        u = clamp((f - 110) / float(f_soon - 110))
        s = lerp(1.0, 0.16, ease_in_expo(u))
        O["rig"].scale = (s, s, s)
        O["rig"].keyframe_insert("scale", frame=f)
        O["rig"].rotation_euler = (0, 0, -0.35 * ease_in_out_cubic(u))
        O["rig"].keyframe_insert("rotation_euler", frame=f)
    core.set_interp(O["rig"], "BEZIER", "scale")
    for f in range(110, 175):
        u = clamp((f - f_soon) / 16.0)
        s = 1.0 + 1.1 * ease_out_expo(u)
        O["halo"].scale = (s, s, 1)
        O["halo"].keyframe_insert("scale", frame=f)
        c = 0.5 + 0.5 * min(1.0, u * 4)
        O["halo"].color = (c, c * 0.5, c * 0.26, 1)
        O["halo"].keyframe_insert("color", frame=f)
    show(O["halo"], f_soon - 2, True)
    # the point brightens as the field closes, then flares
    for f in range(110, 175):
        u = clamp((f - f_soon) / 10.0)
        s = 0.5 + 0.5 * clamp((f - 110) / float(f_soon - 110)) + 1.1 * ease_out_expo(u)
        O["hot"].scale = (s, s, s)
        O["hot"].keyframe_insert("scale", frame=f)
    # lyric: shrink into the point after "soon" is sung
    for f in range(110, 175):
        u = clamp((f - (f_soon + 4)) / 14.0)
        s = lerp(1.0, 0.16, ease_in_expo(u))
        O["group"].scale = (s, s, s)
        O["group"].keyframe_insert("scale", frame=f)
        tx = lerp(-8.55, O["PX"] - 0.55, ease_in_expo(u))
        ty = lerp(0.05, O["PY"] + 0.02, ease_in_expo(u))
        O["group"].location = (tx, ty, 0.2)
        O["group"].keyframe_insert("location", frame=f)
    core.set_interp(O["group"], "BEZIER", "scale")
    core.set_interp(O["group"], "LINEAR", "location")
    for ob in [O["field"], O["field2"], O["rings"], O["hot"]] + [o for w, o in O["lyric"]] + O["cap"]:
        show(ob, 110, True)
        show(ob, f_cut, False)
    show(O["halo"], f_cut, False)


# ------------------------------------------------------------------ D: the odometer
def build_odo(camD):
    N = 31
    digits = "1" + "0" * 30
    # Plex Mono's advance is 0.60 em; keep the digits from overlapping and fit 17.4 units
    size = 17.4 / (N * 0.60 + 9 * 0.34)
    adv = size * 0.60
    gap = size * 0.34
    x0 = -0.5 * (N * adv + 9 * gap) + adv * 0.5
    print("ODO", round(size, 3), round(adv, 3), round(gap, 3))
    objs = []
    x = x0
    grp = 0
    for i, ch in enumerate(digits):
        if i > 0 and i % 3 == 0:
            x += gap
        ob = txt(ch, "mono_bold", size, SIG if i == 0 else BONE, x, 0.0, 0.3,
                 align="CENTER", name="dgt%d" % i)
        # mechanical drop-in, staggered left to right
        f_in = 174 + int(i * 0.20)
        ob.location = (x, 0.16, 0.3)
        ob.keyframe_insert("location", frame=f_in)
        ob.location = (x, 0.0, 0.3)
        ob.keyframe_insert("location", frame=f_in + 5)
        core.set_interp(ob, "BEZIER", "location")
        show(ob, f_in, True)
        objs.append(ob)
        x += adv
    # group commas
    commas = []
    x = x0
    for i in range(N):
        if i > 0 and i % 3 == 0:
            xm = x - adv * 0.5 - gap * 0.5
            commas.append(txt(",", "mono_bold", size * 0.62, D(0.60), xm, -0.03, 0.3,
                              align="CENTER"))
            x += gap
        x += adv
    for gi, ob in enumerate(commas):
        show(ob, 174 + int((gi * 3 + 2) * 0.20) + 1, True)
    # labels
    heads = [txt("MECHANICAL REGISTER   ·   31 DRUMS", "mono_med", 0.125, D(0.40), -8.6, 4.35, 0.3),
             txt("P(doom) 0.42", "mono_med", 0.125, SIG, 8.6, 4.35, 0.3, align="RIGHT")]
    fl = txt("FLOP/s", "mono_bold", 1.15, BONE, -8.6, -2.05, 0.3)
    eq = txt("= 1 × 10³⁰", "mono_med", 0.56, SIG, -1.05, -2.05, 0.3)
    foot = [txt("dense-equivalent throughput · one second of one machine · ±1 order of magnitude",
                "mono_med", 0.115, D(0.38), -8.6, -4.55, 0.3),
            txt("NOT AUDITED", "mono_med", 0.115, D(0.38), 8.6, -4.55, 0.3, align="RIGHT")]
    # lyric
    l4 = data.line("flops")
    ws = l4["words"]
    lyr = []
    x = -8.6
    size_l = 0.66
    for i, w in enumerate(ws):
        body = w["w"].upper()
        ob = txt(body, "archivo700", size_l, D(0.30), x, 2.55, 0.3, spacing=1.06)
        wd = core.measure(sc, body, "archivo700", size_l) * 1.06
        lyr.append((w, ob))
        x += wd + 0.20
    core.sync_words(sc, lyr, sung=BONE, pre=0.3)
    # camera
    for f in range(174, FEND + 1):
        u = (f - 174) / float(FEND - 174)
        camD.location = (0.0, lerp(-1.5, -0.9, u), lerp(48.0, 46.6, ease_in_out_cubic(u)))
        dv = Vector((0.0, 0.0, 0.0)) - camD.location
        camD.rotation_euler = dv.to_track_quat("-Z", "Y").to_euler()
        camD.keyframe_insert("location", frame=f)
        camD.keyframe_insert("rotation_euler", frame=f)
    core.set_interp(camD, "LINEAR", "location")
    core.set_interp(camD, "LINEAR", "rotation_euler")
    for ob in objs + commas + heads + foot + [fl, eq] + [o for w, o in lyr]:
        if ob not in objs:
            show(ob, 174, True)
    return dict(objs=objs)


def build(name):
    global sc
    sc = core.new_scene(name, samples=32, motion_blur=True)
    core.add_bg(sc, color=INK, z=-40.0, size=120.0)
    camA = core.add_camera_persp(sc, (0.3, 1.0, 34), (0.3, 1.0, 0), lens=65)
    camB = core.add_camera_persp(sc, (0, 0, 32), (0, 0, 0), lens=55)
    camC = core.add_camera_ortho(sc, 19.2)
    camD = core.add_camera_persp(sc, (0, -1.0, 45), (0, 0, 0), lens=85)
    sc.camera = camA
    sc.frame_set(1)
    E = build_eye()
    animate_eye(E, camA)
    Nt = build_note(camB)
    O = build_omega(camC)
    animate_omega(O, camC)
    Od = build_odo(camD)
    for nm, fr, c in (("mA", 1, camA), ("mB", 64, camB), ("mC", 110, camC), ("mD", 174, camD)):
        m = sc.timeline_markers.new(nm, frame=fr)
        m.camera = c
    apply_vis()
    sc.render.filepath = os.path.join(core.OUT, "frames", name, "####")
    os.makedirs(os.path.dirname(sc.render.filepath), exist_ok=True)
    print("ASCENT_BUILT", sc.frame_end)
    return sc