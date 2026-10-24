"""
Promo Maker (Phase 5) — slideshow promo templates for product photos +
prices. Business/social commerce promos are among the highest-demand
stock & SMB video formats. 100% local, free, no watermark.

Templates:
  sale-hero   : split screen — animated text panel (headline, product,
                price + old price, CTA) beside a slow-zoom product photo,
                with a rotating starburst price badge.
  catalog     : sequence of product slides (photo top, name+price band),
                crossfaded — for menus, ranges, real-estate, portfolios.
  social-ad   : full-frame photo, dark gradient, headline, starburst
                price badge, pulsing CTA — built for 9:16 / 1:1.

Inputs: product images + [{name, price, old_price}], headline, cta,
theme, ratio. Output H.264 MP4 + faststart.
"""

import math
import os
import shutil
import subprocess

from PIL import Image, ImageDraw, ImageFilter

from .mgfx import THEMES, _font, _text_size, _ease

RESOLUTIONS = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080), "4:5": (1080, 1350)}
TEMPLATES = {"sale-hero", "catalog", "social-ad"}


def _cover_anim(img, w, h, anim, t, amt=0.10):
    """Photo motion styles for promo templates (v5 pro controls)."""
    if anim == "zoom-out":
        return _cover(img, w, h, zoom=1.0 + amt * (1 - t))
    if anim == "pan":
        base = _cover(img, w, h, zoom=1.0 + amt)
        from PIL import Image as _Im
        canvas = _Im.new("RGB", (w, h))
        off = int((t - 0.5) * w * 0.03)
        canvas.paste(base, (off, 0))
        if off > 0:
            canvas.paste(base.crop((0, 0, off, h)), (0, 0))
        return canvas
    if anim == "static":
        return _cover(img, w, h, zoom=1.0 + amt * 0.4)
    return _cover(img, w, h, zoom=1.0 + amt * t)  # zoom-in (default)


def _cover(img, w, h, zoom=1.0):
    img = img.convert("RGB")
    s = max(w / img.width, h / img.height) * zoom
    img = img.resize((max(w, int(img.width * s + 0.5)), max(h, int(img.height * s + 0.5))))
    x, y = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))


def _starburst(d, cx, cy, r, rot, fill):
    pts = []
    for i in range(24):
        ang = rot + i * math.pi / 12
        rr = r if i % 2 == 0 else r * 0.82
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    d.polygon(pts, fill=fill)


def _wrap(draw, text, font, max_w, max_lines=3):
    words, lines, cur = (text or "").split(), [], ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if _text_size(draw, trial, font)[0] <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur); cur = wd
        if len(lines) >= max_lines:
            break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    return lines


def _frame_hero(ctx, p, t):
    """p = progress within this template (0..1 across whole video)."""
    w, h = ctx["w"], ctx["h"]
    bg, pri, acc = ctx["theme"]
    img = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(img, "RGBA")
    prod = ctx["products"][0]
    photo = prod["img"]
    pw = int(w * (0.52 if w >= h else 1.0))
    ph = h if w >= h else int(h * 0.52)
    zoomed = _cover_anim(photo, pw, ph, ctx.get("anim", "zoom-in"), t, 0.10)
    if w >= h:
        img.paste(zoomed, (w - pw, 0)); tx = w * 0.05; tw_ = w - pw - w * 0.09; ty = h * 0.16
    else:
        img.paste(zoomed, (0, 0)); tx = w * 0.06; tw_ = w * 0.88; ty = ph + h * 0.05
    a_in = _ease(min(t / 0.25, 1))
    if ctx.get("brand"):
        fb2 = _font(h * 0.028)
        bx = (w - pw + w * 0.02) if w >= h else w * 0.03
        d.text((bx + 2, h * 0.022 + 2), ctx["brand"], font=fb2, fill=(0, 0, 0, 160))
        d.text((bx, h * 0.022), ctx["brand"], font=fb2, fill=(255, 255, 255, 235))
    slide = (1 - a_in) * w * 0.04
    if ctx["headline"]:
        f = _font(h * 0.052)
        for i, line in enumerate(_wrap(d, ctx["headline"], f, tw_)):
            d.text((tx - slide, ty + i * h * 0.065), line, font=f, fill=(255, 255, 255, int(255 * a_in)))
        ty += h * 0.065 * len(_wrap(d, ctx["headline"], f, tw_)) + h * 0.03
    if prod["name"]:
        f = _font(h * 0.036, bold=False)
        d.text((tx - slide, ty), prod["name"], font=f, fill=acc + (int(230 * a_in),)); ty += h * 0.06
    if prod["price"]:
        f = _font(h * 0.085)
        d.text((tx - slide, ty), prod["price"], font=f, fill=pri + (255,))
        pw_text = _text_size(d, prod["price"], f)[0]
        if prod.get("old_price"):
            f2 = _font(h * 0.042, bold=False)
            ox = tx + pw_text + w * 0.02
            d.text((ox, ty + h * 0.032), prod["old_price"], font=f2, fill=(200, 200, 200, 220))
            ow = _text_size(d, prod["old_price"], f2)[0]
            d.line([ox, ty + h * 0.055, ox + ow, ty + h * 0.055], fill=(255, 90, 90, 255), width=max(3, h // 200))
        if not ctx.get("show_badge", True):
            pass
        else:
          # rotating starburst badge near photo edge
          bcx = (w - pw - w * 0.015) if w >= h else (w * 0.85)
          bcy = h * 0.16 if w >= h else ph * 0.88
          pop = _ease(min(max(0, t - 0.2) / 0.25, 1)) * (1 + 0.05 * math.sin(t * 12))
          _starburst(d, bcx, bcy, h * 0.085 * pop, t * 0.8, (225, 45, 60, 255))
          fb = _font(h * 0.030)
          s = ctx.get("badge_text", "SALE")
        sw, sh = _text_size(d, s, fb)
        d.text((bcx - sw / 2, bcy - sh / 2), s, font=fb, fill=(255, 255, 255, 255))
    if ctx["cta"]:
        f = _font(h * 0.034)
        cw, chh = _text_size(d, ctx["cta"], f)
        pad = w * 0.02
        y0 = h * 0.86 if w >= h else h * 0.90
        pulse = 1 + 0.02 * math.sin(t * 6.28 * 2) * (1 if t > 0.7 else 0)
        bw_, bh_ = (cw + pad * 2) * pulse, (chh + h * 0.03) * pulse
        d.rounded_rectangle([tx, y0, tx + bw_, y0 + bh_], radius=bh_ / 2, fill=pri + (255,))
        d.text((tx + (bw_ - cw) / 2, y0 + (bh_ - chh) / 2 - 2), ctx["cta"], font=f, fill=(255, 255, 255, 255))
    return img


def _frame_catalog_slide(ctx, prod, lt):
    w, h = ctx["w"], ctx["h"]
    bg, pri, acc = ctx["theme"]
    img = _cover_anim(prod["img"], w, h, ctx.get("anim", "zoom-in"), lt, 0.07)
    band_h = int(h * 0.20)
    band_top = ctx.get("band", "bottom") == "top"
    by0 = 0 if band_top else h - band_h
    band = Image.new("RGB", (w, band_h), bg)
    img.paste(band, (0, by0))
    d = ImageDraw.Draw(img, "RGBA")
    a = _ease(min(lt / 0.3, 1))
    if prod["name"]:
        f = _font(h * 0.048)
        d.text((w * 0.05, by0 + band_h * 0.16), prod["name"], font=f,
               fill=(255, 255, 255, int(255 * a)))
    if prod["price"]:
        f = _font(h * 0.052)
        tw = _text_size(d, prod["price"], f)[0]
        d.text((w - tw - w * 0.05, by0 + band_h * 0.13), prod["price"], font=f, fill=pri + (255,))
        if prod.get("old_price"):
            f2 = _font(h * 0.032, bold=False)
            ow = _text_size(d, prod["old_price"], f2)[0]
            ox = w - tw - w * 0.05 - ow - w * 0.02
            d.text((ox, by0 + band_h * 0.24), prod["old_price"], font=f2, fill=(190, 190, 190, 255))
            d.line([ox, by0 + band_h * 0.38, ox + ow, by0 + band_h * 0.38],
                   fill=(255, 90, 90, 255), width=max(3, h // 220))
    if ctx.get("brand"):
        fb3 = _font(h * 0.024, bold=False)
        bw3 = _text_size(d, ctx["brand"], fb3)[0]
        d.text((w - bw3 - w * 0.05, by0 + band_h * 0.62), ctx["brand"], font=fb3,
               fill=(255, 255, 255, int(200 * a)))
    return img


def _frame_social(ctx, p, t):
    w, h = ctx["w"], ctx["h"]
    bg, pri, acc = ctx["theme"]
    prod = ctx["products"][0]
    img = _cover_anim(prod["img"], w, h, ctx.get("anim", "zoom-in"), t, 0.09)
    grad = Image.new("L", (1, h), 0)
    for yy in range(h):
        grad.putpixel((0, yy), int(200 * max(0, (yy / h - 0.45) / 0.55)))
    img = Image.composite(Image.new("RGB", (w, h), (0, 0, 0)), img, grad.resize((w, h)))
    d = ImageDraw.Draw(img, "RGBA")
    a = _ease(min(t / 0.25, 1)) * (1 - _ease(max(0, (t - 0.92) / 0.08)))
    y = h * 0.66
    if ctx["headline"]:
        f = _font(h * 0.055)
        for line in _wrap(d, ctx["headline"], f, w * 0.86):
            tw = _text_size(d, line, f)[0]
            d.text(((w - tw) / 2, y), line, font=f, fill=(255, 255, 255, int(255 * a))); y += h * 0.068
    if prod["name"]:
        f = _font(h * 0.034, bold=False)
        tw = _text_size(d, prod["name"], f)[0]
        d.text(((w - tw) / 2, y + h * 0.01), prod["name"], font=f, fill=acc + (int(230 * a),))
    if prod["price"]:
        bcx, bcy = w * 0.84, h * 0.13
        pop = _ease(min(t / 0.3, 1)) * (1 + 0.04 * math.sin(t * 10))
        _starburst(d, bcx, bcy, h * 0.075 * pop, t * 0.7, (225, 45, 60, 255))
        f = _font(h * 0.034)
        tw, th = _text_size(d, prod["price"], f)
        d.text((bcx - tw / 2, bcy - th / 2), prod["price"], font=f, fill=(255, 255, 255, 255))
    if ctx["cta"]:
        f = _font(h * 0.036)
        cw, chh = _text_size(d, ctx["cta"], f)
        bw_, bh_ = cw + w * 0.10, chh + h * 0.028
        x0, y0 = (w - bw_) / 2, h * 0.885
        d.rounded_rectangle([x0, y0, x0 + bw_, y0 + bh_], radius=bh_ / 2, fill=pri + (int(255 * a),))
        d.text(((w - cw) / 2, y0 + (bh_ - chh) / 2 - 2), ctx["cta"], font=f, fill=(255, 255, 255, int(255 * a)))
    return img


def _frame_endcard(ctx, lt):
    w, h = ctx["w"], ctx["h"]
    bg, pri, acc = ctx["theme"]
    img = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(img, "RGBA")
    a = _ease(min(lt / 0.3, 1))
    main = ctx.get("brand") or ctx["headline"] or "Thank You"
    f = _font(h * 0.075)
    tw, th = _text_size(d, main, f)
    d.text(((w - tw) / 2, h * 0.36), main, font=f, fill=(255, 255, 255, int(255 * a)))
    sub = ctx["headline"] if ctx.get("brand") else ""
    if sub:
        f2 = _font(h * 0.038, bold=False)
        tw2, _ = _text_size(d, sub, f2)
        d.text(((w - tw2) / 2, h * 0.36 + th + h * 0.03), sub, font=f2, fill=acc + (int(230 * a),))
    if ctx["cta"]:
        f3 = _font(h * 0.040)
        cw, chh = _text_size(d, ctx["cta"], f3)
        bw_, bh_ = cw + w * 0.08, chh + h * 0.03
        x0, y0 = (w - bw_) / 2, h * 0.62
        d.rounded_rectangle([x0, y0, x0 + bw_, y0 + bh_], radius=bh_ / 2, fill=pri + (int(255 * a),))
        d.text(((w - cw) / 2, y0 + (bh_ - chh) / 2 - 2), ctx["cta"], font=f3, fill=(255, 255, 255, int(255 * a)))
    return img


def _create_promo_legacy(image_paths, products, dst, *, template="sale-hero", headline="",
                 cta="", theme="crimson", ratio="16:9", per_slide=3.5, fps=30,
                 badge_text="SALE", show_badge=True, brand_text="", anim="zoom-in",
                 band="bottom", end_card=False, audio_path=None, progress_cb=None):
    if template not in TEMPLATES:
        raise ValueError(f"Unknown promo template '{template}'.")
    if not image_paths:
        raise ValueError("Upload at least one product photo.")
    w, h = RESOLUTIONS.get(ratio, RESOLUTIONS["16:9"])
    prods = []
    for i, pth in enumerate(image_paths[:6]):
        meta = products[i] if i < len(products) else {}
        prods.append({"img": Image.open(pth), "name": meta.get("name", ""),
                      "price": meta.get("price", ""), "old_price": meta.get("old_price", "")})
    ctx = {"w": w, "h": h, "theme": THEMES.get(theme, THEMES["crimson"]),
           "products": prods, "headline": headline, "cta": cta,
           "badge_text": (badge_text or "SALE")[:12], "show_badge": bool(show_badge),
           "brand": (brand_text or "")[:40], "anim": anim if anim in
           ("zoom-in", "zoom-out", "pan", "static") else "zoom-in",
           "band": "top" if band == "top" else "bottom"}
    fps = int(fps) if int(fps) in (24, 25, 30) else 30
    if template == "catalog":
        total_dur = per_slide * len(prods)
    else:
        total_dur = max(per_slide, 3.0)
    end_secs = 2.0 if end_card else 0.0
    frames = int((total_dur + end_secs) * fps)
    ff = shutil.which("ffmpeg")
    if not ff:
        raise RuntimeError("FFmpeg not found.")
    cmd = [ff, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
           "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-", "-an",
           "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", dst]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE)
    fade = 0.4
    try:
        prev = None
        for i in range(frames):
            tsec = i / fps
            if end_secs and tsec >= total_dur:
                frame = _frame_endcard(ctx, (tsec - total_dur) / end_secs)
            elif template == "sale-hero":
                frame = _frame_hero(ctx, None, tsec / total_dur)
            elif template == "social-ad":
                frame = _frame_social(ctx, None, tsec / total_dur)
            else:
                idx = min(int(tsec / per_slide), len(prods) - 1)
                lt = (tsec - idx * per_slide) / per_slide
                frame = _frame_catalog_slide(ctx, prods[idx], lt)
                # crossfade into next slide
                since_boundary = per_slide - (tsec - idx * per_slide)
                if idx < len(prods) - 1 and since_boundary < fade:
                    nxt = _frame_catalog_slide(ctx, prods[idx + 1], 0.0)
                    frame = Image.blend(frame, nxt, 1 - since_boundary / fade)
            proc.stdin.write(frame.tobytes())
            if progress_cb and i % 15 == 0:
                progress_cb((i + 1) / frames, {"stage": "promo"})
        proc.stdin.close()
        err = proc.stderr.read().decode() if proc.stderr else ""
        rc = proc.wait(timeout=900)
    except Exception:
        proc.kill(); raise
    if rc != 0 or not os.path.isfile(dst):
        raise RuntimeError("Promo render failed: " + (err or "")[:300])
    if audio_path and os.path.isfile(audio_path):
        tot = total_dur + end_secs
        tmp = dst + ".mus.mp4"
        r = subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-y", "-i", dst,
                            "-stream_loop", "-1", "-i", audio_path, "-t", str(tot),
                            "-af", f"afade=t=out:st={max(tot - 1.2, 0):.2f}:d=1.2,volume=0.9",
                            "-c:v", "copy", "-c:a", "aac", "-shortest", tmp],
                           capture_output=True, text=True, timeout=600)
        if r.returncode == 0 and os.path.isfile(tmp):
            os.replace(tmp, dst)
    if progress_cb:
        progress_cb(1.0, {"stage": "done"})
    return {"template": template, "width": w, "height": h, "ratio": ratio, "fps": fps,
            "duration": round(total_dur + end_secs, 1), "products": len(prods),
            "end_card": bool(end_card), "music": bool(audio_path),
            "size_mb": round(os.path.getsize(dst) / 1048576, 2)}


# ================================================================ v9 engine
# Scene model: a promo = ordered list of scenes; each scene =
# {img, imgs, name, price, old_price, headline, subtext, bullets,
#  duration, transition, voiceover_line, on_screen_text}.
# All v9 renderers consume scenes. The legacy path above is untouched and
# still serves plain pre-v9 calls (see create_promo wrapper at the bottom).
import json as _json

from PIL import Image as _Image

from .mgfx import (get_font as _get_font, ease_in_out as _eio,
                   ease_out_back as _eob, ease_out_elastic as _eoe,
                   _hex_rgb as _hex, _mix as _mixc, _vgrad as _vgrad,
                   RESOLUTIONS_4K as _RES4K, RESOLUTIONS_PREVIEW as _RESPREV,
                   _ffprobe_check as _probe_check)
from . import promo_audio as _paudio

LEGACY_TEMPLATES = {"sale-hero", "catalog", "social-ad"}

TEMPLATE_INFO = {
    "sale-hero": {"label": "Sale Hero", "category": "Sales",
                  "ratios": ["16:9", "9:16", "1:1", "4:5"],
                  "fields": ["photo", "product", "price", "headline", "cta", "badge"]},
    "catalog": {"label": "Catalog Slides", "category": "E-commerce",
                "ratios": ["16:9", "9:16", "1:1", "4:5"],
                "fields": ["photos", "products", "prices", "band"]},
    "social-ad": {"label": "Social Ad", "category": "Social",
                  "ratios": ["9:16", "1:1", "4:5", "16:9"],
                  "fields": ["photo", "price", "headline", "cta"]},
    "product-showcase": {"label": "Product Showcase", "category": "E-commerce",
                         "ratios": ["16:9", "1:1", "9:16", "4:5"],
                         "fields": ["photo", "product", "price", "bullets", "badge"]},
    "flash-sale-countdown": {"label": "Flash Sale Countdown", "category": "Sales",
                             "ratios": ["16:9", "9:16", "1:1"],
                             "fields": ["photo", "price", "headline", "countdown"]},
    "testimonial": {"label": "Testimonial / Review", "category": "Social",
                    "ratios": ["16:9", "1:1", "9:16"],
                    "fields": ["quote", "customer name", "photo (optional)"]},
    "before-after": {"label": "Before / After", "category": "E-commerce",
                     "ratios": ["16:9", "1:1", "9:16"],
                     "fields": ["two photos", "labels"]},
    "compare": {"label": "Compare Two Products", "category": "E-commerce",
                "ratios": ["16:9", "1:1"],
                "fields": ["two products", "prices", "headline"]},
    "real-estate": {"label": "Real Estate Tour", "category": "Real Estate",
                    "ratios": ["16:9", "4:5", "1:1"],
                    "fields": ["photos", "address", "price", "beds/baths info"]},
    "restaurant-menu": {"label": "Restaurant Menu", "category": "Food",
                        "ratios": ["16:9", "4:5", "1:1", "9:16"],
                        "fields": ["dish photos", "dish names", "prices"]},
    "event-sale": {"label": "Event / Seasonal Sale", "category": "Events",
                   "ratios": ["16:9", "9:16", "1:1", "4:5"],
                   "fields": ["headline", "date line", "photo (optional)"]},
    "app-promo": {"label": "App Promo — Device Mockup", "category": "App",
                  "ratios": ["16:9", "9:16", "1:1"],
                  "fields": ["app screenshots", "device", "headline", "badge"]},
    "audiogram": {"label": "Audiogram", "category": "Audio",
                  "ratios": ["1:1", "16:9", "9:16"],
                  "fields": ["image", "audio (voice/music)", "headline"]},
}
TEMPLATES = set(TEMPLATE_INFO) | LEGACY_TEMPLATES
TEXT_STYLES = ("classic", "pop-out", "ribbon", "highlight", "fade-up",
               "slide-in", "backdrop", "center-stage", "typewriter")
FONT_ROLES = ("display", "serif", "sans-bold", "sans")
OUTROS = ("none", "simple", "website", "classic")
TRANSITIONS = ("fade", "slide", "zoom", "wipe", "none")


def _promo_res(ratio, quality):
    if quality == "preview":
        return _RESPREV.get(ratio, _RESPREV["16:9"])
    if quality == "4K":
        return _RES4K.get(ratio, _RES4K["16:9"])
    w, h = RESOLUTIONS.get(ratio, RESOLUTIONS["16:9"])
    if quality == "720p" and min(w, h) > 720:
        f = 720 / min(w, h)
        return (int(w * f) // 2 * 2, int(h * f) // 2 * 2)
    return (w, h)


def _rgba(hex_or_tuple, alpha=255):
    if hex_or_tuple is None:
        return None
    if isinstance(hex_or_tuple, str):
        c = _hex(hex_or_tuple)
    else:
        c = tuple(hex_or_tuple)[:3]
    return c + (alpha,)


def _fit_font(draw, text, role, size, max_w, min_size=10):
    size = int(max(size, min_size))
    while size > min_size:
        f = _get_font(size, role)
        if _text_size(draw, text, f)[0] <= max_w:
            return f
        size = int(size * 0.9)
    return _get_font(min_size, role)


def _center_text(d, cx, y, text, font, fill, stroke_w=0, stroke_fill=(0, 0, 0)):
    tw, th = _text_size(d, text, font)
    d.text((cx - tw / 2, y), text, font=font, fill=fill,
           stroke_width=stroke_w, stroke_fill=stroke_fill)
    return th


def _styled_headline(img, text, cx, y, ctx, lt, max_w, size=None, align="center"):
    """Draw the scene headline with the chosen Part-B text style.
    Returns the height consumed."""
    if not text:
        return 0
    w, h = ctx["w"], ctx["h"]
    style = ctx.get("text_style", "classic")
    role = ctx.get("font_role", "display")
    base_size = size or h * 0.058 * ctx.get("headline_scale", 1.0)
    tcol = ctx.get("text_color", (255, 255, 255))
    acc = ctx["theme"][1]
    d = ImageDraw.Draw(img, "RGBA")
    p = _clamp01(lt / 0.35)  # entrance progress
    lines = []
    probe = _get_font(int(base_size), role)
    for raw in str(text).split("\n"):
        lines += _wrap(d, raw, probe, max_w, 3)
    line_h = base_size * 1.22
    total_h = line_h * len(lines)

    if style == "typewriter":
        full = " ".join(lines)
        n = int(len(full) * _clamp01(lt / 0.6))
        shown = full[:n]
        f = _fit_font(d, shown or " ", role, base_size, max_w)
        _center_text(d, cx, y, shown, f, tcol + (255,))
        return line_h
    if style == "pop-out":
        layer = _Image.new("RGBA", (w, int(total_h + base_size)), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        for i, ln in enumerate(lines):
            f = _fit_font(ld, ln, role, base_size, max_w)
            _center_text(ld, w / 2, i * line_h, ln, f, tcol + (255,))
        s = 0.6 + 0.4 * _eob(p)
        nw, nh = int(w * s), int(layer.height * s)
        layer = layer.resize((nw, nh), _Image.LANCZOS)
        img.alpha_composite(layer, (int(cx - nw / 2), int(y))) if img.mode == "RGBA" \
            else img.paste(layer, (int(cx - nw / 2), int(y)), layer)
        return total_h
    if style == "center-stage":
        for i, ln in enumerate(lines):
            f = _fit_font(d, ln, role, base_size, max_w)
            tw = _text_size(d, ln, f)[0]
            x = cx - tw / 2
            n = len(ln)
            for j, ch in enumerate(ln):
                lp = _clamp01((lt - j * 0.03) / 0.3)
                if lp <= 0:
                    continue
                cw = _text_size(d, ch, f)[0]
                d.text((x, y + i * line_h + (1 - lp) * h * 0.02), ch, font=f,
                       fill=tcol + (int(255 * lp),))
                x += cw
        return total_h
    # block styles share layout; per-style decoration/offset
    xoff, alpha = 0, 255
    if style == "fade-up":
        alpha = int(255 * p)
        y += (1 - _ease(p)) * h * 0.03
    elif style == "slide-in":
        xoff = -(1 - _ease(p)) * w * 0.06
    if style == "ribbon":
        rib = _Image.new("RGBA", (int(max_w * 1.04), int(total_h + base_size * 0.5)),
                         (0, 0, 0, 0))
        rd = ImageDraw.Draw(rib)
        rd.polygon([(0, rib.height * 0.18), (rib.width, 0),
                    (rib.width, rib.height * 0.82), (0, rib.height)],
                   fill=acc + (255,))
        for i, ln in enumerate(lines):
            f = _fit_font(rd, ln, role, base_size, max_w)
            _center_text(rd, rib.width / 2, rib.height * 0.22 + i * line_h, ln, f,
                         (20, 16, 10, 255) if _lum(acc) > 140 else (255, 255, 255, 255))
        rib = rib.rotate(0, resample=_Image.BICUBIC)  # kept flat for readability
        px, py = int(cx - rib.width / 2), int(y - base_size * 0.22)
        if img.mode == "RGBA":
            img.alpha_composite(rib, (px, py))
        else:
            img.paste(rib, (px, py), rib)
        return total_h
    if style == "backdrop":
        pad = base_size * 0.45
        bw = min(max_w, max((_text_size(d, ln, _fit_font(d, ln, role, base_size, max_w))[0]
                             for ln in lines), default=0) + pad * 2)
        d.rounded_rectangle([cx - bw / 2, y - pad * 0.5, cx + bw / 2,
                             y + total_h + pad * 0.4],
                            radius=base_size * 0.3, fill=(5, 5, 10, 165))
    if style == "highlight":
        hl = ctx.get("highlight_color", acc)
        for i, ln in enumerate(lines):
            f = _fit_font(d, ln, role, base_size, max_w)
            tw = _text_size(d, ln, f)[0]
            grow = _clamp01((lt - i * 0.08) / 0.35)
            d.rectangle([cx - tw / 2 - 8, y + i * line_h + base_size * 0.12,
                         cx - tw / 2 - 8 + (tw + 16) * grow,
                         y + i * line_h + base_size * 1.02], fill=hl + (235,))
    for i, ln in enumerate(lines):
        f = _fit_font(d, ln, role, base_size, max_w)
        fill = tcol + (alpha,)
        if style == "highlight" and _lum(ctx.get("highlight_color", acc)) > 140:
            fill = (15, 12, 8, alpha)
        if align == "left":
            d.text((cx + xoff, y + i * line_h), ln, font=f, fill=fill)
        else:
            _center_text(d, cx + xoff, y + i * line_h, ln, f, fill)
    return total_h


def _clamp01(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def _lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def _price_row(d, cx, y, scene, ctx, lt=1.0):
    h = ctx["h"]
    pri = ctx["theme"][1]
    if not scene.get("price"):
        return 0
    f = _fit_font(d, scene["price"], "display", h * 0.075, ctx["w"] * 0.6)
    tw = _text_size(d, scene["price"], f)[0]
    total = tw
    ow = 0
    f2 = None
    if scene.get("old_price"):
        f2 = _get_font(int(h * 0.038), "sans")
        ow = _text_size(d, scene["old_price"], f2)[0] + ctx["w"] * 0.015
        total += ow
    x = cx - total / 2
    d.text((x, y), scene["price"], font=f, fill=pri + (255,))
    if f2:
        ox = x + tw + ctx["w"] * 0.015
        d.text((ox, y + h * 0.02), scene["old_price"], font=f2, fill=(205, 205, 205, 255))
        d.line([ox, y + h * 0.038, ox + ow - ctx["w"] * 0.015, y + h * 0.038],
               fill=(255, 90, 90, 255), width=max(3, h // 200))
    return h * 0.085


def _cta_pill(d, cx, y, text, ctx, tsec=0.0):
    if not text:
        return 0
    w, h = ctx["w"], ctx["h"]
    pri = ctx["theme"][1]
    f = _get_font(int(h * 0.036), "sans-bold")
    cw, chh = _text_size(d, text, f)
    pulse = 1 + 0.02 * math.sin(tsec * 6.28)
    bw_, bh_ = (cw + w * 0.055) * pulse, (chh + h * 0.026) * pulse
    d.rounded_rectangle([cx - bw_ / 2, y, cx + bw_ / 2, y + bh_], radius=bh_ / 2,
                        fill=pri + (255,))
    d.text((cx - cw / 2, y + (bh_ - chh) / 2 - 2), text, font=f,
           fill=(15, 12, 8, 255) if _lum(pri) > 150 else (255, 255, 255, 255))
    return bh_


def _chip(d, x, y, text, ctx, fill=None):
    h = ctx["h"]
    f = _get_font(int(h * 0.026), "sans-bold")
    tw, th = _text_size(d, text, f)
    pad = h * 0.014
    d.rounded_rectangle([x, y, x + tw + pad * 2, y + th + pad * 1.1],
                        radius=(th + pad) / 2, fill=fill or ctx["theme"][1] + (255,))
    d.text((x + pad, y + pad * 0.5), text, font=f, fill=(255, 255, 255, 255))
    return tw + pad * 2


def _star(d, cx, cy, r, fill):
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    d.polygon(pts, fill=fill)


def _darken(img, frac=0.45):
    black = _Image.new(img.mode, img.size, (0, 0, 0) if img.mode == "RGB" else (0, 0, 0, 255))
    return _Image.blend(img, black, frac)


# ------------------------------------------------------------ scene model
def _load_products(image_paths, products, limit=12):
    prods = []
    for i, pth in enumerate(image_paths[:limit]):
        meta = dict(products[i]) if i < len(products) else {}
        img = None
        if pth:
            try:
                img = Image.open(pth)
                img.load()
            except Exception:  # noqa: BLE001
                img = None
        prods.append({"img": img, "name": meta.get("name", ""),
                      "price": meta.get("price", ""),
                      "old_price": meta.get("old_price", ""),
                      "info": meta.get("info", ""),
                      "features": meta.get("features") or [],
                      "meta": meta})
    return prods


def _norm_scene(raw, prods, per_slide, idx=0):
    raw = raw or {}
    img = None
    pmeta = {}
    ii = raw.get("image_index", raw.get("product_index"))
    if isinstance(ii, int) and 0 <= ii < len(prods):
        img = prods[ii]["img"]
        pmeta = prods[ii]
    elif raw.get("image") and os.path.isfile(raw["image"]):
        try:
            img = Image.open(raw["image"])
            img.load()
        except Exception:  # noqa: BLE001
            img = None
    if img is None and prods and idx < len(prods):
        img = prods[idx]["img"]
        pmeta = prods[idx]
    try:
        dur = float(raw.get("duration") or per_slide)
    except (TypeError, ValueError):
        dur = per_slide
    trans = raw.get("transition") or "fade"
    return {"img": img,
            "name": raw.get("name", pmeta.get("name", "")),
            "price": raw.get("price", pmeta.get("price", "")),
            "old_price": raw.get("old_price", pmeta.get("old_price", "")),
            "info": raw.get("info", pmeta.get("info", "")),
            "headline": raw.get("headline", raw.get("on_screen_text", "")),
            "subtext": raw.get("subtext", ""),
            "bullets": raw.get("bullets") or pmeta.get("features") or [],
            "duration": min(max(dur, 0.8), 30.0),
            "transition": trans if trans in TRANSITIONS else "fade",
            "voiceover_line": raw.get("voiceover_line", ""),
            "on_screen_text": raw.get("on_screen_text", raw.get("headline", ""))}


def _default_scenes(template, prods, headline, cta, features, per_slide):
    def sc(i=0, **kw):
        base = {"image_index": i if i < len(prods) else None}
        base.update(kw)
        return _norm_scene(base, prods, per_slide, i)

    first = prods[0] if prods else {"name": "", "price": "", "old_price": ""}
    if template in ("catalog", "restaurant-menu", "real-estate"):
        return [sc(i, headline=headline if i == 0 else "") for i in range(len(prods))] or [sc(0)]
    if template == "product-showcase":
        feats = features or first.get("features") or []
        return [sc(0, headline=headline, bullets=list(feats)[:5])]
    if template == "testimonial":
        return [sc(0, headline=headline, subtext="")]
    if template in ("before-after", "compare"):
        return [sc(0, headline=headline)]
    if template == "app-promo":
        return [sc(0, headline=headline)]
    # single-scene templates
    return [sc(0, headline=headline)]


# ------------------------------------------------------------ renderers
def _legacy_shim(ctx, scene):
    prod = {"img": scene["img"], "name": scene["name"], "price": scene["price"],
            "old_price": scene["old_price"]}
    return {"w": ctx["w"], "h": ctx["h"], "theme": ctx["theme"],
            "products": [prod], "headline": ctx["headline"], "cta": ctx["cta"],
            "badge_text": ctx["badge_text"], "show_badge": ctx["show_badge"],
            "brand": ctx["brand"], "anim": ctx["anim"], "band": ctx["band"]}


def _sc_sale_hero(ctx, scene, lt, tsec):
    return _frame_hero(_legacy_shim(ctx, scene), None, lt).convert("RGBA")


def _sc_social(ctx, scene, lt, tsec):
    return _frame_social(_legacy_shim(ctx, scene), None, lt).convert("RGBA")


def _sc_catalog(ctx, scene, lt, tsec):
    return _frame_catalog_slide(_legacy_shim(ctx, scene),
                                {"img": scene["img"], "name": scene["name"],
                                 "price": scene["price"],
                                 "old_price": scene["old_price"]}, lt).convert("RGBA")


def _sc_restaurant(ctx, scene, lt, tsec):
    w, h = ctx["w"], ctx["h"]
    if scene["img"] is not None:
        img = _cover_anim(scene["img"], w, h, ctx["anim"], lt, 0.06)
    else:
        img = _Image.new("RGB", (w, h), (43, 26, 12))
    warm = _Image.new("RGB", (w, h), (74, 38, 8))
    img = _Image.blend(img, warm, 0.22)
    img = img.convert("RGBA")
    d = ImageDraw.Draw(img, "RGBA")
    a = _ease(min(lt / 0.3, 1))
    band_h = int(h * 0.30)
    d.rectangle([0, h - band_h, w, h], fill=(26, 14, 6, 235))
    d.line([0, h - band_h, w, h - band_h], fill=ctx["theme"][1] + (255,), width=max(2, h // 300))
    f = _get_font(int(h * 0.030), "sans-bold")
    _center_text(d, w / 2, h - band_h + h * 0.025, "— MENU —", f, ctx["theme"][1] + (255,))
    if scene["name"]:
        f2 = _get_font(int(h * 0.052), "serif")
        _center_text(d, w / 2, h - band_h + h * 0.075, scene["name"], f2,
                     (255, 246, 230, int(255 * a)))
    if scene["price"]:
        f3 = _get_font(int(h * 0.048), "display")
        _center_text(d, w / 2, h - band_h + h * 0.165, scene["price"], f3,
                     ctx["theme"][1] + (255,))
    if scene.get("info"):
        f4 = _get_font(int(h * 0.028), "sans")
        _center_text(d, w / 2, h - band_h + h * 0.235, scene["info"], f4,
                     (235, 220, 200, 230))
    return img


def _sc_realestate(ctx, scene, lt, tsec):
    w, h = ctx["w"], ctx["h"]
    if scene["img"] is not None:
        img = _cover_anim(scene["img"], w, h, ctx["anim"], lt, 0.05).convert("RGBA")
    else:
        img = _vgrad(w, h, ctx["theme"][0], (10, 10, 14)).convert("RGBA")
    d = ImageDraw.Draw(img, "RGBA")
    a = _ease(min(lt / 0.3, 1))
    _chip(d, w * 0.045, h * 0.045, "FOR SALE", ctx)
    band_h = int(h * 0.235)
    grad = _Image.new("RGBA", (w, band_h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for yy in range(band_h):
        gd.line([0, yy, w, yy], fill=(4, 6, 10, int(215 * yy / band_h)))
    img.alpha_composite(grad, (0, h - band_h))
    y = h - band_h + h * 0.035
    addr = scene["name"] or scene["headline"]
    if addr:
        f = _fit_font(d, addr, "display", h * 0.05, w * 0.62)
        d.text((w * 0.05, y), addr, font=f, fill=(255, 255, 255, int(255 * a)))
    if scene["price"]:
        f = _get_font(int(h * 0.062), "display")
        tw = _text_size(d, scene["price"], f)[0]
        d.text((w - tw - w * 0.05, y - h * 0.01), scene["price"], font=f,
               fill=ctx["theme"][1] + (255,))
    if scene.get("info"):
        f = _get_font(int(h * 0.032), "sans")
        d.text((w * 0.05, y + h * 0.075), scene["info"], font=f,
               fill=(225, 232, 240, int(235 * a)))
    return img


def _sc_showcase(ctx, scene, lt, tsec):
    w, h = ctx["w"], ctx["h"]
    bg, pri, acc = ctx["theme"]
    img = _vgrad(w, h, bg, _mixc(bg, (0, 0, 0), 0.35)).convert("RGBA")
    d = ImageDraw.Draw(img, "RGBA")
    land = w >= h
    if scene["img"] is not None:
        pw = int(w * (0.46 if land else 0.8))
        ph = int(h * (0.8 if land else 0.42))
        photo = _cover_anim(scene["img"], pw, ph, ctx["anim"], lt, 0.07)
        px = int(w - pw - w * 0.04) if land else int(w * 0.1)
        py = int(h * 0.1) if land else int(h * 0.06)
        sh = _Image.new("RGBA", (pw + 24, ph + 24), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sh)
        sd.rounded_rectangle([12, 12, pw + 12, ph + 12], radius=22, fill=(0, 0, 0, 120))
        sh = sh.filter(ImageFilter.GaussianBlur(12))
        img.alpha_composite(sh, (px - 12, py - 12 + 8))
        img.paste(photo, (px, py))
        d = ImageDraw.Draw(img, "RGBA")
        if scene["price"]:
            bcx = px + pw * 0.06 if land else w * 0.85
            bcy = py + ph * 0.1 if land else py + ph * 0.92
            pop = _ease(min(lt / 0.3, 1)) * (1 + 0.04 * math.sin(tsec * 3))
            _starburst(d, bcx, bcy, h * 0.072 * pop, tsec * 0.5, (225, 45, 60, 255))
            f = _get_font(int(h * 0.030), "sans-bold")
            tw, th = _text_size(d, scene["price"], f)
            d.text((bcx - tw / 2, bcy - th / 2), scene["price"], font=f,
                   fill=(255, 255, 255, 255))
    tx = w * 0.055
    tw_ = w * (0.44 if land else 0.89)
    ty = h * (0.13 if land else 0.52)
    head = scene["headline"] or scene["name"]
    d = ImageDraw.Draw(img, "RGBA")
    if head:
        f = _fit_font(d, head, ctx["font_role"], h * 0.054 * ctx["headline_scale"], tw_)
        for i, ln in enumerate(_wrap(d, head, f, tw_, 2)):
            d.text((tx, ty + i * h * 0.062), ln, font=f, fill=ctx["text_color"] + (255,))
        ty += h * 0.062 * len(_wrap(d, head, f, tw_, 2)) + h * 0.03
    for i, b in enumerate(scene.get("bullets", [])[:5]):
        bp = _clamp01((lt - 0.15 - i * 0.14) / 0.25)
        if bp <= 0:
            continue
        f = _get_font(int(h * 0.034), "sans")
        by = ty + i * h * 0.055
        d.ellipse([tx, by + h * 0.006, tx + h * 0.026, by + h * 0.032],
                  fill=pri + (int(255 * bp),))
        d.text((tx + h * 0.005, by - h * 0.002), "✓", font=_get_font(int(h * 0.024), "sans-bold"),
               fill=(255, 255, 255, int(255 * bp)))
        d.text((tx + h * 0.042, by), str(b), font=f,
               fill=(240, 240, 240, int(255 * bp)))
    if not scene.get("bullets"):
        _price_row(d, tx + tw_ / 2, ty + h * 0.02, scene, ctx, lt)
    elif scene["price"]:
        f = _get_font(int(h * 0.05), "display")
        d.text((tx, ty + 5 * h * 0.055 + h * 0.01), scene["price"], font=f, fill=pri + (255,))
    if ctx["cta"]:
        _cta_pill(d, tx + tw_ / 2, h * 0.88, ctx["cta"], ctx, tsec)
    return img


def _sc_flashsale(ctx, scene, lt, tsec, gt):
    w, h = ctx["w"], ctx["h"]
    if scene["img"] is not None:
        img = _darken(_cover_anim(scene["img"], w, h, ctx["anim"], lt, 0.06), 0.45).convert("RGBA")
    else:
        img = _vgrad(w, h, ctx["theme"][0], (8, 4, 6)).convert("RGBA")
    d = ImageDraw.Draw(img, "RGBA")
    head = scene["headline"] or "FLASH SALE"
    _styled_headline(img, head, w / 2, h * 0.10, ctx, lt, w * 0.9,
                     size=h * 0.075 * ctx["headline_scale"])
    d = ImageDraw.Draw(img, "RGBA")
    remain = max(0.0, ctx.get("countdown_seconds", 600) - gt)
    hh = int(remain // 3600)
    mm = int((remain % 3600) // 60)
    ss = int(remain % 60)
    tstr = f"{hh:02d}:{mm:02d}:{ss:02d}" if hh else f"{mm:02d}:{ss:02d}"
    f = _get_font(int(h * 0.115), "display")
    tw, th = _text_size(d, tstr, f)
    pad = w * 0.03
    bx, by = (w - tw) / 2 - pad, h * 0.30
    d.rounded_rectangle([bx, by, bx + tw + pad * 2, by + th + h * 0.045],
                        radius=h * 0.02, fill=(0, 0, 0, 170),
                        outline=ctx["theme"][1] + (255,), width=max(2, h // 300))
    d.text(((w - tw) / 2, by + h * 0.02), tstr, font=f, fill=(255, 255, 255, 255))
    f2 = _get_font(int(h * 0.026), "sans-bold")
    _center_text(d, w / 2, by - h * 0.045, "OFFER ENDS IN", f2, ctx["theme"][2] + (255,))
    # urgency bar
    bw_ = w * 0.62
    frac = remain / max(ctx.get("countdown_seconds", 600), 1)
    uy = by + th + h * 0.085
    d.rounded_rectangle([(w - bw_) / 2, uy, (w + bw_) / 2, uy + h * 0.016],
                        radius=h * 0.008, fill=(255, 255, 255, 60))
    d.rounded_rectangle([(w - bw_) / 2, uy, (w - bw_) / 2 + bw_ * frac, uy + h * 0.016],
                        radius=h * 0.008, fill=(235, 60, 80, 255))
    _price_row(d, w / 2, h * 0.68, scene, ctx, lt)
    if scene["name"]:
        f3 = _get_font(int(h * 0.034), "sans")
        _center_text(d, w / 2, h * 0.635, scene["name"], f3, (240, 240, 240, 255))
    if ctx["cta"]:
        _cta_pill(d, w / 2, h * 0.85, ctx["cta"], ctx, tsec)
    return img


def _sc_testimonial(ctx, scene, lt, tsec):
    w, h = ctx["w"], ctx["h"]
    bg, pri, acc = ctx["theme"]
    img = _vgrad(w, h, bg, _mixc(bg, (0, 0, 0), 0.3)).convert("RGBA")
    d = ImageDraw.Draw(img, "RGBA")
    a = _ease(min(lt / 0.3, 1))
    cw, chh = int(w * 0.8), int(h * 0.62)
    cx, cy = (w - cw) // 2, (h - chh) // 2
    d.rounded_rectangle([cx, cy, cx + cw, cy + chh], radius=h * 0.03,
                        fill=(255, 255, 255, 26), outline=(255, 255, 255, 70),
                        width=max(1, h // 400))
    fq = _get_font(int(h * 0.11), "serif")
    d.text((cx + cw * 0.05, cy + chh * 0.03), "“", font=fq, fill=pri + (200,))
    quote = scene["headline"] or scene["on_screen_text"] or "Amazing quality — highly recommended!"
    f = _get_font(int(h * 0.042), "serif")
    lines = _wrap(d, quote, f, cw * 0.86, 5)
    y = cy + chh * 0.26
    for ln in lines:
        _center_text(d, w / 2, y, ln, f, (255, 255, 255, int(255 * a)))
        y += h * 0.055
    for i in range(5):
        sp = _clamp01((lt - 0.25 - i * 0.08) / 0.2)
        if sp > 0:
            _star(d, w / 2 + (i - 2) * h * 0.05, y + h * 0.045, h * 0.021 * sp,
                  (250, 192, 60, 255))
    ny = y + h * 0.10
    if scene["img"] is not None:
        r = int(h * 0.045)
        face = _cover(scene["img"], r * 2, r * 2)
        mask = _Image.new("L", (r * 2, r * 2), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, r * 2, r * 2], fill=255)
        img.paste(face, (int(w / 2 - r), int(ny)), mask)
        d = ImageDraw.Draw(img, "RGBA")
        ny += r * 2 + h * 0.015
    name = scene["name"] or "Happy Customer"
    f = _get_font(int(h * 0.034), "sans-bold")
    _center_text(d, w / 2, ny, name, f, acc + (255,))
    if scene["subtext"]:
        f = _get_font(int(h * 0.027), "sans")
        _center_text(d, w / 2, ny + h * 0.05, scene["subtext"], f, (220, 220, 220, 235))
    return img


def _sc_beforeafter(ctx, scene, lt, tsec, prods):
    w, h = ctx["w"], ctx["h"]
    i0 = scene["img"] if scene["img"] is not None else (prods[0]["img"] if prods else None)
    i1 = prods[1]["img"] if len(prods) > 1 else i0
    if i0 is None:
        return _vgrad(w, h, ctx["theme"][0], (0, 0, 0)).convert("RGBA")
    img = _cover(i0, w, h).convert("RGBA")
    if i1 is not None:
        right = _cover(i1, w, h).convert("RGBA")
        p = 0.5 + 0.38 * math.sin(tsec * 0.55)
        dx = int(w * p)
        img.paste(right.crop((dx, 0, w, h)), (dx, 0))
    else:
        dx = w // 2
    d = ImageDraw.Draw(img, "RGBA")
    d.line([dx, 0, dx, h], fill=(255, 255, 255, 255), width=max(3, w // 320))
    d.ellipse([dx - h * 0.028, h / 2 - h * 0.028, dx + h * 0.028, h / 2 + h * 0.028],
              fill=(255, 255, 255, 255))
    f = _get_font(int(h * 0.026), "sans-bold")
    d.text((dx - h * 0.020, h / 2 - h * 0.014), "◂▸", font=f, fill=(30, 30, 30, 255))
    f2 = _get_font(int(h * 0.028), "sans-bold")
    lab = ctx.get("labels") or {}
    _chip(d, w * 0.04, h * 0.045, lab.get("before", "BEFORE"), ctx, (40, 40, 46, 230))
    aft = lab.get("after", "AFTER")
    tw = _text_size(d, aft, f2)[0] + h * 0.03
    _chip(d, w - tw - w * 0.04, h * 0.045, aft, ctx, ctx["theme"][1] + (255,))
    if scene["headline"]:
        _styled_headline(img, scene["headline"], w / 2, h * 0.87, ctx, lt, w * 0.9)
    return img


def _sc_compare(ctx, scene, lt, tsec, prods):
    w, h = ctx["w"], ctx["h"]
    img = _Image.new("RGBA", (w, h), ctx["theme"][0] + (255,))
    d = ImageDraw.Draw(img, "RGBA")
    half = w // 2
    for k in range(2):
        prod = prods[k] if k < len(prods) else {"img": None, "name": "", "price": ""}
        if prod["img"] is not None:
            photo = _cover_anim(prod["img"], half, h, ctx["anim"], lt, 0.05)
            img.paste(photo, (k * half, 0))
        d = ImageDraw.Draw(img, "RGBA")
        band_h = int(h * 0.20)
        d.rectangle([k * half, h - band_h, k * half + half, h], fill=(5, 5, 8, 205))
        if prod["name"]:
            f = _fit_font(d, prod["name"], "display", h * 0.04, half * 0.88)
            _center_text(d, k * half + half / 2, h - band_h + h * 0.025, prod["name"], f,
                         (255, 255, 255, 255))
        if prod["price"]:
            f = _get_font(int(h * 0.05), "display")
            _center_text(d, k * half + half / 2, h - band_h + h * 0.095, prod["price"], f,
                         ctx["theme"][1] + (255,))
    d.ellipse([w / 2 - h * 0.045, h * 0.40, w / 2 + h * 0.045, h * 0.40 + h * 0.09],
              fill=(255, 255, 255, 255))
    f = _get_font(int(h * 0.038), "display")
    _center_text(d, w / 2, h * 0.40 + h * 0.024, "VS", f, (25, 20, 18, 255))
    if scene["headline"]:
        _styled_headline(img, scene["headline"], w / 2, h * 0.07, ctx, lt, w * 0.9)
    return img


def _sc_event(ctx, scene, lt, tsec):
    w, h = ctx["w"], ctx["h"]
    bg, pri, acc = ctx["theme"]
    if scene["img"] is not None:
        img = _darken(_cover_anim(scene["img"], w, h, ctx["anim"], lt, 0.06), 0.35).convert("RGBA")
    else:
        img = _vgrad(w, h, bg, _mixc(bg, (0, 0, 0), 0.3)).convert("RGBA")
    d = ImageDraw.Draw(img, "RGBA")
    # festive confetti (deterministic pseudo-random per piece)
    import random as _rnd
    rng = _rnd.Random(1234)
    pieces = [(rng.random(), rng.random(), rng.random() * 6.28,
               rng.choice([pri, acc, (255, 255, 255)]), rng.uniform(0.05, 0.16))
              for _ in range(int(70 * ctx.get("intensity", 1.0)) + 10)]
    for (fx, fy, rot, col, spd) in pieces:
        yy = ((fy + tsec * spd) % 1.15) * h - h * 0.07
        xx = fx * w + math.sin(tsec * 1.3 + rot) * w * 0.008
        s = h * 0.008
        ang = rot + tsec * 2
        pts = [(xx + s * math.cos(ang + k * math.pi / 2) * (1 if k % 2 else 0.45),
                yy + s * math.sin(ang + k * math.pi / 2) * (1 if k % 2 else 0.45))
               for k in range(4)]
        d.polygon(pts, fill=col + (200,))
    head = scene["headline"] or "Special Event Sale"
    _styled_headline(img, head, w / 2, h * 0.30, ctx, lt, w * 0.9,
                     size=h * 0.08 * ctx["headline_scale"])
    d = ImageDraw.Draw(img, "RGBA")
    date = scene["subtext"] or scene["info"]
    if date:
        f = _get_font(int(h * 0.038), "sans-bold")
        tw, th = _text_size(d, date, f)
        pad = w * 0.025
        d.rounded_rectangle([(w - tw) / 2 - pad, h * 0.47, (w + tw) / 2 + pad,
                             h * 0.47 + th + h * 0.025], radius=h * 0.03,
                            fill=pri + (255,))
        d.text(((w - tw) / 2, h * 0.47 + h * 0.011), date, font=f,
               fill=(15, 12, 8, 255) if _lum(pri) > 150 else (255, 255, 255, 255))
    _price_row(d, w / 2, h * 0.60, scene, ctx, lt)
    if ctx["cta"]:
        _cta_pill(d, w / 2, h * 0.83, ctx["cta"], ctx, tsec)
    return img


def _sc_audiogram(ctx, scene, lt, tsec):
    w, h = ctx["w"], ctx["h"]
    bg, pri, acc = ctx["theme"]
    img = _vgrad(w, h, bg, _mixc(bg, (0, 0, 0), 0.4)).convert("RGBA")
    d = ImageDraw.Draw(img, "RGBA")
    head = scene["headline"] or ctx["brand"] or "Listen Now"
    _styled_headline(img, head, w / 2, h * 0.07, ctx, lt, w * 0.9)
    d = ImageDraw.Draw(img, "RGBA")
    side = int(min(w, h) * 0.42)
    cx, cy = (w - side) // 2, int(h * 0.20)
    if scene["img"] is not None:
        art = _cover(scene["img"], side, side)
        mask = _Image.new("L", (side, side), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, side, side], radius=side * 0.08, fill=255)
        img.paste(art, (cx, cy), mask)
    else:
        d.rounded_rectangle([cx, cy, cx + side, cy + side], radius=side * 0.08,
                            fill=pri + (255,))
        f = _get_font(int(side * 0.4), "display")
        _center_text(d, w / 2, cy + side * 0.3, "♪", f, (255, 255, 255, 255))
    pulse = 1 + 0.012 * math.sin(tsec * 4)
    d.rounded_rectangle([cx - 6, cy - 6, cx + side + 6, cy + side + 6],
                        radius=side * 0.09, outline=pri + (220,), width=max(3, h // 240))
    # equalizer bars (decorative animation, same maths as mgfx bg-equalizer)
    bars = 42
    bw_ = w * 0.86 / bars
    base_y = h * 0.86
    for i in range(bars):
        f1 = math.sin(6.283 * (2 * lt) + i * 0.55)
        f2 = math.sin(6.283 * (3 * lt) + i * 1.31)
        f3 = math.sin(6.283 * (1 * lt) + i * 0.23)
        v = abs(0.45 * f1 + 0.35 * f2 + 0.20 * f3)
        bh_ = h * 0.03 + h * 0.17 * v
        col = _mixc(pri, acc, i / max(bars - 1, 1))
        x0 = w * 0.07 + i * bw_ + bw_ * 0.18
        d.rounded_rectangle([x0, base_y - bh_, x0 + bw_ * 0.64, base_y],
                            radius=bw_ * 0.2, fill=col + (235,))
    if scene["subtext"] or scene["name"]:
        f = _get_font(int(h * 0.03), "sans")
        _center_text(d, w / 2, h * 0.90, scene["subtext"] or scene["name"], f,
                     (235, 235, 235, 240))
    return img


# ------------------------------------------------- Part D: device mockups
def _persp_coeffs(src_pts, dst_pts):
    """Perspective coefficients mapping dst->src (PIL PERSPECTIVE),
    solved with pure-python Gaussian elimination (no numpy)."""
    import itertools
    rows, rhs = [], []
    for (x, y), (u, v) in zip(dst_pts, src_pts):
        rows.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); rhs.append(u)
        rows.append([0, 0, 0, x, y, 1, -v * x, -v * y]); rhs.append(v)
    n = 8
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(rows[r][col]))
        rows[col], rows[piv] = rows[piv], rows[col]
        rhs[col], rhs[piv] = rhs[piv], rhs[col]
        pv = rows[col][col] or 1e-9
        for r in range(n):
            if r != col and rows[r][col]:
                f = rows[r][col] / pv
                rows[r] = [a - f * b for a, b in zip(rows[r], rows[col])]
                rhs[r] -= f * rhs[col]
    return tuple(rhs[i] / (rows[i][i] or 1e-9) for i in range(n))


def _device_layer(kind, screen_img, dw, frame_color, website=""):
    """Draw one device (RGBA layer, width dw). Screen shows screen_img
    cover-fitted. This is a 2.5D drawn mockup — not a 3D render."""
    fc = tuple(frame_color)[:3] if frame_color else (28, 28, 34)
    if kind == "tablet":
        dh = int(dw * 0.74)
        layer = _Image.new("RGBA", (dw, dh), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        d.rounded_rectangle([0, 0, dw, dh], radius=dw * 0.035, fill=fc + (255,))
        bez = int(dw * 0.045)
        sx, sy, sw, sh = bez, int(dh * 0.07), dw - bez * 2, dh - int(dh * 0.14)
    elif kind == "laptop":
        dh = int(dw * 0.70)
        layer = _Image.new("RGBA", (dw, dh), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        sh_h = int(dh * 0.90)
        d.rounded_rectangle([int(dw * 0.04), 0, int(dw * 0.96), sh_h],
                            radius=dw * 0.02, fill=fc + (255,))
        d.polygon([(0, dh), (dw, dh), (int(dw * 0.96), sh_h), (int(dw * 0.04), sh_h)],
                  fill=_mixc(fc, (0, 0, 0), 0.25) + (255,))
        bez = int(dw * 0.028)
        sx, sy = int(dw * 0.04) + bez, bez
        sw, sh = int(dw * 0.92) - bez * 2, sh_h - bez * 2
    elif kind == "browser":
        dh = int(dw * 0.72)
        layer = _Image.new("RGBA", (dw, dh), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        d.rounded_rectangle([0, 0, dw, dh], radius=dw * 0.025, fill=(246, 247, 249, 255))
        bar_h = int(dh * 0.13)
        d.rounded_rectangle([0, 0, dw, bar_h], radius=dw * 0.025, fill=(222, 225, 230, 255))
        d.rectangle([0, bar_h - int(dw * 0.025), dw, bar_h], fill=(222, 225, 230, 255))
        for i, col in enumerate(((237, 106, 94), (245, 191, 79), (98, 199, 110))):
            r = int(bar_h * 0.16)
            cx = int(dw * 0.035) + i * int(bar_h * 0.52)
            d.ellipse([cx - r, bar_h // 2 - r, cx + r, bar_h // 2 + r], fill=col + (255,))
        url = website or "your-website.com"
        f = _get_font(int(bar_h * 0.42), "sans")
        uw = min(int(dw * 0.5), int(_text_size(d, url, f)[0] + dw * 0.05))
        ux = int(dw * 0.16)
        d.rounded_rectangle([ux, bar_h * 0.18, ux + uw, bar_h * 0.82],
                            radius=bar_h * 0.3, fill=(255, 255, 255, 255))
        d.text((ux + dw * 0.02, bar_h * 0.27), url, font=f, fill=(70, 76, 84, 255))
        sx, sy, sw, sh = int(dw * 0.012), bar_h + int(dh * 0.012), \
            dw - int(dw * 0.024), dh - bar_h - int(dh * 0.024)
    else:  # phone
        dh = int(dw * 2.04)
        layer = _Image.new("RGBA", (dw, dh), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        d.rounded_rectangle([0, 0, dw, dh], radius=dw * 0.115, fill=fc + (255,))
        d.rounded_rectangle([dw * 0.012, dh * 0.006, dw * 0.988, dh * 0.994],
                            radius=dw * 0.105, fill=_mixc(fc, (255, 255, 255), 0.10) + (255,))
        bez = int(dw * 0.035)
        sx, sy, sw, sh = bez, bez, dw - bez * 2, dh - bez * 2
        # side buttons
        d.rectangle([-3, int(dh * 0.16), 0, int(dh * 0.23)], fill=fc + (255,))
        d.rectangle([dw, int(dh * 0.19), dw + 3, int(dh * 0.28)], fill=fc + (255,))
    if screen_img is not None:
        scr = _cover(screen_img, max(sw, 2), max(sh, 2)).convert("RGBA")
        mask = _Image.new("L", (sw, sh), 0)
        rad = int(min(sw, sh) * (0.09 if kind == "phone" else 0.03))
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, sw, sh], radius=rad, fill=255)
        layer.paste(scr, (sx, sy), mask)
    if kind == "phone":
        d = ImageDraw.Draw(layer)
        iw = int(dw * 0.34)
        ix = (dw - iw) // 2
        iy = int(dh * 0.016)
        d.rounded_rectangle([ix, iy, ix + iw, iy + int(dh * 0.020)],
                            radius=int(dh * 0.010), fill=(5, 5, 8, 255))
    return layer


def _place_device(img, layer, cx, cy, scale=1.0, angle=0.0, persp=None):
    """Paste a device layer centred at (cx, cy) with optional rotation /
    perspective warp."""
    if scale != 1.0:
        layer = layer.resize((max(10, int(layer.width * scale)),
                                max(10, int(layer.height * scale))), _Image.LANCZOS)
    if persp:  # persp = (x_skew, y_skew) in -0.35..0.35
        lw, lh = layer.size
        sx, sy = persp
        src = [(0, 0), (lw, 0), (lw, lh), (0, lh)]
        dst = [(lw * max(sx, 0), lh * max(sy, 0)), (lw - lw * max(-sx, 0), lh * max(-sy, 0)),
               (lw - lw * max(sx, 0), lh - lh * max(sy, 0)), (lw * max(-sx, 0), lh - lh * max(-sy, 0))]
        coeffs = _persp_coeffs(src, dst)
        layer = layer.transform((lw, lh), _Image.PERSPECTIVE, coeffs,
                                resample=_Image.BICUBIC)
    if angle:
        layer = layer.rotate(angle, resample=_Image.BICUBIC, expand=True)
    img.alpha_composite(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)))
    return layer.size


def _sc_apppromo(ctx, scene, lt, tsec):
    w, h = ctx["w"], ctx["h"]
    dev = ctx.get("device") or {}
    kind = dev.get("kind", "phone")
    preset = dev.get("preset", "float")
    frame_color = _hex(dev["color"]) if dev.get("color") else (28, 28, 34)
    alpha = ctx.get("alpha_bg", False)
    if alpha:
        img = _Image.new("RGBA", (w, h), (0, 0, 0, 0))
    else:
        bgc = _hex(dev["bg"]) if dev.get("bg") else ctx["theme"][0]
        img = _vgrad(w, h, bgc, _mixc(bgc, (0, 0, 0), 0.35)).convert("RGBA")
    shots = [p["img"] for p in ctx["products"] if p["img"] is not None]
    if ctx.get("screen_frames"):
        shots = ctx["screen_frames"]
    land = w >= h
    # layout: device left/centre, headline beside (landscape) or below (portrait)
    if preset == "tour" or len(shots) <= 1:
        cur = shots[0] if shots else None
        if preset == "tour" and len(shots) > 1:
            seg = 1.0 / len(shots)
            i = min(int(lt / seg), len(shots) - 1)
            fp = (lt - i * seg) / seg
            cur = shots[i]
            if fp > 0.8:
                nxt = shots[(i + 1) % len(shots)]
                cur = _Image.blend(_cover(cur, 540, 1080), _cover(nxt, 540, 1080),
                                   (fp - 0.8) / 0.2)
        dw = int(h * (0.30 if kind == "phone" else 0.52))
        if kind in ("laptop", "browser", "tablet"):
            dw = int(w * (0.52 if land else 0.8))
        layer = _device_layer(kind, cur, dw, frame_color,
                              website=ctx.get("brand_kit", {}).get("website", ""))
        dcx = w * (0.30 if land else 0.5)
        dcy = h * (0.52 if land else 0.42)
        scl, ang, per = 1.0, 0.0, None
        if preset == "float":
            dcy += math.sin(tsec * 1.5) * h * 0.008
            dcx += math.sin(tsec * 0.9) * w * 0.004
            ang = math.sin(tsec * 0.8) * 1.2
        elif preset == "tilt-left":
            per = (0.16, 0.05)
        elif preset == "tilt-right":
            per = (-0.16, 0.05)
        elif preset == "zoom-in":
            scl = 0.9 + 0.14 * _eio(lt)
        elif preset == "slide-settle":
            dcx += w * 0.28 * (1 - _eob(_clamp01(tsec / 1.1)))
        if not alpha:
            sh = _Image.new("RGBA", (int(dw * 0.9), int(h * 0.05)), (0, 0, 0, 0))
            ImageDraw.Draw(sh).ellipse([0, 0, sh.width, sh.height], fill=(0, 0, 0, 110))
            sh = sh.filter(ImageFilter.GaussianBlur(10))
            img.alpha_composite(sh, (int(dcx - sh.width / 2), int(dcy + layer.height / 2 - h * 0.01)))
        _place_device(img, layer, dcx, dcy, scl, ang, per)
    else:  # multi-device: tablet behind + phone front
        dw_t = int(w * (0.5 if land else 0.78))
        tab = _device_layer("tablet", shots[0], dw_t, frame_color,
                            website=ctx.get("brand_kit", {}).get("website", ""))
        _place_device(img, tab, w * 0.38, h * 0.52 + math.sin(tsec * 1.2) * h * 0.005,
                      1.0, -6, (0.10, 0.03))
        dw_p = int(h * 0.27)
        pho = _device_layer("phone", shots[min(1, len(shots) - 1)], dw_p, frame_color)
        _place_device(img, pho, w * 0.72, h * 0.54 + math.sin(tsec * 1.5 + 1) * h * 0.006,
                      1.0, 3, (-0.08, 0.02))
    d = ImageDraw.Draw(img, "RGBA")
    # tap indicator
    tap = ctx.get("tap")
    if tap and abs(tsec - float(tap.get("at", 1.5))) < 1.0:
        tp = 1 - abs(tsec - float(tap.get("at", 1.5)))
        tx = w * (0.30 if land else 0.5) + (float(tap.get("x", 50)) - 50) / 100 * w * 0.16
        ty = h * (0.52 if land else 0.42) + (float(tap.get("y", 50)) - 50) / 100 * h * 0.3
        r = h * 0.012 + h * 0.03 * (1 - tp)
        d.ellipse([tx - r, ty - r, tx + r, ty + r], outline=(255, 255, 255, int(230 * tp)),
                  width=max(2, h // 300))
        d.ellipse([tx - 4, ty - 4, tx + 4, ty + 4], fill=(255, 255, 255, 255))
    # headline text block
    head = scene["headline"] or ctx["headline"]
    if head:
        if land:
            _styled_headline(img, head, w * 0.72, h * 0.30, ctx, lt, w * 0.46,
                             size=h * 0.062 * ctx["headline_scale"])
        else:
            _styled_headline(img, head, w * 0.5, h * 0.74, ctx, lt, w * 0.88)
    if ctx["cta"]:
        d = ImageDraw.Draw(img, "RGBA")
        _cta_pill(d, w * (0.72 if land else 0.5), h * (0.55 if land else 0.86),
                  ctx["cta"], ctx, tsec)
    # download badge (generic drawn badge or user's own image)
    badge = ctx.get("badge_image")
    if badge is not None:
        bw_ = int(w * 0.20)
        bh_ = int(badge.height * bw_ / badge.width)
        bx = int(w * (0.72 if land else 0.5) - bw_ / 2)
        by = int(h * (0.68 if land else 0.90))
        img.alpha_composite(badge.resize((bw_, bh_), _Image.LANCZOS), (bx, by))
    elif dev.get("show_badge", True):
        bw_, bh_ = int(w * 0.21), int(h * 0.052)
        bx, by = int(w * (0.72 if land else 0.5) - bw_ / 2), int(h * (0.68 if land else 0.90))
        d = ImageDraw.Draw(img, "RGBA")
        d.rounded_rectangle([bx, by, bx + bw_, by + bh_], radius=bh_ * 0.22,
                            fill=(12, 12, 16, 255), outline=(255, 255, 255, 120))
        f1 = _get_font(int(bh_ * 0.30), "sans")
        f2 = _get_font(int(bh_ * 0.44), "sans-bold")
        d.text((bx + bw_ * 0.16, by + bh_ * 0.10), "Download the", font=f1,
               fill=(200, 200, 200, 255))
        d.text((bx + bw_ * 0.16, by + bh_ * 0.42), "App Now", font=f2,
               fill=(255, 255, 255, 255))
        d.rounded_rectangle([bx + bw_ * 0.045, by + bh_ * 0.22, bx + bw_ * 0.115,
                             by + bh_ * 0.78], radius=3, outline=(255, 255, 255, 255),
                            width=max(2, h // 400))
    return img


_SCENE_RENDERERS = {
    "catalog": _sc_catalog, "restaurant-menu": _sc_restaurant,
    "real-estate": _sc_realestate, "product-showcase": _sc_showcase,
    "testimonial": _sc_testimonial, "event-sale": _sc_event,
    "audiogram": _sc_audiogram,
}


def _render_scene(ctx, template, scene, lt, tsec, gt):
    if template == "sale-hero":
        return _sc_sale_hero(ctx, scene, lt, tsec)
    if template == "social-ad":
        return _sc_social(ctx, scene, lt, tsec)
    if template == "flash-sale-countdown":
        return _sc_flashsale(ctx, scene, lt, tsec, gt)
    if template == "before-after":
        return _sc_beforeafter(ctx, scene, lt, tsec, ctx["products"])
    if template == "compare":
        return _sc_compare(ctx, scene, lt, tsec, ctx["products"])
    if template == "app-promo":
        return _sc_apppromo(ctx, scene, lt, tsec)
    fn = _SCENE_RENDERERS.get(template)
    if fn is None:
        raise ValueError(f"No v9 renderer for template '{template}'.")
    return fn(ctx, scene, lt, tsec)


def _apply_transition(cur, prev, kind, p):
    """Blend cur over prev during scene entry. p = 0..1 progress."""
    if prev is None or kind == "none" or p >= 1:
        return cur
    w, h = cur.size
    if kind == "fade":
        return _Image.blend(prev, cur, _clamp01(p))
    if kind == "slide":
        off = int(w * (1 - _ease(p)))
        if off >= w:
            return prev
        if off <= 0:
            return cur
        out = prev.copy()
        out.paste(cur.crop((0, 0, w - off, h)), (off, 0))
        return out
    if kind == "wipe":
        out = prev.copy()
        dx = int(w * _clamp01(p))
        if dx > 0:
            out.paste(cur.crop((0, 0, dx, h)), (0, 0))
            d = ImageDraw.Draw(out)
            d.line([dx, 0, dx, h], fill=(255, 255, 255), width=max(2, w // 400))
        return out
    if kind == "zoom":
        s = 0.92 + 0.08 * _ease(p)
        zw, zh = int(w * s), int(h * s)
        z = cur.resize((zw, zh), _Image.LANCZOS)
        out = prev.copy()
        out.paste(z, ((w - zw) // 2, (h - zh) // 2))
        return _Image.blend(out, cur, _clamp01(p))
    return cur


# ------------------------------------------------------------ outro / logo
def _outro_frame(ctx, lt):
    w, h = ctx["w"], ctx["h"]
    bk = ctx.get("brand_kit") or {}
    style = ctx.get("outro", "simple")
    bg, pri, acc = ctx["theme"]
    img = _vgrad(w, h, bg, _mixc(bg, (0, 0, 0), 0.35)).convert("RGBA")
    d = ImageDraw.Draw(img, "RGBA")
    a = _ease(min(lt / 0.3, 1))
    cy = h * 0.30
    logo = ctx.get("logo_img")
    if logo is not None:
        lw = int(w * bk.get("logo_size", 0.16))
        lh = int(logo.height * lw / logo.width)
        lh = min(lh, int(h * 0.25))
        lw = int(logo.width * lh / logo.height)
        lg = logo.resize((lw, lh), _Image.LANCZOS)
        if lg.mode != "RGBA":
            lg = lg.convert("RGBA")
        img.alpha_composite(lg, (int(w / 2 - lw / 2), int(cy - lh / 2)))
        cy += lh / 2 + h * 0.03
        d = ImageDraw.Draw(img, "RGBA")
    brand = bk.get("business_name") or ctx["brand"] or ctx["headline"] or "Thank You"
    f = _fit_font(d, brand, ctx["font_role"], h * 0.07, w * 0.85)
    _center_text(d, w / 2, cy, brand, f, (255, 255, 255, int(255 * a)))
    cy += h * 0.10
    if style in ("website", "classic"):
        site = bk.get("website", "")
        phone = bk.get("phone", "")
        big = site or phone
        if big:
            f2 = _fit_font(d, big, "display", h * 0.055, w * 0.85)
            _center_text(d, w / 2, cy, big, f2, pri + (255,))
            cy += h * 0.085
        if style == "classic":
            lines = [x for x in (bk.get("social", ""), phone if big != phone else "",
                                 ctx["headline"] if ctx["headline"] != brand else "") if x]
            f3 = _get_font(int(h * 0.032), "sans")
            for ln in lines[:2]:
                _center_text(d, w / 2, cy, ln, f3, acc + (int(235 * a),))
                cy += h * 0.05
    if ctx["cta"]:
        _cta_pill(d, w / 2, h * 0.78, ctx["cta"], ctx)
    return img


def _logo_overlay(img, ctx):
    logo = ctx.get("logo_img")
    bk = ctx.get("brand_kit") or {}
    if logo is None or not bk:
        return img
    w, h = ctx["w"], ctx["h"]
    wm = bool(bk.get("watermark"))
    pos = bk.get("logo_pos", "br")
    if pos == "center-end":
        return img
    size = float(bk.get("logo_size", 0.12))
    if wm:
        size = min(size, 0.10)
        pos = "br"
    lw = int(w * size)
    lh = int(logo.height * lw / max(logo.width, 1))
    lg = logo.resize((lw, lh), _Image.LANCZOS)
    if lg.mode != "RGBA":
        lg = lg.convert("RGBA")
    op = float(bk.get("logo_opacity", 0.9))
    if wm:
        op *= 0.75
    if op < 1:
        alpha = lg.split()[3].point(lambda v: int(v * op))
        lg.putalpha(alpha)
    m = int(w * 0.025)
    posmap = {"tl": (m, m), "tr": (w - lw - m, m), "bl": (m, h - lh - m),
              "br": (w - lw - m, h - lh - m)}
    x, y = posmap.get(pos, posmap["br"])
    base = img if img.mode == "RGBA" else img.convert("RGBA")
    base.alpha_composite(lg, (x, y))
    return base


# ------------------------------------------------------------ captions
def _caption_overlay(img, ctx, gt):
    cues = ctx.get("caption_cues") or []
    if not cues:
        return img
    cue = next((c for c in cues if c["start"] <= gt < c["end"]), None)
    if cue is None:
        return img
    w, h = ctx["w"], ctx["h"]
    style = ctx.get("caption_style", "clean-outline")
    pos = ctx.get("caption_pos", "bottom")
    scale = float(ctx.get("caption_size", 1.0))
    acc = ctx["theme"][1]
    words = cue["words"]
    cur = len(words) - 1
    for i, (wd, ws, we) in enumerate(words):
        if ws <= gt < we:
            cur = i
            break
    base = img if img.mode == "RGBA" else img.convert("RGBA")
    d = ImageDraw.Draw(base, "RGBA")
    ybase = {"bottom": h * 0.865, "centre": h * 0.46, "top": h * 0.07}[pos]
    if style == "hormozi":
        f = _get_font(int(h * 0.055 * scale), "display")
        text = cue["text"].upper()
        lines = _wrap(d, text, f, w * 0.86, 3)
        y = h * 0.44 if pos == "bottom" else ybase
        done_words = sum(len(ln.split()) for ln in lines)
        seen = 0
        for ln in lines:
            ws_ = ln.split()
            tw = _text_size(d, ln, f)[0]
            x = (w - tw) / 2
            for wd in ws_:
                col = acc if seen == cur else (255, 255, 255)
                d.text((x, y), wd, font=f, fill=col + (255,),
                       stroke_width=max(2, h // 220), stroke_fill=(0, 0, 0, 255))
                x += _text_size(d, wd + " ", f)[0]
                seen += 1
            y += h * 0.068
        return base
    if style == "comics":
        f = _get_font(int(h * 0.037 * scale), "sans-bold")
        lines = _wrap(d, cue["text"], f, w * 0.7, 2)
        th = len(lines) * h * 0.048 + h * 0.03
        twmax = max(_text_size(d, ln, f)[0] for ln in lines) + w * 0.05
        x0, y0 = (w - twmax) / 2, ybase
        d.rounded_rectangle([x0, y0, x0 + twmax, y0 + th], radius=h * 0.018,
                            fill=(255, 255, 255, 245))
        for i, ln in enumerate(lines):
            _center_text(d, w / 2, y0 + h * 0.014 + i * h * 0.048, ln, f, (18, 16, 14, 255))
        return base
    # word-row styles: karaoke / bold-pop / clean-outline / clean-minimal
    fsize = h * (0.040 if style != "clean-minimal" else 0.031) * scale
    f = _get_font(int(fsize), "sans-bold" if style in ("karaoke", "bold-pop") else "sans")
    lines, cur_line, cur_words = [], [], []
    for wd, ws, we in words:
        trial = " ".join(cur_words + [wd])
        if _text_size(d, trial, f)[0] > w * 0.88 and cur_words:
            lines.append(cur_line)
            cur_line, cur_words = [], []
        cur_line.append((wd, ws, we))
        cur_words.append(wd)
    if cur_line:
        lines.append(cur_line)
    if style in ("karaoke", "bold-pop"):
        bar_h = len(lines) * fsize * 1.5 + h * 0.025
        d.rounded_rectangle([w * 0.04, ybase - h * 0.012, w * 0.96, ybase - h * 0.012 + bar_h],
                            radius=h * 0.012, fill=(0, 0, 0, 140))
    y = ybase
    for line in lines:
        line_text = " ".join(wd for wd, _, _ in line)
        tw = _text_size(d, line_text, f)[0]
        x = (w - tw) / 2
        for wd, ws, we in line:
            is_cur = ws <= gt < we
            col = (255, 255, 255)
            if style == "karaoke" and is_cur:
                ww = _text_size(d, wd, f)[0]
                d.rounded_rectangle([x - 4, y - 2, x + ww + 4, y + fsize * 1.25],
                                    radius=6, fill=acc + (255,))
                col = (15, 12, 8) if _lum(acc) > 140 else (255, 255, 255)
            sw = max(2, h // 260) if style in ("clean-outline", "karaoke", "bold-pop") else 0
            d.text((x, y), wd, font=f, fill=col + (255,), stroke_width=sw,
                   stroke_fill=(0, 0, 0, 230))
            x += _text_size(d, wd + " ", f)[0]
        y += fsize * 1.5
    return base


# ------------------------------------------------------------ v9 main
def _assemble_audio(ff, silent_mp4, dst, total, *, voice_track=None,
                    music=None, duck=True, workdir=None):
    """Mux voice + music onto the silent render. Music is ducked under the
    voice with sidechaincompress (volume-envelope fallback). With music
    only, the legacy loop + fade-out behaviour is kept."""
    if not voice_track and not music:
        os.replace(silent_mp4, dst)
        return {"mixer": None}
    tmp = dst + ".mix.mp4"
    if voice_track and music:
        filt = ("[1:a]aformat=sample_rates=44100:channel_layouts=stereo[vpad];"
                f"[vpad]apad,atrim=0:{total:.2f}[voice0];"
                "[voice0]asplit=2[voicekey][voicemix];"
                "[2:a]aformat=sample_rates=44100:channel_layouts=stereo[bedraw];"
                "[bedraw][voicekey]sidechaincompress=threshold=0.02:ratio=10:"
                "attack=15:release=320[bed];"
                "[voicemix][bed]amix=inputs=2:duration=first:dropout_transition=0,"
                f"afade=t=out:st={max(total - 1.0, 0):.2f}:d=1.0[aout]")
        cmd = [ff, "-hide_banner", "-loglevel", "error", "-y", "-i", silent_mp4,
               "-i", voice_track, "-stream_loop", "-1", "-i", music,
               "-filter_complex", filt, "-map", "0:v", "-map", "[aout]",
               "-c:v", "copy", "-c:a", "aac", "-shortest", tmp]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if r.returncode != 0 or not os.path.isfile(tmp):
            filt2 = ("[1:a]aformat=sample_rates=44100:channel_layouts=stereo[vpad];"
                     f"[vpad]apad,atrim=0:{total:.2f}[voice];"
                     "[2:a]aformat=sample_rates=44100:channel_layouts=stereo,"
                     "volume=0.30[bed];"
                     "[voice][bed]amix=inputs=2:duration=first:dropout_transition=0,"
                     f"afade=t=out:st={max(total - 1.0, 0):.2f}:d=1.0[aout]")
            cmd[cmd.index("-filter_complex") + 1] = filt2
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
            if r.returncode == 0 and os.path.isfile(tmp):
                os.replace(tmp, dst)
                return {"mixer": "volume-duck (fallback)"}
            raise RuntimeError("Audio mix failed: " + (r.stderr or "")[:240])
        os.replace(tmp, dst)
        return {"mixer": "sidechaincompress"}
    if voice_track:
        filt = ("[1:a]aformat=sample_rates=44100:channel_layouts=stereo,"
                f"apad,atrim=0:{total:.2f},"
                f"afade=t=out:st={max(total - 0.8, 0):.2f}:d=0.8[aout]")
        cmd = [ff, "-hide_banner", "-loglevel", "error", "-y", "-i", silent_mp4,
               "-i", voice_track, "-filter_complex", filt, "-map", "0:v",
               "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", tmp]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if r.returncode != 0 or not os.path.isfile(tmp):
            raise RuntimeError("Voice mux failed: " + (r.stderr or "")[:240])
        os.replace(tmp, dst)
        return {"mixer": "voice-only"}
    # music only — legacy behaviour
    cmd = [ff, "-hide_banner", "-loglevel", "error", "-y", "-i", silent_mp4,
           "-stream_loop", "-1", "-i", music, "-t", str(total),
           "-af", f"afade=t=out:st={max(total - 1.2, 0):.2f}:d=1.2,volume=0.9",
           "-c:v", "copy", "-c:a", "aac", "-shortest", tmp]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if r.returncode == 0 and os.path.isfile(tmp):
        os.replace(tmp, dst)
    else:
        os.replace(silent_mp4, dst)
    return {"mixer": "music-only"}


def _create_promo_v9(image_paths, products, dst, *, template, headline, cta,
                     theme, ratio, per_slide, fps, badge_text, show_badge,
                     brand_text, anim, band, end_card, audio_path, progress_cb,
                     scenes=None, quality="1080p", text_style="classic",
                     font_role="display", headline_scale=1.0, text_color=None,
                     highlight_color=None, brand_kit=None, outro=None,
                     outro_seconds=2.5, voice_clips=None, voice_track=None,
                     music_path=None, duck_music=True, captions=False,
                     caption_style="clean-outline", caption_pos="bottom",
                     caption_size=1.0, caption_source="voiceover",
                     make_gif=False, gif_width=480, make_poster=False,
                     fmt="mp4", device=None, countdown_seconds=600,
                     features=None, labels=None, tap=None, badge_image=None,
                     screen_video=None):
    if template not in TEMPLATE_INFO:
        raise ValueError(f"Unknown promo template '{template}'.")
    if fmt == "webm" and template != "app-promo":
        raise ValueError("WebM with alpha is available for the App Promo template.")
    if not image_paths and template not in ("testimonial", "event-sale", "audiogram"):
        raise ValueError("Upload at least one photo / screenshot.")
    ff = shutil.which("ffmpeg")
    if not ff:
        raise RuntimeError("FFmpeg not found.")
    fps = int(fps) if int(fps) in (24, 25, 30, 60) else 30
    w, h = _promo_res(ratio, quality)
    prods = _load_products(image_paths or [], products or [], limit=12)
    warnings = []
    if len(products or []) > len(prods):
        warnings.append(f"{len(products) - len(prods)} product line(s) had no matching photo and were ignored.")
    if len(image_paths or []) > len(products or []):
        warnings.append("Some photos have no product line — they get blank name/price.")
    if scenes:
        scns = [_norm_scene(s, prods, per_slide, i) for i, s in enumerate(scenes[:12])]
    else:
        scns = _default_scenes(template, prods, headline, cta, features, per_slide)
    if not scns:
        raise ValueError("No scenes to render.")

    # ---- voice fit: extend scenes to fit their narration clips
    voice_timing = []
    if voice_clips:
        for i, sc in enumerate(scns):
            clip = voice_clips[i] if i < len(voice_clips) else None
            if clip and os.path.isfile(clip):
                vd = _paudio.probe_duration(clip)
                if vd > 0:
                    sc["duration"] = max(sc["duration"], vd + 0.35)
                    voice_timing.append({"index": i, "path": clip, "seconds": vd})

    # ---- timing map
    starts, t_acc = [], 0.0
    for sc in scns:
        starts.append(t_acc)
        t_acc += sc["duration"]
    scenes_total = t_acc
    outro_style = outro if outro in OUTROS else ("simple" if end_card else "none")
    outro_dur = min(max(float(outro_seconds or 2.5), 2.0), 4.0) if outro_style != "none" else 0.0
    total = scenes_total + outro_dur

    bk = brand_kit or {}
    theme_tuple = THEMES.get(theme, THEMES["crimson"])
    if bk.get("colors"):
        cols = bk["colors"]
        theme_tuple = (_hex(cols.get("bg")) if cols.get("bg") else theme_tuple[0],
                       _hex(cols.get("primary")) if cols.get("primary") else theme_tuple[1],
                       _hex(cols.get("accent")) if cols.get("accent") else theme_tuple[2])
    logo_img = None
    if bk.get("logo_path") and os.path.isfile(bk["logo_path"]):
        try:
            logo_img = Image.open(bk["logo_path"])
            logo_img.load()
            logo_img = logo_img.convert("RGBA")
        except Exception:  # noqa: BLE001
            logo_img = None
    badge_img = None
    if badge_image and os.path.isfile(badge_image):
        try:
            badge_img = Image.open(badge_image)
            badge_img.load()
            badge_img = badge_img.convert("RGBA")
        except Exception:  # noqa: BLE001
            badge_img = None
    screen_frames = None
    workdir = os.path.dirname(os.path.abspath(dst))
    if screen_video and os.path.isfile(screen_video):
        fdir = os.path.join(workdir, "_promo_screens_" + os.path.basename(dst))
        os.makedirs(fdir, exist_ok=True)
        subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-y", "-i",
                        screen_video, "-vf", "fps=2,scale=540:-2",
                        os.path.join(fdir, "f_%03d.png")],
                       capture_output=True, timeout=300)
        frames = sorted(os.path.join(fdir, f) for f in os.listdir(fdir)
                        if f.endswith(".png"))
        loaded = []
        for fp_ in frames[:int(total * 2) + 4]:
            try:
                im = Image.open(fp_)
                im.load()
                loaded.append(im)
            except Exception:  # noqa: BLE001
                pass
        if loaded:
            screen_frames = loaded

    ctx = {"w": w, "h": h, "theme": theme_tuple, "products": prods,
           "headline": headline, "cta": cta, "badge_text": badge_text,
           "show_badge": show_badge, "brand": brand_text, "anim": anim,
           "band": band, "text_style": text_style if text_style in TEXT_STYLES else "classic",
           "font_role": (bk.get("font") or font_role) if (bk.get("font") or font_role) in FONT_ROLES else "display",
           "headline_scale": float(headline_scale or 1.0),
           "text_color": _hex(text_color) if text_color else
           (_hex((bk.get("colors") or {}).get("text")) if (bk.get("colors") or {}).get("text") else (255, 255, 255)),
           "highlight_color": _hex(highlight_color) if highlight_color else theme_tuple[1],
           "brand_kit": bk, "logo_img": logo_img, "badge_image": badge_img,
           "outro": outro_style, "device": device or {}, "tap": tap,
           "labels": labels or {}, "countdown_seconds": float(countdown_seconds or 600),
           "intensity": 1.0, "alpha_bg": fmt == "webm",
           "screen_frames": None, "caption_cues": [], "caption_style": caption_style,
           "caption_pos": caption_pos, "caption_size": caption_size}
    if screen_frames:
        ctx["screen_frames"] = [screen_frames[min(int(gt * 2), len(screen_frames) - 1)]
                                for gt in [0]]  # placeholder replaced per-frame below

    # ---- captions from final timings
    cues = []
    if captions:
        timing = [{"start": starts[i], "end": starts[i] + scns[i]["duration"],
                   "voiceover_line": scns[i].get("voiceover_line", ""),
                   "on_screen_text": scns[i].get("on_screen_text", "")}
                  for i in range(len(scns))]
        cues = _paudio.build_captions(timing, source=caption_source)
        ctx["caption_cues"] = cues

    alpha = fmt == "webm"
    frames_n = int(total * fps)
    silent = dst + ".silent.mp4" if not alpha else None
    target = silent if not alpha else dst
    if alpha:
        cmd = [ff, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
               "-pix_fmt", "rgba", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
               "-an", "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
               "-b:v", "0", "-crf", "24", target]
    else:
        cmd = [ff, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
               "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
               "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
               "-pix_fmt", "yuv420p", "-movflags", "+faststart", target]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE)
    poster_img = None
    try:
        for i in range(frames_n):
            gt = i / fps
            if gt >= scenes_total:
                frame = _outro_frame(ctx, (gt - scenes_total) / max(outro_dur, 0.01))
            else:
                si = max(j for j, st in enumerate(starts) if st <= gt)
                sc = scns[si]
                lt = (gt - starts[si]) / sc["duration"]
                if screen_frames:
                    ctx["screen_frames"] = [screen_frames[min(int(gt * 2), len(screen_frames) - 1)]]
                frame = _render_scene(ctx, template, sc, min(lt, 1.0),
                                      gt - starts[si], gt)
                # transition-in from previous scene
                td = 0.45
                if si > 0 and (gt - starts[si]) < td:
                    prev = _render_scene(ctx, template, scns[si - 1], 1.0,
                                         scns[si - 1]["duration"], gt)
                    frame = _apply_transition(frame, prev, sc["transition"],
                                              (gt - starts[si]) / td)
                frame = _logo_overlay(frame, ctx)
                frame = _caption_overlay(frame, ctx, gt)
            if not alpha:
                frame = frame.convert("RGB")
            if make_poster and poster_img is None and gt >= total * 0.4:
                poster_img = frame.convert("RGB")
            proc.stdin.write(frame.tobytes())
            if progress_cb and i % 15 == 0:
                progress_cb((i + 1) / frames_n * 0.92, {"stage": "promo"})
        proc.stdin.close()
        err = proc.stderr.read().decode() if proc.stderr else ""
        rc = proc.wait(timeout=1800)
    except Exception:
        proc.kill()
        raise
    if rc != 0 or not os.path.isfile(target):
        raise RuntimeError("Promo render failed: " + (err or "")[:300])

    extras = {}
    mixer = {"mixer": None}
    if not alpha:
        # voice track from per-scene clips
        vt = voice_track
        if voice_timing and not vt:
            clips = [{"path": v["path"], "start": starts[v["index"]]}
                     for v in voice_timing]
            vt = _paudio.mix_voice_track(clips, total, workdir,
                                         name="_promo_voice_" + os.path.basename(dst) + ".m4a")
        music = music_path or audio_path
        mixer = _assemble_audio(ff, silent, dst, total, voice_track=vt,
                                music=music if music and os.path.isfile(music) else None,
                                duck=duck_music, workdir=workdir)
        if vt and vt != voice_track:
            try:
                os.remove(vt)
            except OSError:
                pass
        if silent and os.path.isfile(silent):
            try:
                os.remove(silent)
            except OSError:
                pass
    if cues:
        srt_path = os.path.splitext(dst)[0] + ".srt"
        _paudio.write_srt(cues, srt_path)
        extras["srt"] = srt_path
    if make_poster and poster_img is not None:
        p_path = os.path.splitext(dst)[0] + "_poster.jpg"
        poster_img.save(p_path, quality=88)
        extras["poster"] = p_path
    if make_gif and not alpha:
        g_path = os.path.splitext(dst)[0] + ".gif"
        gd = min(total, 10.0)
        pal = g_path + ".pal.png"
        r1 = subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-y",
                             "-t", str(gd), "-i", dst, "-vf",
                             f"fps=12,scale={int(gif_width)}:-2:flags=lanczos,palettegen",
                             pal], capture_output=True, timeout=300)
        if r1.returncode == 0:
            r2 = subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-y",
                                 "-t", str(gd), "-i", dst, "-i", pal, "-lavfi",
                                 "fps=12,scale=%d:-2:flags=lanczos[x];[x][1:v]paletteuse"
                                 % int(gif_width), g_path],
                                capture_output=True, timeout=300)
            if r2.returncode == 0 and os.path.isfile(g_path):
                extras["gif"] = g_path
            try:
                os.remove(pal)
            except OSError:
                pass
    if progress_cb:
        progress_cb(1.0, {"stage": "done"})
    meta = {"template": template, "width": w, "height": h, "ratio": ratio,
            "fps": fps, "duration": round(total, 1), "products": len(prods),
            "scenes": len(scns), "end_card": outro_style != "none",
            "outro": outro_style, "music": bool(music_path or audio_path),
            "voice": bool(voice_timing or voice_track), "mixer": mixer.get("mixer"),
            "captions": len(cues), "quality": quality, "format": fmt,
            "size_mb": round(os.path.getsize(dst) / 1048576, 2),
            "extra_files": extras,
            "timing": [{"start": round(starts[i], 2),
                        "end": round(starts[i] + scns[i]["duration"], 2),
                        "voiceover_line": scns[i].get("voiceover_line", "")}
                       for i in range(len(scns))]}
    if warnings:
        meta["warning"] = " ".join(warnings)
    if not alpha:
        meta["stock_check"] = _probe_check(dst, w, h, fps, total)
    return meta


def make_placeholders(dirpath, n=3):
    """Placeholder product images for template previews (server-generated)."""
    os.makedirs(dirpath, exist_ok=True)
    paths = []
    palettes = [((38, 70, 120), (240, 192, 90)), ((90, 30, 40), (255, 190, 190)),
                ((16, 80, 74), (170, 255, 240))]
    for i in range(n):
        p = os.path.join(dirpath, f"placeholder_{i}.png")
        if not os.path.isfile(p):
            bg, acc = palettes[i % len(palettes)]
            img = _vgrad(800, 800, bg, _mixc(bg, (0, 0, 0), 0.3)).convert("RGB")
            d = ImageDraw.Draw(img, "RGBA")
            d.rounded_rectangle([180, 200, 620, 620], radius=36, fill=acc + (255,))
            f = _get_font(120, "display")
            _center_text(d, 400, 340, f"P{i + 1}", f, (20, 18, 14, 255))
            f2 = _get_font(44, "sans-bold")
            _center_text(d, 400, 660, f"Product {i + 1}", f2, (255, 255, 255, 255))
            img.save(p)
        paths.append(p)
    return paths


_PLACEHOLDER_PRODUCTS = [
    {"name": "Leather Wallet", "price": "$24.99", "old_price": "$49.99",
     "features": ["Full-grain leather", "RFID protection", "Slim bifold design"]},
    {"name": "Wireless Earbuds", "price": "$39.99", "old_price": "$79.99",
     "features": ["40h battery", "Noise cancelling", "IPX5 water resistant"]},
    {"name": "Smart Watch", "price": "$59.99", "old_price": "$99.99",
     "features": ["AMOLED display", "Heart-rate tracking", "7-day battery"]},
]


def create_promo(image_paths, products, dst, *, template="sale-hero", headline="",
                 cta="", theme="crimson", ratio="16:9", per_slide=3.5, fps=30,
                 badge_text="SALE", show_badge=True, brand_text="", anim="zoom-in",
                 band="bottom", end_card=False, audio_path=None, progress_cb=None,
                 # ---- v9 additions (all defaulted; old calls unaffected)
                 scenes=None, quality="1080p", text_style="classic",
                 font_role="display", headline_scale=1.0, text_color=None,
                 highlight_color=None, brand_kit=None, outro=None,
                 outro_seconds=2.5, voice_clips=None, voice_track=None,
                 music_path=None, duck_music=True, captions=False,
                 caption_style="clean-outline", caption_pos="bottom",
                 caption_size=1.0, caption_source="voiceover",
                 make_gif=False, gif_width=480, make_poster=False, fmt="mp4",
                 device=None, countdown_seconds=600, features=None,
                 labels=None, tap=None, badge_image=None, screen_video=None):
    """Promo Maker entry point. Plain pre-v9 calls (old templates, no new
    options) take the untouched legacy path; anything new routes to the
    v9 scene engine."""
    new_engaged = (
        scenes is not None or template not in LEGACY_TEMPLATES
        or quality != "1080p" or text_style != "classic" or bool(brand_kit)
        or outro is not None or bool(voice_clips) or bool(voice_track)
        or captions or make_gif or make_poster or fmt != "mp4"
        or int(fps) not in (24, 25, 30) or bool(device) or bool(features)
        or bool(screen_video) or len(image_paths or []) > 6)
    if not new_engaged:
        return _create_promo_legacy(
            image_paths, products, dst, template=template, headline=headline,
            cta=cta, theme=theme, ratio=ratio, per_slide=per_slide, fps=fps,
            badge_text=badge_text, show_badge=show_badge, brand_text=brand_text,
            anim=anim, band=band, end_card=end_card, audio_path=audio_path,
            progress_cb=progress_cb)
    return _create_promo_v9(
        image_paths, products, dst, template=template, headline=headline,
        cta=cta, theme=theme, ratio=ratio, per_slide=per_slide, fps=fps,
        badge_text=badge_text, show_badge=show_badge, brand_text=brand_text,
        anim=anim, band=band, end_card=end_card, audio_path=audio_path,
        progress_cb=progress_cb, scenes=scenes, quality=quality,
        text_style=text_style, font_role=font_role,
        headline_scale=headline_scale, text_color=text_color,
        highlight_color=highlight_color, brand_kit=brand_kit, outro=outro,
        outro_seconds=outro_seconds, voice_clips=voice_clips,
        voice_track=voice_track, music_path=music_path, duck_music=duck_music,
        captions=captions, caption_style=caption_style, caption_pos=caption_pos,
        caption_size=caption_size, caption_source=caption_source,
        make_gif=make_gif, gif_width=gif_width, make_poster=make_poster,
        fmt=fmt, device=device, countdown_seconds=countdown_seconds,
        features=features, labels=labels, tap=tap, badge_image=badge_image,
        screen_video=screen_video)
