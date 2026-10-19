"""PAPERCLIPS — "as paperclips fill the room" (96.813–102.267).

One glowing line bends into a real 3D gem clip; it duplicates on the eighths into a woven
floor of clips, the camera cranes down and glides through the lattice. "Killswitch guy's on
PTO" arrives as a typed out-of-office card. On "Now there's nowhere left to go" a ceiling of
clips comes down and the line is squeezed into the last slot.
"""
import bpy, math, os, sys
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pdoom import core, data, motifs
from pdoom.core import PAL, clamp, lerp, keys, hash01
from pdoom.core import ease_out_expo, ease_in_out_cubic

INK, BONE, SIG, EMB, GRAPH, ASH, BLOOD = (PAL["ink"], PAL["bone"], PAL["signal"], PAL["ember"],
                                          PAL["graphite"], PAL["ash"], PAL["blood"])
DIM = core.sc_x(BONE, 0.30)


# ------------------------------------------------------------------ clip geometry
def clip_path(a=0.22, L=0.82, n=176, tip_drop=0.20):
    """Classic gem clip: outer U, small top eye, three lanes. Returns XY centreline."""
    # segment lengths for even sampling
    segs = []  # list of (point_fn, length)
    def line(p0, p1):
        d = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        return (lambda t, p0=p0, p1=p1: (lerp(p0[0], p1[0], t), lerp(p0[1], p1[1], t))), d
    def arc(cx, cy, r, a0, a1):
        d = abs(a1 - a0) * r
        return (lambda t, cx=cx, cy=cy, r=r, a0=a0, a1=a1: (cx + r * math.cos(lerp(a0, a1, t)),
                                                            cy + r * math.sin(lerp(a0, a1, t)))), d
    segs.append(line((-a, L), (-a, -L)))
    segs.append(arc(0, -L, a, math.pi, math.tau))
    segs.append(line((a, -L), (a, L)))
    segs.append(arc(a * 0.5, L, a * 0.5, 0, math.pi))
    segs.append(line((0, L), (0, -L + tip_drop)))
    total = sum(s[1] for s in segs)
    pts = []
    for i in range(n):
        d = (i / (n - 1)) * total
        for fn, ln in segs:
            if d <= ln or (fn, ln) == segs[-1]:
                t = clamp(d / max(ln, 1e-9))
                pts.append(fn(t))
                break
            d -= ln
    return pts


def make_clip_mesh(name, pts, radius=0.042, sides=8):
    verts, faces, rings = [], [], []
    up = Vector((0, 0, 1))
    for i, (x, y) in enumerate(pts):
        if i == 0:
            t = Vector((pts[1][0] - x, pts[1][1] - y, 0)).normalized()
        elif i == len(pts) - 1:
            t = Vector((x - pts[-2][0], y - pts[-2][1], 0)).normalized()
        else:
            t = Vector((pts[i + 1][0] - pts[i - 1][0], pts[i + 1][1] - pts[i - 1][1], 0)).normalized()
        side = t.cross(up)
        if side.length < 1e-6:
            side = Vector((1, 0, 0))
        side.normalize()
        up2 = side.cross(t).normalized()
        ring = []
        for k in range(sides):
            ang = k / sides * math.tau
            v = Vector((x, y, 0)) + side * (math.cos(ang) * radius) + up2 * (math.sin(ang) * radius)
            ring.append(len(verts))
            verts.append((v.x, v.y, v.z))
        rings.append(ring)
    for i in range(len(rings) - 1):
        A, B = rings[i], rings[i + 1]
        for k in range(sides):
            k2 = (k + 1) % sides
            faces.append((A[k], A[k2], B[k2], B[k]))
    c0 = len(verts); verts.append((pts[0][0], pts[0][1], 0))
    for k in range(sides):
        faces.append((c0, rings[0][(k + 1) % sides], rings[0][k]))
    c1 = len(verts); verts.append((pts[-1][0], pts[-1][1], 0))
    for k in range(sides):
        faces.append((c1, rings[-1][k], rings[-1][(k + 1) % sides]))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate()
    for p in me.polygons:
        p.use_smooth = True
    return me


def merged_mesh(name, template, instances):
    tv = template.vertices
    faces = [tuple(p.vertices) for p in template.polygons]
    verts = []
    for (x, y, z, rz, s) in instances:
        c, sn = math.cos(rz), math.sin(rz)
        for v in tv:
            vx, vy, vz = v.co.x * s, v.co.y * s, v.co.z * s
            verts.append((x + vx * c - vy * sn, y + vx * sn + vy * c, z + vz))
    allf = []
    for k in range(len(instances)):
        off = k * len(tv)
        allf.extend([tuple(i + off for i in f) for f in faces])
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], allf)
    me.validate()
    for p in me.polygons:
        p.use_smooth = True
    return me


# ------------------------------------------------------------------ materials
def mat_clip(fog0=4.0, fog1=26.0):
    m = bpy.data.materials.new("clipmetal")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Metallic"].default_value = 0.20
    bsdf.inputs["Roughness"].default_value = 0.36
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Rotation"].default_value = (0.3, 0.1, 0.8)
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    wave.inputs["Scale"].default_value = 95.0
    wave.inputs["Distortion"].default_value = 0.9
    wave.inputs["Detail"].default_value = 3.0
    wave.inputs["Detail Scale"].default_value = 1.2
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].position = 0.34
    ramp.color_ramp.elements[0].color = (0.050, 0.049, 0.047, 1)
    ramp.color_ramp.elements[1].position = 0.66
    ramp.color_ramp.elements[1].color = (*core.sc_x(BONE, 0.50), 1)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], wave.inputs["Vector"])
    nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    cd = nt.nodes.new("ShaderNodeCameraData")
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs[1].default_value = fog0
    mr.inputs[2].default_value = fog1
    mr.inputs[3].default_value = 0.0
    mr.inputs[4].default_value = 1.0
    nt.links.new(cd.outputs["View Z Depth"], mr.inputs[0])
    fmix = nt.nodes.new("ShaderNodeMix")
    fmix.data_type = "RGBA"
    fmix.inputs[7].default_value = (*INK, 1)
    nt.links.new(ramp.outputs["Color"], fmix.inputs[6])
    nt.links.new(mr.outputs[0], fmix.inputs[0])
    nt.links.new(fmix.outputs[2], bsdf.inputs["Base Color"])
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.45
    pw = nt.nodes.new("ShaderNodeMath")
    pw.operation = "POWER"
    pw.inputs[1].default_value = 3.0
    nt.links.new(lw.outputs["Facing"], pw.inputs[0])
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(mr.outputs[0], inv.inputs[1])
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = 0.26
    nt.links.new(pw.outputs[0], mul.inputs[0])
    mul2 = nt.nodes.new("ShaderNodeMath")
    mul2.operation = "MULTIPLY"
    nt.links.new(mul.outputs[0], mul2.inputs[0])
    nt.links.new(inv.outputs[0], mul2.inputs[1])
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[0].default_value = (*EMB, 1)
    nt.links.new(mul2.outputs[0], em.inputs["Strength"])
    add = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(bsdf.outputs[0], add.inputs[0])
    nt.links.new(em.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs["Surface"])
    return m


def mat_floor():
    m = bpy.data.materials.new("floor")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (0.0022, 0.0022, 0.0021, 1)
    b.inputs["Roughness"].default_value = 0.82
    b.inputs["Metallic"].default_value = 0.0
    try:
        b.inputs["Specular IOR Level"].default_value = 0.10
    except Exception:
        pass
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    return m


def parent_to(ob, parent):
    ob.parent = parent
    ob.matrix_parent_inverse = Matrix.Identity(4)
    return ob


def cam_text(sc, body, font, size, color, loc, cam, name="t", align="LEFT", spacing=1.0):
    ob = core.add_text(sc, body, font, size, color, loc, align_x=align, name=name, spacing=spacing)
    parent_to(ob, cam)
    return ob


# ------------------------------------------------------------------ scene
def build(name):
    sc = core.new_scene(name, samples=32, motion_blur=True)
    sc.frame_set(1)
    cam = core.add_camera_persp(sc, (0, -1.7, 4.1), (0, 0, 0), lens=50)
    cam.data.sensor_width = 36.0
    cam.data.dof.use_dof = False
    cam.data.dof.focus_distance = 2.0
    cam.data.dof.aperture_fstop = 10.0
    cam.data.clip_start = 0.05

    core.add_bg(sc, color=INK, z=-40, size=300)
    floor = core.add_rect(sc, -120, -120, 240, 240, INK, z=-0.055, name="floor")
    floor.data.materials.clear()
    floor.data.materials.append(mat_floor())

    key = core.add_light(sc, "AREA", (5.0, -4.0, 7.5), 3400, BONE, size=6.0, name="key")
    rim = core.add_light(sc, "AREA", (-9.0, 11.0, 5.5), 600, EMB, size=3.0, name="rim")
    kick = core.add_light(sc, "AREA", (-6.0, -2.0, 4.0), 900, core.sc_x(BONE, 0.95), size=4.0, name="kick")
    strip = core.add_light(sc, "AREA", (0.4, -2.6, 6.4), 520, core.sc_x(BONE, 0.9), size=1.0, name="strip")
    try:
        strip.data.shape = "RECTANGLE"
        strip.data.size = 6.0
        strip.data.size_y = 0.55
    except Exception:
        pass
    fill = core.add_light(sc, "POINT", (1.2, 2.0, 1.2), 10, EMB, size=0.6, name="fill")
    rimpt = core.add_light(sc, "POINT", (-4.0, 10.0, 1.35), 220, SIG, size=0.8, name="rimpt")

    # ---- clip meshes
    pts = clip_path(n=176)
    mesh = make_clip_mesh("clip", pts, radius=0.042, sides=8)
    mesh_far = make_clip_mesh("clipfar", clip_path(n=100), radius=0.042, sides=6)
    metal = mat_clip()

    # ---- split tree: 1 -> 2 -> 4 -> ... -> 64, each split a quarter-turn mirror
    splits = [97.267, 97.494, 97.722, 97.949, 98.176, 98.404]
    DX = [1.46, 0.0, 2.92, 0.0, 5.84, 0.0]
    DY = [0.0, 1.46, 0.0, 2.92, 0.0, 5.84]
    items = []
    for idx in range(64):
        bits = [(idx >> l) & 1 for l in range(6)]
        top = -1
        for l in range(6):
            if bits[l]:
                top = l
        pos = {}
        for l in range(6):
            x = y = ang = 0.0
            for k in range(l + 1):
                sgn = 1.0 if bits[k] else -1.0
                x += sgn * DX[k] * 0.5
                y += sgn * DY[k] * 0.5
                if bits[k]:
                    ang += math.pi / 2 * (1 if k % 2 == 0 else -1)
            pos[l] = (x, y, ang)
        items.append({"bits": bits, "top": top, "pos": pos})

    hero = []
    for i, it in enumerate(items):
        ob = bpy.data.objects.new(f"clip{i:02d}", mesh)
        sc.collection.objects.link(ob)
        ob.data.materials.append(metal)
        z = 0.018 + hash01(i, 5) * 0.010
        ob.location = (0, 0, z)
        hero.append(ob)

    def pose_at(ob, l, i, f):
        x, y, ang = items[i]["pos"][l]
        ob.location = (x, y, 0.018 + hash01(i, 5) * 0.010)
        ob.rotation_euler = (0, 0, ang)
        ob.keyframe_insert("location", frame=f)
        ob.keyframe_insert("rotation_euler", frame=f)

    for i, it in enumerate(items):
        ob = hero[i]
        top = it["top"]
        if i == 0:
            # the seed clip sits at the origin until the first split
            ob.location = (0, 0, 0.018)
            ob.rotation_euler = (0, 0, 0)
            ob.keyframe_insert("location", frame=1)
            ob.keyframe_insert("rotation_euler", frame=1)
            core.show_at(ob, 1, False)
            core.show_at(ob, core.frame_of(sc, 97.15), True)
            for l in range(6):
                f0 = core.frame_of(sc, splits[l])
                f1 = core.frame_of(sc, splits[l] + 0.18)
                if l == 0:
                    ob.location = (0, 0, 0.018)
                    ob.rotation_euler = (0, 0, 0)
                    ob.keyframe_insert("location", frame=f0)
                    ob.keyframe_insert("rotation_euler", frame=f0)
                else:
                    pose_at(ob, l - 1, i, f0)
                pose_at(ob, l, i, f1)
            core.set_interp(ob, "BEZIER", "location")
            core.set_interp(ob, "BEZIER", "rotation_euler")
            continue
        f0 = core.frame_of(sc, splits[top])
        x, y, ang = it["pos"][top]
        ob.location = (x, y, 0.018 + hash01(i, 5) * 0.010)
        ob.rotation_euler = (0, 0, ang)
        ob.keyframe_insert("location", frame=f0)
        ob.keyframe_insert("rotation_euler", frame=f0)
        ob.scale = (0.80, 0.80, 0.80)
        ob.keyframe_insert("scale", frame=max(1, f0 - 1))
        ob.scale = (1, 1, 1)
        ob.keyframe_insert("scale", frame=f0 + 5)
        core.set_interp(ob, "BEZIER", "scale")
        core.show_at(ob, 1, False)
        core.show_at(ob, max(1, f0), True)
        for l in range(top + 1, 6):
            f0b = core.frame_of(sc, splits[l])
            f1b = core.frame_of(sc, splits[l] + 0.18)
            pose_at(ob, l - 1, i, f0b)
            pose_at(ob, l, i, f1b)
        core.set_interp(ob, "BEZIER", "location")
        core.set_interp(ob, "BEZIER", "rotation_euler")

    # ---- the spark's line bends into the first clip
    line_pts = [(p[0], p[1], 0.09) for p in pts]
    line = core.add_polyline(sc, line_pts, 0.021, EMB, name="drawline", hot=True)
    line.data.bevel_factor_end = 0.53
    line.data.keyframe_insert("bevel_factor_end", frame=1)
    line.data.bevel_factor_end = 1.0
    line.data.keyframe_insert("bevel_factor_end", frame=core.frame_of(sc, 97.16))
    core.set_interp(line, "BEZIER", "bevel_factor_end")
    core.show_at(line, 1, True)
    core.show_at(line, core.frame_of(sc, 97.24), False)
    acc = [0.0]
    for i in range(1, len(pts)):
        acc.append(acc[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]))
    total_len = acc[-1]

    def path_at(k):
        d = clamp(k) * total_len
        lo, hi = 0, len(acc) - 1
        while lo + 1 < hi:
            mid = (lo + hi) // 2
            if acc[mid] < d:
                lo = mid
            else:
                hi = mid
        seg = max(1e-6, acc[hi] - acc[lo])
        u = (d - acc[lo]) / seg
        return (lerp(pts[lo][0], pts[hi][0], u), lerp(pts[lo][1], pts[hi][1], u))

    spark = core.add_uv_sphere(sc, (0, 0, 0.10), 0.050, EMB, hot=True, name="spark")
    core.show_at(spark, 1, False)
    core.show_at(spark, 1, True)
    core.show_at(spark, core.frame_of(sc, 97.34), False)
    for f in range(1, core.frame_of(sc, 97.34) + 1):
        t = data.frame_to_time(sc.name, f)
        k = lerp(0.53, 1.0, clamp((t - 96.813) / (97.16 - 96.813)))
        p = path_at(k)
        spark.location = (p[0], p[1], 0.10)
        spark.keyframe_insert("location", frame=f)
    core.set_interp(spark, "LINEAR", "location")

    # ---- infinite floor field
    field = []
    for j in range(24):
        for i in range(30):
            x = -29 + i * 2.0 + (hash01(i, j, 1) - 0.5) * 0.9
            y = -13 + j * 2.0 + (hash01(i, j, 2) - 0.5) * 0.9
            if math.hypot(x, y) < 7.0:
                continue
            rz = (hash01(i, j, 3) - 0.5) * 0.14 + (math.pi / 2 if hash01(i, j, 4) < 0.38 else 0.0)
            s = 0.78 + hash01(i, j, 5) * 0.55
            field.append((x, y, hash01(i, j, 6) * 0.05, rz, s))
    fme = merged_mesh("field", mesh_far, field)
    fob = bpy.data.objects.new("field", fme)
    sc.collection.objects.link(fob)
    fme.materials.append(metal)
    core.show_at(fob, 1, False)
    core.show_at(fob, core.frame_of(sc, 98.05), True)

    # far row for depth
    field2 = []
    for j in range(6):
        for i in range(16):
            x = -36 + i * 4.8 + (hash01(i, j, 9) - 0.5) * 2.2
            y = 26 + j * 4.4 + (hash01(i, j, 10) - 0.5) * 2.2
            rz = (hash01(i, j, 11) - 0.5) * 0.2
            field2.append((x, y, hash01(i, j, 13) * 0.1, rz, 0.95 + hash01(i, j, 12) * 0.8))
    fme2 = merged_mesh("field2", mesh_far, field2)
    fob2 = bpy.data.objects.new("field2", fme2)
    sc.collection.objects.link(fob2)
    fme2.materials.append(metal)
    core.show_at(fob2, 1, False)
    core.show_at(fob2, core.frame_of(sc, 99.3), True)

    # ---- ceiling of clips
    ceil = []
    for j in range(10):
        for i in range(15):
            x = -13.5 + i * 1.95 + (hash01(i, j, 21) - 0.5) * 0.4
            y = -1.0 + j * 2.0 + (hash01(i, j, 22) - 0.5) * 0.4
            rz = (math.pi / 2 if (i + j) % 2 else 0.0) + (hash01(i, j, 23) - 0.5) * 0.12
            ceil.append((x, y, (hash01(i, j, 24) - 0.5) * 0.16, rz, 0.80))
    cme = merged_mesh("ceiling", mesh_far, ceil)
    cob = bpy.data.objects.new("ceiling", cme)
    sc.collection.objects.link(cob)
    cme.materials.append(metal)
    core.show_at(cob, 1, False)
    core.show_at(cob, core.frame_of(sc, 100.60), True)
    for f in range(core.frame_of(sc, 100.60), sc.frame_end + 1):
        t = data.frame_to_time(sc.name, f)
        z = keys(t, [(100.60, 7.0), (100.95, 1.95, ease_out_expo), (101.60, 1.10, ease_out_expo),
                     (102.10, 0.98), (102.267, 0.93)])
        cob.location = (0, 0, z)
        cob.keyframe_insert("location", frame=f)
    core.set_interp(cob, "LINEAR", "location")
    # lights dim as the ceiling comes down
    for f in range(core.frame_of(sc, 100.60), sc.frame_end + 1):
        t = data.frame_to_time(sc.name, f)
        k = clamp((t - 100.62) / 1.2)
        key.data.energy = 3400 * (1 - 0.72 * k)
        key.data.keyframe_insert("energy", frame=f)
        rim.data.energy = 600 * (1 - 0.72 * k)
        rim.data.keyframe_insert("energy", frame=f)
        kick.data.energy = 900 * (1 - 0.75 * k)
        kick.data.keyframe_insert("energy", frame=f)
    core.set_interp(key.data, "LINEAR", "energy")
    core.set_interp(rim.data, "LINEAR", "energy")

    # ---- camera
    P = [
        (96.813, (0.0, -1.9, 5.1), (0.0, 0.0, 0.02), 50.0, 0.0, 10.0),
        (97.05, (0.2, -2.0, 5.3), (0.0, 0.0, 0.02), 50.0, 0.0, 10.0),
        (97.45, (0.7, -2.6, 6.4), (0.0, 0.4, 0.0), 48.0, -0.01, 7.5),
        (97.95, (1.8, -4.0, 10.6), (0.0, 1.2, 0.0), 44.0, -0.02, 5.2),
        (98.40, (1.4, -5.2, 7.0), (0.3, 3.0, 0.2), 40.0, -0.025, 3.8),
        (98.95, (-0.9, -6.7, 2.3), (0.2, 4.2, 0.55), 36.0, -0.02, 2.6),
        (99.50, (-0.4, -3.2, 1.45), (0.1, 8.0, 0.72), 33.0, -0.03, 2.2),
        (100.10, (0.6, 1.8, 1.28), (0.4, 10.0, 0.75), 30.0, -0.02, 2.0),
        (100.72, (1.0, 5.4, 1.06), (0.9, 12.0, 0.80), 28.0, 0.02, 1.8),
        (101.55, (1.7, 8.8, 0.78), (1.4, 14.0, 0.92), 26.0, 0.03, 1.6),
        (102.267, (2.1, 11.6, 0.60), (1.8, 16.0, 1.06), 25.0, 0.025, 1.5),
    ]

    def interp_pts(t):
        if t <= P[0][0]:
            return P[0][1], P[0][2], P[0][4]
        for i in range(len(P) - 1):
            t0, t1 = P[i][0], P[i + 1][0]
            if t <= t1:
                k = clamp((t - t0) / max(1e-6, t1 - t0))
                kk = k * k * (3 - 2 * k)
                a, b = P[i], P[i + 1]
                pos = tuple(lerp(a[1][j], b[1][j], kk) for j in range(3))
                tgt = tuple(lerp(a[2][j], b[2][j], kk) for j in range(3))
                return pos, tgt, lerp(a[4], b[4], kk)
        return P[-1][1], P[-1][2], P[-1][4]

    def hitpulse(t):
        v = 0.0
        for s in splits + [100.721, 101.176, 101.631]:
            if t >= s:
                v += math.exp(-(t - s) * 9.0)
        return v

    lens_keys = [(p[0], p[3]) for p in P]
    fstop_keys = [(p[0], p[5]) for p in P]
    for f in range(1, sc.frame_end + 1):
        t = data.frame_to_time(sc.name, f)
        pos, tgt, roll = interp_pts(t)
        hp = hitpulse(t)
        dx = (hash01(f, 1) - 0.5) * 0.005
        dz = (hash01(f, 2) - 0.5) * (0.004 + 0.016 * hp)
        dy = (hash01(f, 3) - 0.5) * 0.004
        cam.location = (pos[0] + dx, pos[1] + dy, pos[2] + dz)
        core.look_at(cam, (tgt[0], tgt[1], tgt[2] + (hash01(f, 4) - 0.5) * 0.004))
        cam.rotation_euler.rotate_axis("Z", roll + (hash01(f, 5) - 0.5) * 0.003)
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
        cam.data.lens = keys(t, lens_keys)
        cam.data.keyframe_insert("lens", frame=f)
        cam.data.dof.aperture_fstop = keys(t, fstop_keys)
        cam.data.keyframe_insert("dof.aperture_fstop", frame=f)
    core.set_interp(cam, "LINEAR", "location")
    core.set_interp(cam, "LINEAR", "rotation_euler")

    # ---- line 1
    l1 = data.line("as paperclips")
    w1 = core.measure(sc, l1["text"], "archivo300", 1.0)
    size1 = min(0.100, 1.16 / w1)
    x0 = -0.600
    y1 = 0.335
    sw = core.space_width(sc, "archivo300", size1)
    total_w = sum(core.measure(sc, w["w"], "archivo300", size1) for w in l1["words"]) + sw * (len(l1["words"]) - 1)
    w1objs = []
    x = x0
    for i, w in enumerate(l1["words"]):
        ob = cam_text(sc, w["w"], "archivo300", size1, DIM, (x, y1, -2.0), cam, name=f"l1_{i}")
        w1objs.append((w, ob))
        x += core.measure(sc, w["w"], "archivo300", size1) + sw
    core.animate_words(sc, w1objs, sung=BONE, dim=DIM, pre=0.20)
    hide1 = core.frame_of(sc, 98.84)
    for w, ob in w1objs:
        core.show_at(ob, 1, True)
        core.show_at(ob, hide1, False)
    rule = core.add_polyline(sc, [(x0, y1 - 0.052), (x0 + total_w, y1 - 0.052)], 0.0011, core.sc_x(BONE, 0.32), name="l1rule")
    parent_to(rule, cam)
    core.show_at(rule, 1, True)
    core.show_at(rule, hide1, False)

    # ---- the out-of-office card
    card_root = bpy.data.objects.new("cardroot", None)
    sc.collection.objects.link(card_root)
    parent_to(card_root, cam)
    card_root.empty_display_size = 0.1
    CW, CH = 0.90, 0.425
    panel = core.add_rect(sc, 0, 0, CW, CH, INK, z=0.0, name="cardpanel")
    parent_to(panel, card_root)
    pm = core.mat_emit((0.011, 0.011, 0.012), 1.0)
    panel.data.materials.clear()
    panel.data.materials.append(pm)
    border = core.add_outline_rect(sc, 0, 0, CW, CH, 0.0016, core.sc_x(BONE, 0.30), z=0.001, name="cardborder")
    parent_to(border, card_root)
    # dark occlusion card behind (slightly offset, gives the float a shadow side)
    sh = core.add_rect(sc, 0.010, -0.014, CW, CH, INK, z=-0.01, name="cardshadow")
    parent_to(sh, card_root)
    sh.data.materials.clear()
    sh.data.materials.append(core.mat_emit((0.0, 0.0, 0.0), 1.0))

    PAD = 0.040
    top = CH - 0.032
    cstatic = []
    cstatic.append(core.add_text(sc, "\u21a9  AUTOMATIC REPLY", "mono_med", 0.0135, core.sc_x(ASH, 0.90),
                                 (PAD, top - 0.012, 0.003), name="c_hdr", spacing=1.14))
    cstatic.append(core.add_text(sc, "DO NOT REPLY", "mono_med", 0.0118, core.sc_x(GRAPH, 1.2),
                                 (CW - PAD, top - 0.012, 0.003), name="c_dnr", align_x="RIGHT", spacing=1.12))
    cstatic.append(core.add_text(sc, "Subject", "mono", 0.0138, core.sc_x(GRAPH, 1.5),
                                 (PAD, top - 0.064, 0.003), name="c_subj"))
    for ob in cstatic:
        parent_to(ob, card_root)

    l2 = data.line("Killswitch")
    subj_size = 0.0500
    subj_y = top - 0.112
    mono_space = core.space_width(sc, "mono_med", subj_size)
    chars = []
    cursor = PAD
    for wi, w in enumerate(l2["words"]):
        wt = w["w"]
        type_a = w["start"]
        type_b = w["start"] + 0.16
        for ci, ch in enumerate(wt):
            if ch == " ":
                cursor += mono_space
                continue
            ob = core.add_text(sc, ch, "mono_med", subj_size, SIG, (cursor, subj_y, 0.006), name=f"subj_{wi}_{ci}")
            parent_to(ob, card_root)
            ft = type_a + (type_b - type_a) * (ci / max(1, len(wt)))
            f = core.frame_of(sc, ft)
            core.show_at(ob, 1, False)
            core.show_at(ob, max(1, f), True)
            core.color_at(ob, 1, SIG)
            core.color_at(ob, max(2, f), SIG)
            core.color_at(ob, core.frame_of(sc, w["end"] + 0.03), core.sc_x(BONE, 0.94))
            core.set_interp(ob, "BEZIER", "color")
            chars.append(ob)
            cursor += core.measure(sc, ch, "mono_med", subj_size)
        cursor += mono_space

    rule2 = core.add_polyline(sc, [(PAD, subj_y - 0.032), (CW - PAD, subj_y - 0.032)], 0.0012,
                              core.sc_x(BONE, 0.18), name="c_rule")
    parent_to(rule2, card_root)
    cstatic.append(rule2)
    body = ["I\u2019m out of office with limited access to",
            "the killswitch. For urgent matters,",
            "please contact \u2014"]
    for i, s in enumerate(body):
        ob = core.add_text(sc, s, "mono", 0.0190, core.sc_x(BONE, 0.76),
                           (PAD, subj_y - 0.076 - i * 0.030, 0.004), name=f"c_body{i}")
        parent_to(ob, card_root)
        cstatic.append(ob)
    ob = core.add_text(sc, "Returning: TBD", "mono", 0.0128, core.sc_x(GRAPH, 1.4), (PAD, 0.056, 0.004), name="c_ret")
    parent_to(ob, card_root); cstatic.append(ob)
    pv = data.pdoom_text(98.9)
    ob = core.add_text(sc, f"Current P(doom): {pv}  (this message was sent automatically)", "mono", 0.0115,
                       core.sc_x(GRAPH, 1.3), (PAD, 0.030, 0.004), name="c_pd")
    parent_to(ob, card_root); cstatic.append(ob)

    caret = core.add_rect(sc, PAD, subj_y - 0.006, 0.0022, subj_size * 0.76, SIG, z=0.007, name="caret")
    parent_to(caret, card_root)

    def typed_cursor(t):
        cx = PAD
        for w in l2["words"]:
            wt = w["w"]
            ta = w["start"]
            tb = w["start"] + 0.16
            if t < ta:
                return cx
            p = clamp((t - ta) / max(1e-5, tb - ta))
            n = int(round(p * len(wt)))
            for ch in wt[:n]:
                cx += mono_space if ch == " " else core.measure(sc, ch, "mono_med", subj_size)
            if p < 1:
                return cx
            cx += mono_space
        return cx

    f_in = core.frame_of(sc, 98.50)
    f_out = core.frame_of(sc, 100.70)
    for ob in [panel, border, sh] + cstatic:
        core.show_at(ob, 1, False)
        core.show_at(ob, f_in - 1, True)
        core.show_at(ob, core.frame_of(sc, 100.745), False)
    for ob in chars:
        core.show_at(ob, core.frame_of(sc, 100.80), False)
    core.show_at(caret, 1, False)
    core.show_at(caret, core.frame_of(sc, 98.78), True)
    core.show_at(caret, core.frame_of(sc, 100.72), False)
    for f in range(core.frame_of(sc, 98.78), core.frame_of(sc, 100.72) + 1):
        t = data.frame_to_time(sc.name, f)
        caret.location = (typed_cursor(t), subj_y - 0.006, 0.007)
        caret.keyframe_insert("location", frame=f)
        vis = True
        if t > 100.30:
            vis = ((f // 6) % 2 == 0)
        core.show_at(caret, f, vis)
    core.set_interp(caret, "LINEAR", "location")

    # card motion: float in, drift, get crushed on the first ceiling slam
    for f in range(1, sc.frame_end + 1):
        t = data.frame_to_time(sc.name, f)
        k_in = ease_out_expo(clamp((t - 98.50) / 0.46))
        lens_now = keys(t, lens_keys)
        halfw = 2.02 * 18.0 / lens_now
        x_target = 0.90 * halfw - CW
        x = lerp(halfw + 0.30, x_target, k_in) - 0.008 * clamp((t - 99.0) / 1.6)
        y = lerp(-0.14, 0.005, k_in) + 0.004 * math.sin((t - 98.5) * 1.7)
        z = -2.02
        rx = 0.010 + 0.004 * math.sin((t - 98.5) * 1.1)
        ry = -0.016 + 0.004 * math.sin((t - 98.5) * 0.8)
        rz = 0.006 + 0.003 * math.sin((t - 98.5) * 0.6)
        sx = sy = 1.0
        if t > 100.68:
            k = ease_in_out_cubic(clamp((t - 100.68) / 0.105))
            y -= 0.62 * k
            sy = max(0.004, 1 - k)
            x += 0.035 * k
        card_root.location = (x, y, z)
        card_root.rotation_euler = (rx, ry, rz)
        card_root.scale = (sx, sy, 1.0)
        card_root.keyframe_insert("location", frame=f)
        card_root.keyframe_insert("rotation_euler", frame=f)
        card_root.keyframe_insert("scale", frame=f)
    core.set_interp(card_root, "LINEAR", "location")
    core.set_interp(card_root, "LINEAR", "rotation_euler")
    core.set_interp(card_root, "LINEAR", "scale")

    # ---- line 3, squeezed into the slot
    l3 = data.line("nowhere left")
    w3m = core.measure(sc, l3["text"], "archivo_w62_900", 1.0)
    size3 = 1.68 / w3m
    sw3 = core.space_width(sc, "archivo_w62_900", size3)
    total3 = sum(core.measure(sc, w["w"], "archivo_w62_900", size3) for w in l3["words"]) + sw3 * 1.55 * (len(l3["words"]) - 1)
    x3 = -total3 / 2
    y3 = 0.0
    # the last slot: a flat ink band, edged with heat, that the words sit inside
    band_y = -0.052
    band_h = 0.192
    band = core.add_rect(sc, -2.8, band_y * 2 + 0.0, 5.6, band_h * 2, INK, z=-4.05, name="slotband")
    parent_to(band, cam)
    band.data.materials.clear()
    band.data.materials.append(core.mat_emit((0.0, 0.0, 0.0), 1.0))
    core.show_at(band, 1, False)
    core.show_at(band, core.frame_of(sc, 100.69), True)
    band.scale = (1, 0.04, 1)
    band.keyframe_insert("scale", frame=core.frame_of(sc, 100.69))
    band.scale = (1, 1, 1)
    band.keyframe_insert("scale", frame=core.frame_of(sc, 100.82))
    core.set_interp(band, "BEZIER", "scale")
    for yy in (band_y * 2, (band_y + band_h) * 2):
        hl = core.add_polyline(sc, [(-2.76, yy), (2.76, yy)], 0.0026, core.sc_x(EMB, 0.55), name="slotline")
        parent_to(hl, cam)
        core.show_at(hl, 1, False)
        core.show_at(hl, core.frame_of(sc, 100.70), True)
    w3objs = []
    x = x3
    for i, w in enumerate(l3["words"]):
        ob = cam_text(sc, w["w"], "archivo_w62_900", size3, DIM, (x, y3, -2.0), cam, name=f"l3_{i}")
        w3objs.append((w, ob))
        x += core.measure(sc, w["w"], "archivo_w62_900", size3) + sw3 * 1.55
        core.show_at(ob, 1, False)
        core.show_at(ob, core.frame_of(sc, 100.70), True)
    core.animate_words(sc, w3objs, sung=BONE, dim=core.sc_x(BONE, 0.22), pre=0.18)
    for w, ob in w3objs:
        ob.scale = (1, 1, 1)
        ob.keyframe_insert("scale", frame=core.frame_of(sc, 100.70))
        ob.scale = (1, 0.86, 1)
        ob.keyframe_insert("scale", frame=core.frame_of(sc, 101.3))
        ob.scale = (1, 0.52, 1)
        ob.keyframe_insert("scale", frame=core.frame_of(sc, 102.05))
        ob.scale = (1, 0.42, 1)
        ob.keyframe_insert("scale", frame=core.frame_of(sc, 102.267))
        core.set_interp(ob, "BEZIER", "scale")

    # ---- dust
    for i in range(18):
        x = -12 + hash01(i, 31) * 26
        y = -6 + hash01(i, 32) * 34
        z = 0.3 + hash01(i, 33) * 3.0
        r = 0.008 + hash01(i, 34) * 0.014
        ob = core.add_uv_sphere(sc, (x, y, z), r, core.sc_x(ASH, 0.48), name=f"dust{i}", segs=8, rings=6)
        for f in range(1, sc.frame_end + 1, 5):
            t = data.frame_to_time(sc.name, f)
            ob.location = (x + math.sin(t * 0.21 + i) * 0.5,
                           y + math.sin(t * 0.13 + i * 2) * 0.4,
                           z + math.sin(t * 0.17 + i * 3) * 0.3)
            ob.keyframe_insert("location", frame=f)
        core.set_interp(ob, "BEZIER", "location")

    print("BUILD paperclips ok  w1=", round(size1, 3), "w3=", round(size3, 3), "line3w=", round(total3, 3))
    return sc