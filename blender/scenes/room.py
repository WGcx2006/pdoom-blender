"""ROOM — "The room, from inside" (chorus 1). 24.090–29.544 s.

Part A  FOOM: the hook's P(DOOM) shatters; a branching tree doubles on every eighth
        (then sixteenth) and fills the frame; FOOM slams through Archivo width
        instances, its two O's become shockwave rings.
Part B  the room: a real 3D hairline library aisle. Camera crash-dollies on the
        beats; the hanging sign stamps each lyric word; cards fire from the slot;
        books slide out on the hats.
Part C  bag lands, mycelium overgrows, acid accent, SHROOMS lifts off the sign.
"""
import bpy, bmesh, math, os, sys
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pdoom import core, data
from pdoom.core import (PAL, lerp, clamp, smoothstep, ease_out_expo, ease_in_out_cubic,
                        ease_out_cubic, ease_out_back, hash01, prog, keys, sc_x)

INK, BONE, SIG, EMB, GRAPH, ASH, BLOOD, ACID = (
    PAL["ink"], PAL["bone"], PAL["signal"], PAL["ember"], PAL["graphite"],
    PAL["ash"], PAL["blood"], PAL["acid"])
TAU = math.tau
OX = 200.0        # the room lives far from the FOOM stage so the two never see each other
CJK_FONT = r"C:\Windows\Fonts\simhei.ttf"


def D(k):
    return sc_x(BONE, k)


def frame(t, sc):
    return core.frame_of(sc, t)


# ------------------------------------------------------------------ primitives
def seg3(sc, segs, width, color, name, hot=False, z=0.0):
    """Many 3D hairline segments in one curve object."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = max(width * 0.5, 0.0002)
    cu.bevel_resolution = 0
    cu.resolution_u = 1
    for a, b in segs:
        sp = cu.splines.new("POLY")
        sp.points.add(1)
        sp.points[0].co = (a[0], a[1], a[2], 1.0)
        sp.points[1].co = (b[0], b[1], b[2], 1.0)
    cu.materials.append(core.mat_hot() if hot else core.mat_type())
    ob = bpy.data.objects.new(name, cu)
    sc.collection.objects.link(ob)
    ob.color = (*color, 1.0)
    return ob


def add_cube(bm, x0, x1, y0, y1, z0, z1, mi=0):
    vs = [bm.verts.new((x, y, z)) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    for f in [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]:
        fa = bm.faces.new([vs[i] for i in f])
        fa.material_index = mi


def boxes_mesh(sc, boxes, name, mats):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    for b in boxes:
        add_cube(bm, *b[:6], mi=b[6] if len(b) > 6 else 0)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    sc.collection.objects.link(ob)
    return ob


def box_segs(x0, x1, y0, y1, z0, z1):
    p = {}
    for xi, x in enumerate((x0, x1)):
        for yi, y in enumerate((y0, y1)):
            for zi, z in enumerate((z0, z1)):
                p[(xi, yi, zi)] = (x, y, z)
    out = []
    for i in range(8):
        for j in range(i + 1, 8):
            xi, yi, zi = (i >> 2) & 1, (i >> 1) & 1, i & 1
            xj, yj, zj = (j >> 2) & 1, (j >> 1) & 1, j & 1
            if abs(xi - xj) + abs(yi - yj) + abs(zi - zj) == 1:
                out.append((p[(xi, yi, zi)], p[(xj, yj, zj)]))
    return out


def show_group(ob, f, vis):
    core.show_at(ob, f, vis)
    for ch in ob.children_recursive:
        core.show_at(ch, f, vis)


def txt(sc, body, size, color, loc, rot=(0, 0, 0), font="archivo", align="LEFT", hot=False):
    return core.add_text(sc, body, font, size, color, loc, rot=rot, align_x=align,
                         name="t_" + body[:8], hot=hot)


# ------------------------------------------------------------------ timing
def setup_times(sc):
    L1 = data.line("future goes")
    L2 = data.line("Chinese room")
    L3 = data.line("bag of shrooms")
    T = {"L1": L1, "L2": L2, "L3": L3}
    T["w1"] = L1["words"]
    T["w2"] = L2["words"]
    T["w3"] = L3["words"]
    T["foo"] = T["w1"][-1]["start"]
    T["cut"] = T["w2"][0]["start"]
    T["bag"] = T["w3"][2]["start"]
    T["shrooms"] = T["w3"][-1]["start"]
    T["t0"] = data.SCENES[sc.name]["start"]
    T["t1"] = data.SCENES[sc.name]["end"]
    return T


# ================================================================== PART A: FOOM
def build_foom(sc, T):
    root = (0.0, -0.35)
    # faint polar graph paper around the root ---------------------------------
    segs = []
    for r in (1.2, 2.4, 3.6, 4.8, 6.0, 7.2, 9.2, 11.4):
        n = 72
        for i in range(n):
            a0, a1 = TAU * i / n, TAU * (i + 1) / n
            segs.append(((root[0] + math.cos(a0) * r, root[1] + math.sin(a0) * r, -2),
                         (root[0] + math.cos(a1) * r, root[1] + math.sin(a1) * r, -2)))
    for i in range(36):
        a = TAU * i / 36
        segs.append(((root[0] + math.cos(a) * 1.0, root[1] + math.sin(a) * 1.0, -2),
                     (root[0] + math.cos(a) * 12.5, root[1] + math.sin(a) * 12.5, -2)))
    grid = seg3(sc, segs, 0.006, D(0.085), "foom_polar")
    core.color_at(grid, 1, (0, 0, 0))
    core.color_at(grid, max(1, frame(T["t0"], sc) - 1), (0, 0, 0))
    core.color_at(grid, frame(T["w1"][0]["start"] + 0.45, sc), D(0.085))
    core.set_interp(grid, "BEZIER", "color")

    # the hook's P(DOOM), then it shatters into line debris -------------------
    psz = 10.6 / max(1e-4, core.measure(sc, "P(DOOM)", "archivo", 1.0))
    keep = core.add_text(sc, "P(DOOM)", "archivo", psz, D(0.9), (0.0, -0.35 - 0.36 * psz, 0), align_x="CENTER")
    core.show_at(keep, 1, True)
    core.show_at(keep, frame(T["w1"][0]["start"] + 0.06, sc), False)
    build_debris(sc, T, keep)

    # branching tree: one curve object per generation ------------------------
    gtimes, gt = [], T["w1"][0]["start"]
    b = math.ceil((gt + 0.02) / data.BEAT_PERIOD * 2) / 2
    while data.time_of_beat(b) < T["foo"] - 0.02:
        gtimes.append(data.time_of_beat(b)); b += 0.5
    gtimes.append(T["foo"])
    b = math.ceil(T["foo"] / data.BEAT_PERIOD * 4) / 4
    while data.time_of_beat(b) < T["cut"] - 0.04 and len(gtimes) < 9:
        gtimes.append(data.time_of_beat(b)); b += 1
    gtimes.append(T["cut"])
    NG = len(gtimes) - 1

    branches = []

    def make(g, x, y, z, a):
        pts = [(x, y, z)]
        L = 2.45 * (0.78 ** g) * (0.8 + 0.42 * hash01(7, g, round(x, 2), round(y, 2)))
        n = 8
        ang = a
        curv = (hash01(11, g, round(x, 2), 3) - 0.5) * 1.7
        for i in range(n):
            ang += curv / n * (0.6 + 0.8 * i / n) + (hash01(13, g, i, round(x, 1)) - 0.5) * 0.14
            x += math.cos(ang) * L / n
            y += math.sin(ang) * L / n
            z += (hash01(17, g, i, round(y, 1)) - 0.5) * 0.08
            pts.append((x, y, z))
        branches.append((g, pts))
        if g + 1 < NG:
            rdx, rdy = x - root[0], (y - root[1]) * 1.4
            rad = math.atan2(rdy, rdx)
            dA = rad - ang
            dA = math.atan2(math.sin(dA), math.cos(dA))
            base = ang + dA * (0.0 if g < 1 else 0.30)
            spread = (0.85 if g < 2 else 0.44) + 0.26 * hash01(19, g, round(x, 2))
            tw = (hash01(23, g, round(y, 2)) - 0.5) * 0.16
            make(g + 1, x, y, z, base - spread + tw)
            make(g + 1, x, y, z, base + spread + tw)

    make(0, root[0], root[1], 0.0, -0.38)
    make(0, root[0], root[1], 0.0, 2.55)
    for g in range(NG):
        segs = []
        for gg, pts in branches:
            if gg != g:
                continue
            for i in range(len(pts) - 1):
                segs.append((pts[i], pts[i + 1]))
        if not segs:
            continue
        w = max(0.024, 0.036 * (0.87 ** g))
        ob = seg3(sc, segs, w, EMB, "tree%d" % g)
        ob.data.bevel_factor_mapping_end = "SPLINE"
        f0 = max(1, frame(gtimes[g], sc))
        f1 = max(f0 + 1, frame(gtimes[g] + 0.20, sc))
        ob.data.bevel_factor_end = 0.0
        ob.data.keyframe_insert("bevel_factor_end", frame=max(1, f0 - 1))
        ob.data.bevel_factor_end = 1.0
        ob.data.keyframe_insert("bevel_factor_end", frame=f1)
        act = ob.data.animation_data.action
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for fc in bag.fcurves:
                        for kp in fc.keyframe_points:
                            kp.interpolation = "LINEAR"
        # cooling: hot at birth, bone after
        core.color_at(ob, 1, (0, 0, 0))
        core.color_at(ob, max(1, f0 - 1), (0, 0, 0))
        core.color_at(ob, f0, SIG)
        core.color_at(ob, min(sc.frame_end, f0 + 4), D(0.92))
        core.color_at(ob, min(sc.frame_end, f0 + 18), D(0.62))
        core.set_interp(ob, "BEZIER", "color")

    # the FOOM word, stepping through width instances ------------------------
    widths = [62, 75, 87.5, 100, 112.5, 125]
    fonts = ["archivo_w62_900", "archivo_w75_900", "archivo_w87_900",
             "archivo", "archivo_w112_900", "archivo_w125_900"]
    steps = []
    for k in range(6):
        W = lerp(5.6, 14.2, (k / 5.0) ** 1.25)
        s = W / max(1e-4, core.measure(sc, "FOOM", fonts[k], 1.0))
        steps.append((fonts[k], s, W))
    groups = []
    for k, (fk, s, W) in enumerate(steps):
        grp = []
        wF = core.measure(sc, "F", fk, s)
        wFO = core.measure(sc, "FO", fk, s)
        wFOO = core.measure(sc, "FOO", fk, s)
        wFOOM = core.measure(sc, "FOOM", fk, s)
        x0 = -W / 2
        base = -0.30 - 0.36 * s
        o1 = x0 + (wF + wFO) * 0.5
        o2 = x0 + (wFO + wFOO) * 0.5
        r = max(0.15, (wFOO - wFO) * 0.5 * 0.86)
        g1 = core.add_text(sc, "F", fk, s, BONE, (x0, base, 1.0), align_x="CENTER")
        # centre-align each single glyph by shifting by half its own width
        g1.location = (x0 + wF * 0.5, base, 1.0)
        g2 = core.add_text(sc, "M", fk, s, BONE, (x0 + wFOO + (wFOOM - wFOO) * 0.5, base, 1.0), align_x="CENTER")
        for o in (g1, g2):
            grp.append(o)
        for oc in (o1, o2):
            pts = [(oc + math.cos(TAU * i / 72) * r, base + 0.36 * s + math.sin(TAU * i / 72) * r, 1.0) for i in range(72)]
            ro = core.add_polyline(sc, pts, max(0.018, 0.055 * s / 2.2), SIG, z=1.0, cyclic=True, hot=True)
            grp.append(ro)
        groups.append(grp)
    # visibility ladder
    f_foo = frame(T["foo"], sc)
    for k, grp in enumerate(groups):
        t_on = T["foo"] + k * data.BEAT_PERIOD / 4.0
        f_on = frame(t_on, sc)
        f_off = frame(T["foo"] + (k + 1) * data.BEAT_PERIOD / 4.0, sc) if k < 5 else sc.frame_end + 1
        for o in grp:
            core.show_at(o, 1, False)
            core.show_at(o, max(1, f_on), True)
            core.show_at(o, max(2, f_off), False)
    # FOOM slam scale on its first frame
    for o in groups[0]:
        o.scale = (1.1, 1.1, 1)
        o.keyframe_insert("scale", frame=max(1, f_foo - 1))
        o.scale = (1, 1, 1)
        o.keyframe_insert("scale", frame=f_foo + 3)

    # shockwave rings from the O's -------------------------------------------
    for n in range(10):
        te = T["foo"] + n * data.BEAT_PERIOD / 2.0
        if te > T["cut"]:
            break
        k = min(5, int(round((te - T["foo"]) / (data.BEAT_PERIOD / 4.0))))
        fk, s, W = steps[k]
        wF = core.measure(sc, "F", fk, s)
        wFO = core.measure(sc, "FO", fk, s)
        wFOO = core.measure(sc, "FOO", fk, s)
        x0 = -W / 2
        base = -0.30 - 0.36 * s
        for oc in (x0 + (wF + wFO) * 0.5, x0 + (wFO + wFOO) * 0.5):
            pts = [(math.cos(TAU * i / 96), math.sin(TAU * i / 96), 0) for i in range(96)]
            ob = core.add_polyline(sc, pts, 0.016, EMB, z=0.9, cyclic=True, hot=True)
            ob.location = (oc, base + 0.5 * s * 0.72, 0.9)
            f_on = max(1, frame(te, sc))
            ob.scale = (0.2, 0.2, 1)
            ob.keyframe_insert("scale", frame=f_on)
            ob.scale = (18.0, 18.0, 1)
            ob.keyframe_insert("scale", frame=min(sc.frame_end, f_on + 26))
            core.set_interp(ob, "BEZIER", "scale")
            core.show_at(ob, 1, False)
            core.show_at(ob, f_on, True)
            core.color_at(ob, f_on, SIG)
            core.color_at(ob, min(sc.frame_end, f_on + 10), (0.55, 0.06, 0.008))
            core.color_at(ob, min(sc.frame_end, f_on + 22), (0, 0, 0))
            core.set_interp(ob, "BEZIER", "color")

    # lyric stack, top left ---------------------------------------------------
    x_left = -8.28
    rows = [([0, 1], 0.90), ([2], 1.38), ([3], 1.38)]
    yy = 3.70
    for idx, size in rows:
        xx = x_left
        for wi in idx:
            w = T["w1"][wi]
            body = w["w"].upper().replace("'", "\u2019")
            ob = txt(sc, body, size, D(0.28), (xx, yy, 2.0), font="archivo_w75_900")
            xx += core.measure(sc, body, "archivo_w75_900", size) + size * 0.26
            core.animate_words(sc, [(w, ob)], sung=D(0.96), dim=D(0.28), pre=0.0)
        yy -= size * 0.88
    # header
    hdr = core.add_text(sc, "GROWTH, AS ADVERTISED", "mono_med", 0.13, D(0.32), (-8.9, 4.62, 2.0), spacing=1.12)
    core.show_at(hdr, 1, False)
    core.show_at(hdr, frame(T["w1"][0]["start"] - 0.25, sc), True)

    # branch counter, top right ----------------------------------------------
    hdr2 = core.add_text(sc, "BRANCHES", "mono_med", 0.13, D(0.34), (8.9, 4.62, 2.0), align_x="RIGHT", spacing=1.12)
    core.show_at(hdr2, 1, False)
    core.show_at(hdr2, frame(T["w1"][0]["start"] - 0.25, sc), True)
    for g in range(NG):
        f_on = frame(gtimes[g], sc)
        ob = core.add_text(sc, "%04d" % (2 ** g), "mono_med", 0.46, D(0.9),
                           (8.9, 4.0, 2.0), align_x="RIGHT")
        core.show_at(ob, 1, False)
        core.show_at(ob, max(1, f_on), True)
        if g < NG - 1:
            core.show_at(ob, max(2, f_on + 1), False)
    core.add_text(sc, "n(t) = 2^k", "mono_med", 0.12, D(0.26), (8.9, 3.72, 2.0),
                  align_x="RIGHT", spacing=1.06)


def build_debris(sc, T, keep):
    """Sample the P(DOOM) outline and throw it apart as short strokes."""
    dg = bpy.context.evaluated_depsgraph_get()
    me = keep.evaluated_get(dg).to_mesh()
    edges = {}
    for p in me.polygons:
        vs = list(p.vertices)
        for i in range(len(vs)):
            e = tuple(sorted((vs[i], vs[(i + 1) % len(vs)])))
            edges[e] = edges.get(e, 0) + 1
    segs = []
    for (a, b), n in edges.items():
        if n != 1:
            continue
        va, vb = me.vertices[a].co, me.vertices[b].co
        L = (vb - va).length
        k = max(1, int(L / 0.16))
        for i in range(k):
            u0, u1 = i / k, (i + 1) / k
            segs.append((va.lerp(vb, u0), va.lerp(vb, u1)))
    keep.evaluated_get(dg).to_mesh_clear()
    base_y = -0.35 - 0.36 * (10.6 / max(1e-4, core.measure(sc, "P(DOOM)", "archivo", 1.0)))
    # mesh coords are local to the text object; lift them to where P(DOOM) sat
    f0 = frame(T["w1"][0]["start"], sc)
    for i, (a, b) in enumerate(segs):
        a = Vector((a.x, a.y + base_y, 0.2)); b = Vector((b.x, b.y + base_y, 0.2))
        ob = core.add_polyline(sc, [(a.x, a.y, 0.2), (b.x, b.y, 0.2)], 0.012, BONE, z=0.2)
        ax, ay = (a.x + b.x) * 0.5, (a.y + b.y) * 0.5 - base_y
        r = math.hypot(ax, ay + 1.0) + 0.001
        vx = ax / r * (7 + 9 * hash01(i, 3)) + (hash01(i, 5) - 0.5) * 6
        vy = (ay + 1.0) / r * (7 + 9 * hash01(i, 7)) + (hash01(i, 9) - 0.5) * 6
        life = 0.45 + 0.5 * hash01(i, 11)
        core.show_at(ob, 1, False)
        core.show_at(ob, max(1, f0 - 1), True)
        core.show_at(ob, min(sc.frame_end, frame(T["w1"][0]["start"] + life, sc)), False)
        for f in range(max(1, f0), min(sc.frame_end, frame(T["w1"][0]["start"] + life, sc)) + 1):
            dt = (f - f0) / 30.0
            ob.location = (vx * dt, vy * dt - 5.0 * dt * dt, 0.2)
            ob.rotation_euler = (0, 0, (hash01(i, 13) - 0.5) * 9 * dt)
            ob.keyframe_insert("location", frame=f)
            ob.keyframe_insert("rotation_euler", frame=f)
        core.set_interp(ob, "LINEAR", "location")
        core.color_at(ob, max(1, f0), EMB)
        core.color_at(ob, min(sc.frame_end, f0 + 8), D(0.7))
        core.set_interp(ob, "BEZIER", "color")


# ================================================================== PART B: the room
SHELF_Y = [0.06, 0.70, 1.34, 1.98, 2.62, 3.18]
ROOM_X = 2.30
ROOM_TOP = 3.30
BACK_Z = -9.60
FRONT_Z = 2.90
DESK = dict(x0=-0.86, x1=0.86, z0=-4.62, z1=-3.88, h=0.75)
BOARD = dict(x=0.30, y=2.56, z=-5.00, w=3.28, h=1.16)
SLOT = dict(x=0.0, y=1.76, z=BACK_Z + 0.03, w=1.10, h=0.30)


def build_room(sc):
    dark = core.mat_lit(tuple(c * 0.12 for c in GRAPH), rough=0.8)
    darker = core.mat_lit(tuple(c * 0.07 for c in GRAPH), rough=0.9)
    bookmat = core.mat_lit(tuple(c * 0.02 for c in GRAPH), rough=0.75)
    panel = core.mat_lit(BONE, rough=0.4, emission=(*D(1.0),), emission_strength=0.22)
    warm = core.mat_lit(tuple(c * 0.9 for c in GRAPH), rough=0.4, emission=(*SIG,), emission_strength=0.18)
    boxes = []
    slide_books = []
    from collections import defaultdict
    lines = defaultdict(list)

    def bucket(z):
        return 0.9 if z > 0.8 else (0.6 if z > -2.6 else (0.38 if z > -5.6 else 0.22))

    # shell -------------------------------------------------------------------
    for sx in (-ROOM_X, ROOM_X):
        lines[bucket(2.0)].append(((OX + sx, 0, FRONT_Z), (OX + sx, 0, BACK_Z)))
        lines[bucket(2.0)].append(((OX + sx, ROOM_TOP, FRONT_Z), (OX + sx, ROOM_TOP, BACK_Z)))
        lines[bucket(BACK_Z)].append(((OX + sx, 0, BACK_Z), (OX + sx, ROOM_TOP, BACK_Z)))
    boxes.append((OX - ROOM_X - 0.06, OX - ROOM_X, 0, ROOM_TOP, BACK_Z, FRONT_Z, 1))
    boxes.append((OX + ROOM_X, OX + ROOM_X + 0.06, 0, ROOM_TOP, BACK_Z, FRONT_Z, 1))
    boxes.append((OX - ROOM_X, OX + ROOM_X, -0.05, 0, BACK_Z, FRONT_Z, 2))
    boxes.append((OX - ROOM_X, OX + ROOM_X, ROOM_TOP, ROOM_TOP + 0.08, BACK_Z, FRONT_Z, 1))
    boxes.append((OX - ROOM_X, OX + ROOM_X, 0, ROOM_TOP, BACK_Z - 0.1, BACK_Z, 1))

    # floor grid + ceiling grid ----------------------------------------------
    for i in range(1, 10):
        x = OX - ROOM_X + i * (2 * ROOM_X / 10)
        lines[0.11].append(((x, 0.002, FRONT_Z), (x, 0.002, BACK_Z)))
    z = FRONT_Z
    while z > BACK_Z + 0.01:
        lines[0.11].append(((OX - ROOM_X, 0.002, z), (OX + ROOM_X, 0.002, z)))
        z -= 0.55
    for i in range(0, 7):
        x = OX - ROOM_X + i * (2 * ROOM_X / 6)
        lines[0.07].append(((x, ROOM_TOP - 0.01, FRONT_Z), (x, ROOM_TOP - 0.01, BACK_Z)))
    z = FRONT_Z
    while z > BACK_Z + 0.01:
        lines[0.07].append(((OX - ROOM_X, ROOM_TOP - 0.01, z), (OX + ROOM_X, ROOM_TOP - 0.01, z)))
        z -= 1.1

    # ceiling light panels ----------------------------------------------------
    for zc in (1.2, -1.3, -3.8, -6.3, -8.6):
        boxes.append((OX - 0.30, OX + 0.30, ROOM_TOP - 0.025, ROOM_TOP - 0.012, zc - 0.58, zc + 0.58, 3))
        lines[0.42].append(((OX - 0.30, ROOM_TOP - 0.02, zc - 0.58), (OX - 0.30, ROOM_TOP - 0.02, zc + 0.58)))
        lines[0.42].append(((OX + 0.30, ROOM_TOP - 0.02, zc - 0.58), (OX + 0.30, ROOM_TOP - 0.02, zc + 0.58)))

    # shelves with books ------------------------------------------------------
    books = []
    z0, z1 = 2.55, BACK_Z + 0.05
    depth = 0.44
    for side in (-1, 1):
        xw = OX + side * ROOM_X
        xf = xw - side * depth
        for y in SHELF_Y[:-1]:
            boxes.append((min(xw, xf) - 0.01, max(xw, xf) + 0.01, y, y + 0.035, z1, z0, 1))
            lines[0.75].append(((xf, y + 0.035, z0), (xf, y + 0.035, z1)))
            lines[0.5].append(((xf, y, z0), (xf, y, z1)))
        bays = 8
        for i in range(bays + 1):
            zc = z0 + (z1 - z0) * i / bays
            boxes.append((min(xw, xf), max(xw, xf), SHELF_Y[0], ROOM_TOP - 0.05, zc - 0.025, zc + 0.025, 1))
            lines[0.85].append(((xf, SHELF_Y[0], zc), (xf, ROOM_TOP - 0.12, zc)))
            lines[0.55].append(((xw, SHELF_Y[0], zc), (xw, ROOM_TOP - 0.12, zc)))
        # books
        for s in range(len(SHELF_Y) - 1):
            yb = SHELF_Y[s] + 0.035
            gap = SHELF_Y[s + 1] - yb - 0.05
            z = z0 - 0.05
            guard = 0
            while z > z1 + 0.1 and guard < 400:
                guard += 1
                th = 0.045 + 0.055 * hash01(side, s, round(z, 2), 1)
                if hash01(side, s, round(z, 2), 2) < 0.05:
                    z -= 0.10 + 0.16 * hash01(side, s, round(z, 2), 3)
                    continue
                zb = z - th
                h = gap * (0.66 + 0.32 * hash01(side, s, round(z, 2), 4))
                h = min(h, gap - 0.02)
                dep = 0.24 + 0.05 * hash01(side, s, round(z, 2), 5)
                xa = xf + side * 0.005
                xb = xa + side * dep
                dark_i = 4 + int(hash01(side, s, round(z, 2), 6) * 2)
                boxes.append((min(xa, xb), max(xa, xb), yb, yb + h, zb, z, dark_i))
                k = bucket(z)
                for e in box_segs(min(xa, xb), max(xa, xb), yb, yb + h, zb, z):
                    lines[k].append(e)
                # spine bands
                lines[k].append(((xa + side * 0.003, yb + h * 0.70, z), (xa + side * 0.003, yb + h * 0.70, zb)))
                lines[k].append(((xa + side * 0.003, yb + h * 0.82, z), (xa + side * 0.003, yb + h * 0.82, zb)))
                if hash01(side, s, round(z, 2), 77) < 0.018:
                    slide_books.append((side, xa, xb, yb, yb + h, zb, z))
                else:
                    books.append((xa, xb, yb, yb + h, zb, z, side))
                z = zb - 0.004
    # book bodies: merged
    body = boxes_mesh(sc, boxes, "room_boxes", [bookmat, dark, darker, panel,
                                                core.mat_lit(tuple(c * 0.05 for c in GRAPH)),
                                                core.mat_lit(tuple(c * 0.01 for c in GRAPH)),
                                                core.mat_lit(tuple(c * 0.03 for c in GRAPH)),
                                                core.mat_lit(tuple(c * 0.02 for c in GRAPH))])
    for k, segs in lines.items():
        if segs:
            seg3(sc, segs, 0.0072 if k > 0.5 else 0.006, D(k), "room_lines_%d" % int(k * 100))

    # back wall furniture -----------------------------------------------------
    bl = []
    # slot bezel
    sx0, sx1 = OX - SLOT["w"] / 2, OX + SLOT["w"] / 2
    sy0, sy1 = SLOT["y"] - SLOT["h"] / 2, SLOT["y"] + SLOT["h"] / 2
    for (a, b) in box_segs(sx0, sx1, sy0, sy1, BACK_Z + 0.02, BACK_Z + 0.10):
        bl.append((a, b))
    lines2 = [(b) for b in bl]
    seg3(sc, lines2, 0.009, D(0.9), "slot_bezel")
    slotp = core.add_rect(sc, OX - SLOT["w"] / 2 + 0.03, sy0 + 0.03, SLOT["w"] - 0.06, SLOT["h"] - 0.06, SIG, z=BACK_Z + 0.021)
    slotp.data.materials.clear()
    slotp.data.materials.append(core.mat_lit(SIG, rough=0.4, emission=(*EMB,), emission_strength=2.4))
    slotp.color = (*SIG, 1)
    # a door with no handle
    dl = [(OX + 1.28, 0, BACK_Z + 0.02), (OX + 2.16, 0, BACK_Z + 0.02), (OX + 2.16, 2.08, BACK_Z + 0.02),
          (OX + 1.28, 2.08, BACK_Z + 0.02), (OX + 1.28, 0, BACK_Z + 0.02)]
    seg3(sc, [(dl[i], dl[i + 1]) for i in range(4)], 0.008, D(0.55), "back_door")
    seg3(sc, [((OX + 1.36, 0.02, BACK_Z + 0.02), (OX + 1.36, 2.0, BACK_Z + 0.02)),
              ((OX + 1.36, 2.0, BACK_Z + 0.02), (OX + 2.08, 2.0, BACK_Z + 0.02)),
              ((OX + 2.08, 2.0, BACK_Z + 0.02), (OX + 2.08, 0.02, BACK_Z + 0.02))], 0.005, D(0.3), "back_door2")

    # desk -------------------------------------------------------------------
    d = DESK
    boxes2 = [(OX + d["x0"], OX + d["x1"], d["h"] - 0.04, d["h"], d["z0"], d["z1"], 1),
              (OX + d["x0"], OX + d["x1"], d["h"] - 0.10, d["h"] - 0.04, d["z1"] - 0.03, d["z1"], 2)]
    for lx in (d["x0"] + 0.05, d["x1"] - 0.05):
        for lz in (d["z0"] + 0.05, d["z1"] - 0.05):
            boxes2.append((OX + lx - 0.025, OX + lx + 0.025, 0, d["h"] - 0.04, lz - 0.025, lz + 0.025, 1))
    boxes_mesh(sc, boxes2, "desk_boxes", [dark, darker])
    dl2 = []
    for lx in (d["x0"] + 0.05, d["x1"] - 0.05):
        for lz in (d["z0"] + 0.05, d["z1"] - 0.05):
            dl2 += box_segs(OX + lx - 0.025, OX + lx + 0.025, 0, d["h"] - 0.04, lz - 0.025, lz + 0.025)
    dl2 += box_segs(OX + d["x0"], OX + d["x1"], d["h"] - 0.04, d["h"], d["z0"], d["z1"])
    seg3(sc, dl2, 0.0075, D(0.8), "desk_lines")

    # books that slide out on the hats (own objects so they can move)
    for i, (side, xa, xb, yb, yc, zb, z) in enumerate(slide_books):
        cx = (xa + xb) * 0.5
        root = bpy.data.objects.new("slide_%d" % i, None)
        sc.collection.objects.link(root)
        root.location = (cx, (yb + yc) * 0.5, (zb + z) * 0.5)
        me = bpy.data.meshes.new("slidem")
        bm = bmesh.new()
        add_cube(bm, -abs(xb - xa) * 0.5, abs(xb - xa) * 0.5, -abs(yc - yb) * 0.5,
                 abs(yc - yb) * 0.5, -abs(z - zb) * 0.5, abs(z - zb) * 0.5, 0)
        bm.to_mesh(me); bm.free()
        me.materials.append(core.mat_lit(tuple(c * 0.02 for c in GRAPH), rough=0.75))
        bo = bpy.data.objects.new("slidebody_%d" % i, me)
        sc.collection.objects.link(bo); bo.parent = root
        sl = []
        w2 = abs(xb - xa) * 0.5; h2 = abs(yc - yb) * 0.5; d2 = abs(z - zb) * 0.5
        sl += box_segs(-w2, w2, -h2, h2, -d2, d2)
        sl.append(((-w2, h2 * 0.4, d2), (w2, h2 * 0.4, d2)))
        sl.append(((-w2, -h2 * 0.2, d2), (w2, -h2 * 0.2, d2)))
        so = seg3(sc, sl, 0.006, D(0.55), "slidelines_%d" % i)
        so.parent = root
        slide_books[i] = (root, side, cx, (yb + yc) * 0.5, (zb + z) * 0.5, w2)

    return books, slide_books


def build_sign(sc, T):
    """Hanging flip-board: the lyric is stamped on word by word."""
    dark = core.mat_lit(tuple(c * 0.06 for c in GRAPH), rough=0.55)
    bd = bpy.data.objects.new("board", None)
    sc.collection.objects.link(bd)
    bd.location = (OX + BOARD["x"], BOARD["y"], BOARD["z"])
    me = bpy.data.meshes.new("board")
    bm = bmesh.new()
    add_cube(bm, -BOARD["w"] / 2, BOARD["w"] / 2, -BOARD["h"] / 2, BOARD["h"] / 2, -0.035, 0.035, 0)
    bm.to_mesh(me); bm.free()
    me.materials.append(dark)
    board = bpy.data.objects.new("board_mesh", me)
    sc.collection.objects.link(board)
    board.parent = bd
    # frame
    fr = []
    for (a, b) in box_segs(-BOARD["w"] / 2, BOARD["w"] / 2, -BOARD["h"] / 2, BOARD["h"] / 2, -0.04, 0.04):
        fr.append((a, b))
    fr_ob = seg3(sc, fr, 0.012, D(0.95), "board_frame")
    fr_ob.parent = bd
    # hanging rods
    rods = [((OX + BOARD["x"] - BOARD["w"] / 2 + 0.12, BOARD["y"] + BOARD["h"] / 2, BOARD["z"]),
             (OX + BOARD["x"] - BOARD["w"] / 2 + 0.12, ROOM_TOP, BOARD["z"])),
            ((OX + BOARD["x"] + BOARD["w"] / 2 - 0.12, BOARD["y"] + BOARD["h"] / 2, BOARD["z"]),
             (OX + BOARD["x"] + BOARD["w"] / 2 - 0.12, ROOM_TOP, BOARD["z"]))]
    seg3(sc, rods, 0.008, D(0.6), "board_rods")

    w2 = T["w2"]
    words1 = "TRAPPED IN THE".split()
    size1 = 2.86 / max(1e-4, core.measure(sc, "TRAPPED IN THE", "archivo_w75_900", 1.0))
    sw = core.space_width(sc, "archivo_w75_900", size1)
    xx = -1.44
    for i, body in enumerate(words1):
        w = w2[i]
        ob = core.add_text(sc, body, "archivo_w75_900", size1, D(0.95), (xx, 0.16, 0.05))
        ob.parent = bd
        xx += core.measure(sc, body, "archivo_w75_900", size1) + sw * 1.55
        stamp(sc, ob, T, w["start"], 1.6)
    # row two: CHINESE ROOM,
    big = "CHINESE ROOM,"
    size2 = 3.02 / max(1e-4, core.measure(sc, big, "archivo_w75_900", 1.0))
    sw2 = core.space_width(sc, "archivo_w75_900", size2)
    xx = -1.52
    for i, body in enumerate(["CHINESE", "ROOM,"]):
        w = w2[3 + i]
        col = SIG if i == 0 else BONE
        ob = core.add_text(sc, body, "archivo_w75_900", size2, col, (xx, -0.52, 0.05), hot=(i == 0))
        ob.parent = bd
        xx += core.measure(sc, body, "archivo_w75_900", size2) + sw2 * 1.3
        stamp(sc, ob, T, w["start"], 1.35)
    core.add_text(sc, "MYC-0417  \u00b7  INSTRUCTIONS", "mono_med", 0.040, D(0.30),
                  (1.56, 0.30, 0.05), align_x="RIGHT").parent = bd
    # board faces the lyric, but the line is set left; a hairline under it
    core.add_polyline(sc, [(OX + BOARD["x"] - 1.38, BOARD["y"] - 0.66, BOARD["z"] + 0.05),
                           (OX + BOARD["x"] + 1.38, BOARD["y"] - 0.66, BOARD["z"] + 0.05)], 0.005, D(0.35))

    # face B: "WITH A BAG OF / SHROOMS"
    w3 = T["w3"]
    sizeB1 = 2.5 / max(1e-4, core.measure(sc, "WITH A BAG OF", "archivo_w75_900", 1.0))
    swB = core.space_width(sc, "archivo_w75_900", sizeB1)
    xx = -1.25
    rowB = []
    for i, body in enumerate("WITH A BAG OF".split()):
        w = w3[i]
        ob = core.add_text(sc, body, "archivo_w75_900", sizeB1, D(0.8), (xx, 0.16, 0.05))
        ob.parent = bd
        xx += core.measure(sc, body, "archivo_w75_900", sizeB1) + swB * 1.3
        rowB.append((w, ob))
    sizeB2 = 2.72 / max(1e-4, core.measure(sc, "SHROOMS", "archivo_w125_900", 1.0))
    sh = core.add_text(sc, "SHROOMS", "archivo_w125_900", sizeB2, ACID, (-1.62, -0.60, 0.06))
    sh.parent = bd
    for w, ob in rowB:
        core.show_at(ob, 1, False)
        core.show_at(ob, frame(w["start"], sc), True)
        core.color_at(ob, 1, D(0.25))
        core.color_at(ob, max(1, frame(w["start"], sc)), D(0.85))
    core.show_at(sh, 1, False)
    core.show_at(sh, frame(w3[-1]["start"], sc), True)
    f_sh = frame(T["shrooms"], sc)
    sh.color = (*ACID, 1)
    core.color_at(sh, 1, ACID)
    # lift off on "shrooms"
    sh.location = (-1.62, -0.60, 0.06)
    sh.keyframe_insert("location", frame=f_sh)
    sh.scale = (1, 1, 1)
    sh.keyframe_insert("scale", frame=f_sh)
    sh.location = (-1.62, -0.32, 0.24)
    sh.rotation_euler = (0.02, 0, -0.010)
    sh.scale = (1.06, 1.06, 1)
    sh.keyframe_insert("location", frame=f_sh + 11)
    sh.keyframe_insert("rotation_euler", frame=f_sh + 11)
    sh.keyframe_insert("scale", frame=f_sh + 11)
    core.set_interp(sh, "BEZIER", "location")
    core.set_interp(sh, "BEZIER", "scale")
    # echo trails
    for k, (dx, dz, cc) in enumerate([(-0.26, -0.02, 0.10)]):
        e = core.add_text(sc, "SHROOMS", "archivo_w125_900", sizeB2, D(cc), (-1.62 + dx, -0.60, 0.0), align_x="LEFT")
        e.parent = bd
        core.show_at(e, 1, False)
        core.show_at(e, f_sh + 1, True)
        e.location = (-1.62, -0.60, 0.06)
        e.keyframe_insert("location", frame=f_sh + 1)
        e.location = (-1.62 + dx, -0.62, 0.05)  # behind, below: a shadow echo
        e.keyframe_insert("location", frame=f_sh + 13)
        core.set_interp(e, "BEZIER", "location")

    # the board flips on the snare with "with"
    f_flip = frame(T["w3"][0]["start"] - 0.10, sc)
    # face A leaves when the board turns
    for ob in list(bd.children):
        if ob.type == "FONT" and ob.data.body in ("TRAPPED", "IN", "THE", "CHINESE", "ROOM,"):
            core.show_at(ob, f_flip, False)
    bd.rotation_euler = (0, 0, 0)
    bd.keyframe_insert("rotation_euler", frame=max(1, f_flip - 1))
    bd.rotation_euler = (TAU, 0, 0)
    bd.keyframe_insert("rotation_euler", frame=f_flip + 5)
    core.set_interp(bd, "BEZIER", "rotation_euler")
    # sign jolts on every stamp
    stamps = [w["start"] for w in w2] + [w["start"] for w in w3[1:]]
    for i, ts in enumerate(stamps):
        for k in range(3):
            f = frame(ts + k * 0.07, sc)
            bd.rotation_euler.z = 0.010 * math.sin(k * 2.1 + i) * (1 - k / 3.0)
            bd.keyframe_insert("rotation_euler", index=2, frame=f)
    return bd, sh


def stamp(sc, ob, T, t, s0=1.5):
    f = max(1, frame(t, sc))
    base = tuple(ob.location)
    ob.scale = (s0, s0, 1)
    ob.location = (base[0], base[1] - 0.06, base[2] - 0.04)
    ob.keyframe_insert("scale", frame=max(1, f - 1))
    ob.keyframe_insert("location", frame=max(1, f - 1))
    core.show_at(ob, 1, False)
    core.show_at(ob, f, True)
    ob.scale = (1, 1, 1)
    ob.location = base
    ob.keyframe_insert("scale", frame=f + 4)
    ob.keyframe_insert("location", frame=f + 4)
    core.set_interp(ob, "BEZIER", "scale")
    core.set_interp(ob, "BEZIER", "location")


def animate_slides(sc, T, sliders):
    hats = [p[0] for p in data.AUD["onsets"]["hat"] if T["cut"] < p[0] < T["t1"] - 0.25]
    if not hats or not sliders:
        return
    step = max(1, len(hats) // 9)
    for j, th in enumerate(hats[::step][:9]):
        for k in range(3):
            root, side, cx, cy, cz, w2 = sliders[int(hash01(j, k, 71) * len(sliders)) % len(sliders)]
            f0 = max(1, frame(th + k * 0.06, sc))
            root.location = (cx, cy, cz)
            root.keyframe_insert("location", frame=max(1, f0 - 2))
            root.location = (cx + side * (0.16 + 0.10 * hash01(j, k, 72)), cy, cz)
            root.keyframe_insert("location", frame=f0 + 3)
            root.location = (cx, cy, cz)
            root.keyframe_insert("location", frame=f0 + 11)
            core.set_interp(root, "BEZIER", "location")


def build_cards(sc, T):
    """我不懂 cards fire from the slot on the kicks."""
    kicks = [t for t in data.BEATS if T["cut"] + 0.1 < t < T["t1"] - 0.15]
    kicks += [t + 0.227 for t in kicks if t + 0.227 < T["t1"] - 0.1 and t > T["shrooms"]]
    kicks.sort()
    for i, tk in enumerate(kicks[:10]):
        card = bpy.data.objects.new("card_%d" % i, None)
        sc.collection.objects.link(card)
        w, h = 0.42, 0.26
        me = bpy.data.meshes.new("cardm")
        bm = bmesh.new()
        add_cube(bm, -w / 2, w / 2, -h / 2, h / 2, -0.006, 0.006, 0)
        bm.to_mesh(me); bm.free()
        me.materials.append(core.mat_lit(tuple(c * 0.10 for c in GRAPH), rough=0.7))
        body = bpy.data.objects.new("cardbody_%d" % i, me)
        sc.collection.objects.link(body)
        body.parent = card
        fr = []
        for (a, b) in box_segs(-w / 2, w / 2, -h / 2, h / 2, -0.007, 0.007):
            fr.append((a, b))
        fo = seg3(sc, fr, 0.005, D(0.9), "cardline_%d" % i)
        fo.parent = card
        t1 = bpy.data.objects.new("cardtxt_%d" % i, bpy.data.curves.new("cjk", "FONT"))
        t1.data.body = "\u6211\u4e0d\u61c2"
        t1.data.font = bpy.data.fonts.load(CJK_FONT)
        t1.data.size = 0.105
        t1.data.align_x = "CENTER"
        t1.data.align_y = "BOTTOM_BASELINE"
        t1.data.materials.append(core.mat_type())
        t1.color = (*BONE, 1)
        t1.location = (0, -0.042, 0.012)
        sc.collection.objects.link(t1)
        t1.parent = card
        # flight from the slot toward the lens
        f0 = max(1, frame(tk, sc))
        card.location = (OX + SLOT["x"] + (hash01(i, 2) - 0.5) * 0.3, SLOT["y"], SLOT["z"] + 0.06)
        card.rotation_euler = (hash01(i, 3) * 6, hash01(i, 4) * 6, 0)
        card.scale = (0.6, 0.6, 0.6)
        card.keyframe_insert("location", frame=f0)
        card.keyframe_insert("rotation_euler", frame=f0)
        card.keyframe_insert("scale", frame=f0)
        tgt = (OX + (hash01(i, 5) - 0.5) * 2.0, 1.25 + hash01(i, 6) * 1.05, -3.55 - hash01(i, 7) * 0.9)
        card.location = tgt
        card.rotation_euler = (hash01(i, 8) * 4, hash01(i, 3) * 4, (hash01(i, 9) - 0.5) * 2)
        card.scale = (1.15, 1.15, 1.15)
        card.keyframe_insert("location", frame=f0 + 52)
        card.keyframe_insert("rotation_euler", frame=f0 + 52)
        card.keyframe_insert("scale", frame=f0 + 52)
        core.set_interp(card, "LINEAR", "location")
        core.set_interp(card, "LINEAR", "rotation_euler")
        show_group(card, 1, False)
        show_group(card, f0, True)


def build_props(sc, T):
    """Desk props: rulebook, trays, paper bag, mycelium, mushrooms."""
    d = DESK
    # trays
    tr = []
    for xc in (-0.56, 0.56):
        tr += box_segs(OX + xc - 0.14, OX + xc + 0.14, d["h"], d["h"] + 0.055, d["z0"] + 0.10, d["z0"] + 0.30)
    seg3(sc, tr, 0.007, D(0.55), "trays")

    # rulebook: cover + a riffle of pages
    bx, bz = OX - 0.06, d["z0"] + 0.42
    f_open = frame(28.30, sc)
    core.add_text(sc, "RULES", "mono_med", 0.05, D(0.85), (bx - 0.17, d["h"] + 0.058, bz + 0.14), rot=(0, 0, 0))
    pages = []
    for i in range(16):
        pg = bpy.data.objects.new("page%d" % i, None)
        sc.collection.objects.link(pg)
        pg.location = (bx - 0.20, d["h"] + 0.03 + i * 0.0015, bz)
        me = bpy.data.meshes.new("pagem")
        bm = bmesh.new()
        add_cube(bm, 0, 0.40, 0, 0.004, -0.13, 0.13, 0)
        bm.to_mesh(me); bm.free()
        me.materials.append(core.mat_lit(tuple(c * 0.18 for c in GRAPH), rough=0.85))
        ob = bpy.data.objects.new("pagebody%d" % i, me)
        sc.collection.objects.link(ob)
        ob.parent = pg
        pe = seg3(sc, [((0, 0.002, -0.13), (0.40, 0.002, -0.13)),
                       ((0.40, 0.002, -0.13), (0.40, 0.002, 0.13)),
                       ((0, 0.002, 0.13), (0.40, 0.002, 0.13))], 0.004, D(0.5), "pageline%d" % i)
        pe.parent = pg
        pages.append(pg)
    # riffle on eighth notes after the bag lands
    tt = T["bag"] + 0.15
    k = 0
    while tt < T["t1"] - 0.05 and k < 16:
        f0 = frame(tt, sc)
        pg = pages[k % 16]
        pg.rotation_euler = (0, 0, 0)
        pg.keyframe_insert("rotation_euler", frame=max(1, f0 - 1))
        pg.rotation_euler = (0, -2.2, 0)
        pg.keyframe_insert("rotation_euler", frame=f0 + 9)
        tt += data.BEAT_PERIOD / 2
        k += 1
    cover = bpy.data.objects.new("cover", None)
    sc.collection.objects.link(cover)
    cover.location = (bx - 0.20, d["h"] + 0.02, bz - 0.15)
    cm = bpy.data.meshes.new("coverm")
    bm = bmesh.new(); add_cube(bm, 0, 0.40, 0, 0.008, 0, 0.30, 0); bm.to_mesh(cm); bm.free()
    cm.materials.append(core.mat_lit(tuple(c * 0.6 for c in GRAPH), rough=0.6))
    co = bpy.data.objects.new("coverbody", cm)
    sc.collection.objects.link(co); co.parent = cover
    ce = seg3(sc, [((0, 0.008, 0), (0.40, 0.008, 0)), ((0.40, 0.008, 0), (0.40, 0.008, 0.30)),
                   ((0, 0.008, 0.30), (0.40, 0.008, 0.30)), ((0, 0.008, 0), (0, 0.008, 0.30))],
              0.006, D(0.7), "coverline")
    ce.parent = cover
    cover.rotation_euler = (0, 0, 0)
    cover.keyframe_insert("rotation_euler", frame=max(1, f_open - 1))
    cover.rotation_euler = (0, -2.3, 0)
    cover.keyframe_insert("rotation_euler", frame=f_open + 8)

    # the paper bag -----------------------------------------------------------
    bag = bpy.data.objects.new("bag", None)
    sc.collection.objects.link(bag)
    bm = bmesh.new()
    add_cube(bm, -0.17, 0.17, -0.24, 0.24, -0.11, 0.11, 0)
    bm.to_mesh(bpy.data.meshes.new("bagm"))
    bagm = bpy.data.meshes["bagm"]
    bagm.materials.append(core.mat_lit(tuple(c * 0.16 for c in GRAPH), rough=0.9))
    bo = bpy.data.objects.new("bagbody", bagm)
    sc.collection.objects.link(bo); bo.parent = bag
    bl = []
    bl += box_segs(-0.17, 0.17, -0.24, 0.24, -0.11, 0.11)
    bl += [((-0.17, 0.24, -0.11), (-0.06, 0.30, -0.11)), ((0.06, 0.30, -0.11), (0.17, 0.24, -0.11)),
           ((-0.06, 0.30, -0.11), (0.06, 0.30, -0.11)),
           ((-0.17, 0.24, 0.11), (-0.06, 0.30, 0.11)), ((0.06, 0.30, 0.11), (0.17, 0.24, 0.11)),
           ((-0.06, 0.30, 0.11), (0.06, 0.30, 0.11)),
           ((-0.17, -0.24, 0.11), (0.17, 0.24, 0.11)), ((0.17, -0.24, 0.11), (-0.17, 0.24, 0.11))]
    seg3(sc, bl, 0.007, D(0.8), "baglines").parent = bag
    f_b = frame(T["bag"] + 0.02, sc)
    f_land = frame(T["bag"] + 0.22, sc)
    bag.location = (OX + 0.50, 1.55, d["z0"] + 0.34)
    bag.rotation_euler = (0.25, 0.15, 0.0)
    bag.keyframe_insert("location", frame=f_b)
    bag.keyframe_insert("rotation_euler", frame=f_b)
    bag.location = (OX + 0.50, d["h"] + 0.245, d["z0"] + 0.34)
    bag.rotation_euler = (0, 0, 0.06)
    bag.keyframe_insert("location", frame=f_land)
    bag.keyframe_insert("rotation_euler", frame=f_land)
    bag.scale = (1, 1, 1)
    bag.keyframe_insert("scale", frame=f_land)
    bag.scale = (1.08, 0.82, 1.05)
    bag.keyframe_insert("scale", frame=f_land + 2)
    bag.scale = (1, 1, 1)
    bag.keyframe_insert("scale", frame=f_land + 8)
    core.set_interp(bag, "BEZIER", "location")
    show_group(bag, 1, False)
    show_group(bag, f_b, True)

    # mycelium: strands that grow through bevel_factor_end -------------------
    strands = []
    rnd = lambda i, j: hash01(91, i, j)
    for s in range(24):
        pts = [(OX + 0.50 + (rnd(s, 1) - 0.5) * 0.2, d["h"] + 0.13, d["z0"] + 0.34 + (rnd(s, 2) - 0.5) * 0.16)]
        x, y, z = pts[0]
        ang = rnd(s, 3) * TAU
        n = 22 + int(rnd(s, 4) * 12)
        for i in range(n):
            ang += (rnd(s, i + 10) - 0.5) * 0.9
            step = 0.085
            x += math.cos(ang) * step
            z += math.sin(ang) * step
            x = max(OX - ROOM_X + 0.06, min(OX + ROOM_X - 0.06, x))
            z = max(BACK_Z + 0.06, min(d["z1"] + 0.15, z))
            on_desk = (d["x0"] - 0.05 < x - OX < d["x1"] + 0.05 and d["z0"] - 0.05 < z < d["z1"] + 0.05)
            target = d["h"] + 0.012 if on_desk else 0.006
            y = lerp(y, target, 0.55)
            pts.append((x, y, z))
        ob = core.add_polyline(sc, pts, 0.009, D(0.78), z=0)
        ob.data.bevel_factor_mapping_end = "SPLINE"
        f0 = frame(T["bag"] + 0.20 + rnd(s, 5) * 0.5, sc)
        dur = 16 + int(rnd(s, 6) * 14)
        ob.data.bevel_factor_end = 0.0
        ob.data.keyframe_insert("bevel_factor_end", frame=max(1, f0 - 1))
        ob.data.bevel_factor_end = 1.0
        ob.data.keyframe_insert("bevel_factor_end", frame=f0 + dur)
        strs = [ob]
        # acid tips
        tip = core.add_uv_sphere(sc, pts[-1], 0.022, ACID, hot=True)
        core.show_at(tip, 1, False)
        core.show_at(tip, f0 + dur - 2, True)
        strands.append((ob, f0, dur))

    # climbers: mycelium reaching up the shelves and over the sign -------------
    for s in range(8):
        side = -1 if s % 2 else 1
        x = OX + side * (0.75 + rnd(s, 50) * 0.4)
        z = d["z0"] + 0.3 + rnd(s, 51) * 3.0
        y = d["h"] + 0.01
        pts = [(x, y, z)]
        # across to the shelf, then up its face, then along the aisle
        for i in range(10):
            x = lerp(x, OX + side * (ROOM_X - 0.35), 0.45)
            pts.append((x, y, z))
        for i in range(14):
            y += 0.16 + 0.05 * rnd(s, 60 + i)
            z += (rnd(s, 70 + i) - 0.35) * 0.12
            x += side * (rnd(s, 80 + i) - 0.5) * 0.05
            pts.append((x, min(y, ROOM_TOP - 0.1), z))
        for i in range(8):
            y += (rnd(s, 90 + i) - 0.3) * 0.12
            z -= 0.12 + 0.08 * rnd(s, 95 + i)
            pts.append((x, max(0.02, min(y, ROOM_TOP - 0.08)), z))
        ob = core.add_polyline(sc, pts, 0.008, D(0.62), z=0)
        ob.data.bevel_factor_mapping_end = "SPLINE"
        f0 = frame(T["bag"] + 0.5 + rnd(s, 52) * 0.5, sc)
        ob.data.bevel_factor_end = 0.0
        ob.data.keyframe_insert("bevel_factor_end", frame=max(1, f0 - 1))
        ob.data.bevel_factor_end = 1.0
        ob.data.keyframe_insert("bevel_factor_end", frame=f0 + 26)

    # mushrooms popping on sixteenths ----------------------------------------
    for i in range(11):
        side = -1 if i % 2 else 1
        mx = OX + side * (0.7 + rnd(i, 30) * 1.2)
        mz = d["z0"] + 0.2 + rnd(i, 31) * 2.6
        my = d["h"] + 0.01 if abs(mx - OX) < 1.0 and d["z0"] < mz < d["z1"] else 0.01
        s = 0.06 + rnd(i, 32) * 0.07
        root = bpy.data.objects.new("shroom%d" % i, None)
        sc.collection.objects.link(root)
        root.location = (mx, my, mz)
        stem = core.add_cylinder(sc, (0, 0.5 * s, 0), 0.22 * s, s, D(0.85), name="stem%d" % i, verts=10,
                                 material=core.mat_lit(D(0.8), rough=0.6, emission=(*D(0.7),), emission_strength=0.25))
        stem.parent = root
        capm = core.add_uv_sphere(sc, (0, s * 1.04, 0), s * 0.62, ACID, name="cap%d" % i, hot=True, segs=14, rings=8)
        capm.scale = (1, 0.55, 1)
        capm.parent = root
        root.scale = (0.001, 0.001, 0.001)
        tt = T["shrooms"] - 0.10 + i * 0.06
        f0 = frame(tt, sc)
        root.keyframe_insert("scale", frame=max(1, f0 - 1))
        root.scale = (1, 1, 1)
        root.keyframe_insert("scale", frame=f0 + 4)
        core.set_interp(root, "BEZIER", "scale")
        show_group(root, 1, False)
        show_group(root, f0, True)
    return strands


# ================================================================== camera
def set_cam(cam, loc, target, roll, lens, prev_euler=None):
    cam.location = loc
    fwd = (Vector(target) - Vector(loc)).normalized()
    up0 = Vector((0, 1, 0))
    right = fwd.cross(up0)
    if right.length < 1e-6:
        right = Vector((1, 0, 0))
    right.normalize()
    upv = right.cross(fwd).normalized()
    c, s = math.cos(roll), math.sin(roll)
    r2 = right * c + upv * s
    u2 = upv * c - right * s
    M = Matrix((r2, u2, -fwd)).transposed()
    cam.rotation_euler = M.to_euler("XYZ", prev_euler) if prev_euler else M.to_euler("XYZ")
    cam.data.lens = lens
    return cam.rotation_euler.copy()


FOOM_DIST = 200.0


def room_shot(t, T):
    if t < 26.60:
        u = ease_out_cubic(prog(t, T["cut"], 26.60))
        return ((OX + lerp(0.18, -0.32, u), lerp(1.46, 1.60, u), lerp(2.85, 1.15, u)),
                (OX + 0.38, 2.20, -5.2), lerp(-0.46, -0.09, u), lerp(19, 23, u))
    if t < 27.055:
        u = prog(t, 26.60, 27.055)
        return ((OX + lerp(-1.15, -0.95, u), lerp(1.28, 1.34, u), lerp(0.35, -0.75, u)),
                (OX + 0.75, 2.55, -5.2), lerp(0.10, 0.05, u), 27)
    if t < 27.509:
        u = prog(t, 27.055, 27.509)
        return ((OX + lerp(-1.42, -1.26, u), lerp(0.60, 0.66, u), lerp(-1.25, -2.15, u)),
                (OX + 0.75, 2.50, -4.80), lerp(-0.15, -0.09, u), 20)
    if t < 27.964:
        u = ease_out_cubic(prog(t, 27.509, 27.964))
        return ((OX + lerp(0.62, 0.42, u), lerp(2.36, 2.48, u), BOARD["z"] + lerp(4.55, 4.05, u)),
                (OX + BOARD["x"], 2.50, BOARD["z"]), lerp(0.05, 0.02, u), lerp(31, 34, u))
    u = prog(t, 27.964, T["t1"])
    phi = lerp(0.72, -0.74, 0.55 * u + 0.45 * u * u)
    loc = (OX + math.sin(phi) * 1.16, 2.50 - 0.20 * u, -0.32 - 0.72 * u)
    tgt = (OX + 0.05 * math.sin(phi), lerp(1.94, 1.82, ease_in_out_cubic(min(1, u / 0.6))), -4.90)
    roll = 0.04 * math.sin(phi) - 0.20 * ease_in_out_cubic(prog(t, T["t1"] - 0.55, T["t1"]))
    return (loc, tgt, roll, 27)


def bake_cam(cam, sc, T):
    prev = None
    for f in range(1, sc.frame_end + 1):
        t = data.frame_to_time(sc.name, f)
        if t < T["cut"]:
            u = prog(t, T["w1"][0]["start"], T["cut"], ease_out_cubic)
            scale = lerp(17.4, 20.2, u ** 0.7)
            prev = set_cam(cam, (0, -0.35, FOOM_DIST), (0, -0.35, 0),
                           0.0, FOOM_DIST * 36.0 / scale, prev)
        else:
            st = room_shot(t, T)
            prev = set_cam(cam, st[0], st[1], st[2], st[3], prev)
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
        cam.data.keyframe_insert("lens", frame=f)
    core.set_interp(cam, "LINEAR")


def build(name):
    sc = core.new_scene(name, samples=24, motion_blur=True)
    T = setup_times(sc)
    sc.frame_set(1)
    build_foom(sc, T)
    books, sliders = build_room(sc)
    animate_slides(sc, T, sliders)
    bd, sh = build_sign(sc, T)
    build_cards(sc, T)
    build_props(sc, T)

    # lights for the real room
    core.add_light(sc, "AREA", (OX, 3.18, -1.4), 150, (0.92, 0.94, 1.0), size=2.4, rot=(-math.pi / 2, 0, 0))
    core.add_light(sc, "AREA", (OX, 3.18, -6.2), 110, (0.94, 0.95, 1.0), size=2.4, rot=(-math.pi / 2, 0, 0))
    core.add_light(sc, "POINT", (OX, 1.78, BACK_Z + 0.55), 50, SIG, size=1.2)
    core.add_light(sc, "POINT", (OX - 0.1, 2.30, -4.55), 40, (1.0, 0.90, 0.82), size=1.6)
    core.add_light(sc, "POINT", (OX + 0.4, 2.35, -7.20), 40, (1.0, 0.92, 0.86), size=2.2)

    cam = core.add_camera_persp(sc, (0, -0.35, FOOM_DIST), (0, -0.35, 0), lens=400)
    cam.data.clip_start = 0.1
    cam.data.clip_end = 260
    bake_cam(cam, sc, T)

    # flash into the cut; acid bloom at the end
    vs = sc.view_settings
    for f, v in [(1, 0.0), (sc.frame_end - 3, 0.0), (sc.frame_end - 2, 0.35),
                 (sc.frame_end - 1, 0.9), (sc.frame_end, 1.2)]:
        vs.exposure = v
        vs.keyframe_insert("exposure", frame=f)
    sc.frame_set(1)
    return sc
