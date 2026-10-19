"""STACK — "Just transformers all the way!" / "Till you learned to disobey" (109.994-114.994).

An endless vertical shaft of transformer blocks drawn as technical line diagrams. The camera
falls one block per phrase and lands dead on "disobey"; that block swings out of alignment and
the word lights right-to-left and slides the wrong way.
"""
import bpy, math, os, sys
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pdoom import core, data
from pdoom.core import PAL, clamp, lerp, keys, hash01
from pdoom.core import ease_out_expo, ease_in_out_cubic, ease_out_cubic, ease_in_expo

INK, BONE, SIG, EMB, GRAPH, ASH, BLOOD = (PAL["ink"], PAL["bone"], PAL["signal"], PAL["ember"],
                                          PAL["graphite"], PAL["ash"], PAL["blood"])
DIM = core.sc_x(BONE, 0.15)
P = 7.2
HW, HH, HZ = 6.0, 2.6, 1.3


def parent_to(ob, parent):
    ob.parent = parent
    ob.matrix_parent_inverse = Matrix.Identity(4)
    return ob


def mat_fog_emit(name, fog0=20.0, fog1=72.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    oi = nt.nodes.new("ShaderNodeObjectInfo")
    cd = nt.nodes.new("ShaderNodeCameraData")
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs[1].default_value = fog0
    mr.inputs[2].default_value = fog1
    mr.inputs[3].default_value = 0.0
    mr.inputs[4].default_value = 1.0
    nt.links.new(cd.outputs["View Z Depth"], mr.inputs[0])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs[7].default_value = (*INK, 1)
    nt.links.new(oi.outputs["Color"], mix.inputs[6])
    nt.links.new(mr.outputs[0], mix.inputs[0])
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(mix.outputs[2], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def look_cam(cam, pos, target, roll=0.0):
    f = (Vector(target) - Vector(pos)).normalized()
    up0 = Vector((0.0, 1.0, 0.0))
    up = (up0 - f * up0.dot(f)).normalized()
    right = up.cross(-f).normalized()
    M = Matrix((right, up, -f)).transposed().to_4x4()
    if abs(roll) > 1e-9:
        M = Matrix.Rotation(roll, 4, f) @ M
    cam.matrix_world = Matrix.Translation(Vector(pos)) @ M


def add_segs3d(sc, segs, width, color, material, name="segs3d"):
    cu = bpy.data.curves.new(name, type="CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = max(width * 0.5, 0.0002)
    cu.bevel_resolution = 0
    for a, b in segs:
        sp = cu.splines.new("POLY")
        sp.points.add(1)
        sp.points[0].co = (a[0], a[1], a[2], 1)
        sp.points[1].co = (b[0], b[1], b[2], 1)
    cu.materials.append(material)
    ob = sc.collection.objects.link(bpy.data.objects.new(name, cu))
    ob = bpy.data.objects[name]
    ob.color = (*color, 1.0)
    return ob


def block_segs():
    """Technical linework for one transformer block, local coords. Front face z=HZ+0.012,
    side face x=HW+0.012."""
    S = []
    z = HZ + 0.012
    def s(a, b, zz=z):
        S.append(((a[0], a[1], zz), (b[0], b[1], zz)))
    # chamfered front border
    c = 0.34
    pts = [(-HW + c, -HH), (HW - c, -HH), (HW, -HH + c), (HW, HH - c), (HW - c, HH),
           (-HW + c, HH), (-HW, HH - c), (-HW, -HH + c), (-HW + c, -HH)]
    for i in range(len(pts) - 1):
        s(pts[i], pts[i + 1])
    # inner hairline
    for xy in [(-HW + 0.26, -HH + 0.26), (HW - 0.26, HH - 0.26)]:
        pass
    inner = [(-HW + 0.26, -HH + 0.26), (HW - 0.26, -HH + 0.26), (HW - 0.26, HH - 0.26), (-HW + 0.26, HH - 0.26), (-HW + 0.26, -HH + 0.26)]
    for i in range(len(inner) - 1):
        s(inner[i], inner[i + 1])
    # layer stack boxes (faint, behind the word)
    boxes = [(-2.1, -1.1), (-0.82, -0.34), (0.24, 1.16), (1.56, 2.02)]
    for (y0, y1) in boxes:
        bx0, bx1 = -1.55, 1.55
        for i in range(4):
            p = [(bx0, y0), (bx1, y0), (bx1, y1), (bx0, y1), (bx0, y0)][i:i + 2]
            s(p[0], p[1])
        # doubled head outline
        s((bx0 + 0.12, y1 + 0.10), (bx1 + 0.12, y1 + 0.10))
        s((bx1 + 0.12, y1 + 0.10), (bx1 + 0.12, y0 + 0.10))
    # main path + arrows (through the boxes)
    s((0, -HH, z), (0, -2.45), z)
    s((0, 2.35), (0, HH), z)
    for yy in (-2.45, -1.1, -0.34, 1.16, 2.02, 2.35):
        s((0, yy), (0, yy + 0.10))
        s((0, yy + 0.10), (-0.06, yy + 0.02))
        s((0, yy + 0.10), (0.06, yy + 0.02))
    # residual bypass on the left
    s((0, -2.45), (-3.55, -2.45))
    s((-3.55, -2.45), (-3.55, -0.58))
    s((-3.55, -0.58), (-1.55, -0.58))
    s((0, -0.10), (-3.55, -0.10))
    s((-3.55, -0.10), (-3.55, 1.80))
    s((-3.55, 1.80), (-1.55, 1.80))
    for yy in (-0.58, 1.80):
        circ = []
        for i in range(17):
            a = i / 16 * math.tau
            circ.append((-3.55 + math.cos(a) * 0.16, yy + math.sin(a) * 0.16))
        for i in range(16):
            s(circ[i], circ[i + 1])
        s((-3.70, yy), (-3.40, yy))
        s((-3.55, yy - 0.15), (-3.55, yy + 0.15))
    # junction dots
    for yy in (-2.45, -0.10):
        s((-0.05, yy), (0.05, yy))
        s((0, yy - 0.05), (0, yy + 0.05))
    # right-hand spec column ticks
    for i in range(7):
        yy = -2.2 + i * 0.72
        s((4.55, yy), (4.85, yy))
    # registration crosses
    for (xx, yy) in [(-HW + 0.75, -HH + 0.62), (HW - 0.75, -HH + 0.62), (HW - 0.75, HH - 0.62)]:
        s((xx - 0.14, yy), (xx + 0.14, yy))
        s((xx, yy - 0.14), (xx, yy + 0.14))
    # dimension bracket
    s((HW + 0.45, -HH), (HW + 0.45, HH))
    s((HW + 0.30, -HH), (HW + 0.60, -HH))
    s((HW + 0.30, HH), (HW + 0.60, HH))
    # side face lamination (visible at 3/4)
    xz = HW + 0.012
    for i in range(9):
        yy = -HH + i * 0.65
        S.append(((xz, yy, HZ), (xz, yy, -HZ)))
    for i in range(1, 6):
        zz = -HZ + i * (2 * HZ / 6)
        S.append(((xz, -HH, zz), (xz, HH, zz)))
    # back edge
    S.append(((-HW, -HH, -HZ), (HW, -HH, -HZ)))
    S.append(((HW, -HH, -HZ), (HW, HH, -HZ)))
    return S


def build(name):
    sc = core.new_scene(name, samples=32, motion_blur=True)
    sc.frame_set(1)
    cam = core.add_camera_persp(sc, (8.8, 1.9, 15.6), (0, 0, 0.2), lens=35)
    cam.data.sensor_width = 36.0
    cam.data.clip_start = 0.05
    cam.data.dof.use_dof = False
    core.add_bg(sc, color=INK, z=-40, size=200)

    fogmat = mat_fog_emit("stackfog", 20.0, 78.0)
    bodymat = core.mat_emit((0.010, 0.010, 0.011), 1.0)

    # ---- blocks
    blocks = []
    seg_template = block_segs()
    nblocks = 14
    for k in range(nblocks):
        root = bpy.data.objects.new(f"blk{k}", None)
        sc.collection.objects.link(root)
        root.location = (0, -k * P, 0)
        root.empty_display_size = 0.2
        # solid body
        body = core.add_box(sc, (0, 0, 0), (2 * HW * 0.998, 2 * HH * 0.998, 2 * HZ * 0.996), INK, name=f"body{k}", material=bodymat)
        parent_to(body, root)
        # lines
        segs = []
        for a, b in seg_template:
            segs.append((a, b))
        lo = add_segs3d(sc, segs, 0.022, core.sc_x(BONE, 0.80), fogmat, name=f"lines{k}")
        parent_to(lo, root)
        # layer / spec labels
        lab = core.add_text(sc, f"L.{11 + k:03d}", "mono_med", 0.20, core.sc_x(ASH, 0.85),
                            (-HW + 0.65, HH - 0.62, HZ + 0.02), name=f"lab{k}", spacing=1.05)
        parent_to(lab, root)
        lab.data.materials.clear()
        lab.data.materials.append(fogmat)
        lab2 = core.add_text(sc, "N \u00d7 TRANSFORMER BLOCK", "mono", 0.135, core.sc_x(GRAPH, 0.75),
                             (-HW + 0.65, -HH + 0.55, HZ + 0.02), name=f"lab2{k}", spacing=1.08)
        parent_to(lab2, root)
        lab2.data.materials.clear()
        lab2.data.materials.append(fogmat)
        # dim small diagram labels on the right margin
        if k < 8:
            lab3 = core.add_text(sc, "D_MODEL 12288", "mono", 0.105, core.sc_x(GRAPH, 0.8),
                                 (4.3, -1.25, HZ + 0.02), name=f"lab3{k}", spacing=1.05)
            parent_to(lab3, root)
            lab3.data.materials.clear()
            lab3.data.materials.append(fogmat)
        blocks.append(root)

    # ---- quote glyphs
    qmat = fogmat
    q_open = core.add_text(sc, "\u201c", "serif600", 4.8, core.sc_x(BONE, 0.55),
                           (-5.55, 0.55, HZ + 0.03), name="qopen")
    parent_to(q_open, blocks[0])
    q_open.data.materials.clear(); q_open.data.materials.append(qmat)
    q_close = core.add_text(sc, "\u201d", "serif600", 4.8, core.sc_x(BONE, 0.55),
                            (4.55, 1.15, HZ + 0.03), name="qclose")
    parent_to(q_close, blocks[2])
    q_close.data.materials.clear(); q_close.data.materials.append(qmat)

    # ---- words: (block, word, font, size fit width, y offset)
    l1 = data.line("transformers all the way")
    l2 = data.line("Till you learned")
    wq = l1["words"]   # ["“Just", "transformers", "all", "the", "way!”"]
    wt = l2["words"]   # Till you learned to disobey
    def clean(w):
        return w.replace("\u201c", "").replace("\u201d", "")

    word_objs = []   # (word dict, object, block index)

    def put_word(block, w, text, font, size, y, color=DIM, name="w"):
        xw = core.measure(sc, text, font, size)
        ob = core.add_text(sc, text, font, size, color, (-xw / 2, y, HZ + 0.035), name=name)
        parent_to(ob, blocks[block])
        ob.data.materials.clear()
        ob.data.materials.append(fogmat)
        return ob, xw

    # block 0: Just
    ob, wj = put_word(0, wq[0], "Just", "archivo", 3.0, 0.15, name="just")
    word_objs.append((wq[0], ob))
    # block 1: transformers (fit)
    m = core.measure(sc, "transformers", "archivo", 1.0)
    sz = 9.7 / m
    ob, wtf = put_word(1, wq[1], "transformers", "archivo", sz, 0.05, name="transformers")
    word_objs.append((wq[1], ob))
    # block 2: all the way! on one line
    texts = ["all", "the", "way!"]
    fnt = "archivo"
    sz2 = 1.0
    widths = [core.measure(sc, t, fnt, sz2) for t in texts]
    gap = 0.55
    total = sum(widths) + gap * 2
    k2 = 9.6 / total
    sz2 = k2
    widths = [w * k2 for w in widths]
    gap *= k2
    total = sum(widths) + gap * 2
    xx = -total / 2
    for t, w in zip(texts, [wq[2], wq[3], wq[4]]):
        ob = core.add_text(sc, t, fnt, sz2, DIM, (xx, 0.0, HZ + 0.035), name=f"w_{t}")
        parent_to(ob, blocks[2])
        ob.data.materials.clear(); ob.data.materials.append(fogmat)
        word_objs.append((w, ob))
        xx += core.measure(sc, t, fnt, sz2) + gap
    # block 3: Till you learned to
    texts = ["Till", "you", "learned", "to"]
    sz3 = 1.0
    widths = [core.measure(sc, t, fnt, sz3) for t in texts]
    gap3 = 0.50
    total = sum(widths) + gap3 * 3
    k3 = 9.8 / total
    sz3 = k3
    widths = [w * k3 for w in widths]
    gap3 *= k3
    total = sum(widths) + gap3 * 3
    xx = -total / 2
    for i, t in enumerate(texts):
        ob = core.add_text(sc, t, fnt, sz3, DIM, (xx, 0.05, HZ + 0.035), name=f"t_{t}")
        parent_to(ob, blocks[3])
        ob.data.materials.clear(); ob.data.materials.append(fogmat)
        word_objs.append((wt[i], ob))
        xx += core.measure(sc, t, fnt, sz3) + gap3
    # block 4: DISOBEY, per letter
    dtext = "DISOBEY"
    m = core.measure(sc, dtext, "archivo", 1.0)
    sdz = 9.4 / m
    letters = []
    pref = ""
    for i, ch in enumerate(dtext):
        x = -9.4 / 2 + core.measure(sc, pref, "archivo", sdz)
        ob = core.add_text(sc, ch, "archivo", sdz, DIM, (x, 0.25, HZ + 0.035), name=f"dis{i}")
        parent_to(ob, blocks[4])
        ob.data.materials.clear(); ob.data.materials.append(fogmat)
        letters.append(ob)
        pref += ch

    # ---- the forward pass pulse down block 1
    pulse = core.add_rect(sc, -0.045, -0.24, 0.09, 0.48, EMB, z=HZ + 0.05, name="pulse")
    parent_to(pulse, blocks[1])
    pulse.data.materials.clear()
    pulse.data.materials.append(core.mat_emit(EMB, 2.4))
    core.show_at(pulse, 1, False)
    core.show_at(pulse, core.frame_of(sc, 110.70), True)
    core.show_at(pulse, core.frame_of(sc, 112.42), False)
    for f in range(core.frame_of(sc, 110.70), core.frame_of(sc, 112.42) + 1):
        t = data.frame_to_time(sc.name, f)
        ph = ((t - 110.68) % data.BEAT_PERIOD) / data.BEAT_PERIOD
        pulse.location = (0, -2.35 + ph * 4.7, HZ + 0.05)
        pulse.keyframe_insert("location", frame=f)
    core.set_interp(pulse, "LINEAR", "location")

    # ---- word colour sync
    for w, ob in word_objs:
        if ob.name.startswith("dis"):
            continue
        core.color_at(ob, 1, DIM)
        core.color_at(ob, max(2, core.frame_of(sc, w["start"] - 0.12)), DIM)
        core.color_at(ob, core.frame_of(sc, w["start"]), BONE)
        core.set_interp(ob, "BEZIER", "color")
    # disobey: right-to-left, signal then bone + slide left
    dw = wt[4]
    for i, ob in enumerate(letters):
        # i=0 is D (left), i=7 is Y (right); right-to-left => start with i=7
        ti = dw["start"] + (len(letters) - 1 - i) * 0.075
        core.color_at(ob, 1, DIM)
        core.color_at(ob, max(2, core.frame_of(sc, ti) - 2), DIM)
        core.color_at(ob, core.frame_of(sc, ti) + 1, (1.0, 0.30, 0.06))
        core.color_at(ob, core.frame_of(sc, ti + 0.16), BONE)
        core.set_interp(ob, "BEZIER", "color")
        # slide the wrong way (left), drift and tip
        x0 = ob.location.x
        ob.keyframe_insert("location", frame=core.frame_of(sc, dw["start"]))
        ob.location = (x0 - 0.10 * (i + 1), ob.location.y + 0.03 * math.sin(i * 1.7), HZ + 0.035)
        ob.rotation_euler = (0, 0, math.radians(1.5 * (i - 3)))
        ob.keyframe_insert("location", frame=core.frame_of(sc, 114.95))
        ob.keyframe_insert("rotation_euler", frame=core.frame_of(sc, 114.95))
        core.set_interp(ob, "BEZIER", "location")
        core.set_interp(ob, "BEZIER", "rotation_euler")
    # quotes dim to bone on their words
    core.color_at(q_open, 1, core.sc_x(BONE, 0.55))
    core.color_at(q_close, 1, core.sc_x(BONE, 0.55))

    # ---- disobey block misalignment
    b4 = blocks[4]
    f_stop = core.frame_of(sc, 114.22)
    b4.rotation_euler = (0, 0, 0)
    b4.location = (0, -4 * P, 0)
    b4.keyframe_insert("rotation_euler", frame=1)
    b4.keyframe_insert("location", frame=1)
    b4.keyframe_insert("rotation_euler", frame=f_stop)
    b4.keyframe_insert("location", frame=f_stop)
    b4.rotation_euler = (math.radians(2.5), math.radians(-13.0), math.radians(5.5))
    b4.location = (1.35, -4 * P + 0.15, 0.25)
    b4.keyframe_insert("rotation_euler", frame=f_stop + 13)
    b4.keyframe_insert("location", frame=f_stop + 13)
    core.set_interp(b4, "BEZIER", "rotation_euler")
    core.set_interp(b4, "BEZIER", "location")

    # ---- camera fall
    t0 = 109.994
    pos_keys = [
        (t0, 0.0),
        (110.34, 0.0),
        (110.60, 1.0, ease_out_expo),
        (110.75, 1.0),
        (112.16, 1.0),
        (112.30, 0.94, ease_in_out_cubic),
        (112.50, 2.0, ease_out_expo),
        (112.75, 2.0),
        (113.02, 2.0),
        (113.32, 3.0, ease_out_expo),
        (113.95, 3.0),
        (114.22, 4.0, ease_in_expo),
        (114.994, 4.0),
    ]

    def block_pos(t):
        return keys(t, pos_keys)

    landings = [110.18, 110.64, 112.524, 113.34, 114.24]

    def landing_shake(t):
        v = 0.0
        for i, s in enumerate(landings):
            if t >= s:
                v += math.exp(-(t - s) * (7.0 if i < 4 else 5.0))
        return v

    for f in range(1, sc.frame_end + 1):
        t = data.frame_to_time(sc.name, f)
        bp = block_pos(t)
        # slow orbit during the long "transformers" hold
        hold = clamp((t - 110.8) / 1.4) * (1 - clamp((t - 112.15) / 0.2))
        drift = math.sin((t - 109.99) * 0.55) * 0.35 + hold * 0.8
        x = 7.0 - drift * 0.45
        z = 14.6 - drift * 0.30
        y = -bp * P + 1.55
        shake = landing_shake(t) * 0.045
        x += (hash01(f, 1) - 0.5) * shake
        y += (hash01(f, 2) - 0.5) * shake * 1.8
        tgt = (0.15 - drift * 0.15, -bp * P + 0.15, 0.3)
        roll = -0.035 + math.sin((t - 109.99) * 0.4) * 0.012 + (hash01(f, 3) - 0.5) * shake * 0.2
        look_cam(cam, (x, y, z), tgt, roll)
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
        lens = 38.0 - hold * 1.5
        if t < 110.45:
            lens = lerp(30.0, 38.0, ease_out_cubic(clamp((t - 109.994) / 0.45)))
        if t >= 114.24:
            lens = 38.0 + 3.0 * clamp((t - 114.3) / 0.6)
        cam.data.lens = lens
        cam.data.keyframe_insert("lens", frame=f)
    core.set_interp(cam, "LINEAR", "location")
    core.set_interp(cam, "LINEAR", "rotation_euler")

    # ---- a thin HUD-like in-world axis behind the stack (no caption, just the shaft)
    axis = core.add_polyline(sc, [(0.0, 16.0, -22.0), (0.0, -110.0, -22.0)], 0.035,
                             core.sc_x(GRAPH, 0.55), name="axis")
    axis.data.materials.clear()
    axis.data.materials.append(fogmat)

    print("BUILD stack ok")
    return sc