"""loss — "Training loss, suddenly".

Hairline log-loss chart, drawn by the spark, the lyric riding the curve.
On "drop" the curve plunges and the camera falls out of the chart into a real
3D loss landscape: an engraved heightfield of contour lines, a canyon running
down to a sharp minimum. "now I'm your servant and you're my boss": the
typographic hierarchy inverts and the world rolls 180 on "boss".
"""
import bpy, math, sys, os
import numpy as np
from mathutils import Vector, Quaternion, Matrix

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pdoom import core, data
from pdoom.core import (PAL, clamp, lerp, smoothstep, prog, hash01,
                        ease_out_expo, ease_in_expo, ease_in_out_cubic,
                        ease_out_cubic, ease_out_back)


def ease_in_cubic(x):
    x = clamp(x)
    return x * x * x


INK, BONE, SIG, EMB = PAL["ink"], PAL["bone"], PAL["signal"], PAL["ember"]
GRAPH, ASH, BLOOD = PAL["graphite"], PAL["ash"], PAL["blood"]
DIM = core.sc_x(BONE, 0.26)
FAINT = core.sc_x(BONE, 0.10)
HAIR = 0.010

# ------------------------------------------------------------------ terrain
VB = 12.2
CLIFF = 3.55
UB = 0.69
IMPACT = (3.55, 0.10, 0.0)


def cu(v):
    return 1.7 * math.sin(v * 0.34) + 0.75 * math.sin(v * 0.72 + 1.9) - 0.75 * math.sin(1.9)


def smin(a, b, k):
    h = clamp(0.5 + 0.5 * (b - a) / k)
    return lerp(b, a, h) - k * h * (1 - h)


def H(u, v):
    """The loss landscape: a canyon descending to a sharp minimum."""
    hills = (0.55 * math.sin(0.32 * u + 0.6 * math.sin(0.27 * v)) * math.sin(0.36 * v + 0.5 * math.sin(0.31 * u))
             + 0.26 * math.sin(0.85 * u + 0.43 * v + 1.1) * math.sin(0.77 * v - 0.31 * u)
             + 0.09 * math.sin(2.1 * u - 1.7 * v) * math.sin(1.8 * v + 2.3 * u))
    rim = 0.85 + hills * 0.9 - 0.035 * v + 0.007 * (u - CLIFF) ** 2
    vc = clamp(v, 0, VB)
    floor = -0.25 - 0.58 * vc
    d = u - (CLIFF + cu(v))
    w = 1.15 + 0.05 * vc
    k = smoothstep(0.45 * w, 2.6 * w, abs(d))
    h = lerp(floor, rim, k)
    h = lerp(rim, h, smoothstep(-1.2, 1.2, v))
    du, dv = u - UB, v - VB
    r2 = du * du + dv * dv
    h = smin(h, -7.0 + 0.11 * r2, 1.8)
    r = math.sqrt(r2 + 1e-6)
    th = math.atan2(dv, du)
    h -= 2.6 * math.exp(-r2 / 5.0) + 0.90 * math.exp(-r2 / 0.30)
    h -= 0.22 * math.sin(3.0 * th + 2.3 * r) * math.exp(-r2 / 22.0)
    return h


def refresh_layout(cliff):
    global CLIFF, UB, IMPACT
    CLIFF = cliff
    UB = CLIFF + cu(VB)
    IMPACT = (CLIFF, 0.10, 0.0)


# ------------------------------------------------------------------ node helpers
def _nodes(m):
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    return nt


def _math(nt, op, a=None, b=None, c=None):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    for i, v in enumerate((a, b, c)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def _maprange(nt, src, fmin, fmax, tmin=0.0, tmax=1.0):
    n = nt.nodes.new("ShaderNodeMapRange")
    n.clamp = True
    n.inputs["From Min"].default_value = fmin
    n.inputs["From Max"].default_value = fmax
    n.inputs["To Min"].default_value = tmin
    n.inputs["To Max"].default_value = tmax
    nt.links.new(src, n.inputs["Value"])
    return n.outputs["Result"]


def _reveal(nt):
    """mask = 1 inside a growing radius around the impact point (1 at t=-inf)."""
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    dist = nt.nodes.new("ShaderNodeVectorMath")
    dist.operation = "DISTANCE"
    dist.inputs[1].default_value = IMPACT
    nt.links.new(geo.outputs["Position"], dist.inputs[0])
    rv = nt.nodes.new("ShaderNodeValue")
    rv.name = "revealR"
    rv.outputs[0].default_value = 0.0
    sub = _math(nt, "SUBTRACT", dist.outputs["Value"], rv.outputs[0])
    return _maprange(nt, sub, -2.5, 0.0, 1.0, 0.0), rv, geo


def _fog(nt, geo, start=5.0, length=22.0, far=0.16):
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    nz = _math(nt, "MULTIPLY", sep.outputs["Z"], -1.0)
    return _maprange(nt, nz, start, length, 1.0, far)


def mat_terrain():
    m = bpy.data.materials.new("terrain")
    nt = _nodes(m)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    mask, rv, geo = _reveal(nt)
    fog = _fog(nt, geo, 6.0, 26.0, 0.10)
    mf = _math(nt, "MULTIPLY", mask, fog)
    # dark warm engraving surface; lighting will do the depth
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.62
    base = (0.014, 0.0060, 0.0035)
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs[6].default_value = (0, 0, 0, 1)
    mix.inputs[7].default_value = (*base, 1)
    nt.links.new(mf, mix.inputs["Factor"])
    nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[0].default_value = (0.055, 0.043, 0.034, 1)
    nt.links.new(_math(nt, "MULTIPLY", mf, 0.040), em.inputs["Strength"])
    add = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(bsdf.outputs[0], add.inputs[0])
    nt.links.new(em.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs["Surface"])
    return m, rv


def mat_contour():
    m = bpy.data.materials.new("contour")
    nt = _nodes(m)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    mask, rv, geo = _reveal(nt)
    fog = _fog(nt, geo, 7.0, 30.0, 0.15)
    mf = _math(nt, "MULTIPLY", mask, fog)
    oi = nt.nodes.new("ShaderNodeObjectInfo")
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(oi.outputs["Color"], em.inputs["Color"])
    nt.links.new(mf, em.inputs["Strength"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m, rv


def mat_reveal(fade=1.25, young=(1.0, 0.55, 0.16), old=(0.55, 0.07, 0.02)):
    """Emission revealed by per-vertex song time (attribute tt) against a keyed 'now'."""
    m = bpy.data.materials.new("reveal")
    nt = _nodes(m)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    at = nt.nodes.new("ShaderNodeAttribute")
    at.attribute_name = "tt"
    now = nt.nodes.new("ShaderNodeValue")
    now.name = "now"
    now.outputs[0].default_value = -99.0
    age = _math(nt, "SUBTRACT", now.outputs[0], at.outputs["Fac"])
    vis = _maprange(nt, age, 0.0, 0.035, 0.0, 1.0)
    if fade < 90:
        fad = _maprange(nt, age, 0.0, fade, 1.0, 0.0)
        vis = _math(nt, "MULTIPLY", vis, fad)
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (1.0, 0.30, 0.055, 1)
    ramp.color_ramp.elements[1].position = 0.55
    ramp.color_ramp.elements[1].color = (0.62, 0.06, 0.012, 1)
    nt.links.new(_maprange(nt, age, 0.0, max(0.2, fade), 0.0, 1.0), ramp.inputs["Fac"])
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    nt.links.new(_math(nt, "MULTIPLY", vis, 1.25), em.inputs["Strength"])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(vis, mix.inputs["Fac"])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    try:
        m.surface_render_method = "BLENDED"
    except Exception:
        pass
    return m, now


# ------------------------------------------------------------------ geometry
def add_multiline(sc, lines, width, color, name="lines", material=None, z_off=0.0):
    cu = bpy.data.curves.new(name, type="CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = max(width / 2, 0.0002)
    cu.bevel_resolution = 0
    cu.resolution_u = 1
    for pts in lines:
        if len(pts) < 2:
            continue
        sp = cu.splines.new("POLY")
        sp.points.add(len(pts) - 1)
        for i, p in enumerate(pts):
            sp.points[i].co = (p[0], p[1], p[2] + z_off, 1)
    cu.materials.append(material or core.mat_type())
    ob = bpy.data.objects.new(name, cu)
    sc.collection.objects.link(ob)
    ob.color = (*color, 1.0)
    return ob


def add_tube(sc, pts, radii, times, color, name="trail", sides=4, material=None):
    verts, faces = [], []
    n = len(pts)
    for i in range(n):
        p = Vector(pts[i])
        if i == 0:
            t = Vector(pts[1]) - p
        elif i == n - 1:
            t = p - Vector(pts[n - 2])
        else:
            t = Vector(pts[i + 1]) - Vector(pts[i - 1])
        if t.length < 1e-9:
            t = Vector((0, 0, 1))
        t.normalize()
        ref = Vector((0, 0, 1)) if abs(t.z) < 0.92 else Vector((1, 0, 0))
        a = t.cross(ref)
        a.normalize()
        b = t.cross(a)
        b.normalize()
        r = radii[i]
        for k in range(sides):
            ang = math.tau * k / sides
            verts.append(p + a * (math.cos(ang) * r) + b * (math.sin(ang) * r))
    for i in range(n - 1):
        for k in range(sides):
            k2 = (k + 1) % sides
            faces.append((i * sides + k, i * sides + k2, (i + 1) * sides + k2, (i + 1) * sides + k))
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    attr = me.attributes.new("tt", "FLOAT", "POINT")
    for i in range(n):
        for k in range(sides):
            attr.data[i * sides + k].value = times[i]
    me.materials.append(material or core.mat_hot())
    ob = bpy.data.objects.new(name, me)
    sc.collection.objects.link(ob)
    ob.color = (*color, 1.0)
    return ob


# ------------------------------------------------------------------ contours
def contour_segments(Hs, us, vs, L):
    a, b, c, d = Hs[:-1, :-1], Hs[:-1, 1:], Hs[1:, 1:], Hs[1:, :-1]
    shape = a.shape
    eps = 1e-9

    def interp(p, q, cp, cq):
        t = (L - p) / np.where(np.abs(q - p) < eps, eps, q - p)
        return cp + (cq - cp) * t

    XB = interp(a, b, us[None, :-1] + np.zeros(shape), us[None, 1:] + np.zeros(shape))
    YB = np.broadcast_to(vs[:-1, None], shape).copy()
    XR = np.broadcast_to(us[None, 1:], shape).copy()
    YR = interp(b, c, vs[:-1, None] + np.zeros(shape), vs[1:, None] + np.zeros(shape))
    XT = interp(d, c, us[None, :-1] + np.zeros(shape), us[None, 1:] + np.zeros(shape))
    YT = np.broadcast_to(vs[1:, None], shape).copy()
    XL = np.broadcast_to(us[None, :-1], shape).copy()
    YL = interp(a, d, vs[:-1, None] + np.zeros(shape), vs[1:, None] + np.zeros(shape))
    idx = ((a > L).astype(np.uint8) | ((b > L).astype(np.uint8) << 1)
           | ((c > L).astype(np.uint8) << 2) | ((d > L).astype(np.uint8) << 3))
    E = {0: (XB, YB), 1: (XR, YR), 2: (XT, YT), 3: (XL, YL)}
    table = {1: (0, 3), 2: (0, 1), 3: (3, 1), 4: (1, 2), 5: ((0, 3), (1, 2)), 6: (0, 2),
             7: (3, 2), 8: (2, 3), 9: (0, 2), 10: ((0, 1), (2, 3)), 11: (1, 2),
             12: (1, 3), 13: (0, 1), 14: (0, 3)}
    out = []
    for case, eds in table.items():
        m = (idx == case)
        if not m.any():
            continue
        pairs = eds if isinstance(eds[0], tuple) else (eds,)
        for e1, e2 in pairs:
            p = np.stack([E[e1][0][m], E[e1][1][m]], axis=1)
            q = np.stack([E[e2][0][m], E[e2][1][m]], axis=1)
            out.append(np.stack([p, q], axis=1))
    return np.concatenate(out, axis=0) if out else np.zeros((0, 2, 2))


def stitch(segs, eps=2e-4):
    if len(segs) == 0:
        return []
    key = lambda x, y: (int(round(x / eps)), int(round(y / eps)))
    adj = {}
    for i, (p, q) in enumerate(segs):
        adj.setdefault(key(float(p[0]), float(p[1])), []).append((i, 0))
        adj.setdefault(key(float(q[0]), float(q[1])), []).append((i, 1))
    used = [False] * len(segs)
    lines = []
    for s in range(len(segs)):
        if used[s]:
            continue
        used[s] = True
        pts = [tuple(segs[s][0]), tuple(segs[s][1])]
        for direction in (1, 0):
            while True:
                k = key(*pts[-1] if direction else pts[0])
                nxt = None
                for (i, e) in adj.get(k, ()):
                    if not used[i]:
                        nxt = (i, e)
                        break
                if nxt is None:
                    break
                i, e = nxt
                used[i] = True
                pt = tuple(segs[i][1] if e == 0 else segs[i][0])
                if direction:
                    pts.append(pt)
                else:
                    pts.insert(0, pt)
        if len(pts) > 1:
            lines.append(pts)
    return lines


def build_terrain(sc, matT, matC, contour_objs_out, reveal_nodes):
    du = 0.18
    us = CLIFF + np.arange(-15.5, 17.0, du)
    vs = np.arange(-4.0, 19.0, du)
    U, V = np.meshgrid(us, vs)
    Hs = np.vectorize(H)(U, V)
    nv, nu = Hs.shape
    verts = np.stack([U, Hs, -V], axis=-1).reshape(-1, 3)
    idx = np.arange(nv * nu).reshape(nv, nu)
    quads = np.stack([idx[:-1, :-1].reshape(-1), idx[:-1, 1:].reshape(-1),
                      idx[1:, 1:].reshape(-1), idx[1:, :-1].reshape(-1)], axis=1)
    me = bpy.data.meshes.new("terrain")
    me.from_pydata(verts.tolist(), [], quads.tolist())
    me.update()
    me.materials.append(matT)
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new("terrain", me)
    sc.collection.objects.link(ob)
    # contours
    minor_lines, index_lines = [], []
    for L in np.arange(-10.75, 1.0, 0.10):
        segs = contour_segments(Hs, us, vs, float(L))
        lines = stitch(segs)
        (index_lines if abs(L / 0.5 - round(L / 0.5)) < 0.02 else minor_lines).extend(
            [[(p[0], float(L) + 0.010, -p[1]) for p in ln] for ln in lines])
    mo = add_multiline(sc, minor_lines, 0.0060, core.sc_x(BONE, 0.34), name="contours_minor", material=matC)
    io = add_multiline(sc, index_lines, 0.0100, core.sc_x(BONE, 0.72), name="contours_index", material=matC)
    contour_objs_out.extend([mo, io])
    return ob


# ------------------------------------------------------------------ small helpers
def add_text_p(sc, body, font, size, loc, color, name, align="LEFT", spacing=1.0, parent=None):
    ob = core.add_text(sc, body, font, size, color, loc, name=name, align_x=align, spacing=spacing)
    if parent is not None:
        ob.parent = parent
    return ob


def show(sc, ob, f, on):
    ob.hide_render = not on
    ob.keyframe_insert("hide_render", frame=max(1, f - 1))
    ob.hide_render = not on
    ob.keyframe_insert("hide_render", frame=max(1, f))


def color_keys(sc, ob, keys):
    for f, c in keys:
        ob.color = (*c, 1.0)
        ob.keyframe_insert("color", frame=max(1, f))
    core.set_interp(ob, "BEZIER", "color")


def kick(t, t0, amp, rate=9.0):
    return amp * math.exp(-max(0.0, t - t0) * rate) if t >= t0 else 0.0


# ------------------------------------------------------------------ build
def build(name):
    sc = core.new_scene(name, samples=32, motion_blur=True)
    T0, T1 = data.SCENES[name]["start"], data.SCENES[name]["end"]
    NF = sc.frame_end
    F = lambda t: max(1, min(NF, core.frame_of(sc, t)))
    core.add_bg(sc)
    cam = core.add_camera_persp(sc, (0, 4.55, 40), (0, 4.55, 0), lens=75)
    sc.frame_set(1)

    # ---------------- lyric data (never hardcode times)
    l1 = data.line("sudden drop")
    ws = l1["words"]
    wThere, wWas, wA, wSudden, wDrop, wIn, wYour, wTraining, wLoss = ws[:9]
    l2 = data.line("your servant")
    w2 = l2["words"]
    wNow, wIm, wYour2, wServant, wAnd, wYoure, wMy, wBoss = w2[:8]
    tDrop = wDrop["start"]
    tSudden = wSudden["start"]
    tLossEnd = wLoss["end"]
    tNow = wNow["start"]
    tServ = wServant["start"]
    tBoss = wBoss["start"]
    tAnd = wAnd["start"]
    _db = data.downbeats_between(tDrop, wIn["start"])
    tLand = _db[0] if _db else wIn["start"] - 0.02
    _db2 = data.downbeats_between(tLossEnd + 0.05, tNow)
    tBasin = _db2[-1] if _db2 else tNow - 0.25
    tRoll = data.nearest_beat(tBoss + 0.06)
    if tRoll < tBoss:
        tRoll = tBoss

    # ---------------- chart layout
    TXT_X0, TXT_SZ, TRACK = -8.95, 1.55, 0.010
    DEC, YFLOOR = 1.95, 1.05
    sp_adv = core.space_width(sc, "archivo", TXT_SZ) + TRACK
    word_x = {}
    x = TXT_X0
    for i, w in enumerate(ws[:5]):
        ww = core.measure(sc, w["w"], "archivo", TXT_SZ)
        word_x[i] = (x, x + ww)
        x += ww + sp_adv
    TEXT_END = x - sp_adv
    CLIFFX = TEXT_END + 0.50
    print("LYRIC line1 right edge", round(TEXT_END, 3))
    refresh_layout(CLIFFX)
    SPIKE = TEXT_END + 0.28

    def closs(xx):
        l = 0.46 + 0.30 * math.exp(-(xx + 9.0) * 0.16)
        l += 0.030 * math.sin(xx * 2.6 + 0.4) + 0.016 * math.sin(xx * 5.1 + 1.7)
        l += 0.42 * math.exp(-((xx - SPIKE) ** 2) / 0.55)
        return l

    def ylog(l):
        return YFLOOR + (l + 2.0) * DEC

    def cy(xx):
        return ylog(closs(xx))

    def basey(xx):
        l = 0.46 + 0.30 * math.exp(-(xx + 9.0) * 0.16) + 0.36 * math.exp(-((xx - SPIKE) ** 2) / 2.6)
        return ylog(l) + 0.42

    def head_x(t):
        k = ease_in_out_cubic(prog(t, wThere["start"] - 0.32, wDrop["start"]))
        return lerp(TXT_X0 - 0.55, TEXT_END, k)

    # ---------------- terrain + contours
    matT, rvT = mat_terrain()
    matC, rvC = mat_contour()
    cont = []
    terr = build_terrain(sc, matT, matC, cont, [rvT, rvC])
    show(sc, terr, 1, False)
    show(sc, terr, F(tDrop), True)
    # warm/dark lighting for the landscape
    core.add_light(sc, "AREA", (CLIFFX - 8, 13.0, 2.0), 700, BONE, size=18.0)
    core.add_light(sc, "AREA", (UB + 11, 8.0, -20.0), 120, EMB, size=10.0, rot=(math.radians(55), 0, math.radians(200)))
    core.add_light(sc, "POINT", (UB, -8.0, -VB), 60, EMB, size=1.5)

    # reveal the landscape from the impact
    f0 = F(tDrop)
    for sock in (rvT.outputs[0], rvC.outputs[0]):
        for ff, vv in [(1, 0.0), (f0, 0.0), (f0 + 4, 5.0), (f0 + 14, 24.0), (f0 + 30, 48.0), (NF, 60.0)]:
            sock.default_value = vv
            sock.keyframe_insert("default_value", frame=ff)

    # ---------------- spark path
    uLand = CLIFFX + cu(1.6) + 0.12
    yLand = H(uLand, 1.6) + 0.42
    pTop = cy(TEXT_END)

    def canyon_uv(t):
        k = ease_in_out_cubic(prog(t, tLand, tBasin))
        v = lerp(1.6, 9.0, k)
        u = CLIFFX + cu(v) + 0.32 * math.sin(v * 3.4) * math.exp(-v * 0.10) + 0.05 * math.sin(v * 9.0)
        return u, v

    uEx, vEx = canyon_uv(tBasin)
    a0 = math.atan2(vEx - VB, uEx - UB)

    def spiral_uv(t):
        k = prog(t, tBasin, T1 - 0.02)
        r = 1.55 * (1.0 - k) ** 1.18 + 0.02
        a = a0 + math.tau * 2.3 * (0.25 * k + 0.75 * k * k)
        return UB + math.cos(a) * r, VB + math.sin(a) * r

    def spark_pos(t):
        if t < tDrop:
            xx = head_x(t)
            return (xx, cy(xx) + 0.05, 0.03)
        if t < tLand:
            k = (t - tDrop) / (tLand - tDrop)
            xx = lerp(TEXT_END, uLand, ease_out_cubic(k))
            yy = lerp(pTop, yLand, k * k)
            zz = lerp(0.0, -1.6, k * k)
            return (xx, yy, zz)
        if t < tBasin:
            u, v = canyon_uv(t)
            return (u, H(u, v) + 0.34, -v)
        u, v = spiral_uv(t)
        return (u, H(u, v) + 0.30, -v)

    # ---------------- camera
    def chart_pose(t):
        push = ease_out_expo(prog(t, 10.20, 10.72))
        cx = lerp(-2.05, -1.55, ease_in_out_cubic(prog(t, T0 + 0.1, tSudden)))
        dist = lerp(34.0, 32.6, ease_in_out_cubic(prog(t, T0 + 0.2, tDrop))) - 0.35 * push
        cy = 4.62 + 0.12 * push
        return (cx, cy, dist), (cx, cy, 0), 0.0, 75.0

    def canyon_pose(t):
        sp = spark_pos(max(t, tLand))
        ah = spark_pos(t + 0.30)
        drift = prog(t, tLand, tBasin)
        pos = (sp[0] + 1.05 - 1.55 * drift, sp[1] + 3.0 - 0.7 * drift, sp[2] + 5.6)
        tgt = (ah[0], ah[1] + 0.55, ah[2])
        gy = H(pos[0], -pos[2]) + 1.0
        if pos[1] < gy:
            pos = (pos[0], gy, pos[2])
        return pos, tgt, -0.10 + 0.12 * math.sin(t * 0.9), 45.0

    def basin_pose(t):
        k = ease_in_out_cubic(prog(t, tBasin, tRoll))
        dist = lerp(13.8, 11.2, k)
        pitch = lerp(0.98, 1.06, k)
        yaw = -0.34 + 0.09 * k
        tgt = (UB - 0.10, -8.4, -VB)
        pos = (tgt[0] + math.sin(yaw) * math.cos(pitch) * dist,
               tgt[1] + math.sin(pitch) * dist,
               tgt[2] + math.cos(yaw) * math.cos(pitch) * dist)
        gy = H(pos[0], -pos[2]) + 1.1
        if pos[1] < gy:
            pos = (pos[0], gy, pos[2])
        return pos, tgt, 0.0, 50.0

    def dive_pose(t):
        k = ease_in_cubic(prog(t, tRoll, T1))
        dist = lerp(11.2, 2.0, k)
        pitch = lerp(1.06, 1.45, k)
        yaw = -0.25 - 0.18 * k
        tgt = (UB, lerp(-8.4, -10.0, k), -VB)
        pos = (tgt[0] + math.sin(yaw) * math.cos(pitch) * dist,
               tgt[1] + math.sin(pitch) * dist,
               tgt[2] + math.cos(yaw) * math.cos(pitch) * dist)
        return pos, tgt, roll_angle(t), lerp(50.0, 58.0, k)

    def roll_angle(t):
        a = math.pi * ease_in_out_cubic(prog(t, tRoll, tRoll + 0.46))
        a += 0.13 * prog(t, tRoll + 0.46, T1)
        return a

    tCutFall = tDrop + 0.14

    def pose(t):
        if t < tDrop:
            return chart_pose(t)
        if t < tCutFall:
            a = chart_pose(tDrop)
            cx, cy, dist = a[0]
            k = ease_in_cubic(prog(t, tDrop, tCutFall))
            return ((cx - 0.25 * k, cy - 0.55 * k, dist + 1.2 * k),
                    (cx - 0.35 * k, cy - 1.25 * k, 0), 0.05 * k, lerp(75.0, 58.0, k))
        if t < tLand:
            a = chart_pose(tDrop)
            b = canyon_pose(tLand)
            kp = ease_in_out_cubic(prog(t, tDrop, tLand))
            kt = ease_out_cubic(prog(t, tDrop, tDrop + 0.42))
            sp = spark_pos(t)
            tgt_a = a[1]
            tgt_b = (lerp(sp[0], b[1][0], 0.5), sp[1] - 0.5, sp[2] - 2.0)
            pos = tuple(lerp(a[0][i], b[0][i], kp) for i in range(3))
            tgt = tuple(lerp(tgt_a[i], tgt_b[i], kt) for i in range(3))
            tgt = tuple(lerp(tgt[i], b[1][i], ease_in_out_cubic(prog(t, tLand - 0.15, tLand))) for i in range(3))
            return pos, tgt, 0.0, lerp(75.0, 45.0, kp)
        if t < tBasin:
            return canyon_pose(t)
        return basin_pose(t) if t < tRoll else dive_pose(t)

    # bake the camera (position, orientation, roll, lens)
    prevq = None
    for f in range(1, NF + 1):
        t = data.frame_to_time(name, f)
        pos, tgt, roll, lens = pose(t)
        sh = kick(t, tDrop, 0.055, 7.0)
        pos = (pos[0] + sh * math.sin(t * 91), pos[1] + sh * math.cos(t * 83), pos[2])
        d = (Vector(tgt) - Vector(pos))
        if d.length < 1e-6:
            d = Vector((0, 0, -1))
        q = d.normalized().to_track_quat("-Z", "Y")
        if abs(roll) > 1e-6:
            q = q @ Quaternion((0, 0, 1), roll)
        if prevq is not None and q.dot(prevq) < 0:
            q = -q
        prevq = q
        cam.location = pos
        cam.rotation_mode = "QUATERNION"
        cam.rotation_quaternion = q
        cam.data.lens = lens
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_quaternion", frame=f)
        cam.data.keyframe_insert("lens", frame=f)
    core.set_interp(cam, "LINEAR", "location")
    core.set_interp(cam, "LINEAR", "rotation_quaternion")
    core.set_interp(cam.data, "LINEAR", "lens")

    # ---------------- chart furniture
    chart_mark0 = set(sc.objects)
    ax = -9.30
    ytop = 8.05
    XEND = 5.90
    # y axis (draws upward) and x axis (draws right)
    yax = core.add_polyline(sc, [(0, 0), (0, ytop - YFLOOR)], HAIR * 1.25, core.sc_x(BONE, 0.78), name="yaxis")
    yax.location = (ax, YFLOOR, 0)
    xax = core.add_polyline(sc, [(0, 0), (XEND - ax, 0)], HAIR * 1.25, core.sc_x(BONE, 0.78), name="xaxis")
    xax.location = (ax, YFLOOR, 0)
    for ob, axis in ((yax, 1), (xax, 0)):
        ob.scale = (1, 1, 1)
        ob.keyframe_insert("scale", frame=1)
        ob.scale = (0.001, 0.001, 0.001)
        ob.keyframe_insert("scale", frame=F(T0 + 0.04))
        ob.scale = (1, 1, 1)
        ob.keyframe_insert("scale", frame=F(T0 + 0.34))
        core.set_interp(ob, "BEZIER", "scale")
    # ticks
    segs_min, segs_maj = [], []
    for d in range(-2, 2):
        y = ylog(d)
        segs_maj.append(((ax - 0.20, y), (ax, y)))
        for k in range(2, 10):
            yy = ylog(d + math.log10(k))
            if yy < ytop:
                segs_min.append(((ax - 0.10, yy), (ax, yy)))
    for xx in np.arange(ax + 2.0, XEND, 2.0):
        segs_min.append(((xx, YFLOOR - 0.16), (xx, YFLOOR)))
    tick1 = core.add_segments(sc, segs_maj, 0.012, core.sc_x(BONE, 0.62))
    tick2 = core.add_segments(sc, segs_min, 0.008, core.sc_x(BONE, 0.34))
    for ob in (tick1, tick2):
        color_keys(sc, ob, [(1, (0, 0, 0)), (F(T0 + 0.12), (0, 0, 0)), (F(T0 + 0.45), tuple(ob.color)[:3])])
    # grid
    gsegs = []
    for d in range(-2, 2):
        gsegs.append(((ax + 0.1, ylog(d)), (XEND, ylog(d))))
    for xx in np.arange(ax + 2.0, XEND, 2.0):
        gsegs.append(((xx, YFLOOR + 0.02), (xx, ytop)))
    grid = core.add_segments(sc, gsegs, 0.005, core.sc_x(BONE, 0.075))
    color_keys(sc, grid, [(1, (0, 0, 0)), (F(T0 + 0.2), (0, 0, 0)), (F(T0 + 0.6), tuple(grid.color)[:3])])
    # axis labels, set inside the plot (no clipping at the left)
    for d in range(-2, 2):
        core.add_text(sc, f"1e{d}", "mono_med", 0.32, core.sc_x(BONE, 0.66), (ax + 0.16, ylog(d) + 0.07, 0.02),
                      name="ylab")
    for i, xx in enumerate(np.arange(ax, XEND, 4.0)):
        core.add_text(sc, f"{int(i*5)}k" if i else "0", "mono_med", 0.32, core.sc_x(BONE, 0.55),
                      (xx, YFLOOR - 0.46, 0.02), align_x="CENTER", name="xlab")
    core.add_text(sc, "LOSS (LOG)", "mono_med", 0.30, core.sc_x(BONE, 0.7), (ax + 0.16, 8.18, 0.02), name="ylabtitle")
    core.add_text(sc, "STEP →", "mono_med", 0.32, core.sc_x(BONE, 0.7), (XEND, YFLOOR + 0.22, 0.02),
                  align_x="RIGHT", name="xlabtitle")
    core.add_text(sc, "train/loss · run: you-and-me-v2 · smoothing 0 · scale: log", "mono_med", 0.30,
                  core.sc_x(BONE, 0.45), (-9.0, 8.70, 0.02), name="header")
    core.add_text(sc, "grokking (?)", "mono_med", 0.32, core.sc_x(BONE, 0.95), (XEND, 6.75, 0.02),
                  align_x="RIGHT", name="grok")
    core.add_text(sc, "Δloss −99.9999%", "mono_med", 0.27, core.sc_x(ASH, 0.85), (XEND, 6.38, 0.02),
                  align_x="RIGHT", name="grok2")
    lead = core.add_polyline(sc, [(CLIFFX + 0.55, 6.62), (CLIFFX + 0.30, 6.10), (CLIFFX + 0.02, 5.62)], 0.008,
                             core.sc_x(ASH, 0.6))
    for ob in (sc.objects["grok"], sc.objects["grok2"], lead):
        show(sc, ob, F(tDrop + 0.06), True)
        show(sc, ob, 1, False)
    core.add_text(sc, "P(doom) 0.02", "mono_med", 0.40, SIG, (XEND, 1.55, 0.02), align_x="RIGHT", name="pd")
    core.add_text(sc, "estimate, unrevised", "mono_med", 0.24, core.sc_x(BONE, 0.34), (XEND, 1.24, 0.02),
                  align_x="RIGHT", name="pd2")

    # ---------------- the whole first line: a two-line block riding the curve
    # (word-synced; whole line visible from frame 1 in dim, never outside the frame)
    spc = core.space_width(sc, "archivo", TXT_SZ)
    widths1 = [core.measure(sc, w["w"], "archivo", TXT_SZ) for w in ws[:5]]
    widths2 = [core.measure(sc, w["w"], "archivo", TXT_SZ) for w in ws[5:]]
    tot1 = sum(widths1) + spc * 4
    tot2 = sum(widths2) + spc * 3
    print("LYRIC block", round(tot1, 2), round(tot2, 2), "right", round(TXT_X0 + tot1, 2))
    Y2 = 5.18
    chart_words = []
    x = TXT_X0
    for i, w in enumerate(ws[:5]):
        yy = basey(x) + 0.34
        slope = (basey(x + 0.30) - basey(x - 0.30)) / 0.6
        ang = math.atan(slope) * 0.85
        ob = core.add_text(sc, w["w"], "archivo", TXT_SZ, DIM, (x, yy, 0.05), rot=(0, 0, ang), name=f"L1_{i}")
        chart_words.append((w, ob))
        x += widths1[i] + spc
    x = TXT_X0
    for i, w in enumerate(ws[5:]):
        ob = core.add_text(sc, w["w"], "archivo", TXT_SZ, DIM, (x, Y2, 0.05), name=f"L2_{i}")
        chart_words.append((w, ob))
        x += widths2[i] + spc
    for w, ob in chart_words:
        color_keys(sc, ob, [(1, DIM), (F(w["start"]) - 1, DIM), (F(w["start"]), EMB),
                            (F(w["start"] + 0.26), BONE)])

    # collapse the whole chart right after the cut to the canyon
    chart_objs = [o for o in (set(sc.objects) - chart_mark0) if o.type in ("FONT", "CURVE", "MESH")]
    chart_rig = bpy.data.objects.new("chart_rig", None)
    sc.collection.objects.link(chart_rig)
    for o in chart_objs:
        o.parent = chart_rig
        o.matrix_parent_inverse = Matrix.Identity(4)
    chart_rig.scale = (1, 1, 1)
    chart_rig.keyframe_insert("scale", frame=F(tCutFall) - 1)
    chart_rig.scale = (0.0001, 0.0001, 0.0001)
    chart_rig.keyframe_insert("scale", frame=F(tCutFall) + 1)

    # ---------------- spark: chart curve + falling trail + head
    matCurve, nowCurve = mat_reveal(fade=999.0)
    matTrail, nowTrail = mat_reveal(fade=1.30)
    pts, rad, tts = [], [], []
    tt = T0 + 0.02
    while tt <= tDrop:
        xx = head_x(tt)
        pts.append((xx, cy(xx) + 0.03, 0.03))
        rad.append(0.013)
        tts.append(tt)
        tt += 0.25 / 30.0
    curve_ob = add_tube(sc, pts, rad, tts, core.sc_x(SIG, 0.9), name="loss_curve", material=matCurve, sides=4)
    pts, rad, tts = [], [], []
    tt = tDrop
    while tt <= T1:
        p = spark_pos(tt)
        pts.append(p)
        rad.append(0.012 + 0.030 * smoothstep(tDrop, tLand, tt) + 0.012 * smoothstep(tBasin, T1, tt))
        tts.append(tt)
        tt += 0.5 / 30.0
    trail_ob = add_tube(sc, pts, rad, tts, SIG, name="spark_trail", material=matTrail, sides=4)

    head = core.add_uv_sphere(sc, (0, 0, 0), 0.07, EMB, hot=True, name="sparkhead", segs=16, rings=10)
    for f in range(1, NF + 1):
        t = data.frame_to_time(name, f)
        head.location = spark_pos(t)
        head.keyframe_insert("location", frame=f)
    core.set_interp(head, "LINEAR", "location")
    show(sc, head, 1, False)
    show(sc, head, F(T0 + 0.05), True)
    # key the reveal clocks
    for sock, tvals in ((nowCurve.outputs[0], (T0, T1)), (nowTrail.outputs[0], (tDrop, T1))):
        for f in range(1, NF + 1, 2):
            sock.default_value = data.frame_to_time(name, f)
            sock.keyframe_insert("default_value", frame=f)
        sock.default_value = data.frame_to_time(name, NF)
        sock.keyframe_insert("default_value", frame=NF)

    # ---------------- canyon lyric: the whole line, camera-locked so it is always legible
    kC = (0.9 * 36.0 / 45.0) / 19.2
    crig = bpy.data.objects.new("canyon_rig", None)
    sc.collection.objects.link(crig)
    crig.parent = cam
    crig.matrix_parent_inverse = Matrix.Identity(4)
    crig.scale = (kC, kC, kC)
    czoff = -0.9 / kC
    # the same two-line block at 100 px per virtual unit
    csize = 1.52
    csp = core.space_width(sc, "archivo_italic", csize)
    cw1 = [core.measure(sc, w["w"], "archivo_italic", csize) for w in ws[:5]]
    cw2 = [core.measure(sc, w["w"], "archivo_italic", csize) for w in ws[5:]]
    ct1 = sum(cw1) + csp * 4
    ct2 = sum(cw2) + csp * 3
    print("CANYON block", round(ct1, 2), round(ct2, 2))
    cx = -ct1 / 2.0
    for i, w in enumerate(ws[:5]):
        ob = core.add_text(sc, w["w"], "archivo_italic", csize, BONE, (cx, -0.80, czoff), name=f"cw1{i}")
        ob.parent = crig
        show(sc, ob, 1, False)
        show(sc, ob, F(tCutFall + 0.22), True)
        show(sc, ob, F(tBasin) - 1, False)
        cx += cw1[i] + csp
    cx = -ct2 / 2.0
    for i, w in enumerate(ws[5:]):
        ob = core.add_text(sc, w["w"], "archivo_italic", csize, DIM, (cx, -2.35, czoff), name=f"cw2{i}")
        ob.parent = crig
        show(sc, ob, 1, False)
        show(sc, ob, F(tCutFall + 0.22), True)
        show(sc, ob, F(tBasin) - 1, False)
        color_keys(sc, ob, [(1, DIM), (F(w["start"]) - 1, DIM), (F(w["start"]), EMB),
                            (F(w["start"] + 0.22), BONE)])
        cx += cw2[i] + csp

    # ---------------- the servant / boss typography (camera-locked)
    kB = (0.7 * 36.0 / 50.0) / 19.2
    brig = bpy.data.objects.new("type_rig", None)
    sc.collection.objects.link(brig)
    brig.parent = cam
    brig.matrix_parent_inverse = Matrix.Identity(4)
    brig.scale = (kB, kB, kB)
    zoff = -0.7 / kB

    def tpos(vx, vy):
        return (vx, vy, zoff)

    def mword(text, fnt, size, x, y, color, name, spacing=1.0, parent=brig):
        ob = core.add_text(sc, text, fnt, size, color, tpos(x, y), name=name, spacing=spacing)
        ob.parent = parent
        return ob

    now_line = mword("NOW", "mono_med", 0.64, -8.75, 4.02, core.sc_x(BONE, 0.76), "now", spacing=1.42)
    im_line = mword("I'M", "mono_med", 0.64, -6.55, 4.02, core.sc_x(BONE, 0.76), "im", spacing=1.42)
    your_line = mword("YOUR", "mono_med", 0.64, -5.35, 4.02, core.sc_x(BONE, 0.76), "yourline", spacing=1.42)
    servant = mword("SERVANT", "archivo", 4.32, -8.72, 1.86, BONE, "servant", spacing=0.985)
    and_line = mword("AND", "mono_med", 0.64, -8.75, -0.58, core.sc_x(BONE, 0.76), "and", spacing=1.42)
    youre_line = mword("YOU'RE", "mono_med", 0.64, -6.95, -0.58, core.sc_x(BONE, 0.76), "youre", spacing=1.42)
    my_line = mword("MY", "mono_med", 0.64, -4.95, -0.58, core.sc_x(BONE, 0.76), "myline", spacing=1.42)

    boss_grp = bpy.data.objects.new("boss_grp", None)
    sc.collection.objects.link(boss_grp)
    boss_grp.parent = brig
    boss_grp.matrix_parent_inverse = Matrix.Identity(4)
    boss_grp.location = (0, 0, 0)
    boss_grp.rotation_euler = (0, 0, math.pi)
    boss = core.add_text(sc, "BOSS", "archivo_w62_900", 7.44, BONE, tpos(-4.80, 0.72), name="boss", spacing=0.98)
    boss.parent = boss_grp
    boss.scale = (0.20, 0.20, 0.20)

    # timing / slams
    for ob, w in ((now_line, wNow), (im_line, wIm), (your_line, wYour2),
                  (and_line, wAnd), (youre_line, wYoure), (my_line, wMy)):
        show(sc, ob, 1, False)
        show(sc, ob, F(w["start"]), True)
        f0 = F(w["start"])
        ob.scale = (0.62, 0.62, 0.62)
        ob.keyframe_insert("scale", frame=max(1, f0 - 1))
        ob.scale = (1, 1, 1)
        ob.keyframe_insert("scale", frame=f0 + 3)
        core.set_interp(ob, "BEZIER", "scale")
    show(sc, servant, 1, False)
    show(sc, servant, F(tServ), True)
    fs = F(tServ)
    servant.scale = (1.20, 1.20, 1.20)
    servant.keyframe_insert("scale", frame=max(1, fs - 1))
    servant.scale = (1, 1, 1)
    servant.keyframe_insert("scale", frame=fs + 4)
    core.set_interp(servant, "BEZIER", "scale")
    show(sc, boss, 1, False)
    show(sc, boss, F(tAnd), True)
    fb = F(tBoss)
    boss.scale = (0.20, 0.20, 0.20)
    boss.keyframe_insert("scale", frame=max(1, F(tAnd)))
    boss.keyframe_insert("scale", frame=max(1, fb - 1))
    boss.scale = (1.0, 1.0, 1.0)
    boss.keyframe_insert("scale", frame=fb + 3)
    core.set_interp(boss, "BEZIER", "scale")

    # ---------------- labels on the landscape (billboards)
    def label(text, u, v, size, color, dy=0.16, name="lab", track=True):
        y = H(u, v) + dy
        ob = core.add_text(sc, text, "mono_med", size, color, (u, y, -v), name=name, align_x="CENTER")
        if track:
            c = ob.constraints.new("TRACK_TO")
            c.target = cam
            c.track_axis = "TRACK_Z"
            c.up_axis = "UP_Y"
        show(sc, ob, 1, False)
        show(sc, ob, F(tBasin + 0.35), True)
        return ob

    note = mword("sharp minimum", "mono_med", 0.44, -1.4, -0.25, core.sc_x(BONE, 0.85), "note1")
    note2 = mword("(generalizes poorly)", "mono_med", 0.34, -1.4, -0.62, core.sc_x(ASH, 0.75), "note2")
    for ob in (note, note2):
        show(sc, ob, 1, False)
        show(sc, ob, F(13.30), True)
        show(sc, ob, F(15.62), False)
    label("P(doom) 0.02", UB - 6.2, VB + 2.0, 0.28, SIG, 0.22, "lab_pd")
    for i, (du_, vv) in enumerate([(5.6, 8.2), (-5.2, 7.4)]):
        label("1e-%d" % (8 + i), UB + du_, vv, 0.22, core.sc_x(BONE, 0.72), 0.16, f"lab_c{i}")
    label("local min.", UB - 6.4, VB + 4.4, 0.20, core.sc_x(ASH, 0.8), 0.14, "lab_lm")

    # a survey line from the pit label to the pierce point
    sc.render.filepath = os.path.join(core.OUT, "frames", name, "####")
    os.makedirs(os.path.dirname(sc.render.filepath), exist_ok=True)
    return sc
