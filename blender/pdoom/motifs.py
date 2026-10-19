"""Shared motifs: spark, mask, HUD furniture, plates help, 3D lighting rigs."""
import bpy, math, os, sys
from . import core, data
from .core import PAL, clamp, lerp, smoothstep, ease_out_expo, hash01

INK, BONE, SIG, EMB, GRAPH, ASH, BLOOD, ACID = (PAL["ink"], PAL["bone"], PAL["signal"], PAL["ember"],
                                                PAL["graphite"], PAL["ash"], PAL["blood"], PAL["acid"])


def dim(k=0.3):
    return core.sc_x(BONE, k)


def mono(sc, text, x, y, size=0.13, color=None, align="LEFT", z=0.0, name="mono"):
    return core.add_text(sc, text, "mono_med", size, color or GRAPH, (x, y, z),
                         align_x=align, name=name, spacing=1.02)


def serif(sc, text, x, y, size=0.5, color=None, italic=True, align="LEFT", z=0.0):
    return core.add_text(sc, text, "serif_italic" if italic else "serif", size, color or BONE,
                         (x, y, z), align_x=align)


def rule(sc, x0, y0, x1, y1, color=None, width=0.009, z=0.0):
    return core.add_polyline(sc, [(x0, y0), (x1, y1)], width, color or dim(0.3), z=z)


def crop_marks(sc, margin=0.36, length=0.24, color=None, z=20.0):
    """Four L-shaped corner marks in camera space (call with the ortho camera)."""
    c = color or dim(0.34)
    x0, x1 = -9.6 + margin, 9.6 - margin
    y0, y1 = -5.4 + margin, 5.4 - margin
    for (x, y, sx, sy) in [(x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)]:
        core.add_polyline(sc, [(x + sx * length, y), (x, y), (x, y + sy * length)], 0.012, c, z=z)


def readout(sc, x, y, value, v=None, scale=1.0, color=None, bar=True, label=True, z=0.0):
    """The P(doom) instrument, staged anywhere (label, digits, tick bar)."""
    color = color or SIG
    text = value if isinstance(value, str) else (f"{value:.3f}" if value >= 0.99 else f"{value:.2f}")
    vv = float(v if v is not None else (value if not isinstance(value, str) else 0.5))
    out = []
    if label:
        out.append(core.add_text(sc, "P(DOOM)", "mono_med", 0.13 * scale, dim(0.55), (x, y + 0.38 * scale, z), spacing=1.08))
    out.append(core.add_text(sc, text, "mono_med", 0.42 * scale, color, (x - 0.02 * scale, y, z), name="readout"))
    if bar:
        bw = 2.2 * scale
        core.add_rect(sc, x, y - 0.28 * scale, bw, 0.012 * scale, dim(0.18), z=z)
        core.add_rect(sc, x, y - 0.30 * scale, bw * clamp(vv), 0.03 * scale, color, z=z)
    return out


def value_bar(sc, x, y, w, v, color=None, z=0.0):
    core.add_rect(sc, x, y, w, 0.012, dim(0.18), z=z)
    core.add_rect(sc, x, y - 0.006, w * clamp(v), 0.024, color or SIG, z=z + 0.01)


def mask2d(sc, x, y, R, rot=0.0, face=None, ink=None, z=0.0, smile=0.55, name="mask"):
    """The bland assistant mask: bone disc, two ink dots, a smile. Returns the objects."""
    face = face or core.sc_x(BONE, 0.9)
    ink = ink or INK
    objs = []
    d = core.add_disc(sc, 0, 0, R, face, z=z, name=name + "_disc")
    d.location = (x, y, z)
    d.rotation_euler = (0, 0, rot)
    objs.append(d)
    for sx in (-0.32, 0.32):
        e = core.add_disc(sc, x + math.cos(rot) * sx * R, y + math.sin(rot) * sx * R, R * 0.075, ink, z=z + 0.01, name=name + "_eye")
        objs.append(e)
    # smile: an arc
    pts = []
    for i in range(17):
        a = math.radians(lerp(-35, 35, i / 16))
        px = math.sin(a) * 0.46 * R
        py = -0.10 * R + (1 - math.cos(a)) * 0.34 * R
        pts.append((x + math.cos(rot) * px - math.sin(rot) * py,
                    y + math.sin(rot) * px + math.cos(rot) * py))
    sm = core.add_polyline(sc, pts, R * 0.055, ink, z=z + 0.012, name=name + "_smile")
    objs.append(sm)
    return objs


def spark(sc, path, t0, t1, r=0.09, color=None, z=1.0, trail=True, trail_len=0.22, name="spark"):
    """Orange point travelling along path(t) between song times t0..t1."""
    color = color or EMB
    head = core.add_uv_sphere(sc, (0, 0, z), r, color, hot=True, name=name)
    core.show_at(head, 1, False)
    f0, f1 = core.frame_of(sc, t0), core.frame_of(sc, t1)
    core.show_at(head, max(1, f0), True)
    core.show_at(head, min(sc.frame_end, f1) + 1, False)
    for f in range(max(1, f0), min(sc.frame_end, f1) + 1):
        p = path(data.frame_to_time(sc.name, f))
        head.location = (p[0], p[1], z)
        head.keyframe_insert("location", frame=f)
    core.set_interp(head, "LINEAR", "location")
    trailobj = None
    if trail:
        pts = []
        for f in range(max(1, f0), min(sc.frame_end, f1) + 1, 2):
            p = path(data.frame_to_time(sc.name, f))
            pts.append((p[0], p[1]))
        if len(pts) > 1:
            trailobj = core.add_polyline(sc, pts, 0.010, core.sc_x(SIG, 0.55), z=z - 0.2)
    return head


def spark_head(sc, x, y, r=0.09, z=1.0, color=None, name="sparkhead"):
    return core.add_uv_sphere(sc, (x, y, z), r, color or EMB, hot=True, name=name)


def stage3d(sc, key=(4, -6, 5), key_energy=500, rim=(-5, 3, 3), rim_energy=900, rim_color=None,
            fill=(0, -3, -2), fill_energy=80, bg=None):
    """Standard 3-point rig for the raymarched / modelled plates."""
    if bg:
        core.add_bg(sc, bg)
    core.add_light(sc, "AREA", key, key_energy, BONE, size=4.0)
    core.add_light(sc, "AREA", rim, rim_energy, rim_color or SIG, size=3.0)
    core.add_light(sc, "POINT", fill, fill_energy, EMB, size=1.5)


def perspective(sc, loc, target, lens=55, dof=None):
    cam = core.add_camera_persp(sc, loc, target, lens=lens)
    if dof:
        cam.data.dof.use_dof = True
        cam.data.dof.focus_distance = dof[0]
        cam.data.dof.aperture_fstop = dof[1]
    return cam


def ring(sc, cx, cy, r, color=None, width=0.008, z=0.0, segs=96, name="ring"):
    pts = [(cx + math.cos(i / segs * math.tau) * r, cy + math.sin(i / segs * math.tau) * r) for i in range(segs)]
    return core.add_polyline(sc, pts, width, color or dim(0.2), z=z, cyclic=True, name=name)


def hatch_panel(sc, x, y, w, h, color=None, step=0.12, angle=45, z=0.0):
    """A panel of diagonal hairlines (cheap engraving texture for 2D plates)."""
    segs = []
    c = math.cos(math.radians(angle)); s = math.sin(math.radians(angle))
    n = int((w + h) / step)
    for i in range(n):
        t = -h + i * step
        p0 = (x + t, y)
        p1 = (x + t + h, y + h)
        segs.append((p0, p1))
    ob = core.add_segments(sc, segs, 0.006, color or dim(0.12), z=z)
    # clip via a parent? curves are cheap; callers should size the panel to the area
    return ob


def fit_text(sc, text, font, width, height=None):
    m = core.measure(sc, text, font, 1.0)
    return width / m if m > 0 else 1.0