"""FUSE — "Too late now, we lit the fuse" / "Orthogonality thesis blues" (102.267-109.994).

Part A: a braided fuse burns across the dark; the lyric sits cleanly above it, word-synced.
Part B: a bone graph-paper sheet with the orthogonality chart in ink; the flat regression line is
strung as a guitar string and bends with the voice on "blues". Camera dives into the spark.
"""
import bpy, math, os, sys
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pdoom import core, data
from pdoom.core import PAL, clamp, lerp, keys, hash01
from pdoom.core import ease_out_expo, ease_out_cubic, ease_in_out_cubic, ease_out_back

INK, BONE, SIG, EMB, GRAPH, ASH, BLOOD = (PAL["ink"], PAL["bone"], PAL["signal"], PAL["ember"],
                                          PAL["graphite"], PAL["ash"], PAL["blood"])
C_INK = (0.010, 0.010, 0.011)
C_MID = (0.055, 0.054, 0.052)
C_FAINT = (0.14, 0.137, 0.132)
C_GRID1 = (0.30, 0.29, 0.275)
C_GRID2 = (0.20, 0.195, 0.185)
C_DIM = (0.45, 0.44, 0.42)


def parent_to(ob, parent):
    ob.parent = parent
    ob.matrix_parent_inverse = Matrix.Identity(4)
    return ob


# ------------------------------------------------------------------ cord
def cord_at(u):
    x = -7.1 + 13.0 * u
    z = 1.28 + 0.30 * math.sin(u * math.pi * 1.18 + 0.25) - 0.22 * u
    return Vector((x, 0.0, z))


def cord_tangent(u):
    a = cord_at(max(0.0, u - 0.002))
    b = cord_at(min(1.0, u + 0.002))
    return (b - a).normalized()


def make_cord(n=280, strands=3, rc=0.060, rr=0.030, turns=26.0):
    verts, faces, arcs = [], [], []
    for s in range(strands):
        pts = []
        for i in range(n):
            u = i / (n - 1)
            c = cord_at(u)
            t = cord_tangent(u)
            yaxis = Vector((0, 1, 0))
            b = t.cross(yaxis).normalized()
            th = math.tau * turns * u + s * math.tau / strands
            pts.append(c + yaxis * (math.cos(th) * rc) + b * (math.sin(th) * rc))
        ring_ids = []
        for i, p in enumerate(pts):
            if i == 0:
                t = (pts[1] - p).normalized()
            elif i == n - 1:
                t = (p - pts[-2]).normalized()
            else:
                t = (pts[i + 1] - pts[i - 1]).normalized()
            side = t.cross(Vector((0, 0, 1)))
            if side.length < 1e-5:
                side = t.cross(Vector((1, 0, 0)))
            side.normalize()
            up2 = side.cross(t).normalized()
            ring = []
            for k in range(8):
                a = k / 8 * math.tau
                v = p + side * (math.cos(a) * rr) + up2 * (math.sin(a) * rr)
                ring.append(len(verts))
                verts.append((v.x, v.y, v.z))
                arcs.append(i / (n - 1))
            ring_ids.append(ring)
        for i in range(n - 1):
            A, B = ring_ids[i], ring_ids[i + 1]
            for k in range(8):
                k2 = (k + 1) % 8
                faces.append((A[k], A[k2], B[k2], B[k]))
    me = bpy.data.meshes.new("cord")
    me.from_pydata(verts, [], faces)
    me.validate()
    for p in me.polygons:
        p.use_smooth = True
    at = me.attributes.new(name="arc", type="FLOAT", domain="POINT")
    at.data.foreach_set("value", arcs)
    return me


def mat_cord():
    m = bpy.data.materials.new("cord")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Metallic"].default_value = 0.30
    bsdf.inputs["Roughness"].default_value = 0.50
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_name = "arc"
    burn = nt.nodes.new("ShaderNodeValue")
    burn.name = "burn"
    sub = nt.nodes.new("ShaderNodeMath")
    sub.operation = "SUBTRACT"
    nt.links.new(burn.outputs[0], sub.inputs[0])
    nt.links.new(attr.outputs["Fac"], sub.inputs[1])
    burnt = nt.nodes.new("ShaderNodeMapRange")
    burnt.inputs[1].default_value = -0.018
    burnt.inputs[2].default_value = 0.006
    burnt.inputs[3].default_value = 0.0
    burnt.inputs[4].default_value = 1.0
    nt.links.new(sub.outputs[0], burnt.inputs[0])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs[6].default_value = (*core.sc_x(BONE, 0.52), 1)
    mix.inputs[7].default_value = (0.012, 0.011, 0.011, 1)
    nt.links.new(burnt.outputs[0], mix.inputs[0])
    nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    rough = nt.nodes.new("ShaderNodeMix")
    rough.data_type = "FLOAT"
    rough.inputs[2].default_value = 0.42
    rough.inputs[3].default_value = 0.9
    nt.links.new(burnt.outputs[0], rough.inputs[0])
    nt.links.new(rough.outputs[0], bsdf.inputs["Roughness"])
    ab = nt.nodes.new("ShaderNodeMath")
    ab.operation = "ABSOLUTE"
    nt.links.new(sub.outputs[0], ab.inputs[0])
    ember = nt.nodes.new("ShaderNodeMapRange")
    ember.inputs[1].default_value = 0.0
    ember.inputs[2].default_value = 0.026
    ember.inputs[3].default_value = 1.0
    ember.inputs[4].default_value = 0.0
    nt.links.new(ab.outputs[0], ember.inputs[0])
    emul = nt.nodes.new("ShaderNodeMath")
    emul.operation = "MULTIPLY"
    emul.inputs[1].default_value = 3.0
    nt.links.new(ember.outputs[0], emul.inputs[0])
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[0].default_value = (*EMB, 1)
    nt.links.new(emul.outputs[0], em.inputs["Strength"])
    add = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(bsdf.outputs[0], add.inputs[0])
    nt.links.new(em.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs["Surface"])
    return m


def add_em(sc, body, font, size, color, x, y, z=0.02, align="LEFT", parent=None, name="t", spacing=1.0):
    ob = core.add_text(sc, body, font, size, color, (x, y, z), align_x=align, name=name, spacing=spacing)
    if parent is not None:
        parent_to(ob, parent)
    return ob


def ln(sc, pts, width, color, z=0.01, parent=None, name="ln"):
    ob = core.add_polyline(sc, [(p[0], p[1], z) for p in pts], width, color, name=name)
    if parent is not None:
        parent_to(ob, parent)
    return ob


def build(name):
    sc = core.new_scene(name, samples=32, motion_blur=True)
    sc.frame_set(1)
    cam = core.add_camera_persp(sc, (0, -9.8, 2.7), (0, 0, 1.2), lens=40)
    cam.data.sensor_width = 36.0
    cam.data.dof.use_dof = False
    cam.data.clip_start = 0.02

    # ============================================================ PART A
    me = make_cord()
    cord = bpy.data.objects.new("cord", me)
    sc.collection.objects.link(cord)
    cmat = mat_cord()
    me.materials.append(cmat)
    burn_node = cmat.node_tree.nodes["burn"]
    keyA = core.add_light(sc, "AREA", (0.0, -6.0, 4.5), 420, BONE, size=7.0, name="keyA")
    core.look_at(keyA, (0, 0, 1.1))
    burnlight = core.add_light(sc, "POINT", (0, 0, 1), 260, EMB, size=0.30, name="burnlight")
    spark_a = core.add_uv_sphere(sc, (0, 0, 1), 0.075, EMB, hot=True, name="sparkA", segs=14, rings=10)

    lA = data.line("Too late")
    wordsA = lA["words"]
    total_txt = core.measure(sc, lA["text"], "archivo500", 1.0)
    # lyric in camera space, upper left, always readable
    sizeA = min(0.150, 1.36 / total_txt)
    swA = core.space_width(sc, "archivo500", sizeA)
    lx = -0.66
    ly = 0.315
    w_objs = []
    cursor = lx
    for i, w in enumerate(wordsA):
        ob = core.add_text(sc, w["w"], "archivo500", sizeA, core.sc_x(BONE, 0.24),
                           (cursor, ly, -2.0), name=f"lyA{i}")
        parent_to(ob, cam)
        w_objs.append((w, ob))
        cursor += core.measure(sc, w["w"], "archivo500", sizeA) + swA
    core.animate_words(sc, w_objs, sung=BONE, dim=core.sc_x(BONE, 0.22), pre=0.18)
    ruleA = core.add_polyline(sc, [(lx, ly - 0.045), (cursor - swA, ly - 0.045)], 0.0012,
                              core.sc_x(BONE, 0.30), name="ruleA")
    parent_to(ruleA, cam)
    mobj = core.add_text(sc, "P(doom) " + data.pdoom_text(104.0), "mono_med", 0.022,
                         SIG, (0.68, 0.315, -2.0), align_x="RIGHT", name="pdA")
    parent_to(mobj, cam)

    def u_of_text_x(x):
        return 0.03 + (x / total_txt) * 0.91

    prefix = ""
    word_spans = []
    for w in wordsA:
        wx0 = core.measure(sc, prefix, "archivo500", sizeA) / sizeA
        wx1 = wx0 + core.measure(sc, w["w"], "archivo500", sizeA) / sizeA
        word_spans.append((u_of_text_x(wx0), u_of_text_x(wx1)))
        prefix += w["w"] + " "

    def burn_at(t):
        if t <= wordsA[0]["start"]:
            return lerp(0.0, word_spans[0][0], clamp((t - 102.25) / max(0.01, wordsA[0]["start"] - 102.25)))
        for i, w in enumerate(wordsA):
            if t <= w["end"]:
                p = clamp((t - w["start"]) / max(1e-5, w["end"] - w["start"]))
                return lerp(word_spans[i][0], word_spans[i][1], p)
            if i + 1 < len(wordsA) and t < wordsA[i + 1]["start"]:
                p = clamp((t - w["end"]) / max(1e-5, wordsA[i + 1]["start"] - w["end"]))
                return lerp(word_spans[i][1], word_spans[i + 1][0], p)
        return clamp(lerp(word_spans[-1][1], 1.0, (t - wordsA[-1]["end"]) / 0.3))

    fA_end = core.frame_of(sc, 105.88)
    for f in range(1, fA_end + 1):
        t = data.frame_to_time(sc.name, f)
        bfront = burn_at(t) if t >= 102.26 else 0.0
        burn_node.outputs[0].default_value = bfront
        burn_node.outputs[0].keyframe_insert("default_value", frame=f)
        p = cord_at(bfront)
        spark_a.location = (p.x, -0.02, p.z + 0.02)
        spark_a.keyframe_insert("location", frame=f)
        burnlight.location = (p.x, -0.24, p.z + 0.10)
        burnlight.data.energy = 220 + 130 * data.env("vocal", t)
        burnlight.data.keyframe_insert("energy", frame=f)
    core.set_interp(spark_a, "LINEAR", "location")

    # ember flecks
    flecks = []
    for i in range(12):
        ob = core.add_uv_sphere(sc, (0, 0, 1), 0.014 + hash01(i, 2) * 0.012, EMB, hot=True,
                                name=f"flk{i}", segs=6, rings=4)
        flecks.append(ob)
    for i, ob in enumerate(flecks):
        for f in range(1, fA_end + 1, 2):
            t = data.frame_to_time(sc.name, f)
            bfront = burn_at(t) if t >= 102.26 else 0.0
            p = cord_at(max(0.0, bfront - 0.004 - hash01(i, 3) * 0.016))
            age = (t * (7 + i)) % 0.7
            ob.location = (p.x + (hash01(i, 4) - 0.5) * 0.22 * age,
                           -0.05 - 0.06 * age,
                           p.z + 0.05 + (hash01(i, 5) - 0.2) * 0.18 - 0.10 * age * age)
            ob.keyframe_insert("location", frame=f)
        core.set_interp(ob, "LINEAR", "location")
        core.show_at(ob, 1, True)
        core.show_at(ob, fA_end, False)

    def camera_a_at(t):
        bf = burn_at(t) if t >= 102.26 else 0.0
        p = cord_at(bf)
        tx = clamp(p.x + 1.1, -6.0, 5.5)
        push = ease_in_out_cubic(clamp((t - 104.25) / 1.55))
        y = lerp(-9.8, -6.0, push)
        z = lerp(2.7, 2.0, push)
        lens = 40.0
        return (tx, y, z), (tx + 0.35, 0.0, lerp(1.22, 1.02, push)), lens

    # ============================================================ PART B
    chart = bpy.data.objects.new("chart", None)
    sc.collection.objects.link(chart)
    chart.empty_display_size = 0.3
    chart.rotation_euler = (math.radians(90.0), 0, 0)
    chart.location = (0, 0, 0)

    paper = core.add_rect(sc, -8.0, -5.1, 16.0, 10.2, INK, z=-0.03, name="paper")
    parent_to(paper, chart)
    pm = bpy.data.materials.new("papercream")
    pm.use_nodes = True
    nt = pm.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[1].default_value = 1.0
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sub = nt.nodes.new("ShaderNodeVectorMath")
    sub.operation = "SUBTRACT"
    sub.inputs[1].default_value = (6.2, -0.5, 0.0)
    nt.links.new(tc.outputs["Object"], sub.inputs[0])
    lng = nt.nodes.new("ShaderNodeVectorMath")
    lng.operation = "LENGTH"
    nt.links.new(sub.outputs[0], lng.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs[1].default_value = 0.0
    mr.inputs[2].default_value = 13.0
    mr.inputs[3].default_value = 1.0
    mr.inputs[4].default_value = 0.0
    nt.links.new(lng.outputs["Value"], mr.inputs[0])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs[6].default_value = (0.74, 0.705, 0.635, 1)
    mix.inputs[7].default_value = (0.86, 0.71, 0.55, 1)
    nt.links.new(mr.outputs[0], mix.inputs[0])
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 240.0
    noise.inputs["Detail"].default_value = 3.0
    grain = nt.nodes.new("ShaderNodeMix")
    grain.data_type = "RGBA"
    grain.inputs[7].default_value = (0.66, 0.63, 0.57, 1)
    gm = nt.nodes.new("ShaderNodeMath")
    gm.operation = "MULTIPLY"
    gm.inputs[1].default_value = 0.12
    nt.links.new(noise.outputs["Fac"], gm.inputs[0])
    nt.links.new(mix.outputs[2], grain.inputs[6])
    nt.links.new(gm.outputs[0], grain.inputs[0])
    nt.links.new(grain.outputs[2], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    pm_scrap = core.mat_emit((0.76, 0.725, 0.65), 1.0)
    paper.data.materials.clear()
    paper.data.materials.append(pm)
    back = core.add_rect(sc, -8.08, -5.2, 16.0, 10.2, INK, z=-0.07, name="paperback")
    parent_to(back, chart)
    back.data.materials.clear()
    back.data.materials.append(core.mat_emit((0.0, 0.0, 0.0), 1.0))

    keyB = core.add_light(sc, "AREA", (3.0, -8.0, 6.0), 0, BONE, size=8.0, name="keyB")
    core.look_at(keyB, (0, 0, 0))
    fillB = core.add_light(sc, "AREA", (-7.0, -6.0, 2.0), 0, core.sc_x(BONE, 0.9), size=6.0, name="fillB")
    core.look_at(fillB, (0, 0, 0))
    sparkB = core.add_uv_sphere(sc, (6.2, -0.12, -0.5), 0.060, EMB, hot=True, name="sparkB", segs=16, rings=10)
    sparkcore = core.add_uv_sphere(sc, (6.2, -0.16, -0.5), 0.024, (1.0, 0.82, 0.55), hot=True, name="sparkcore", segs=12, rings=8)
    sparklight = core.add_light(sc, "POINT", (6.2, -0.55, -0.5), 0, EMB, size=0.5, name="sparklight")

    # grid
    minor, major = [], []
    x = -8.0
    while x <= 8.01:
        tgt = major if abs((x / 2.0) - round(x / 2.0)) < 1e-6 else minor
        tgt.append(((x, -5.0), (x, 5.0)))
        x += 0.5
    y = -5.0
    while y <= 5.01:
        tgt = major if abs((y / 2.0) - round(y / 2.0)) < 1e-6 else minor
        tgt.append(((-8.0, y), (8.0, y)))
        y += 0.5
    g1 = core.add_segments(sc, minor, 0.0045, C_GRID1, name="gridmin")
    parent_to(g1, chart)
    g2 = core.add_segments(sc, major, 0.0080, C_GRID2, name="gridmaj")
    parent_to(g2, chart)

    AX0, AY0 = -6.35, -3.25
    ln(sc, [(AX0, AY0), (7.1, AY0)], 0.011, C_INK, z=0.03, parent=chart)
    ln(sc, [(7.10, AY0), (6.92, AY0 + 0.14)], 0.011, C_INK, z=0.03, parent=chart)
    ln(sc, [(7.10, AY0), (6.92, AY0 - 0.14)], 0.011, C_INK, z=0.03, parent=chart)
    ln(sc, [(AX0, AY0), (AX0, 4.1)], 0.011, C_INK, z=0.03, parent=chart)
    ln(sc, [(AX0, 4.10), (AX0 - 0.14, 3.92)], 0.011, C_INK, z=0.03, parent=chart)
    ln(sc, [(AX0, 4.10), (AX0 + 0.14, 3.92)], 0.011, C_INK, z=0.03, parent=chart)
    ticks = []
    for i in range(1, 21):
        xx = AX0 + i * 0.62
        if xx < 6.9:
            ticks.append(((xx, AY0), (xx, AY0 + 0.07)))
    for i in range(1, 11):
        yy = AY0 + i * 0.62
        if yy < 3.95:
            ticks.append(((AX0, yy), (AX0 - 0.07, yy)))
    tk = core.add_segments(sc, ticks, 0.006, C_MID, name="ticks")
    parent_to(tk, chart)

    add_em(sc, "INTELLIGENCE \u2192", "mono_med", 0.19, C_MID, 5.35, AY0 - 0.34, 0.03, "LEFT", chart, "lab_x", 1.08)
    add_em(sc, "GOALS \u2191", "mono_med", 0.19, C_MID, AX0 + 0.22, 3.93, 0.03, "LEFT", chart, "lab_y", 1.08)
    add_em(sc, "THE ORTHOGONALITY THESIS", "mono_med", 0.22, C_MID, -7.75, 4.32, 0.03, "LEFT", chart, "title", 1.12)
    add_em(sc, "P(doom) " + data.pdoom_text(107.0), "mono_med", 0.22, SIG, 7.7, 4.32, 0.03, "RIGHT", chart, "pd", 1.06)
    add_em(sc, "r = 0.00", "mono_med", 0.22, C_INK, 5.75, -0.88, 0.03, "LEFT", chart, "rval", 1.04)
    add_em(sc, "n = 14", "mono_med", 0.14, C_MID, 6.75, -1.15, 0.03, "RIGHT", chart, "nval")
    add_em(sc, "Any level of intelligence, any final goal.", "serif_italic", 0.36, C_MID, -7.55, -4.52, 0.03, "LEFT", chart, "foot")

    pts = [
        (-4.9, 2.9, "a rock", 2, -1, 1),
        (-3.4, 1.7, "Moloch", 1, 1, 1),
        (-1.9, 3.3, "the board", 3, 0, 1),
        (-0.4, 0.8, "GPT-6", 0, 1, 1),
        (1.3, 2.4, "Sydney", 0, -1, 1),
        (2.9, 1.2, "paperclip maximizer", 1, 1, 1),
        (4.5, 3.1, "your ex", 2, 0, 1),
        (5.9, 1.9, "a very good boy", 0, -1, 1),
        (-4.2, -0.9, "the Loom", 3, -1, 1),
        (-2.6, -2.1, "shoggoth", 1, 1, 1),
        (0.4, -1.6, "RLHF", 2, 1, 1),
        (2.2, -2.3, "toolformer", 0, 1, 1),
        (4.1, -1.5, "P(doom) 0.99", 1, -1, 1),
        (5.3, -2.6, "safety team", 3, -1, 1),
    ]
    for i, (px, py, lab, kind, dx, dy) in enumerate(pts):
        col = C_MID
        if kind == 0:
            d = core.add_disc(sc, px, py, 0.052, col, z=0.04, segments=20)
            parent_to(d, chart)
        elif kind == 1:
            rr = 0.075
            pp = [(px + math.cos(a / 20 * math.tau) * rr, py + math.sin(a / 20 * math.tau) * rr) for a in range(21)]
            ln(sc, pp, 0.007, col, z=0.04, parent=chart)
        elif kind == 2:
            ln(sc, [(px - 0.06, py - 0.06), (px + 0.06, py + 0.06)], 0.008, col, z=0.04, parent=chart)
            ln(sc, [(px + 0.06, py - 0.06), (px - 0.06, py + 0.06)], 0.008, col, z=0.04, parent=chart)
        else:
            ln(sc, [(px - 0.06, py - 0.06), (px + 0.06, py - 0.06), (px + 0.06, py + 0.06),
                    (px - 0.06, py + 0.06), (px - 0.06, py - 0.06)], 0.007, col, z=0.04, parent=chart)
        lx = px + 0.16 * dx
        ly = py + 0.14 * dy
        ln(sc, [(px + 0.07 * dx, py + 0.05 * dy), (lx - 0.04 * dx, ly - 0.02)], 0.004, C_FAINT, z=0.035, parent=chart)
        add_em(sc, lab, "mono", 0.13, C_MID, lx, ly - 0.03, 0.04, "RIGHT" if dx < 0 else "LEFT", chart, f"sc{i}", 0.98)

    # lyric "Orthogonality thesis" along the bottom
    lB = data.line("Orthogonality")
    lyr_size = 0.95
    o1 = add_em(sc, "Orthogonality", "archivo700", lyr_size, C_DIM, -6.05, AY0 - 0.60, 0.05, "LEFT", chart, "lyr1")
    w1 = core.measure(sc, "Orthogonality", "archivo700", lyr_size)
    o2 = add_em(sc, "thesis", "archivo700", lyr_size, C_DIM, -6.05 + w1 + 0.42, AY0 - 0.60, 0.05, "LEFT", chart, "lyr2")
    o1w = lB["words"][0]
    o2w = lB["words"][1]
    btw = lB["words"][2]
    for ob, w in [(o1, o1w), (o2, o2w)]:
        core.color_at(ob, 1, C_DIM)
        core.color_at(ob, core.frame_of(sc, w["start"] - 0.12), C_DIM)
        core.color_at(ob, core.frame_of(sc, w["start"]), C_INK)
        core.set_interp(ob, "BEZIER", "color")

    # regression line + string
    reg = []
    x = -5.9
    while x < 6.25:
        reg.append(((x, -0.5), (min(x + 0.16, 6.25), -0.5)))
        x += 0.30
    regl = core.add_segments(sc, reg, 0.009, C_MID, name="regress")
    parent_to(regl, chart)
    core.show_at(regl, 1, False)
    core.show_at(regl, core.frame_of(sc, 105.9), True)
    core.show_at(regl, core.frame_of(sc, 107.44), False)

    SX0, SX1, SY = -5.9, 6.25, -0.5
    NS = 90
    verts = []
    for i in range(NS + 1):
        u = i / NS
        x = lerp(SX0, SX1, u)
        verts.append((x, SY - 0.030, 0.06))
        verts.append((x, SY + 0.030, 0.06))
    faces = []
    for i in range(NS):
        a = 2 * i
        faces.append((a, a + 2, a + 3, a + 1))
    sme = bpy.data.meshes.new("string")
    sme.from_pydata(verts, [], faces)
    sme.validate()
    sob = bpy.data.objects.new("string", sme)
    sc.collection.objects.link(sob)
    parent_to(sob, chart)
    smat = core.mat_type()
    sme.materials.append(smat)
    sob.color = (*C_INK, 1)
    core.color_at(sob, 1, C_INK)
    core.color_at(sob, core.frame_of(sc, 107.44), C_INK)
    core.color_at(sob, core.frame_of(sc, 107.46), SIG)
    core.color_at(sob, core.frame_of(sc, 108.60), core.mixc(SIG, C_INK, 0.25))
    core.set_interp(sob, "BEZIER", "color")
    sob.shape_key_add(name="Basis")
    kb = sob.shape_key_add(name="bend")
    kv = sob.shape_key_add(name="vib")
    kb.slider_min = -2.0; kb.slider_max = 2.0
    kv.slider_min = -2.0; kv.slider_max = 2.0
    for i in range(NS + 1):
        u = i / NS
        for j in (0, 1):
            idx = 2 * i + j
            kb.data[idx].co.y += 1.25 * math.sin(math.pi * u)
            kv.data[idx].co.y += 0.16 * math.sin(3 * math.pi * u)
    for ax in (SX0, SX1):
        an = core.add_rect(sc, ax - 0.05, SY - 0.17, 0.10, 0.34, C_INK, z=0.05, name="anchor")
        parent_to(an, chart)
        core.show_at(an, 1, False)
        core.show_at(an, core.frame_of(sc, 107.44), True)

    # blues riding the string
    bluesF = "archivo"
    bluesSize = 0.82
    bluesX = 1.65
    blues = []
    bpref = ""
    for i, ch in enumerate("BLUES"):
        bx = bluesX + core.measure(sc, bpref, bluesF, bluesSize)
        ob = add_em(sc, ch, bluesF, bluesSize, C_DIM, bx, SY + 0.06, 0.10, "LEFT", chart, f"blues{i}")
        blues.append((ob, bx, ch))
        bpref += ch
    for ob, bx, ch in blues:
        core.color_at(ob, 1, C_DIM)
        core.color_at(ob, core.frame_of(sc, btw["start"] - 0.12), C_DIM)
        core.color_at(ob, core.frame_of(sc, btw["start"]), (1.0, 0.22, 0.04))
        core.color_at(ob, core.frame_of(sc, btw["start"] + 0.2), SIG)
        core.set_interp(ob, "BEZIER", "color")

    # staff scrap
    scrap = bpy.data.objects.new("scrap", None)
    sc.collection.objects.link(scrap)
    parent_to(scrap, chart)
    scrap.location = (4.55, -3.82, 0.42)
    scrap.rotation_euler = (0, 0, math.radians(-7))
    scrap.empty_display_size = 0.2
    scrap_shadow = core.add_rect(sc, 4.45, -3.92, 2.5, 1.7, INK, z=0.02, name="scrapshadow")
    parent_to(scrap_shadow, chart)
    scrap_shadow.rotation_euler = (0, 0, math.radians(-7))
    scrap_shadow.data.materials.clear()
    scrap_shadow.data.materials.append(core.mat_emit((0.0, 0.0, 0.0), 1.0))
    scrap_paper = core.add_rect(sc, -1.25, -0.85, 2.5, 1.7, INK, z=0.0, name="scrappaper")
    parent_to(scrap_paper, scrap)
    scrap_paper.data.materials.clear()
    scrap_paper.data.materials.append(pm_scrap)
    border = core.add_outline_rect(sc, -1.25, -0.85, 2.5, 1.7, 0.006, C_MID, z=0.003, name="scrapborder")
    parent_to(border, scrap)
    staves = []
    for i in range(5):
        yy = -0.05 - i * 0.12
        staves.append(((-1.10, yy), (1.10, yy)))
    st = core.add_segments(sc, staves, 0.005, C_MID, name="staff")
    parent_to(st, scrap)
    note = core.add_disc(sc, 0.13, -0.05 - 2 * 0.12, 0.075, EMB, z=0.006, segments=24, name="note")
    parent_to(note, scrap)
    stem = core.add_rect(sc, 0.195, -0.05 - 2 * 0.12, 0.022, 0.52, EMB, z=0.006, name="stem")
    parent_to(stem, scrap)
    flat = add_em(sc, "\u266d", "serif", 0.42, EMB, -0.85, -0.05 - 2 * 0.12, 0.007, "LEFT", scrap, "flat")
    bn = add_em(sc, "the blue note", "mono", 0.10, C_MID, -1.10, -0.80, 0.007, "LEFT", scrap, "bn", 0.98)
    pin = core.add_uv_sphere(sc, (-0.95, 0.62, 0.06), 0.045, core.sc_x(ASH, 0.8), name="pin", segs=10, rings=8)
    parent_to(pin, scrap)
    scrap_children = [scrap_paper, border, st, note, stem, flat, bn, pin]

    # string / blues motion
    f_start = core.frame_of(sc, 105.9)
    for f in range(f_start, sc.frame_end + 1):
        t = data.frame_to_time(sc.name, f)
        if t < btw["start"]:
            bend = 0.0
            vib = 0.0
        else:
            k = ease_out_cubic(clamp((t - btw["start"]) / 0.16))
            vib_amp = data.env("vocal", t)
            vib = math.sin((t - btw["start"]) * math.tau * 5.4) * 0.45 * vib_amp * k
            bend = 0.48 * k + vib
            if t > btw["end"] + 0.05:
                k2 = clamp((t - btw["end"] - 0.05) / 0.6)
                bend = (0.48 + vib) * (1 - k2) + vib * 0.2 * (1 - k2)
        kb.value = bend
        kv.value = vib * 1.2
        kb.keyframe_insert("value", frame=f)
        kv.keyframe_insert("value", frame=f)
        for ob, bx, ch in blues:
            u = clamp((bx + 0.14 - SX0) / (SX1 - SX0))
            yy = SY + (1.25 * bend + 0.16 * kv.value * math.sin(3 * math.pi * u)) * math.sin(math.pi * u)
            ob.location = (bx, yy + 0.06, 0.10)
            ob.keyframe_insert("location", frame=f)
        if t >= 107.42:
            k = ease_out_back(clamp((t - 107.42) / 0.28), 1.4)
            scrap.scale = (max(0.01, k), max(0.01, k), 1)
            scrap.keyframe_insert("scale", frame=f)
    for ob, bx, ch in blues:
        core.set_interp(ob, "LINEAR", "location")
    core.set_interp(sob, "BEZIER", "color")

    # camera B
    PB = [
        (105.900, (0.0, -18.5, 0.6), (0.0, 0.0, 0.10), 38.0),
        (106.40, (-0.5, -18.2, 0.55), (-0.2, 0.0, 0.15), 38.0),
        (107.10, (0.4, -17.6, 0.50), (0.3, 0.0, 0.10), 39.0),
        (107.48, (1.2, -16.6, 0.40), (1.0, 0.0, -0.05), 40.0),
        (108.10, (2.7, -8.4, 0.05), (3.1, 0.0, -0.24), 52.0),
        (108.45, (2.9, -7.6, 0.00), (3.3, 0.0, -0.26), 54.0),
        (108.80, (1.2, -13.5, 0.20), (1.2, 0.0, -0.40), 44.0),
        (109.20, (3.6, -9.0, 0.00), (5.2, 0.0, -0.45), 48.0),
        (109.60, (5.9, -3.0, -0.45), (6.2, 0.0, -0.50), 50.0),
        (109.994, (6.2, -1.25, -0.50), (6.2, 0.0, -0.50), 50.0),
    ]

    def camera_b_at(t):
        for i in range(len(PB) - 1):
            if t <= PB[i + 1][0]:
                k = ease_in_out_cubic(clamp((t - PB[i][0]) / (PB[i + 1][0] - PB[i][0])))
                a, b = PB[i], PB[i + 1]
                return (tuple(lerp(a[1][j], b[1][j], k) for j in range(3)),
                        tuple(lerp(a[2][j], b[2][j], k) for j in range(3)),
                        lerp(a[3], b[3], k))
        return PB[-1][1], PB[-1][2], PB[-1][3]

    f_cut = core.frame_of(sc, 105.88)
    # visibility: part A then chart
    for ob in [cord, spark_a, burnlight, keyA] + flecks + [o for w, o in w_objs] + [ruleA, mobj]:
        core.show_at(ob, 1, True)
        core.show_at(ob, f_cut, False)
    # collect chart children after all creation below (see end)

    # chart camera bake and part A camera
    for f in range(1, sc.frame_end + 1):
        t = data.frame_to_time(sc.name, f)
        if t < 105.88:
            p, tg, lens = camera_a_at(t)
        else:
            p, tg, lens = camera_b_at(t)
        cam.location = p
        core.look_at(cam, tg)
        cam.rotation_euler.rotate_axis("Z", 0.006 if t < 105.88 else 0.0)
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
        cam.data.lens = lens
        cam.data.keyframe_insert("lens", frame=f)
    core.set_interp(cam, "LINEAR", "location")
    core.set_interp(cam, "LINEAR", "rotation_euler")

    # chart is self-lit graphic paper; no lamp pass needed

    # the final axis + flash
    axis = ln(sc, [(6.2, -5.0), (6.2, 5.0)], 0.012, C_INK, z=0.08, parent=chart)
    core.show_at(axis, 1, False)
    core.show_at(axis, core.frame_of(sc, 109.55), True)
    core.color_at(axis, 1, C_INK)
    core.color_at(axis, core.frame_of(sc, 109.68), C_INK)
    core.color_at(axis, core.frame_of(sc, 109.72), BONE)
    core.set_interp(axis, "BEZIER", "color")
    flash = core.add_uv_sphere(sc, (6.2, -0.4, -0.5), 0.05, EMB, hot=True, name="flash", segs=16, rings=10)
    core.show_at(flash, 1, False)
    core.show_at(flash, core.frame_of(sc, 109.92), True)
    flash.scale = (1, 1, 1)
    flash.keyframe_insert("scale", frame=core.frame_of(sc, 109.92))
    flash.scale = (2.0, 2.0, 2.0)
    flash.keyframe_insert("scale", frame=sc.frame_end)
    core.set_interp(flash, "BEZIER", "scale")

    # chart visibility (after everything exists)
    for ob in sc.objects:
        if ob.parent == chart and ob not in (scrap_shadow, axis):
            core.show_at(ob, 1, False)
            core.show_at(ob, f_cut, True)
    for ob in scrap_children + [scrap_shadow]:
        core.show_at(ob, 1, False)
        core.show_at(ob, core.frame_of(sc, 107.42), True)
    for ob in sc.objects:
        if ob.parent == scrap:
            core.show_at(ob, 1, False)
            core.show_at(ob, core.frame_of(sc, 107.42), True)
    # the final dive: paper and chart fall into darkness, the spark and its axis remain
    for ob in sc.objects:
        if ob.parent == chart and ob not in (sparkB, sparkcore, axis):
            core.show_at(ob, core.frame_of(sc, 109.70), False)
    for ob in scrap_children + [scrap_shadow]:
        core.show_at(ob, core.frame_of(sc, 109.70), False)

    print("BUILD fuse ok")
    return sc