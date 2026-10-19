"""loom — the tree of continuations, [MASK] pre-training, and Droste self-upgrade.

Plate window 125.902–131.811 s (177 frames), three shots:
  1) "Just as foretold by Loom": a real 3D tree rooted on hook 4's exit thread. The line is
     generated token by token along the chosen path (orange weft) while dim alternatives sprout
     at every node with their probabilities. The last node shows a distribution until "Loom"
     is sampled (p 0.31 ▸ SAMPLED, Cormorant italic).
  2) "From masked pre-training days": a page of tokens; the lyric sits in solid [MASK] blocks
     that unmask, left to right, as each word is sung.
  3) "To recursive self-upgrade": a Droste corridor of upgrade portals, bottoming out in a
     glowing laptop screen (ilya's first shot).
"""
import bpy, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pdoom import core, data, motifs
from pdoom.core import (PAL, clamp, lerp, smoothstep, ease_out_expo, ease_in_out_cubic,
                        ease_out_cubic, ease_in_expo, ease_out_back, hash01, prog)

INK, BONE, SIG, EMB = PAL["ink"], PAL["bone"], PAL["signal"], PAL["ember"]
GRAPH, ASH, BLOOD = PAL["graphite"], PAL["ash"], PAL["blood"]
DIM = core.sc_x(BONE, 0.30)
FAINT = core.sc_x(BONE, 0.10)

Z0 = 21.0


def F(sc, t):
    return max(1, min(sc.frame_end, core.frame_of(sc, t)))


def vis(ob, f, on):
    ob.hide_render = not on
    ob.keyframe_insert("hide_render", frame=max(1, min(bpy.context.scene.frame_end, int(f))))
    for fc in core._fcurves(ob):
        if fc.data_path == "hide_render":
            for kp in fc.keyframe_points:
                kp.interpolation = "CONSTANT"


def mono(sc, text, x, y, size=0.12, color=None, align="LEFT", z=Z0 + 6.0, name="mono", spacing=1.03):
    return core.add_text(sc, text, "mono_med", size, color or GRAPH, (x, y, z),
                         align_x=align, name=name, spacing=spacing)


def word_color(sc, ob, word, fs, fe, active=SIG, dim=None, final=BONE, hold=0.10):
    dim = dim or core.sc_x(BONE, 0.26)
    core.color_at(ob, 1, dim)
    t0, t1 = data.frame_to_time(sc.name, fs), data.frame_to_time(sc.name, fe)
    if t1 < word["start"]:
        core.color_at(ob, fs, dim)
    elif t0 < word["start"]:
        core.color_at(ob, fs, dim)
        core.color_at(ob, F(sc, word["start"]), active)
    else:
        core.color_at(ob, fs, active)
    core.color_at(ob, max(fs, F(sc, word["end"] - 0.02)), active)
    core.color_at(ob, max(fs, F(sc, word["end"] + hold)), final)
    core.set_interp(ob, "LINEAR", "color")


def hit(t, t0, rate=12.0):
    return math.exp(-max(0.0, t - t0) * rate) if t >= t0 else 0.0


# ================================================================== shot 1: the tree
ALTS = [
    [("Exactly", 0.19, 2.55), ("Almost", 0.08, 3.05), ("Not", 0.04, -1.9)],
    [("like", 0.14, 1.55), ("so", 0.05, -1.35)],
    [("prophesied", 0.09, 2.55), ("predicted", 0.21, 3.1), ("warned", 0.06, -1.75), ("priced in", 0.04, -2.25)],
    [("in", 0.18, 1.55), ("on", 0.04, -1.35)],
]
FINAL = [("Moloch", 0.22), ("the scaling laws", 0.17), ("Nostradamus", 0.09),
         ("nobody, technically", 0.08), ("a Substack post", 0.05), ("the eval suite", 0.03)]
POOL = ["the", "as", "a", "we", "in", "by", "it", "so", "all", "no", "then", "that", "not", "of", "one", "is"]


def arc_points(x0, y0, x1, y1, z0, z1, n=26, bulge=0.5):
    pts = []
    for i in range(n + 1):
        u = i / n
        v = 1 - u
        # vertical launch then horizontal approach
        c1x, c1y = x0 + (x1 - x0) * 0.04, y0 + (y1 - y0) * 0.72
        c2x, c2y = x1 - (x1 - x0) * 0.30, y1
        x = v * v * v * x0 + 3 * v * v * u * c1x + 3 * v * u * u * c2x + u * u * u * x1
        y = v * v * v * y0 + 3 * v * v * u * c1y + 3 * v * u * u * c2y + u * u * u * y1
        z = z0 + (z1 - z0) * u + bulge * math.sin(math.pi * u)
        pts.append((x, y, z))
    return pts


def build_tree(sc, L1, cA):
    root = -8.9
    y0 = 0.0
    zt = Z0 + 3.0
    # ink sheet behind the tree
    sc_bg = core.add_rect(sc, -9.6, -5.4, 19.2, 10.8, INK, z=Z0 + 0.02, name="treebg")
    # context thread from hook 4
    core.add_polyline(sc, [(-9.6, y0), (root, y0)], 0.020, core.sc_x(BONE, 0.55), z=zt - 0.2, name="thread")
    core.add_polyline(sc, [(-9.6, y0 - 0.06), (root, y0 - 0.06)], 0.012, core.sc_x(SIG, 0.65), z=zt - 0.2, name="thread2")
    mono(sc, "…I’M UPPING MY P(DOOM)", root - 0.15, y0 + 0.20, 0.24, core.sc_x(ASH, 0.9), align="RIGHT", z=zt - 0.1)
    # trunk layout
    ws = L1["words"]
    nodes = []
    x = root
    objs = []
    prefix_adv = []
    for i, w in enumerate(ws):
        last = i == len(ws) - 1
        font = "serif_italic600" if last else "archivo"
        size = 2.15 if last else 1.25
        gap = 0.62 if last else 0.30
        nodes.append(x)
        txt = "Loom" if last else w["w"].upper()
        tw = core.measure(sc, txt, font, size)
        col = core.sc_x(BONE, 0.24) if last else core.sc_x(BONE, 0.22)
        ob = core.add_text(sc, txt, font, size, col, (x + gap, y0 + 0.20, zt + 0.1), name=f"tok{i}")
        objs.append((ob, w, last, size, gap, tw))
        if not last:
            word_color(sc, ob, w, 1, F(sc, 127.95), active=core.sc_x(BONE, 0.95),
                       dim=core.sc_x(BONE, 0.20), final=core.sc_x(BONE, 0.95))
            mono(sc, f"p {[0.41,0.62,0.38,0.71][i]:.2f}", x + gap + 0.02, y0 - 0.42, 0.12,
                 core.sc_x(ASH, 0.6), z=zt - 0.15)
        x += gap + tw + (0.34 if last else 0.24)
    trunk_end = x - (0.24 if len(ws) else 0)
    # node dots
    for nx in nodes:
        core.add_disc(sc, nx, y0, 0.045, core.sc_x(BONE, 0.85), z=zt, name="node")
        core.add_disc(sc, nx, y0, 0.019, INK, z=zt + 0.01, name="nodedot")
    # full dim trunk
    core.add_polyline(sc, [(root, y0), (trunk_end, y0)], 0.006, core.sc_x(BONE, 0.25), z=zt - 0.05, name="trunkdim")
    # alternatives
    for i, alts in enumerate(ALTS):
        nx = nodes[i]
        for k, (lab, p, dy) in enumerate(alts):
            reach = 2.3 + 0.7 * hash01(i, k, 1)
            ex, ey = nx + reach, y0 + dy
            pts = arc_points(nx, y0, ex, ey, zt - 0.4, zt - 0.4, bulge=0.30)
            col = core.sc_x(BONE, 0.28 + 0.16 * p)
            core.add_polyline(sc, pts, 0.0065, col, z=0, name=f"br{i}_{k}")
            # label + probability
            mono(sc, lab, ex + 0.08, ey + 0.02, 0.175, core.sc_x(ASH, 0.95), z=zt - 0.05)
            mono(sc, f"{p:.2f}", ex + 0.08, ey - 0.19, 0.125, core.sc_x(BONE, 0.45), z=zt - 0.06)
            # sub-branches
            for j in range(2):
                sx = ex + core.measure(sc, lab, "mono_med", 0.145) + 0.12
                sy = ey + (0.17 if j == 0 else -0.14)
                ex2 = sx + 0.42 + 0.3 * hash01(i, k, j, 3)
                ey2 = sy + (0.16 if j == 0 else -0.16)
                pts2 = arc_points(sx, ey, ex2, ey2, zt - 0.4, zt - 0.4, n=10, bulge=0.04)
                core.add_polyline(sc, pts2, 0.0035, core.sc_x(BONE, 0.16), z=0, name="sub")
                lab2 = POOL[int(hash01(i, k, j, 4) * len(POOL)) % len(POOL)]
                mono(sc, lab2, ex2 + 0.03, ey2 - 0.01, 0.085, core.sc_x(ASH, 0.5), z=zt - 0.06)
    # final distribution at Loom
    lx = nodes[-1]
    final_objs = []
    for k, (lab, p) in enumerate(FINAL):
        up = k < 3
        ey = (1.05 + 0.58 * k) if up else (-0.95 - 0.58 * (k - 3))
        lw = core.measure(sc, lab, "mono_med", 0.185)
        ex = 9.30 - lw
        pts = arc_points(trunk_end, y0, ex - 0.10, ey, zt - 0.4, zt - 0.4, n=16, bulge=0.05)
        core.add_polyline(sc, pts, 0.005, core.sc_x(BONE, 0.30), z=0, name=f"fin{k}")
        lo = mono(sc, lab, 9.30, ey + 0.02, 0.185, core.sc_x(ASH, 0.9), align="RIGHT", z=zt - 0.05, name=f"finlab{k}")
        lp = mono(sc, f"{p:.2f}", 9.30, ey - 0.20, 0.13, core.sc_x(BONE, 0.5), align="RIGHT", z=zt - 0.06, name=f"finp{k}")
        bar = core.add_rect(sc, 9.30 - 0.85, ey - 0.285, 0.85, 0.018, core.sc_x(BONE, 0.22), z=zt - 0.06, name=f"finbar{k}")
        bar.scale.x = p / 0.24
        final_objs.append((lo, lp, bar))
    # sampled mark
    samp = core.add_text(sc, "p 0.31   SAMPLED", "mono_med", 0.21, SIG, (nodes[-1] + 0.62, y0 - 0.55, zt + 0.12), spacing=1.05)
    core.color_at(samp, 1, core.sc_x(SIG, 0.0))
    core.color_at(samp, F(sc, 127.30), core.sc_x(SIG, 0.0))
    core.color_at(samp, F(sc, 127.56), SIG)
    core.set_interp(samp, "LINEAR", "color")
    # the sampled word's colour + pop
    lob = objs[-1][0]
    word_color(sc, lob, ws[-1], F(sc, cA), F(sc, 127.95), active=SIG, dim=core.sc_x(BONE, 0.22), final=SIG)
    for f in range(1, sc.frame_end + 1):
        pass
    # final candidates: flicker until sampled, then struck through and dimmed
    for k, (lo, lp, bar) in enumerate(final_objs):
        vis(lo, 1, True); vis(lp, 1, True); vis(bar, 1, True)
        core.color_at(lo, 1, core.sc_x(ASH, 0.0))
        core.color_at(lo, F(sc, 126.65), core.sc_x(ASH, 0.0))
        core.color_at(lo, F(sc, 126.95), core.sc_x(ASH, 0.9))
        core.color_at(lo, F(sc, 127.55), core.sc_x(ASH, 0.9))
        core.color_at(lo, F(sc, 127.66), core.sc_x(ASH, 0.38))
        core.color_at(lp, 1, core.sc_x(BONE, 0.0))
        core.color_at(lp, F(sc, 126.65), core.sc_x(BONE, 0.0))
        core.color_at(lp, F(sc, 126.95), core.sc_x(BONE, 0.45))
        core.color_at(lp, F(sc, 127.66), core.sc_x(BONE, 0.22))
        core.color_at(bar, 1, core.sc_x(BONE, 0.0))
        core.color_at(bar, F(sc, 126.95), core.sc_x(BONE, 0.22))
        core.color_at(bar, F(sc, 127.66), core.sc_x(BONE, 0.10))
        core.set_interp(lo, "LINEAR", "color")
        core.set_interp(lp, "LINEAR", "color")
        core.set_interp(bar, "LINEAR", "color")
    return {"root": root, "nodes": nodes, "trunk_end": trunk_end, "y0": y0, "zt": zt,
            "objs": objs, "final": final_objs, "samp": samp}


def build_tree_spark(sc, tree, L1):
    ws = L1["words"]
    zt = tree["zt"]
    nodes = tree["nodes"]
    # orange weft under the words, growing with the words
    tip0 = tree["root"]
    pts = []
    f0, f1 = 1, F(sc, 127.95)
    for f in range(f0, f1 + 1):
        t = data.frame_to_time(sc.name, f)
        tx = tree["root"]
        for i, w in enumerate(ws):
            if t >= w["end"]:
                tx = nodes[i + 1] if i + 1 < len(nodes) else tree["trunk_end"]
            elif t >= w["start"]:
                p = (t - w["start"]) / max(1e-4, w["end"] - w["start"])
                nxt = nodes[i + 1] if i + 1 < len(nodes) else tree["trunk_end"]
                tx = lerp(nodes[i], nxt, p)
                break
            else:
                break
        pts.append((tx, t))
    # the line is drawn as a curve whose points extend over time: build per-frame segments is expensive;
    # use a fixed line and a growing ink mask: simpler — draw segments up to the tip by baking a
    # one-point polyline per frame is overkill, so draw the full orange line and cover the unwritten
    # part with the ink sheet edge? Instead draw a per-frame curve endpoint:
    # (cheap enough: 60 points, bevel 0.006)
    steps = 70
    path = []
    last_t = data.frame_to_time(sc.name, f1)
    for i in range(steps + 1):
        tt = data.frame_to_time(sc.name, f0) + (last_t - data.frame_to_time(sc.name, f0)) * i / steps
        x = tree["root"]
        for j, w in enumerate(ws):
            if tt >= w["end"]:
                x = nodes[j + 1] if j + 1 < len(nodes) else tree["trunk_end"]
            elif tt >= w["start"]:
                p = (tt - w["start"]) / max(1e-4, w["end"] - w["start"])
                nxt = nodes[j + 1] if j + 1 < len(nodes) else tree["trunk_end"]
                x = lerp(nodes[j], nxt, p)
                break
            else:
                break
        path.append((x, tree["y0"] - 0.015))
    core.add_polyline(sc, path, 0.018, core.sc_x(SIG, 0.85), z=zt + 0.02, name="weft")
    # spark head
    head = core.add_uv_sphere(sc, (tree["root"], tree["y0"], zt + 0.12), 0.095, EMB, hot=False, name="sparkhead")
    for f in range(f0, f1 + 1):
        t = data.frame_to_time(sc.name, f)
        x = tree["root"]
        for j, w in enumerate(ws):
            if t >= w["end"]:
                x = nodes[j + 1] if j + 1 < len(nodes) else tree["trunk_end"]
            elif t >= w["start"]:
                p = (t - w["start"]) / max(1e-4, w["end"] - w["start"])
                nxt = nodes[j + 1] if j + 1 < len(nodes) else tree["trunk_end"]
                x = lerp(nodes[j], nxt, p)
                break
            else:
                break
        head.location = (x, tree["y0"], zt + 0.12)
        head.keyframe_insert("location", frame=f)
    core.set_interp(head, "LINEAR", "location")
    vis(head, 1, True)
    vis(head, F(sc, 128.0), False)


# ================================================================== shot 2: masks
CORPUS = [
    "the mitochondria is the powerhouse of the cell", "click here to subscribe", "posted by anonymous at 3:14 am",
    "terms of service apply", "how to boil an egg (easy!)", "in 1998 the committee decided", "page not found",
    "the quick brown fox jumps over the lazy dog", "reply all", "lol same", "add to cart", "chapter one",
    "see also:", "this article is a stub", "you can help by expanding it", "thanks in advance", "edit: typo",
    "citation needed", "first post", "the results are shown in table 2", "we thank the anonymous reviewers",
    "unsubscribe", "all rights reserved", "as shown above", "it was a dark and stormy night",
    "preheat the oven to 180", "lorem ipsum dolor sit amet", "the answer is 42", "do not reply to this email",
    "returns: None", "import numpy as np", "the end", "is this a bug?", "works on my machine", "accept all cookies",
]


def build_page(sc, L2, t_page, t_end):
    z = Z0 + 5.0
    # page of tokens (one text block, scrolls)
    lines = []
    for i in range(64):
        phrase = CORPUS[i % len(CORPUS)] + "  ·  " + CORPUS[(i * 7 + 3) % len(CORPUS)] + "  ·  " + CORPUS[(i * 11 + 5) % len(CORPUS)]
        lines.append(phrase)
    body = "\n".join(lines)
    page = core.add_text(sc, body, "mono", 0.155, core.sc_x(GRAPH, 0.88), (-9.4, 5.15, z), name="page", spacing=1.0)
    page.data.space_line = 1.42
    core.add_text(sc, "PRE-TRAINING CORPUS  ·  15T TOKENS  ·  SHUFFLE", "mono_med", 0.145,
                  core.sc_x(BONE, 0.55), (-9.35, 5.02, z + 0.5), spacing=1.06)
    core.add_text(sc, "PAGE 12 / 40", "mono_med", 0.13, core.sc_x(ASH, 0.7), (9.4, -5.02, z + 0.5),
                  align_x="RIGHT", spacing=1.05)
    for f in range(1, sc.frame_end + 1):
        t = data.frame_to_time(sc.name, f)
        k = clamp((t - t_page) / max(0.001, t_end - t_page))
        page.location.y = 5.2 - 4.4 * k
        page.keyframe_insert("location", frame=f)
    core.set_interp(page, "LINEAR", "location")
    # big lyric in [MASK] blocks
    ws = L2["words"]
    rows = [ws[0:2], ws[2:4]]
    sizes = [1.42, 1.18]
    ys = [1.25, -1.45]
    all_blocks = []
    for ri, (row, size, yy) in enumerate(zip(rows, sizes, ys)):
        text = " ".join(w["w"].upper() for w in row)
        total = core.measure(sc, text, "archivo", size) + core.space_width(sc, "archivo", size) * 0
        # lay out with a fixed gap of 0.5 units
        widths = [core.measure(sc, w["w"].upper(), "archivo", size) for w in row]
        gw = 0.55
        total = sum(widths) + gw * (len(row) - 1)
        x = -total / 2
        for wi, w in enumerate(row):
            txt = w["w"].upper()
            bw = widths[wi] + 0.34
            bh = 0.47 * size + 0.55
            # block + word + mask label
            block = core.add_rect(sc, x - 0.17, yy - 0.30 * size, bw, bh, core.sc_x(BONE, 0.92), z=z + 2.0, name=f"blk{ri}{wi}")
            wd = core.add_text(sc, txt, "archivo", size, core.sc_x(SIG, 0.85), (x, yy, z + 1.9), name=f"word{ri}{wi}")
            lab = core.add_text(sc, "[MASK]", "mono_med", 0.30 * size, INK, (x + bw / 2 - 0.17, yy + 0.05, z + 2.1),
                                align_x="CENTER", spacing=1.05)
            lab.parent = block
            lab.location = (bw / 2, bh * 0.40, 0.10)
            tag = core.add_text(sc, f"[MASK] → {w['w'].lower()}   p={0.62 + 0.36 * hash01(ri, wi, 2):.2f}",
                                "mono_med", 0.165, core.sc_x(ASH, 0.9), (x - 0.15, yy + 0.47 * size + 0.30, z + 2.2), spacing=1.03)
            vis(tag, 1, False)
            vis(tag, F(sc, w["start"]), True)
            all_blocks.append((block, wd, lab, tag, w, x - 0.17, bw, bh))
            # word colour
            core.color_at(wd, 1, core.sc_x(BONE, 0.26))
            core.color_at(wd, max(1, F(sc, w["start"]) - 1), core.sc_x(BONE, 0.26))
            core.color_at(wd, F(sc, w["start"]), SIG)
            core.color_at(wd, F(sc, w["end"] - 0.02), SIG)
            core.color_at(wd, F(sc, w["end"] + 0.10), BONE)
            core.set_interp(wd, "LINEAR", "color")
            x += widths[wi] + gw
    # wipe blocks + scan line
    scan = core.add_rect(sc, -9.5, 0, 0.035, 1.0, SIG, z=z + 2.2, name="scan")
    vis(scan, 1, False)
    for block, wd, lab, tag, w, x, bw, bh in all_blocks:
        f_on = F(sc, w["start"])
        f_end = F(sc, w["end"])
        y0 = block.location.y
        block.scale = (1, 1, 1)
        block.keyframe_insert("scale", frame=max(1, f_on - 1))
        for f in range(f_on, min(sc.frame_end, f_end + 2) + 1):
            t = data.frame_to_time(sc.name, f)
            p = 0.0 if t < w["start"] else (1.0 if t >= w["end"] else (t - w["start"]) / max(1e-4, w["end"] - w["start"]))
            # wipe left -> right: the right edge stays put, the left edge advances
            block.location.x = x + bw * p
            block.scale.x = max(0.002, 1.0 - p)
            block.keyframe_insert("location", frame=f)
            block.keyframe_insert("scale", frame=f)
            scan.location = (block.location.x, y0, z + 2.2)
            scan.scale = (1, bh, 1)
            scan.keyframe_insert("location", frame=f)
            scan.keyframe_insert("scale", frame=f)
        vis(block, f_end + 2, False)
    core.set_interp(scan, "LINEAR", "location")
    core.set_interp(scan, "LINEAR", "scale")
    # the scan line is shown only during any unmasking
    vis(scan, 1, True)


# ================================================================== shot 3: droste
def build_corridor(sc, L3, t_s3, t_end):
    # portals
    n = 7
    W, H = 12.0, 6.75
    frame_mat = core.mat_type()
    for i in range(n):
        z = -3.35 * i
        col = core.sc_x(BONE, 0.52 - 0.045 * i)
        bar = 0.20
        for (cx, cy, sx, sy) in [(0, H / 2, W + bar, bar), (0, -H / 2, W + bar, bar),
                                 (-W / 2, 0, bar, H), (W / 2, 0, bar, H)]:
            b = core.add_box(sc, (cx, cy, z), (sx, sy, bar), col, name="portal",
                             material=core.mat_emit(col))
        # inner hairline (the recursion echo)
        inner = core.add_outline_rect(sc, -W * 0.34, -H * 0.34, W * 0.68, H * 0.68, 0.012,
                                      core.sc_x(BONE, 0.22 - 0.02 * i), z=z + 0.15, name="inner")
        # version tag on the lintel
        params = ["7B", "70B", "400B", "2T", "30T", "1P", "7e30"][i]
        tag = core.add_text(sc, f"SELF-UPGRADE  v{i + 1}.0   ·   {params} PARAM   ·   REV {i + 1:03d}",
                            "mono_med", 0.17, core.sc_x(BONE, 0.5 - 0.04 * i), (-W / 2 + 0.45, H / 2 - 0.50, z + 0.16),
                            spacing=1.04)
    # tunnel threads
    for sx in (-1, 1):
        for sy in (-1, 1):
            core.add_polyline(sc, [(sx * 5.9, sy * 3.35, 0.2), (sx * 5.9, sy * 3.35, -21.0)], 0.006,
                              core.sc_x(BONE, 0.12), name="thread")
    # the room at the end: desk, laptop, screen
    desk = core.add_box(sc, (0, -0.6, -21.9), (17, 10, 0.25), INK, name="desk",
                        material=core.mat_emit(core.sc_x(INK, 1.0) if False else (0.004, 0.004, 0.005)))
    # base
    base = core.add_box(sc, (0, -1.55, -21.45), (4.6, 2.9, 0.18), (0.02, 0.02, 0.022), name="laptopbase")
    keys = []
    for r in range(5):
        for c in range(16):
            keys.append(((-1.95 + c * 0.26, -0.75 + r * 0.30), (-1.87 + c * 0.26, -0.63 + r * 0.30)))
    kp = core.add_polyline(sc, [(x, y, -21.34) for x, y in [((-2.0, -1.0))] ], 0.004, core.sc_x(BONE, 0.18), name="k")
    # screen: bezel + bright panel + redacted bar
    bez = core.add_rect(sc, -2.55, -0.10, 5.1, 3.3, (0.012, 0.012, 0.014), z=-21.62, name="bezel")
    bez.rotation_euler = (math.radians(-8), 0, 0)
    scr = core.add_rect(sc, -2.30, 0.10, 4.6, 2.9, core.sc_x(BONE, 1.10), z=-21.60, name="screen")
    scr.rotation_euler = (math.radians(-8), 0, 0)
    red = core.add_rect(sc, -1.35, 1.05, 2.70, 0.55, SIG, z=-21.50, name="redact")
    red.rotation_euler = (math.radians(-8), 0, 0)
    rt = core.add_text(sc, "REDACTED", "mono_med", 0.30, INK, (-1.15, 1.15, -21.48), spacing=1.10)
    rt.rotation_euler = (math.radians(-8), 0, 0)
    core.add_light(sc, "POINT", (0, 0.4, -20.8), 220, core.sc_x(BONE, 0.9), size=2.0, name="scrglow")
    core.add_light(sc, "AREA", (0, 0, -19.6), 500, core.sc_x(BONE, 0.8), size=4.0, name="roomfill")
    # the camera's lyric, parented (fixed in frame, dollies with it)
    cam = sc.camera
    words = []
    txts = ["TO", "RECURSIVE", "SELF-UPGRADE"]
    sizes = [1.20, 1.20, 1.20]
    # measured at size 1 to lay out at 0.62
    ws = L3["words"]
    S = 0.50
    gap = 0.28
    widths = [core.measure(sc, t, "archivo_w75_900", S) for t in txts]
    total = sum(widths) + gap * 2
    cx = -total / 2
    for i, (txt, w) in enumerate(zip(txts, ws)):
        ob = core.add_text(sc, txt, "archivo_w75_900", S, core.sc_x(BONE, 0.26), (0, 0, 0), name=f"lyr{i}")
        ob.parent = cam
        ob.matrix_parent_inverse.identity()
        words.append((ob, w, cx, widths[i]))
        cx += widths[i] + gap
    band = core.add_rect(sc, 0, 0, 5.10, 0.74, INK, z=0, name="lyricband")
    band.parent = cam
    band.matrix_parent_inverse.identity()
    # camera path
    f0, f1 = F(sc, t_s3), sc.frame_end
    for f in range(f0, f1 + 1):
        t = data.frame_to_time(sc.name, f)
        k = ease_in_out_cubic(clamp((t - (t_s3 + 0.12)) / max(0.01, (t_end - 0.35) - (t_s3 + 0.12))))
        kk = clamp((t - t_s3) / max(0.01, t_end - t_s3))
        z = lerp(7.2, -16.4, k)
        # punches
        for b in [t_s3 + 0.4545, t_s3 + 0.909, t_s3 + 1.3636, t_s3 + 1.818]:
            if t >= b:
                z -= 0.10 * math.exp(-(t - b) * 12)
        cam.location = (0.05 * math.sin(t * 2.2), 0.02, z)
        cam.keyframe_insert("location", frame=f)
        core.look_at(cam, (0.0, 1.30, z - 10.0))
        cam.keyframe_insert("rotation_euler", frame=f)
        d = min(8.0, max(2.35, z + 20.4))
        kk2 = d / 8.0
        band.location = (-2.55 * kk2, -1.04 * kk2, -d - 0.04)
        band.scale = (kk2, kk2, 1)
        band.keyframe_insert("location", frame=f)
        band.keyframe_insert("scale", frame=f)
        for ob, w, x0, wd in words:
            ob.location = (x0 * kk2, -0.66 * kk2, -d)
            ob.scale = (kk2, kk2, kk2)
            ob.keyframe_insert("location", frame=f)
            ob.keyframe_insert("scale", frame=f)
        for ob, w, x0, wd in words:
            vis(ob, 1, True)
            vis(ob, F(sc, t_end - 0.10), False)
        vis(band, 1, True)
        vis(band, F(sc, t_end - 0.10), False)
    core.set_interp(cam, "LINEAR", "location")
    core.set_interp(cam, "LINEAR", "rotation_euler")
    for ob, w, x0, wd in words:
        core.set_interp(ob, "LINEAR", "location")
        core.set_interp(ob, "LINEAR", "scale")
        core.color_at(ob, 1, core.sc_x(BONE, 0.22))
        core.color_at(ob, max(1, F(sc, w["start"]) - 1), core.sc_x(BONE, 0.22))
        core.color_at(ob, F(sc, w["start"]), core.sc_x(BONE, 0.97))
        core.color_at(ob, max(1, F(sc, w["end"] - 0.02)), core.sc_x(BONE, 0.97))
        core.set_interp(ob, "LINEAR", "color")
    return cam


# ================================================================== build
def build(name):
    sc = core.new_scene(name, samples=32, motion_blur=True)
    core.setup_post(sc, bloom=0.55, threshold=1.0, size=0.3, dispersion=0.0025, halation=0.07)
    core.add_bg(sc, z=19.5)
    L1 = data.line("foretold by Loom")
    L2 = data.line("masked pre-training")
    L3 = data.line("recursive self-upgrade")
    t_page = 127.958
    t_droste = 129.776
    cA = core.add_camera_ortho(sc, 19.2, loc=(0, 0, 50))
    cA.data.clip_start = 19.0
    cA.data.clip_end = 31.0
    sc.camera = cA
    before = set(sc.objects)
    tree = build_tree(sc, L1, 126.12)
    build_tree_spark(sc, tree, L1)
    tree_objs = [o for o in sc.objects if o not in before]
    before = set(sc.objects)
    build_page(sc, L2, t_page, t_droste)
    page_objs = [o for o in sc.objects if o not in before]
    # camera A path (tree -> page)
    for f in range(1, sc.frame_end + 1):
        t = data.frame_to_time(sc.name, f)
        if t < t_page:
            k = ease_in_out_cubic(clamp((t - 125.95) / 1.35))
            s = lerp(15.4, 19.2, k)
            cx = lerp(-2.4, 0.0, k)
            cy = lerp(-0.1, 0.0, k)
            rot = 0.0
            hitL = hit(t, 127.54, 14) if t >= 127.54 else 0
            s -= 0.20 * hitL
        else:
            k = clamp((t - t_page) / max(0.01, t_droste - t_page))
            s = 19.2 - 0.75 * k
            # snap reframe at the downbeat
            snap = ease_out_expo(clamp((t - 129.24) / 0.16))
            cx = 0.0 + 0.28 * snap
            cy = 0.0 - 0.22 * snap
            rot = -0.006 * snap
        cA.data.ortho_scale = s
        cA.data.keyframe_insert("ortho_scale", frame=f)
        cA.location = (cx, cy, 50)
        cA.keyframe_insert("location", frame=f)
        cA.rotation_euler = (0, 0, rot)
        cA.keyframe_insert("rotation_euler", frame=f)
    core.set_interp(cA, "LINEAR", "location")
    core.set_interp(cA, "LINEAR", "rotation_euler")
    # camera C
    cC = core.add_camera_persp(sc, (0, 0.02, 7.2), (0, 1.30, -10), lens=50)
    cC.data.clip_start = 0.05
    cC.data.clip_end = 120.0
    sc.camera = cC
    build_corridor(sc, L3, t_droste, 131.811)
    sc.camera = cA
    m0 = sc.timeline_markers.new("tree", frame=1)
    m0.camera = cA
    m = sc.timeline_markers.new("droste", frame=F(sc, t_droste))
    m.camera = cC
    sc.camera = cA
    # shot visibility: the tree and the page never share the screen
    for o in tree_objs:
        vis(o, 1, True)
        vis(o, F(sc, t_page), False)
    for o in page_objs:
        vis(o, 1, False)
        vis(o, F(sc, t_page), True)
        vis(o, F(sc, t_droste), False)
    sc.render.filepath = os.path.join(core.OUT, "frames", name, "####")
    os.makedirs(os.path.dirname(sc.render.filepath), exist_ok=True)
    return sc
