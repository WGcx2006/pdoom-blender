"""HOOK x4 — typographic slams, escalating. One word per sung word."""
import bpy, math, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pdoom import core, data
from pdoom.core import PAL, lerp, clamp, smoothstep, ease_out_expo, hash01

INK, BONE, SIG, EMB, GRAPH, ASH, BLOOD = PAL["ink"], PAL["bone"], PAL["signal"], PAL["ember"], PAL["graphite"], PAL["ash"], PAL["blood"]
DIM = core.sc_x(BONE, 0.30)


def fit(sc, text, font, width):
    m = core.measure(sc, text, font, 1.0)
    return width / m if m > 0 else 1.0


def header(sc, label, t0=None, color=None, x=-8.65, y=4.55):
    return core.add_text(sc, label, "mono_med", 0.135, color or GRAPH, (x, y, 0), spacing=1.06)


def grid(sc, step=1.6, color=None, z=-2):
    segs = []
    x = -9.6
    while x <= 9.6:
        segs.append(((x, -5.4), (x, 5.4)))
        x += step
    y = -5.4
    while y <= 5.4:
        segs.append(((-9.6, y), (9.6, y)))
        y += step
    return core.add_segments(sc, segs, 0.005, color or core.sc_x(BONE, 0.045), z=z)


def shake(cam, sc, hits, amp=0.045, decay=16.0, seed=1):
    for f in range(1, sc.frame_end + 1):
        t = data.frame_to_time(sc.name, f)
        dx = dy = 0.0
        for k, ht in enumerate(hits):
            if t >= ht:
                a = amp * math.exp(-(t - ht) * decay)
                dx += (hash01(seed, k, f) - 0.5) * 2 * a
                dy += (hash01(seed + 7, k, f * 3 + 1) - 0.5) * 2 * a
        cam.location = (dx, dy, 50)
        cam.keyframe_insert("location", frame=f)
    core.set_interp(cam, "LINEAR", "location")


def spark(sc, path, t0, t1, r=0.1, color=None):
    head = core.add_uv_sphere(sc, (0, 0, 1), r, color or EMB, hot=True, name="spark")
    f0, f1 = core.frame_of(sc, t0), core.frame_of(sc, t1)
    core.show_at(head, 1, False)
    core.show_at(head, max(1, f0), True)
    core.show_at(head, min(sc.frame_end, f1) + 1, False)
    for f in range(max(1, f0), min(sc.frame_end, f1) + 1):
        p = path(data.frame_to_time(sc.name, f))
        head.location = (p[0], p[1], 1.0)
        head.keyframe_insert("location", frame=f)
    core.set_interp(head, "LINEAR", "location")


def word_slam(ob, sc, t, scale0=1.22, dur=0.16, rot0=0.0, dx=0.0, dy=0.0):
    f = core.frame_of(sc, t)
    fd = max(2, core.frame_of(sc, t + dur))
    ob.rotation_euler = (0, 0, math.radians(rot0))
    ob.scale = (scale0, scale0, 1)
    ob.location = (ob.location.x + dx, ob.location.y + dy, ob.location.z)
    ob.keyframe_insert("scale", frame=max(1, f - 1))
    ob.keyframe_insert("location", frame=max(1, f - 1))
    core.show_at(ob, 1, False)
    core.show_at(ob, max(1, f), True)
    ob.rotation_euler = (0, 0, 0)
    ob.scale = (1, 1, 1)
    ob.location = (ob.location.x - dx, ob.location.y - dy, ob.location.z)
    ob.keyframe_insert("scale", frame=fd)
    ob.keyframe_insert("location", frame=fd)
    core.set_interp(ob, "BEZIER", "scale")
    core.set_interp(ob, "BEZIER", "location")


def rising_chars(sc, text, fnt, size, x, y, t_start, color, stagger=0.016, rise=0.9, z=0):
    objs = core.layout_chars(sc, text, fnt, size, x, y, z)
    for i, (ch, ob, cx) in enumerate(objs):
        t = t_start + i * stagger
        f = core.frame_of(sc, t)
        fd = core.frame_of(sc, t + 0.20)
        core.show_at(ob, 1, False)
        core.show_at(ob, max(1, f), True)
        base = (ob.location.x, ob.location.y, z)
        ob.location = (base[0], base[1] - rise, z)
        ob.keyframe_insert("location", frame=max(1, f))
        ob.location = (base[0], base[1], z)
        ob.keyframe_insert("location", frame=fd)
        core.set_interp(ob, "BEZIER", "location")
    return objs


def readout(sc, x, y, value, scale=1.0, color=None, label=True):
    color = color or SIG
    if label:
        core.add_text(sc, "P(DOOM)", "mono_med", 0.13 * scale, core.sc_x(BONE, 0.5), (x, y + 0.38 * scale, 0), spacing=1.08)
    core.add_text(sc, value, "mono_med", 0.46 * scale, color, (x, y, 0))


def hook_layout(sc, cam, t_i, t_u, t_m, t_p, ink_mode=False, up_width=12.0, p_width=15.0):
    col = INK if ink_mode else BONE
    im = core.add_text(sc, "I’M", "archivo", 1.7, col, (-8.65, 4.35, 0), name="im")
    word_slam(im, sc, t_i, 1.3, 0.18)
    usz = fit(sc, "UPPING", "archivo_w62_900", up_width)
    rising_chars(sc, "UPPING", "archivo_w62_900", usz, -8.65, 0.9, t_u, col, 0.014, 0.95)
    my = core.add_text(sc, "MY", "archivo", 1.7, core.sc_x(col, 0.55) if not ink_mode else core.sc_x(col, 1.0), (-8.65, -0.95, 0), name="my")
    word_slam(my, sc, t_m, 1.45, 0.12)
    psz = fit(sc, "P(DOOM)", "archivo", p_width * (0.92 if ink_mode else 1.0))
    pdoom = core.add_text(sc, "P(DOOM)", "archivo", psz, col if ink_mode else SIG, (8.65, -3.05, 0), align_x="RIGHT", name="pdoom")
    word_slam(pdoom, sc, t_p, 1.14, 0.22)
    return pdoom


def build(name):
    n = int(name[-1])
    sc = core.new_scene(name, samples=32, motion_blur=True)
    core.add_bg(sc)
    cam = core.add_camera_ortho(sc, 19.2)
    sc.frame_set(1)
    l = data.line("upping my P(doom)", n - 1)
    ws = l["words"]
    t_i, t_u, t_m, t_p = ws[0]["start"], ws[1]["start"], ws[2]["start"], ws[3]["start"]

    if n == 1:
        header(sc, "FIG. 03  ·  HOOK  ·  P(DOOM) 0.15", x=8.65, y=4.78, color=core.sc_x(BONE, 0.42))
        readout(sc, 5.9, 3.5, "0.15", 0.9, SIG)
        hook_layout(sc, cam, t_i, t_u, t_m, t_p)
        core.add_polyline(sc, [(-8.65, -1.45), (8.65, -1.45)], 0.010, core.sc_x(BONE, 0.22))
        core.add_polyline(sc, [(-8.65, 4.95), (-8.65, 4.6), (-8.3, 4.6)], 0.010, core.sc_x(BONE, 0.32))
        core.add_polyline(sc, [(8.65, -4.6), (8.65, -4.95), (8.3, -4.95)], 0.010, core.sc_x(BONE, 0.32))
        shake(cam, sc, [t_i, t_u, t_m, t_p], 0.03, 15, 3)

    elif n == 2:
        core.add_rect(sc, -9.6, -5.4, 19.2, 10.8, core.sc_x(SIG, 0.78), z=-4)
        header(sc, "FIG. 06  ·  HOOK  ·  P(DOOM) 0.42", x=8.65, y=4.78, color=core.sc_x(INK, 1.0))
        readout(sc, 5.9, 3.5, "0.42", 0.9, core.sc_x(INK, 1.0))
        hook_layout(sc, cam, t_i, t_u, t_m, t_p, ink_mode=True)
        core.add_polyline(sc, [(-8.65, -4.5), (8.65, -4.5)], 0.014, core.sc_x(INK, 1.0))
        core.add_polyline(sc, [(-8.65, -1.45), (8.65, -1.45)], 0.010, core.sc_x(INK, 0.75))
        # a single bone accent, like a print registration mark
        core.add_disc(sc, -8.65, 4.95, 0.09, core.sc_x(BONE, 0.9), z=0.1)
        shake(cam, sc, [t_i, t_u, t_m, t_p], 0.05, 14, 8)

    elif n == 3:
        header(sc, "FIG. 09  ·  HOOK  ·  P(DOOM) 0.81", x=8.65, y=4.78, color=core.sc_x(BONE, 0.30))
        # the words as a quiet sentence at the top
        x = -8.65
        a = core.add_text(sc, "I’M", "archivo300", 1.05, core.sc_x(BONE, 0.72), (x, 3.05, 0), name="im")
        word_slam(a, sc, t_i, 1.06, 0.2)
        x += core.measure(sc, "I’M", "archivo300", 1.05) + 0.38
        b = core.add_text(sc, "upping", "serif_italic", 1.55, core.sc_x(BONE, 0.85), (x, 3.0, 0), name="up")
        word_slam(b, sc, t_u, 1.04, 0.22)
        x += core.measure(sc, "upping", "serif_italic", 1.55) + 0.30
        c = core.add_text(sc, "my", "archivo300", 1.05, core.sc_x(BONE, 0.6), (x, 3.05, 0), name="my")
        word_slam(c, sc, t_m, 1.08, 0.15)
        # huge, almost-off value
        num = core.add_text(sc, "0.81", "mono_light", 6.2, core.sc_x(BONE, 0.13), (-8.9, -4.15, -1), name="num")
        # payoff: a small, precise P(DOOM) at the lower right
        psz = 1.15
        pdoom = core.add_text(sc, "P(DOOM)", "archivo300", psz, core.sc_x(SIG, 0.95), (8.6, -3.1, 0), align_x="RIGHT", name="pdoom")
        word_slam(pdoom, sc, t_p, 1.0, 0.3)
        core.add_polyline(sc, [(-9.5, 2.2), (9.5, 2.2)], 0.008, core.sc_x(BONE, 0.20))
        core.add_uv_sphere(sc, (2.6, 2.2, 0.2), 0.035, SIG, hot=True)
        core.add_text(sc, "ESTIMATE, REVISED — 0.81", "mono_med", 0.11, core.sc_x(BONE, 0.30), (-8.65, -4.7, 0), spacing=1.1)
        core.add_polyline(sc, [(5.6, -3.45), (8.62, -3.45)], 0.007, core.sc_x(SIG, 0.6))
        shake(cam, sc, [t_i, t_u, t_m, t_p], 0.012, 20, 11)

    else:
        grid(sc, 1.2, core.sc_x(SIG, 0.10))
        header(sc, "FIG. 12  ·  HOOK  ·  P(DOOM) 0.99999", x=8.65, y=4.78, color=core.sc_x(BONE, 0.45))
        # layered P(DOOM), all inside the frame
        psz = fit(sc, "P(DOOM)", "archivo", 14.2)
        copies = []
        for k, (dx, dy, col) in enumerate([(0.0, 0.0, BONE), (0.10, -0.10, core.sc_x(SIG, 0.9)),
                                           (-0.12, 0.10, core.sc_x(BLOOD, 1.0)), (0.18, 0.18, core.sc_x(BONE, 0.18))]):
            ob = core.add_text(sc, "P(DOOM)", "archivo", psz, col, (8.65 + dx, -2.9 + dy, -k * 0.05),
                               align_x="RIGHT", name=f"pdoom{k}")
            core.show_at(ob, 1, False)
            copies.append(ob)
        base = copies[0]
        core.show_at(base, max(1, core.frame_of(sc, t_p) - 1), True)
        # strobe the stack at 2-frame intervals after the hit
        f0 = core.frame_of(sc, t_p)
        for f in range(f0, sc.frame_end + 1, 2):
            for k in (1, 2, 3):
                core.show_at(copies[k], f, ((f - f0) // 2 + k) % 3 == 0)
        # words
        im = core.add_text(sc, "I’M", "archivo", 1.8, BONE, (-8.65, 4.35, 0), name="im")
        word_slam(im, sc, t_i, 1.3, 0.15)
        usz = fit(sc, "UPPING", "archivo_w62_900", 11.4)
        rising_chars(sc, "UPPING", "archivo_w62_900", usz, -8.65, 0.9, t_u, BONE, 0.008, 0.95)
        my = core.add_text(sc, "MY", "archivo", 1.7, core.sc_x(SIG, 0.9), (-8.65, -0.65, 0), name="my")
        word_slam(my, sc, t_m, 1.5, 0.1)
        # tiny stuttering number at the top
        for k, (x, y, s) in enumerate([(5.0, 3.6, 1.0), (1.2, 4.1, 0.55)]):
            ob = core.add_text(sc, "0.99999…", "mono_med", 0.45 * s, core.sc_x(SIG, 0.9), (x, y, 0), name=f"num{k}")
            core.show_at(ob, 1, False)
            core.show_at(ob, core.frame_of(sc, t_p) + k * 2, True)
        core.add_polyline(sc, [(-8.65, -4.5), (8.65, -4.5)], 0.010, core.sc_x(BONE, 0.3))
        shake(cam, sc, [t_i, t_u, t_m, t_p, t_p + 0.1, t_p + 0.2], 0.10, 12, 17)

    def path(t):
        k = clamp((t - t_p) / 0.55)
        return (lerp(-2.0, 8.2, k), lerp(3.8, -4.7, ease_out_expo(k)))
    if n in (1, 2, 4):
        spark(sc, path, t_p, t_p + 0.55, 0.12)
        core.add_polyline(sc, [(-2.0, 3.8), (1.5, 0.2), (5.2, -4.4)], 0.012, core.sc_x(SIG, 0.75), z=0.5)

    sc.render.filepath = os.path.join(core.OUT, "frames", name, "####")
    os.makedirs(os.path.dirname(sc.render.filepath), exist_ok=True)
    return sc