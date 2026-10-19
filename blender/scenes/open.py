"""OPEN — a luminous construction sheet: a plotter draws a unicorn for AGI."""
import bpy, math, os, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from pdoom import core, data, motifs
from pdoom.core import PAL, lerp, clamp, smoothstep, ease_out_expo, ease_in_out_cubic, hash01

INK, BONE, SIG, EMB, GRAPH, ASH, BLOOD, ACID = (PAL["ink"], PAL["bone"], PAL["signal"], PAL["ember"],
                                                PAL["graphite"], PAL["ash"], PAL["blood"], PAL["acid"])
DIM = core.sc_x(BONE, 0.24)
FAINT = core.sc_x(BONE, 0.09)


def fit(sc, text, font, width):
    m = core.measure(sc, text, font, 1.0)
    return width / m if m > 0 else 1.0


def poly_len(pts):
    n = 0.0
    for i in range(1, len(pts)):
        n += math.dist(pts[i - 1], pts[i])
    return n


def point_at(pts, k):
    total = poly_len(pts)
    want = total * clamp(k)
    acc = 0.0
    for i in range(1, len(pts)):
        d = math.dist(pts[i - 1], pts[i])
        if acc + d >= want:
            u = (want - acc) / max(1e-9, d)
            return (lerp(pts[i - 1][0], pts[i][0], u), lerp(pts[i - 1][1], pts[i][1], u))
        acc += d
    return pts[-1]


def ellipse(cx, cy, rx, ry, rot=0.0, n=96):
    out = []
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    for i in range(n + 1):
        a = i / n * math.tau
        x, y = math.cos(a) * rx, math.sin(a) * ry
        out.append((cx + c * x - s * y, cy + s * x + c * y))
    return out


def bezier(p0, p1, p2, p3, n=40):
    out = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        x = u**3*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t**3*p3[0]
        y = u**3*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t**3*p3[1]
        out.append((x, y))
    return out


def stroke(sc, pts, width, color, t0, t1, name="stroke", z=0.06, delay=0.0):
    ob = core.add_polyline(sc, pts, width, color, name=name, z=z)
    ob.data.bevel_factor_start = 0.0
    ob.data.bevel_factor_end = 0.0
    try:
        ob.data.bevel_factor_mapping_end = "SPLINE"
    except Exception:
        pass
    f0 = max(1, core.frame_of(sc, t0 + delay))
    f1 = max(f0 + 1, core.frame_of(sc, t1 + delay))
    ob.data.keyframe_insert("bevel_factor_end", frame=1)
    ob.data.keyframe_insert("bevel_factor_end", frame=f0)
    ob.data.bevel_factor_end = 1.0
    ob.data.keyframe_insert("bevel_factor_end", frame=f1)
    for fc in core._fcurves(ob.data):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    return ob


def dash(sc, x0, y0, x1, y1, n=12, width=0.007, color=None, z=0.03):
    segs = []
    for i in range(n):
        a = i / n
        b = a + 0.55 / n
        segs.append(((lerp(x0, x1, a), lerp(y0, y1, a)), (lerp(x0, x1, b), lerp(y0, y1, b))))
    return core.add_segments(sc, segs, width, color or core.sc_x(BONE, 0.18), z=z)


def callout(sc, x, y, tx, ty, text, t, color=None, size=0.13):
    color = color or core.sc_x(BONE, 0.55)
    pts = [(x, y), (x + (tx - x) * 0.55, y), (tx, ty)]
    o = core.add_polyline(sc, pts, 0.007, color, z=0.1)
    dot = core.add_uv_sphere(sc, (x, y, 0.12), 0.035, SIG, hot=True)
    lab = core.add_text(sc, text, "mono_med", size, color, (x + 0.15, y + 0.12, 0.12))
    core.show_at(o, 1, False); core.show_at(lab, 1, False); core.show_at(dot, 1, False)
    f = core.frame_of(sc, t)
    core.show_at(o, max(1, f), True); core.show_at(lab, max(1, f), True); core.show_at(dot, max(1, f), True)
    return o, lab


def sheet(sc):
    # a large dark sheet with a faint warm noise and a hairline border
    m = bpy.data.materials.new("sheet")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 55.0
    noise.inputs["Detail"].default_value = 4.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.3
    ramp.color_ramp.elements[0].color = (0.0035, 0.0035, 0.0040, 1)
    ramp.color_ramp.elements[1].position = 0.7
    ramp.color_ramp.elements[1].color = (0.0085, 0.0083, 0.0080, 1)
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    ob = core.add_rect(sc, -9.55, -5.35, 19.1, 10.7, INK, z=-0.6, name="sheet")
    ob.data.materials.clear()
    ob.data.materials.append(m)
    core.add_outline_rect(sc, -9.55, -5.35, 19.1, 10.7, 0.012, core.sc_x(BONE, 0.22), z=-0.55, name="sheetborder")
    # a sparse construction grid on the sheet
    segs = []
    for i in range(-16, 17):
        x = i * 1.2
        if -9.5 < x < 9.5:
            segs.append(((x, -5.3), (x, 5.3)))
    for j in range(-8, 9):
        y = j * 1.2
        if -5.3 < y < 5.3:
            segs.append(((-9.5, y), (9.5, y)))
    grid = core.add_segments(sc, segs, 0.0040, core.sc_x(BONE, 0.032), z=-0.5, name="grid")
    return ob, grid


def hatch_ellipse(sc, cx, cy, rx, ry, rot, angle, spacing, color, t0, t1, z=0.05):
    """Hatch chords clipped to a rotated ellipse (engraving inside the body)."""
    out = []
    n = (-math.sin(math.radians(angle)), math.cos(math.radians(angle)))
    u = (math.cos(math.radians(angle)), math.sin(math.radians(angle)))
    rmax = math.hypot(rx * n[0], ry * n[1])
    d = -rmax
    k = 0
    while d <= rmax:
        # line p = d*n + t*u; solve (px/rx)^2+(py/ry)^2=1
        A = (u[0] / rx) ** 2 + (u[1] / ry) ** 2
        B = 2 * (d * n[0] * u[0] / rx ** 2 + d * n[1] * u[1] / ry ** 2)
        C = (d * n[0] / rx) ** 2 + (d * n[1] / ry) ** 2 - 1
        disc = B * B - 4 * A * C
        if disc > 0:
            t = math.sqrt(disc)
            p0 = (d * n[0] - u[0] * t / (2 * A), d * n[1] - u[1] * t / (2 * A))
            p1 = (d * n[0] + u[0] * t / (2 * A), d * n[1] + u[1] * t / (2 * A))
            c, s_ = math.cos(math.radians(rot)), math.sin(math.radians(rot))
            w0 = (cx + c * p0[0] - s_ * p0[1], cy + s_ * p0[0] + c * p0[1])
            w1 = (cx + c * p1[0] - s_ * p1[1], cy + s_ * p1[0] + c * p1[1])
            if math.dist(w0, w1) > 0.18:
                out.append(stroke(sc, [w0, w1], 0.008, color, t0 + k * 0.01, t1 + k * 0.01, name=f"hatch{k}", z=z))
            k += 1
        d += spacing
    return out


def unicorn(sc, T):
    """Draws the unicorn from primitives; returns (parts, strokes) with reveal times."""
    parts = []
    # ground
    parts.append(("ground", [(-9.1, -2.85), (1.1, -2.85)], 0.012, core.sc_x(BONE, 0.28), 1.1, 1.7, 0.02))
    # body ellipse + inner hatch
    body = ellipse(-4.0, 0.15, 2.85, 1.45, -5, 160)
    parts.append(("body", body, 0.034, core.sc_x(BONE, 0.82), 1.9, 3.0, 0.06))
    parts.append(("bodyinner", ellipse(-4.0, 0.15, 2.97, 1.57, -5, 160), 0.010, core.sc_x(SIG, 0.55), 2.1, 3.15, 0.055))
    hatch_ellipse(sc, -4.0, 0.15, 2.85, 1.45, -5, 28, 0.30, core.sc_x(BONE, 0.30), 2.25, 3.2, 0.05)
    # neck (two lines)
    parts.append(("neck1", [(-1.35, 1.25), (-5.05, 2.72)], 0.034, core.sc_x(BONE, 0.82), 2.15, 2.6, 0.06))
    parts.append(("neck2", [(-0.95, 0.25), (-4.8, 1.85)], 0.034, core.sc_x(BONE, 0.82), 2.2, 2.65, 0.06))
    # head + muzzle
    parts.append(("head", ellipse(-5.95, 2.72, 1.18, 0.78, 17, 120), 0.034, core.sc_x(BONE, 0.84), 2.6, 3.2, 0.06))
    parts.append(("muzzle", ellipse(-6.95, 2.25, 0.56, 0.42, 12, 80), 0.028, core.sc_x(BONE, 0.84), 2.9, 3.35, 0.06))
    # ears
    parts.append(("ear1", [(-5.15, 3.35), (-5.0, 4.1), (-5.7, 3.5)], 0.026, core.sc_x(BONE, 0.72), 3.0, 3.3, 0.06))
    parts.append(("ear2", [(-5.8, 3.35), (-5.85, 4.05), (-6.25, 3.4)], 0.026, core.sc_x(BONE, 0.72), 3.05, 3.35, 0.06))
    # legs (four, bent at the knee)
    legdata = [(-5.55, -0.55, -5.85, -2.85), (-4.35, -0.7, -4.5, -2.85), (-1.55, -0.7, -1.35, -2.85), (-0.45, -0.5, -0.2, -2.85)]
    for i, (x0, y0, x1, y1) in enumerate(legdata):
        parts.append((f"leg{i}", [(x0, y0), (x0 - 0.10, (y0 + y1) / 2), (x1, y1)], 0.032, core.sc_x(BONE, 0.80), 2.35 + i * 0.1, 2.95 + i * 0.1, 0.05))
        parts.append((f"hoof{i}", [(x1 - 0.13, y1), (x1 + 0.13, y1), (x1 + 0.13, y1 - 0.22), (x1 - 0.13, y1 - 0.22)], 0.024, core.sc_x(BONE, 0.6), 2.9 + i * 0.1, 3.1 + i * 0.1, 0.05))
    # tail
    parts.append(("tail", bezier((-1.15, 0.9), (0.4, 2.0), (0.3, 0.3), (1.15, 1.25), 60), 0.030, core.sc_x(BONE, 0.76), 3.0, 3.6, 0.06))
    parts.append(("tail2", bezier((-1.15, 0.7), (0.15, 1.5), (0.0, -0.1), (0.95, 0.55), 60), 0.022, core.sc_x(BONE, 0.58), 3.15, 3.7, 0.06))
    # mane: strands down the neck
    parts.append(("mane", bezier((-5.5, 3.35), (-4.4, 2.95), (-3.4, 2.0), (-1.7, 1.55), 60), 0.028, core.sc_x(BONE, 0.7), 3.2, 3.75, 0.06))
    parts.append(("mane2", bezier((-6.0, 2.95), (-5.2, 2.55), (-4.4, 2.4), (-3.3, 1.8), 60), 0.022, core.sc_x(BONE, 0.55), 3.3, 3.8, 0.06))
    # horn
    parts.append(("horn", [(-6.35, 3.3), (-7.75, 5.05)], 0.034, SIG, 3.4, 3.95, 0.10))
    for k in range(6):
        y = 3.5 + k * 0.24
        x = -6.35 - (y - 3.3) * 0.8
        parts.append((f"hornring{k}", [(x - 0.10, y + 0.02), (x + 0.10, y - 0.02)], 0.015, core.sc_x(SIG, 0.8), 3.55 + k * 0.05, 3.75 + k * 0.05, 0.11))
    # eye dot
    parts.append(("eye", ellipse(-6.28, 2.86, 0.095, 0.095, 0, 32), 0.020, SIG, 4.75, 4.95, 0.12))
    return parts


def pcb(sc, t0):
    # circuit traces that grow out of the unicorn's outline
    traces = [
        [(-5.4, -2.85), (-5.4, -3.5), (-7.2, -3.5), (-7.2, -4.3)],
        [(-1.2, -2.85), (-1.2, -3.6), (0.4, -3.6), (0.4, -4.4)],
        [(-6.9, -0.9), (-8.2, -0.9), (-8.2, 0.4), (-8.9, 0.4)],
        [(0.2, 0.0), (1.0, 0.0), (1.0, -1.2), (1.7, -1.2)],
        [(-7.3, 2.45), (-8.4, 2.45), (-8.4, 3.3)],
    ]
    objs = []
    for i, tr in enumerate(traces):
        ob = core.add_polyline(sc, tr, 0.012, core.sc_x(SIG, 0.45), name=f"pcb{i}", z=0.07)
        f0 = core.frame_of(sc, t0 + i * 0.06)
        f1 = core.frame_of(sc, t0 + 0.55 + i * 0.06)
        ob.data.bevel_factor_end = 0.0
        ob.data.keyframe_insert("bevel_factor_end", frame=max(1, f0))
        ob.data.bevel_factor_end = 1.0
        ob.data.keyframe_insert("bevel_factor_end", frame=f1)
        for fc in core._fcurves(ob.data):
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
        objs.append(ob)
        # pads
        for p in (tr[-1],):
            d = core.add_disc(sc, p[0], p[1], 0.06, core.sc_x(SIG, 0.8), z=0.08)
            core.show_at(d, 1, False)
            core.show_at(d, f1, True)
    return objs


def build(name):
    assert name == "open"
    sc = core.new_scene("open", samples=40, motion_blur=True)
    core.add_bg(sc)
    cam = core.add_camera_ortho(sc, 19.2)
    sheet(sc)
    sc.frame_set(1)

    l1 = data.line("sparks of AGI")
    l2 = data.line("Your circuits")
    l3 = data.line("that's no surprise")

    # header / title block
    motifs.mono(sc, "FIG. 01  ·  SPARKS OF AGI", -9.25, 4.85, 0.15, core.sc_x(BONE, 0.55))
    motifs.mono(sc, "PAPERS.OF.THE.END / PLATE 01 / SHEET 1 OF 1", -9.25, 4.55, 0.10, core.sc_x(BONE, 0.25))
    core.add_polyline(sc, [(-9.3, 4.4), (-4.4, 4.4)], 0.008, core.sc_x(BONE, 0.25))
    # TikZ listing at top right, typed line by line
    listing = [
        "\\draw[ellipse] (0,0) ellipse (2.85 and 1.45);",
        "\\draw (2.7,1.0) -- (-2.0,3.1) -- (-3.2,3.3);",
        "\\draw (-1.0,-0.5) -- (-1.0,-2.85);",
        "\\draw[horn] (-3.0,3.4) -- (-4.4,5.3);",
        "\\fill[signal] (-3.0,3.1) circle (0.08);",
    ]
    for i, line in enumerate(listing[:3]):
        ob = motifs.mono(sc, line, 1.35, 4.78 - i * 0.22, 0.090, core.sc_x(BONE, 0.22))
        core.show_at(ob, 1, False)
        core.show_at(ob, core.frame_of(sc, 1.5 + i * 0.45), True)

    # the drawing
    parts = unicorn(sc, 0)
    for (nm, pts, w, col, t0, t1, z) in parts:
        stroke(sc, pts, w, col, t0, t1, name=nm, z=z)
    # during the eye close-up, strip the drawing back to the head
    for ob in list(sc.objects):
        if any(ob.name.startswith(p) for p in ("body", "hatch", "leg", "hoof", "tail", "mane", "ground")):
            core.show_at(ob, 1, True)
            core.show_at(ob, core.frame_of(sc, 5.02), False)
            core.show_at(ob, core.frame_of(sc, 5.86), True)
    # the spark is the pen: a hot point at the tip of each stroke as it draws
    for (nm, pts, w, col, t0, t1, z) in parts:
        if nm in ("body", "neck1", "head", "horn", "eye", "tail", "mane", "leg0", "leg2"):
            pen = core.add_uv_sphere(sc, (0, 0, 0.2), 0.045, EMB, hot=True, name="pen_" + nm)
            core.show_at(pen, 1, False)
            fa, fb = core.frame_of(sc, max(0.9, t0)), core.frame_of(sc, t1)
            core.show_at(pen, max(1, fa), True)
            core.show_at(pen, min(sc.frame_end, fb) + 1, False)
            for ff in range(max(1, fa), min(sc.frame_end, fb) + 1):
                k = (ff - fa) / max(1, fb - fa)
                p = point_at(pts, k)
                pen.location = (p[0], p[1], 0.2)
                pen.keyframe_insert("location", frame=ff)
            core.set_interp(pen, "LINEAR", "location")

    # the pen arrives across the sheet before the first line
    arr = core.add_polyline(sc, [(9.7, 2.45), (-6.4, 2.45)], 0.006, core.sc_x(SIG, 0.35), z=0.12, name="pen_arrival")
    arr.data.bevel_factor_end = 0.0
    arr.data.keyframe_insert("bevel_factor_end", frame=core.frame_of(sc, 0.35))
    arr.data.bevel_factor_end = 1.0
    arr.data.keyframe_insert("bevel_factor_end", frame=core.frame_of(sc, 1.25))
    for fc in core._fcurves(arr.data):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    core.show_at(arr, core.frame_of(sc, 1.55), False)
    pen0 = core.add_uv_sphere(sc, (9.7, 2.45, 0.2), 0.05, EMB, hot=True, name="pen_arrival_head")
    core.show_at(pen0, 1, False)
    core.show_at(pen0, core.frame_of(sc, 0.35), True)
    core.show_at(pen0, core.frame_of(sc, 1.28), False)
    for ff in range(core.frame_of(sc, 0.35), core.frame_of(sc, 1.3)):
        k = (ff - core.frame_of(sc, 0.35)) / max(1, core.frame_of(sc, 1.3) - core.frame_of(sc, 0.35))
        pen0.location = (lerp(9.7, -6.4, ease_out_expo(k)), 2.45, 0.2)
        pen0.keyframe_insert("location", frame=ff)
    core.set_interp(pen0, "LINEAR", "location")

    # construction geometry
    dash(sc, -8.2, -1.75, 1.0, -1.75, 24, 0.006, core.sc_x(BONE, 0.16))
    dash(sc, -4.0, -2.55, -4.0, 2.35, 20, 0.006, core.sc_x(BONE, 0.16))
    circ = ellipse(-4.0, 0.15, 3.0, 1.58, 0, 180)
    conste = core.add_polyline(sc, circ, 0.005, core.sc_x(BONE, 0.13), z=0.02, cyclic=True, name="constructellipse")
    core.show_at(conste, 1, True)
    core.show_at(conste, core.frame_of(sc, 5.02), False)
    core.show_at(conste, core.frame_of(sc, 5.86), True)
    motifs.mono(sc, "ellipse(2.9, 1.35)", -4.0, 2.28, 0.10, core.sc_x(BONE, 0.3), align="CENTER")
    # dimension arrows for the body
    core.add_polyline(sc, [(-6.85, -1.9), (0.85, -1.9)], 0.006, core.sc_x(BONE, 0.2), z=0.02)
    for xx in (-6.85, 0.85):
        core.add_polyline(sc, [(xx - 0.12, -1.82), (xx, -1.9), (xx - 0.12, -1.98)], 0.006, core.sc_x(BONE, 0.2), z=0.02)
    motifs.mono(sc, "w = 5.70", -3.0, -2.15, 0.09, core.sc_x(BONE, 0.28), align="CENTER")
    # eye callout
    callout(sc, -6.28, 2.86, -5.2, 3.75, "r = 0.08", 4.9, SIG, 0.105)
    # sheet furniture
    motifs.mono(sc, "1 : 1  ·  INK / BONE / SIGNAL", 5.4, -4.55, 0.10, core.sc_x(BONE, 0.25))
    motifs.mono(sc, "DRAWN BY SPARK / PEN 0.3 mm", 5.4, -4.8, 0.10, core.sc_x(BONE, 0.25))

    # AGI
    agi_size = fit(sc, "AGI", "archivo", 7.15)
    agi = core.add_text(sc, "AGI", "archivo", agi_size, core.sc_x(BONE, 0.16), (9.2, 1.75, 0.05), align_x="RIGHT", name="agi")
    core.show_at(agi, 1, False)
    f_agi = core.frame_of(sc, 3.677)
    core.show_at(agi, max(1, f_agi), True)
    agi.color = (*BONE, 1)
    agi.keyframe_insert("color", frame=max(1, f_agi))
    agi.scale = (1.16, 1.16, 1)
    agi.keyframe_insert("scale", frame=max(1, f_agi))
    agi.scale = (1, 1, 1)
    agi.keyframe_insert("scale", frame=f_agi + 5)
    # a rule under AGI and its mono footnote
    core.add_polyline(sc, [(2.1, 1.55), (9.25, 1.55)], 0.010, core.sc_x(SIG, 0.85), z=0.04)
    motifs.mono(sc, "ARTIFICIAL GENERAL INTELLIGENCE / NOT YET A PRODUCT", 2.1, 1.3, 0.09, core.sc_x(BONE, 0.3))

    # lyric 1 — along the bottom
    lyr1, objs1, w1 = core.add_lyric(sc, "sparks of AGI", -8.95, -4.15, "archivo", 1.35, color=BONE,
                                     max_width=17.3, name="l1")
    core.sync_words(sc, objs1, pre=0.25)
    # a baseline rule
    core.add_polyline(sc, [(-9.25, -4.45), (9.25, -4.45)], 0.008, core.sc_x(BONE, 0.2))

    # lyric 2 and 3 share one row on the right (line change at "that's no surprise")
    lyr2, objs2, w2 = core.add_lyric(sc, "Your circuits", 0.4, -3.3, "archivo", 0.82, color=BONE,
                                     max_width=8.7, name="l2")
    core.sync_words(sc, objs2)
    lyr3, objs3, w3 = core.add_lyric(sc, "that's no surprise", 0.4, -3.3, "archivo", 0.82,
                                     color=core.sc_x(BONE, 0.75), max_width=8.7, name="l3")
    core.sync_words(sc, objs3)
    for w, ob in objs3:
        core.show_at(ob, 1, False)
    for w, ob in objs2:
        core.show_at(ob, 1, False)
        core.show_at(ob, core.frame_of(sc, 5.5), True)
        core.show_at(ob, core.frame_of(sc, 7.72), False)
    for w, ob in objs3:
        core.show_at(ob, core.frame_of(sc, 7.45), True)

    # PCB reroute on "circuits"
    pcb(sc, 6.1)

    # surprisal readout
    sur = motifs.mono(sc, "−log p", 6.2, -2.25, 0.13, core.sc_x(BONE, 0.5))
    sur2 = core.add_text(sc, "2.31", "mono_med", 0.5, SIG, (6.2, -2.9, 0.1))
    core.show_at(sur, 1, False); core.show_at(sur2, 1, False)
    core.show_at(sur, core.frame_of(sc, 7.8), True)
    core.show_at(sur2, core.frame_of(sc, 7.8), True)
    zero = core.add_text(sc, "0.00", "mono_med", 0.5, core.sc_x(BONE, 0.65), (6.2, -2.9, 0.11))
    core.show_at(zero, 1, False)
    core.show_at(zero, core.frame_of(sc, 8.35), True)
    core.show_at(sur2, core.frame_of(sc, 8.35), False)

    # end: an ink curtain rises and hands off to the loss curve's pen
    curtain = core.add_rect(sc, -9.6, -5.4, 19.2, 10.8, INK, z=30.0, name="curtain")
    curtain.scale = (1, 0.001, 1)
    curtain.keyframe_insert("scale", frame=1)
    curtain.keyframe_insert("scale", frame=core.frame_of(sc, 8.75))
    curtain.scale = (1, 1, 1)
    curtain.keyframe_insert("scale", frame=core.frame_of(sc, 9.01))
    core.set_interp(curtain, "BEZIER", "scale")

    # camera rig: sheet, dive onto the eye, pull back, tremble on "nervous"
    rig = bpy.data.objects.new("camrig", None)
    sc.collection.objects.link(rig)
    cam.parent = rig
    cam.location = (0, 0, 50)

    def rig_key(f, x, y):
        rig.location = (x, y, 0)
        rig.keyframe_insert("location", frame=f)

    def scale_key(f, s):
        cam.data.ortho_scale = s
        cam.data.keyframe_insert("ortho_scale", frame=f)

    rig_key(1, 0, 0); scale_key(1, 19.2)
    rig_key(core.frame_of(sc, 1.4), 0, 0); scale_key(core.frame_of(sc, 1.4), 19.2)
    rig_key(core.frame_of(sc, 4.7), 0, 0); scale_key(core.frame_of(sc, 4.7), 19.2)
    rig_key(core.frame_of(sc, 5.05), -5.95, 2.55); scale_key(core.frame_of(sc, 5.05), 5.4)
    rig_key(core.frame_of(sc, 5.7), -5.95, 2.55); scale_key(core.frame_of(sc, 5.7), 5.4)
    rig_key(core.frame_of(sc, 6.0), 0, 0); scale_key(core.frame_of(sc, 6.0), 19.2)
    rig_key(core.frame_of(sc, 8.6), 0, 0); scale_key(core.frame_of(sc, 8.6), 19.2)
    core.set_interp(rig, "BEZIER", "location")
    for fc in core._fcurves(cam.data):
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.handle_left_type = "AUTO_CLAMPED"
            kp.handle_right_type = "AUTO_CLAMPED"
    # tremble only in its own window (the camera's local offset, on top of the rig)
    for f in range(core.frame_of(sc, 7.0), core.frame_of(sc, 7.78)):
        t = data.frame_to_time(sc.name, f)
        a = 0.010 * math.exp(-(t - 7.0) * 8)
        cam.location = ((hash01(1, f) - 0.5) * 2 * a, (hash01(2, f) - 0.5) * 2 * a, 50)
        cam.keyframe_insert("location", frame=f)
    cam.location = (0, 0, 50)
    cam.keyframe_insert("location", frame=core.frame_of(sc, 7.9))
    core.set_interp(cam, "BEZIER", "location")

    # the spark: the pen, then the horn's streak, then the loss curve's pen at the end
    def pen_path(t):
        return (-6.95, 3.1)
    motifs.spark(sc, pen_path, 4.7, 5.2, 0.11, EMB, z=0.18)
    return sc