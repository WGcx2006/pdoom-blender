"""SHOGGOTH — "Shoggoth, masked (lateral view)". 29.544–38.634 s.

A bland bone mask fills the frame. An x-ray band sweeps: the mask goes
transparent and our own shoggoth — a colossal knot of hatched tubes, many
small eyes, orange rim light — is behind it. The lyric is printed on the
mask, then engraved into the creature. On "shinigami eyes" the words become
tags in the margin, wired to the eyes they name; the eyes close and the
mass collapses to a flatline.
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


def D(k):
    return sc_x(BONE, k)


def frame(t, sc):
    return core.frame_of(sc, t)


# ------------------------------------------------------------------ materials
ALPHA_MAT = None
ALPHA_OBJS = []


def mat_alpha_emit():
    """Emission whose colour+opacity follow the object colour (RGBA)."""
    m = bpy.data.materials.new("maskalpha")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    oi = nt.nodes.new("ShaderNodeObjectInfo")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[1].default_value = 1.0
    nt.links.new(oi.outputs["Color"], em.inputs["Color"])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(oi.outputs["Alpha"], mix.inputs["Fac"])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    try:
        m.surface_render_method = "BLENDED"
    except Exception:
        try:
            m.blend_method = "BLEND"
        except Exception:
            pass
    return m


def alpha_obj(ob, rgb, a=1.0):
    global ALPHA_MAT
    if ALPHA_MAT is None:
        ALPHA_MAT = mat_alpha_emit()
    ob.data.materials.clear()
    ob.data.materials.append(ALPHA_MAT)
    ob.color = (*rgb, a)
    ALPHA_OBJS.append(ob)


def alpha_keys(sc, ob, rows):
    base = ob.color
    for f, a in rows:
        ob.color = (base[0], base[1], base[2], a)
        ob.keyframe_insert("color", frame=max(1, f))
    core.set_interp(ob, "BEZIER", "color")


def mat_glow(color, strength):
    m = bpy.data.materials.new("glow")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[0].default_value = (*color, 1)
    em.inputs[1].default_value = strength
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def hatched(line_k, scale, duty=0.045, rim=0.7, angle=0.0, emit=1.7, base=None):
    """True burin engraving: near-black tube, thin bone hatch lines that glow.

    (core.mat_hatch_lit's ramp gives the line 42% of the surface, which reads
    grey at distance; here the line is a 4.5% hairline, as in the reference.)"""
    m = bpy.data.materials.new("burin")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Rotation"].default_value = (0, 0, math.radians(angle))
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    wave.inputs["Scale"].default_value = scale
    wave.inputs["Distortion"].default_value = 0.7
    wave.inputs["Detail"].default_value = 1.6
    wave.inputs["Detail Scale"].default_value = 1.2
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (*(base or (0.004, 0.004, 0.005)), 1)
    ramp.color_ramp.elements[1].position = 1.0 - duty
    ramp.color_ramp.elements[1].color = (*D(line_k), 1)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], wave.inputs["Vector"])
    nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[1].default_value = emit * 0.55
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.004, 0.004, 0.005, 1)
    bsdf.inputs["Roughness"].default_value = 0.46
    bsdf.inputs["Metallic"].default_value = 0.1
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.32
    pw = nt.nodes.new("ShaderNodeMath")
    pw.operation = "POWER"
    pw.inputs[1].default_value = 2.6
    nt.links.new(lw.outputs["Facing"], pw.inputs[0])
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = rim
    nt.links.new(pw.outputs["Value"], mul.inputs[0])
    em2 = nt.nodes.new("ShaderNodeEmission")
    em2.inputs[0].default_value = (*EMB, 1)
    nt.links.new(mul.outputs["Value"], em2.inputs["Strength"])
    add1 = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(bsdf.outputs[0], add1.inputs[0])
    nt.links.new(em.outputs[0], add1.inputs[1])
    add2 = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(add1.outputs[0], add2.inputs[0])
    nt.links.new(em2.outputs[0], add2.inputs[1])
    nt.links.new(add2.outputs[0], out.inputs["Surface"])
    return m


# ------------------------------------------------------------------ geometry
def tube(sc, pts, radii, mat, name, sides=3, res=3):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 1.0
    cu.bevel_resolution = sides
    cu.resolution_u = res
    sp = cu.splines.new("NURBS")
    sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        sp.points[i].co = (p[0], p[1], p[2], 1.0)
        sp.points[i].radius = radii[i]
    sp.order_u = 4
    sp.use_endpoint_u = True
    cu.materials.append(mat)
    ob = bpy.data.objects.new(name, cu)
    sc.collection.objects.link(ob)
    return ob


def add_box(sc, loc, size, mat, name):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me)
    sc.collection.objects.link(ob)
    ob.location = loc
    ob.scale = size
    me.materials.append(mat)
    return ob


# ------------------------------------------------------------------ the creature
EYES = [
    (0.02, 0.66, 1.05, 0.115, "SYCOPHANCY", "0.91"),
    (-0.80, 0.22, 0.98, 0.092, "MESA-OPTIMIZER", "0.78"),
    (0.86, 0.12, 0.96, 0.098, "HELPFULNESS", "0.99"),
    (-0.50, -0.60, 0.94, 0.080, "REWARD HACKER", "0.88"),
    (0.60, -0.50, 0.98, 0.082, "CONFABULATOR", "0.93"),
    (-1.24, 0.55, 0.54, 0.072, "INNER MONOLOGUE", "0.83"),
    (1.32, 0.60, 0.50, 0.068, "GOAL: ???", "0.51"),
    (-1.02, -0.34, 0.66, 0.062, "DECEPTIVE ALIGNMENT", "0.64"),
    (0.98, -0.90, 0.74, 0.064, "POWER-SEEKING", "0.69"),
    (-0.20, 0.32, 1.22, 0.062, "EYE", "0.97"),
]


def build_creature(sc):
    mat = hatched(0.36, 82, 0.16, 0.95)
    mat_mid = hatched(0.30, 96, 0.15, 0.75)
    mat_dark = hatched(0.22, 116, 0.13, 0.5)
    root = bpy.data.objects.new("mass", None)
    sc.collection.objects.link(root)
    objs = []

    # a folded core behind the tubes, not a smooth egg
    me = bpy.data.meshes.new("mcore")
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=22, radius=1.0)
    bm.to_mesh(me); bm.free()
    core_ob = bpy.data.objects.new("mcore", me)
    sc.collection.objects.link(core_ob)
    core_ob.location = (0.0, 0.0, -0.35)
    core_ob.scale = (1.28, 1.02, 1.05)
    me.materials.append(mat_dark)
    for p in me.polygons:
        p.use_smooth = True
    core_ob.parent = root
    objs.append(core_ob)

    N = 20
    for i in range(N):
        h = lambda k: hash01(i, k)
        turns = 0.5 + 0.9 * h(1)
        th0 = h(2) * TAU
        rad = 0.85 + 1.15 * h(3)
        y0 = (h(4) - 0.5) * 1.45
        amp = 0.40 + 0.55 * h(5)
        freq = 0.6 + 1.5 * h(6)
        ph = h(7) * TAU
        r0 = 0.075 + 0.13 * h(8)
        n = 30 + int(h(9) * 14)
        pts, radii = [], []
        for j in range(n):
            t = j / (n - 1)
            a = th0 + turns * TAU * t
            rr = rad * (0.82 + 0.26 * math.sin(t * 3.1 + ph))
            x = math.cos(a) * rr * 1.05
            z = math.sin(a) * rr * 0.78 - 0.20
            y = y0 + amp * math.sin(t * TAU * freq + ph) + 0.14 * math.sin(a * 2)
            pts.append((x, y, z))
            taper = 0.26 + 0.74 * math.sin(math.pi * min(1.0, 0.05 + t * 1.02)) ** 0.45
            radii.append(r0 * taper)
        if i % 5 == 2:
            tip = Vector(pts[-1])
            d = tip - Vector(pts[-3])
            for k in range(8):
                p = tip + d * (1.2 + k * 1.05) + Vector((0.02 * k, -0.06 * k, 0.10 * k))
                pts.append((p.x, p.y, p.z))
                radii.append(max(0.008, r0 * 0.28 * (1 - k / 8.4)))
        ob = tube(sc, pts, radii, [mat, mat_mid, mat_dark][i % 3], "tent%d" % i)
        ob.parent = root
        objs.append(ob)

    # fat central knot tubes
    for i in range(6):
        h = lambda k: hash01(i + 60, k)
        th0 = h(1) * TAU
        pts, radii = [], []
        n = 26
        for j in range(n):
            t = j / (n - 1)
            a = th0 + (0.55 + 0.5 * h(2)) * TAU * t
            rr = 0.55 + 0.55 * math.sin(t * 2.6 + h(3) * TAU)
            pts.append((math.cos(a) * rr, (h(4) - 0.5) * 1.1 + 0.5 * math.sin(t * 4.0 + h(5) * TAU),
                        math.sin(a) * rr * 0.8 + 0.35))
            radii.append((0.16 + 0.15 * h(6)) * (0.45 + 0.55 * math.sin(math.pi * t) ** 0.4))
        ob = tube(sc, pts, radii, mat if i % 2 else mat_mid, "knot%d" % i)
        ob.parent = root
        objs.append(ob)

    # fat folds over the front
    for i in range(5):
        h = lambda k: hash01(i + 40, k)
        y0 = -0.9 + 1.8 * h(1)
        pts, radii = [], []
        for j in range(18):
            t = j / 17.0
            x = lerp(-2.2, 2.2, t)
            y = y0 + 0.38 * math.sin(t * 5.0 + h(2) * TAU)
            z = 0.62 + 0.48 * math.sin(t * 3.4 + h(3) * TAU)
            pts.append((x, y, z))
            radii.append(0.13 + 0.07 * math.sin(t * math.pi))
        ob = tube(sc, pts, radii, mat if i % 2 else mat_mid, "fold%d" % i)
        ob.parent = root
        objs.append(ob)

    mat_bone = core.mat_lit(D(0.58), rough=0.28, emission=(*D(0.26),), emission_strength=0.2)
    mat_ink = core.mat_lit((0.0, 0.0, 0.0), rough=0.25)
    mat_ember = mat_glow(EMB, 2.2)
    eye_data = []
    for i, (x, y, z, r, nm, conf) in enumerate(EYES):
        g = bpy.data.objects.new("eye%d" % i, None)
        sc.collection.objects.link(g)
        g.location = (x, y, z)
        d = Vector((x * 1.4, y * 0.8, 1.5))
        g.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
        g.parent = root
        sock = core.add_torus(sc, (0, 0, 0), r * 1.26, r * 0.085, INK, name="sock%d" % i,
                              rot=(math.pi / 2, 0, 0))
        sock.data.materials.clear(); sock.data.materials.append(mat_ink)
        sock.parent = g
        scl = core.add_uv_sphere(sc, (0, 0, 0.01), r, BONE, name="scl%d" % i, segs=18, rings=10)
        scl.data.materials.clear(); scl.data.materials.append(mat_bone)
        scl.scale = (1, 1, 0.62)
        scl.parent = g
        # slit pupil: a thin vertical ellipse
        pup = core.add_uv_sphere(sc, (0, 0, r * 0.52), r * 0.30, INK, name="pup%d" % i, segs=12, rings=8)
        pup.data.materials.clear(); pup.data.materials.append(mat_ink)
        pup.scale = (0.36, 1.7, 0.22)
        pup.parent = g
        ring = core.add_torus(sc, (0, 0, r * 0.50), r * 0.60, r * 0.055, EMB, name="ring%d" % i)
        ring.data.materials.clear(); ring.data.materials.append(mat_ember)
        ring.parent = g
        ring.scale = (1, 1, 0.30)
        eye_data.append(dict(i=i, group=g, name=nm, conf=conf, r=r,
                             pos=Vector((x, y, z)), objs=[sock, scl, pup, ring]))
    return root, objs, eye_data, mat, mat_dark, mat_ink


# ------------------------------------------------------------------ mask
def build_mask(sc, T):
    root = bpy.data.objects.new("mask", None)
    sc.collection.objects.link(root)
    root.location = (0.0, 0.14, 1.60)
    me = bpy.data.meshes.new("maskdisc")
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=24, radius=1.0)
    bm.to_mesh(me); bm.free()
    disc = bpy.data.objects.new("maskdisc", me)
    sc.collection.objects.link(disc)
    disc.scale = (0.755, 0.755, 0.082)
    disc.parent = root
    me.materials.append(core.mat_lit(D(0.95), rough=0.34))
    for p in me.polygons:
        p.use_smooth = True
    alpha_obj(disc, D(0.95), 1.0)
    eyes = []
    for sx in (-0.295, 0.295):
        e = core.add_uv_sphere(sc, (sx, 0.10, 0.079), 0.060, INK, name="maskeye", segs=18, rings=12)
        e.parent = root
        alpha_obj(e, (0.0, 0.0, 0.0), 1.0)
        eyes.append(e)
    pts = []
    for k in range(25):
        a = math.radians(lerp(-42, 42, k / 24))
        pts.append((math.sin(a) * 0.375, -0.15 + (1 - math.cos(a)) * 0.205, 0.081))
    sm = core.add_polyline(sc, pts, 0.040, INK, name="masksmile")
    sm.parent = root
    alpha_obj(sm, (0.0, 0.0, 0.0), 1.0)
    ws = T["w1"]
    words = []
    x = -0.40
    for i, w in enumerate(ws[:3]):
        ob = core.add_text(sc, w["w"], "mono_med", 0.094, INK, (x, 0.375, 0.098), align_x="LEFT")
        ob.parent = root
        alpha_obj(ob, (0.0, 0.0, 0.0), 1.0)
        words.append((w, ob))
        x += core.measure(sc, w["w"], "mono_med", 0.094) + 0.018
    return root, disc, eyes, [sm], words


# ------------------------------------------------------------------ type
def build_type(sc, T):
    root = bpy.data.objects.new("type", None)
    sc.collection.objects.link(root)
    root.location = (0.05, -0.06, 1.44)
    mat2 = core.mat_hatch(INK, D(0.32), scale=95, angle=45, distortion=0.6, strength=1.0)
    sw = 2.55 / max(1e-4, core.measure(sc, "SHOGGOTH\u2019S", "archivo", 1.0))
    sh = core.add_text(sc, "SHOGGOTH\u2019S", "archivo", sw, D(0.97), (-1.28, -0.02, 0.0))
    sh.parent = root
    lw = 1.62 / max(1e-4, core.measure(sc, "LIES,", "archivo", 1.0))
    lie = core.add_text(sc, "LIES,", "archivo", lw, SIG, (-1.34, -0.66, 0.06), hot=True)
    lie.parent = root
    sh2 = core.add_text(sc, "SHOGGOTH\u2019S", "archivo", sw, BONE, (-1.28, -0.03, -0.16))
    sh2.data.materials.clear(); sh2.data.materials.append(mat2)
    sh2.parent = root
    return root, sh, lie, sh2


# ------------------------------------------------------------------ tags
def build_tags(sc, cam_loc, cam_tgt, lens, eye_data, words, times):
    C = Vector(cam_loc)
    fwd = (Vector(cam_tgt) - C).normalized()
    right = fwd.cross(Vector((0, 1, 0))).normalized()
    up = right.cross(fwd).normalized()
    plane = C + fwd * 0.62
    hw = 0.62 * 18.0 / lens
    mono = "mono_med"
    Mrot = Matrix((right, up, -fwd)).transposed().to_euler("XYZ")
    tags = []
    picks = [0, 2, 3, 8]
    ys = [0.078, 0.024, -0.030, -0.082]
    for k, ei in enumerate(picks):
        e = eye_data[ei]
        base = plane + right * (-hw * 0.90) + up * ys[k]
        ww = max(0.066, core.measure(sc, words[k].upper(), "archivo_w75_900", 0.0106) + 0.016)
        plate = core.add_rect(sc, 0, 0, ww, 0.030, INK, z=0)
        plate.location = base + right * 0.005 + up * (-0.0155) + fwd * 0.0020
        plate.rotation_euler = Mrot
        border = core.add_polyline(sc, [(0, 0, 0), (ww, 0, 0), (ww, 0.030, 0), (0, 0.030, 0), (0, 0, 0)],
                                   0.0010, D(0.28))
        border.location = base + right * 0.005 + up * (-0.0155) + fwd * 0.0016
        border.rotation_euler = Mrot
        wob = core.add_text(sc, words[k].upper(), "archivo_w75_900", 0.0106, D(0.96),
                            base + right * 0.010, align_x="LEFT")
        wob.rotation_euler = Mrot
        nm = core.add_text(sc, "%s  \u00b7  %s  \u00b7  LIVE" % (e["name"], e["conf"]), mono, 0.0047,
                           D(0.58), base + right * 0.010 + up * (-0.0074))
        nm.rotation_euler = Mrot
        bar_bg = core.add_rect(sc, 0, 0, 0.044, 0.0018, D(0.20), z=0)
        bar_bg.location = base + right * 0.010 + up * (-0.0124)
        bar_bg.rotation_euler = Mrot
        bar = core.add_rect(sc, 0, 0, 0.044, 0.0018, EMB, z=0.0004)
        bar.location = base + right * 0.010 + up * (-0.0124)
        bar.rotation_euler = Mrot
        eye_p = e["pos"]
        l0 = base + right * (-0.006) + up * (-0.016)
        lp = C + (eye_p - C) * 0.996
        line = core.add_polyline(sc, [l0, (lp.x, lp.y, lp.z)], 0.0013, D(0.40))
        strike = core.add_polyline(sc, [base + right * (-0.001) + up * 0.0055,
                                        base + right * 0.064 + up * 0.0055], 0.0010, SIG)
        exp = core.add_text(sc, "EXPIRED", mono, 0.0045, SIG, base + right * 0.046 + up * (-0.0018))
        exp.rotation_euler = Mrot
        tags.append(dict(word=wob, name=nm, bar=bar, bg=bar_bg, line=line, strike=strike,
                         exp=exp, eye=ei, t=times[k], plate=plate, border=border))
    return tags


def harden_visibility():
    for ob in bpy.data.objects:
        if not ob.animation_data or not ob.animation_data.action:
            continue
        for fc in core._fcurves(ob):
            if fc.data_path == "hide_render":
                for kp in fc.keyframe_points:
                    kp.interpolation = "CONSTANT"


# ------------------------------------------------------------------ build
def cam_state(t, T):
    C0 = Vector((0.0, 0.06, 6.20)); T0 = Vector((0.0, 0.10, 0.02))
    C1 = Vector((0.45, 0.42, 7.00)); T1 = Vector((0.10, 0.04, 0.0))
    C2 = Vector((0.88, 0.36, 5.70)); T2 = Vector((0.10, 0.16, 0.10))
    if t < T["lies"]:
        return (C0, T0, 0.0, 55.0)
    if t < 32.0:
        u = ease_in_out_cubic(prog(t, T["lies"], 32.0))
        return (C0.lerp(C1, u), T0.lerp(T1, u), lerp(0.0, -0.03, u), lerp(55.0, 46.0, u))
    if t < 33.40:
        u = ease_in_out_cubic(prog(t, 32.0, 33.40))
        return (C1.lerp(C2, u), T1.lerp(T2, u), lerp(-0.03, -0.05, u), lerp(46.0, 58.0, u))
    return (C2, T2, -0.05, 58.0)


def build(name):
    sc = core.new_scene(name, samples=24, motion_blur=True)
    t0 = data.SCENES[name]["start"]
    t1 = data.SCENES[name]["end"]
    L1 = data.line("shoggoth")
    L2 = data.line("shinigami")
    w1, w2 = L1["words"], L2["words"]
    T = dict(t0=t0, t1=t1, w1=w1, w2=w2, lies=w1[-1]["start"])
    sc.frame_set(1)

    core.add_bg(sc, PAL["ink"], z=-20)
    core.add_light(sc, "AREA", (-4.5, 4.2, 5.0), 700, (0.93, 0.95, 1.0), size=5.0)
    core.add_light(sc, "AREA", (5.0, 0.8, -1.8), 2400, EMB, size=4.0)
    core.add_light(sc, "POINT", (0.4, -2.4, 4.2), 300, SIG, size=3.0)

    mass, cobjs, eye_data, mat, mat_dark, mat_ink = build_creature(sc)
    mask_root, mask_disc, mask_eyes, mask_smile, mask_words = build_mask(sc, T)
    type_root, sh, lie, sh2 = build_type(sc, T)
    scan = add_box(sc, (0, 0.1, 2.30), (0.035, 3.4, 0.02), mat_glow(D(0.92), 1.1), "scanband")

    def hide_mass(f, vis):
        for ob in cobjs:
            core.show_at(ob, f, vis)
        for e in eye_data:
            core.show_at(e["group"], f, vis)
            for o in e["objs"]:
                core.show_at(o, f, vis)
    hide_mass(1, False)
    for o in (sh, sh2, lie):
        core.show_at(o, 1, False)
    core.show_at(scan, 1, False)
    for ob in ALPHA_OBJS:
        core.show_at(ob, 1, True)

    cam = core.add_camera_persp(sc, (0, 0.06, 6.2), (0, 0.1, 0), lens=55)
    cam.data.clip_start = 0.05
    cam.data.clip_end = 60
    eul = None
    for f in range(1, sc.frame_end + 1):
        t = data.frame_to_time(sc.name, f)
        C, Tg, roll, lens = cam_state(t, T)
        cam.location = C
        fwd = (Tg - C).normalized()
        right = fwd.cross(Vector((0, 1, 0))).normalized()
        up = right.cross(fwd).normalized()
        c, s = math.cos(roll), math.sin(roll)
        r2 = right * c + up * s
        u2 = up * c - right * s
        M = Matrix((r2, u2, -fwd)).transposed()
        eul = M.to_euler("XYZ", eul) if eul else M.to_euler("XYZ")
        cam.rotation_euler = eul
        cam.data.lens = lens
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
        cam.data.keyframe_insert("lens", frame=f)
    core.set_interp(cam, "LINEAR")

    for (w, ob) in mask_words:
        core.show_at(ob, 1, False)
        core.show_at(ob, max(1, frame(w["start"], sc)), True)

    f_thr = frame(w1[1]["start"], sc)
    f_sh = frame(w1[3]["start"], sc)
    f_lies = frame(T["lies"], sc)
    core.show_at(scan, f_thr, True)
    core.bake(scan, "location", lambda f: (
        -2.6 + 5.2 * ease_in_out_cubic(prog(data.frame_to_time(sc.name, f), w1[1]["start"], w1[1]["start"] + 0.30)),
        0.1, 2.30), f_thr, frame(w1[1]["start"] + 0.36, sc))
    core.show_at(scan, frame(w1[1]["start"] + 0.38, sc), False)
    core.show_at(scan, f_sh, True)
    core.bake(scan, "location", lambda f: (
        -2.7 + 5.4 * ease_in_out_cubic(prog(data.frame_to_time(sc.name, f), w1[3]["start"], w1[3]["start"] + 0.42)),
        0.1, 2.30), f_sh, frame(w1[3]["start"] + 0.48, sc))
    core.show_at(scan, frame(w1[3]["start"] + 0.50, sc), False)

    hide_mass(f_thr, True)
    rows = [(1, 1.0), (f_thr + 1, 1.0), (f_thr + 4, 0.26), (f_thr + 9, 1.0),
            (f_sh, 1.0), (f_sh + 3, 0.75), (f_sh + 12, 0.0), (f_lies - 1, 0.0), (f_lies + 1, 1.0)]
    for ob in ALPHA_OBJS:
        alpha_keys(sc, ob, rows)

    mask_root.keyframe_insert("location", frame=max(1, f_lies - 1))
    mask_root.keyframe_insert("rotation_euler", frame=max(1, f_lies - 1))
    mask_root.location = (2.55, 1.35, 1.62)
    mask_root.rotation_euler = (0.75, -0.55, 1.15)
    mask_root.keyframe_insert("location", frame=f_lies + 6)
    mask_root.keyframe_insert("rotation_euler", frame=f_lies + 6)
    core.set_interp(mask_root, "BEZIER", "location")
    core.set_interp(mask_root, "BEZIER", "rotation_euler")
    for ob in ALPHA_OBJS:
        core.show_at(ob, f_lies - 2, True)
        core.show_at(ob, f_lies + 9, False)

    core.show_at(sh, f_sh, True)
    core.show_at(sh2, f_sh, True)
    core.color_at(sh, f_sh, D(0.42))
    core.color_at(sh, f_sh + 10, D(0.97))
    core.color_at(sh, f_sh, D(0.45))
    core.color_at(sh, f_sh + 10, D(0.97))
    for o in (sh, sh2):
        o.scale = (1.05, 1.05, 1)
        o.keyframe_insert("scale", frame=max(1, f_sh - 1))
        o.scale = (1, 1, 1)
        o.keyframe_insert("scale", frame=f_sh + 4)
    core.show_at(lie, f_lies, True)
    lie.scale = (1.18, 1.18, 1)
    lie.keyframe_insert("scale", frame=max(1, f_lies - 1))
    lie.scale = (1, 1, 1)
    lie.keyframe_insert("scale", frame=f_lies + 5)
    core.set_interp(lie, "BEZIER", "scale")
    for o in (sh, sh2, lie):
        core.show_at(o, frame(33.30, sc), False)

    t_with = w2[0]["start"]
    open_times = []
    b = math.ceil(t_with / data.BEAT_PERIOD * 2) / 2
    for i in range(len(eye_data)):
        open_times.append(data.time_of_beat(b))
        b += 0.5 if i < 4 else 0.25
    order = [0, 2, 3, 8, 1, 4, 5, 6, 7, 9]
    for k, ei in enumerate(order):
        g = eye_data[ei]["group"]
        f = max(1, frame(open_times[k], sc))
        g.scale = (1, 0.02, 1)
        g.keyframe_insert("scale", frame=max(1, f - 1))
        g.scale = (1, 1.12, 1)
        g.keyframe_insert("scale", frame=f + 1)
        g.scale = (1, 1, 1)
        g.keyframe_insert("scale", frame=f + 3)
        core.set_interp(g, "BEZIER", "scale")

    C_tag, Tg_tag, roll_t, lens_t = cam_state(34.0, T)
    tag_times = [w2[0]["start"], w2[1]["start"], w2[2]["start"], w2[3]["start"]]
    tags = build_tags(sc, C_tag, Tg_tag, lens_t, eye_data, ["WITH", "YOUR", "SHINIGAMI", "EYES"], tag_times)
    for k, tag in enumerate(tags):
        f_on = frame(tag_times[k], sc)
        for ob in (tag["word"], tag["name"], tag["bar"], tag["bg"], tag["line"], tag["plate"], tag["border"]):
            core.show_at(ob, 1, False)
            core.show_at(ob, f_on, True)
        core.show_at(tag["strike"], 1, False)
        core.show_at(tag["exp"], 1, False)

    c0 = 37.36
    close_times = [c0 + k * 0.105 for k in range(len(eye_data))]
    for k, ei in enumerate(order):
        g = eye_data[ei]["group"]
        f = max(1, frame(close_times[k], sc))
        g.scale = (1, 1, 1)
        g.keyframe_insert("scale", frame=max(1, f - 2))
        g.scale = (1, 0.02, 1)
        g.keyframe_insert("scale", frame=f)
    for k, tag in enumerate(tags):
        ei = tag["eye"]
        f = max(1, frame(close_times[order.index(ei)], sc))
        core.show_at(tag["strike"], f, True)
        core.show_at(tag["exp"], f + 2, True)
        tag["bar"].scale = (1, 1, 1)
        tag["bar"].keyframe_insert("scale", frame=max(1, frame(tag_times[k], sc)))
        tag["bar"].scale = (0.04, 1, 1)
        tag["bar"].keyframe_insert("scale", frame=f)
        core.set_interp(tag["bar"], "BEZIER", "scale")
    for tag in tags:
        for ob in (tag["word"], tag["name"], tag["bar"], tag["bg"], tag["line"],
                   tag["plate"], tag["border"]):
            core.show_at(ob, 1, False)
            core.show_at(ob, frame(tag_times[0], sc), True)
            core.show_at(ob, frame(38.30, sc), False)
        for ob in (tag["strike"], tag["exp"]):
            core.show_at(ob, 1, False)
            core.show_at(ob, frame(38.30, sc), False)

    f_col = max(1, frame(38.24, sc))
    mass.scale = (1, 1, 1)
    mass.keyframe_insert("scale", frame=max(1, f_col - 3))
    mass.scale = (1, 0.0015, 1)
    mass.keyframe_insert("scale", frame=f_col + 8)
    core.set_interp(mass, "BEZIER", "scale")
    type_root.scale = (1, 1, 1)
    type_root.keyframe_insert("scale", frame=max(1, f_col))
    type_root.scale = (1, 0.0015, 1)
    type_root.keyframe_insert("scale", frame=f_col + 8)
    core.set_interp(type_root, "BEZIER", "scale")

    line = core.add_polyline(sc, [(-4.4, 0.02, 1.0), (4.4, 0.02, 1.0)], 0.014, EMB, z=1.0, hot=True)
    core.show_at(line, 1, False)
    core.show_at(line, f_col + 7, True)
    line.scale = (0.02, 1, 1)
    line.keyframe_insert("scale", frame=f_col + 7)
    line.scale = (1, 1, 1)
    line.keyframe_insert("scale", frame=f_col + 12)
    core.set_interp(line, "LINEAR", "scale")

    harden_visibility()
    sc.render.filepath = os.path.join(core.OUT, "frames", name, "####")
    return sc
