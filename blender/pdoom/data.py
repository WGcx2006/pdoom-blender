"""Timeline, lyric and audio data for the Blender rebuild of pdoom-video."""
import json, os, math

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "pdoom-video", "data")
AUDIO = os.path.join(ROOT, "pdoom-video", "audio", "pdoom.mp3")
FPS = 30
W, H = 1920, 1080

with open(os.path.join(DATA, "lyrics.json"), encoding="utf-8") as f:
    _LY = json.load(f)
with open(os.path.join(DATA, "audio.json"), encoding="utf-8") as f:
    _AU = json.load(f)

LINES = _LY["lines"]
AUD = _AU
BEATS = _AU["beats"]
DOWNBEATS = _AU["downbeats"]
SECTIONS = _AU["sections"]
DURATION = _AU["duration"]
BEAT_PERIOD = _AU["beat_period"]

# Scene windows in seconds (same edit as pdoom-video/app/src/timeline.ts, recomputed from the data).
_SCENES = [
    ("open", 0.000, 9.090),
    ("loss", 9.090, 16.363),
    ("prompt1", 16.363, 22.726),
    ("hook1", 22.726, 24.090),
    ("room", 24.090, 29.544),
    ("shoggoth", 29.544, 38.634),
    ("spacetime", 38.634, 52.724),
    ("prompt2", 52.724, 59.088),
    ("hook2", 59.088, 60.451),
    ("ascent", 60.451, 69.542),
    ("bureau", 69.542, 80.905),
    ("leftturn", 80.905, 89.086),
    ("prompt3", 89.086, 95.449),
    ("hook3", 95.449, 96.813),
    ("paperclips", 96.813, 102.267),
    ("fuse", 102.267, 109.994),
    ("stack", 109.994, 114.994),
    ("dense", 114.994, 124.538),
    ("hook4", 124.538, 125.902),
    ("loom", 125.902, 131.811),
    ("ilya", 131.811, 140.230),
    ("outro", 140.230, 156.651),
]
SCENES = {n: {"name": n, "start": s, "end": e, "frames": int(round((e - s) * FPS))} for n, s, e in _SCENES}
SCENE_ORDER = [n for n, _, _ in _SCENES]


def scene(name):
    return SCENES[name]


def frame_to_time(scene_name, frame):
    s = SCENES[scene_name]
    return s["start"] + (frame - 1) / FPS


def time_to_frame(scene_name, t):
    s = SCENES[scene_name]
    return int(round((t - s["start"]) * FPS)) + 1


def _smart_match(text, q):
    return q.lower() in text.lower()


def line(q, nth=0):
    """Find a lyric line by substring (like the original's lyrics.get)."""
    hits = [l for l in LINES if _smart_match(l["text"], q)]
    if not hits:
        raise KeyError(q)
    return hits[nth]


def word(q, nth_word=0, nth=0):
    return line(q, nth)["words"][nth_word]


def words(q, nth=0):
    return line(q, nth)["words"]


def word_start(q, nth_word=0, nth=0):
    return word(q, nth_word, nth)["start"]


def find_words(sub):
    out = []
    for l in LINES:
        for w in l["words"]:
            if _smart_match(w["w"], sub):
                out.append(w)
    return out


def word_progress(w, t):
    if t <= w["start"]:
        return 0.0
    if t >= w["end"]:
        return 1.0
    return (t - w["start"]) / max(1e-4, w["end"] - w["start"])


def time_of_beat(i):
    return i * BEAT_PERIOD


def beat_at(t):
    return t / BEAT_PERIOD


def nearest_beat(t):
    return round(beat_at(t)) * BEAT_PERIOD


def beats_between(t0, t1):
    i0 = math.ceil(beat_at(t0) - 1e-6)
    i1 = math.floor(beat_at(t1) + 1e-6)
    return [time_of_beat(i) for i in range(i0, i1 + 1)]


def downbeats_between(t0, t1):
    return [b for b in DOWNBEATS if t0 - 1e-6 <= b <= t1 + 1e-6]


def section_at(t):
    for s in SECTIONS:
        if s["start"] <= t < s["end"]:
            return s
    return {"name": "end", "start": DURATION, "end": DURATION}


def env(name, t):
    """Loudness/band envelope 0..1 at time t (100 fps data)."""
    arr = AUD.get(name)
    if not arr:
        return 0.0
    i = int(round(t * 100))
    if i < 0:
        return 0.0
    if i >= len(arr):
        return 0.0
    return float(arr[i])


def hit(kind, t, half_life=0.06):
    """Decaying pulse after the nearest onset of a kind."""
    best = 0.0
    for ot, strength in AUD["onsets"].get(kind, []):
        if ot <= t and t - ot < half_life * 8:
            best = max(best, strength * (0.5 ** ((t - ot) / half_life)))
    return best


# P(doom) value, ported from the original's hud.ts.
_PDOOM_STEPS = None


def _pdoom_steps():
    global _PDOOM_STEPS
    if _PDOOM_STEPS is None:
        hits = [w["start"] + 0.06 for w in find_words("P(doom)")]
        vals = [0.15, 0.42, 0.81, 0.99]
        steps = [(-1.0, 0.02)]
        for i, t in enumerate(hits):
            steps.append((t, vals[i] if i < len(vals) else 0.99))
        _PDOOM_STEPS = steps
    return _PDOOM_STEPS


def _ease_out_expo(x):
    return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)


def _smoothstep(a, b, x):
    if b <= a:
        return 1.0 if x >= b else 0.0
    k = max(0.0, min(1.0, (x - a) / (b - a)))
    return k * k * (3 - 2 * k)


def pdoom(t):
    steps = _pdoom_steps()
    i = 0
    while i + 1 < len(steps) and steps[i + 1][0] <= t:
        i += 1
    ct, cv = steps[i]
    pt, pv = steps[max(0, i - 1)]
    k = 1.0 if i == 0 else _ease_out_expo(max(0.0, min(1.0, (t - ct) / 0.9)))
    base = pv + (cv - pv) * k
    if i + 1 < len(steps):
        nt, nv = steps[i + 1]
        base += (nv - cv) * 0.2 * _smoothstep(ct + 1.0, nt, t)
    return max(0.0, min(1.0, base))


def pdoom_text(t):
    v = pdoom(t)
    return f"{v:.3f}" if v >= 0.99 else f"{v:.2f}"
