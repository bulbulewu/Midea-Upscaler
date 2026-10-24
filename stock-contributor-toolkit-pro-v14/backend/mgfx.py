"""
Motion Graphics Pack v6 — MotionHero-standard rebuild.

What changed vs v5 (see CHANGELOG.md):
  * The uploaded artwork itself animates (new "Image to Motion" category).
  * Bundled OFL fonts (Montserrat / Playfair Display / Poppins) — Windows
    no longer falls back to Pillow's tiny bitmap font.
  * Easing library + keyframe helper with staggered entrances.
  * Supersampled rendering (anti-aliasing), glow sprites, real gradients,
    resolution-scaled element counts/sizes.
  * Seamless loops by construction: every periodic motion completes an
    integer number of cycles; speed quantises cycle counts so loops stay
    seamless at any speed.
  * 60 FPS, MOV export, ffprobe stock-compliance check in the result.

Free and local: Pillow + NumPy + FFmpeg only. No watermark.
"""

import colorsys
import math
import os
import random
import shutil
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

RESOLUTIONS = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080), "4:5": (1080, 1350)}
RESOLUTIONS_4K = {"16:9": (3840, 2160), "9:16": (2160, 3840), "1:1": (2160, 2160), "4:5": (2160, 2700)}
RESOLUTIONS_PREVIEW = {"16:9": (854, 480), "9:16": (480, 854), "1:1": (480, 480), "4:5": (480, 600)}

THEMES = {  # name -> (background, colour A, colour B)
    "gold": ((16, 14, 8), (240, 192, 90), (255, 236, 190)),
    "teal": ((4, 20, 22), (32, 201, 190), (170, 255, 240)),
    "violet": ((14, 8, 28), (150, 90, 255), (230, 200, 255)),
    "crimson": ((24, 6, 10), (235, 60, 80), (255, 190, 190)),
    "ocean": ((4, 14, 30), (50, 130, 246), (170, 215, 255)),
    "rose": ((26, 8, 16), (250, 110, 160), (255, 205, 225)),
}

CATALOG = {
    "bg-gradient": {"label": "Aurora Gradient (loop)", "category": "Backgrounds"},
    "bg-particles": {"label": "Golden Particles (loop)", "category": "Backgrounds"},
    "bg-bokeh": {"label": "Bokeh Dreams (loop)", "category": "Backgrounds"},
    "bg-waves": {"label": "Wave Layers (loop)", "category": "Backgrounds"},
    "bg-confetti": {"label": "Confetti Celebration (loop)", "category": "Backgrounds"},
    "bg-geometric": {"label": "Geometric Pulse (loop)", "category": "Backgrounds"},
    "bg-light-trails": {"label": "Neon Light Trails (loop)", "category": "Backgrounds"},
    "bg-hexwave": {"label": "Hexagon Wave (loop)", "category": "Backgrounds"},
    "bg-equalizer": {"label": "Audio Visualizer / Equalizer (loop)", "category": "Backgrounds"},
    "bg-vortex": {"label": "Galaxy Vortex (loop)", "category": "Backgrounds"},
    "bg-burst": {"label": "Comic Burst / Sunburst (loop)", "category": "Backgrounds"},
    "greeting-card": {"label": "Greeting Card (Birthday / Festival)", "category": "Backgrounds"},
    "title-cinematic": {"label": "Cinematic Title", "category": "Titles"},
    "title-bold": {"label": "Bold Modern Title", "category": "Titles"},
    "lower-third": {"label": "Lower Third (name / role bar)", "category": "Titles"},
    "logo-reveal": {"label": "Logo Reveal", "category": "Intros & Logos"},
    "intro-sting": {"label": "Intro Sting", "category": "Intros & Logos"},
    "countdown": {"label": "Countdown 5 → 1", "category": "Intros & Logos"},
    "overlay-leak": {"label": "Light Leak (overlay)", "category": "Overlays"},
    "overlay-grain": {"label": "Film Grain (overlay)", "category": "Overlays"},
    "overlay-sparkle": {"label": "Sparkles (overlay)", "category": "Overlays"},
    "img-breathing": {"label": "Breathing Loop ★ Image to Motion", "category": "Image to Motion"},
    "img-orbit": {"label": "Particle Orbit ★ Image to Motion", "category": "Image to Motion"},
    "img-sweep": {"label": "Light Sweep Reveal ★ Image to Motion", "category": "Image to Motion"},
    "img-parallax": {"label": "Parallax Float ★ Image to Motion", "category": "Image to Motion"},
    "img-kenburns": {"label": "Ken Burns Photo ★ Image to Motion", "category": "Image to Motion"},
}
LOOPING = ({k for k, v in CATALOG.items() if v["category"] in ("Backgrounds", "Overlays")}
           | {"img-breathing", "img-orbit", "img-parallax"}) - {"greeting-card"}

# ---------------------------------------------------------------- fonts
_FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "assets", "fonts")
_FONT_FILES = {
    "display": ("Montserrat-Bold.ttf", 700),
    "serif": ("PlayfairDisplay.ttf", 700),
    "sans-bold": ("Poppins-Bold.ttf", None),
    "sans": ("Poppins-Regular.ttf", None),
}
_font_cache = {}


def _os_font_candidates(bold):
    windir = os.environ.get("WINDIR", r"C:\Windows")
    if os.name == "nt":
        names = ["arialbd.ttf", "segoeuib.ttf"] if bold else ["arial.ttf", "segoeui.ttf"]
        return [os.path.join(windir, "Fonts", n) for n in names]
    names = ["DejaVuSans-Bold.ttf"] if bold else ["DejaVuSans.ttf"]
    return [os.path.join("/usr/share/fonts/truetype/dejavu", n) for n in names]


def get_font(size, role="display"):
    """Bundled OFL fonts first, OS fonts second; never the bitmap default."""
    size = max(int(size), 8)
    key = (role, size)
    if key in _font_cache:
        return _font_cache[key]
    fname, weight = _FONT_FILES.get(role, _FONT_FILES["display"])
    path = os.path.join(_FONT_DIR, fname)
    font = None
    if os.path.isfile(path):
        font = ImageFont.truetype(path, size)
        if weight:
            try:
                font.set_variation_by_axes([weight])
            except Exception:  # noqa: BLE001 — static font or older Pillow
                pass
    else:
        for cand in _os_font_candidates(role in ("display", "serif", "sans-bold")):
            if os.path.isfile(cand):
                font = ImageFont.truetype(cand, size)
                break
    if font is None:
        raise RuntimeError("No usable font found (bundled fonts missing from assets/fonts).")
    _font_cache[key] = font
    return font


# ---------------------------------------------------------------- easing
def _clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def ease_linear(x):
    return _clamp(x)


def ease_in_out(x):
    x = _clamp(x)
    return x * x * x * (x * (x * 6 - 15) + 10)


def ease_out(x):
    x = _clamp(x)
    return 1 - (1 - x) ** 3


def ease_out_back(x, s=1.70158):
    x = _clamp(x)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def ease_out_elastic(x):
    x = _clamp(x)
    if x in (0.0, 1.0):
        return x
    return 2 ** (-10 * x) * math.sin((x * 10 - 0.75) * (2 * math.pi / 3)) + 1


def kf(t, t0, t1, v0, v1, ease=ease_out):
    """Keyframe: value moves v0->v1 between times t0..t1 with easing."""
    if t1 <= t0:
        return v1
    return v0 + (v1 - v0) * ease((t - t0) / (t1 - t0))


# ---------------------------------------------------------------- helpers
def _mix(c1, c2, f):
    return tuple(int(a + (b - a) * f) for a, b in zip(c1, c2))


def _hex_rgb(s):
    s = (s or "").strip().lstrip("#")
    if len(s) == 6:
        try:
            return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))
        except ValueError:
            return None
    return None


def _vgrad(w, h, top, bottom):
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    for i, ch in enumerate(range(3)):
        arr[:, :, i] = np.linspace(top[ch], bottom[ch], h).astype(np.uint8)[:, None]
    return Image.fromarray(arr, "RGB")


def _radial_sprite(size, inner=(255, 255, 255), peak=255):
    """Soft radial glow/dot sprite (RGBA), precomputed once."""
    y, x = np.mgrid[0:size, 0:size]
    d = np.sqrt((x - size / 2) ** 2 + (y - size / 2) ** 2) / (size / 2)
    a = np.clip(1 - d, 0, 1) ** 1.8 * peak
    arr = np.zeros((size, size, 4), dtype=np.uint8)
    arr[:, :, 0], arr[:, :, 1], arr[:, :, 2] = inner
    arr[:, :, 3] = a.astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def _tint(sprite, color):
    arr = np.array(sprite).copy()
    arr[:, :, 0] = (arr[:, :, 0].astype(np.uint16) * color[0] // 255).astype(np.uint8)
    arr[:, :, 1] = (arr[:, :, 1].astype(np.uint16) * color[1] // 255).astype(np.uint8)
    arr[:, :, 2] = (arr[:, :, 2].astype(np.uint16) * color[2] // 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def _paste(base, sprite, cx, cy, scale=1.0, alpha=1.0):
    if scale <= 0 or alpha <= 0:
        return
    s = sprite
    if scale != 1.0:
        ns = max(int(sprite.width * scale), 2)
        s = sprite.resize((ns, ns), Image.LANCZOS)
    if alpha < 1.0:
        a = s.split()[3].point(lambda v: int(v * alpha))
        s = s.copy(); s.putalpha(a)
    base.alpha_composite(s, (int(cx - s.width / 2), int(cy - s.height / 2)))


def _text_size(draw, text, font, tracking=0):
    if not text:
        return (0, 0)
    box = draw.textbbox((0, 0), text, font=font)
    w = box[2] - box[0] + tracking * max(len(text) - 1, 0)
    return (w, box[3] - box[1])


def _draw_tracked(draw, xy, text, font, fill, tracking=0, anchor_left=None):
    x, y = xy
    if anchor_left is not None:
        x = anchor_left
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        adv = draw.textlength(ch, font=font)
        x += adv + tracking
    return x


def _stagger_letters(base, t, text, font, cx, cy, fill, tracking=0,
                     per=0.075, dur=0.38, rise=0.35, ease=ease_out):
    """Letter-by-letter staggered reveal, optically centred."""
    d = ImageDraw.Draw(base)
    widths = [d.textlength(ch, font=font) for ch in text]
    total = sum(widths) + tracking * max(len(text) - 1, 0)
    x = cx - total / 2
    asc = font.getmetrics()[0]
    for i, ch in enumerate(text):
        lt = _clamp((t - i * per) / dur)
        if lt > 0:
            a = int(255 * ease(lt))
            dy = (1 - ease(lt)) * rise * asc
            d.text((x, cy - asc / 2 + dy), ch, font=font,
                   fill=fill[:3] + (a,) if len(fill) > 3 else fill)
        x += widths[i] + tracking


# ---------------------------------------------------------------- context
class _Ctx:
    def __init__(self, kind, ow, oh, theme_name, colors, text, subtext,
                 base_img, logo_img, art_img, seed=7, speed=1.0, intensity=1.0,
                 ss=1.5, art_motion="none", art_w_frac=0.80, art_h_frac=0.80):
        self.kind = kind
        self.ow, self.oh = ow, oh                # output size
        self.ss = ss
        self.w, self.h = int(ow * ss), int(oh * ss)  # internal (supersampled)
        self.u = self.h / 1080.0                  # size unit vs 1080p
        self.speed = min(max(float(speed or 1.0), 0.25), 2.0)
        self.intensity = min(max(float(intensity if intensity is not None else 1.0), 0.1), 1.0)
        self.text = (text or "").strip()
        self.subtext = (subtext or "").strip()
        # v10: artwork's own motion (from prompt plans) + artwork size caps
        self.art_motion = (art_motion or "none").strip().lower()
        self.art_w_frac = min(max(float(art_w_frac), 0.1), 0.98)
        self.art_h_frac = min(max(float(art_h_frac), 0.1), 0.98)
        rng = random.Random(seed)
        self.rng = rng
        bgc, ca, cb = colors
        self.bg, self.ca, self.cb = bgc, ca, cb
        self.theme_name = theme_name
        # pre-rendered static assets (once per render, not per frame)
        self.bg_img = _vgrad(self.w, self.h, _mix(bgc, (0, 0, 0), 0.25),
                             _mix(bgc, ca, 0.14)).convert("RGBA")
        self.glow_a = _tint(_radial_sprite(256), ca)
        self.glow_b = _tint(_radial_sprite(256), cb)
        self.dot = _radial_sprite(64, peak=255)
        self.dot_a = _tint(self.dot, ca)
        self.dot_b = _tint(self.dot, cb)
        # vignette
        vig = Image.new("L", (self.w, self.h), 0)
        vd = ImageDraw.Draw(vig)
        vd.ellipse([-self.w * 0.25, -self.h * 0.25, self.w * 1.25, self.h * 1.25], fill=255)
        vig = vig.filter(ImageFilter.GaussianBlur(self.w // 6))
        black = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 255))
        self.vignette = (black, vig.point(lambda v: int((255 - v) * 0.32)))
        # particle field (positions in unit space, integer laps -> seamless)
        area = (ow * oh) / (1920 * 1080)
        n = int(240 * area * (0.35 + 0.65 * self.intensity)) + 20
        self.particles = [{
            "x": rng.random(), "y": rng.random(), "depth": rng.random(),
            "laps": rng.choice([1, 1, 2]), "tw": rng.choice([2, 3, 4]),
            "ph": rng.random() * math.tau} for _ in range(n)]
        self.bokeh = [{
            "x": rng.random(), "y": rng.random(), "r": 0.03 + rng.random() * 0.10,
            "ph": rng.random() * math.tau, "cyc": rng.choice([1, 2])}
            for _ in range(int(56 * (0.4 + 0.6 * self.intensity)) + 8)]
        self.confetti = [{
            "x": rng.random(), "y": rng.random(), "s": 0.5 + rng.random(),
            "rot": rng.random() * math.tau, "rsp": rng.choice([1, 2, 3]),
            "laps": rng.choice([1, 2]), "hue": rng.random()} for _ in range(90)]
        self.stars = [{
            "x": rng.random(), "y": rng.random(), "r": 1 + rng.random() * 2.4,
            "tw": rng.choice([2, 3, 5]), "ph": rng.random() * math.tau}
            for _ in range(int(150 * (0.4 + 0.6 * self.intensity)) + 20)]
        # pre-sized sprites (per-particle size is constant across frames —
        # resizing sprites per frame was the v6.0 speed bottleneck)
        for p in self.particles:
            base = self.dot_a if p["depth"] > 0.35 else self.dot_b
            px = max(int((1.5 + p["depth"] * 5.5) * self.u * 2 * 3), 4)
            p["spr"] = base.resize((px, px), Image.LANCZOS)
        for b in self.bokeh:
            spr = self.glow_a if int(b["ph"] * 10) % 2 else self.glow_b
            px = max(int(b["r"] * self.h * 2), 8)
            b["spr"] = spr.resize((px, px), Image.LANCZOS)
        self.vortex_dots = []
        for a_i in range(3):
            for k in range(70):
                frac = k / 70
                col = _mix(self.ca, self.cb, frac)
                px = max(int((0.35 + frac * 2.6) * self.u * 2 * 3), 4)
                spr = _tint(self.dot, col).resize((px, px), Image.LANCZOS)
                self.vortex_dots.append((a_i, frac, spr, 0.20 + 0.6 * frac))
        # user artwork / photos
        self.base_img = None
        if base_img is not None:
            self.base_img = self._cover(base_img.convert("RGB"), self.w, self.h).convert("RGBA")
        self.logo = None
        if logo_img is not None:
            lg = logo_img.convert("RGBA")
            maxw, maxh = int(self.w * 0.52), int(self.h * 0.52)
            lg.thumbnail((maxw, maxh), Image.LANCZOS)
            self.logo = lg
        self.art = None
        self.art_shadow = None
        if art_img is not None:
            art = art_img.convert("RGBA")
            maxw, maxh = int(self.w * self.art_w_frac), int(self.h * self.art_h_frac)
            art.thumbnail((maxw, maxh), Image.LANCZOS)
            self.art = art
            sh = Image.new("RGBA", art.size, (0, 0, 0, 255))
            sh.putalpha(art.split()[3].point(lambda v: int(v * 0.45)))
            self.art_shadow = sh.filter(ImageFilter.GaussianBlur(12 * self.u))

    @staticmethod
    def _cover(img, w, h, zoom=1.0):
        scale = max(w / img.width, h / img.height) * zoom
        nw, nh = max(int(img.width * scale), 1), max(int(img.height * scale), 1)
        r = img.resize((nw, nh), Image.LANCZOS)
        x, y = (nw - w) // 2, (nh - h) // 2
        return r.crop((x, y, x + w, y + h))

    def cycles(self, base_cycles):
        """Speed-quantised integer cycles (loops stay seamless)."""
        return max(1, int(round(base_cycles * self.speed)))

    def base_canvas(self, dark=0.0):
        if self.base_img is not None and self.kind in (
                "title-bold", "lower-third", "img-kenburns"):
            img = self.base_img.copy()
            if dark:
                ov = Image.new("RGBA", img.size, (0, 0, 0, int(255 * dark)))
                img.alpha_composite(ov)
            return img
        return self.bg_img.copy()

    def add_vignette(self, img):
        black, mask = self.vignette
        img.alpha_composite(Image.composite(black, Image.new("RGBA", img.size, (0, 0, 0, 0)), mask))


# ---------------------------------------------------------------- frames
def _frame_particles(ctx, img, t, rise=True):
    d = ImageDraw.Draw(img)
    for p in ctx.particles:
        laps = ctx.cycles(p["laps"])
        y = (p["y"] - t * laps) % 1.0 if rise else p["y"]
        x = (p["x"] + 0.01 * math.sin(math.tau * ctx.cycles(1) * t + p["ph"])) % 1.0
        tw = 0.55 + 0.45 * math.sin(math.tau * p["tw"] * t + p["ph"])
        spr = p["spr"]
        a = max(0.12, tw)
        s2 = spr if a >= 0.999 else spr.copy()
        if a < 0.999:
            s2.putalpha(spr.split()[3].point(lambda v: int(v * a)))
        img.alpha_composite(s2, (int(x * ctx.w - spr.width / 2), int(y * ctx.h - spr.height / 2)))


def _frame(ctx, i, n):
    kind = ctx.kind
    t = i / max(n - 1, 1)
    w, h, u = ctx.w, ctx.h, ctx.u
    overlay_kinds = kind.startswith("overlay-")
    img = Image.new("RGBA", (w, h), (0, 0, 0, 255)) if overlay_kinds else ctx.base_canvas()
    d = ImageDraw.Draw(img)
    TAU = math.tau

    if kind == "bg-gradient":
        for k, spr, cyc, rad, ph in (
                (0, ctx.glow_a, 1, 0.75, 0.0), (1, ctx.glow_b, 2, 0.6, 2.1),
                (2, ctx.glow_a, 1, 0.5, 4.2)):
            cx = w * (0.5 + 0.30 * math.sin(TAU * ctx.cycles(cyc) * t + ph))
            cy = h * (0.5 + 0.26 * math.cos(TAU * ctx.cycles(cyc) * t + ph * 1.7))
            _paste(img, spr, cx, cy, scale=(rad * h) / 128, alpha=0.5)
        ctx.add_vignette(img)

    elif kind == "bg-particles":
        _frame_particles(ctx, img, t)
        ctx.add_vignette(img)

    elif kind == "bg-bokeh":
        for b in ctx.bokeh:
            cx = (b["x"] + 0.03 * math.sin(TAU * b["cyc"] * t + b["ph"])) * w
            cy = (b["y"] + 0.03 * math.cos(TAU * b["cyc"] * t + b["ph"] * 2)) * h
            spr = b["spr"]
            s2 = spr.copy(); s2.putalpha(spr.split()[3].point(lambda v: int(v * 0.20)))
            img.alpha_composite(s2, (int(cx - spr.width / 2), int(cy - spr.height / 2)))
        ctx.add_vignette(img)

    elif kind == "bg-waves":
        layers = [(0.52, 0.05, 1, 70), (0.62, 0.07, 2, 100), (0.74, 0.09, 1, 140), (0.86, 0.11, 2, 190)]
        for li, (base_y, amp, cyc, alpha) in enumerate(layers):
            col = _mix(ctx.ca, ctx.cb, li / max(len(layers) - 1, 1))
            pts = []
            steps = 48
            for s_i in range(steps + 1):
                x = w * s_i / steps
                y = h * base_y + h * amp * math.sin(TAU * (s_i / steps * 2 + ctx.cycles(cyc) * t + li * 0.33))
                pts.append((x, y))
            poly = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            pd = ImageDraw.Draw(poly)
            pd.polygon(pts + [(w, h), (0, h)], fill=col + (alpha,))
            img.alpha_composite(poly)

    elif kind == "bg-confetti":
        _celebration_confetti(ctx, img, t)
        ctx.add_vignette(img)

    elif kind == "bg-geometric":
        cols, rows = max(4, w // int(260 * u)), max(3, h // int(260 * u))
        cw, ch = w / cols, h / rows
        for gy in range(rows):
            for gx in range(cols):
                ph = (gx + gy) * 0.45
                s = 0.72 + 0.28 * math.sin(TAU * ctx.cycles(2) * t + ph)
                cx, cy = (gx + 0.5) * cw, (gy + 0.5) * ch
                r = min(cw, ch) * 0.30 * s
                col = _mix(ctx.ca, ctx.cb, ((gx + gy) % 5) / 4)
                if (gx + gy) % 3 == 0:
                    ang = TAU * ctx.cycles(1) * t + ph
                    sq = [(cx + r * math.cos(ang + k * math.pi / 2 + math.pi / 4),
                           cy + r * math.sin(ang + k * math.pi / 2 + math.pi / 4)) for k in range(4)]
                    d.polygon(sq, outline=col + (230,), width=max(2, int(3 * u)))
                elif (gx + gy) % 3 == 1:
                    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col + (200,),
                              width=max(2, int(3 * u)))
                else:
                    d.polygon([(cx, cy - r), (cx + r, cy + r), (cx - r, cy + r)],
                              outline=col + (170,), width=max(2, int(3 * u)))

    elif kind == "bg-light-trails":
        trails = 7
        for k in range(trails):
            base_y = h * (0.16 + 0.11 * k)
            amp = h * (0.05 + 0.012 * k)
            freq = 1.5 + 0.35 * k
            pts = []
            steps = 90
            for s_i in range(steps + 1):
                x = w * s_i / steps
                y = base_y + amp * math.sin(TAU * (freq * s_i / steps - ctx.cycles(1) * t) + k)
                pts.append((x, y))
            col = _mix(ctx.ca, ctx.cb, k / max(trails - 1, 1))
            d.line(pts, fill=col + (46,), width=max(6, int(16 * u)))
            d.line(pts, fill=col + (190,), width=max(2, int(4 * u)))
            hx = w * ((t * ctx.cycles(1) + k / trails) % 1.0)
            hy = base_y + amp * math.sin(TAU * (freq * hx / w - ctx.cycles(1) * t) + k)
            _paste(img, _tint(ctx.dot, col), hx, hy, scale=1.6 * u, alpha=0.95)

    elif kind == "bg-hexwave":
        R = 46 * u
        dx, dy = R * 1.74, R * 1.5
        gy = 0
        y = -R
        while y < h + R:
            gx = 0
            x = -R + (R * 0.87 if gy % 2 else 0)
            while x < w + R:
                dist = math.hypot(x - w / 2, y - h / 2) / (h * 0.62)
                b = 0.5 + 0.5 * math.sin(TAU * (ctx.cycles(2) * t) - dist * 5.2)
                col = _mix(ctx.bg, _mix(ctx.ca, ctx.cb, b), 0.25 + 0.75 * b)
                hexpts = [(x + R * 0.92 * math.cos(math.pi / 3 * k + math.pi / 6),
                           y + R * 0.92 * math.sin(math.pi / 3 * k + math.pi / 6)) for k in range(6)]
                if b > 0.55:
                    d.polygon(hexpts, fill=col + (int(90 + 120 * b),))
                d.polygon(hexpts, outline=_mix(col, (255, 255, 255), 0.25) + (160,),
                          width=max(1, int(1.6 * u)))
                x += dx; gx += 1
            y += dy; gy += 1
        ctx.add_vignette(img)

    elif kind == "bg-equalizer":
        bars = max(18, int(30 * ctx.intensity) + 8)
        bw_ = w / bars
        for b_i in range(bars):
            f1 = math.sin(TAU * (ctx.cycles(2) * t) + b_i * 0.55)
            f2 = math.sin(TAU * (ctx.cycles(3) * t) + b_i * 1.31)
            f3 = math.sin(TAU * (ctx.cycles(1) * t) + b_i * 0.23)
            v = abs(0.45 * f1 + 0.35 * f2 + 0.20 * f3)
            bh_ = h * 0.08 + h * 0.62 * v
            col = _mix(ctx.ca, ctx.cb, b_i / max(bars - 1, 1))
            x0 = b_i * bw_ + bw_ * 0.18
            d.rounded_rectangle([x0, h * 0.82 - bh_, x0 + bw_ * 0.64, h * 0.82],
                                radius=bw_ * 0.2, fill=col + (235,))
            d.rounded_rectangle([x0, h * 0.84, x0 + bw_ * 0.64, h * 0.84 + bh_ * 0.4],
                                radius=bw_ * 0.2, fill=col + (50,))
        d.line([0, h * 0.83, w, h * 0.83], fill=(255, 255, 255, 60), width=max(1, int(2 * u)))

    elif kind == "bg-vortex":
        cx, cy = w / 2, h / 2
        for s in ctx.stars:
            d.ellipse([s["x"] * w - s["r"] * u, s["y"] * h - s["r"] * u,
                       s["x"] * w + s["r"] * u, s["y"] * h + s["r"] * u],
                      fill=(255, 255, 255, int(120 + 100 * math.sin(TAU * s["tw"] * t + s["ph"]))))
        for a_i, frac, spr, al in ctx.vortex_dots:
            ang = a_i * TAU / 3 + frac * 4.4 + TAU * ctx.cycles(1) * t
            rad = frac * h * 0.52
            x, y = cx + rad * math.cos(ang), cy + rad * math.sin(ang) * 0.62
            s2 = spr if al >= 0.999 else spr.copy()
            if al < 0.999:
                s2.putalpha(spr.split()[3].point(lambda v: int(v * al)))
            img.alpha_composite(s2, (int(x - spr.width / 2), int(y - spr.height / 2)))
        _paste(img, ctx.glow_b, cx, cy, scale=h * 0.36 / 128, alpha=0.75)
        ctx.add_vignette(img)

    elif kind == "bg-burst":
        cx, cy = w / 2, h * 0.56
        rays = 24
        rot = TAU * ctx.cycles(1) * t * 0.25
        R = math.hypot(w, h)
        for k in range(rays):
            if k % 2:
                continue
            a0 = rot + k * TAU / rays
            a1 = a0 + TAU / rays * 0.55
            d.polygon([(cx, cy), (cx + R * math.cos(a0), cy + R * math.sin(a0)),
                       (cx + R * math.cos(a1), cy + R * math.sin(a1))],
                      fill=_mix(ctx.ca, (255, 255, 255), 0.15) + (52,))
        pulse = 1 + 0.05 * math.sin(TAU * ctx.cycles(2) * t)
        _paste(img, ctx.glow_b, cx, cy, scale=h * 0.30 * pulse / 128, alpha=0.8)

    elif kind == "overlay-leak":
        for k, spr, cyc, ph in ((0, ctx.glow_a, 1, 0.0), (1, ctx.glow_b, 2, 2.4), (2, ctx.glow_a, 1, 4.4)):
            cx = w * (0.5 + 0.42 * math.sin(TAU * ctx.cycles(cyc) * t + ph))
            cy = h * (0.5 + 0.36 * math.cos(TAU * ctx.cycles(cyc) * t + ph))
            _paste(img, spr, cx, cy, scale=h * 0.85 / 128, alpha=0.55)

    elif kind == "overlay-grain":
        rng = np.random.default_rng(1234 + i)
        noise = rng.normal(128, 42, (h // 2, w // 2)).clip(0, 255).astype(np.uint8)
        grain = Image.fromarray(noise, "L").resize((w, h), Image.BILINEAR)
        img.alpha_composite(Image.merge("RGBA", (grain, grain, grain,
                                                 grain.point(lambda v: 46))))

    elif kind == "overlay-sparkle":
        for s in ctx.stars:
            tw = 0.5 + 0.5 * math.sin(TAU * s["tw"] * t + s["ph"])
            if tw < 0.55:
                continue
            x, y = s["x"] * w, s["y"] * h
            r = s["r"] * u * (0.6 + tw)
            col = _mix(ctx.ca, (255, 255, 255), 0.5)
            d.line([x - r * 3, y, x + r * 3, y], fill=col + (int(200 * tw),), width=max(1, int(2 * u)))
            d.line([x, y - r * 3, x, y + r * 3], fill=col + (int(200 * tw),), width=max(1, int(2 * u)))
            _paste(img, ctx.dot_b, x, y, scale=r / 14, alpha=tw * 0.8)

    else:
        _frame_story(ctx, img, d, t)
    return img


def _celebration_confetti(ctx, img, t):
    d = ImageDraw.Draw(img)
    TAU = math.tau
    palette = [ctx.ca, ctx.cb, (255, 255, 255),
               colorsys.hsv_to_rgb(0.1, 0.6, 1.0), colorsys.hsv_to_rgb(0.55, 0.5, 1.0)]
    for ci, c in enumerate(ctx.confetti):
        laps = ctx.cycles(c["laps"])
        y = -0.07 + ((c["y"] + t * laps) % 1.0) * 1.14  # integer-lap wrap: seamless
        x = (c["x"] + 0.02 * math.sin(TAU * ctx.cycles(1) * t + ci)) % 1.0
        ang = c["rot"] + TAU * c["rsp"] * t
        s = c["s"] * 13 * ctx.u
        col = palette[int(c["hue"] * 10 + ci) % len(palette)]
        col = tuple(int(v * 255) if isinstance(v, float) else v for v in col[:3])
        dx, dy = s * math.cos(ang), s * math.sin(ang)
        px, py = s * 0.45 * math.cos(ang + math.pi / 2), s * 0.45 * math.sin(ang + math.pi / 2)
        cxp, cyp = x * ctx.w, y * ctx.h
        d.polygon([(cxp - dx - px, cyp - dy - py), (cxp + dx - px, cyp + dy - py),
                   (cxp + dx + px, cyp + dy + py), (cxp - dx + px, cyp - dy + py)],
                  fill=col + (235,))


# ------------------------------------------------------- story templates
def _frame_story(ctx, img, d, t):
    kind, w, h, u, TAU = ctx.kind, ctx.w, ctx.h, ctx.u, math.tau
    ca, cb = ctx.ca, ctx.cb

    if kind == "title-cinematic":
        for k, spr, ph in ((0, ctx.glow_a, 0.0), (1, ctx.glow_b, 2.6)):
            cx = w * (0.5 + 0.22 * math.sin(TAU * ctx.cycles(1) * t + ph))
            _paste(img, spr, cx, h * 0.42, scale=h * 0.55 / 128, alpha=0.35)
        text = ctx.text or "Your Title"
        font = get_font(h * 0.115, "serif")
        tracking = h * 0.012
        _stagger_letters(img, t, text.upper(), font, w / 2, h * 0.44,
                         (255, 255, 255), tracking=tracking, per=0.055, dur=0.30)
        lw_ = kf(t, 0.35, 0.75, 0, w * 0.16, ease_in_out)
        d.line([w / 2 - lw_, h * 0.545, w / 2 + lw_, h * 0.545], fill=ca + (255,),
               width=max(2, int(3 * u)))
        if ctx.subtext:
            f2 = get_font(h * 0.034, "sans")
            a = kf(t, 0.55, 0.9, 0, 1, ease_out)
            tw_, _ = _text_size(d, ctx.subtext, f2)
            d.text(((w - tw_) / 2, h * 0.60), ctx.subtext, font=f2,
                   fill=(230, 230, 230, int(255 * a)))
        ctx.add_vignette(img)

    elif kind == "title-bold":
        img.paste(ctx.base_canvas(dark=0.25), (0, 0))
        d = ImageDraw.Draw(img)
        zoom = 1.0  # base already covers; motion comes from text/accents
        bar_w = kf(t, 0.05, 0.4, 0, w * 0.075, ease_out)
        d.rectangle([w * 0.07, h * 0.30, w * 0.07 + bar_w, h * 0.335], fill=ca + (255,))
        text = ctx.text or "Bold Title"
        font = get_font(h * 0.13, "display")
        words = text.split()
        y = h * 0.38
        line_h = h * 0.15
        lines, cur = [], ""
        for wd in words:
            trial = (cur + " " + wd).strip()
            if _text_size(d, trial, font)[0] > w * 0.86 and cur:
                lines.append(cur); cur = wd
            else:
                cur = trial
        if cur:
            lines.append(cur)
        for li, line in enumerate(lines[:3]):
            lt = _clamp((t - 0.12 - li * 0.09) / 0.35)
            if lt <= 0:
                continue
            a = int(255 * ease_out(lt))
            dy = (1 - ease_out_back(lt)) * h * 0.05
            d.text((w * 0.07, y + li * line_h + dy), line, font=font,
                   fill=(255, 255, 255, a))
        if ctx.subtext:
            f2 = get_font(h * 0.036, "sans")
            a = kf(t, 0.5, 0.85, 0, 1)
            d.text((w * 0.07, y + min(len(lines), 3) * line_h + h * 0.02), ctx.subtext,
                   font=f2, fill=cb + (int(240 * a),))

    elif kind == "lower-third":
        img.paste(ctx.base_canvas(dark=0.08), (0, 0))
        d = ImageDraw.Draw(img)
        slide = kf(t, 0.05, 0.45, 0, 1, ease_out)
        stay = 1 - kf(t, 0.94, 1.0, 0, 1, ease_in_out)
        x0 = w * 0.06 - (1 - slide) * w * 0.5
        alpha = int(255 * min(slide, stay + 0.001))
        bar_y, bar_h = h * 0.74, h * 0.155
        d.rectangle([x0, bar_y, x0 + w * 0.016, bar_y + bar_h], fill=ca + (alpha,))
        panel = Image.new("RGBA", (int(w * 0.56), int(bar_h)), (8, 10, 14, int(205 * slide)))
        img.alpha_composite(panel, (int(x0 + w * 0.016), int(bar_y)))
        d = ImageDraw.Draw(img)
        name = ctx.text or "Your Name"
        f1 = get_font(h * 0.052, "display")
        d.text((x0 + w * 0.035, bar_y + bar_h * 0.13), name, font=f1,
               fill=(255, 255, 255, alpha))
        if ctx.subtext:
            f2 = get_font(h * 0.032, "sans")
            a2 = kf(t, 0.3, 0.65, 0, 1)
            d.text((x0 + w * 0.035, bar_y + bar_h * 0.60), ctx.subtext, font=f2,
                   fill=cb + (int(255 * a2 * stay),))

    elif kind == "logo-reveal":
        _frame_particles(ctx, img, t, rise=False)
        cx, cy = w / 2, h / 2
        pop = ease_out_back(_clamp(t / 0.30))
        pulse = 1 + 0.03 * math.sin(TAU * ctx.cycles(2) * t)
        ring_r = kf(t, 0.1, 0.9, 0.06, 0.30, ease_out) * h
        ring_a = int(200 * (1 - kf(t, 0.1, 0.95, 0, 1)))
        if ring_a > 4:
            d.ellipse([cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r],
                      outline=ca + (ring_a,), width=max(2, int(3 * u)))
        _paste(img, ctx.glow_a, cx, cy, scale=h * 0.5 * pop * pulse / 128, alpha=0.5)
        if ctx.logo is not None:
            lg = ctx.logo
            ns = max(int(lg.width * pop * pulse), 2)
            lgr = lg.resize((ns, int(lg.height * ns / lg.width)), Image.LANCZOS)
            if pop > 0.02:
                img.alpha_composite(lgr, (int(cx - ns / 2), int(cy - lgr.height / 2)))
        else:
            text = ctx.text or "BRAND"
            font = get_font(h * 0.11, "display")
            _stagger_letters(img, t, text, font, cx, cy, (255, 255, 255),
                             tracking=h * 0.008, per=0.05, dur=0.3)
        if ctx.subtext:
            f2 = get_font(h * 0.032, "sans")
            a = kf(t, 0.55, 0.9, 0, 1)
            tw_, _ = _text_size(ImageDraw.Draw(img), ctx.subtext, f2)
            ImageDraw.Draw(img).text(((w - tw_) / 2, h * 0.68), ctx.subtext, font=f2,
                                     fill=cb + (int(240 * a),))
        ctx.add_vignette(img)

    elif kind == "intro-sting":
        sweep = kf(t, 0.0, 0.35, -0.2, 1.2, ease_in_out)
        band = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        bd = ImageDraw.Draw(band)
        bx = sweep * w
        bd.polygon([(bx - w * 0.25, 0), (bx, 0), (bx - w * 0.45, h), (bx - w * 0.7, h)],
                   fill=ca + (60,))
        img.alpha_composite(band)
        d = ImageDraw.Draw(img)
        text = ctx.text or "STUDIO"
        font = get_font(h * 0.125, "display")
        sc = kf(t, 0.05, 0.4, 1.35, 1.0, ease_out)
        tw_, th_ = _text_size(d, text, font)
        tile = Image.new("RGBA", (int(tw_) + 8, int(th_) + int(h * 0.05)), (0, 0, 0, 0))
        td = ImageDraw.Draw(tile)
        td.text((4, 0), text, font=font, fill=(255, 255, 255, 255))
        tile = tile.resize((max(int(tile.width * sc), 2), max(int(tile.height * sc), 2)),
                           Image.LANCZOS)
        img.alpha_composite(tile, (int(w / 2 - tile.width / 2), int(h * 0.44 - tile.height / 2)))
        lw_ = kf(t, 0.3, 0.55, 0, w * 0.11, ease_out)
        d = ImageDraw.Draw(img)
        d.line([w / 2 - lw_, h * 0.60, w / 2 + lw_, h * 0.60], fill=cb + (255,),
               width=max(2, int(4 * u)))

    elif kind == "countdown":
        _frame_particles(ctx, img, t)
        seg = min(int(t * 5), 4)
        lt = (t * 5) - seg
        num = str(5 - seg)
        font = get_font(h * 0.46, "display")
        pop = ease_out_back(_clamp(lt / 0.30))
        fade = 1 - kf(lt, 0.8, 1.0, 0, 1)
        tile = Image.new("RGBA", (int(h * 0.6), int(h * 0.6)), (0, 0, 0, 0))
        td = ImageDraw.Draw(tile)
        tw_, th_ = _text_size(td, num, font)
        td.text(((tile.width - tw_) / 2, (tile.height - th_) / 2 - h * 0.03), num,
                font=font, fill=(255, 255, 255, int(255 * fade)))
        tile = tile.resize((max(int(tile.width * pop), 2), max(int(tile.height * pop), 2)),
                           Image.LANCZOS)
        img.alpha_composite(tile, (int(w / 2 - tile.width / 2), int(h / 2 - tile.height / 2)))
        d = ImageDraw.Draw(img)
        arc = -90 + 360 * lt
        d.arc([w / 2 - h * 0.31, h / 2 - h * 0.31, w / 2 + h * 0.31, h / 2 + h * 0.31],
              start=-90, end=arc, fill=ca + (220,), width=max(3, int(6 * u)))

    elif kind == "greeting-card":
        _celebration_confetti(ctx, img, t)
        card = Image.new("RGBA", (int(w * 0.72), int(h * 0.58)), (255, 252, 246, 255))
        cd = ImageDraw.Draw(card)
        cd.rounded_rectangle([0, 0, card.width - 1, card.height - 1],
                             radius=int(24 * u), outline=ca + (255,), width=max(3, int(5 * u)))
        pop = ease_out_back(_clamp(t / 0.3))
        card_r = card.resize((max(int(card.width * pop), 2), max(int(card.height * pop), 2)),
                             Image.LANCZOS)
        sh = Image.new("RGBA", card_r.size, (0, 0, 0, 110))
        img.alpha_composite(sh, (int(w / 2 - card_r.width / 2 + 10 * u),
                                 int(h / 2 - card_r.height / 2 + 14 * u)))
        img.alpha_composite(card_r, (int(w / 2 - card_r.width / 2),
                                     int(h / 2 - card_r.height / 2)))
        d = ImageDraw.Draw(img)
        text = ctx.text or "Happy Birthday!"
        font = get_font(h * 0.085, "serif")
        a = kf(t, 0.25, 0.6, 0, 1)
        tw_, _ = _text_size(d, text, font)
        ink = _mix(ctx.bg, (0, 0, 0), 0.35) if sum(ctx.bg) > 200 else (40, 30, 20)
        d.text(((w - tw_) / 2, h * 0.40), text, font=font, fill=ink + (int(255 * a),))
        if ctx.subtext:
            f2 = get_font(h * 0.036, "sans")
            tw2, _ = _text_size(d, ctx.subtext, f2)
            d.text(((w - tw2) / 2, h * 0.53), ctx.subtext, font=f2,
                   fill=_mix(ink, ca, 0.4) + (int(240 * a),))

    elif kind.startswith("img-"):
        _frame_image_motion(ctx, img, d, t)


def _art_base(ctx, img, t):
    """Paste artwork shadow + artwork with transform; returns art rect."""
    art = ctx.art
    if art is None:
        return None
    return art


def _art_motion_tf(ctx, t):
    """v10 — the artwork's OWN motion, combined with the template effect.
    Returns (scale, dx, dy) in internal (supersampled) pixels.
    Loop safety: every motion is built from integer-cycle cos/sin terms,
    so at t=1 the transform is exactly the identity again — the v6
    seamless-loop property of the looping kinds is preserved."""
    am = getattr(ctx, "art_motion", "none") or "none"
    TAU = math.tau
    ph = TAU * ctx.cycles(1) * t
    if am == "zoom-in":     # grow to +16% mid-loop, return to start
        return 1 + 0.16 * (0.5 - 0.5 * math.cos(ph)), 0.0, 0.0
    if am == "zoom-out":    # start +16%, settle back to 100%
        return 1 + 0.16 * (0.5 + 0.5 * math.cos(ph)), 0.0, 0.0
    if am == "pan-left":    # drift left mid-loop and return
        return 1.0, -ctx.w * 0.045 * (0.5 - 0.5 * math.cos(ph)), 0.0
    if am == "pan-right":
        return 1.0, ctx.w * 0.045 * (0.5 - 0.5 * math.cos(ph)), 0.0
    if am == "sway":        # gentle side-to-side + vertical sway
        return (1.0, math.sin(ph) * ctx.w * 0.018,
                math.sin(TAU * ctx.cycles(2) * t) * ctx.h * 0.010)
    if am == "breathe":
        return 1 + 0.030 * math.sin(ph), 0.0, 0.0
    return 1.0, 0.0, 0.0


def _frame_image_motion(ctx, img, d, t):
    kind, w, h, u, TAU = ctx.kind, ctx.w, ctx.h, ctx.u, math.tau
    art = ctx.art
    if art is None:
        f = get_font(h * 0.05, "sans")
        msg = "Upload an image / logo to animate"
        tw_, _ = _text_size(d, msg, f)
        d.text(((w - tw_) / 2, h * 0.47), msg, font=f, fill=(255, 255, 255, 220))
        return
    cx, cy = w / 2, h / 2
    ms, mdx, mdy = _art_motion_tf(ctx, t)   # v10 artwork motion

    if kind == "img-breathing":
        _frame_particles(ctx, img, t)
        breathe = (1 + 0.022 * math.sin(TAU * ctx.cycles(1) * t)) * ms
        glow_a = 0.35 + 0.25 * (0.5 + 0.5 * math.sin(TAU * ctx.cycles(1) * t))
        _paste(img, ctx.glow_a, cx, cy, scale=h * 0.62 / 128, alpha=glow_a)
        nw = int(art.width * breathe)
        a = art.resize((nw, int(art.height * breathe)), Image.LANCZOS)
        sh = ctx.art_shadow.resize(a.size, Image.LANCZOS)
        img.alpha_composite(sh, (int(cx - nw / 2 + mdx), int(cy - a.height / 2 + 14 * u + mdy)))
        img.alpha_composite(a, (int(cx - nw / 2 + mdx), int(cy - a.height / 2 + mdy)))
        ctx.add_vignette(img)

    elif kind == "img-orbit":
        for oi in range(int(130 * ctx.intensity) + 20):
            ang = TAU * (oi / 130) + TAU * ctx.cycles(1) * t * (1 if oi % 2 else -1)
            rad = h * (0.30 + 0.10 * math.sin(oi * 2.7))
            x = cx + rad * math.cos(ang) * (w / h if w > h else 1)
            y = cy + rad * math.sin(ang) * 0.72
            trail = 0.5 + 0.5 * math.sin(ang * 2 + oi)
            _paste(img, ctx.dot_a if oi % 3 else ctx.dot_b, x, y,
                   scale=(0.5 + trail * 1.3) * u, alpha=0.25 + 0.55 * trail)
        fy = math.sin(TAU * ctx.cycles(2) * t) * 6 * u
        rot = 1.0 * math.sin(TAU * ctx.cycles(1) * t)
        a = art
        if ms != 1.0:
            a = art.resize((max(int(art.width * ms), 2),
                            max(int(art.height * ms), 2)), Image.LANCZOS)
        a = a.rotate(rot, resample=Image.BICUBIC, expand=False)
        sh = ctx.art_shadow
        if ms != 1.0:
            sh = sh.resize(a.size, Image.LANCZOS)
        sh = sh.rotate(rot, resample=Image.BICUBIC, expand=False)
        img.alpha_composite(sh, (int(cx - a.width / 2 + mdx), int(cy - a.height / 2 + fy + 14 * u + mdy)))
        img.alpha_composite(a, (int(cx - a.width / 2 + mdx), int(cy - a.height / 2 + fy + mdy)))
        ctx.add_vignette(img)

    elif kind == "img-sweep":
        _frame_particles(ctx, img, t)
        scale_in = kf(t, 0.0, 0.28, 0.82, 1.0, ease_out_back) * ms
        nw = max(int(art.width * scale_in), 2)
        a = art.resize((nw, int(art.height * scale_in)), Image.LANCZOS)
        sh = ctx.art_shadow.resize(a.size, Image.LANCZOS)
        ax, ay = int(cx - nw / 2 + mdx), int(cy - a.height / 2 + mdy)
        img.alpha_composite(sh, (ax, ay + int(14 * u)))
        # diagonal shine sweep, masked by the artwork's alpha, 1 cycle per loop
        shine_x = kf(t, 0.30, 0.62, -0.3, 1.3, ease_in_out)
        shine = Image.new("RGBA", a.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(shine)
        bw_ = a.width * 0.28
        sx = shine_x * a.width
        sd.polygon([(sx - bw_, a.height), (sx, 0), (sx + bw_ * 0.5, 0),
                    (sx - bw_ * 0.5, a.height)], fill=(255, 255, 255, 120))
        shine.putalpha(Image.composite(shine.split()[3],
                                       Image.new("L", a.size, 0), a.split()[3]))
        a2 = a.copy(); a2.alpha_composite(shine)
        img.alpha_composite(a2, (ax, ay))
        ring_r = kf(t, 0.05, 0.55, 0.05, 0.34, ease_out) * h
        ring_a = int(190 * (1 - kf(t, 0.05, 0.6, 0, 1)))
        if ring_a > 4:
            d = ImageDraw.Draw(img)
            d.ellipse([cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r],
                      outline=ctx.cb + (ring_a,), width=max(2, int(3 * u)))
        ctx.add_vignette(img)

    elif kind == "img-parallax":
        bgart = ctx._cover(art.convert("RGB"), w, h, zoom=1.15).convert("RGBA")
        bgart = bgart.filter(ImageFilter.GaussianBlur(18 * u))
        dark = Image.new("RGBA", (w, h), (0, 0, 0, 70))
        bgart.alpha_composite(dark)
        ox = math.sin(TAU * ctx.cycles(1) * t) * w * 0.012
        img.alpha_composite(bgart, (int(ox), 0))
        fx = math.sin(TAU * ctx.cycles(1) * t) * w * -0.02 + mdx
        fy = math.cos(TAU * ctx.cycles(2) * t) * h * 0.008 + mdy
        fart, sh = art, ctx.art_shadow
        if ms != 1.0:
            fart = art.resize((max(int(art.width * ms), 2),
                               max(int(art.height * ms), 2)), Image.LANCZOS)
            sh = ctx.art_shadow.resize(fart.size, Image.LANCZOS)
        img.alpha_composite(sh, (int(cx - fart.width / 2 + fx),
                                 int(cy - fart.height / 2 + fy + 14 * u)))
        img.alpha_composite(fart, (int(cx - fart.width / 2 + fx),
                                   int(cy - fart.height / 2 + fy)))
        ctx.add_vignette(img)

    elif kind == "img-kenburns":
        zoom = kf(t, 0, 1, 1.06, 1.16, ease_in_out)
        cover = ctx._cover(art.convert("RGB"), w, h, zoom=zoom).convert("RGBA")
        img.paste(cover, (0, 0))
        ctx.add_vignette(img)
        if ctx.text:
            d = ImageDraw.Draw(img)
            f = get_font(h * 0.05, "display")
            a = kf(t, 0.15, 0.5, 0, 1)
            tw_, _ = _text_size(d, ctx.text, f)
            d.text(((w - tw_) / 2 + 2 * u, h * 0.86 + 2 * u), ctx.text, font=f,
                   fill=(0, 0, 0, int(160 * a)))
            d.text(((w - tw_) / 2, h * 0.86), ctx.text, font=f,
                   fill=(255, 255, 255, int(255 * a)))


# ---------------------------------------------------------------- export
def _load_image(path):
    if not path or not os.path.isfile(path):
        return None
    if path.lower().endswith(".svg"):
        from .svg_render import render_svg_to_png
        tmp = path + ".rendered.png"
        render_svg_to_png(path, tmp, 1600, 1600)
        path = tmp
    try:
        im = Image.open(path)
        im.load()
        return im
    except Exception:  # noqa: BLE001
        return None


def _ffprobe_check(path, ow, oh, fps, duration):
    fp = shutil.which("ffprobe")
    check = {"ffprobe": bool(fp), "adobe_stock_ready": False}
    if not fp:
        check["note"] = "ffprobe not found — install FFmpeg (includes ffprobe) to verify exports."
        return check
    try:
        out = subprocess.run([fp, "-v", "error", "-select_streams", "v:0",
                              "-show_entries", "stream=codec_name,width,height,avg_frame_rate",
                              "-show_entries", "format=duration,size",
                              "-of", "json", path],
                             capture_output=True, text=True, timeout=60)
        import json as _json
        data = _json.loads(out.stdout or "{}")
        st = (data.get("streams") or [{}])[0]
        fmt = data.get("format") or {}
        num, den = (st.get("avg_frame_rate") or "0/1").split("/")
        real_fps = float(num) / float(den) if float(den or 0) else 0
        real_dur = float(fmt.get("duration") or 0)
        check.update({
            "codec": st.get("codec_name"), "width": st.get("width"),
            "height": st.get("height"), "fps": round(real_fps, 2),
            "duration": round(real_dur, 2),
            "size_mb": round(int(fmt.get("size") or 0) / 1048576, 2)})
        check["checks"] = {
            "codec_h264": st.get("codec_name") == "h264",
            "resolution_ok": st.get("width") == ow and st.get("height") == oh,
            "fps_ok": abs(real_fps - fps) < 0.6,
            "duration_ok": abs(real_dur - duration) <= 0.35,
        }
        check["adobe_stock_ready"] = all(check["checks"].values())
    except Exception as e:  # noqa: BLE001
        check["note"] = f"ffprobe check failed: {str(e)[:120]}"
    return check


def create_mgfx(dst, kind="bg-gradient", *, theme="gold", text="", subtext="",
                ratio="16:9", duration=5.0, fps=30, image_path=None, logo_path=None,
                quality="HD", speed=1.0, intensity=1.0, color_primary=None,
                color_accent=None, color_bg=None, fmt="mp4", preview=False,
                progress_cb=None, art_motion=None, art_scale=None):
    """Render one motion graphic.

    v10 kwargs (both defaulted — old calls are unaffected):
      art_motion: the artwork's own motion for img-* kinds — one of
        zoom-in / zoom-out / pan-left / pan-right / sway / breathe / none.
        Combines with the template effect and is loop-safe (see
        _art_motion_tf). img-kenburns keeps its one-way ease as before.
      art_scale: artwork size caps as frame fractions — None keeps the
        classic (0.80, 0.80); a float scales both caps; a (w_frac, h_frac)
        pair sets them directly (the prompt route passes (0.88, 0.75) so
        the artwork fills more of the frame)."""
    if kind not in CATALOG:
        raise ValueError(f"Unknown motion graphic '{kind}'.")
    if preview:
        ow, oh = RESOLUTIONS_PREVIEW.get(ratio, RESOLUTIONS_PREVIEW["16:9"])
        ss = 1.0
    elif str(quality).upper() == "4K":
        ow, oh = RESOLUTIONS_4K.get(ratio, RESOLUTIONS_4K["16:9"])
        ss = 1.5 if kind.startswith(("title", "logo", "img-")) else 1.25
    else:
        ow, oh = RESOLUTIONS.get(ratio, RESOLUTIONS["16:9"])
        ss = 2.0 if kind.startswith(("title", "logo", "img-")) else 1.5
    fps = int(fps) if int(fps) in (24, 25, 30, 60) else 30
    duration = min(max(float(duration), 2.0), 20.0)
    frames = int(duration * fps)

    bgc, ca, cb = THEMES.get(theme, THEMES["gold"])
    cp, cac, cbg = _hex_rgb(color_primary), _hex_rgb(color_accent), _hex_rgb(color_bg)
    colors = (cbg or bgc, cp or ca, cac or cb)

    if art_scale is None:
        art_wf, art_hf = 0.80, 0.80
    elif isinstance(art_scale, (tuple, list)) and len(art_scale) == 2:
        art_wf, art_hf = float(art_scale[0]), float(art_scale[1])
    else:
        art_wf = art_hf = 0.80 * float(art_scale)
    base_img = _load_image(image_path) if kind not in (
        "img-breathing", "img-orbit", "img-sweep", "img-parallax", "img-kenburns") else None
    art_img = _load_image(image_path) if kind.startswith("img-") else None
    logo_img = _load_image(logo_path)
    ctx = _Ctx(kind, ow, oh, theme, colors, text, subtext, base_img, logo_img,
               art_img, speed=speed, intensity=intensity, ss=ss,
               art_motion=art_motion or "none",
               art_w_frac=art_wf, art_h_frac=art_hf)

    ff = shutil.which("ffmpeg")
    if not ff:
        raise RuntimeError("FFmpeg not found.")
    enc = ["-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p",
           "-preset", "medium", "-movflags", "+faststart"]
    if str(quality).upper() == "4K" and not preview:
        # 4K size targeting: keep a 5–10 s clip under ~90 MB.
        # maxrate (kbps) = 85 MB * 8192 kbit/MB / duration_s * 0.92 headroom
        maxrate = int(85 * 8192 / duration * 0.92)
        enc += ["-crf", "20", "-maxrate", f"{maxrate}k", "-bufsize", f"{maxrate * 2}k"]
    else:
        enc += ["-crf", "18"]
    cmd = [ff, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
           "-pix_fmt", "rgb24", "-s", f"{ow}x{oh}", "-r", str(fps), "-i", "-", "-an",
           *enc, dst]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE)
    try:
        for i in range(frames):
            frame = _frame(ctx, i, frames)
            if ctx.ss != 1.0:
                frame = frame.resize((ow, oh), Image.LANCZOS)
            proc.stdin.write(frame.convert("RGB").tobytes())
            if progress_cb and i % 10 == 0:
                progress_cb((i + 1) / frames, {"stage": "mgfx"})
        proc.stdin.close()
        err = proc.stderr.read().decode() if proc.stderr else ""
        rc = proc.wait(timeout=1800)
    except Exception:
        proc.kill(); raise
    if rc != 0 or not os.path.isfile(dst):
        raise RuntimeError("Motion graphics render failed: " + (err or "")[:200])
    if progress_cb:
        progress_cb(1.0, {"stage": "done"})
    meta = {"kind": kind, "label": CATALOG[kind]["label"],
            "category": CATALOG[kind]["category"], "theme": theme,
            "width": ow, "height": oh, "ratio": ratio, "fps": fps,
            "duration": round(duration, 1), "quality": "PREVIEW" if preview else str(quality).upper(),
            "speed": ctx.speed, "format": fmt,
            "art_motion": ctx.art_motion,
            "art_scale": [ctx.art_w_frac, ctx.art_h_frac],
            "size_mb": round(os.path.getsize(dst) / 1048576, 2)}
    meta["stock_check"] = _ffprobe_check(dst, ow, oh, fps, duration)
    return meta


# ------------------------------------------------- v5 compatibility aliases
# backend/promo.py imports these names from v5 mgfx — keep them working.
def _font(size, bold=True):
    return get_font(size, "display" if bold else "sans")


def _ease(x):
    return ease_out(x)
