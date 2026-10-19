"""OUTRO — detonation, the number upped past every bound, an equation that simplifies
to NaN, and a Regenerate button that rewinds the film into its first frame.

One perspective camera locked to a 19.2-unit-wide frame at z=0 (so all 2D layout is
the usual ortho layout), real 3D debris/shockwave, a real paper sheet, and a fast
procedural rewind montage. Deterministic; beats and times come from pdoom.data.
"""
import bpy, bmesh, math, os, sys
from mathutils import Matrix, Quaternion, Vector
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pdoom import core, data
from pdoom.core import (PAL, clamp, lerp, smoothstep, ease_out_expo, ease_in_out_cubic,
                        ease_out_cubic, ease_in_expo, hash01, prog, keys)

INK, BONE, SIG, EMB, GRAPH, ASH, BLOOD = (PAL["ink"], PAL["bone"], PAL["signal"], PAL["ember"],
                                          PAL["graphite"], PAL["ash"], PAL["blood"])
DIM = core.sc_x(BONE, 0.30)
FAINT = core.sc_x(BONE, 0.10)
CAMZ = 26.68          # 50 mm lens, 19.2 world units across at z = 0
START = data.SCENES["outro"]["start"]
END = data.SCENES["outro"]["end"]
BD = [b for b in data.BEATS if START - 0.02 <= b <= END + 0.01]


def TB(i):
    j = int(math.floor(i))
    fr = i - j
    if j + 1 < len(BD):
        return BD[j] + (BD[j + 1] - BD[j]) * fr
    if j < len(BD):
        return BD[j] + fr * data.BEAT_PERIOD
    return START + i * data.BEAT_PERIOD


def F(t):
    return core.frame_of(SC, t)


def txt(s, font, size, color, x, y, z=0.02, align="LEFT", name="t", spacing=1.0, rot=0.0):
    return core.add_text(SC, s, font, size, color, (x, y, z), align_x=align,
                         align_y="BOTTOM_BASELINE", name=name, spacing=spacing)


def show(ob, t, vis):
    core.show_at(ob, F(t), vis)


def col(ob, t, c):
    core.color_at(ob, max(1, F(t)), c)


def mesh_quad(w, h, color, name, material=None, loc=(0, 0, 0), z=0.0):
    me = bpy.data.meshes.new(name)
    me.from_pydata([(-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0)],
                   [], [(0, 1, 2, 3)])
    me.update()
    ob = bpy.data.objects.new(name, me)
    SC.collection.objects.link(ob)
    me.materials.append(material or core.mat_type())
    ob.color = (*color, 1)
    ob.location = loc
    return ob


def mesh_box(size, color, name, material, loc=(0, 0, 0), bevel=0.0):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= size[0]
        v.co.y *= size[1]
        v.co.z *= size[2]
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    SC.collection.objects.link(ob)
    me.materials.append(material)
    ob.color = (*color, 1)
    ob.location = loc
    if bevel:
        md = ob.modifiers.new("bev", "BEVEL")
        md.width = bevel
        md.segments = 1
    return ob


def ring_mesh(name, inner=0.97, outer=1.0, segs=96, color=None, mat=None):
    vs, fs = [], []
    for i in range(segs):
        a = i / segs * math.tau
        vs.append((math.cos(a) * inner, math.sin(a) * inner, 0))
    for i in range(segs):
        a = i / segs * math.tau
        vs.append((math.cos(a) * outer, math.sin(a) * outer, 0))
    for i in range(segs):
        j = (i + 1) % segs
        fs.append((i, j, segs + j, segs + i))
    me = bpy.data.meshes.new(name)
    me.from_pydata(vs, [], fs)
    me.update()
    ob = bpy.data.objects.new(name, me)
    SC.collection.objects.link(ob)
    me.materials.append(mat or core.mat_hot())
    ob.color = (*(color or SIG), 1)
    return ob


def poly3(points, width, color, name="p", z=0.0, hot=False, cyclic=False):
    return core.add_polyline(SC, [(p[0], p[1], p[2] if len(p) > 2 else z) for p in points],
                             width, color, name=name, hot=hot, cyclic=cyclic)


def lemniscate(cx, cy, A, n=200):
    pts = []
    for i in range(n + 1):
        u = i / n * math.tau
        d = 1 + math.sin(u) ** 2
        pts.append((cx + A * math.cos(u) / d, cy + A * math.sin(u) * math.cos(u) / d, 0))
    return pts


# ----------------------------------------------------------------------------- detonation
def build_detonation():
    f_over = F(TB(4))
    # flash card
    flash = mesh_quad(30, 17, core.sc_x(BONE, 2.0), "flash", core.mat_hot(), (0, 0, 5))
    show(flash, TB(0), True)
    col(flash, TB(0), core.sc_x(BONE, 2.0))
    col(flash, TB(0) + 0.11, (0, 0, 0))
    show(flash, TB(0) + 0.13, False)

    # hot core
    core.add_uv_sphere(SC, (0, 0, 0.4), 0.55, BONE, hot=True, name="core")
    core_obj = bpy.data.objects["core"]
    show(core_obj, TB(0), True)
    for f, s in [(1, 0.5), (4, 2.4), (12, 3.2), (26, 1.4), (f_over, 0.01)]:
        core_obj.scale = (s, s, s)
        core_obj.keyframe_insert("scale", frame=f)
    show(core_obj, f_over, False)

    # shockwave rings
    for k, (dz, col0, sc0) in enumerate([(0.0, SIG, 1.0), (-0.5, EMB, 1.15), (0.6, BONE, 0.85)]):
        r = ring_mesh(f"wave{k}", 0.982, 1.0, 120, color=col0)
        r.location = (0, 0, 0.1 + dz)
        show(r, TB(0), True)
        for f, s in [(1, 0.15), (6, 2.2), (16, 9.0), (30, 17.5)]:
            r.scale = (s * sc0, s * sc0, 1)
            r.keyframe_insert("scale", frame=f)
        col(r, TB(0), core.sc_x(col0, 1.0))
        col(r, TB(0) + 0.25, core.sc_x(col0, 0.8))
        col(r, TB(0) + 0.9, core.sc_x(col0, 0.0))
        show(r, TB(1), False)
    # rings on the next three beats
    for k in (1, 2, 3):
        r = ring_mesh(f"waveb{k}", 0.982, 1.0, 96, color=SIG)
        r.location = (0, 0, 0.2)
        show(r, TB(k), True)
        for f, s in [(F(TB(k)), 0.2), (F(TB(k)) + 4, 3.0), (F(TB(k)) + 18, 12.0)]:
            r.scale = (s, s, 1)
            r.keyframe_insert("scale", frame=f)
        col(r, TB(k), core.sc_x(SIG, 0.9))
        col(r, TB(k) + 0.5, core.sc_x(SIG, 0.0))
        show(r, TB(k + 1), False)

    # debris
    mats = [core.mat_lit(core.sc_x(ASH, 0.5), 0.4, 0.4),
            core.mat_emit(core.sc_x(BONE, 0.55), 1.0),
            core.mat_emit(core.sc_x(EMB, 0.95), 1.0)]
    for i in range(130):
        a = hash01(i, 1) * math.tau
        el = (hash01(i, 2) - 0.45) * 0.9
        sp = 6.0 + hash01(i, 3) ** 1.6 * 26.0
        dx = math.cos(a) * math.cos(el)
        dy = math.sin(a) * math.cos(el)
        dz = math.sin(el) * 0.5
        L = 0.10 + hash01(i, 4) * 0.36
        ob = mesh_box((0.012 + hash01(i, 5) * 0.03, L, 0.004), core.sc_x(BONE, 0.5),
                      f"deb{i}", mats[i % 3], (dx * 0.1, dy * 0.1, dz * 0.1))
        ob.rotation_euler = (hash01(i, 6) * math.tau, hash01(i, 7) * math.tau, hash01(i, 8) * math.tau)
        show(ob, TB(0), True)
        t0 = TB(0) + hash01(i, 9) * 0.04
        t_end = t0 + 1.25
        for j, (tt, dist) in enumerate([(t0, 0.0), (t0 + 0.22, sp * 0.22), (t_end, sp * 1.2)]):
            zz = dz * dist + 0.3 - 2.2 * (tt - t0) ** 2
            ob.location = (dx * dist, dy * dist, zz)
            ob.keyframe_insert("location", frame=F(tt))
        core.set_interp(ob, "LINEAR", "location")
        ob.rotation_euler = (ob.rotation_euler.x + 2.6, ob.rotation_euler.y + 3.4, ob.rotation_euler.z + 1.7)
        ob.keyframe_insert("rotation_euler", frame=F(t_end))
        core.set_interp(ob, "LINEAR", "rotation_euler")
        show(ob, TB(4), False)

    # blast light
    pl = core.add_light(SC, "POINT", (0, 0, 2.0), 0.0, core.sc_x(EMB, 1.0), size=2.0, name="blast")
    for f, e in [(1, 90000), (4, 30000), (12, 6000), (28, 600), (f_over, 0)]:
        pl.data.energy = e
        pl.data.keyframe_insert("energy", frame=f)
    core.set_interp(pl.data, "LINEAR", "energy")
    fa = core.add_light(SC, "AREA", (0, 3, 8), 9000, core.sc_x(BONE, 0.9), size=6, name="blastfill")
    core.look_at(fa, (0, 0, 0))
    show(fa, TB(4), False)

    # P(DOOM) 1.00 readout, staged left
    lab = txt("P(DOOM)", "mono_semi", 0.40, core.sc_x(SIG, 1.0), -8.55, 2.35, 0.2, name="dlab")
    num = txt("1.00", "mono_light", 3.0, core.sc_x(BONE, 1.0), -8.65, 0.75, 0.2, name="dnum")
    show(lab, TB(0) + 0.05, True)
    show(num, TB(0) + 0.05, True)
    num.scale = (1.12, 1.12, 1)
    num.keyframe_insert("scale", frame=F(TB(0) + 0.05))
    num.scale = (1, 1, 1)
    num.keyframe_insert("scale", frame=F(TB(0) + 0.3))
    core.set_interp(num, "BEZIER", "scale")
    # track under the number
    tr = core.add_rect(SC, -8.6, -0.25, 7.6, 0.02, core.sc_x(BONE, 0.18), z=0.2, name="dtrack")
    fill = core.add_rect(SC, -8.6, -0.27, 7.6, 0.05, SIG, z=0.21, name="dfill")
    show(tr, TB(0) + 0.08, True)
    show(fill, TB(0) + 0.08, True)
    show(lab, TB(4), False)
    show(num, TB(4), False)
    show(tr, TB(4), False)
    show(fill, TB(4), False)


# ----------------------------------------------------------------------------- overflow
def build_overflow():
    # ---------------- bar 0: the readout breaks its 1.0 cap
    fx = -8.5
    fy = 1.55
    lab = txt("P(DOOM)", "mono_semi", 0.24, core.sc_x(SIG, 1.0), fx, fy + 1.75, 0.2, name="olab", spacing=1.08)
    show(lab, TB(4), True)
    show(lab, TB(7.85), False)
    vals = ["1.01", "1.10", "1.50", "2.00"]
    nums = []
    for i, v in enumerate(vals):
        ob = txt(v, "mono_light", 2.6, core.sc_x(BONE, 1.0), fx, fy, 0.2, name=f"onum{i}")
        nums.append(ob)
        show(ob, TB(4 + i), i == 0)
        if i > 0:
            show(ob, TB(4 + i) + 0.02, True)
            ob.scale = (1.08, 1.08, 1)
            ob.keyframe_insert("scale", frame=F(TB(4 + i)))
            ob.scale = (1, 1, 1)
            ob.keyframe_insert("scale", frame=F(TB(4 + i) + 0.22))
            core.set_interp(ob, "BEZIER", "scale")
        if i < 3:
            show(ob, TB(5 + i), False)
        else:
            show(ob, TB(7.85), False)
    # track 0..2, cap at 1.0, ticks
    x0, x1 = -8.5, 5.2
    yy = -0.75
    trk = core.add_rect(SC, x0, yy, x1 - x0, 0.024, core.sc_x(BONE, 0.16), z=0.2, name="otrack")
    show(trk, TB(4), True)
    show(trk, TB(7.85), False)
    ticks = []
    for i in range(9):
        xx = x0 + (x1 - x0) * i / 8.0
        major = i % 4 == 0
        ticks.append(((xx, yy - (0.24 if major else 0.12)), (xx, yy)))
    core.add_segments(SC, ticks, 0.012, core.sc_x(BONE, 0.50), name="oticks", z=0.2)
    ticks_ob = bpy.data.objects["oticks"]
    show(ticks_ob, TB(4), True)
    show(ticks_ob, TB(7.85), False)
    cap_x = x0 + (x1 - x0) * 0.5
    for sgn in (-1, 1):
        cap = core.add_rect(SC, cap_x - 0.03, yy - 0.3, 0.06, 0.6, core.sc_x(BONE, 0.9), z=0.2, name=f"cap{sgn}")
        cap.location.x = cap_x
        show(cap, TB(4), True)
        show(cap, TB(7.85), False)
        cap.rotation_euler = (0, 0, 0)
        cap.keyframe_insert("rotation_euler", frame=F(TB(4) + 0.1))
        cap.rotation_euler = (0, 0, math.radians(12 * sgn))
        cap.location.y = yy - 0.3 + sgn * 0.25
        cap.keyframe_insert("rotation_euler", frame=F(TB(5)))
        cap.keyframe_insert("location", frame=F(TB(5)))
    core.set_interp(bpy.data.objects["cap-1"], "BEZIER", "rotation_euler")
    core.set_interp(bpy.data.objects["cap1"], "BEZIER", "rotation_euler")
    maxl = txt("max", "mono", 0.14, core.sc_x(ASH, 0.9), cap_x - 0.25, yy + 0.42, 0.2, name="maxlab")
    show(maxl, TB(4), True)
    show(maxl, TB(7.85), False)
    endticks = txt("2.00", "mono", 0.14, core.sc_x(ASH, 0.9), x1 - 0.3, yy + 0.42, 0.2, name="endlab")
    show(endticks, TB(4), True)
    show(endticks, TB(7.85), False)
    fill = core.add_rect(SC, x0, yy - 0.016, 1.0, 0.055, SIG, z=0.21, name="ofill")
    show(fill, TB(4), True)
    show(fill, TB(7.85), False)
    for f in range(F(TB(4)), F(TB(7.85)) + 1):
        t = data.frame_to_time(SC.name, f)
        rb = (t - START) / data.BEAT_PERIOD
        i = int(clamp(math.floor(rb - 4), 0, 3))
        prev = 1.0 if i == 0 else float(vals[i - 1])
        cur = float(vals[i])
        local = clamp((rb - 4) - i)
        v = lerp(prev, cur, ease_out_expo(clamp(local / 0.30)))
        fill.scale = ((x1 - x0) * v / 2.0, 1, 1)
        fill.keyframe_insert("scale", frame=f)
    core.set_interp(fill, "LINEAR", "scale")
    foot = txt("¹ Kolmogorov (1933): P(doom) = 1. Deprecated.", "mono", 0.15,
               core.sc_x(ASH, 0.95), -8.5, -4.55, 0.2, name="foot")
    show(foot, TB(5), True)
    show(foot, TB(7.85), False)

    # ---------------- bar 1: log ruler flies past
    rx, ry = 4.0, -2.0
    ruler = bpy.data.objects.new("ruler", None)
    SC.collection.objects.link(ruler)
    tick_segs = []
    labels = []
    PPD = 5.8
    for d in range(-1, 6):
        for n in range(1, 10):
            xx = (d + math.log10(n)) * PPD
            major = n == 1
            tick_segs.append(((xx, 0), (xx, 0.55 if major else 0.26)))
            if major:
                lab = txt(str(10 ** d if d < 3 else f"{10**(d-3)}k"), "mono", 0.24,
                          core.sc_x(ASH, 0.95), xx - 0.12, -0.55, 0.2, name=f"rlab{d}")
                lab.parent = ruler
                labels.append(lab)
    cu = bpy.data.curves.new("rticks", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.008
    for a, b in tick_segs:
        sp = cu.splines.new("POLY")
        sp.points.add(1)
        sp.points[0].co = (a[0], a[1], 0.2, 1)
        sp.points[1].co = (b[0], b[1], 0.2, 1)
    cu.materials.append(core.mat_type())
    to = bpy.data.objects.new("rticks", cu)
    SC.collection.objects.link(to)
    to.color = (*core.sc_x(BONE, 0.55), 1)
    to.parent = ruler
    labels_vis = [to] + labels
    core.add_polyline(SC, [(-9.6, ry, 0.2), (9.6, ry, 0.2)], 0.012, core.sc_x(BONE, 0.25), name="rbase")
    base = bpy.data.objects["rbase"]
    mark = core.add_polyline(SC, [(rx, ry - 0.65, 0.25), (rx, ry + 0.7, 0.25)], 0.03, SIG, name="rmark", hot=True)
    spark = core.add_uv_sphere(SC, (rx, ry, 0.3), 0.11, EMB, hot=True, name="rspark")
    fillr = core.add_rect(SC, -9.6, ry - 0.02, 1.0, 0.04, SIG, z=0.23, name="rfill")
    fillr.scale = (13.6, 1, 1)
    for ob in (base, mark, spark, fillr):
        show(ob, TB(8), True)
        show(ob, TB(11.85), False)
    for lab in labels:
        show(lab, TB(8), True)
        show(lab, TB(11.85), False)
    show(to, TB(8), True)
    show(to, TB(11.85), False)

    lr = ["3.14", "10.00", "42.00", "1,000.00"]
    notes = ["≈ π (irrational)", "an order of magnitude", "the answer (question pending)", "units: dooms"]
    big = []
    for i in range(4):
        ob = txt(lr[i], "mono_light", 2.25, core.sc_x(BONE, 1.0), -8.7, 2.5, 0.25, name=f"lr{i}")
        nb = txt(notes[i], "mono", 0.18, core.sc_x(SIG, 0.95), -8.7, 1.75, 0.25, name=f"ln{i}")
        big.append((ob, nb))
        show(ob, TB(8 + i), i == 0)
        show(nb, TB(8 + i), i == 0)
        show(ob, TB(9 + i), False)
        show(nb, TB(9 + i), False)
    plab = txt("P(DOOM)", "mono_semi", 0.22, core.sc_x(SIG, 1.0), -8.7, 4.2, 0.25, name="plab2")
    show(plab, TB(8), True)
    show(plab, TB(11.85), False)
    # animate the ruler + digits
    lv = [math.log10(3.14), 1.0, math.log10(42), 3.0]
    for f in range(F(TB(8)), F(TB(11.85)) + 1):
        t = data.frame_to_time(SC.name, f)
        rb = (t - START) / data.BEAT_PERIOD
        i = int(clamp(math.floor(rb - 8), 0, 3))
        prev = math.log10(2.0) if i == 0 else lv[i - 1]
        cur = lv[i]
        local = clamp((rb - 8) - i)
        l = lerp(prev, cur, ease_out_expo(clamp(local / 0.42)))
        ruler.location = (rx - l * PPD, ry, 0)
        ruler.keyframe_insert("location", frame=f)
    core.set_interp(ruler, "LINEAR", "location")
    for i in range(4):
        if i > 0:
            show(big[i][0], TB(8 + i) + 0.01, True)
            show(big[i][1], TB(8 + i) + 0.01, True)
        show(big[i][0], TB(9 + i), False)
        show(big[i][1], TB(9 + i), False)

    # ---------------- bar 2: walls of typed zeros
    body = "\n".join(["0" * 70 for _ in range(3)])
    for k, (xx0, yy0) in enumerate([(-9.4, 4.35), (-9.4, 3.55), (-9.4, 2.75), (-9.4, 1.95),
                                   (-9.4, -1.95), (-9.4, -2.75), (-9.4, -3.55), (-9.4, -4.35),
                                   (0.8, 4.35), (0.8, -4.35)]):
        ob = txt(body, "mono", 0.15, core.sc_x(GRAPH, 0.7), xx0, yy0, 0.15, name=f"zw{k}")
        show(ob, TB(12), True)
        show(ob, TB(15.85), False)
    zlab = txt("P(DOOM) =", "mono_semi", 0.22, core.sc_x(SIG, 1.0), -9.4, 4.95, 0.2, name="zlab")
    show(zlab, TB(12), True)
    show(zlab, TB(15.85), False)
    zs = ["1e9", "1e30", "1e100", "1e1000"]
    zn = ["(a billion)", "(one E thirty — see above)", "(a googol)", "(does not fit)"]
    for i in range(4):
        ob = txt(zs[i], "mono_light", 2.0, core.sc_x(BONE, 1.0), 7.8, -0.6, 0.25,
                 align="RIGHT", name=f"z{i}")
        nb = txt(zn[i], "mono", 0.18, core.sc_x(ASH, 0.95), 7.8, -1.3, 0.25,
                 align="RIGHT", name=f"zn{i}")
        show(ob, TB(12 + i), i == 0)
        show(nb, TB(12 + i), i == 0)
        if i > 0:
            show(ob, TB(12 + i) + 0.01, True)
            show(nb, TB(12 + i) + 0.01, True)
        show(ob, TB(13 + i), False)
        show(nb, TB(13 + i), False)
    # a signal edge on the first beat
    edge = core.add_rect(SC, -9.6, 3.1, 0.03, 5.0, SIG, z=0.2, name="zedge")
    show(edge, TB(12), True)
    show(edge, TB(13), False)

    # ---------------- bar 3: the spark traces infinity, 16th recap
    cx, cy, A = 0.0, 0.5, 3.1
    inf = poly3(lemniscate(cx, cy, A), 0.045, SIG, name="infcurve", z=0.25, hot=True)
    show(inf, TB(16), True)
    data_curve = inf.data
    data_curve.bevel_factor_mapping_end = "SPLINE"
    data_curve.bevel_factor_end = 0.0
    data_curve.keyframe_insert("bevel_factor_end", frame=F(TB(16)))
    data_curve.bevel_factor_end = 1.0
    data_curve.keyframe_insert("bevel_factor_end", frame=F(TB(17.5)))
    core.set_interp(inf.data, "BEZIER", "bevel_factor_end")
    head = core.add_uv_sphere(SC, (cx + A, cy, 0.5), 0.13, EMB, hot=True, name="inhead")
    show(head, TB(16), True)
    for f in range(F(TB(16)), F(TB(17.5)) + 1):
        t = data.frame_to_time(SC.name, f)
        pr = clamp((t - TB(16)) / (TB(17.5) - TB(16)))
        u = pr * math.tau
        d = 1 + math.sin(u) ** 2
        head.location = (cx + A * math.cos(u) / d, cy + A * math.sin(u) * math.cos(u) / d, 0.5)
        head.keyframe_insert("location", frame=f)
    core.set_interp(head, "LINEAR", "location")
    show(head, TB(17.55), False)
    pl3 = txt("P(DOOM) =", "mono_semi", 0.26, core.sc_x(SIG, 1.0), cx - A - 0.2, cy + 2.6, 0.2, name="pl3")
    show(pl3, TB(16), True)
    show(pl3, TB(18), False)
    foot3 = txt("¹ upper bound removed", "mono", 0.16, core.sc_x(ASH, 0.95), cx - A - 0.2, cy - 3.0, 0.2, name="foot3")
    show(foot3, TB(16.5), True)
    show(foot3, TB(18), False)
    seq = ["1.00", "1.50", "3.14", "42.00", "1,000", "1e30", "1e100", "∞"]
    for i, s in enumerate(seq):
        t0 = TB(18) + i * 0.25
        sz = 4.6 if s == "∞" else 2.4 + hash01(i, 5) * 1.5
        ob = txt(s, "mono_light", sz, core.sc_x(SIG if i % 2 else BONE, 1.0),
                 cx + (hash01(i, 2) - 0.5) * 2.6, 3.35 + (hash01(i, 3) - 0.5) * 0.7, 0.3,
                 align="CENTER", name=f"seq{i}")
        show(ob, t0, True)
        if i < len(seq) - 1:
            show(ob, t0 + 0.25, False)
        else:
            show(ob, TB(20), False)
    show(inf, TB(20), False)


# ----------------------------------------------------------------------------- end card
def build_card():
    card = bpy.data.objects.new("card", None)
    SC.collection.objects.link(card)
    card.location = (0, 0, 0.55)
    # sheet + backing
    paper = mesh_box((17.4, 9.7, 0.06), core.sc_x(BONE, 0.8), "paper", core.mat_paper(), (0, 0, -0.06))
    paper.parent = card
    # opaque dark table in front of every earlier phase; only the sheet is on top
    cardback = mesh_quad(30, 17, INK, "cardback", core.mat_emit(INK, 1.0), (0, 0, -0.15))
    cardback.parent = card
    show(cardback, 1, False)
    show(cardback, TB(20), True)
    backing = mesh_quad(26, 15, INK, "backing", core.mat_emit(INK, 1.0), (0, 0, -0.6))
    backing.parent = card
    # a soft light to give the sheet a shadow
    sl = core.add_light(SC, "AREA", (1.5, 3.0, 9.0), 200.0, core.sc_x(BONE, 0.9), size=8.0, name="paperlight")
    core.look_at(sl, (0, 0, 0))
    sl.parent = card
    show(sl, 1, False)
    show(sl, TB(20), True)
    # title
    xs = -7.2
    title_words = ["I’m", "upping", "my"]
    tw = [core.measure(SC, w, "archivo700", 0.95) for w in title_words]
    xx = xs
    for i, w in enumerate(title_words):
        ob = txt(w, "archivo700", 0.95, core.sc_x(INK, 1.0), xx, 3.35, 0.03, name=f"title{i}")
        ob.parent = card
        show(ob, TB(20 + i), True)
        ob.scale = (1.0, 0.02, 1)
        ob.keyframe_insert("scale", frame=F(TB(20 + i)))
        ob.scale = (1.0, 1.0, 1)
        ob.keyframe_insert("scale", frame=F(TB(20 + i) + 0.28))
        core.set_interp(ob, "BEZIER", "scale")
        xx += tw[i] + 0.30
    # equation: P(doom) = value (1)
    p = txt("P", "serif_italic600", 1.65, core.sc_x(INK, 1.0), -7.2, 0.15, 0.03, name="eqP")
    p.parent = card
    xd = -7.2 + core.measure(SC, "P", "serif_italic600", 1.65) + 0.06
    doom = txt("(doom)", "serif600", 1.65, core.sc_x(INK, 1.0), xd, 0.15, 0.03, name="eqdoom")
    doom.parent = card
    xe = xd + core.measure(SC, "(doom)", "serif600", 1.65) + 0.55
    eq = txt("=", "serif600", 1.65, core.sc_x(INK, 1.0), xe, 0.15, 0.03, name="eqeq")
    eq.parent = card
    vx = xe + core.measure(SC, "=", "serif600", 1.65) + 0.55
    inf_t = txt("∞", "serif600", 1.75, core.sc_x(SIG, 1.0), vx, 0.15, 0.035, name="eqinf")
    inf_t.parent = card
    eight = txt("8", "serif600", 1.75, core.sc_x(INK, 1.0), vx + 0.15, 0.15, 0.04, name="eq8")
    eight.parent = card
    num1 = txt("(1)", "mono", 0.34, core.sc_x(ASH, 1.0), 6.35, 0.75, 0.03, align="RIGHT", name="eqnum")
    num1.parent = card
    # hidden until their beats
    for ob, t in [(p, TB(22.9)), (doom, TB(22.9)), (eq, TB(23.8)), (inf_t, TB(25.05)), (eight, TB(99))]:
        show(ob, 1, False)
        show(ob, t, True)
    # trace under P(doom)
    tr_pts = [(-7.5, -0.25), (-6.8, -0.35), (-5.5, -0.30), (-4.0, -0.34), (-2.4, -0.28), (-1.5, -0.2)]
    tr = poly3(tr_pts, 0.035, SIG, name="eqtrace", z=0.05, hot=True)
    tr.parent = card
    show(tr, TB(22.7), True)
    tr.data.bevel_factor_mapping_end = "SPLINE"
    tr.data.bevel_factor_end = 0.0
    tr.data.keyframe_insert("bevel_factor_end", frame=F(TB(22.7)))
    tr.data.bevel_factor_end = 1.0
    tr.data.keyframe_insert("bevel_factor_end", frame=F(TB(23.5)))
    core.set_interp(tr.data, "BEZIER", "bevel_factor_end")
    show(tr, TB(23.7), False)
    # infinity trace
    il = poly3(lemniscate(vx + 0.9, 0.86, 0.95, 160), 0.03, SIG, name="inftrace", z=0.06, hot=True)
    il.parent = card
    show(il, TB(24.15), True)
    il.data.bevel_factor_mapping_end = "SPLINE"
    il.data.bevel_factor_end = 0.0
    il.data.keyframe_insert("bevel_factor_end", frame=F(TB(24.15)))
    il.data.bevel_factor_end = 1.0
    il.data.keyframe_insert("bevel_factor_end", frame=F(TB(25.15)))
    core.set_interp(il.data, "BEZIER", "bevel_factor_end")
    show(il, TB(25.12), False)
    # infinity -> 8 (echo rotations)
    for j in range(2):
        ec = txt("∞", "serif600", 1.75, core.sc_x(SIG, 0.5 - 0.15 * j), vx, 0.15, 0.032, name=f"echo{j}")
        ec.parent = card
        show(ec, TB(26) - 0.04 * (j + 1), True)
        ec.rotation_euler = (0, 0, 0)
        ec.keyframe_insert("rotation_euler", frame=F(TB(26) - 0.04 * (j + 1)))
        ec.rotation_euler = (0, 0, math.radians(90))
        ec.keyframe_insert("rotation_euler", frame=F(TB(26.3) - 0.04 * j))
        show(ec, TB(26.34), False)
    inf_t.rotation_euler = (0, 0, 0)
    inf_t.keyframe_insert("rotation_euler", frame=F(TB(26)))
    inf_t.rotation_euler = (0, 0, math.radians(90))
    inf_t.keyframe_insert("rotation_euler", frame=F(TB(26.3)))
    core.set_interp(inf_t, "BEZIER", "rotation_euler")
    show(inf_t, TB(26.32), False)
    show(eight, TB(26.3), True)
    eight.scale = (0.7, 0.7, 1)
    eight.keyframe_insert("scale", frame=F(TB(26.3)))
    eight.scale = (1, 1, 1)
    eight.keyframe_insert("scale", frame=F(TB(26.5)))
    core.set_interp(eight, "BEZIER", "scale")
    show(eight, TB(27.0), False)
    # fraction 0/0
    frac = bpy.data.objects.new("frac", None)
    SC.collection.objects.link(frac)
    frac.parent = card
    z0 = txt("0", "serif600", 1.10, core.sc_x(INK, 1.0), vx + 0.8, 0.95, 0.035, align="CENTER", name="frac0a")
    z0.parent = frac
    z1 = txt("0", "serif600", 1.10, core.sc_x(INK, 1.0), vx + 0.8, 0.0, 0.035, align="CENTER", name="frac0b")
    z1.parent = frac
    bar = core.add_rect(SC, vx + 0.05, 0.90, 1.55, 0.04, core.sc_x(INK, 1.0), z=0.04, name="fracbar")
    bar.location.y = 0.90
    bar.parent = frac
    for ob, t in [(z0, TB(26.95)), (z1, TB(26.95)), (bar, TB(26.95))]:
        show(ob, 1, False)
        show(ob, t, True)
    bar.scale = (0.0, 1, 1)
    bar.keyframe_insert("scale", frame=F(TB(26.95)))
    bar.scale = (1.0, 1, 1)
    bar.keyframe_insert("scale", frame=F(TB(27.35)))
    core.set_interp(bar, "BEZIER", "scale")
    # taffy strands (brief)
    for sgn in (-1, 1):
        pts = [(vx + 0.8 + sgn * 0.18, 0.75), (vx + 0.8 + sgn * 0.30, 0.92), (vx + 0.8 + sgn * 0.18, 1.08)]
        ta = poly3(pts, 0.035, core.sc_x(INK, 0.9), name=f"taffy{sgn}", z=0.045)
        ta.parent = frac
        show(ta, TB(26.95), True)
        show(ta, TB(27.15), False)
    # tremble + collapse
    for f in range(F(TB(27.35)), F(TB(28.06)) + 1):
        t = data.frame_to_time(SC.name, f)
        pr = prog(t, TB(27.5), TB(28.05)) ** 2
        frac.location = (0.035 * pr * math.sin(t * 97.0), 0.025 * pr * math.cos(t * 83.0), 0)
        frac.keyframe_insert("location", frame=f)
    core.set_interp(frac, "LINEAR", "location")
    # NaN inflates from the bar
    nan = txt("NaN", "serif600", 1.55, core.sc_x(INK, 1.0), vx + 0.95, 0.12, 0.045, align="CENTER", name="nan")
    nan.parent = card
    show(nan, 1, False)
    show(nan, TB(28.04), True)
    nan.scale = (0.55, 0.03, 1)
    nan.keyframe_insert("scale", frame=F(TB(28.04)))
    nan.scale = (1.0, 1.0, 1)
    nan.keyframe_insert("scale", frame=F(TB(28.35)))
    core.set_interp(nan, "BEZIER", "scale")
    sup = txt("¹", "mono", 0.36, core.sc_x(INK, 0.8), vx + 2.75, 1.0, 0.045, name="nansup")
    sup.parent = card
    show(sup, 1, False)
    show(sup, TB(28.35), True)
    for ob in (z0, z1, bar):
        show(ob, TB(28.05), False)
    # flat shockwave at the collapse
    sw = ring_mesh("flatwave", 0.97, 1.0, 96, color=SIG)
    sw.parent = card
    sw.location = (vx + 0.9, 0.55, 0.05)
    show(sw, TB(28.04), True)
    for f, sxv, syv in [(F(TB(28.04)), 0.2, 0.025), (F(TB(28.4)), 3.4, 0.20)]:
        sw.scale = (sxv, syv, 1)
        sw.keyframe_insert("scale", frame=f)
    col(sw, TB(28.04), core.sc_x(SIG, 1.0))
    col(sw, TB(28.4), (0, 0, 0))
    show(sw, TB(28.45), False)
    # footnote
    fn = txt("¹ estimate no longer defined", "mono", 0.21, core.sc_x(ASH, 0.95), -7.2, -3.9, 0.03, name="cardfoot")
    fn.parent = card
    show(fn, 1, False)
    show(fn, TB(28.45), True)
    show(num1, TB(24.5), True)
    for f, scv in [(F(TB(20)), 0.985), (F(TB(29.4)), 1.025), (F(TB(30)), 1.025), (F(TB(30.42)), 0.001)]:
        sv = 0.001 if scv < 0.01 else scv * 0.78
        card.scale = (sv, sv, sv)
        card.keyframe_insert("scale", frame=f)
    core.set_interp(card, "BEZIER", "scale")
    show(paper, TB(20), True)
    show(backing, TB(20), True)
    return card


# ----------------------------------------------------------------------------- tail
def build_tail():
    # the frame / crop marks
    cm = bpy.data.objects.new("cropmarks", None)
    SC.collection.objects.link(cm)
    for (sx, sy) in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
        x, y = sx * 8.9, sy * 4.6
        pts = [(x + sx * 0.25, y), (x, y), (x, y + sy * 0.25)]
        ob = poly3(pts, 0.016, core.sc_x(BONE, 0.42), name="crop", z=0.9)
        ob.parent = cm
        show(ob, TB(30.6), True)
        show(ob, TB(33.1), False)
        show(ob, TB(34.3), True)
    # spark + button
    sp = core.add_uv_sphere(SC, (0, 0.92, 0.55), 0.10, EMB, hot=True, name="tailspark")
    show(sp, TB(30.0), True)
    show(sp, TB(33.15), False)
    bx, by, bw, bh = -2.6, -0.95, 5.2, 1.1
    # rounded outline
    rr = 0.16
    pts = []
    for cx0, cy0, a0 in [(-bw / 2 + rr, -bh / 2 + rr, math.pi), (bw / 2 - rr, -bh / 2 + rr, -math.pi / 2),
                         (bw / 2 - rr, bh / 2 - rr, 0.0), (-bw / 2 + rr, bh / 2 - rr, math.pi / 2)]:
        for k in range(9):
            a = a0 + k / 8 * (math.pi / 2)
            pts.append((cx0 + math.cos(a) * rr, cy0 + math.sin(a) * rr))
    outline = poly3(pts, 0.02, core.sc_x(BONE, 0.75), name="btnoutline", z=0.54, cyclic=True)
    outline.location = (0, by + 0.5, 0)
    bfill = core.add_rect(SC, bx, by, bw, bh, core.sc_x(INK, 1.0), z=0.50, name="btnfill")
    btext = txt("↻  Regenerate", "mono_semi", 0.54, core.sc_x(BONE, 0.95), 0, by + 0.42, 0.56,
                align="CENTER", name="btntext")
    bnote = txt("this response could not be verified", "mono", 0.17, core.sc_x(ASH, 0.85),
                0, by - 0.55, 0.55, align="CENTER", name="btnnote")
    # cursor
    cur = mesh_quad(0.0001, 0.0001, BONE, "cursor", core.mat_emit(core.sc_x(BONE, 0.9), 1.0))
    me = bpy.data.meshes.new("cursor2")
    cpts = [(0, 0), (0, 0.34), (0.085, 0.26), (0.145, 0.39), (0.19, 0.37), (0.135, 0.24), (0.25, 0.24)]
    me.from_pydata([(p[0], p[1], 0) for p in cpts], [], [(0, 1, 2, 3, 4, 5, 6)])
    me.update()
    cursor = bpy.data.objects.new("cursorpoly", me)
    SC.collection.objects.link(cursor)
    me.materials.append(core.mat_emit(core.sc_x(BONE, 0.95), 1.0))
    cursor.location = (4.8, -3.8, 0.6)
    for ob in (outline, bfill, btext, bnote):
        show(ob, 1, False)
        show(ob, TB(31.1), True)
    show(cursor, 1, False)
    show(cursor, TB(31.2), True)
    for f in range(F(TB(31.2)), F(TB(33.0)) + 1):
        t = data.frame_to_time(SC.name, f)
        pr = ease_in_out_cubic(prog(t, TB(31.2), TB(33.0)))
        cursor.location = (lerp(4.8, 1.8, pr), lerp(-3.8, by + 0.38, pr), 0.6)
        cursor.keyframe_insert("location", frame=f)
    core.set_interp(cursor, "LINEAR", "location")
    # click
    col(btext, TB(33.0), core.sc_x(BONE, 0.95))
    col(btext, TB(33.03), core.sc_x(INK, 1.0))
    col(outline, TB(33.0), core.sc_x(BONE, 0.75))
    col(outline, TB(33.05), core.sc_x(INK, 1.0))
    clickflash = col(bfill, TB(33.0), core.sc_x(INK, 1.0))
    for f, c in [(F(TB(33.02)), core.sc_x(BONE, 0.9)), (F(TB(33.1)), core.sc_x(INK, 1.0))]:
        bfill.color = (*c, 1)
        bfill.keyframe_insert("color", frame=f)
    for ob in (outline, btext, bnote, cursor, bfill):
        show(ob, TB(33.12), False)
    show(sp, TB(30.0), True)
    show(sp, TB(33.12), False)


def make_rewind_cards():
    cards = []
    # 1 BREAKING THROUGH
    objs = [core.add_rect(SC, -9.6, -5.4, 19.2, 10.8, INK, z=0.7, name="rc1bg"),
            txt("BREAKING", "archivo", 2.15, core.sc_x(BONE, 0.92), -8.6, 0.6, 0.72, name="rc1a"),
            txt("THROUGH", "archivo", 2.15, core.sc_x(SIG, 0.95), -8.6, -2.0, 0.72, name="rc1b"),
            txt("DENSE  ·  SCALE  ·  114.99–124.54", "mono", 0.20, core.sc_x(ASH, 0.9),
                -8.6, -4.4, 0.72, name="rc1c")]
    cards.append(objs)
    # 2 NVDA: bone paper note with guilloche
    objs = [core.add_rect(SC, -9.6, -5.4, 19.2, 10.8, core.sc_x(BONE, 0.80), z=0.7, name="rc2bg"),
            txt("NVDA", "serif600", 2.8, core.sc_x(INK, 1.0), -8.5, 0.7, 0.72, name="rc2a"),
            txt("TO THE MOON", "mono_med", 0.40, core.sc_x(INK, 0.9), -8.4, -0.3, 0.72, name="rc2b"),
            txt("LUNAR RESERVE NOTE  ·  1e30", "mono", 0.16, core.sc_x(GRAPH, 0.9),
                5.6, -3.9, 0.72, align="CENTER", name="rc2c")]
    for j, rr in enumerate((3.2, 2.85, 2.5)):
        pts = [(5.6 + math.cos(i / 96 * math.tau) * rr, 0.5 + math.sin(i / 96 * math.tau) * rr, 0.72)
               for i in range(97)]
        objs.append(core.add_polyline(SC, pts, 0.009,
                                      core.sc_x(EMB, 0.8) if j == 0 else core.sc_x(GRAPH, 0.65),
                                      name=f"rc2r{j}"))
    cards.append(objs)
    # 3 SERVANT
    pp = [(-9.0 + i * 0.5, -3.35 + 0.55 * math.sin(i * 0.4), 0.71) for i in range(36)]
    objs = [core.add_rect(SC, -9.6, -5.4, 19.2, 10.8, INK, z=0.7, name="rc3bg"),
            core.add_polyline(SC, pp, 0.012, core.sc_x(GRAPH, 0.8), name="rc3line"),
            txt("SERVANT", "archivo", 2.55, core.sc_x(BONE, 0.9), -8.6, 0.4, 0.72, name="rc3a"),
            core.add_rect(SC, -8.6, -1.25, 7.5, 0.06, SIG, z=0.72, name="rc3rule"),
            txt("LOSS  ·  9.09–16.36", "mono", 0.20, core.sc_x(ASH, 0.9), -8.6, -4.4, 0.72, name="rc3b")]
    cards.append(objs)
    for objs in cards:
        for ob in objs:
            show(ob, 1, False)
    t0 = TB(33) + 0.24
    step = 0.24
    for ci, objs in enumerate(cards):
        a = t0 + ci * step
        b = a + step
        for ob in objs:
            show(ob, a, True)
            show(ob, b, False)
    return cards


def seg3(segs, w, color, name):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = w / 2
    for a, b in segs:
        sp = cu.splines.new("POLY")
        sp.points.add(1)
        sp.points[0].co = (a[0], a[1], 0, 1)
        sp.points[1].co = (b[0], b[1], 0, 1)
    cu.materials.append(core.mat_type())
    ob = bpy.data.objects.new(name, cu)
    SC.collection.objects.link(ob)
    ob.color = (*color, 1)
    return ob


# ----------------------------------------------------------------------------- opening sheet
def build_opening():
    sheet = bpy.data.objects.new("opensheet", None)
    SC.collection.objects.link(sheet)
    sheet.location = (0, 0, 0.8)
    obg = core.add_rect(SC, -9.6, -5.4, 19.2, 10.8, INK, z=-0.01, name="obg")
    obg.parent = sheet
    # grid
    segs = []
    for i in range(39):
        x = -9.6 + i * 0.5
        segs.append(((x, -5.4), (x, 5.4)))
    for j in range(22):
        y = -5.4 + j * 0.5
        segs.append(((-9.6, y), (9.6, y)))
    go = core.add_segments(SC, segs, 0.003, core.sc_x(BONE, 0.055), name="ogrid")
    go.parent = sheet
    # axes
    ax = poly3([(-6.8, -1.4), (7.2, -1.4)], 0.012, core.sc_x(BONE, 0.55), name="oax", z=0.02)
    ay = poly3([(-6.8, -1.4), (-6.8, 3.6)], 0.012, core.sc_x(BONE, 0.55), name="oay", z=0.02)
    ax.parent = sheet
    ay.parent = sheet
    tx = []
    for i in range(-3, 8):
        x = -6.8 + (i + 3) * 1.2
        tx.append(core.add_polyline(SC, [(x, -1.5, 0.02), (x, -1.3, 0.02)], 0.008, core.sc_x(BONE, 0.28)))
    for i in range(6):
        y = -1.4 + i * 0.9
        tx.append(core.add_polyline(SC, [(-6.9, y, 0.02), (-6.7, y, 0.02)], 0.008, core.sc_x(BONE, 0.28)))
    for ob in tx:
        ob.parent = sheet
    prompt = txt('% prompt: "Draw a unicorn in TikZ."', "mono", 0.17, core.sc_x(BONE, 0.85), -7.4, 3.85, 0.03, name="oprompt")
    listing1 = txt("\\begin{tikzpicture}", "mono", 0.14, core.sc_x(ASH, 0.85), -7.4, 3.52, 0.03, name="olist1")
    listing2 = txt("\\draw[unicorn];", "mono", 0.14, core.sc_x(ASH, 0.7), -7.4, 3.28, 0.03, name="olist2")
    for ob in (prompt, listing1, listing2):
        ob.parent = sheet
    pen = core.add_uv_sphere(SC, (-6.8, -1.4, 0.2), 0.09, EMB, hot=True, name="openpen")
    pen.parent = sheet
    # a few construction ticks / arcs
    arc = []
    for i in range(40):
        a = i / 39 * math.pi * 0.9
        arc.append((-6.8 + math.cos(a) * 3.2, -1.4 + math.sin(a) * 3.2, 0.01))
    ao = poly3(arc, 0.006, core.sc_x(BONE, 0.2), name="oarc", z=0.01)
    ao.parent = sheet
    # sheet scale brake
    for f, scv in [(F(TB(34.3)), 1.07), (F(TB(36.0)), 1.0), (SC.frame_end, 1.0)]:
        sheet.scale = (scv, scv, scv)
        sheet.keyframe_insert("scale", frame=f)
    core.set_interp(sheet, "BEZIER", "scale")
    for ob in [sheet] + list(sheet.children_recursive):
        pass
    # visibility: all objects shown only after the rewind
    for ob in [obg, go, ax, ay, prompt, listing1, listing2, pen, ao] + tx:
        show(ob, TB(34.28), True)
        show(ob, 1, False)
    return sheet


def build(name):
    global SC
    sc = core.new_scene(name, samples=32, motion_blur=True)
    SC = sc
    sc.frame_set(1)
    # camera: fixed perspective with a frame 19.2 wide at z=0
    cam = core.add_camera_persp(sc, (0, 0, CAMZ), (0, 0, 0), lens=50)
    cam.data.clip_start = 0.1
    cam.data.clip_end = 200.0
    # detonation shake
    for f in range(1, 46):
        t = data.frame_to_time(sc.name, f)
        a = 0.12 * math.exp(-max(0.0, t - START) * 7.0)
        cam.location = (a * math.sin(t * 91.0), a * math.cos(t * 77.0), CAMZ)
        cam.keyframe_insert("location", frame=f)
    core.set_interp(cam, "LINEAR", "location")
    # disperse on the collapse
    try:
        for n in sc.compositing_node_group.nodes:
            if n.type == "CompositorNodeLensdist":
                n.inputs["Dispersion"].default_value = 0.005
                n.inputs["Dispersion"].keyframe_insert("default_value", frame=F(TB(27.5)))
                n.inputs["Dispersion"].default_value = 0.035
                n.inputs["Dispersion"].keyframe_insert("default_value", frame=F(TB(28.05)))
                n.inputs["Dispersion"].default_value = 0.005
                n.inputs["Dispersion"].keyframe_insert("default_value", frame=F(TB(28.5)))
    except Exception as e:
        print("dispersion anim failed", e)
    s0 = set(bpy.data.objects)
    build_detonation()
    det = [o for o in bpy.data.objects if o not in s0]
    s1 = set(bpy.data.objects)
    build_overflow()
    over = [o for o in bpy.data.objects if o not in s1]
    s2 = set(bpy.data.objects)
    build_card()
    cardobjs = [o for o in bpy.data.objects if o not in s2]
    s3 = set(bpy.data.objects)
    build_tail()
    tail = [o for o in bpy.data.objects if o not in s3]
    s4 = set(bpy.data.objects)
    cards = make_rewind_cards()
    rew = [o for o in bpy.data.objects if o not in s4]
    s5 = set(bpy.data.objects)
    build_opening()
    for o in det:
        core.show_at(o, F(TB(4) + 0.1), False)
    for o in over:
        core.show_at(o, F(TB(20)), False)
        core.show_at(o, 300, False)
    for o in cardobjs:
        core.show_at(o, F(TB(30.5)), False)
    for o in tail + rew:
        if o.name.startswith("crop"):
            continue
        core.show_at(o, F(TB(34.25)), False)
    # anything whose first hide_render key says "visible" at a later frame must be hidden
    # from frame 1, or every phase would be on screen at once
    for ob in list(bpy.data.objects):
        try:
            fcs = [fc for fc in core._fcurves(ob) if fc.data_path == "hide_render"]
            if not fcs:
                continue
            ks = sorted([kp for fc in fcs for kp in fc.keyframe_points], key=lambda k: k.co.x)
            if ks and ks[0].co.x > 1.5 and ks[0].co.y < 0.5:
                ob.hide_render = True
                ob.keyframe_insert("hide_render", frame=1)
        except Exception:
            pass
    sc.frame_set(1)
    sc.render.filepath = os.path.join(core.OUT, "frames", name, "####")
    os.makedirs(os.path.dirname(sc.render.filepath), exist_ok=True)
    print("OUTRO frames", sc.frame_start, sc.frame_end, "beats", len(BD), "b0", round(TB(0), 2), "b36", round(TB(36), 2))
    return sc