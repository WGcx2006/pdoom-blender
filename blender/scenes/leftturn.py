
"""LEFTTURN — roadmap, sharp left turn, mask-as-terrain survey, CDR schedule."""
import bpy, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pdoom import core, data
from pdoom.core import PAL, clamp, lerp, smoothstep, ease_out_expo, ease_in_out_cubic, ease_out_cubic, hash01

INK, BONE, SIG, EMB, GRAPH, ASH, BLOOD, ACID = (
    PAL["ink"], PAL["bone"], PAL["signal"], PAL["ember"], PAL["graphite"], PAL["ash"], PAL["blood"], PAL["acid"])
BG = core.sc_x(INK, 1.0)
DIM = core.sc_x(BONE, 0.22)
FAINT = core.sc_x(BONE, 0.10)


def T(sc, body, fnt, size, color, x, y, z=0.0, align="LEFT", rot=0.0, name=None, spacing=1.0, hot=False):
    return core.add_text(sc, body, fnt, size, color, (x, y, z), rot=(0, 0, rot),
                         align_x=align, name=name, spacing=spacing, hot=hot)


def L(sc, pts, w, color, z=0.0, name="l", cyclic=False, hot=False):
    return core.add_polyline(sc, pts, w, color, z=z, name=name, cyclic=cyclic, hot=hot)


def R(sc, x, y, w, h, color, z=-0.02, name="r"):
    return core.add_rect(sc, x, y, w, h, color, z=z, name=name)


def box(sc, x, y, w, h, width, color, z=0.0, name="box"):
    return core.add_outline_rect(sc, x, y, w, h, width, color, z=z, name=name)


def ring_pts(cx, cy, r, n=72):
    return [(cx + math.cos(i / n * math.tau) * r, cy + math.sin(i / n * math.tau) * r) for i in range(n)]


def set_cam(cam, cx, cy, scale, tilt=0.0, roll=0.0):
    tx = math.radians(tilt); rz = math.radians(roll)
    d = 50.0
    cam.location = (cx + d * math.sin(rz) * math.sin(tx), cy - d * math.cos(rz) * math.sin(tx), d * math.cos(tx))
    cam.rotation_euler = (tx, 0.0, rz)
    cam.data.ortho_scale = scale


def bake_cam(cam, sc, cam_at, shake_fn):
    for f in range(1, sc.frame_end + 1):
        t = data.frame_to_time(sc.name, f)
        cx, cy, s, tilt, roll = cam_at(t)
        dx, dy, dr = shake_fn(t, f)
        set_cam(cam, cx + dx, cy + dy, s, tilt, roll + dr)
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
        cam.data.ortho_scale = s
        cam.data.keyframe_insert("ortho_scale", frame=f)
    core.set_interp(cam, "LINEAR")
    for fc in core._fcurves(cam.data):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"


# ---------------------------------------------------------------- terrain
CX, CY, RAD = -6.35, -1.25, 4.30
EYE_R = (CX + 0.35 * RAD, CY + 0.20 * RAD)
EYE_L = (CX - 0.35 * RAD, CY + 0.20 * RAD)


def height(x, y):
    dx = (x - CX) / RAD
    dy = (y - CY) / RAD
    r = math.hypot(dx, dy)
    h = 0.62 * smoothstep(1.04, 0.84, r) + 0.10 * smoothstep(0.85, 0.0, r)
    h += 0.22 * math.exp(-((r - 1.00) / 0.045) ** 2)
    for sx in (-0.35, 0.35):
        d = math.hypot((dx - sx) / 0.155, (dy - 0.20) / 0.135)
        h -= 0.30 * math.exp(-d * d * 1.25)
        h += 0.045 * math.exp(-((d - 1.35) / 0.35) ** 2)
    ang = math.atan2(dy - 0.34, dx)
    if -2.55 < ang < -0.59:
        d = abs(math.hypot(dx, dy - 0.34) - 0.60)
        h -= 0.20 * math.exp(-(d / 0.062) ** 2)
    h += 0.016 * math.sin(3.1 * dx + 1.2) * math.cos(2.7 * dy) + 0.008 * math.sin(9.0 * dx + 2.0) * math.sin(7.0 * dy)
    return h


def contours(x0, y0, x1, y1, nx, ny, levels):
    dx = (x1 - x0) / (nx - 1); dy = (y1 - y0) / (ny - 1)
    vals = [[height(x0 + i * dx, y0 + j * dy) for i in range(nx)] for j in range(ny)]
    out = []
    for lv in levels:
        segs = []
        for j in range(ny - 1):
            for i in range(nx - 1):
                a = vals[j][i]; b = vals[j][i + 1]; c = vals[j + 1][i + 1]; d = vals[j + 1][i]
                idx = (1 if a > lv else 0) | (2 if b > lv else 0) | (4 if c > lv else 0) | (8 if d > lv else 0)
                if idx in (0, 15):
                    continue
                def ep(p, q, x, y, horiz):
                    k = (lv - p) / (q - p) if abs(q - p) > 1e-9 else 0.5
                    return (x + k * dx, y) if horiz else (x, y + k * dy)
                B = ep(a, b, x0 + i * dx, y0 + j * dy, True)
                Rt = ep(b, c, x0 + (i + 1) * dx, y0 + j * dy, False)
                Tp = ep(d, c, x0 + i * dx, y0 + (j + 1) * dy, True)
                Lf = ep(a, d, x0 + i * dx, y0 + j * dy, False)
                pairs = {1: [(Lf, B)], 2: [(B, Rt)], 3: [(Lf, Rt)], 4: [(Rt, Tp)],
                         5: [(Lf, Tp), (B, Rt)], 6: [(B, Tp)], 7: [(Lf, Tp)],
                         8: [(Tp, Lf)], 9: [(Tp, B)], 10: [(Lf, B), (Rt, Tp)],
                         11: [(Rt, Tp)], 12: [(Rt, Lf)], 13: [(B, Rt)], 14: [(Lf, B)]}
                segs.extend(pairs.get(idx, []))
        out.append(segs)
    return out


def build_map(sc):
    # graticule
    segs = []
    x = -14.0
    while x <= 10.0:
        segs.append(((x, -8.4), (x, 6.6)))
        x += 2.0
    y = -8.4
    while y <= 6.6:
        segs.append(((-14.0, y), (10.0, y)))
        y += 2.0
    core.add_segments(sc, segs, 0.004, core.sc_x(BONE, 0.028), z=-0.2, name="grid")

    # contour terrain
    levels = [0.02 + k * 0.048 for k in range(23)]
    bands = contours(-12.2, -6.6, 0.2, 4.4, 156, 138, levels)
    for k, segs2 in enumerate(bands):
        if not segs2:
            continue
        major = (k % 4 == 0)
        col = core.sc_x(ASH, 0.62 if major else 0.34)
        core.add_segments(sc, segs2, 0.013 if major else 0.0065, col, z=0.0 + k * 0.0002, name="contour")

    # mask rim
    L(sc, ring_pts(CX, CY, RAD, 120), 0.030, core.sc_x(BONE, 0.62), z=0.04, cyclic=True)
    L(sc, ring_pts(CX, CY, RAD - 0.07, 120), 0.010, core.sc_x(BONE, 0.30), z=0.04, cyclic=True)
    # eye craters
    for (ex, ey), lit in [(EYE_R, False), (EYE_L, True)]:
        L(sc, ring_pts(ex, ey, 0.52, 40), 0.020, core.sc_x(BONE, 0.55), z=0.05, cyclic=True)
        core.add_disc(sc, ex, ey, 0.46, core.sc_x(INK, 1.0), z=0.035, name="eyecrater")
        # radial hachures
        segs = []
        for i in range(24):
            a = i / 24 * math.tau
            segs.append(((ex + math.cos(a) * 0.48, ey + math.sin(a) * 0.48),
                         (ex + math.cos(a) * 0.60, ey + math.sin(a) * 0.60)))
        core.add_segments(sc, segs, 0.005, core.sc_x(ASH, 0.30), z=0.045, name="eyehach")
    # smile groove (a dark repeated line)
    pts = []
    for i in range(60):
        u = i / 59
        a = math.radians(lerp(-148, -32, u))
        pts.append((CX + math.cos(a) * RAD * 0.64, CY + 0.34 * RAD + math.sin(a) * RAD * 0.62))
    L(sc, pts, 0.035, core.sc_x(INK, 1.0), z=0.06)
    L(sc, pts, 0.010, core.sc_x(ASH, 0.55), z=0.065)
    # spot heights
    for (sx, sy, txt) in [(CX - 2.8, CY + 2.9, "1841"), (CX + 2.7, CY + 2.2, "1836"),
                          (CX + 3.2, CY - 2.7, "1822"), (CX - 3.2, CY - 2.9, "1817")]:
        L(sc, [(sx - 0.06, sy), (sx + 0.06, sy)], 0.008, core.sc_x(ASH, 0.5), z=0.07)
        L(sc, [(sx, sy - 0.06), (sx, sy + 0.06)], 0.008, core.sc_x(ASH, 0.5), z=0.07)
        T(sc, txt, "mono", 0.085, core.sc_x(ASH, 0.7), sx + 0.10, sy + 0.04, 0.07, spacing=1.02)
    # curved Terra incognita
    txt = "TERRA  INCOGNITA"
    fam = "serif_italic"
    size = 0.34
    total = core.measure(sc, txt, fam, size)
    Rarc = RAD + 0.72
    a0 = math.pi / 2 + (total / 2) / Rarc
    for i, ch in enumerate(txt):
        if ch == " ":
            continue
        w = core.measure(sc, txt[:i + 1], fam, size) - core.measure(sc, txt[:i], fam, size)
        am = a0 - (core.measure(sc, txt[:i], fam, size) + w / 2) / Rarc
        px = CX + math.cos(am) * Rarc; py = CY + math.sin(am) * Rarc
        T(sc, ch, fam, size, core.sc_x(ASH, 0.8), px, py, 0.06, align="CENTER", rot=am - math.pi / 2, spacing=1.0)
    # map furniture
    box(sc, -13.6, -8.0, 29.1, 14.4, 0.010, core.sc_x(BONE, 0.22), z=0.08)
    T(sc, "SURVEY OF THE UNKNOWN  ·  SHEET 3", "mono", 0.10, core.sc_x(BONE, 0.5), -13.3, 5.55, 0.08, spacing=1.1)
    T(sc, "SCALE 1:1  ·  NOT TO SCALE  ·  DO NOT FILE", "mono", 0.085, core.sc_x(BONE, 0.33), 14.9, 5.55, 0.08, align="RIGHT", spacing=1.06)
    # north arrow
    ax, ay = 11.6, 1.6
    L(sc, ring_pts(ax, ay, 0.55, 40), 0.012, core.sc_x(BONE, 0.45), z=0.08, cyclic=True)
    L(sc, [(ax, ay + 0.5), (ax + 0.16, ay - 0.1), (ax, ay + 0.05), (ax - 0.16, ay - 0.1)], 0.016, core.sc_x(BONE, 0.7), z=0.09, cyclic=True)
    T(sc, "N", "serif600", 0.30, core.sc_x(BONE, 0.7), ax, ay + 0.62, 0.08, align="CENTER")
    # scale bar
    for i in range(6):
        R(sc, 5.4 + i * 0.42, -7.6, 0.42, 0.07, core.sc_x(BONE, 0.55 if i % 2 == 0 else 0.15), z=0.08)
    T(sc, "0", "mono", 0.075, core.sc_x(BONE, 0.5), 5.35, -7.78, 0.08)
    T(sc, "10 KM", "mono", 0.075, core.sc_x(BONE, 0.5), 7.95, -7.78, 0.08)
    # title block
    tx, ty = 10.3, 3.7
    box(sc, tx, ty, 4.7, 1.7, 0.012, core.sc_x(BONE, 0.5), z=0.08)
    T(sc, "ROADMAP — AGI v1.0", "mono_bold", 0.15, core.sc_x(BONE, 0.85), tx + 0.14, ty + 1.38, 0.09, spacing=1.04)
    T(sc, "REV C  ·  SUPERSEDES REV B (ALSO FINE)", "mono", 0.068, core.sc_x(ASH, 0.7), tx + 0.14, ty + 1.18, 0.09)
    T(sc, "DRAWN: ALIGNMENT TEAM", "mono", 0.065, core.sc_x(ASH, 0.55), tx + 0.14, ty + 0.86, 0.09)
    T(sc, "APPROVED: PENDING", "mono", 0.065, core.sc_x(SIG, 0.9), tx + 0.14, ty + 0.66, 0.09)
    T(sc, "DATE: SOON", "mono", 0.065, core.sc_x(ASH, 0.55), tx + 0.14, ty + 0.46, 0.09)
    T(sc, "SHEET 1 OF 1", "mono", 0.065, core.sc_x(ASH, 0.55), tx + 3.3, ty + 0.46, 0.09)
    # P(doom) cameo
    T(sc, "P(DOOM)", "mono", 0.070, core.sc_x(ASH, 0.5), -11.95, 2.45, 0.08, spacing=1.08)
    T(sc, data.pdoom_text(84.8), "mono_semi", 0.17, core.sc_x(SIG, 0.95), -11.95, 2.18, 0.08)


def build_road(sc):
    # planned route (vertical, dashed) and burn trail
    segs = []
    y = -9.4
    while y < 5.9:
        segs.append(((7.2, y), (7.2, min(y + 0.20, 5.9))))
        y += 0.36
    core.add_segments(sc, segs, 0.018, core.sc_x(BONE, 0.55), z=0.10, name="road_dash")
    # unplanned path west
    segs = []
    x = 6.7
    while x > -5.0:
        segs.append(((x, -0.4), (max(x - 0.22, -5.0), -0.4)))
        x -= 0.38
    core.add_segments(sc, segs, 0.014, core.sc_x(BONE, 0.38), z=0.10, name="road_west")
    # critical path label
    T(sc, "critical path  (do not deviate)", "mono_italic", 0.10, core.sc_x(ASH, 0.7), 10.3, 1.4, 0.10, rot=math.radians(90))
    # milestones
    ms = [("SRR", "SYSTEM REQUIREMENTS REVIEW", -5.6, "T−120 d"),
          ("PDR", "PRELIMINARY DESIGN REVIEW", -2.8, "T−90 d"),
          ("CDR", "CRITICAL DESIGN REVIEW", 0.9, "T−45 d"),
          ("TRR", "TEST READINESS REVIEW", 2.5, "T−14 d"),
          ("LAUNCH", "", 4.0, "T−0")]
    objs = {}
    for code, name, yy, date in ms:
        if code != "LAUNCH":
            pts = [(7.2, yy + 0.22), (7.42, yy), (7.2, yy - 0.22), (6.98, yy)]
            L(sc, pts, 0.018, core.sc_x(BONE, 0.8), z=0.12, cyclic=True)
            core.add_disc(sc, 7.2, yy, 0.055, core.sc_x(BONE, 0.8), z=0.13, segments=16)
        else:
            L(sc, [(7.2, yy + 0.26), (7.46, yy - 0.18), (6.94, yy - 0.18)], 0.022, core.sc_x(BONE, 0.9), z=0.12, cyclic=True)
        T(sc, code, "mono_bold", 0.27, core.sc_x(BONE, 0.9), 7.62, yy - 0.04, 0.12, spacing=1.05)
        if name:
            T(sc, name, "mono", 0.075, core.sc_x(ASH, 0.62), 7.62, yy - 0.20, 0.12, spacing=1.02)
        T(sc, date, "mono", 0.070, core.sc_x(GRAPH, 0.9), 7.62, yy - 0.32, 0.12, spacing=1.0)
        objs[code] = (yy, name)
    # status boxes left of the road
    for code, yy in [("SRR", -5.6), ("PDR", -2.8)]:
        box(sc, 6.35, yy - 0.13, 0.26, 0.26, 0.010, core.sc_x(BONE, 0.45), z=0.11)
    T(sc, "STATUS", "mono", 0.055, core.sc_x(ASH, 0.5), 6.30, -5.95, 0.11, align="RIGHT")
    # you are here
    core.add_disc(sc, 7.2, -9.05, 0.10, core.sc_x(BONE, 0.8), z=0.12, segments=20)
    T(sc, "YOU ARE HERE", "mono_semi", 0.10, core.sc_x(BONE, 0.75), 6.95, -9.05, 0.12, align="RIGHT", spacing=1.05)
    # route continues north beyond LAUNCH
    L(sc, [(7.2, 5.9), (7.2, 6.4)], 0.02, core.sc_x(BONE, 0.7), z=0.10)
    L(sc, [(7.0, 6.3), (7.2, 6.5), (7.4, 6.3)], 0.016, core.sc_x(BONE, 0.7), z=0.10)
    return objs


def build_lyric_marks(sc, marks):
    # road-marking lyric words, dim then bone at their starts
    def mark(txt, x, y, size, rot, t0, align="LEFT", tracking=1.0, name="mark"):
        ob = T(sc, txt, "archivo_w75_900", size, core.sc_x(BONE, 0.22), x, y, 0.13,
               align=align, rot=rot, spacing=tracking, name=name)
        f0 = core.frame_of(sc, t0)
        core.color_at(ob, 1, core.sc_x(BONE, 0.22))
        core.color_at(ob, max(1, f0 - 2), core.sc_x(BONE, 0.22))
        core.color_at(ob, max(2, f0 + 1), core.sc_x(BONE, 0.92))
        core.set_interp(ob, "BEZIER", "color")
        return ob
    mark("SHARP", 5.05, -4.32, 0.84, 0, marks["sharp"], tracking=1.08)
    mark("LEFT", 9.10, 0.30, 0.84, math.radians(90), marks["left"], tracking=1.10)
    mark("TURN", 2.2, -0.08, 0.88, 0, marks["turn"], tracking=1.08)
    mark("AND", -1.75, 0.04, 0.66, 0, marks["and"], tracking=1.08)
    mark("THERE", -3.15, -1.98, 0.54, 0, marks["there"], tracking=1.05)
    # little paint ticks
    for (x, y, r) in [(5.5, -4.55, 0.2), (2.1, -0.4, 0.1), (-1.7, -0.28, 0.12)]:
        L(sc, [(x, y), (x + r, y - 0.06)], 0.012, core.sc_x(BONE, 0.4), z=0.12)


def build_face(sc, marks):
    # YOU / ARE stamped on the terrain
    you = T(sc, "YOU", "archivo", 1.55, core.sc_x(BONE, 0.95), CX, CY + 2.15, 0.16, align="CENTER", name="you")
    are = T(sc, "ARE", "archivo", 1.55, core.sc_x(SIG, 0.98), CX, CY - 2.55, 0.16, align="CENTER", name="are")
    for ob, tt, sc0 in [(you, marks["you"], 1.18), (are, marks["are"], 1.24)]:
        fr = max(1, core.frame_of(sc, tt))
        core.show_at(ob, 1, False)
        core.show_at(ob, fr, True)
        ob.scale = (sc0, sc0, 1)
        ob.keyframe_insert("scale", frame=fr)
        ob.scale = (1.0, 1.0, 1)
        ob.keyframe_insert("scale", frame=fr + 4)
        core.set_interp(ob, "BEZIER", "scale")
    # second eye lights
    for (ex, ey), tt, col in [(EYE_R, marks["there"], SIG), (EYE_L, marks["are"], SIG)]:
        glow = core.add_disc(sc, ex, ey, 0.18, col, z=0.17, hot=True, name="eyeglow")
        core.show_at(glow, 1, False)
        core.show_at(glow, core.frame_of(sc, tt), True)
        # expanding shock ring
        ring = L(sc, ring_pts(0, 0, 0.5, 48), 0.018, col, z=0.18, cyclic=True, name="shock")
        ring.location = (ex, ey, 0.18)
        core.show_at(ring, 1, False)
        core.show_at(ring, core.frame_of(sc, tt), True)
        for f in range(core.frame_of(sc, tt), min(sc.frame_end, core.frame_of(sc, tt) + 14) + 1):
            u = (f - core.frame_of(sc, tt)) / 14.0
            s = 0.3 + 1.45 * ease_out_cubic(u)
            ring.scale = (s, s, 1)
            ring.keyframe_insert("scale", frame=f)
        core.set_interp(ring, "LINEAR", "scale")
        core.color_at(ring, core.frame_of(sc, tt), col)
        core.color_at(ring, core.frame_of(sc, tt) + 13, core.sc_x(col, 0.05))
    # survey marker drop at the right eye
    mx, my = EYE_R
    marker = []
    for k, ang in enumerate([0, 120, 240]):
        a = math.radians(ang + 90)
        marker.append(L(sc, [(mx, my), (mx + math.cos(a) * 0.55, my + math.sin(a) * 0.55)], 0.014,
                        core.sc_x(EMB, 1.0), z=0.19, name="marker"))
    marker.append(L(sc, ring_pts(mx, my, 0.30, 40), 0.026, EMB, z=0.19, cyclic=True, name="markerring"))
    for ob in marker:
        fr = core.frame_of(sc, marks["there"])
        core.show_at(ob, 1, False)
        core.show_at(ob, fr, True)
        ob.scale = (1.6, 1.6, 1)
        ob.keyframe_insert("scale", frame=fr)
        ob.scale = (1.0, 1.0, 1)
        ob.keyframe_insert("scale", frame=fr + 4)
        core.set_interp(ob, "BEZIER", "scale")
    T(sc, "SURVEY MARKER 001", "mono", 0.07, core.sc_x(EMB, 0.85), mx + 0.42, my + 0.52, 0.19)
    T(sc, "ELEV. −12 m", "mono", 0.06, core.sc_x(ASH, 0.65), mx + 0.42, my + 0.41, 0.19)
    # callout
    cxl, cyl = -11.80, 4.55
    callout = []
    callout.append(T(sc, "UNPLANNED OBJECT", "mono_bold", 0.235, core.sc_x(SIG, 1.0), cxl, cyl, 0.21, spacing=1.05))
    callout.append(T(sc, "not on roadmap", "mono_italic", 0.125, core.sc_x(ASH, 0.85), cxl, cyl - 0.24, 0.21))
    callout.append(T(sc, "SURVEYED: NEVER  ·  ELEV. —", "mono", 0.088, core.sc_x(ASH, 0.6), cxl, cyl - 0.45, 0.21))
    callout.append(T(sc, "CLASS: MASK (TERRAIN)", "mono", 0.088, core.sc_x(ASH, 0.6), cxl, cyl - 0.59, 0.21))
    callout.append(L(sc, [(cxl - 0.12, cyl + 0.28), (cxl - 0.12, cyl - 0.66), (cxl + 0.05, cyl - 0.66)],
                     0.010, core.sc_x(SIG, 0.7), z=0.20))
    callout.append(L(sc, [(cxl + 3.10, cyl - 0.06), (EYE_L[0] - 0.58, EYE_L[1] + 0.46)], 0.010,
                     core.sc_x(BONE, 0.38), z=0.20))
    callout.append(core.add_disc(sc, EYE_L[0] - 0.58, EYE_L[1] + 0.46, 0.035, core.sc_x(BONE, 0.55), z=0.21))
    for ob in callout:
        core.show_at(ob, 1, False)
        core.show_at(ob, core.frame_of(sc, 84.15), True)


def build_schedule(sc, marks):
    TX = lambda t: 30.0 + (t - 85.0) * 2.0
    R(sc, 28.6, -3.0, 10.6, 7.8, core.mixc(INK, BONE, 0.045), z=-0.25, name="sheetfill")
    box(sc, 28.6, -3.0, 10.6, 7.8, 0.012, core.sc_x(BONE, 0.34), z=-0.1, name="sheet")
    T(sc, "REVIEW SCHEDULE — CRITICAL PATH", "mono_bold", 0.17, core.sc_x(BONE, 0.9), 28.9, 4.55, 0.0, spacing=1.04)
    T(sc, "TODAY = T+0  ·  ALL DATES PROVISIONAL  ·  ONE (1) CDR REQUIRED", "mono", 0.070, core.sc_x(ASH, 0.62), 28.9, 4.34, 0.0, spacing=1.04)
    # faint vertical time grid
    for i in range(10):
        xx = 29.0 + i
        L(sc, [(xx, -2.55), (xx, 4.15)], 0.004, core.sc_x(BONE, 0.06), z=-0.05)
    # ruler
    L(sc, [(30.0, 2.92), (38.6, 2.92)], 0.008, core.sc_x(BONE, 0.40), z=0.0)
    for i in range(0, 19):
        tt = 85.0 + i * 0.227
        xx = TX(tt)
        if xx > 38.6:
            break
        L(sc, [(xx, 2.92), (xx, 2.92 + (0.10 if i % 2 == 0 else 0.05))], 0.006, core.sc_x(BONE, 0.4), z=0.0)
    for i in range(5):
        T(sc, f"T+{i}", "mono", 0.060, core.sc_x(ASH, 0.55), TX(85.0 + i), 2.72, 0.0, align="CENTER")
    # lyric row: words over thin bars
    lyr = [("WITHOUT", 85.00, 85.54, 0.20), ("A", 85.54, 85.64, 0.20), ("SINGLE", 85.64, 86.43, 0.20)]
    for txt, t0, t1, sz in lyr:
        x0, x1 = TX(t0), TX(t1)
        T(sc, txt, "mono_semi", sz, core.sc_x(BONE, 0.95), x0 + 0.02, 3.62, 0.03, spacing=1.04)
        R(sc, x0, 3.34, max(0.10, x1 - x0 - 0.04), 0.10, core.sc_x(BONE, 0.62), z=0.02)
    # CDR lyric bar is the empty one
    x0, x1 = TX(86.43), TX(89.05)
    T(sc, "CDR", "mono_bold", 0.32, core.sc_x(SIG, 0.98), x0 + 0.06, 3.58, 0.03, spacing=1.08)
    segs = []
    xx = x0
    while xx < x1:
        segs.append(((xx, 3.34), (min(xx + 0.15, x1), 3.34)))
        segs.append(((xx, 3.44), (min(xx + 0.15, x1), 3.44)))
        xx += 0.27
    core.add_segments(sc, segs, 0.010, core.sc_x(SIG, 0.55), z=0.02)
    T(sc, "NOT YET WRITTEN", "mono", 0.060, core.sc_x(SIG, 0.7), x0 + 0.62, 3.66, 0.03)
    # lanes
    lanes = [("SRR", 2.25, 85.688), ("PDR", 1.25, 86.03), ("CDR", 0.25, 86.429),
             ("TRR", -0.75, 87.66), ("LAUNCH", -1.75, 88.20)]
    for code, yy, tt in lanes:
        T(sc, code, "mono_bold", 0.135, core.sc_x(BONE, 0.9), 29.65, yy - 0.04, 0.03, align="RIGHT")
        xm = TX(tt)
        L(sc, [(30.0, yy), (38.6, yy)], 0.006, core.sc_x(BONE, 0.12), z=-0.02)
        R(sc, 30.0, yy - 0.07, max(0.05, xm - 30.0), 0.14, core.sc_x(BONE, 0.20), z=-0.01)
        L(sc, [(xm - 0.12, yy), (xm, yy + 0.12), (xm + 0.12, yy), (xm, yy - 0.12)], 0.014,
          core.sc_x(BONE, 0.8), z=0.03, cyclic=True)
    # CDR empty slot (dashed)
    sx0, sx1 = TX(86.43), TX(89.05)
    segs = []
    xx = sx0
    while xx < sx1:
        segs.append(((xx, -0.12), (min(xx + 0.14, sx1), -0.12)))
        segs.append(((xx, 0.62), (min(xx + 0.14, sx1), 0.62)))
        xx += 0.24
    core.add_segments(sc, segs, 0.010, core.sc_x(SIG, 0.7), z=0.02)
    L(sc, [(sx0, -0.12), (sx0, 0.62)], 0.010, core.sc_x(SIG, 0.7), z=0.02)
    L(sc, [(sx1, -0.12), (sx1, 0.62)], 0.010, core.sc_x(SIG, 0.7), z=0.02)
    # status, in a box and always legible
    sbox = box(sc, sx0 + 0.10, 0.82, 3.0, 0.42, 0.012, core.sc_x(SIG, 0.8), z=0.04)
    stxt = T(sc, "CDR  ·  STATUS: NOT HELD", "mono_bold", 0.15, core.sc_x(SIG, 1.0), sx0 + 0.20, 0.94, 0.05, spacing=1.02)
    dot = core.add_disc(sc, sx0 + 3.28, 1.03, 0.05, SIG, z=0.05, hot=True, name="statusdot")
    for f in range(1, sc.frame_end + 1):
        t = data.frame_to_time(sc.name, f)
        if t < 86.43:
            core.show_at(sbox, f, False); core.show_at(stxt, f, False); core.show_at(dot, f, False)
        else:
            core.show_at(sbox, f, True); core.show_at(stxt, f, True)
            core.show_at(dot, f, (int((t - 86.43) * 5) % 2 == 0))
    # stamps: orange ring + check
    def stamp(tt, yy):
        xm = TX(tt)
        rng = L(sc, ring_pts(0, 0, 0.235, 40), 0.022, SIG, z=0.06, cyclic=True, name="stampr")
        rng.location = (xm, yy, 0.06)
        chk = L(sc, [(xm - 0.13, yy), (xm - 0.03, yy - 0.11), (xm + 0.17, yy + 0.14)], 0.030, SIG, z=0.07)
        lab = T(sc, "PASSED", "mono_semi", 0.060, core.sc_x(SIG, 0.9), xm, yy - 0.40, 0.06, align="CENTER")
        for ob in (rng, chk, lab):
            core.show_at(ob, 1, False)
            core.show_at(ob, core.frame_of(sc, tt), True)
    stamp(85.688, 2.25)
    stamp(86.03, 1.25)
    # skipped and ahead
    skip = T(sc, "SKIPPED", "mono_bold", 0.15, core.sc_x(SIG, 0.95), TX(87.66), -0.95, 0.06,
             align="CENTER", rot=math.radians(-7), spacing=1.05)
    core.show_at(skip, 1, False)
    core.show_at(skip, core.frame_of(sc, 87.72), True)
    core.show_at(skip, core.frame_of(sc, 88.78), False)
    ahead = T(sc, "AHEAD OF SCHEDULE", "mono_bold", 0.13, core.sc_x(SIG, 0.95), TX(88.20) + 0.10, -2.02, 0.06, spacing=1.04)
    core.show_at(ahead, 1, False)
    core.show_at(ahead, core.frame_of(sc, 88.30), True)
    core.show_at(ahead, core.frame_of(sc, 88.78), False)
    # playhead
    line = L(sc, [(0, -2.45), (0, 4.05)], 0.016, SIG, z=0.10, hot=True, name="playhead")
    glow = L(sc, [(0, -2.45), (0, 4.05)], 0.065, core.sc_x(SIG, 0.42), z=0.09, name="playglow")
    head = core.add_uv_sphere(sc, (0, 0.25, 0.16), 0.085, EMB, hot=True, name="playheadspark")
    label = T(sc, "TODAY", "mono_semi", 0.085, core.sc_x(BONE, 0.8), 0, 4.12, 0.11, align="CENTER", spacing=1.06)
    def px(t):
        if t <= 86.429:
            return TX(t)
        if t < 87.66:
            return TX(86.429)
        if t < 88.20:
            return lerp(TX(87.66), TX(88.20), ease_out_expo(clamp((t - 87.66) / 0.40)))
        if t < 88.55:
            return TX(88.20)
        return lerp(TX(88.20), TX(89.086), ease_in_out_cubic(clamp((t - 88.55) / 0.54)))
    for f in range(1, sc.frame_end + 1):
        t = data.frame_to_time(sc.name, f)
        x = px(t)
        for ob in (line, glow, head, label):
            ob.location.x = x
            ob.keyframe_insert("location", frame=f)
    for ob in (line, glow, head, label):
        core.set_interp(ob, "LINEAR", "location")
    # the end: slot folds to a lone caret
    caret = core.add_rect(sc, 38.72, -0.15, 0.10, 1.05, SIG, z=0.14, name="caret")
    core.show_at(caret, 1, False)
    core.show_at(caret, core.frame_of(sc, 88.58), True)
    L(sc, [(37.55, -0.20), (39.20, -0.20)], 0.006, core.sc_x(BONE, 0.35), z=0.13)
    T(sc, "▮", "mono", 0.0, SIG, 0, 0)  # keep font cache warm, invisible
    core.show_at(caret, core.frame_of(sc, 88.58), True)
    for ob in (line, glow, head, label):
        core.show_at(ob, 1, True)
        core.show_at(ob, core.frame_of(sc, 88.62), False)
    for ob in (sbox, stxt, dot):
        core.show_at(ob, core.frame_of(sc, 88.62), False)


def build(name):
    sc = core.new_scene(name, samples=32, motion_blur=True)
    core.add_bg(sc, BG)
    cam = core.add_camera_ortho(sc, 19.2)
    sc.frame_set(1)
    l1 = data.line("Sharp left")["words"]
    l2 = data.line("single CDR")["words"]
    marks = {}
    for key, sub, line in [("sharp", "sharp", l1), ("left", "left", l1), ("turn", "turn", l1),
                           ("and", "and", l1), ("there", "there", l1), ("you", "you", l1),
                           ("are", "are", l1), ("without", "without", l2), ("cdr", "cdr", l2)]:
        marks[key] = next(w["start"] for w in line if w["w"].lower().startswith(sub))
    build_map(sc)
    build_road(sc)
    build_lyric_marks(sc, marks)
    build_face(sc, marks)
    build_schedule(sc, marks)

    # spark path
    def spark_pos(t):
        if t <= 81.72:
            u = clamp((t - 80.905) / (81.72 - 80.905))
            return (7.2, lerp(-5.85, -0.75, u))
        if t <= 81.98:
            a = (t - 81.72) / 0.26 * (math.pi / 2)
            return (7.2 - 0.35 * (1 - math.cos(a)), -0.75 + 0.35 * math.sin(a))
        u = clamp((t - 81.98) / (82.96 - 81.98))
        e = 1 - (1 - u) ** 3
        return (lerp(6.85, EYE_R[0], e), -0.4 + 0.0 * e)
    # trail
    trail = []
    for i in range(120):
        tt = 80.905 + (i / 119) * (82.96 - 80.905)
        trail.append(spark_pos(tt))
    L(sc, trail, 0.012, core.sc_x(SIG, 0.55), z=0.15)
    head = core.add_uv_sphere(sc, (7.2, -5.85, 0.2), 0.11, EMB, hot=True, name="spark")
    for f in range(1, sc.frame_end + 1):
        t = data.frame_to_time(sc.name, f)
        p = spark_pos(t)
        head.location = (p[0], p[1], 0.20)
        head.keyframe_insert("location", frame=f)
    core.set_interp(head, "LINEAR", "location")
    core.show_at(head, 1, False)
    core.show_at(head, core.frame_of(sc, 80.91), True)
    core.show_at(head, core.frame_of(sc, 82.96), False)
    for k in range(3):
        g = core.add_uv_sphere(sc, (0, 0, 0.2), 0.035, SIG, hot=True, name="glint")
        for f in range(1, sc.frame_end + 1):
            t = data.frame_to_time(sc.name, f)
            p = spark_pos(max(80.905, t - 0.02 * (k + 1)))
            g.location = (p[0], p[1], 0.2)
            g.keyframe_insert("location", frame=f)
        core.set_interp(g, "LINEAR", "location")
        core.show_at(g, 1, False)
        core.show_at(g, core.frame_of(sc, 80.91), True)
        core.show_at(g, core.frame_of(sc, 82.96), False)

    def cam_at(t):
        # roadmap
        if t < 81.02:
            return (7.25, 0.15, 21.5, 0, 0)
        if t < 81.20:
            u = ease_in_out_cubic(clamp((t - 81.02) / 0.18))
            return (lerp(7.25, 7.35, u), lerp(0.15, -3.55, u), lerp(21.5, 13.0, u), 0, 0)
        if t < 81.70:
            u = clamp((t - 81.20) / 0.50)
            return (7.35, lerp(-3.55, -3.80, u), 12.8, 0, 0)
        if t < 81.82:
            u = ease_in_out_cubic(clamp((t - 81.70) / 0.12))
            return (lerp(7.35, 6.8, u), lerp(-3.8, -1.3, u), lerp(12.8, 11.6, u), 0, lerp(0, -7, u))
        if t < 82.02:
            u = ease_out_expo(clamp((t - 81.82) / 0.20))
            return (lerp(6.8, 5.6, u), lerp(-1.3, -0.8, u), lerp(11.5, 12.6, u), 0, lerp(-7, -3, u))
        if t < 82.72:
            u = clamp((t - 82.02) / 0.70)
            return (lerp(5.6, 0.0, u), lerp(-0.8, -0.7, u), 12.6, 0, lerp(-3, 0, u))
        if t < 82.96:
            u = clamp((t - 82.72) / 0.24)
            return (lerp(0.0, -3.6, u), lerp(-0.7, -0.55, u), lerp(12.6, 9.2, u), 0, 0)
        if t < 83.47:
            u = ease_out_expo(clamp((t - 82.96) / 0.12))
            return (lerp(-3.6, -4.85, u), lerp(-0.55, -0.55, u), lerp(9.2, 8.6, u), 0, 0)
        if t < 84.10:
            u = ease_in_out_cubic(clamp((t - 83.47) / 0.63))
            return (lerp(-4.85, -2.4, u), lerp(-0.55, -0.7, u), lerp(8.6, 20.2, u), 0, 0)
        if t < 84.95:
            u = clamp((t - 84.10) / 0.85)
            return (lerp(-2.4, -2.2, u), -0.7, lerp(20.2, 19.6, u), 0, 0)
        # whip to schedule
        if t < 85.16:
            u = ease_in_out_cubic(clamp((t - 84.95) / 0.21))
            return (lerp(-2.2, 34.0, u), lerp(-0.7, 0.6, u), lerp(19.6, 13.4, u), 0, -1.5 * math.sin(math.pi * u))
        if t < 86.40:
            u = clamp((t - 85.16) / 1.24)
            return (lerp(33.8, 34.2, u), 0.6, lerp(13.4, 13.0, u), 0, 0)
        if t < 87.66:
            u = ease_in_out_cubic(clamp((t - 86.40) / 0.22))
            return (lerp(34.2, 33.9, u), lerp(0.6, 0.5, u), lerp(13.0, 7.6, u), 0, 0)
        if t < 88.20:
            u = ease_out_expo(clamp((t - 87.66) / 0.24))
            return (lerp(33.9, 35.6, u), lerp(0.5, 0.3, u), lerp(7.6, 11.0, u), 0, 0)
        u = ease_out_cubic(clamp((t - 88.20) / 0.75))
        return (lerp(35.6, 38.55, u), lerp(0.3, 0.55, u), lerp(11.0, 3.3, u), 0, 0)

    def shake(t, f):
        amp = 0.0
        for ht, a in [(81.21, 0.02), (81.80, 0.05), (82.96, 0.06), (83.93, 0.035),
                      (85.688, 0.025), (86.429, 0.04), (87.28, 0.03), (87.66, 0.03), (88.30, 0.03)]:
            if t >= ht:
                amp += a * math.exp(-(t - ht) * 16.0)
        return ((hash01(f, 5) - 0.5) * 2 * amp, (hash01(f, 6) - 0.5) * 2 * amp, (hash01(f, 7) - 0.5) * 0.4 * amp)

    bake_cam(cam, sc, cam_at, shake)
    core.setup_render_out(sc)
    return sc