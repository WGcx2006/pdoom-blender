
"""BUREAU — Form 7-B, Annex B (MLP), Appendix C (von Neumann). Bone paper, ink, orange stamp."""
import bpy, bmesh, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pdoom import core, data
from mathutils import Vector
from pdoom.core import PAL, clamp, lerp, smoothstep, ease_out_expo, ease_in_out_cubic, ease_out_cubic, hash01

INK, BONE, SIG, EMB, GRAPH, ASH, BLOOD, ACID = (
    PAL["ink"], PAL["bone"], PAL["signal"], PAL["ember"], PAL["graphite"], PAL["ash"], PAL["blood"], PAL["acid"])
PAPER = core.sc_x(BONE, 1.0)

A = (0.0, 0.0)
B = (26.0, 0.0)
C = (0.0, -14.0)

def fit_size(sc, text, fnt, width):
    m = core.measure(sc, text, fnt, 1.0)
    return width / m if m > 0 else 1.0


def T(sc, body, fnt, size, color, x, y, z=0.0, align="LEFT", rot=0.0, name=None, spacing=1.0, hot=False):
    return core.add_text(sc, body, fnt, size, color, (x, y, z), rot=(0, 0, rot),
                         align_x=align, name=name, spacing=spacing, hot=hot)


def R(sc, x, y, w, h, color, z=-0.02, name="r"):
    return core.add_rect(sc, x, y, w, h, color, z=z, name=name)


def L(sc, pts, w, color, z=0.0, name="l", cyclic=False):
    return core.add_polyline(sc, pts, w, color, z=z, name=name, cyclic=cyclic)


def box(sc, x, y, w, h, width, color, z=0.0, name="box"):
    return core.add_outline_rect(sc, x, y, w, h, width, color, z=z, name=name)


def arrow(sc, x0, y0, x1, y1, width, color, z=0.0, head=0.12, name="arr"):
    L(sc, [(x0, y0), (x1, y1)], width, color, z=z, name=name)
    ang = math.atan2(y1 - y0, x1 - x0)
    for da in (2.5, -2.5):
        L(sc, [(x1, y1), (x1 + math.cos(ang + da) * head, y1 + math.sin(ang + da) * head)],
          width, color, z=z, name=name + "_h")


def catmull(anchors, per=10, jitter=0.0, seed=0):
    pts = []
    A = [anchors[0]] + list(anchors) + [anchors[-1]]
    for i in range(1, len(A) - 2):
        p0, p1, p2, p3 = A[i - 1], A[i], A[i + 1], A[i + 2]
        for j in range(per):
            u = j / per
            u2, u3 = u * u, u * u * u
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * u + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * u2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * u3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * u + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * u2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * u3)
            if jitter:
                x += (hash01(seed, i, j) - 0.5) * jitter
                y += (hash01(seed + 1, i, j) - 0.5) * jitter
            pts.append((x, y))
    pts.append(anchors[-1])
    return pts


# ---------------------------------------------------------------- materials
def mat_paper_bureau():
    m = bpy.data.materials.new("bureau_paper")
    nt = core._nodes(m)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n1 = nt.nodes.new("ShaderNodeTexNoise")
    n1.inputs["Scale"].default_value = 2.2
    n1.inputs["Detail"].default_value = 3.0
    n1.inputs["Roughness"].default_value = 0.55
    n2 = nt.nodes.new("ShaderNodeTexNoise")
    n2.inputs["Scale"].default_value = 260.0
    n2.inputs["Detail"].default_value = 2.0
    n2.inputs["Roughness"].default_value = 0.6
    r1 = nt.nodes.new("ShaderNodeValToRGB")
    r1.color_ramp.elements[0].position = 0.30
    r1.color_ramp.elements[0].color = (*core.sc_x(PAPER, 0.975), 1)
    r1.color_ramp.elements[1].position = 0.72
    r1.color_ramp.elements[1].color = (*PAPER, 1)
    r2 = nt.nodes.new("ShaderNodeValToRGB")
    r2.color_ramp.elements[0].position = 0.35
    r2.color_ramp.elements[0].color = (*core.sc_x(PAPER, 0.995), 1)
    r2.color_ramp.elements[1].position = 0.68
    r2.color_ramp.elements[1].color = (*core.sc_x(PAPER, 1.0), 1)
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs[0].default_value = 0.45
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[1].default_value = 1.0
    nt.links.new(tc.outputs["Object"], n1.inputs["Vector"])
    nt.links.new(tc.outputs["Object"], n2.inputs["Vector"])
    nt.links.new(n1.outputs["Fac"], r1.inputs["Fac"])
    nt.links.new(n2.outputs["Fac"], r2.inputs["Fac"])
    nt.links.new(r1.outputs["Color"], mix.inputs[6])
    nt.links.new(r2.outputs["Color"], mix.inputs[7])
    nt.links.new(mix.outputs[2], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def mat_stamp_ink(coord_ob, name="stamp_ink"):
    """Orange rubber ink with erosion that shows paper. Coordinates shared by the whole stamp."""
    m = bpy.data.materials.new(name)
    nt = core._nodes(m)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    tc.object = coord_ob
    nf = nt.nodes.new("ShaderNodeTexNoise")
    nf.inputs["Scale"].default_value = 48.0
    nf.inputs["Detail"].default_value = 3.0
    nf.inputs["Roughness"].default_value = 0.62
    np = nt.nodes.new("ShaderNodeTexNoise")
    np.inputs["Scale"].default_value = 7.2
    np.inputs["Detail"].default_value = 2.0
    np.inputs["Roughness"].default_value = 0.5
    np.inputs["Distortion"].default_value = 0.35
    rf = nt.nodes.new("ShaderNodeValToRGB")
    rf.color_ramp.interpolation = "CONSTANT"
    rf.color_ramp.elements[0].position = 0.305
    rf.color_ramp.elements[0].color = (0, 0, 0, 1)
    rf.color_ramp.elements[1].position = 0.335
    rf.color_ramp.elements[1].color = (1, 1, 1, 1)
    rp = nt.nodes.new("ShaderNodeValToRGB")
    rp.color_ramp.interpolation = "CONSTANT"
    rp.color_ramp.elements[0].position = 0.300
    rp.color_ramp.elements[0].color = (0, 0, 0, 1)
    rp.color_ramp.elements[1].position = 0.330
    rp.color_ramp.elements[1].color = (1, 1, 1, 1)
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    oi = nt.nodes.new("ShaderNodeObjectInfo")
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs[6].default_value = (*core.sc_x(PAPER, 0.975), 1)
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[1].default_value = 1.0
    nt.links.new(tc.outputs["Object"], nf.inputs["Vector"])
    nt.links.new(tc.outputs["Object"], np.inputs["Vector"])
    nt.links.new(nf.outputs["Fac"], rf.inputs["Fac"])
    nt.links.new(np.outputs["Fac"], rp.inputs["Fac"])
    nt.links.new(rf.outputs["Color"], mul.inputs[0])
    nt.links.new(rp.outputs["Color"], mul.inputs[1])
    nt.links.new(mul.outputs[0], mix.inputs[0])
    nt.links.new(oi.outputs["Color"], mix.inputs[7])
    nt.links.new(mix.outputs[2], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def mat_shadow(name="contact_shadow"):
    m = bpy.data.materials.new(name)
    nt = core._nodes(m)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    ln = nt.nodes.new("ShaderNodeVectorMath")
    ln.operation = "LENGTH"
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.0
    mr.inputs["From Max"].default_value = 0.48
    mr.inputs["To Min"].default_value = 1.0
    mr.inputs["To Max"].default_value = 0.0
    oi = nt.nodes.new("ShaderNodeObjectInfo")
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs[7].default_value = (*core.sc_x(PAPER, 0.985), 1)
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[1].default_value = 1.0
    nt.links.new(tc.outputs["Object"], ln.inputs[0])
    nt.links.new(ln.outputs["Value"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], mix.inputs[0])
    nt.links.new(oi.outputs["Color"], mix.inputs[6])
    nt.links.new(mix.outputs[2], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def shadow_plane(sc, cx, cy, r):
    me = bpy.data.meshes.new("shadow")
    bm = bmesh.new()
    n = 64
    vs = [bm.verts.new((math.cos(i / n * math.tau) * 0.5, math.sin(i / n * math.tau) * 0.5, 0)) for i in range(n)]
    bm.faces.new(vs)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new("shadow", me)
    sc.collection.objects.link(ob)
    ob.location = (cx, cy, -0.12)
    ob.scale = (2 * r, 2 * r, 1)
    me.materials.append(mat_shadow())
    return ob


# ---------------------------------------------------------------- camera
def set_cam(cam, cx, cy, scale, tilt=0.0, roll=0.0):
    tx = math.radians(tilt); rz = math.radians(roll)
    d = 50.0
    dirx = -math.sin(rz) * math.sin(tx)
    diry = math.cos(rz) * math.sin(tx)
    dirz = -math.cos(tx)
    cam.location = (cx - d * dirx, cy - d * diry, -d * dirz)
    cam.rotation_euler = (tx, 0.0, rz)
    cam.data.ortho_scale = scale


def bake_cam(cam, sc, cam_at, shake_fn=None):
    for f in range(1, sc.frame_end + 1):
        t = data.frame_to_time(sc.name, f)
        cx, cy, s, tilt, roll = cam_at(t)
        if shake_fn:
            dx, dy, dr = shake_fn(t, f)
            cx += dx; cy += dy; roll += dr
        set_cam(cam, cx, cy, s, tilt, roll)
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
        cam.data.ortho_scale = s
        cam.data.keyframe_insert("ortho_scale", frame=f)
    core.set_interp(cam, "LINEAR")
    for fc in core._fcurves(cam.data):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"


# ---------------------------------------------------------------- typewriter
def mono_advance(sc, fnt, size):
    return core.measure(sc, "MM", fnt, size) - core.measure(sc, "M", fnt, size)


def type_words(sc, words, fnt, size, x, y, z, color, seed=0, per_max=0.055, name="tw"):
    adv = mono_advance(sc, fnt, size)
    objs = []
    cx = x
    for wi, w in enumerate(words):
        chars = list(w["w"])
        per = min(per_max, max(0.016, (w["end"] - w["start"]) / max(1, len(chars))))
        for i, ch in enumerate(chars):
            if ch != " ":
                k = seed * 131 + wi * 17 + i
                jy = (hash01(k, 3) - 0.5) * 0.018
                rot = (hash01(k, 4) - 0.5) * 0.014
                dens = 0.86 + 0.14 * hash01(k, 5)
                ob = T(sc, ch, fnt, size, core.sc_x(color, dens), cx, y + jy, z + i * 0.00002,
                       rot=rot, name=f"{name}_{wi}_{i}")
                tt = w["start"] + i * per
                fr = max(1, core.frame_of(sc, tt))
                if fr > 1:
                    core.show_at(ob, 1, False)
                    core.show_at(ob, fr, True)
                objs.append((ch, ob, cx, tt))
            cx += adv
        if wi < len(words) - 1:
            cx += adv
    return objs, cx


def make_caret(sc, x, y, h, color, z=0.03, name="caret"):
    return core.add_rect(sc, x, y, 0.014, h, color, z=z, name=name)


# ---------------------------------------------------------------- section A
def build_form(sc):
    box(sc, -8.35, -4.55, 16.7, 9.05, 0.022, INK)
    box(sc, -8.27, -4.47, 16.54, 8.89, 0.008, core.sc_x(INK, 0.55))
    for (x, y, sx, sy) in [(-8.9, -4.85, 1, 1), (8.9, -4.85, -1, 1), (-8.9, 4.85, 1, -1), (8.9, 4.85, -1, -1)]:
        L(sc, [(x + sx * 0.25, y), (x, y), (x, y + sy * 0.25)], 0.01, core.sc_x(INK, 0.45))

    # header
    T(sc, "FORM 7-B", "mono_bold", 0.62, INK, -8.05, 4.16, 0.01)
    T(sc, "SAFETY EVALUATION OF A FRONTIER SYSTEM", "mono_semi", 0.225, INK, -4.55, 4.25, 0.01)
    T(sc, "ABRIDGED EDITION  ·  PLEASE TYPE OR PRINT CLEARLY", "mono", 0.128, GRAPH, -4.55, 4.035, 0.01, spacing=1.02)
    L(sc, [(-8.05, 3.62), (8.05, 3.62)], 0.035, INK, z=0.02)
    T(sc, "CASE NO. 0000-000-342", "mono", 0.105, GRAPH, -8.05, 3.40, 0.01)
    T(sc, "CLASSIFICATION:  BENIGN", "mono", 0.105, GRAPH, -2.55, 3.40, 0.01)
    T(sc, "PAGE 1 OF 1  ·  DO NOT DETACH", "mono", 0.105, GRAPH, 8.05, 3.40, 0.01, align="RIGHT")
    L(sc, [(-8.05, 3.255), (8.05, 3.255)], 0.008, core.sc_x(INK, 0.4), z=0.01)

    # 1 findings
    T(sc, "1.", "mono_semi", 0.145, INK, -8.05, 2.86, 0.01)
    T(sc, "FINDINGS", "mono_semi", 0.145, INK, -7.80, 2.86, 0.01, spacing=1.05)
    T(sc, "(describe observed behaviour; attach additional sheets if the system asks you to)",
      "mono", 0.098, core.sc_x(INK, 0.52), -6.55, 2.86, 0.01, spacing=1.01)
    findings, find_end = type_words(sc, data.line("safe enough")["words"][:4],
                                     "mono_med", 0.50, -7.92, 1.82, 0.02, INK, seed=1, per_max=0.052,
                                     name="find")
    L(sc, [(-8.02, 1.55), (7.95, 1.55)], 0.012, core.sc_x(INK, 0.55), z=0.0)
    T(sc, "OBSERVED:  nominal.  NO ANOMALIES DETECTED.", "mono", 0.092, core.sc_x(INK, 0.42),
      -8.02, 1.64, 0.01, spacing=1.0)

    # 2 risk level
    L(sc, [(-8.05, 1.25), (8.05, 1.25)], 0.008, core.sc_x(INK, 0.35), z=0.0)
    T(sc, "2.", "mono_semi", 0.145, INK, -8.05, 0.94, 0.01)
    T(sc, "RISK LEVEL", "mono_semi", 0.145, INK, -7.80, 0.94, 0.01, spacing=1.05)
    opts = [("LOW", -5.85), ("MODERATE", -4.35), ("HIGH", -2.50), ("SAFE ENOUGH", -0.55)]
    for label, ox in opts:
        box(sc, ox, 0.80, 0.19, 0.19, 0.014, core.sc_x(INK, 0.85), name="cbx")
        T(sc, label, "mono", 0.145, core.sc_x(INK, 0.9), ox + 0.30, 0.83, 0.01, spacing=1.03)
    xo = -0.55
    x1 = L(sc, [(xo + 0.03, 0.82), (xo + 0.16, 0.97)], 0.024, INK, z=0.03, name="cbx_x1")
    x2 = L(sc, [(xo + 0.16, 0.82), (xo + 0.03, 0.97)], 0.024, INK, z=0.03, name="cbx_x2")
    for ob in (x1, x2):
        core.show_at(ob, 1, False)
        core.show_at(ob, core.frame_of(sc, 70.50), True)
    L(sc, [(-8.05, 0.62), (8.05, 0.62)], 0.008, core.sc_x(INK, 0.35), z=0.0)

    # 3 conclusion
    T(sc, "3.", "mono_semi", 0.145, INK, -8.05, 0.27, 0.01)
    T(sc, "CONCLUSION", "mono_semi", 0.145, INK, -7.80, 0.27, 0.01, spacing=1.05)
    concl, concl_end = type_words(sc, data.line("safe enough")["words"][4:],
                                   "mono_med", 0.50, -7.92, -0.72, 0.02, INK, seed=2, per_max=0.040,
                                   name="conc")
    L(sc, [(-8.02, -1.01), (7.95, -1.01)], 0.012, core.sc_x(INK, 0.55), z=0.0)
    L(sc, [(-8.05, -1.18), (8.05, -1.18)], 0.008, core.sc_x(INK, 0.35), z=0.0)

    # 4 signature
    T(sc, "4.", "mono_semi", 0.145, INK, -8.05, -1.55, 0.01)
    T(sc, "SIGNATURE OF EVALUATOR(S)", "mono_semi", 0.145, INK, -7.80, -1.55, 0.01, spacing=1.05)
    L(sc, [(-7.92, -2.95), (-4.45, -2.95)], 0.01, core.sc_x(INK, 0.55), z=0.0)
    T(sc, "SIGN HERE", "mono", 0.088, core.sc_x(INK, 0.48), -7.92, -3.10, 0.01, spacing=1.04)
    T(sc, "DATE  31 / 02 / SOON", "mono", 0.105, core.sc_x(INK, 0.55), -3.95, -2.72, 0.01, align="RIGHT")
    T(sc, "WITNESS", "mono_semi", 0.11, core.sc_x(INK, 0.65), -3.55, -1.70, 0.01, spacing=1.06)
    L(sc, [(-3.55, -2.95), (-0.15, -2.95)], 0.01, core.sc_x(INK, 0.42), z=0.0)
    T(sc, "WITNESS SIGNATURE", "mono", 0.078, core.sc_x(INK, 0.38), -3.55, -3.10, 0.01, spacing=1.02)

    # handwritten "We" — cursive strokes, revealed in chunks
    w1 = catmull([(-7.62, -2.42), (-7.44, -2.12), (-7.26, -2.68), (-7.06, -2.12), (-6.88, -2.68),
                  (-6.70, -2.22), (-6.58, -2.46)], per=7, jitter=0.012, seed=31)
    e1 = catmull([(-6.55, -2.50), (-6.43, -2.29), (-6.23, -2.34), (-6.28, -2.54), (-6.44, -2.52),
                  (-6.30, -2.70), (-6.02, -2.66), (-5.72, -2.60), (-5.40, -2.73)], per=8, jitter=0.010, seed=32)
    stroke = w1 + e1
    n = len(stroke)
    chunks = 10
    for ci in range(chunks):
        a = int(ci * (n - 1) / chunks); b = int((ci + 1) * (n - 1) / chunks)
        seg = stroke[a:b + 1]
        if len(seg) >= 2:
            ob = L(sc, seg, 0.015, INK, z=0.03, name=f"sig{ci}")
            fr = max(1, core.frame_of(sc, 72.30 + ci * 0.030))
            if fr > 1:
                core.show_at(ob, 1, False)
                core.show_at(ob, fr, True)
    L(sc, [(-8.05, -3.40), (8.05, -3.40)], 0.008, core.sc_x(INK, 0.35), z=0.0)

    # footnote
    T(sc, "* “Safe enough” is defined in Form 7-C, which has not been drafted.  Do not detach.",
      "mono", 0.098, core.sc_x(INK, 0.6), -8.05, -3.66, 0.01, spacing=1.0)
    T(sc, "FORM 7-C IS NOT AVAILABLE IN THIS UNIVERSE.", "mono", 0.080, core.sc_x(INK, 0.40),
      -8.05, -3.83, 0.01, spacing=1.02)

    # bottom right: est p(doom)
    T(sc, "5.", "mono_semi", 0.14, INK, 3.05, -3.80, 0.01)
    T(sc, "EST. P(DOOM)", "mono_semi", 0.14, INK, 3.35, -3.80, 0.01, spacing=1.04)
    T(sc, "(ROUND DOWN)", "mono", 0.082, core.sc_x(INK, 0.48), 3.35, -3.95, 0.01, spacing=1.02)
    L(sc, [(4.30, -4.12), (7.95, -4.12)], 0.01, core.sc_x(INK, 0.55), z=0.0)
    val = data.pdoom_text(72.55)
    pchars, pend = type_words(sc, [{"w": val, "start": 72.30, "end": 72.65}], "mono_med", 0.34,
                              4.42, -3.72, 0.02, INK, seed=4, per_max=0.045, name="pdoomfield")

    # right column: system card
    sx0, sy0, sw, sh = 2.55, 0.05, 5.45, 2.32
    box(sc, sx0, sy0, sw, sh, 0.014, core.sc_x(INK, 0.8), name="card")
    T(sc, "SYSTEM UNDER EVALUATION", "mono_semi", 0.105, core.sc_x(INK, 0.7), sx0 + 0.14, sy0 + sh - 0.20, 0.01, spacing=1.08)
    L(sc, [(sx0, sy0 + sh - 0.28), (sx0 + sw, sy0 + sh - 0.28)], 0.008, core.sc_x(INK, 0.45), z=0.0)
    rows = [("DESIGNATION", "ORACLE-7  (internal)"),
            ("PARAMETERS", "7.2 × 10^12"),
            ("TRAINING TOKENS", "1.8 × 10^13"),
            ("ALIGNMENT EVALS", "NONE ON FILE"),
            ("OPERATOR", "we")]
    yy = sy0 + sh - 0.53
    for k, v in rows:
        T(sc, k, "mono", 0.083, core.sc_x(INK, 0.48), sx0 + 0.14, yy, 0.01, spacing=1.02)
        T(sc, v, "mono_semi", 0.105, core.sc_x(INK, 0.85), sx0 + 1.62, yy, 0.01, spacing=1.02)
        yy -= 0.33
    T(sc, "NOTES", "mono", 0.083, core.sc_x(INK, 0.48), sx0 + 0.14, yy, 0.01)
    T(sc, "“seems fine”", "mono_italic", 0.115, core.sc_x(INK, 0.7), sx0 + 1.62, yy, 0.01)
    L(sc, [(sx0 + 1.55, sy0 + 0.10), (sx0 + 1.55, sy0 + sh - 0.30)], 0.006, core.sc_x(INK, 0.25), z=0.0)

    # caret for findings line
    caret = make_caret(sc, -7.92, 1.84, 0.40, INK)
    fdone = core.frame_of(sc, 70.95)
    for f in range(1, sc.frame_end + 1):
        t = data.frame_to_time(sc.name, f)
        x = -7.92
        for ch, ob, xx, tt in findings:
            if t >= tt:
                x = xx + mono_advance(sc, "mono_med", 0.50)
        caret.location.x = x
        caret.keyframe_insert("location", frame=f)
    core.set_interp(caret, "LINEAR", "location")
    core.show_at(caret, 1, False)
    core.show_at(caret, core.frame_of(sc, 69.66), True)
    core.show_at(caret, fdone + 24, False)

    # imprinters
    stamp_center = bpy.data.objects.new("stamp_coords", None)
    sc.collection.objects.link(stamp_center)
    stamp_center.location = (3.10, -1.75, 0.0)
    stamp_mat = mat_stamp_ink(stamp_center)

    scx, scy, srot = 3.10, -1.75, math.radians(-5.5)
    def P(u, v):
        return (scx + math.cos(srot) * u - math.sin(srot) * v,
                scy + math.sin(srot) * u + math.cos(srot) * v)
    stamp_objs = []
    for w, h, wid in [(5.30, 1.90, 0.048), (5.04, 1.66, 0.020)]:
        pts = [P(-w/2, -h/2), P(w/2, -h/2), P(w/2, h/2), P(-w/2, h/2)]
        stamp_objs.append(L(sc, pts, wid, SIG, z=0.06, name="stampbox", cyclic=True))
    stamp_objs.append(T(sc, "SAFE ENOUGH", "archivo_w87_900", 0.90, SIG, *P(0, -0.06), z=0.07,
                        align="CENTER", rot=srot, name="stamptext"))
    stamp_objs.append(T(sc, "EVALUATED  ·  WE RECKON", "mono_semi", 0.132, SIG, *P(0, 0.62), z=0.07,
                        align="CENTER", rot=srot, spacing=1.16))
    stamp_objs.append(T(sc, "DEPT. OF REASONABLE ASSURANCES", "mono_semi", 0.105, SIG, *P(0, -0.70),
                        z=0.07, align="CENTER", rot=srot, spacing=1.14))
    fimp = core.frame_of(sc, 71.12)
    for ob in stamp_objs:
        if ob.data.materials:
            ob.data.materials[0] = stamp_mat
        ob.color = (*PAPER, 1)
        core.color_at(ob, 1, PAPER)
        core.color_at(ob, fimp, PAPER)
        core.color_at(ob, core.frame_of(sc, 71.43), SIG)
        core.set_interp(ob, "BEZIER", "color")
        core.show_at(ob, 1, False)
        core.show_at(ob, fimp, True)
    # files stamp (over a paper knock-out)
    fknock = R(sc, 5.08, 2.55, 2.30, 0.82, PAPER, z=-0.03, name="filed_knock")
    fknock.color = (*PAPER, 1)
    fx, fy, fr = 6.20, 2.95, math.radians(4.0)
    def Q(u, v):
        return (fx + math.cos(fr) * u - math.sin(fr) * v, fy + math.sin(fr) * u + math.cos(fr) * v)
    filed = [fknock]
    for w, h, wid in [(2.20, 0.70, 0.026), (2.03, 0.55, 0.011)]:
        pts = [Q(-w/2, -h/2), Q(w/2, -h/2), Q(w/2, h/2), Q(-w/2, h/2)]
        filed.append(L(sc, pts, wid, INK, z=0.06, cyclic=True, name="filedbox"))
    filed.append(T(sc, "FILED", "mono_bold", 0.24, INK, *Q(0, 0.02), z=0.07, align="CENTER", rot=fr, spacing=1.12))
    filed.append(T(sc, "NO FURTHER ACTION", "mono", 0.056, INK, *Q(0, -0.24), z=0.07, align="CENTER", rot=fr, spacing=1.08))
    for ob in filed[1:]:
        if ob.data.materials:
            ob.data.materials[0] = stamp_mat
        ob.color = (*core.sc_x(PAPER, 0.975), 1)
    fstamp = core.frame_of(sc, 72.97)
    for ob in filed:
        core.show_at(ob, 1, False)
        core.show_at(ob, fstamp, True)
    for ob in filed[1:]:
        core.color_at(ob, fstamp, core.sc_x(PAPER, 0.975))
        core.color_at(ob, fstamp + 2, INK)
        core.set_interp(ob, "BEZIER", "color")
        ob.scale = (1.12, 1.12, 1)
        ob.keyframe_insert("scale", frame=fstamp)
        ob.scale = (1.0, 1.0, 1)
        ob.keyframe_insert("scale", frame=fstamp + 3)
        core.set_interp(ob, "BEZIER", "scale")

    # binder holes
    for yy in (2.15, -0.95, -3.75):
        core.add_disc(sc, -8.20, yy, 0.055, core.sc_x(INK, 0.9), z=-0.05, name="hole")
        core.add_disc(sc, -8.20, yy, 0.095, core.sc_x(PAPER, 0.86), z=-0.06, name="hole2")

    return findings, concl, stamp_center



# ---------------------------------------------------------------- section B: annex (MLP)
def build_mlp(sc):
    INKX = INK
    # header
    T(sc, "ANNEX B — TRAINING PROCEDURE", "mono_bold", 0.22, INK, 16.90, 4.55, 0.01, spacing=1.03)
    T(sc, "SCHEMATIC · NOT TO SCALE · DO NOT OPERATE UNSUPERVISED", "mono", 0.108, core.sc_x(INK, 0.55),
      16.90, 4.28, 0.01, spacing=1.03)
    L(sc, [(16.90, 3.78), (31.10, 3.78)], 0.02, INK, z=0.02)
    T(sc, "FORWARD PASS  →", "mono_semi", 0.135, core.sc_x(INK, 0.75), 31.10, 3.56, 0.01, align="RIGHT", spacing=1.06)
    T(sc, "EPOCH 001,042   LOSS 0.0341", "mono", 0.10, core.sc_x(INK, 0.5), 31.10, 3.38, 0.01, align="RIGHT", spacing=1.04)
    T(sc, "←  BACKWARD PASS  (∂L/∂w)", "mono_semi", 0.135, core.sc_x(INK, 0.75), 30.00, -3.86, 0.01,
      align="RIGHT", spacing=1.06)

    # network
    xs = [18.2, 21.5, 24.8, 28.1]
    counts = [4, 6, 6, 3]
    yc = 0.0
    sp = 0.72
    layers = []
    for x, n in zip(xs, counts):
        ys = [yc + (j - (n - 1) / 2.0) * sp for j in range(n)]
        layers.append(ys)
        for y in ys:
            pts = [(x + math.cos(i / 48 * math.tau) * 0.19, y + math.sin(i / 48 * math.tau) * 0.19) for i in range(48)]
            L(sc, pts, 0.018, core.sc_x(INK, 0.85), z=0.04, cyclic=True, name="node")
            core.add_disc(sc, x, y, 0.040, core.sc_x(INK, 0.8), z=0.05, name="nodedot")
    # wires
    segs = []
    for li in range(3):
        for ya in layers[li]:
            for yb in layers[li + 1]:
                segs.append(((xs[li], ya), (xs[li + 1], yb)))
    core.add_segments(sc, segs, 0.0055, core.sc_x(INK, 0.30), z=0.0, name="wires")
    # node halos that light with the pulse
    halos = []
    for li, x in enumerate(xs):
        for y in layers[li]:
            pts = [(math.cos(i / 40 * math.tau) * 0.265, math.sin(i / 40 * math.tau) * 0.265) for i in range(40)]
            ob = core.add_polyline(sc, pts, 0.018, PAPER, z=0.06, cyclic=True, name="halo")
            ob.location = (x, y, 0.06)
            halos.append((x, y, ob))
    # layer ticks and labels
    for li, x in enumerate(xs):
        names = ["INPUT  x", "HIDDEN  h1", "HIDDEN  h2", "OUTPUT  y"]
        T(sc, names[li], "mono_semi", 0.135, core.sc_x(INK, 0.78), x, -2.42, 0.01, align="CENTER", spacing=1.06)
        L(sc, [(x, -2.10), (x, -2.22)], 0.012, core.sc_x(INK, 0.55), z=0.0)
    for k in range(3):
        T(sc, f"W{k+1}", "mono_semi", 0.115, core.sc_x(INK, 0.7), (xs[k] + xs[k+1]) / 2, 1.58, 0.01,
          align="CENTER", spacing=1.1)
    T(sc, "b", "mono", 0.10, core.sc_x(INK, 0.45), xs[0] - 0.42, yc, 0.01, align="CENTER")
    T(sc, "b", "mono", 0.10, core.sc_x(INK, 0.45), xs[1] - 0.42, yc, 0.01, align="CENTER")
    T(sc, "b", "mono", 0.10, core.sc_x(INK, 0.45), xs[2] - 0.42, yc, 0.01, align="CENTER")
    T(sc, "Σ", "mono", 0.13, core.sc_x(INK, 0.6), xs[3] + 0.42, yc, 0.01, align="CENTER")

    # lyric: Forward MLP,
    fsz = 1.12
    fw = core.measure(sc, "Forward", "archivo", fsz)
    fwd_chars = []
    per = 0.072
    for i, ch in enumerate("Forward"):
        a = core.measure(sc, "Forward"[:i], "archivo", fsz)
        ob = T(sc, ch, "archivo", fsz, INK, 16.90 + a, 2.55, 0.02, rot=0.0, name=f"fwdchar{i}")
        fr = max(1, core.frame_of(sc, 74.06 + i * per))
        if fr > 1:
            core.show_at(ob, 1, False)
            core.show_at(ob, fr, True)
        fwd_chars.append(ob)
    mlp_x = 16.90 + fw + 0.22
    chars = []
    tM, tL, tP = 74.84, 75.244, 75.66
    for (ch, tt, off) in [("M", tM, 0.0), ("L", tL, 0.0), ("P", tP, 0.0), (",", 75.95, 0.0)]:
        pass
    # lay out letters with kerning from prefix widths
    prefix = ""
    for i, (ch, tt) in enumerate([("M", tM), ("L", tL), ("P", tP), (",", 75.98)]):
        a = core.measure(sc, prefix, "archivo", fsz)
        ob = T(sc, ch, "archivo", fsz, INK, mlp_x + a, 2.55, 0.02, name=f"mlpchar{i}")
        fr = max(1, core.frame_of(sc, tt))
        core.show_at(ob, 1, False)
        core.show_at(ob, fr, True)
        ob.scale = (1.10, 1.10, 1)
        ob.keyframe_insert("scale", frame=max(1, fr))
        ob.scale = (1.0, 1.0, 1)
        ob.keyframe_insert("scale", frame=fr + 3)
        core.set_interp(ob, "BEZIER", "scale")
        prefix += ch
        chars.append(ob)
    
    # backward, mirrored right->left
    total = core.measure(sc, "backward,", "archivo", 0.92)
    T_right = 30.00
    prefix = ""
    back_objs = []
    for i, ch in enumerate("backward,"):
        a = core.measure(sc, prefix, "archivo", 0.92)
        b = a + core.measure(sc, ch, "archivo", 0.92)
        prefix += ch
        if ch != " ":
            k = 70 + i
            jy = (hash01(k, 2) - 0.5) * 0.025
            ob = core.add_text(sc, ch, "archivo", 0.92, core.sc_x(INK, 0.94),
                               (T_right - b, -3.05 + jy, 0.02), align_x="RIGHT",
                               name=f"bwd{i}")
            ob.scale.x = -1.0
            fr = max(1, core.frame_of(sc, 76.12 + i * 0.046))
            core.show_at(ob, 1, False)
            core.show_at(ob, fr, True)
            back_objs.append(ob)
    
    # repeat + loop counters
    rep = T(sc, "repeat", "archivo", 0.92, INK, 16.90, -3.05, 0.02, name="repeat")
    core.show_at(rep, 1, False)
    core.show_at(rep, core.frame_of(sc, 76.845), True)
    rep.scale = (1.15, 1.15, 1)
    rep.keyframe_insert("scale", frame=max(1, core.frame_of(sc, 76.845)))
    rep.scale = (1.0, 1.0, 1)
    rep.keyframe_insert("scale", frame=core.frame_of(sc, 76.99))
    core.set_interp(rep, "BEZIER", "scale")
    counters = []
    for k in range(3):
        ob = T(sc, f"×{k+1}", "mono_bold", 0.26, SIG, 20.05, -2.97, 0.02, spacing=1.02)
        core.show_at(ob, 1, False)
        core.show_at(ob, core.frame_of(sc, 76.845 + k * 0.2513), True)
        if k < 2:
            core.show_at(ob, core.frame_of(sc, 76.845 + (k + 1) * 0.2513), False)
        counters.append(ob)
    T(sc, "LAST BEAT  ×3", "mono", 0.095, core.sc_x(INK, 0.45), 20.05, -3.34, 0.01, spacing=1.06)

    # pulse line (hot) and its glow
    pulse = core.add_polyline(sc, [(0, -2.25), (0, 2.08)], 0.018, SIG, z=0.10, hot=True, name="pulse")
    glow = core.add_polyline(sc, [(0, -2.25), (0, 2.08)], 0.07, core.sc_x(SIG, 0.42), z=0.09, name="pulseglow")

    def pulse_x(t):
        if t < 74.06:
            return 17.0
        if t <= 76.12:
            pts = [(74.06, 17.0), (74.84, 21.5), (75.244, 24.8), (75.66, 28.1), (76.12, 29.15)]
            return core.keys(t, [(a, b, core.ease_in_out_cubic) for a, b in pts])
        if t <= 76.68:
            u = ease_in_out_cubic(clamp((t - 76.12) / 0.56))
            return lerp(29.15, 17.0, u)
        if t < 76.845:
            return 17.0
        if t <= 77.599:
            seg = (77.599 - 76.845) / 3.0
            k = min(2, int((t - 76.845) / seg))
            u = ((t - 76.845) - k * seg) / seg
            return lerp(29.15, 17.0, ease_in_out_cubic(u))
        return 17.0

    for f in range(1, sc.frame_end + 1):
        t = data.frame_to_time(sc.name, f)
        px = pulse_x(t)
        pulse.location = (px, 0, 0.10)
        glow.location = (px, 0, 0.09)
        pulse.keyframe_insert("location", frame=f)
        glow.keyframe_insert("location", frame=f)
    core.set_interp(pulse, "LINEAR", "location")
    core.set_interp(glow, "LINEAR", "location")
    core.show_at(pulse, 1, False); core.show_at(glow, 1, False)
    core.show_at(pulse, core.frame_of(sc, 74.04), True)
    core.show_at(glow, core.frame_of(sc, 74.04), True)
    core.show_at(pulse, core.frame_of(sc, 77.64), False)
    core.show_at(glow, core.frame_of(sc, 77.64), False)

    # halos heat
    for (hx, hy, ob) in halos:
        prev = None
        for f in range(2, sc.frame_end + 1, 2):
            t = data.frame_to_time(sc.name, f)
            if t < 74.0 or t > 77.65:
                heat = 0.0
            else:
                heat = math.exp(-((pulse_x(t) - hx) / 0.42) ** 2)
            col = core.mixc(PAPER, SIG, heat)
            ob.color = (*col, 1)
            ob.keyframe_insert("color", frame=f)
        core.set_interp(ob, "LINEAR", "color")

    # a faint registration mark and annex tab in the blank paper before the sheet
    T(sc, "ANNEX B", "archivo_w62_900", 0.7, core.sc_x(INK, 0.10), 13.9, 0.0, -0.05, align="CENTER", rot=math.radians(90))
    L(sc, [(13.25, -4.6), (13.25, 4.6)], 0.008, core.sc_x(INK, 0.18), z=-0.04)
    L(sc, [(14.55, -4.6), (14.55, 4.6)], 0.008, core.sc_x(INK, 0.18), z=-0.04)


# ---------------------------------------------------------------- section C: appendix
def build_appendix(sc):
    Y = -14.0
    # the sheet's own paper (above the dark underlay, below the ink); split at the burn line
    paper_mat = core.mat_emit(PAPER)
    for (px, pw) in [(-25.0, 25.2), (0.2, 25.0)]:
        pn = core.add_rect(sc, px, Y - 10.0, pw, 20.0, PAPER, z=-0.6, name="app_paper")
        pn.data.materials.clear()
        pn.data.materials.append(paper_mat)
    T(sc, "APPENDIX C — LEGACY ARCHITECTURES (FOR REFERENCE ONLY)", "mono_semi", 0.145, core.sc_x(INK, 0.8),
      -8.05, Y + 4.28, 0.01, spacing=1.03)
    T(sc, "FIG. C-1", "mono", 0.10, core.sc_x(INK, 0.5), 8.05, Y + 4.28, 0.01, align="RIGHT", spacing=1.08)

    # lyric heading
    t_now = 77.72
    now_words = data.line("Neumann")["words"]  # Now von Neumann's obsolete
    small = now_words[:3]
    # small words typed in archivo 700
    cx = -7.90
    ybase = Y + 3.02
    small_objs = []
    for wi, w in enumerate(small):
        chars = list(w["w"])
        per = min(0.05, (w["end"] - w["start"]) / max(1, len(chars)))
        adv = core.measure(sc, "x", "archivo700", 0.68)
        for i, ch in enumerate(chars):
            if ch != " ":
                a = core.measure(sc, w["w"][:i], "archivo700", 0.68)
                ob = T(sc, ch, "archivo700", 0.68, INK, cx + a, ybase, 0.02, name=f"now{wi}_{i}")
                fr = max(1, core.frame_of(sc, w["start"] + i * per))
                core.show_at(ob, 1, False)
                core.show_at(ob, fr, True)
                small_objs.append(ob)
        cx += core.measure(sc, w["w"], "archivo700", 0.68) + core.space_width(sc, "archivo700", 0.68)
    # obsolete, huge
    ob_word = "obsolete"
    objs_obs = []
    obs_x = cx + 0.10
    obs_y = ybase - 0.14
    for i, ch in enumerate(ob_word):
        a = core.measure(sc, ob_word[:i], "archivo", 1.52)
        ob = T(sc, ch, "archivo", 1.52, INK, obs_x + a, obs_y, 0.02, name=f"obs{i}")
        fr = max(1, core.frame_of(sc, 80.043 + i * 0.040))
        core.show_at(ob, 1, False)
        core.show_at(ob, fr, True)
        objs_obs.append(ob)
    # underline rule
    L(sc, [(-8.05, Y + 2.42), (0.2, Y + 2.42)], 0.012, core.sc_x(INK, 0.5), z=0.0)
    L(sc, [(0.2, Y + 2.42), (8.05, Y + 2.42)], 0.012, core.sc_x(INK, 0.5), z=0.0)

    # ---------------- the von Neumann figure
    # light block fills
    core.add_rect(sc, -7.90, Y - 3.85, 5.30, 4.45, core.mixc(PAPER, INK, 0.035), z=-0.02, name="cpufill")
    core.add_rect(sc, -7.60, Y - 3.55, 2.45, 2.20, core.mixc(PAPER, INK, 0.045), z=-0.01, name="alufill")
    core.add_rect(sc, -4.90, Y - 3.55, 2.30, 2.20, core.mixc(PAPER, INK, 0.030), z=-0.01, name="ctrlf")
    core.add_rect(sc, 0.65, Y - 0.45, 7.25, 1.70, core.mixc(PAPER, INK, 0.030), z=-0.02, name="memfill")
    core.add_rect(sc, 0.65, Y - 4.05, 7.25, 1.65, core.mixc(PAPER, INK, 0.030), z=-0.02, name="iofill")

    # CPU
    cpx, cpy, cpw, cph = -7.90, Y - 3.85, 5.30, 4.45
    box(sc, cpx, cpy, cpw, cph, 0.022, INK, z=0.01, name="cpu")
    T(sc, "CPU", "mono_bold", 0.155, INK, cpx + 0.18, cpy + cph - 0.28, 0.02, spacing=1.1)
    T(sc, "CENTRAL PROCESSING UNIT", "mono", 0.068, core.sc_x(INK, 0.55), cpx + 0.18, cpy + cph - 0.43, 0.02)
    # ALU
    ax, ay, aw, ah = -7.60, Y - 3.55, 2.45, 2.20
    box(sc, ax, ay, aw, ah, 0.012, INK, z=0.02, name="alu")
    T(sc, "ALU", "mono_bold", 0.185, INK, ax + 0.15, ay + ah - 0.28, 0.03, spacing=1.12)
    T(sc, "ARITHMETIC / LOGIC", "mono", 0.062, core.sc_x(INK, 0.55), ax + 0.15, ay + ah - 0.41, 0.03)
    # adder symbol
    axs, ays = ax + aw / 2, ay + 0.62
    L(sc, [(axs - 0.55, ays + 0.32), (axs + 0.55, ays + 0.32), (axs + 0.30, ays - 0.18), (axs - 0.30, ays - 0.18)],
      0.011, core.sc_x(INK, 0.7), z=0.03, cyclic=True)
    T(sc, "+", "mono_med", 0.26, core.sc_x(INK, 0.75), axs, ays + 0.01, 0.04, align="CENTER")
    T(sc, "A", "mono", 0.06, core.sc_x(INK, 0.5), axs - 0.72, ays + 0.28, 0.03)
    T(sc, "B", "mono", 0.06, core.sc_x(INK, 0.5), axs - 0.72, ays - 0.02, 0.03)
    # CONTROL
    kx, ky, kw, kh = -4.90, Y - 3.55, 2.30, 2.20
    box(sc, kx, ky, kw, kh, 0.012, INK, z=0.02, name="ctrl")
    T(sc, "CONTROL", "mono_bold", 0.16, INK, kx + 0.15, ky + kh - 0.27, 0.03, spacing=1.12)
    T(sc, "UNIT", "mono_bold", 0.16, INK, kx + 0.15, ky + kh - 0.44, 0.03, spacing=1.12)
    T(sc, "SEQUENCER · DECODE", "mono", 0.058, core.sc_x(INK, 0.55), kx + 0.15, ky + kh - 0.57, 0.03)
    for i in range(4):
        for j in range(3):
            box(sc, kx + 0.15 + i * 0.48, ky + 0.16 + j * 0.40, 0.34, 0.27, 0.008, core.sc_x(INK, 0.55), z=0.03)
    # registers
    rx, ry = -7.60, Y - 2.05
    T(sc, "REGISTERS", "mono_semi", 0.068, core.sc_x(INK, 0.6), rx, ry + 0.48, 0.03, spacing=1.08)
    for i, lab in enumerate(["PC", "IR", "ACC", "MAR"]):
        box(sc, rx + i * 1.18, ry + 0.05, 1.02, 0.35, 0.010, core.sc_x(INK, 0.75), z=0.03)
        T(sc, lab, "mono_semi", 0.105, core.sc_x(INK, 0.8), rx + i * 1.18 + 0.11, ry + 0.15, 0.04, spacing=1.1)
    # a few control wires inside the CPU
    for i in range(5):
        yy = ky + 0.20 + i * 0.18
        L(sc, [(kx + kw + 0.02, yy), (kx + kw + 0.35, yy)], 0.006, core.sc_x(INK, 0.4), z=0.03)
        core.add_disc(sc, kx + kw + 0.37, yy, 0.018, core.sc_x(INK, 0.6), z=0.04, segments=12)

    # MEMORY
    mx, my, mw, mh = 0.65, Y - 0.45, 7.25, 1.70
    box(sc, mx, my, mw, mh, 0.022, INK, z=0.01, name="mem")
    T(sc, "MEMORY", "mono_bold", 0.18, INK, mx + 0.18, my + mh - 0.29, 0.03, spacing=1.1)
    T(sc, "1,024 WORDS × 32 BITS  ·  FERRITE CORE", "mono", 0.068, core.sc_x(INK, 0.55), mx + 1.95, my + mh - 0.27, 0.03)
    for i in range(8):
        for j in range(2):
            box(sc, mx + 0.22 + i * 0.86, my + 0.20 + j * 0.47, 0.74, 0.32, 0.007, core.sc_x(INK, 0.55), z=0.03)
    # I/O
    ix, iy, iw, ih = 0.65, Y - 4.05, 7.25, 1.65
    box(sc, ix, iy, iw, ih, 0.022, INK, z=0.01, name="io")
    T(sc, "INPUT / OUTPUT", "mono_bold", 0.16, INK, ix + 0.18, iy + ih - 0.28, 0.03, spacing=1.12)
    T(sc, "PAPER TAPE · TELETYPE · LINE PRINTER", "mono", 0.062, core.sc_x(INK, 0.55), ix + 2.55, iy + ih - 0.26, 0.03)
    # tape reel
    core.add_disc(sc, ix + 0.72, iy + 0.54, 0.28, core.mixc(PAPER, INK, 0.05), z=0.03, name="reel")
    for rr in (0.28, 0.19, 0.09):
        core.add_disc(sc, ix + 0.72, iy + 0.54, rr, core.sc_x(INK, 0.55), z=0.04, name="reelring")
    core.add_disc(sc, ix + 0.72, iy + 0.54, 0.15, core.mixc(PAPER, INK, 0.05), z=0.05)
    T(sc, "TAPE", "mono", 0.055, core.sc_x(INK, 0.5), ix + 0.72, iy + 0.10, 0.03, align="CENTER")
    # printer
    for i in range(3):
        box(sc, ix + 1.65 + i * 0.36, iy + 0.28, 0.28, 0.66, 0.009, core.sc_x(INK, 0.6), z=0.03)
        L(sc, [(ix + 1.72 + i * 0.36, iy + 0.80), (ix + 1.86 + i * 0.36, iy + 0.80)], 0.006, core.sc_x(INK, 0.45), z=0.04)
    T(sc, "PRINTER", "mono", 0.055, core.sc_x(INK, 0.5), ix + 2.14, iy + 0.10, 0.03, align="CENTER")
    # console
    box(sc, ix + 3.15, iy + 0.26, 1.05, 0.72, 0.011, core.sc_x(INK, 0.6), z=0.03)
    T(sc, "> ▮", "mono", 0.16, core.sc_x(INK, 0.7), ix + 3.28, iy + 0.48, 0.04)
    T(sc, "CONSOLE", "mono", 0.055, core.sc_x(INK, 0.5), ix + 3.67, iy + 0.10, 0.03, align="CENTER")
    # human
    box(sc, ix + 4.65, iy + 0.26, 0.95, 0.72, 0.011, core.sc_x(INK, 0.6), z=0.03)
    T(sc, "?", "archivo", 0.36, core.sc_x(INK, 0.75), ix + 5.12, iy + 0.36, 0.04, align="CENTER")
    T(sc, "HUMAN", "mono", 0.055, core.sc_x(INK, 0.5), ix + 5.12, iy + 0.10, 0.03, align="CENTER")
    # operator note under the printer
    T(sc, "(NOT TO SCALE)", "mono", 0.052, core.sc_x(INK, 0.35), ix + 6.95, iy + 0.10, 0.03, align="RIGHT")

    # SYSTEM BUS
    bx = -1.15
    L(sc, [(bx, Y - 4.10), (bx, Y + 1.30)], 0.045, INK, z=0.02)
    for yy in (-1.65, -2.05, -2.45):
        L(sc, [(-2.60, Y + yy), (bx, Y + yy)], 0.014, INK, z=0.02)
    T(sc, "ADDR", "mono", 0.052, core.sc_x(INK, 0.55), -1.25, Y - 1.57, 0.03, align="RIGHT")
    T(sc, "DATA", "mono", 0.052, core.sc_x(INK, 0.55), -1.25, Y - 1.97, 0.03, align="RIGHT")
    T(sc, "CTRL", "mono", 0.052, core.sc_x(INK, 0.55), -1.25, Y - 2.37, 0.03, align="RIGHT")
    # memory stub
    arrow(sc, bx, Y + 0.40, mx - 0.02, Y + 0.40, 0.012, INK, z=0.03, head=0.09)
    T(sc, "MEMORY BUS", "mono", 0.055, core.sc_x(INK, 0.5), bx + 0.12, Y + 0.48, 0.04, spacing=1.04)
    # io stub
    arrow(sc, bx, Y - 3.20, ix - 0.02, Y - 3.20, 0.012, INK, z=0.03, head=0.09)
    T(sc, "I/O BUS", "mono", 0.055, core.sc_x(INK, 0.5), bx + 0.12, Y - 3.12, 0.04, spacing=1.04)
    # spine ends
    arrow(sc, bx, Y - 4.10, bx, Y + 1.30, 0.010, core.sc_x(INK, 0.65), z=0.04, head=0.09)
    T(sc, "SYSTEM BUS", "mono_semi", 0.075, core.sc_x(INK, 0.65), bx + 0.14, Y - 1.85, 0.03,
      rot=math.radians(90), spacing=1.1)
    # dashed control line from control unit down to the bus
    segs = []
    for i in range(12):
        x0 = kx + kw + 0.05 + i * 0.30
        segs.append(((x0, Y - 3.85), (x0 + 0.16, Y - 3.85)))
    core.add_segments(sc, segs, 0.008, core.sc_x(INK, 0.4), z=0.03)
    T(sc, "CONTROL LINES", "mono", 0.052, core.sc_x(INK, 0.45), kx + 1.1, Y - 3.98, 0.04, align="CENTER")
    # caption
    T(sc, "FIG. C-1  —  VON NEUMANN ARCHITECTURE, 1945", "mono_semi", 0.10, core.sc_x(INK, 0.7),
      -7.92, Y - 4.32, 0.03, spacing=1.04)
    T(sc, "THE BOTTLENECK IS THE POINT.", "mono", 0.07, core.sc_x(INK, 0.45), 7.88, Y - 4.32, 0.03,
      align="RIGHT", spacing=1.06)
    # notes under the heading
    T(sc, "i.  STORED-PROGRAM CONCEPT      ii.  SHARED MEMORY      iii.  ONE INSTRUCTION AT A TIME",
      "mono", 0.062, core.sc_x(INK, 0.45), -7.95, Y + 2.18, 0.02, spacing=1.02)

    # orange marker strike on "obsolete"
    strike_pts = []
    for i in range(40):
        u = i / 39
        x = obs_x - 0.14 + u * (core.measure(sc, ob_word, "archivo", 1.52) + 0.28)
        y = obs_y + 0.30 + 0.045 * math.sin(u * 9.0) - 0.02 * u
        strike_pts.append((x, y))
    chunks = []
    n = len(strike_pts)
    for ci in range(6):
        a = int(ci * (n - 1) / 6); b = int((ci + 1) * (n - 1) / 6)
        ob = L(sc, strike_pts[a:b + 1], 0.055, SIG, z=0.05, name=f"obs_strike{ci}")
        core.show_at(ob, 1, False)
        core.show_at(ob, core.frame_of(sc, 80.043 + ci * 0.018), True)
        chunks.append(ob)
    # big orange cross-out over the figure
    def wob(x0, y0, x1, y1, seed):
        pts = []
        for i in range(64):
            u = i / 63
            x = lerp(x0, x1, u) + (hash01(seed, i) - 0.5) * 0.05
            y = lerp(y0, y1, u) + (hash01(seed + 3, i) - 0.5) * 0.05 + 0.02 * math.sin(u * 13.0)
            pts.append((x, y))
        return pts
    ex0, ey0, ex1, ey1 = -7.72, Y + 0.85, 7.15, Y - 4.05
    ex2, ey2 = -7.72, Y - 4.05
    ex3, ey3 = 7.15, Y + 0.85
    for si, pts in enumerate([wob(ex0, ey0, ex1, ey1, 51), wob(ex2, ey2, ex3, ey3, 61)]):
        for ci in range(9):
            a = int(ci * (len(pts) - 1) / 9); b = int((ci + 1) * (len(pts) - 1) / 9)
            ob = L(sc, pts[a:b + 1], 0.075, SIG, z=0.06, name=f"xout{si}_{ci}")
            core.show_at(ob, 1, False)
            core.show_at(ob, core.frame_of(sc, 80.09 + si * 0.05 + ci * 0.022), True)
    # spatter
    for k in range(18):
        x = lerp(-7.6, 7.0, hash01(k, 71)) + 0.0
        y = Y + 0.9 - hash01(k, 72) * 5.0
        r = 0.012 + hash01(k, 73) * 0.030
        ob = core.add_disc(sc, x, y, r, SIG, z=0.07, name="spatter")
        core.show_at(ob, 1, False)
        core.show_at(ob, core.frame_of(sc, 80.12 + hash01(k, 74) * 0.18), True)
    return


def ink_safe():
    return core.sc_x(INK, 0.55)



def build_burn(sc, bx):
    ax = bx
    # dark under-page and a hot glow in the tear
    under = core.add_rect(sc, -30, -30, 60, 32, core.sc_x(INK, 1.0), z=-3.0, name="underpage")
    core.show_at(under, 1, False)
    core.show_at(under, core.frame_of(sc, 80.36), True)
    warm = core.add_rect(sc, ax - 0.9, -24.0, 1.8, 16.0, core.sc_x(EMB, 0.55), z=-2.9, name="tearglow")
    warm.data.materials.clear()
    warm.data.materials.append(core.mat_emit(core.sc_x(EMB, 0.45)))
    core.show_at(warm, 1, False)
    core.show_at(warm, core.frame_of(sc, 80.44), True)
    # burn line: jagged, revealed behind a rising spark
    pts = []
    for i in range(90):
        u = i / 89
        y = lerp(-22.0, -9.2, u)
        x = ax + math.sin(u * 17.0) * 0.055 + (hash01(i, 91) - 0.5) * 0.06
        pts.append((x, y))
    n = len(pts)
    chunks = 22
    for ci in range(chunks):
        a = int(ci * (n - 1) / chunks); b = int((ci + 1) * (n - 1) / chunks)
        seg = pts[a:b + 1]
        if len(seg) >= 2:
            ob = L(sc, seg, 0.030, SIG, z=0.30, name=f"burn{ci}")
            if ob.data.materials:
                ob.data.materials[0] = core.mat_hot()
            ob.color = (*SIG, 1)
            core.show_at(ob, 1, False)
            core.show_at(ob, core.frame_of(sc, 80.40 + ci * 0.014), True)
            # a wider ember glow under the crack
            gl = L(sc, seg, 0.075, core.sc_x(EMB, 0.8), z=0.28, name=f"burnglow{ci}")
            core.show_at(gl, 1, False)
            core.show_at(gl, core.frame_of(sc, 80.40 + ci * 0.014), True)
    # scorched edges
    for s in (-1, 1):
        pts2 = [(x + s * 0.10, y) for (x, y) in pts]
        for ci in range(chunks):
            a = int(ci * (n - 1) / chunks); b = int((ci + 1) * (n - 1) / chunks)
            seg = pts2[a:b + 1]
            if len(seg) >= 2:
                ob = L(sc, seg, 0.045, core.sc_x(INK, 0.9), z=0.26, name="scorch")
                core.show_at(ob, 1, False)
                core.show_at(ob, core.frame_of(sc, 80.44 + ci * 0.014), True)
    # spark head rises with the crack
    head = core.add_uv_sphere(sc, (ax, -22.0, 0.4), 0.10, EMB, hot=True, name="burnspark")
    for f in range(1, sc.frame_end + 1):
        t = data.frame_to_time(sc.name, f)
        u = clamp((t - 80.40) / 0.44)
        y = lerp(-22.0, -9.2, u)
        head.location = (ax + math.sin(u * 17.0) * 0.055, y, 0.4)
        head.keyframe_insert("location", frame=f)
    core.set_interp(head, "LINEAR", "location")
    core.show_at(head, 1, False)
    core.show_at(head, core.frame_of(sc, 80.39), True)
    core.show_at(head, core.frame_of(sc, 80.86), False)
    # embers
    for k in range(16):
        x0 = ax + (hash01(k, 101) - 0.5) * 0.5
        y0 = -20.0 + hash01(k, 102) * 10.0
        sp = hash01(k, 103)
        ob = core.add_uv_sphere(sc, (x0, y0, 0.5), 0.02 + 0.03 * hash01(k, 104), EMB, hot=True, name="ember")
        core.show_at(ob, 1, False)
        core.show_at(ob, core.frame_of(sc, 80.46 + sp * 0.28), True)
        for f in range(core.frame_of(sc, 80.46 + sp * 0.28), sc.frame_end + 1):
            tt = data.frame_to_time(sc.name, f) - (80.46 + sp * 0.28)
            ob.location = (x0 + math.sin(tt * 7 + k) * 0.15 * tt, y0 + 1.7 * tt, 0.5 + 0.3 * tt)
            ob.keyframe_insert("location", frame=f)
        core.set_interp(ob, "LINEAR", "location")
        core.color_at(ob, core.frame_of(sc, 80.46 + sp * 0.28), EMB)
        core.color_at(ob, sc.frame_end, core.sc_x(EMB, 0.15))
        core.set_interp(ob, "LINEAR", "color")
    # a quick flash behind the tear
    fl = core.add_rect(sc, ax - 0.35, -20.0, 0.7, 12.0, EMB, z=-2.8, name="tearflash")
    fl.data.materials.clear()
    fl.data.materials.append(core.mat_hot())
    fl.color = (*EMB, 1)
    core.show_at(fl, 1, False)
    core.show_at(fl, core.frame_of(sc, 80.62), True)
    core.show_at(fl, sc.frame_end + 1, False)


def build(name):
    sc = core.new_scene(name, samples=32, motion_blur=True)
    bg = core.add_rect(sc, -100, -100, 200, 200, PAPER, z=-10.0, name="paperbg")
    bg.data.materials.clear()
    bg.data.materials.append(mat_paper_bureau())
    cam = core.add_camera_ortho(sc, 19.2)
    sc.frame_set(1)

    findings, concl, stamp_center = build_form(sc)

    # 3D stamp prop: an industrial hand stamp (base plate + grip + T handle)
    body = core.add_box(sc, (3.10, -1.75, 0.90), (5.28, 1.90, 0.50), INK,
                        material=core.mat_lit(core.sc_x(GRAPH, 0.42), 0.4, 0.25), name="stamp_body")
    pad = core.add_box(sc, (3.10, -1.75, 0.31), (5.58, 2.02, 0.56), SIG,
                       material=core.mat_lit(core.sc_x(SIG, 0.95), 0.45, 0.05), name="stamp_pad")
    band = core.add_box(sc, (3.10, -1.75, 1.18), (4.60, 1.48, 0.06), SIG,
                        material=core.mat_lit(core.sc_x(SIG, 0.95), 0.45, 0.1), name="stamp_band")
    grip = core.add_box(sc, (3.10, -1.75, 1.45), (4.35, 1.30, 0.50), BONE,
                        material=core.mat_lit(core.sc_x(BONE, 0.48), 0.42), name="stamp_grip")
    top = core.add_box(sc, (3.10, -1.75, 1.715), (4.05, 1.10, 0.06), core.sc_x(BONE, 0.6),
                       material=core.mat_lit(core.sc_x(BONE, 0.55), 0.35), name="stamp_top")
    post = core.add_cylinder(sc, (3.10, -1.75, 2.10), 0.22, 0.85, BONE,
                             material=core.mat_lit(core.sc_x(BONE, 0.5), 0.4), name="stamp_post")
    collar = core.add_torus(sc, (3.10, -1.75, 1.75), 0.26, 0.045, SIG, name="stamp_collar")
    collar.data.materials.clear()
    collar.data.materials.append(core.mat_lit(core.sc_x(SIG, 0.8), 0.3, 0.5))
    knob = core.add_uv_sphere(sc, (3.10, -1.75, 2.70), 0.62, BONE, name="stamp_knob")
    knob.scale = (1.0, 0.72, 0.62)
    knob.data.materials.clear()
    knob.data.materials.append(core.mat_lit(core.sc_x(BONE, 0.55), 0.35))
    padlab = T(sc, "SAFE ENOUGH", "mono_semi", 0.135, core.sc_x(INK, 0.9), 3.10, -2.78, 0.30,
              align="CENTER", rot=math.radians(90), name="padlabel")
    padlab.rotation_euler = (math.radians(90), 0, 0)
    stamp_parts = [body, pad, band, grip, top, post, collar, knob, padlab]
    for ob in (body, pad, grip, top, knob):
        mod = ob.modifiers.new("bev", "BEVEL")
        mod.width = 0.05
        mod.segments = 2
    T(sc, "FORM 7-B", "mono_semi", 0.17, INK, 3.10, -1.75, 1.755, align="CENTER", name="stamp_label")
    T(sc, "SAFE ENOUGH", "mono", 0.075, core.sc_x(INK, 0.55), 3.10, -1.24, 1.755,
      align="CENTER", name="stamp_label2")

    sh = shadow_plane(sc, 3.10, -1.95, 3.6)

    core.add_light(sc, "AREA", (0.0, 7.0, 12.0), 900, BONE, size=5.0, rot=(math.radians(-30), 0, 0), name="key")
    core.add_light(sc, "AREA", (-8.0, 2.0, 7.0), 260, SIG, size=3.0, rot=(math.radians(-70), 0, math.radians(-55)), name="rim")
    core.add_light(sc, "POINT", (4.0, -7.0, 4.0), 150, EMB, size=2.0, name="fill")

    f_hit = core.frame_of(sc, 71.12)
    f_start = core.frame_of(sc, 71.075)
    f_lift = core.frame_of(sc, 71.34)
    f_gone = core.frame_of(sc, 71.50)
    for ob in stamp_parts:
        base_loc = ob.location.copy()
        base_scale = ob.scale.copy()
        ob.location.z = base_loc.z + 2.4
        ob.keyframe_insert("location", frame=max(1, f_start - 1))
        for f in range(f_start, f_hit + 1):
            u = (f - f_start) / max(1, f_hit - f_start)
            ob.location.z = base_loc.z + 2.4 * (1 - u * u)
            ob.keyframe_insert("location", frame=f)
        ob.location.z = base_loc.z - 0.05
        ob.keyframe_insert("location", frame=f_hit + 2)
        ob.location.z = base_loc.z
        ob.keyframe_insert("location", frame=f_hit + 5)
        ob.location.z = base_loc.z + 0.05
        ob.keyframe_insert("location", frame=f_lift)
        ob.location.z = base_loc.z + 10.0
        ob.keyframe_insert("location", frame=f_gone)
        core.set_interp(ob, "BEZIER", "location")
        ob.scale = base_scale
        ob.keyframe_insert("scale", frame=1)
        ob.scale = (base_scale[0] * 1.02, base_scale[1] * 1.02, base_scale[2] * 0.78)
        ob.keyframe_insert("scale", frame=f_hit + 2)
        ob.scale = base_scale
        ob.keyframe_insert("scale", frame=f_hit + 7)
        core.set_interp(ob, "BEZIER", "scale")
        core.show_at(ob, 1, False)
        core.show_at(ob, f_start - 1, True)
        core.show_at(ob, f_gone + 2, False)
    # stamp label objects ride with the plate (parent to the plate)
    for ob in list(sc.objects):
        if ob.name.startswith("stamp_label"):
            ob.parent = top
            ob.matrix_parent_inverse = top.matrix_world.inverted()
    # shadow
    for f in range(1, sc.frame_end + 1):
        t = data.frame_to_time(sc.name, f)
        if t < 71.05:
            sc_ = 0.7; col = core.sc_x(PAPER, 0.975)
        elif t < 71.12:
            u = (t - 71.05) / 0.07
            sc_ = 0.7 + 1.35 * u * u
            col = core.mixc(core.sc_x(PAPER, 0.975), core.sc_x(PAPER, 0.55), u)
        elif t < 71.34:
            sc_ = 2.05; col = core.sc_x(PAPER, 0.55)
        else:
            u = clamp((t - 71.34) / 0.16)
            sc_ = 2.05 + 0.8 * u
            col = core.mixc(core.sc_x(PAPER, 0.55), core.sc_x(PAPER, 0.975), u)
        sh.scale = (sc_, sc_ * 0.62, 1)
        sh.color = (*col, 1)
        sh.keyframe_insert("scale", frame=f)
        sh.keyframe_insert("color", frame=f)
    core.set_interp(sh, "LINEAR", "scale")
    core.set_interp(sh, "LINEAR", "color")
    core.show_at(sh, 1, False)
    core.show_at(sh, f_start - 1, True)

    core.show_at(sh, core.frame_of(sc, 71.44), False)

    build_mlp(sc)

    before_c = set(sc.objects)
    build_appendix(sc)
    c_objs = [o for o in sc.objects if o not in before_c]

    BURN_X = 0.2
    left = bpy.data.objects.new("half_left", None)
    right = bpy.data.objects.new("half_right", None)
    for e in (left, right):
        e.empty_display_size = 1.0
        sc.collection.objects.link(e)
        e.location = (BURN_X, -14.0, 0.0)
    bpy.context.view_layer.update()
    for ob in c_objs:
        try:
            c = sum((ob.matrix_world @ Vector(corner) for corner in ob.bound_box), Vector()) / 8.0
        except Exception:
            c = ob.location
        e = left if c.x < BURN_X else right
        ob.parent = e
        ob.matrix_parent_inverse = e.matrix_world.inverted()
    for e, sgn in [(left, 1.0), (right, -1.0)]:
        e.rotation_euler = (0, 0, 0)
        e.keyframe_insert("rotation_euler", frame=core.frame_of(sc, 80.46))
        e.keyframe_insert("location", frame=core.frame_of(sc, 80.46))
        e.rotation_euler = (0, 0, 0)
        e.keyframe_insert("rotation_euler", frame=core.frame_of(sc, 80.60))
        e.keyframe_insert("location", frame=core.frame_of(sc, 80.60))
        e.rotation_euler = (0, math.radians(91) * sgn, 0)
        e.location = (BURN_X + sgn * 3.0, -14.0, 0.8)
        e.keyframe_insert("rotation_euler", frame=sc.frame_end)
        e.keyframe_insert("location", frame=sc.frame_end)
        core.set_interp(e, "BEZIER", "rotation_euler")
        core.set_interp(e, "BEZIER", "location")

    build_burn(sc, BURN_X)

    def cam_at(t):
        if t < 70.92:
            u = clamp((t - 69.55) / 1.37)
            return (lerp(-3.45, -2.35, u), 1.25, lerp(13.2, 12.9, u), 0, 0)
        if t < 71.05:
            u = ease_in_out_cubic(clamp((t - 70.92) / 0.13))
            return (lerp(-2.35, -0.95, u), lerp(1.25, -0.80, u), lerp(12.9, 15.6, u), lerp(0, 26, u), lerp(0.7, 0, u))
        if t < 71.12:
            u = ease_out_expo(clamp((t - 71.05) / 0.07))
            return (lerp(-0.95, -0.85, u), lerp(-0.80, -0.85, u), lerp(15.6, 15.4, u), lerp(26, 30, u), 0)
        if t < 71.55:
            u = clamp((t - 71.12) / 0.43)
            return (lerp(-0.85, -0.75, u), lerp(-0.85, -0.90, u), lerp(15.4, 15.2, u), 30, 0)
        if t < 72.15:
            u = ease_in_out_cubic(clamp((t - 71.55) / 0.60))
            return (lerp(-0.75, 0.0, u), lerp(-0.90, 0.0, u), lerp(15.2, 18.7, u), lerp(30, 0, u), 0)
        if t < 72.60:
            u = ease_in_out_cubic(clamp((t - 72.15) / 0.45))
            return (lerp(0.0, -4.95, u), lerp(0.0, -1.85, u), lerp(18.7, 9.4, u), 0, 0)
        if t < 72.95:
            return (-4.95, -1.85, 9.4, 0, 0)
        if t < 73.40:
            u = ease_in_out_cubic(clamp((t - 72.95) / 0.45))
            return (lerp(-4.95, 0.15, u), lerp(-1.85, 0.0, u), lerp(9.4, 18.2, u), 0, 0)
        if t < 73.55:
            return (0.15, 0.0, 18.2, 0, 0)
        if t < 74.02:
            u = ease_in_out_cubic(clamp((t - 73.55) / 0.47))
            return (lerp(0.15, 21.40, u), 0.0, lerp(18.2, 15.2, u), 0, -2.0 * math.sin(math.pi * u))
        if t < 74.84:
            u = clamp((t - 74.02) / 0.82)
            return (lerp(21.40, 21.90, u), 0.0, lerp(15.2, 15.0, u), 0, 0)
        if t < 75.244:
            u = ease_out_expo(clamp((t - 74.84) / 0.20))
            return (lerp(21.90, 22.30, u), 0.0, lerp(15.0, 14.9, u), 0, 0)
        if t < 75.66:
            u = ease_out_expo(clamp((t - 75.244) / 0.20))
            return (lerp(22.30, 22.70, u), 0.0, 14.9, 0, 0)
        if t < 76.12:
            u = clamp((t - 75.66) / 0.46)
            return (lerp(22.70, 23.00, u), 0.0, lerp(14.9, 15.2, u), 0, 0)
        if t < 76.68:
            u = ease_in_out_cubic(clamp((t - 76.12) / 0.56))
            return (23.00, 0.0, lerp(15.2, 16.6, u), 0, lerp(1.0, -0.8, u))
        if t < 77.60:
            st = 0.0
            if t >= 76.845:
                seg = (77.599 - 76.845) / 3.0
                k = min(2, int((t - 76.845) / seg))
                ph = ((t - 76.845) - k * seg) / seg
                st = 0.9 * math.exp(-ph * 8.0)
            return (23.00, 0.05 * st, 16.6 + 0.3 * st, 0, -0.8 + st * 0.7)
        if t < 77.72:
            u = clamp((t - 77.60) / 0.12)
            return (lerp(23.00, -3.20, u), lerp(0.0, -11.30, u), lerp(16.6, 12.4, u), 0, 0)
        if t < 78.82:
            u = clamp((t - 77.72) / 1.10)
            return (lerp(-3.20, -2.90, u), -11.30, lerp(12.4, 12.1, u), 0, 0)
        if t < 79.40:
            u = ease_in_out_cubic(clamp((t - 78.82) / 0.58))
            return (lerp(-2.90, 0.0, u), lerp(-11.30, -13.90, u), lerp(12.1, 18.2, u), 0, 0)
        if t < 80.043:
            u = clamp((t - 79.40) / 0.643)
            return (lerp(0.0, -0.05, u), lerp(-13.90, -13.95, u), lerp(18.2, 18.0, u), 0, 0)
        if t < 80.30:
            u = ease_out_expo(clamp((t - 80.043) / 0.20))
            return (lerp(-0.05, 0.0, u), lerp(-13.95, -13.70, u), lerp(18.0, 17.5, u), 0, 0)
        if t < 80.50:
            u = ease_in_out_cubic(clamp((t - 80.30) / 0.20))
            return (lerp(0.0, 0.05, u), lerp(-13.70, -13.95, u), lerp(17.5, 18.0, u), 0, 0)
        u = clamp((t - 80.50) / 0.40)
        return (lerp(0.05, 0.10, u), lerp(-13.95, -14.05, u), lerp(18.0, 17.0, u), lerp(0, 14, u), 0)

    def shake(t, f):
        amp = 0.0
        for ht, a in [(71.12, 0.075), (72.97, 0.035), (70.49, 0.010), (70.92, 0.010),
                      (74.84, 0.012), (75.244, 0.012), (75.66, 0.012),
                      (76.845, 0.014), (77.10, 0.014), (77.35, 0.014),
                      (78.16, 0.008), (78.82, 0.008),
                      (80.043, 0.016), (80.12, 0.012), (80.55, 0.030)]:
            if t >= ht:
                amp += a * math.exp(-(t - ht) * 19.0)
        return ((hash01(f, 21) - 0.5) * 2 * amp,
                (hash01(f, 22) - 0.5) * 2 * amp,
                (hash01(f, 23) - 0.5) * 0.5 * amp)

    bake_cam(cam, sc, cam_at, shake)
    core.setup_render_out(sc)
    return sc
