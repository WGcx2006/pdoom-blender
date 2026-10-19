"""FIG. 14 — ILYA / "What was seen": a room in white line, a laptop, a redaction,
a lid pushed down, and an empty theatre. Quiet, human, engraved.

Real 3D geometry: room, desk, laptop (stickers on the lid's back), practical screen
light, shallow DOF. Second set: proscenium, curtains, spotlight, dust. All motion is a
pure function of song time; words come from pdoom.data.
"""
import bpy, bmesh, math, os, sys
from mathutils import Matrix, Quaternion, Vector
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pdoom import core, data
from pdoom.core import (PAL, clamp, lerp, smoothstep, ease_out_expo, ease_in_out_cubic,
                        ease_out_cubic, hash01, prog, keys)

INK, BONE, SIG, EMB, GRAPH, ASH, BLOOD = (PAL["ink"], PAL["bone"], PAL["signal"], PAL["ember"],
                                          PAL["graphite"], PAL["ash"], PAL["blood"])
DIM = core.sc_x(BONE, 0.30)
EMBER_MIX = core.mixc(core.sc_x(BONE, 0.8), EMB, 0.5)

TY = 200.0
FACE_Y = Matrix(((-1, 0, 0), (0, 0, 1), (0, 1, 0))).to_euler()   # +Y wall text, correct reading


# ----------------------------------------------------------------------------- little helpers
def link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


def quad(w, h, color, name="quad", material=None, loc=(0, 0, 0), rot=(0, 0, 0)):
    me = bpy.data.meshes.new(name)
    me.from_pydata([(-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0)],
                   [], [(0, 1, 2, 3)])
    me.update()
    ob = link(bpy.data.objects.new(name, me))
    me.materials.append(material or core.mat_type())
    ob.color = (*color, 1)
    ob.location = loc
    ob.rotation_euler = rot
    return ob


def quad_xz(w, h, color, name="qxz", material=None, loc=(0, 0, 0)):
    me = bpy.data.meshes.new(name)
    me.from_pydata([(-w / 2, 0, -h / 2), (w / 2, 0, -h / 2), (w / 2, 0, h / 2), (-w / 2, 0, h / 2)],
                   [], [(0, 1, 2, 3)])
    me.update()
    ob = link(bpy.data.objects.new(name, me))
    me.materials.append(material or core.mat_type())
    ob.color = (*color, 1)
    ob.location = loc
    return ob


def mesh_box(size, color, name="box", material=None, loc=(0, 0, 0), rot=(0, 0, 0), bevel=0.0):
    sx, sy, sz = size
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= sx
        v.co.y *= sy
        v.co.z *= sz
    bm.to_mesh(me)
    bm.free()
    ob = link(bpy.data.objects.new(name, me))
    me.materials.append(material or core.mat_type())
    ob.color = (*color, 1)
    ob.location = loc
    ob.rotation_euler = rot
    if bevel:
        md = ob.modifiers.new("bev", "BEVEL")
        md.width = bevel
        md.segments = 2
        md.limit_method = "ANGLE"
    return ob


def screen_material():
    m = bpy.data.materials.new("ilya_screen")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[1].default_value = 1.05
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sub = nt.nodes.new("ShaderNodeVectorMath")
    sub.operation = "SUBTRACT"
    sub.inputs[1].default_value = (0.5, 0.5, 0.0)
    ln = nt.nodes.new("ShaderNodeVectorMath")
    ln.operation = "LENGTH"
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.0
    mr.inputs["From Max"].default_value = 0.62
    mr.inputs["To Min"].default_value = 1.0
    mr.inputs["To Max"].default_value = 0.30
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs[6].default_value = (0.72, 0.55, 0.40, 1)
    mix.inputs[7].default_value = (0.10, 0.065, 0.045, 1)
    nt.links.new(tc.outputs["Generated"], sub.inputs[0])
    nt.links.new(sub.outputs["Vector"], ln.inputs[0])
    nt.links.new(ln.outputs["Value"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], mix.inputs["Factor"])
    nt.links.new(mix.outputs[2], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def pool_material():
    m = bpy.data.materials.new("ilya_pool")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[1].default_value = 1.35
    em.inputs[0].default_value = (*core.sc_x(EMB, 0.55), 1)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sub = nt.nodes.new("ShaderNodeVectorMath")
    sub.operation = "SUBTRACT"
    sub.inputs[1].default_value = (0.5, 0.5, 0.0)
    ln = nt.nodes.new("ShaderNodeVectorMath")
    ln.operation = "LENGTH"
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.06
    mr.inputs["From Max"].default_value = 0.50
    mr.inputs["To Min"].default_value = 1.0
    mr.inputs["To Max"].default_value = 0.0
    nt.links.new(tc.outputs["Generated"], sub.inputs[0])
    nt.links.new(sub.outputs["Vector"], ln.inputs[0])
    nt.links.new(ln.outputs["Value"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], em.inputs["Strength"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


# ----------------------------------------------------------------------------- times
def times():
    l1 = data.line("What did Ilya")
    l2 = data.line("all for show")
    w1, w2 = l1["words"], l2["words"]
    see, well, never, know = w1[3], w1[4], w1[5], w1[6]
    was, show = w2[0], w2[4]
    slam = min(data.DOWNBEATS, key=lambda d: abs(d - (see["start"] + 0.10)))
    slit = min(data.DOWNBEATS, key=lambda d: abs(d - (know["start"] + 0.30)))
    dark = min([b for b in data.BEATS if b > slit + 0.20], default=slit + 0.45)
    led_off = max([b for b in data.BEATS if b <= was["start"] - 0.05], default=was["start"] - 0.1)
    know_bar = min([d for d in data.DOWNBEATS if dark + 0.4 < d < led_off], default=(dark + led_off) / 2)
    meet = max([b for b in data.BEATS if b <= show["start"] - 0.05], default=show["start"] - 0.1)
    return dict(l1=l1, l2=l2, w1=w1, w2=w2, what=w1[0], ilya=w1[2], see=see, well=well,
                never=never, know=know, was=was, show=show, forw=w2[3], slam=slam, slit=slit, dark=dark,
                led_off=led_off, know_bar=know_bar, meet=meet, theatre=led_off + 0.12)


# ----------------------------------------------------------------------------- room
def build_room(sc, T, ROOM):
    reg = ROOM.append

    floor = mesh_box((3.4, 4.4, 0.02), INK, "floor",
                     core.mat_hatch_lit(INK, GRAPH, 30, 0, 1.0, 0.5, 0.10, core.sc_x(ASH, 0.7), 0.008), (0, 0.1, -0.01))
    reg(floor)
    wall = mesh_box((3.4, 0.02, 3.0), INK, "wall",
                    core.mat_hatch_lit(INK, GRAPH, 44, 90, 1.0, 0.6, 0.10, core.sc_x(ASH, 0.7), 0.010), (0, -1.36, 1.5))
    reg(wall)
    reg(mesh_box((0.02, 2.0, 3.0), INK, "leftwall",
                 core.mat_hatch_lit(INK, GRAPH, 44, 90, 1.0, 0.6, 0.10, core.sc_x(ASH, 0.7), 0.010), (-1.55, -0.4, 1.5)))

    segs = []
    for i in range(9):
        x = -1.6 + i * 0.4
        segs.append(((x, -1.345, 0.0), (x, -1.345, 3.0)))
    for j in range(8):
        z = j * 0.4
        segs.append(((-1.6, -1.345, z), (1.6, -1.345, z)))
    reg(core.add_segments(sc, segs, 0.0035, core.sc_x(BONE, 0.045), name="wallgrid"))
    fsegs = []
    for i in range(9):
        x = -1.6 + i * 0.4
        fsegs.append(((x, -1.35, 0.002), (x, 0.9, 0.002)))
    for j in range(7):
        y = -1.35 + j * 0.38
        fsegs.append(((-1.6, y, 0.002), (1.6, y, 0.002)))
    reg(core.add_segments(sc, fsegs, 0.003, core.sc_x(BONE, 0.035), name="floorgrid"))

    reg(mesh_box((1.9, 0.92, 0.045), INK, "desk",
                 core.mat_hatch_lit(INK, GRAPH, 55, 0, 0.8, 0.32, 0.10, core.sc_x(ASH, 0.8), 0.02),
                 (0, -0.02, 0.7175), bevel=0.004))
    top = 0.74
    for sx in (-0.88, 0.88):
        for sy in (-0.40, 0.38):
            reg(mesh_box((0.045, 0.045, 0.70), INK, "leg",
                         core.mat_lit(INK, 0.5, 0.2), (sx, sy, 0.35), bevel=0.002))
    reg(mesh_box((1.72, 0.02, 0.30), INK, "deskpanel", core.mat_lit(INK, 0.6, 0.1), (0, 0.40, 0.55)))
    reg(core.add_polyline(sc, [(-0.95, 0.44, top), (0.95, 0.44, top), (0.95, 0.44, 0.695),
                               (-0.95, 0.44, 0.695)], 0.005, core.sc_x(BONE, 0.34), name="deskedge"))
    reg(core.add_polyline(sc, [(-0.95, -0.48, top), (0.95, -0.48, top), (0.95, 0.44, top)],
                          0.0035, core.sc_x(BONE, 0.16), name="deskbackedge"))
    reg(core.add_polyline(sc, [(-0.95, -0.48, top), (-0.95, 0.44, top)], 0.004,
                          core.sc_x(BONE, 0.14), name="deskedge2"))

    # far side of the room (seen from behind the laptop): wall, window, chair
    reg(mesh_box((3.6, 0.02, 3.0), INK, "farwall",
                 core.mat_hatch_lit(INK, GRAPH, 44, 90, 1.0, 0.6, 0.10, core.sc_x(ASH, 0.7), 0.008),
                 (0.1, 2.0, 1.5)))
    wsegs = []
    for i in range(8):
        x = -0.42 + i * 0.155
        wsegs.append(((x, 1.985, 1.46), (x, 1.985, 2.36)))
    for j in range(4):
        z = 1.46 + j * 0.30
        wsegs.append(((-0.45, 1.985, z), (0.66, 1.985, z)))
    reg(core.add_segments(sc, wsegs, 0.0035, core.sc_x(BONE, 0.11), name="window"))
    reg(core.add_polyline(sc, [(-0.48, 1.978, 1.43), (0.69, 1.978, 1.43), (0.69, 1.978, 2.39),
                               (-0.48, 1.978, 2.39)], 0.006, core.sc_x(BONE, 0.30), cyclic=True))
    reg(mesh_box((1.26, 0.10, 0.045), INK, "sill", core.mat_lit(INK, 0.5, 0.1), (0.105, 1.96, 1.42)))
    reg(core.add_polyline(sc, [(-0.53, 1.95, 1.445), (0.74, 1.95, 1.445)], 0.004,
                          core.sc_x(BONE, 0.22)))

    # a chair, turned to the desk; bone outline in the screen's warm pool
    cseat = reg(mesh_box((0.44, 0.42, 0.06), INK, "chairseat", core.mat_lit(INK, 0.45, 0.08),
                         (0.70, 0.64, 0.46), bevel=0.008))
    reg(mesh_box((0.44, 0.055, 0.50), INK, "chairback", core.mat_lit(INK, 0.45, 0.08),
                 (0.70, 0.84, 0.79), bevel=0.008))
    reg(core.add_polyline(sc, [(0.48, 0.812, 0.54), (0.92, 0.812, 0.54), (0.92, 0.812, 1.04),
                               (0.48, 0.812, 1.04)], 0.0035, core.sc_x(BONE, 0.22), cyclic=True, name="chairline"))
    reg(core.add_polyline(sc, [(0.48, 0.43, 0.49), (0.92, 0.43, 0.49), (0.92, 0.85, 0.49),
                               (0.48, 0.85, 0.49)], 0.0030, core.sc_x(BONE, 0.16), cyclic=True))
    reg(core.add_cylinder(sc, (0.70, 0.64, 0.24), 0.028, 0.40, INK, name="chairpost",
                          material=core.mat_lit(INK, 0.4, 0.2), verts=16))
    for a in (0.4, 1.9, 3.5, 5.0):
        reg(core.add_polyline(sc, [(0.70, 0.64, 0.07), (0.70 + math.cos(a) * 0.27, 0.64 + math.sin(a) * 0.27, 0.07)],
                              0.020, core.sc_x(GRAPH, 0.6), name="chairleg"))
    reg(core.add_polyline(sc, [(0.48, 0.42, 0.46), (0.70, 0.42, 0.46), (0.92, 0.42, 0.46)], 0.0025,
                          core.sc_x(BONE, 0.14)))

    reg(mesh_box((0.66, 0.17, 0.025), INK, "shelf", core.mat_lit(INK, 0.5, 0.2), (-0.52, -1.25, 1.42)))
    reg(core.add_polyline(sc, [(-0.85, -1.16, 1.435), (-0.19, -1.16, 1.435)], 0.004,
                          core.sc_x(BONE, 0.22)))
    for i, (bx, bh, bw, tilt) in enumerate([(-0.78, 0.20, 0.045, 0.0), (-0.72, 0.17, 0.035, 0.0),
                                            (-0.66, 0.22, 0.05, 0.12), (-0.58, 0.14, 0.11, 0.0)]):
        reg(mesh_box((bw, 0.13, bh), core.sc_x(BONE, 0.10), f"book{i}",
                     core.mat_lit(core.sc_x(BONE, 0.06), 0.7, 0.0),
                     (bx, -1.25, 1.435 + bh / 2), rot=(0, 0, tilt)))
        reg(core.add_polyline(sc, [(bx - bw / 2, -1.178, 1.435), (bx - bw / 2, -1.178, 1.435 + bh),
                                   (bx + bw / 2, -1.178, 1.435 + bh), (bx + bw / 2, -1.178, 1.435)],
                              0.0025, core.sc_x(BONE, 0.16)))

    reg(mesh_box((0.52, 0.02, 0.42), core.sc_x(BONE, 0.05), "print",
                 core.mat_lit(core.sc_x(BONE, 0.04), 0.8, 0.0), (0.85, -1.335, 1.72)))
    reg(core.add_polyline(sc, [(0.59, -1.32, 1.51), (1.11, -1.32, 1.51), (1.11, -1.32, 1.93),
                               (0.59, -1.32, 1.93)], 0.006, core.sc_x(BONE, 0.30), cyclic=True))

    reg(core.add_cylinder(sc, (-0.48, -0.22, top + 0.045), 0.043, 0.09, core.sc_x(BONE, 0.35),
                          name="mug", material=core.mat_lit(core.sc_x(BONE, 0.10), 0.55, 0.0), verts=28))
    hp = []
    for i in range(15):
        a = -1.2 + 2.4 * i / 14
        hp.append((-0.48 + 0.063 + 0.016 * math.cos(a), -0.22, top + 0.045 + 0.028 * math.sin(a)))
    reg(core.add_polyline(sc, hp, 0.008, core.sc_x(BONE, 0.35), name="mughandle"))

    reg(mesh_box((0.20, 0.26, 0.012), core.sc_x(BONE, 0.10), "notebook",
                 core.mat_lit(core.sc_x(BONE, 0.07), 0.8, 0.0), (0.70, 0.20, top + 0.006),
                 rot=(0, 0, math.radians(-14))))
    reg(core.add_polyline(sc, [(0.615, 0.335, top + 0.013), (0.795, 0.335, top + 0.013)], 0.0025,
                          core.sc_x(BONE, 0.24)))
    reg(core.add_polyline(sc, [(0.74, 0.10, top + 0.019), (0.80, 0.32, top + 0.019)], 0.006,
                          core.sc_x(BONE, 0.5), name="pencil"))

    cp = []
    for i in range(30):
        u = i / 29
        cp.append((0.46 + 0.05 * u + 0.10 * math.sin(u * 3.0), 0.02 + 0.32 * u,
                   top + 0.008 - 0.004 * math.sin(u * 6)))
    cp += [(0.60, 0.47, top - 0.06), (0.59, 0.50, top - 0.35), (0.57, 0.52, 0.02)]
    reg(core.add_polyline(sc, cp, 0.006, core.sc_x(GRAPH, 1.0), name="cable"))


# ----------------------------------------------------------------------------- laptop
def build_laptop(sc, T, ROOM):
    reg = ROOM.append
    LX, LY = 0.30, -0.04
    TOP = 0.74
    BASE_W, BASE_D, BASE_T = 0.36, 0.235, 0.016
    HINGE = Vector((LX, LY - BASE_D / 2, TOP + BASE_T + 0.001))
    LID_L, LID_W, LID_T = 0.235, 0.36, 0.007
    OPEN = math.radians(112)

    reg(mesh_box((BASE_W, BASE_D, BASE_T), INK, "laptopbase",
                 core.mat_lit(core.sc_x(ASH, 0.22), 0.34, 0.55), (LX, LY, TOP + BASE_T / 2), bevel=0.006))
    reg(quad(BASE_W * 0.94, BASE_D * 0.92, INK, "keywell",
             core.mat_lit(INK, 0.55, 0.25), (LX, LY + 0.004, TOP + BASE_T + 0.0008),
             rot=(math.radians(90), 0, 0)))
    # keyboard: one mesh of keycaps
    me = bpy.data.meshes.new("keys")
    bm = bmesh.new()
    keyw, keyd, keyh, gap = 0.0205, 0.0180, 0.0032, 0.0016
    rows, cols = 4, 14
    x0 = LX - (cols * (keyw + gap) - gap) / 2 + keyw / 2
    y0 = LY - 0.072
    for r in range(rows):
        for c in range(cols):
            cx = x0 + c * (keyw + gap)
            cy = y0 + r * (keyd + gap)
            vs = []
            for dz in (-1, 1):
                for dy in (-1, 1):
                    for dx in (-1, 1):
                        vs.append(bm.verts.new((cx + dx * keyw / 2, cy + dy * keyd / 2,
                                                TOP + BASE_T + keyh / 2 + dz * keyh / 2)))
            for f in [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]:
                try:
                    bm.faces.new([vs[i] for i in f])
                except ValueError:
                    pass
    bm.to_mesh(me)
    bm.free()
    keys = link(bpy.data.objects.new("keys", me))
    me.materials.append(core.mat_lit(core.sc_x(ASH, 0.20), 0.5, 0.1))
    keys.color = (*core.sc_x(BONE, 0.25), 1)
    reg(keys)
    reg(quad(0.095, 0.060, core.sc_x(ASH, 0.10), "trackpad",
             core.mat_lit(core.sc_x(GRAPH, 0.35), 0.3, 0.5), (LX, LY + 0.078, TOP + BASE_T + 0.0012),
             rot=(math.radians(90), 0, 0)))
    reg(core.add_polyline(sc, [(LX - 0.048, LY + 0.048, TOP + BASE_T + 0.0016),
                               (LX + 0.048, LY + 0.048, TOP + BASE_T + 0.0016),
                               (LX + 0.048, LY + 0.108, TOP + BASE_T + 0.0016),
                               (LX - 0.048, LY + 0.108, TOP + BASE_T + 0.0016)],
                          0.0022, core.sc_x(BONE, 0.20), cyclic=True))
    reg(core.add_polyline(sc, [(LX - BASE_W / 2 + 0.004, LY - BASE_D / 2 + 0.01, TOP + BASE_T + 0.0005),
                               (LX + BASE_W / 2 - 0.004, LY - BASE_D / 2 + 0.01, TOP + BASE_T + 0.0005)],
                          0.0025, core.sc_x(BONE, 0.16)))

    # lid rig
    lid = link(bpy.data.objects.new("lidrig", None))
    lid.location = HINGE
    reg(lid)
    lidmesh = mesh_box((LID_W, LID_L, LID_T), INK, "lid",
                       core.mat_hatch_lit(INK, GRAPH, 240, 90, 1.0, 0.28, 0.16, core.sc_x(ASH, 0.7), 0.015))
    lidmesh.data.transform(Matrix.Translation((0, LID_L / 2, -LID_T / 2)))
    lidmesh.parent = lid
    lidmesh.location = (0, 0, 0)
    reg(lidmesh)
    ledge = core.add_polyline(sc, [(-LID_W / 2, 0, 0.0007), (-LID_W / 2, LID_L, 0.0007),
                                   (LID_W / 2, LID_L, 0.0007), (LID_W / 2, 0, 0.0007)],
                              0.0016, core.sc_x(BONE, 0.20), name="lidedge", cyclic=True)
    ledge.parent = lid
    reg(ledge)
    reg(core.add_polyline(sc, [(LX - BASE_W / 2, LY - BASE_D / 2, TOP + BASE_T + 0.0004),
                               (LX - BASE_W / 2, LY + BASE_D / 2, TOP + BASE_T + 0.0004),
                               (LX + BASE_W / 2, LY + BASE_D / 2, TOP + BASE_T + 0.0004),
                               (LX + BASE_W / 2, LY - BASE_D / 2, TOP + BASE_T + 0.0004)],
                          0.0016, core.sc_x(BONE, 0.16), cyclic=True))
    for sx in (-1, 1):
        hb = core.add_cylinder(sc, (HINGE.x + sx * 0.155, HINGE.y + 0.002, HINGE.z - 0.005),
                               0.008, 0.035, core.sc_x(ASH, 0.2), name="hinge",
                               rot=(0, math.radians(90), 0),
                               material=core.mat_lit(core.sc_x(ASH, 0.25), 0.3, 0.7), verts=20)
        hb.parent = lid
        hb.location = (sx * 0.155, 0.002, -0.005)
        hb.rotation_euler = (0, math.radians(90), 0)
        reg(hb)

    # screen rig (inner face), rotated 180 about lid Y so text reads from the front
    rig = link(bpy.data.objects.new("screenrig", None))
    rig.parent = lid
    rig.location = (0, 0.122, -0.0082)
    rig.rotation_euler = (0, math.pi, 0)
    reg(rig)
    bz = quad(0.334, 0.196, INK, "bezel", core.mat_lit(INK, 0.5, 0.2))
    bz.parent = rig
    bz.location = (0, 0, -0.0008)
    reg(bz)
    scr = quad(0.300, 0.166, BONE, "screen", screen_material())
    scr.parent = rig
    scr.location = (0, 0, 0.0)
    reg(scr)
    # hot hairline rim: the screen's own glow, not a white card
    sr = core.add_polyline(sc, [(-0.15, -0.083, 0.0006), (0.15, -0.083, 0.0006),
                                (0.15, 0.083, 0.0006), (-0.15, 0.083, 0.0006)],
                           0.0013, core.mixc(core.sc_x(BONE, 0.6), EMB, 0.55), name="screenrim",
                           cyclic=True, hot=True)
    sr.parent = rig
    reg(sr)
    for i in range(5):
        b = quad(0.055 + 0.018 * ((i * 37) % 3), 0.0055, core.sc_x(ASH, 0.5), f"cb{i}",
                 core.mat_emit(core.sc_x(BONE, 0.16), 1.0))
        b.parent = rig
        b.location = (-0.055, 0.046 - i * 0.0165, 0.0004)
        reg(b)
    cpts = []
    for i in range(40):
        u = i / 39
        cpts.append((-0.10 + 0.20 * u, -0.055 + 0.16 * (u ** 4), 0.0005))
    cc = core.add_polyline(sc, cpts, 0.0022, core.sc_x(BONE, 0.24), name="cplot")
    cc.parent = rig
    reg(cc)

    # redaction rig
    rrig = link(bpy.data.objects.new("redactrig", None))
    rrig.parent = rig
    rrig.location = (0, 0, 0.0016)
    reg(rrig)
    rbar = quad(0.266, 0.074, core.sc_x(BONE, 0.82), "redactbar", core.mat_emit(core.sc_x(BONE, 0.82), 1.0))
    rbar.parent = rrig
    reg(rbar)
    rtxt = core.add_text(sc, "REDACTED", "mono_bold", 0.0275, core.sc_x(INK, 1.0), (0, -0.0098, 0.0007),
                         align_x="CENTER", name="redacted", spacing=1.22)
    rtxt.parent = rrig
    rtxt.location = (0, -0.0098, 0.0007)
    reg(rtxt)
    redact = [rbar, rtxt]
    for sy in (-1, 1):
        q = quad(0.266, 0.0009, core.sc_x(INK, 1.0), "rrule", core.mat_emit(core.sc_x(INK, 1.0), 1.0))
        q.parent = rrig
        q.location = (0, sy * 0.0375, 0.0008)
        reg(q)
        redact.append(q)

    al = core.add_light(sc, "AREA", (0, 0, 0), 1.9, core.mixc(core.sc_x(BONE, 0.9), EMB, 0.45), size=0.26, name="screenlight")
    al.parent = lid
    al.location = (0, 0.122, -0.035)
    al.data.shape = "RECTANGLE"
    al.data.size = 0.28
    al.data.size_y = 0.15
    reg(al)
    pl = core.add_light(sc, "POINT", (0, 0, 0), 0.22, core.mixc(core.sc_x(BONE, 0.9), EMB, 0.5), size=0.14, name="screenglow")
    pl.parent = lid
    pl.location = (0, 0.122, -0.09)
    reg(pl)

    ledpos = (LX + 0.148, LY + BASE_D / 2 + 0.0012, TOP + 0.008)
    led = core.add_disc(sc, 0, 0, 0.0026, SIG, z=0, name="led", hot=True)
    led.rotation_euler = (math.radians(-90), 0, 0)
    led.location = ledpos
    reg(led)
    ledl = core.add_light(sc, "POINT", (ledpos[0], ledpos[1] + 0.02, ledpos[2]), 0.0,
                          core.sc_x(SIG, 1.0), size=0.012, name="ledlight")
    reg(ledl)

    # slit light at the front gap (world space, faces +Y)
    slitq = quad_xz(0.30, 0.0038, EMB, "slit", core.mat_hot(), (LX, LY + BASE_D / 2, TOP + 0.032))
    reg(slitq)

    # stickers
    root = link(bpy.data.objects.new("stickers", None))
    root.parent = lid
    root.location = (0, 0, 0.0015)
    reg(root)
    build_stickers(sc, root, ROOM)
    return dict(lid=lid, rig=rig, redact=redact, rrig=rrig, screen=scr, hinge=HINGE,
                led=led, ledlight=ledl, slidelight=al, screenglow=pl, slit=slitq,
                LX=LX, LY=LY, TOP=TOP, BASE_D=BASE_D, OPEN=OPEN, LID_L=LID_L)


def build_stickers(sc, root, ROOM):
    reg = ROOM.append
    c_bone = core.sc_x(BONE, 0.46)
    c_ink = core.sc_x(INK, 1.0)
    c_sig = core.sc_x(SIG, 0.46)

    def panel(x, y, rot=0.0):
        st = link(bpy.data.objects.new("sticker", None))
        st.parent = root
        st.location = (x, y, 0.0)
        st.rotation_euler = (0, 0, rot)
        reg(st)
        return st

    def put(ob, st, loc=(0, 0, 0), rot=0.0):
        ob.parent = st
        ob.location = loc
        ob.rotation_euler = (0, 0, rot)
        reg(ob)
        return ob

    # 1 FEEL THE AGI
    st = panel(0.0, 0.190, -0.07)
    put(quad(0.272, 0.070, c_bone, "st1cut"), st, (0, 0, 0))
    put(quad(0.260, 0.060, c_sig, "st1"), st, (0, 0, 0.0006))
    t = core.add_text(sc, "FEEL THE AGI", "archivo700", 0.028, c_ink, (0, -0.009, 0),
                      align_x="CENTER", name="st1t")
    put(t, st, (0, -0.009, 0.0012))

    # 2 the mask
    st = panel(0.145, 0.119, 0.10)
    put(core.add_disc(sc, 0, 0, 0.030, c_bone, z=0, name="st2disc", segments=48), st)
    for sx in (-0.0095, 0.0095):
        put(core.add_disc(sc, sx, 0.006, 0.0024, c_ink, z=0.0006, name="st2eye"), st, (0, 0, 0.0006))
    sm = []
    for i in range(13):
        a = math.radians(-42 + 84 * i / 12)
        sm.append((math.sin(a) * 0.015, -0.009 + (1 - math.cos(a)) * 0.008, 0.0008))
    put(core.add_polyline(sc, sm, 0.0018, c_ink, name="st2smile"), st, (0, 0, 0.0008))

    # 3 TikZ unicorn die-cut
    st = panel(-0.064, 0.096, 0.045)
    put(quad(0.128, 0.126, c_bone, "st3cut"), st)
    put(quad(0.118, 0.116, c_ink, "st3ink"), st, (0, 0, 0.0005))
    u = link(bpy.data.objects.new("unicorn", None))
    u.parent = st
    u.location = (0, 0.002, 0.001)
    u.scale = (1.32, 1.32, 1)
    reg(u)
    unicorn_lines(sc, u, ROOM, c_bone, c_sig)

    # 4 SLIGHTLY CONSCIOUS (oval)
    st = panel(0.118, 0.075, -0.14)
    ov = core.add_disc(sc, 0, 0, 0.040, c_bone, z=0, name="st4disc", segments=48)
    put(ov, st)
    ov.scale = (0.95, 0.60, 1.0)
    t1 = core.add_text(sc, "SLIGHTLY", "mono_med", 0.0128, c_ink, (0, 0.0025, 0.001),
                       align_x="CENTER", name="st4a")
    put(t1, st, (0, 0.0025, 0.001))
    t2 = core.add_text(sc, "CONSCIOUS", "mono_med", 0.0128, c_ink, (0, -0.0115, 0.001),
                       align_x="CENTER", name="st4b")
    put(t2, st, (0, -0.0115, 0.001))

    # 5 Q* star
    st = panel(0.030, 0.058, 0.28)
    starpts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        r = 0.026 if i % 2 == 0 else 0.0115
        starpts.append((math.cos(a) * r, math.sin(a) * r, 0.0004))
    put(core.add_polyline(sc, starpts, 0.0018, c_bone, name="st5star", cyclic=True), st, (0, 0, 0.0004))
    q = core.add_text(sc, "Q*", "serif_italic600", 0.021, c_sig, (0, -0.0075, 0.0012),
                      align_x="CENTER", name="st5q")
    put(q, st, (0, -0.0075, 0.0012))

    # 6 bumper strip
    st = panel(0.080, 0.007, 0.01)
    put(quad(0.224, 0.026, c_ink, "st6strip"), st)
    put(core.add_polyline(sc, [(-0.108, -0.011, 0.0007), (0.108, -0.011, 0.0007),
                               (0.108, 0.011, 0.0007), (-0.108, 0.011, 0.0007)], 0.0011, c_bone,
                          name="st6rule", cyclic=True), st)
    t6 = core.add_text(sc, "attention is all you need", "serif_italic", 0.016, c_bone,
                       (0, -0.0053, 0.0012), align_x="CENTER", name="st6")
    put(t6, st, (0, -0.0053, 0.0012))


def unicorn_lines(sc, parent, ROOM, bone, sig):
    def ln(pts, w=0.0016, col=None, name="u"):
        ob = core.add_polyline(sc, [(p[0], p[1], p[2]) for p in pts], w, col or bone, name=name)
        ob.parent = parent
        ROOM.append(ob)
        return ob

    z = 0.0
    ln([(-0.020, -0.002, z), (0.020, -0.002, z), (0.023, 0.016, z), (-0.016, 0.016, z),
        (-0.020, -0.002, z)], 0.0018)
    ln([(0.018, 0.012, z), (0.030, 0.034, z), (0.040, 0.043, z)], 0.0018)
    ln([(0.030, 0.034, z), (0.044, 0.036, z), (0.046, 0.028, z), (0.038, 0.024, z)], 0.0018)
    ln([(0.046, 0.036, z), (0.043, 0.040, z), (0.047, 0.043, z)], 0.0014)
    ln([(0.039, 0.044, z), (0.033, 0.060, z), (0.041, 0.045, z)], 0.0022, sig, "uhorn")
    for lx in (-0.014, -0.006, 0.008, 0.016):
        ln([(lx, -0.002, z), (lx - 0.001, -0.026, z)], 0.0017)
        ln([(lx - 0.001, -0.026, z), (lx + 0.003, -0.026, z)], 0.0015)
    mane = []
    for i in range(7):
        a = i / 6
        mane.append((0.018 + 0.010 * math.sin(a * 3.0), 0.014 + 0.030 * a, z))
    ln(mane, 0.0014)
    ln([(-0.020, 0.004, z), (-0.030, 0.010, z), (-0.028, 0.024, z)], 0.0014)
    ln([(-0.038, -0.030, z), (0.050, -0.030, z)], 0.0010, core.sc_x(bone, 0.5))


# ----------------------------------------------------------------------------- lyric overlay
def build_lyric_overlay(sc, cam, T, ROOM):
    rig = link(bpy.data.objects.new("lyricrig", None))
    rig.parent = cam
    rig.location = (0, 0, -1.0)
    ROOM.append(rig)
    dim = core.sc_x(BONE, 0.42)
    bone = core.sc_x(BONE, 0.94)
    x0, y1, y2 = -0.30, 0.138, 0.083
    size = 0.055
    space = core.space_width(sc, "serif_italic", size)
    rows = [T["w1"][:4], T["w1"][4:]]
    objs = []
    positions = {}
    for ri, ws in enumerate(rows):
        x = x0
        y = y1 if ri == 0 else y2
        for w in ws:
            ob = core.add_text(sc, w["w"], "serif_italic", size, dim, (x, y, 0),
                               name=f"ly{ri}_{w['w'][:4]}", spacing=1.0)
            ob.parent = rig
            ob.location = (x, y, 0)
            objs.append((w, ob))
            ww = core.measure(sc, w["w"], "serif_italic", size)
            positions[w["w"]] = (x, ww)
            x += ww + space
    print("LYRIC row1 x-end", round(x, 3))

    f_rev = core.frame_of(sc, T["w1"][0]["start"] - 0.10)
    f_out0 = core.frame_of(sc, T["led_off"] - 0.06)
    f_out1 = core.frame_of(sc, T["led_off"])
    black = (0.0, 0.0, 0.0)
    for w, ob in objs:
        core.color_at(ob, 1, black)
        core.color_at(ob, max(1, f_rev), dim)
        core.color_at(ob, max(f_rev, core.frame_of(sc, w["start"] - 0.22)), dim)
        core.color_at(ob, max(2, core.frame_of(sc, w["start"])), core.sc_x(SIG, 0.95))
        core.color_at(ob, max(3, core.frame_of(sc, w["end"] + 0.22)), bone)
        core.color_at(ob, max(4, f_out0), bone)
        core.color_at(ob, max(5, f_out1), black)
        core.set_interp(ob, "BEZIER", "color")

    kx, kw = positions["know"]
    barw = kw + 0.012
    barh = 0.054
    left = kx - 0.005
    bottom = y2 - 0.011
    kb = link(bpy.data.objects.new("knowbar", None))
    kb.parent = rig
    kb.location = (left, bottom, 0.004)
    ROOM.append(kb)
    fill = quad(barw, barh, core.sc_x(INK, 1.0), "kbfill", core.mat_emit(core.sc_x(INK, 1.0), 1.0))
    fill.data.transform(Matrix.Translation((barw / 2, barh / 2, 0)))
    fill.parent = kb
    fill.location = (0, 0, 0)
    ROOM.append(fill)
    border = core.add_polyline(sc, [(0, 0, 0.0004), (barw, 0, 0.0004), (barw, barh, 0.0004),
                                    (0, barh, 0.0004)], 0.0016, core.sc_x(BONE, 0.34),
                               name="kbborder", cyclic=True)
    border.parent = kb
    border.location = (0, 0, 0.0004)
    ROOM.append(border)
    wt = core.add_text(sc, "WITHHELD", "mono_bold", 0.0088, core.sc_x(SIG, 0.95),
                       (barw / 2, -0.021, 0.0006), align_x="CENTER", name="withheld", spacing=1.3)
    wt.parent = kb
    wt.location = (barw / 2, -0.021, 0.0006)
    ROOM.append(wt)

    core.show_at(fill, 1, False)
    core.show_at(border, 1, False)
    core.show_at(wt, 1, False)
    core.show_at(fill, core.frame_of(sc, T["know_bar"] - 0.03), True)
    core.show_at(border, core.frame_of(sc, T["know_bar"] - 0.03), True)
    core.show_at(wt, core.frame_of(sc, T["know_bar"] + 0.10), True)
    for o in (fill, border, wt):
        core.show_at(o, core.frame_of(sc, T["led_off"] - 0.05), False)
    kb.scale = (0.0, 1, 1)
    kb.keyframe_insert("scale", frame=max(1, core.frame_of(sc, T["know_bar"] - 0.03)))
    kb.scale = (1.0, 1, 1)
    kb.keyframe_insert("scale", frame=max(2, core.frame_of(sc, T["know_bar"] + 0.12)))
    core.set_interp(kb, "BEZIER", "scale")
    return rig, objs


# ----------------------------------------------------------------------------- theatre
def curtain_mesh(sc, side, mat, color, THEATRE):
    nx, nz = 64, 14
    verts, faces = [], []
    for j in range(nz + 1):
        z = 5.65 * j / nz
        for i in range(nx + 1):
            u = i / nx
            x = -side * 5.6 * u
            y = 0.075 * math.sin(u * 34.0 + 0.7) + 0.012 * math.sin(z * 2.2 + u * 7.0) - 0.02
            verts.append((x, y, z))
    for j in range(nz):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    me = bpy.data.meshes.new("curtain")
    me.from_pydata(verts, [], faces)
    me.update()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(mat)
    ob = link(bpy.data.objects.new("curtain", me))
    ob.color = (*color, 1)
    ob.location = (side * 5.6, TY + 49.86, 0)
    md = ob.modifiers.new("sol", "SOLIDIFY")
    md.thickness = 0.012
    md.offset = 0
    THEATRE.append(ob)
    cu = bpy.data.curves.new("folds", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.003
    for k in range(23):
        u = (k + 0.5) / 23
        x = -side * 5.6 * u
        sp = cu.splines.new("POLY")
        sp.points.add(11)
        for j in range(12):
            z = 5.6 * j / 11
            y = 0.075 * math.sin(u * 34.0 + 0.7) + 0.012 * math.sin(z * 2.2 + u * 7.0) - 0.018
            sp.points[j].co = (x, y, z, 1)
    cu.materials.append(core.mat_type())
    fo = link(bpy.data.objects.new("folds", cu))
    fo.color = (*core.sc_x(BONE, 0.09), 1)
    fo.parent = ob
    THEATRE.append(fo)
    return ob


def build_theatre(sc, T, THEATRE):
    reg = THEATRE.append
    reg(mesh_box((16.0, 12.0, 0.05), INK, "stagefloor",
                 core.mat_hatch_lit(core.sc_x(ASH, 0.10), core.sc_x(ASH, 0.38), 26, 0, 1.2, 0.55, 0.14, core.sc_x(ASH, 0.8), 0.008),
                 (0, TY + 46, -0.025)))
    reg(mesh_box((16.0, 0.08, 9.0), INK, "stageback",
                 core.mat_hatch_lit(INK, GRAPH, 20, 90, 1.0, 0.6, 0.1, EMB, 0.004),
                 (0, TY + 40.0, 4.5)))
    segs = []
    for j in range(14):
        z = 0.4 + j * 0.6
        segs.append(((-7.9, TY + 40.05, z), (7.9, TY + 40.05, z)))
    reg(core.add_segments(sc, segs, 0.004, core.sc_x(BONE, 0.05), name="backlines"))

    pmat = core.mat_lit(core.sc_x(INK, 1.0), 0.62, 0.08)
    for sx in (-1, 1):
        reg(mesh_box((2.0, 0.5, 7.6), INK, "leg", pmat, (sx * 6.6, TY + 50.5, 3.8)))
        for i in range(6):
            x = sx * (5.78 + i * 0.26)
            reg(core.add_polyline(sc, [(x, TY + 50.76, 0.15), (x, TY + 50.76, 7.25)], 0.0045,
                                  core.sc_x(BONE, 0.08)))
    reg(mesh_box((15.2, 0.5, 1.9), INK, "fascia", pmat, (0, TY + 50.5, 6.45)))
    reg(mesh_box((15.6, 0.62, 0.22), INK, "cornice", pmat, (0, TY + 50.5, 7.5)))
    for z in (5.52, 7.32):
        reg(core.add_polyline(sc, [(-7.55, TY + 50.77, z), (7.55, TY + 50.77, z)], 0.007,
                              core.sc_x(BONE, 0.18)))
    reg(core.add_polyline(sc, [(-7.55, TY + 50.77, 5.52), (-7.55, TY + 50.77, 7.32)], 0.004,
                          core.sc_x(BONE, 0.12)))
    # inner opening hairline: the proscenium reads as architecture
    reg(core.add_polyline(sc, [(-5.62, TY + 50.78, 0.02), (-5.62, TY + 50.78, 5.48),
                               (5.62, TY + 50.78, 5.48), (5.62, TY + 50.78, 0.02)], 0.010,
                          core.sc_x(BONE, 0.26)))
    # pilasters + capitals on the legs
    for sx in (-1, 1):
        reg(mesh_box((0.74, 0.10, 6.4), INK, "pilaster", pmat, (sx * 7.05, TY + 50.79, 3.35), bevel=0.01))
        reg(mesh_box((0.90, 0.16, 0.22), INK, "capital", pmat, (sx * 7.05, TY + 50.80, 6.62), bevel=0.01))
        reg(mesh_box((0.90, 0.18, 0.26), INK, "pedestal", pmat, (sx * 7.05, TY + 50.80, 0.20), bevel=0.01))
        for z in (0.36, 6.48):
            reg(core.add_polyline(sc, [(sx * 7.05 - 0.36, TY + 50.86, z), (sx * 7.05 + 0.36, TY + 50.86, z)],
                                  0.006, core.sc_x(BONE, 0.20)))
        reg(core.add_polyline(sc, [(sx * 7.05 - 0.37, TY + 50.86, 0.36), (sx * 7.05 - 0.37, TY + 50.86, 6.48),
                                   (sx * 7.05 + 0.37, TY + 50.86, 6.48), (sx * 7.05 + 0.37, TY + 50.86, 0.36)],
                              0.0035, core.sc_x(BONE, 0.15)))
        for i in range(7):
            x = sx * 7.05 + (i - 3) * 0.095
            reg(core.add_polyline(sc, [(x, TY + 50.855, 0.40), (x, TY + 50.855, 6.44)], 0.003,
                                  core.sc_x(BONE, 0.10)))
    # dentils under the cornice
    for i in range(29):
        x = -7.2 + i * 0.515
        reg(core.add_polyline(sc, [(x, TY + 50.815, 7.20), (x, TY + 50.815, 7.31)], 0.010,
                              core.sc_x(BONE, 0.16)))
    # stage lip under the opening
    reg(mesh_box((11.2, 0.28, 0.24), INK, "stagelip", pmat, (0, TY + 50.34, 0.12), bevel=0.008))
    reg(core.add_polyline(sc, [(-5.6, TY + 50.48, 0.245), (5.6, TY + 50.48, 0.245)], 0.008,
                          core.sc_x(BONE, 0.24)))

    cmat = core.mat_hatch_lit(core.sc_x(INK, 1.0), core.sc_x(ASH, 0.62), 15, 90, 1.6, 0.60, 0.34, core.sc_x(ASH, 0.9), 0.03)
    cl = curtain_mesh(sc, -1, cmat, core.sc_x(BONE, 0.1), THEATRE)
    cr = curtain_mesh(sc, 1, cmat, core.sc_x(BONE, 0.1), THEATRE)
    # valance: a scalloped band hung across the top of the opening
    vnx, vnz = 72, 6
    vv, vf = [], []
    for j in range(vnz + 1):
        for i in range(vnx + 1):
            u = i / vnx
            x = -5.62 + 11.24 * u
            ztop = 5.58
            zb = 5.02 + 0.085 * abs(math.sin(u * math.pi * 8.0))
            z = ztop - (ztop - zb) * (j / vnz)
            y = TY + 49.93 + 0.035 * math.sin(u * 60.0) + 0.012 * math.sin(j * 1.7 + u * 9.0)
            vv.append((x, y, z))
    for j in range(vnz):
        for i in range(vnx):
            a = j * (vnx + 1) + i
            vf.append((a, a + 1, a + vnx + 2, a + vnx + 1))
    vme = bpy.data.meshes.new("valance")
    vme.from_pydata(vv, [], vf)
    vme.update()
    for p in vme.polygons:
        p.use_smooth = True
    vme.materials.append(cmat)
    vo = link(bpy.data.objects.new("valance", vme))
    vo.color = (*core.sc_x(BONE, 0.1), 1)
    THEATRE.append(vo)
    # scalloped bottom hairline
    scallop = []
    for i in range(145):
        u = i / 144
        x = -5.62 + 11.24 * u
        z = 5.02 + 0.085 * abs(math.sin(u * math.pi * 8.0))
        scallop.append((x, TY + 49.895, z))
    reg(core.add_polyline(sc, scallop, 0.006, core.sc_x(BONE, 0.22), name="valanceedge"))

    seam = quad_xz(0.4, 5.4, EMB, "seam", core.mat_hot(), (0, TY + 49.70, 2.8))

    spot = core.add_light(sc, "SPOT", (0, TY + 46, 9.2), 0.0, core.mixc(core.sc_x(BONE, 0.95), EMB, 0.30),
                          size=0.35, name="spot")
    spot.data.spot_size = math.radians(27.0)
    spot.data.spot_blend = 0.45
    core.look_at(spot, (0, TY + 46, 0))
    reg(spot)
    fill = core.add_light(sc, "AREA", (0, TY + 58.0, 5.2), 7.0, core.sc_x(BONE, 0.85), size=6.0, name="housefill")
    for sx in (-1, 1):
        rake = core.add_light(sc, "AREA", (sx * 8.0, TY + 54.5, 2.2), 9.0, core.sc_x(EMBER_MIX, 1.0),
                              size=1.6, name="raking")
        core.look_at(rake, (-sx * 5.4, TY + 50.2, 2.8))
        reg(rake)
    core.look_at(fill, (0, TY + 50.0, 3.6))
    reg(fill)

    # a soft volume-ish shaft: a translucent cone shell (plus a few engraved rays)
    bm = bpy.data.materials.new("beamcone")
    bm.use_nodes = True
    nt = bm.node_tree
    nt.nodes.clear()
    bo_ = nt.nodes.new("ShaderNodeOutputMaterial")
    mixs = nt.nodes.new("ShaderNodeMixShader")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[0].default_value = (*core.mixc(core.sc_x(BONE, 0.35), EMB, 0.35), 1)
    em.inputs[1].default_value = 1.2
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.0
    mr.inputs["From Max"].default_value = 1.0
    mr.inputs["To Min"].default_value = 0.20
    mr.inputs["To Max"].default_value = 0.015
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], mixs.inputs["Fac"])
    nt.links.new(tr.outputs[0], mixs.inputs[1])
    nt.links.new(em.outputs[0], mixs.inputs[2])
    nt.links.new(mixs.outputs[0], bo_.inputs["Surface"])
    bm.surface_render_method = "BLENDED"
    bm.use_backface_culling = False
    bm.use_transparent_shadow = False

    apex = Vector((0, TY + 46, 9.2))
    crings, csegs = 14, 48
    cv, cf = [], []
    for j in range(crings + 1):
        z = 9.2 * (1 - j / crings)
        rad = 0.02 + (j / crings) * 1.95
        for i in range(csegs):
            a = i / csegs * math.tau
            cv.append((math.cos(a) * rad, TY + 46 + math.sin(a) * rad, z))
    for j in range(crings):
        for i in range(csegs):
            a = j * csegs + i
            b = j * csegs + (i + 1) % csegs
            cf.append((a, b, b + csegs, a + csegs))
    cme = bpy.data.meshes.new("beamcone")
    cme.from_pydata(cv, [], cf)
    cme.update()
    cme.materials.append(bm)
    co = link(bpy.data.objects.new("beamcone", cme))
    co.color = (1, 1, 1, 1)
    reg(co)

    beams = []
    for i in range(10):
        a = i / 10 * math.tau
        beams.append([(apex.x, apex.y, apex.z),
                      (math.cos(a) * 1.75, TY + 46 + math.sin(a) * 1.75, 0.0)])
    for k in (4, 7):
        z = k * 1.0
        r = (9.2 - z) / 9.2 * 1.75
        pts = []
        for i in range(48):
            a = i / 48 * math.tau
            pts.append((math.cos(a) * r, TY + 46 + math.sin(a) * r, z))
        pts.append(pts[0])
        beams.append(pts)
    cu = bpy.data.curves.new("beam", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.006
    for pts in beams:
        sp = cu.splines.new("POLY")
        sp.points.add(len(pts) - 1)
        for i, p in enumerate(pts):
            sp.points[i].co = (*p, 1)
    cu.materials.append(core.mat_type())
    bo = link(bpy.data.objects.new("beam", cu))
    bo.color = (*core.sc_x(EMB, 0.07), 1)
    reg(bo)

    me = bpy.data.meshes.new("dust")
    verts, faces = [], []
    for i in range(110):
        u = hash01(i, 3)
        a = hash01(i, 7) * math.tau
        z = 0.4 + hash01(i, 11) * 8.2
        r = (9.2 - z) / 9.2 * 1.68 * (0.25 + 0.75 * math.sqrt(u))
        cx, cy = math.cos(a) * r, TY + 46 + math.sin(a) * r
        s = 0.008 + 0.012 * hash01(i, 13)
        base = len(verts)
        verts += [(cx - s, cy, z - s), (cx + s, cy, z - s), (cx + s, cy, z + s), (cx - s, cy, z + s)]
        faces.append((base, base + 1, base + 2, base + 3))
    me.from_pydata(verts, [], faces)
    me.update()
    me.materials.append(core.mat_emit(core.sc_x(BONE, 0.9), 1.0))
    du = link(bpy.data.objects.new("dust", me))
    du.color = (*core.sc_x(BONE, 0.9), 1)
    reg(du)

    # engraved pool edge: concentric hairlines on the floor instead of an occluding decal
    for rr in (1.55, 1.9, 2.25):
        pts = []
        for i in range(72):
            a = i / 72 * math.tau
            pts.append((math.cos(a) * rr, TY + 46 + math.sin(a) * rr * 0.92, 0.004))
        reg(core.add_polyline(sc, pts, 0.0045, core.sc_x(EMB, 0.16), name="poolring", cyclic=True))

    for mx, my in [(-1.2, -1.1), (1.4, -1.6), (-0.6, 1.9), (2.2, 0.8), (0.2, 0.3)]:
        x, y = mx, TY + 46 + my
        for a, b in [((x - 0.10, y, 0.006), (x + 0.10, y, 0.006)),
                     ((x, y - 0.10, 0.006), (x, y + 0.10, 0.006))]:
            reg(core.add_polyline(sc, [a, b], 0.006, core.sc_x(BONE, 0.20)))

    words = T["w2"]
    size = 1.45
    gap = 0.62 * size
    widths = [core.measure(sc, w["w"].upper(), "serif600", size) for w in words]
    total = sum(widths) + gap * (len(words) - 1)
    if total > 12.6:
        k = 12.6 / total
        size *= k
        gap *= k
        widths = [core.measure(sc, w["w"].upper(), "serif600", size) for w in words]
        total = sum(widths) + gap * (len(words) - 1)
    x = total / 2
    zbase = 5.88
    for i, w in enumerate(words):
        ob = core.add_text(sc, w["w"].upper(), "serif600", size, core.sc_x(BONE, 0.10),
                           (x, TY + 50.78, zbase), rot=FACE_Y, name="pros" + str(i), spacing=1.0)
        reg(ob)
        core.color_at(ob, 1, core.sc_x(BONE, 0.10))
        core.color_at(ob, max(1, core.frame_of(sc, w["start"] - 0.2)), core.sc_x(BONE, 0.10))
        core.color_at(ob, max(2, core.frame_of(sc, w["start"])), core.sc_x(SIG, 0.98))
        core.color_at(ob, max(3, core.frame_of(sc, w["end"] + 0.22)), core.sc_x(BONE, 0.90))
        core.set_interp(ob, "BEZIER", "color")
        x -= widths[i] + gap
    print("THEATRE lyric total", round(total, 2), "size", round(size, 2))
    return dict(spot=spot, fill=fill, seam=seam, cl=cl, cr=cr)


# ----------------------------------------------------------------------------- cameras
def bake_quat(ob, q, f, prev):
    if prev is not None and q.dot(prev) < 0:
        q = -q
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = q
    ob.keyframe_insert("rotation_quaternion", frame=f)
    return q


def room_cam_fn(sc, T, L):
    OPEN = L["OPEN"]
    hinge = L["hinge"]
    led = Vector((L["LX"] + 0.148, L["LY"] + L["BASE_D"] / 2, L["TOP"] + 0.008))

    def lid_angle(t):
        return keys(t, [(T["well"]["start"] - 0.06, OPEN),
                        (T["never"]["start"], math.radians(81), ease_out_cubic),
                        (T["know"]["start"], math.radians(46), ease_out_cubic),
                        (T["slit"], math.radians(4), ease_in_out_cubic),
                        (T["dark"], math.radians(2)),
                        (T["dark"] + 0.22, 0.0)])

    def state(t):
        phi = keys(t, [(T["l1"]["start"] - 0.5, math.pi),
                       (T["what"]["start"], math.pi + 0.05, ease_in_out_cubic),
                       (T["ilya"]["start"], math.pi + 0.30, ease_in_out_cubic),
                       (T["slam"] - 0.02, math.tau - 0.50, ease_in_out_cubic),
                       (T["slam"] + 0.35, math.tau - 0.46, ease_out_cubic),
                       (T["slit"], math.tau, ease_in_out_cubic)])
        r = keys(t, [(T["l1"]["start"] - 0.5, 1.16),
                     (T["what"]["start"], 1.10),
                     (T["slam"], 0.74, ease_in_out_cubic),
                     (T["well"]["start"], 0.70),
                     (T["slit"], 0.58, ease_in_out_cubic),
                     (T["dark"] + 0.1, 0.32, ease_in_out_cubic),
                     (T["led_off"], 0.29)])
        h = keys(t, [(T["l1"]["start"] - 0.5, 0.30),
                     (T["what"]["start"], 0.28),
                     (T["slam"], 0.155, ease_in_out_cubic),
                     (T["well"]["start"], 0.145),
                     (T["slit"], 0.055, ease_in_out_cubic),
                     (T["dark"] + 0.1, 0.024),
                     (T["led_off"], 0.018)])
        th = lid_angle(t)
        tgt_lid = hinge + Vector((0, math.cos(th), math.sin(th))) * 0.122
        mix = prog(t, T["slit"] + 0.04, T["dark"] + 0.06, ease_in_out_cubic)
        base = tgt_lid.lerp(led, mix)
        pos = base + Vector((r * math.sin(phi), r * math.cos(phi), h))
        q0 = (base - pos).to_track_quat("-Z", "Y")
        right = q0 @ Vector((1, 0, 0))
        side = prog(t, T["l1"]["start"], T["what"]["start"] + 0.30, ease_in_out_cubic) * \
               (1 - prog(t, T["slit"] - 0.40, T["slit"] + 0.10, ease_in_out_cubic))
        tgt = base + right * (-0.09 * r * side)
        q = (tgt - pos).to_track_quat("-Z", "Y")
        roll = 0.014 * math.sin(phi) * (1 - prog(t, T["well"]["start"], T["slit"], ease_in_out_cubic))
        q = q @ Quaternion((0, 0, 1), roll)
        focus = (pos - tgt).length
        return pos, q, focus, th

    return state


def theatre_cam_fn(sc, T):
    aim = Vector((0, TY + 49.70, 2.80))

    def state(t):
        u = prog(t, T["was"]["start"], data.SCENES[sc.name]["end"], ease_in_out_cubic)
        pos = Vector((0, TY + 70.0 - 1.4 * u, 4.2))
        a = 0.0
        if t > T["was"]["start"]:
            a = 0.045 * math.exp(-(t - T["was"]["start"]) * 9.0)
        pos = pos + Vector((a * math.sin(t * 91.0), 0, a * math.cos(t * 77.0)))
        q = (aim - pos).to_track_quat("-Z", "Y")
        focus = (pos - aim).length
        return pos, q, focus

    return state


def build(name):
    sc = core.new_scene(name, samples=32, motion_blur=True)
    sc.frame_set(1)
    T = times()
    ROOM, THEATRE = [], []
    build_room(sc, T, ROOM)
    L = build_laptop(sc, T, ROOM)

    cam = core.add_camera_persp(sc, (0.30, -1.15, 1.13), (0.30, -0.20, 0.87), lens=50)
    cam.data.dof.use_dof = True
    cam.data.dof.aperture_fstop = 4.0
    cam.data.clip_start = 0.02
    cam.data.clip_end = 200.0
    rig, lyr_objs = build_lyric_overlay(sc, cam, T, ROOM)

    thcam = core.add_camera_persp(sc, (0, TY + 70, 4.2), (0, TY + 49.7, 2.8), lens=40)
    thcam.data.dof.use_dof = True
    thcam.data.dof.aperture_fstop = 4.5
    thcam.data.clip_start = 0.1
    thcam.data.clip_end = 200.0

    TH = build_theatre(sc, T, THEATRE)

    rim = core.add_light(sc, "AREA", (-0.62, -1.02, 1.34), 1.3, core.sc_x(BONE, 0.9), size=0.65, name="lidrim")
    core.look_at(rim, (0.30, -0.18, 0.86))
    ROOM.append(rim)
    roomfill = core.add_light(sc, "AREA", (0.9, 1.6, 2.3), 0.6, core.sc_x(BONE, 0.75), size=2.5, name="roomfill")
    core.look_at(roomfill, (0.1, -0.5, 0.9))
    ROOM.append(roomfill)

    f_led = core.frame_of(sc, T["led_off"])
    f_cut = core.frame_of(sc, T["theatre"])
    f_slam = core.frame_of(sc, T["slam"])
    f_dark = core.frame_of(sc, T["dark"])
    f_slit = core.frame_of(sc, T["slit"])
    f_meet = core.frame_of(sc, T["meet"])

    lf = room_cam_fn(sc, T, L)
    core.bake(L["lid"], "rotation_euler",
              lambda f: lf(data.frame_to_time(sc.name, f))[3], 1, min(sc.frame_end, f_led + 2), index=0)

    def screen_on(t):
        flick = 1.0 + 0.025 * math.sin(t * 23.0) * math.sin(t * 7.0 + 1.0)
        off = 1.0 - prog(t, T["dark"] - 0.06, T["dark"] + 0.02)
        return flick * off

    for f in range(1, min(sc.frame_end, f_led + 2) + 1, 2):
        t = data.frame_to_time(sc.name, f)
        L["slidelight"].data.energy = 1.9 * screen_on(t)
        L["slidelight"].data.keyframe_insert("energy", frame=f)
        L["screenglow"].data.energy = 0.22 * screen_on(t)
        L["screenglow"].data.keyframe_insert("energy", frame=f)
    core.set_interp(L["slidelight"].data, "LINEAR", "energy")
    core.set_interp(L["screenglow"].data, "LINEAR", "energy")

    r0 = max(1, core.frame_of(sc, T["slam"] - 0.075))
    for o in L["redact"]:
        core.show_at(o, 1, False)
        core.show_at(o, r0, True)
    L["rrig"].scale = (1.55, 1.55, 1.55)
    L["rrig"].rotation_euler = (0, 0, 0.0)
    L["rrig"].keyframe_insert("scale", frame=r0)
    L["rrig"].keyframe_insert("rotation_euler", frame=r0)
    L["rrig"].scale = (1, 1, 1)
    L["rrig"].rotation_euler = (0, 0, math.radians(-2.6))
    L["rrig"].keyframe_insert("scale", frame=f_slam)
    L["rrig"].keyframe_insert("rotation_euler", frame=f_slam)
    core.set_interp(L["rrig"], "BEZIER", "scale")
    core.set_interp(L["rrig"], "BEZIER", "rotation_euler")

    black = (0.0, 0.0, 0.0)
    core.color_at(L["led"], 1, black)
    core.color_at(L["led"], max(2, f_dark - 1), black)
    core.color_at(L["led"], max(3, f_dark + 1), core.sc_x(SIG, 0.72))
    core.color_at(L["led"], max(4, core.frame_of(sc, T["dark"] + 0.45)), core.sc_x(SIG, 0.38))
    core.color_at(L["led"], max(5, core.frame_of(sc, T["know_bar"])), core.sc_x(SIG, 0.72))
    core.color_at(L["led"], max(6, core.frame_of(sc, T["led_off"] - 0.10)), core.sc_x(SIG, 0.30))
    core.color_at(L["led"], max(7, core.frame_of(sc, T["led_off"])), black)
    core.set_interp(L["led"], "BEZIER", "color")
    core.show_at(L["led"], 1, True)

    ledl = L["ledlight"]
    for f in range(1, min(sc.frame_end, f_led + 1) + 1, 2):
        t = data.frame_to_time(sc.name, f)
        e = 0.0
        if T["dark"] - 0.06 < t < T["led_off"] + 0.02:
            e = keys(t, [(T["dark"] - 0.05, 0.0), (T["dark"] + 0.06, 1.0, ease_out_cubic),
                         (T["dark"] + 0.45, 0.35), (T["know_bar"], 1.0),
                         (T["led_off"] - 0.12, 0.25), (T["led_off"], 0.0)])
        ledl.data.energy = 0.9 * e
        ledl.data.keyframe_insert("energy", frame=f)
    core.set_interp(ledl.data, "LINEAR", "energy")

    sl0 = max(1, f_slit - 1)
    core.show_at(L["slit"], 1, False)
    core.show_at(L["slit"], sl0, True)
    core.show_at(L["slit"], f_dark + 2, False)
    L["slit"].location = (L["LX"], L["LY"] + L["BASE_D"] / 2, 0.7730)
    L["slit"].scale = (1, 1, 1)
    L["slit"].keyframe_insert("location", frame=sl0)
    L["slit"].keyframe_insert("scale", frame=sl0)
    L["slit"].location = (L["LX"], L["LY"] + L["BASE_D"] / 2, 0.7585)
    L["slit"].scale = (0.05, 1, 0.28)
    L["slit"].keyframe_insert("location", frame=f_dark)
    L["slit"].keyframe_insert("scale", frame=f_dark)
    core.color_at(L["slit"], sl0, EMB)
    core.color_at(L["slit"], f_dark, core.sc_x(SIG, 0.9))
    core.set_interp(L["slit"], "BEZIER", "location")
    core.set_interp(L["slit"], "BEZIER", "scale")

    state = room_cam_fn(sc, T, L)
    prev = None
    f1 = min(sc.frame_end, f_cut + 2)
    for f in range(1, f1 + 1):
        t = data.frame_to_time(sc.name, f)
        pos, q, focus, th = state(t)
        cam.location = pos
        cam.keyframe_insert("location", frame=f)
        prev = bake_quat(cam, q, f, prev)
        cam.data.dof.focus_distance = focus
        cam.data.dof.keyframe_insert("focus_distance", frame=f)
        rig.location = (0, 0, -focus)
        rig.scale = (focus, focus, focus)
        rig.keyframe_insert("location", frame=f)
        rig.keyframe_insert("scale", frame=f)
    core.set_interp(cam, "LINEAR", "location")
    core.set_interp(cam, "LINEAR", "rotation_quaternion")
    core.set_interp(cam.data, "LINEAR", "focus_distance")
    core.set_interp(rig, "LINEAR", "location")
    core.set_interp(rig, "LINEAR", "scale")

    for panel in (TH["cl"], TH["cr"]):
        for f in range(1, sc.frame_end + 1):
            t = data.frame_to_time(sc.name, f)
            k = 0.24 + 0.758 * ease_in_out_cubic(prog(t, T["forw"]["start"], T["meet"]))
            panel.scale = (k, 1, 1)
            panel.keyframe_insert("scale", frame=f)
        core.set_interp(panel, "LINEAR", "scale")

    seam = TH["seam"]
    f_seam = max(f_cut, core.frame_of(sc, T["meet"] - 0.16))
    core.show_at(seam, 1, False)
    core.show_at(seam, f_seam, True)
    for f in range(f_seam, sc.frame_end + 1):
        t = data.frame_to_time(sc.name, f)
        k = 0.24 + 0.758 * ease_in_out_cubic(prog(t, T["forw"]["start"], T["meet"]))
        gap = max(0.024, 11.24 * (1 - k))
        colv = prog(t, T["show"]["start"] - 0.02, data.SCENES[sc.name]["end"] - 0.08, ease_in_out_cubic)
        seam.scale = (gap / 0.4 * (1 - colv) + 0.02 * colv, 1, 1 - 0.996 * colv)
        seam.location = (0, TY + 49.70, 2.80)
        seam.keyframe_insert("scale", frame=f)
        seam.keyframe_insert("location", frame=f)
        seam.color = (*core.mixc(core.sc_x(EMB, 1.0), core.sc_x(BONE, 1.0), 0.25 * colv), 1)
        seam.keyframe_insert("color", frame=f)
    core.set_interp(seam, "LINEAR", "scale")
    core.set_interp(seam, "LINEAR", "color")

    spark = core.add_uv_sphere(sc, (0, TY + 49.70, 2.80), 0.085, EMB, hot=True, name="endspark")
    core.show_at(spark, 1, False)
    core.show_at(spark, core.frame_of(sc, 140.14), True)
    core.show_at(spark, sc.frame_end + 1, False)

    spot = TH["spot"]
    for f in range(1, sc.frame_end + 1):
        t = data.frame_to_time(sc.name, f)
        e = 0.0
        if t >= T["was"]["start"] - 0.01:
            e = keys(t, [(T["was"]["start"] - 0.01, 0.0), (T["was"]["start"] + 0.012, 17000.0),
                         (T["was"]["start"] + 0.06, 8000.0, ease_out_cubic),
                         (T["was"]["start"] + 0.18, 12000.0, ease_out_cubic)])
        spot.data.energy = e
        spot.data.keyframe_insert("energy", frame=f)
    core.set_interp(spot.data, "LINEAR", "energy")

    for ob in ROOM:
        try:
            has_vis = any(fc.data_path == "hide_render" for fc in core._fcurves(ob))
            if not has_vis:
                core.show_at(ob, 1, True)
            core.show_at(ob, f_led, False)
        except Exception:
            pass
    for ob in THEATRE:
        core.show_at(ob, 1, False)
        core.show_at(ob, f_cut, True)

    cam.name = "CAM_ROOM"
    thcam.name = "CAM_THEATRE"
    sc.camera = cam
    m1 = sc.timeline_markers.new("room", frame=1)
    m1.camera = cam
    m2 = sc.timeline_markers.new("theatre", frame=f_cut)
    m2.camera = thcam

    tstate = theatre_cam_fn(sc, T)
    prev = None
    for f in range(1, sc.frame_end + 1):
        t = data.frame_to_time(sc.name, f)
        pos, q, focus = tstate(t)
        thcam.location = pos
        thcam.keyframe_insert("location", frame=f)
        prev = bake_quat(thcam, q, f, prev)
        thcam.data.dof.focus_distance = focus
        thcam.data.dof.keyframe_insert("focus_distance", frame=f)
    core.set_interp(thcam, "LINEAR", "location")
    core.set_interp(thcam, "LINEAR", "rotation_quaternion")
    core.set_interp(thcam.data, "LINEAR", "focus_distance")

    sc.frame_set(1)
    sc.render.filepath = os.path.join(core.OUT, "frames", name, "####")
    os.makedirs(os.path.dirname(sc.render.filepath), exist_ok=True)
    print("ILYA times", {k: round(v, 3) for k, v in T.items() if isinstance(v, (int, float))})
    print("frames led/cut/slam/slit/dark/meet", f_led, f_cut, f_slam, f_slit, f_dark, f_meet)
    return sc

