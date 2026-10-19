"""Blender toolkit for the pdoom rebuild: palette, typography, line art, cameras, post, baking."""
import bpy, bmesh, math, os, random
from mathutils import Vector, Euler, Quaternion
from . import data

ROOT = data.ROOT
FONT_DIR = os.path.join(ROOT, "pdoom-video", "app", "public", "fonts")
OUT = os.path.join(ROOT, "out")
W, H = data.W, data.H
FPS = data.FPS


def _srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _hex(h):
    h = h.lstrip("#")
    return tuple(_srgb_to_linear(int(h[i:i + 2], 16) / 255.0) for i in (0, 2, 4))


HEX = {
    "ink": "#0A0A0B", "ink2": "#151517", "graphite": "#5E5B57", "ash": "#9C978F",
    "bone": "#EEE9DF", "signal": "#FF4D12", "ember": "#FF8A3D", "blood": "#C21D0B",
    "acid": "#D8FF3C",
}
PAL = {k: _hex(v) for k, v in HEX.items()}


def mixc(a, b, k):
    return tuple(a[i] + (b[i] - a[i]) * k for i in range(3))


def sc_x(c, k):
    return tuple(min(1.0, v * k) for v in c)


# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def lerp(a, b, k):
    return a + (b - a) * k


def smoothstep(a, b, x):
    if b == a:
        return 1.0 if x >= b else 0.0
    k = clamp((x - a) / (b - a))
    return k * k * (3 - 2 * k)


def ease_out_expo(x):
    x = clamp(x)
    return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)


def ease_in_expo(x):
    x = clamp(x)
    return 0.0 if x <= 0 else 2 ** (10 * (x - 1))


def ease_in_out_cubic(x):
    x = clamp(x)
    return 4 * x * x * x if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_out_cubic(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_out_back(x, s=1.7):
    x = clamp(x)
    c3 = s + 1
    return 1 + c3 * (x - 1) ** 3 + s * (x - 1) ** 2


def ease_out_elastic(x):
    x = clamp(x)
    if x in (0.0, 1.0):
        return x
    c4 = (2 * math.pi) / 3
    return 2 ** (-10 * x) * math.sin((x * 10 - 0.75) * c4) + 1


def prog(t, a, b, ease=None):
    k = clamp((t - a) / max(1e-6, b - a))
    return ease(k) if ease else k


def keys(t, pts):
    """Piecewise interpolation: pts = [(time, value, ease_fn), ...]."""
    if t <= pts[0][0]:
        return pts[0][1]
    for i in range(len(pts) - 1):
        t0, v0 = pts[i][0], pts[i][1]
        t1, v1 = pts[i + 1][0], pts[i + 1][1]
        if t <= t1:
            fn = pts[i][2] if len(pts[i]) > 2 and pts[i][2] else ease_in_out_cubic
            return lerp(v0, v1, fn((t - t0) / max(1e-6, t1 - t0)))
    return pts[-1][1]


def hash01(*xs):
    h = 0
    for x in xs:
        h = (h * 1664525 + int(x * 100003) + 1013904223) & 0xFFFFFFFF
    h ^= h >> 16
    h = (h * 2246822519) & 0xFFFFFFFF
    h ^= h >> 13
    return h / 0xFFFFFFFF


# ---------------------------------------------------------------- fonts
_FONTS = {}


def font(path_or_key):
    p = F.get(path_or_key, path_or_key) if "F" in globals() else path_or_key
    if not os.path.isabs(p):
        p = os.path.join(FONT_DIR, p)
    if p in _FONTS:
        return _FONTS[p]
    f = bpy.data.fonts.load(p)
    _FONTS[p] = f
    return f


F = {
    "archivo": "Archivo-w1000-900.ttf",
    "archivo700": "Archivo-w1000-700.ttf",
    "archivo500": "Archivo-w1000-500.ttf",
    "archivo300": "Archivo-w1000-300.ttf",
    "archivo_w62_900": "Archivo-w620-900.ttf",
    "archivo_w62_700": "Archivo-w620-700.ttf",
    "archivo_w62_500": "Archivo-w620-500.ttf",
    "archivo_w75_900": "Archivo-w750-900.ttf",
    "archivo_w75_700": "Archivo-w750-700.ttf",
    "archivo_w87_900": "Archivo-w875-900.ttf",
    "archivo_w112_900": "Archivo-w1125-900.ttf",
    "archivo_w125_900": "Archivo-w1250-900.ttf",
    "archivo_w125_700": "Archivo-w1250-700.ttf",
    "archivo_italic": "ArchivoItalic-w1000-400.ttf",
    "archivo_italic800": "ArchivoItalic-w1000-800.ttf",
    "mono": "src/IBMPlexMono-Regular.ttf",
    "mono_light": "src/IBMPlexMono-Light.ttf",
    "mono_med": "src/IBMPlexMono-Medium.ttf",
    "mono_semi": "src/IBMPlexMono-SemiBold.ttf",
    "mono_bold": "src/IBMPlexMono-Bold.ttf",
    "mono_italic": "src/IBMPlexMono-Italic.ttf",
    "serif": "Cormorant-400.ttf",
    "serif600": "Cormorant-600.ttf",
    "serif_italic": "CormorantItalic-400.ttf",
    "serif_italic600": "CormorantItalic-600.ttf",
}


# ---------------------------------------------------------------- scene setup
def _nodes(mat):
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    return nt


_MATS = {}


def mat_emit(color, strength=1.0, name=None):
    key = ("emit", tuple(round(c, 5) for c in color), strength)
    if key in _MATS:
        return _MATS[key]
    m = bpy.data.materials.new(name or "emit")
    nt = _nodes(m)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[0].default_value = (*color, 1.0)
    em.inputs[1].default_value = strength
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    _MATS[key] = m
    return m


def mat_type():
    """Emission driven by each object's colour: one material for all typography and line art."""
    if "type" in _MATS:
        return _MATS["type"]
    m = bpy.data.materials.new("type")
    nt = _nodes(m)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    oi = nt.nodes.new("ShaderNodeObjectInfo")
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(oi.outputs["Color"], em.inputs["Color"])
    em.inputs[1].default_value = 1.0
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    _MATS["type"] = m
    return m


def mat_hot():
    """Like mat_type but 3x brighter (cores, sparks, glow)."""
    if "hot" in _MATS:
        return _MATS["hot"]
    m = bpy.data.materials.new("hot")
    nt = _nodes(m)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    oi = nt.nodes.new("ShaderNodeObjectInfo")
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(oi.outputs["Color"], em.inputs["Color"])
    em.inputs[1].default_value = 3.0
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    _MATS["hot"] = m
    return m


def mat_paper():
    if "paper" in _MATS:
        return _MATS["paper"]
    m = bpy.data.materials.new("paper")
    nt = _nodes(m)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 140.0
    noise.inputs["Detail"].default_value = 5.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = (0.62, 0.60, 0.55, 1)
    ramp.color_ramp.elements[1].position = 0.65
    ramp.color_ramp.elements[1].color = (0.76, 0.73, 0.67, 1)
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    _MATS["paper"] = m
    return m


def mat_hatch(base, line, scale=45.0, angle=0.0, distortion=1.6, strength=1.0, name=None):
    """Engraved hatch: parallel warm lines on a dark surface (object coordinates)."""
    key = ("hatch", tuple(base), tuple(line), scale, angle, distortion, strength)
    if key in _MATS:
        return _MATS[key]
    m = bpy.data.materials.new(name or "hatch")
    nt = _nodes(m)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Rotation"].default_value = (0, 0, math.radians(angle))
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    wave.inputs["Scale"].default_value = scale
    wave.inputs["Distortion"].default_value = distortion
    wave.inputs["Detail"].default_value = 2.0
    wave.inputs["Detail Scale"].default_value = 2.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].position = 0.38
    ramp.color_ramp.elements[0].color = (*base, 1)
    ramp.color_ramp.elements[1].position = 0.62
    ramp.color_ramp.elements[1].color = (*line, 1)
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[1].default_value = strength
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], wave.inputs["Vector"])
    nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    _MATS[key] = m
    return m


def mat_hatch_lit(base, line, scale=25.0, angle=0.0, distortion=1.6, rough=0.55,
                  rim=0.5, rim_color=None, line_emit=0.10, name=None):
    """Engraved surface under real lights: hatch lines are albedo, a fresnel rim outlines it."""
    key = ("hatchlit", tuple(base), tuple(line), scale, angle, distortion, rough, rim,
           tuple(rim_color) if rim_color else None, line_emit)
    if key in _MATS:
        return _MATS[key]
    m = bpy.data.materials.new(name or "hatchlit")
    nt = _nodes(m)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Rotation"].default_value = (0, 0, math.radians(angle))
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    wave.inputs["Scale"].default_value = scale
    wave.inputs["Distortion"].default_value = distortion
    wave.inputs["Detail"].default_value = 2.0
    wave.inputs["Detail Scale"].default_value = 2.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].position = 0.42
    ramp.color_ramp.elements[0].color = (*base, 1)
    ramp.color_ramp.elements[1].position = 0.58
    ramp.color_ramp.elements[1].color = (*line, 1)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*base, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = 0.15
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], wave.inputs["Vector"])
    nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    # faint self-lit hatching so shadows keep the engraving
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[1].default_value = line_emit
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    # fresnel rim
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.35
    pw = nt.nodes.new("ShaderNodeMath")
    pw.operation = "POWER"
    pw.inputs[1].default_value = 3.0
    nt.links.new(lw.outputs["Facing"], pw.inputs[0])
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = rim
    nt.links.new(pw.outputs["Value"], mul.inputs[0])
    em2 = nt.nodes.new("ShaderNodeEmission")
    rc = rim_color or line
    em2.inputs[0].default_value = (*rc, 1)
    nt.links.new(mul.outputs["Value"], em2.inputs["Strength"])
    add1 = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(bsdf.outputs[0], add1.inputs[0])
    nt.links.new(em.outputs[0], add1.inputs[1])
    add2 = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(add1.outputs[0], add2.inputs[0])
    nt.links.new(em2.outputs[0], add2.inputs[1])
    nt.links.new(add2.outputs[0], out.inputs["Surface"])
    _MATS[key] = m
    return m


def mat_lit(base, rough=0.45, metal=0.0, emission=None, emission_strength=0.0):
    key = ("lit", tuple(base), rough, metal, tuple(emission) if emission else None, emission_strength)
    if key in _MATS:
        return _MATS[key]
    m = bpy.data.materials.new("lit")
    nt = _nodes(m)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*base, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
    _MATS[key] = m
    return m


def mat_stripes(base, line, scale=50.0, angle=0.0):
    return mat_hatch(base, line, scale, angle, 0.4, 1.0)


# ---------------------------------------------------------------- geometry
def _link(sc, ob):
    sc.collection.objects.link(ob)
    return ob


def add_text(sc, body, font_key, size, color, loc=(0, 0, 0), rot=(0, 0, 0),
             align_x="LEFT", align_y="BOTTOM_BASELINE", extrude=0.0, bevel=0.0,
             name=None, hot=False, spacing=1.0, offset=0.0):
    cu = bpy.data.curves.new(name or "txt", type="FONT")
    cu.body = body
    cu.font = font(font_key)
    cu.size = size
    cu.align_x = align_x
    cu.align_y = align_y
    cu.extrude = extrude
    cu.bevel_depth = bevel
    cu.bevel_resolution = 2 if bevel else 0
    cu.space_character = spacing
    cu.offset_x = offset
    cu.materials.append(mat_hot() if hot else mat_type())
    ob = _link(sc, bpy.data.objects.new(name or "txt", cu))
    ob.location = loc
    ob.rotation_euler = rot
    ob.color = (*color, 1.0)
    return ob


_MEASURE = {}


def _measure_text(sc, text, font_key, size):
    key = (text, font_key, round(size, 6))
    if key in _MEASURE:
        return _MEASURE[key]
    if "_obj" not in _MEASURE:
        cu = bpy.data.curves.new("_measure", type="FONT")
        cu.align_x = "LEFT"
        cu.align_y = "BOTTOM_BASELINE"
        ob = _link(sc, bpy.data.objects.new("_measure", cu))
        ob.hide_render = True
        _MEASURE["_obj"] = ob
    ob = _MEASURE["_obj"]
    ob.data.font = font(font_key)
    ob.data.size = size
    ob.data.body = text
    bpy.context.view_layer.update()
    w = ob.dimensions.x
    _MEASURE[key] = w
    return w


def measure(sc, text, font_key, size):
    return _measure_text(sc, text, font_key, size)


def space_width(sc, font_key, size):
    return measure(sc, "A A", font_key, size) - measure(sc, "AA", font_key, size)


def text_width(sc, text, font_key, size, tracking=0.0):
    return measure(sc, text, font_key, size) + max(0, len(text) - 1) * tracking


def layout_chars(sc, text, font_key, size, x, y, z=0.0, tracking=0.0):
    """Per-character objects with exact kerning from prefix advances. Returns [(char, obj, xstart)]."""
    out = []
    prefix = ""
    for i, ch in enumerate(text):
        cx = x + measure(sc, prefix, font_key, size) + i * tracking
        if ch != " ":
            ob = add_text(sc, ch, font_key, size, PAL["bone"], (cx, y, z), name=f"ch_{i}")
            out.append((ch, ob, cx))
        prefix += ch
    return out


def add_polyline(sc, points, width, color, name="line", z=0.0, hot=False, cyclic=False,
                 bevel_resolution=1, material=None):
    """World-space polyline; width is the full stroke width in world units."""
    cu = bpy.data.curves.new(name, type="CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = max(width / 2, 0.0002)
    cu.bevel_resolution = bevel_resolution
    cu.resolution_u = 2
    sp = cu.splines.new("POLY")
    sp.points.add(len(points) - 1)
    for i, p in enumerate(points):
        if len(p) == 2:
            sp.points[i].co = (p[0], p[1], z, 1)
        else:
            sp.points[i].co = (p[0], p[1], p[2], 1)
    sp.use_cyclic_u = cyclic
    cu.materials.append(material or (mat_hot() if hot else mat_type()))
    ob = _link(sc, bpy.data.objects.new(name, cu))
    ob.color = (*color, 1.0)
    return ob


def add_segments(sc, segments, width, color, name="segs", z=0.0, hot=False):
    """Many disjoint segments in one curve object (dashed rules, hatching)."""
    cu = bpy.data.curves.new(name, type="CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = max(width / 2, 0.0002)
    cu.bevel_resolution = 0
    for a, b in segments:
        sp = cu.splines.new("POLY")
        sp.points.add(1)
        sp.points[0].co = (a[0], a[1], z, 1)
        sp.points[1].co = (b[0], b[1], z, 1)
    cu.materials.append(mat_hot() if hot else mat_type())
    ob = _link(sc, bpy.data.objects.new(name, cu))
    ob.color = (*color, 1.0)
    return ob


def add_rect(sc, x, y, w, h, color, z=0.0, fill=True, line_width=0.0, name="rect", rot=0.0):
    """Flat rectangle in the XY plane, corner at (x,y), rotating around its corner."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    vs = [bm.verts.new((0, 0, 0)), bm.verts.new((w, 0, 0)), bm.verts.new((w, h, 0)), bm.verts.new((0, h, 0))]
    bm.faces.new(vs)
    bm.to_mesh(me)
    bm.free()
    ob = _link(sc, bpy.data.objects.new(name, me))
    ob.location = (x, y, z)
    ob.rotation_euler = (0, 0, rot)
    if fill:
        me.materials.append(mat_type())
        ob.color = (*color, 1.0)
    else:
        me.materials.append(mat_type())
        ob.color = (*color, 1.0)
    return ob


def add_outline_rect(sc, x, y, w, h, width, color, z=0.0, name="frame"):
    pts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    return add_polyline(sc, pts, width, color, name=name, z=z, cyclic=True)


def add_disc(sc, x, y, r, color, z=0.0, segments=64, name="disc", hot=False):
    cu = bpy.data.curves.new(name, type="CURVE")
    cu.dimensions = "2D"
    cu.fill_mode = "BOTH"
    sp = cu.splines.new("POLY")
    sp.points.add(segments - 1)
    for i in range(segments):
        a = i / segments * math.tau
        sp.points[i].co = (x + math.cos(a) * r, y + math.sin(a) * r, z, 1)
    sp.use_cyclic_u = True
    cu.materials.append(mat_hot() if hot else mat_type())
    ob = _link(sc, bpy.data.objects.new(name, cu))
    ob.color = (*color, 1.0)
    return ob


def add_box(sc, loc, size, color, name="box", material=None, rot=(0, 0, 0)):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(me)
    bm.free()
    ob = _link(sc, bpy.data.objects.new(name, me))
    ob.location = loc
    ob.scale = size
    ob.rotation_euler = rot
    me.materials.append(material or mat_type())
    ob.color = (*color, 1.0)
    return ob


def add_uv_sphere(sc, loc, r, color, name="sphere", hot=False, segs=20, rings=12):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=r)
    bm.to_mesh(me)
    bm.free()
    ob = _link(sc, bpy.data.objects.new(name, me))
    ob.location = loc
    me.materials.append(mat_hot() if hot else mat_type())
    ob.color = (*color, 1.0)
    for p in me.polygons:
        p.use_smooth = True
    return ob


def add_cylinder(sc, loc, r, depth, color, name="cyl", rot=(0, 0, 0), hot=False, verts=32, material=None):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=verts,
                          radius1=r, radius2=r, depth=depth)
    bm.to_mesh(me)
    bm.free()
    ob = _link(sc, bpy.data.objects.new(name, me))
    ob.location = loc
    ob.rotation_euler = rot
    me.materials.append(material or (mat_hot() if hot else mat_type()))
    ob.color = (*color, 1.0)
    return ob


def add_torus(sc, loc, R, r, color, name="torus", rot=(0, 0, 0), hot=False):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=64, minor_segments=12, location=loc)
    ob = bpy.context.active_object
    ob.name = name
    ob.rotation_euler = rot
    ob.data.materials.append(mat_hot() if hot else mat_type())
    ob.color = (*color, 1.0)
    return ob


def add_light(sc, kind, loc, energy, color, size=1.0, rot=(0, 0, 0), name="light"):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = color
    if kind == "AREA":
        ld.size = size
    if kind == "POINT":
        ld.shadow_soft_size = size
    ob = _link(sc, bpy.data.objects.new(name, ld))
    ob.location = loc
    ob.rotation_euler = rot
    return ob


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def add_camera_ortho(sc, scale=19.2, loc=(0, 0, 50)):
    cd = bpy.data.cameras.new("cam")
    cd.type = "ORTHO"
    cd.ortho_scale = scale
    cam = _link(sc, bpy.data.objects.new("cam", cd))
    cam.location = loc
    sc.camera = cam
    return cam


def add_camera_persp(sc, loc, target, lens=50.0, sensor=36.0):
    cd = bpy.data.cameras.new("cam")
    cd.type = "PERSP"
    cd.lens = lens
    cd.sensor_width = sensor
    cam = _link(sc, bpy.data.objects.new("cam", cd))
    cam.location = loc
    look_at(cam, target)
    sc.camera = cam
    return cam


def add_bg(sc, color=None, z=-30.0, size=60.0, gradient=False, glow=0.0, name="bg"):
    """Flat background plane (default: dead-flat ink, like the original's #0A0A0B)."""
    m = bpy.data.materials.new(name)
    nt = _nodes(m)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    c1 = color or PAL["ink"]
    if gradient:
        tc = nt.nodes.new("ShaderNodeTexCoord")
        ln = nt.nodes.new("ShaderNodeVectorMath")
        ln.operation = "LENGTH"
        nt.links.new(tc.outputs["Object"], ln.inputs[0])
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = 0.0
        mr.inputs["From Max"].default_value = size * 0.45
        mr.inputs["To Min"].default_value = 1.0
        mr.inputs["To Max"].default_value = 0.0
        nt.links.new(ln.outputs["Value"], mr.inputs["Value"])
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.inputs[6].default_value = (*c1, 1)
        mix.inputs[7].default_value = (*[c * 2.2 for c in c1], 1)
        nt.links.new(mr.outputs["Result"], mix.inputs["Factor"])
        nt.links.new(mix.outputs[2], em.inputs["Color"])
    else:
        em.inputs[0].default_value = (*c1, 1)
    em.inputs[1].default_value = 1.0
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    s = size / 2
    vs = [bm.verts.new((-s, -s, 0)), bm.verts.new((s, -s, 0)), bm.verts.new((s, s, 0)), bm.verts.new((-s, s, 0))]
    bm.faces.new(vs)
    bm.to_mesh(me)
    bm.free()
    ob = _link(sc, bpy.data.objects.new(name, me))
    ob.location = (0, 0, z)
    me.materials.append(m)
    return ob


def add_paper_bg(sc, z=-60.0, size=200.0, color=None, name="paperbg"):
    ob = add_rect(sc, -size / 2, -size / 2, size, size, color or PAL["bone"], z=z, name=name)
    ob.data.materials.clear()
    ob.data.materials.append(mat_paper())
    return ob


# ---------------------------------------------------------------- post
def setup_post(sc, bloom=0.55, threshold=1.0, size=0.30, dispersion=0.005, halation=0.10):
    g = bpy.data.node_groups.new("pdoom_post", "CompositorNodeTree")
    sc.compositing_node_group = g
    g.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    rl = g.nodes.new("CompositorNodeRLayers")
    rl.location = (-600, 0)
    gl = g.nodes.new("CompositorNodeGlare")
    gl.location = (-300, 0)
    gl.inputs["Type"].default_value = "Bloom"
    gl.inputs["Quality"].default_value = "High"
    gl.inputs["Threshold"].default_value = threshold
    gl.inputs["Smoothness"].default_value = 0.3
    gl.inputs["Strength"].default_value = bloom
    gl.inputs["Size"].default_value = size
    gl.inputs["Saturation"].default_value = 1.0
    g.links.new(rl.outputs["Image"], gl.inputs["Image"])
    last = gl.outputs["Image"]
    if halation > 0:
        gl2 = g.nodes.new("CompositorNodeGlare")
        gl2.location = (0, 0)
        gl2.inputs["Type"].default_value = "Fog Glow"
        gl2.inputs["Quality"].default_value = "Medium"
        gl2.inputs["Threshold"].default_value = 1.15
        gl2.inputs["Strength"].default_value = halation
        gl2.inputs["Size"].default_value = 0.5
        gl2.inputs["Tint"].default_value = (1.0, 0.35, 0.12, 1.0)
        g.links.new(last, gl2.inputs["Image"])
        last = gl2.outputs["Image"]
    ld = g.nodes.new("CompositorNodeLensdist")
    ld.location = (300, 0)
    ld.inputs["Distortion"].default_value = 0.0
    ld.inputs["Dispersion"].default_value = dispersion
    ld.inputs["Fit"].default_value = True
    g.links.new(last, ld.inputs["Image"])
    go = g.nodes.new("NodeGroupOutput")
    go.location = (600, 0)
    g.links.new(ld.outputs["Image"], go.inputs[0])
    sc.render.use_compositing = True
    sc.render.use_sequencer = False


def new_scene(name, samples=32, motion_blur=True):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.name = name
    info = data.SCENES[name]
    sc["plate"] = name
    sc["start"] = info["start"]
    sc["end"] = info["end"]
    sc.frame_start = 1
    sc.frame_end = info["frames"]
    sc.render.fps = FPS
    sc.render.resolution_x = W
    sc.render.resolution_y = H
    sc.render.resolution_percentage = 100
    sc.render.engine = "BLENDER_EEVEE"
    sc.eevee.taa_render_samples = samples
    sc.eevee.use_raytracing = False
    sc.render.use_motion_blur = bool(motion_blur)
    sc.render.motion_blur_shutter = 0.32
    sc.render.motion_blur_position = "CENTER"
    try:
        sc.eevee.motion_blur_steps = 4
        sc.eevee.motion_blur_max = 64
    except Exception:
        pass
    sc.render.filter_size = 1.0
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.image_settings.color_depth = "8"
    sc.render.image_settings.compression = 15
    sc.render.film_transparent = False
    w = bpy.data.worlds.new("world")
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (*PAL["ink"], 1)
    bg.inputs[1].default_value = 0.0
    sc.render.filepath = os.path.join(OUT, "frames", name, "####")
    setup_post(sc)
    return sc


def set_samples(sc, n):
    sc.eevee.taa_render_samples = n


# ---------------------------------------------------------------- animation
def key(ob, path, frame, value, interp="BEZIER"):
    setattr(ob, path, value)
    ob.keyframe_insert(path, frame=frame)
    if interp != "BEZIER":
        for fc in _fcurves(ob):
            if fc.data_path == path:
                for kp in fc.keyframe_points:
                    if abs(kp.co.x - frame) < 0.5:
                        kp.interpolation = interp


def _fcurves(ob):
    if ob.animation_data and ob.animation_data.action:
        act = ob.animation_data.action
        # Blender 5: layered actions
        if hasattr(act, "layers") and len(act.layers):
            fcs = []
            for layer in act.layers:
                for strip in layer.strips:
                    for bag in strip.channelbags:
                        fcs.extend(bag.fcurves)
            return fcs
        return list(act.fcurves)
    return []


def set_interp(ob, mode="BEZIER", path=None):
    for fc in _fcurves(ob):
        if path and fc.data_path != path:
            continue
        for kp in fc.keyframe_points:
            kp.interpolation = mode
            if mode == "BEZIER":
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"


def bake(ob, path, fn, f0, f1, step=1, interp="LINEAR", index=-1):
    for f in range(f0, f1 + 1, step):
        v = fn(f)
        if index >= 0:
            cur = list(getattr(ob, path))
            cur[index] = v
            setattr(ob, path, cur)
        else:
            setattr(ob, path, v)
        ob.keyframe_insert(path, frame=f)
    set_interp(ob, interp, path)


def show_at(ob, frame, visible):
    ob.hide_render = not visible
    ob.keyframe_insert("hide_render", frame=frame)


def color_at(ob, frame, color):
    ob.color = (*color, 1.0)
    ob.keyframe_insert("color", frame=frame)


def frame_of(sc, t):
    return data.time_to_frame(sc.name, t)


def time_of(sc, frame=None):
    f = sc.frame_current if frame is None else frame
    return data.frame_to_time(sc.name, f)


def animate_words(sc, word_objs, sung=None, dim=None, pre=0.35, first=None):
    """word_objs: [(word dict, object)]. Dim before the word starts, sung from its start."""
    sung = sung or PAL["bone"]
    dim = dim or sc_x(PAL["bone"], 0.08)
    for w, ob in word_objs:
        if first is not None and w is first:
            color_at(ob, 1, sung)
            continue
        f0 = frame_of(sc, w["start"] - pre)
        f1 = frame_of(sc, w["start"])
        color_at(ob, 1, dim)
        color_at(ob, max(1, f0), dim)
        color_at(ob, max(2, f1), sung)
    for w, ob in word_objs:
        set_interp(ob, "BEZIER", "color")


def add_lyric(sc, q, x, y, font_key="archivo", size=2.0, z=0.0, color=None, dim=None,
              tracking=0.0, name="lyric", align="left", max_width=None):
    """Lay a lyric line out as individual word objects, with word-synced colour.
    If max_width is given the whole line is scaled down to fit it."""
    l = data.line(q)
    color = color or PAL["bone"]
    dim = dim or sc_x(PAL["bone"], 0.08)
    ws = l["words"]
    widths = [measure(sc, w["w"], font_key, size) for w in ws]
    sw = space_width(sc, font_key, size) + 0.06 * size
    total = sum(widths) + sw * (len(ws) - 1) + tracking * (len(ws) - 1)
    if max_width and total > max_width:
        k = max_width / total
        size *= k
        widths = [v * k for v in widths]
        sw *= k
        tracking *= k
        total = max_width
    cx = x - total / 2 if align == "center" else x
    objs = []
    for i, w in enumerate(ws):
        ob = add_text(sc, w["w"], font_key, size, dim, (cx, y, z), name=f"{name}{i}", spacing=1.0)
        objs.append((w, ob))
        cx += widths[i] + sw + tracking
    return l, objs, total


def sync_words(sc, objs, sung=None, dim=None, pre=0.3):
    animate_words(sc, objs, sung=sung, dim=dim, pre=pre)


# ---------------------------------------------------------------- post helpers
def fade_in(sc, ob, t0, dur=0.6):
    """Fade an object in by scaling its emission colour (works for type material)."""
    f0 = frame_of(sc, t0)
    f1 = frame_of(sc, t0 + dur)
    color_at(ob, max(1, f0 - 1), (0, 0, 0))
    color_at(ob, max(1, f0), (0, 0, 0))
    color_at(ob, f1, tuple(ob.color)[:3])
    set_interp(ob, "BEZIER", "color")


def render_stills(sc, frames, outdir):
    os.makedirs(outdir, exist_ok=True)
    sc.render.image_settings.file_format = "PNG"
    for f in frames:
        sc.frame_set(f)
        sc.render.filepath = os.path.join(outdir, f"f{f:04d}.png")
        bpy.ops.render.render(write_still=True)


def save_blend(sc, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=path)


def setup_render_out(sc, tag="frames"):
    sc.render.filepath = os.path.join(OUT, tag, sc.name, "####")
    os.makedirs(os.path.dirname(sc.render.filepath), exist_ok=True)