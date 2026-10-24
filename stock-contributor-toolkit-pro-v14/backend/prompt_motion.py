"""
v8 — "Create Motion from Image + Prompt" interpreter (MotionHero-style).

A plain-English prompt like "slow zoom in with golden particles orbiting
the logo, elegant glow, dark background" is interpreted into a WHITELISTED
render plan for this app's own procedural templates (backend/mgfx.py):

    {kind, theme, speed, intensity, duration, ratio, text,
     color_primary, color_accent, color_bg, source,
     art_motion (v10 — how the artwork itself moves), subject,
     image_colors}

Two interpreters:
1. interpret_prompt() — built-in deterministic keyword parser. Works
   offline, no key, always available. This is the required path.
2. ai_interpret() — optional: asks the user's OWN provider key (Gemini /
   Groq / Grok / OpenRouter, vision when an image is supplied, same
   pattern as ai_hub.analyze_reference) for the same plan JSON. Every
   field is validated against the whitelist and merged over the built-in
   plan; anything invalid or missing falls back to the built-in value.
   Provider output can NEVER escape the whitelist.

Honesty: this interprets a prompt into the app's own motion templates —
it is not generative video.

v11 (Prompt #4, Job B): ONE shared AI key serves this tab (browser
localStorage `mgfx_byok`; checked via ai_hub.test_key, saved only in the
browser). The AI now acts as a commercial stock-motion ART DIRECTOR: the
plan gains subtext, colors{primary,accent,background}, commercial_angle
(why the motion sells / where it is used) and buyer_category (logo sting
/ product ad / social promo / stock background loop / greeting). The
returned plan is shown in an editable "AI Motion Plan" card BEFORE any
render; the user's edits are what renders (validate_plan_fields). With a
saved key, an AI failure STOPS the render route with the error visible —
Retry AI or explicitly choose the built-in interpreter; there is no
silent fallback.
"""

import json
import re
import urllib.error
import urllib.parse

from . import ai_hub
from .mgfx import CATALOG, THEMES

IMG_KINDS = ["img-breathing", "img-orbit", "img-sweep", "img-parallax",
             "img-kenburns"]
BG_KINDS = ["bg-gradient", "bg-particles", "bg-bokeh", "bg-waves",
            "bg-confetti", "bg-geometric", "bg-light-trails", "bg-hexwave",
            "bg-equalizer", "bg-vortex", "bg-burst", "overlay-sparkle"]
PLAN_KINDS = IMG_KINDS + BG_KINDS

# v10: the artwork's OWN motion (mgfx art_motion). Parsed from the prompt
# by BOTH interpreters and combined with the template effect at render.
ART_MOTIONS = ["zoom-in", "zoom-out", "pan-left", "pan-right", "sway",
               "breathe", "none"]

# v11: buyer categories the AI art director must choose from.
BUYER_CATEGORIES = ["logo sting", "product ad", "social promo",
                    "stock background loop", "greeting"]
_ART_MOTION_RULES = [  # first match wins — explicit zoom/pan beats defaults
    (("zoom out", "zooming out", "pull back"), "zoom-out"),
    (("zoom in", "zoom into", "zooming in", "zooming", "slow zoom", "zoom"),
     "zoom-in"),
    (("pan left", "pan to the left", "move left", "slide left"), "pan-left"),
    (("pan right", "pan to the right", "pan across", "move right",
      "slide right", "pan"), "pan-right"),
    (("sway", "rotate", "rotating", "rocking", "tilt", "swing"), "sway"),
    (("breathe", "breathing", "pulse", "pulsing"), "breathe"),
]

_THEME_WORDS = [
    ("gold", ("gold", "golden", "champagne", "amber")),
    ("teal", ("teal", "turquoise", "mint", "emerald")),
    ("violet", ("violet", "purple", "lavender", "magenta")),
    ("crimson", ("crimson", "red", "ruby", "burgundy")),
    ("ocean", ("ocean", "blue", "navy", "azure", "sky")),
    ("rose", ("rose", "pink", "blush")),
]

_KIND_RULES = [  # (words, kind) — first match wins, most specific first
    (("orbit", "orbiting", "spiral", "particles around", "circling"), "img-orbit"),
    (("parallax", "layers", "depth", "2.5d", "3d float"), "img-parallax"),
    (("ken burns", "kenburns", "zoom in", "zoom into", "zooming", "slow zoom",
      "zoom"), "img-kenburns"),
    (("sweep", "shine", "shimmer", "reveal", "light across"), "img-sweep"),
    (("breathing", "breathe", "pulse", "pulsing", "glow"), "img-breathing"),
    (("confetti", "celebration", "party"), "bg-confetti"),
    (("vortex", "galaxy", "swirl", "cosmic"), "bg-vortex"),
    (("neon", "light trails", "light streaks"), "bg-light-trails"),
    (("hexagon", "honeycomb"), "bg-hexwave"),
    (("equalizer", "music bars", "audio visual"), "bg-equalizer"),
    (("bokeh",), "bg-bokeh"),
    (("waves", "wave", "ocean layers"), "bg-waves"),
    (("burst", "sunburst", "comic"), "bg-burst"),
    (("sparkle", "sparkles", "glitter"), "overlay-sparkle"),
    (("particles", "particle", "dust"), "bg-particles"),
    (("gradient", "aurora"), "bg-gradient"),
]


def _clamp(v, lo, hi, default):
    try:
        return min(max(float(v), lo), hi)
    except (TypeError, ValueError):
        return default


def interpret_prompt(prompt, has_image=True):
    """Built-in deterministic parser — no key, no network."""
    p = (prompt or "").lower()
    plan = {"kind": "img-breathing" if has_image else "bg-gradient",
            "theme": "gold", "speed": 1.0, "intensity": 0.8,
            "duration": 5, "ratio": "16:9", "text": "", "subtext": "",
            "color_primary": None, "color_accent": None,
            "color_bg": None, "source": "builtin",
            "art_motion": "breathe" if has_image else "none",
            "subject": "", "image_colors": [],
            "commercial_angle": "", "buyer_category": ""}
    # quoted text -> overlay text
    m = re.search(r'"([^"]{1,90})"|\u201c([^\u201d]{1,90})\u201d', prompt or "")
    if m:
        plan["text"] = (m.group(1) or m.group(2) or "").strip()
    # duration hint: "6 seconds" / "10s"
    m = re.search(r"(\d{1,2})\s*(?:s\b|sec|secs|second|seconds)", p)
    if m:
        plan["duration"] = int(_clamp(m.group(1), 2, 20, 5))
    # template kind
    for words, kind in _KIND_RULES:
        if any(w in p for w in words):
            plan["kind"] = kind
            break
    if plan["kind"].startswith("bg-") and not has_image and "particles" in p \
            and ("orbit" in p or "logo" in p):
        plan["kind"] = "bg-particles"
    # theme / colours
    for theme, words in _THEME_WORDS:
        if any(w in p for w in words):
            plan["theme"] = theme
            break
    if any(w in p for w in ("dark", "black", "night", "moody")):
        bgc, _ca, _cb = THEMES[plan["theme"]]
        plan["color_bg"] = "#%02x%02x%02x" % tuple(max(0, c - 6) for c in bgc) \
            if plan["theme"] != "gold" else "#0a0a12"
        if plan["theme"] == "teal":
            plan["color_bg"] = "#04141a"
    # speed
    if any(w in p for w in ("very fast", "rapid")):
        plan["speed"] = 2.0
    elif any(w in p for w in ("fast", "quick", "energetic", "dynamic")):
        plan["speed"] = 1.5
    elif any(w in p for w in ("slow", "gentle", "calm", "elegant", "smooth")):
        plan["speed"] = 0.5
    # intensity
    if any(w in p for w in ("subtle", "minimal", "soft", "light touch")):
        plan["intensity"] = 0.4
    elif any(w in p for w in ("intense", "strong", "dramatic", "bold",
                              "heavy")):
        plan["intensity"] = 1.0
    # v10: the artwork's own motion — an explicit zoom/pan/sway in the
    # prompt wins over the template default (breathe for image plans)
    for words, motion in _ART_MOTION_RULES:
        if any(w in p for w in words):
            plan["art_motion"] = motion
            break
    if not has_image:
        plan["art_motion"] = "none"
    # ratio hints
    if any(w in p for w in ("vertical", "9:16", "portrait", "reel",
                            "tiktok", "story")):
        plan["ratio"] = "9:16"
    elif any(w in p for w in ("square", "1:1", "instagram post")):
        plan["ratio"] = "1:1"
    elif "4:5" in p:
        plan["ratio"] = "4:5"
    plan["buyer_category"] = _builtin_category(plan, p)
    plan["commercial_angle"] = _builtin_angle(plan["buyer_category"])
    return plan


def _builtin_category(plan, p):
    """Deterministic buyer category for the no-key built-in plan."""
    kind = plan.get("kind", "")
    if kind.startswith(("bg-", "overlay-")):
        return "stock background loop"
    if any(w in p for w in ("greeting", "card", "birthday", "wedding",
                            "ramadan", "eid", "christmas", "new year",
                            "diwali", "anniversary")):
        return "greeting"
    if plan.get("ratio") in ("9:16", "1:1") or any(
            w in p for w in ("reel", "tiktok", "instagram", "social",
                             "story", "shorts")):
        return "social promo"
    if any(w in p for w in ("sale", "discount", "offer", "product",
                            "shop", "price", "promo")):
        return "product ad"
    return "logo sting"


_BUILTIN_ANGLES = {
    "logo sting": "Subtle, premium motion that keeps the artwork centre-"
                  "stage and readable at thumbnail size — sells as a "
                  "logo sting / brand intro.",
    "product ad": "Energetic, product-first motion with a clear headline "
                  "— sells as a product ad for marketplace promos.",
    "social promo": "Bold, fast-reading motion in a social ratio — sells "
                    "as a social promo for reels, stories and posts.",
    "stock background loop": "A seamless loop buyers can drop behind any "
                             "title, product shot or presentation.",
    "greeting": "Warm, celebratory motion — sells as a greeting card / "
                "seasonal opener.",
}


def _builtin_angle(category):
    return _BUILTIN_ANGLES.get(category, _BUILTIN_ANGLES["logo sting"])


_AI_INSTRUCTION = """You are a commercial stock-motion ART DIRECTOR. A contributor uploads artwork (optionally) plus a plain-English prompt; YOU decide the motion that will SELL. Reply with ONLY a JSON object, no markdown:
{"kind": one of KINDS, "theme": one of THEMES, "speed": 0.25-2.0, "intensity": 0.1-1.0, "duration": 2-20, "ratio": "16:9"|"9:16"|"1:1"|"4:5", "text": "headline overlay text or empty", "subtext": "smaller supporting line or empty", "art_motion": one of ART_MOTIONS, "subject": "2-6 word description of the image subject (empty if no image)", "dominant_colors": ["#rrggbb", "#rrggbb"], "colors": {"primary": "#rrggbb", "accent": "#rrggbb", "background": "#rrggbb"}, "commercial_angle": "ONE line: why this motion sells and where it is used", "buyer_category": one of CATEGORIES}
ART-DIRECTION RULES:
- Backgrounds must be SEAMLESS LOOPS (gentle, tileable motion, no hard cuts).
- Logos and brands get SUBTLE, PREMIUM motion — slow, elegant, nothing bouncy.
- Sales and products get ENERGETIC motion — decisive movement, clear headline.
- NEVER invent trademark/brand text; only use words the user gave you.
- The subject must stay readable at THUMBNAIL size — favour contrast and centre weight.
ART_MOTIONS describes how the uploaded artwork ITSELF moves, combined with the template effect: zoom-in, zoom-out, pan-left, pan-right, sway, breathe, none. An explicit zoom/pan/sway named in the prompt must win.
"colors": take primary/accent/background from the image's dominant colours, unless the prompt itself names colours — then the prompt wins.
If an image is attached, REALLY look at it: fill "subject" with what the image shows and "dominant_colors" with its 1-3 dominant colours as hex.
KINDS (img-* animate the uploaded image itself; bg-* are animated backgrounds) = """ \
    + ", ".join(PLAN_KINDS) + """
THEMES = """ + ", ".join(THEMES.keys()) + """
CATEGORIES = """ + ", ".join(BUYER_CATEGORIES) + """
Pick the kind that best matches the described motion. speed <1 = slower/calm, >1 = faster."""

_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def _prompt_names_colour(prompt):
    p = (prompt or "").lower()
    return any(w in p for _t, words in _THEME_WORDS for w in words)


def _validate_plan(raw, fallback):
    """Merge provider JSON over the built-in plan — whitelist only."""
    if not isinstance(raw, dict):
        return fallback
    plan = dict(fallback)
    if raw.get("kind") in PLAN_KINDS:
        plan["kind"] = raw["kind"]
    if raw.get("theme") in THEMES:
        plan["theme"] = raw["theme"]
    plan["speed"] = _clamp(raw.get("speed"), 0.25, 2.0, plan["speed"])
    plan["intensity"] = _clamp(raw.get("intensity"), 0.1, 1.0,
                               plan["intensity"])
    plan["duration"] = int(_clamp(raw.get("duration"), 2, 20,
                                   plan["duration"]))
    if raw.get("ratio") in ("16:9", "9:16", "1:1", "4:5"):
        plan["ratio"] = raw["ratio"]
    if isinstance(raw.get("text"), str) and raw["text"].strip():
        plan["text"] = raw["text"].strip()[:90]
    elif isinstance(raw.get("headline"), str) and raw["headline"].strip():
        plan["text"] = raw["headline"].strip()[:90]
    # v10: artwork motion from the AI — whitelisted; the fallback already
    # carries the built-in parse, so an explicit prompt zoom/pan survives
    # even when the AI omits the field.
    if raw.get("art_motion") in ART_MOTIONS:
        plan["art_motion"] = raw["art_motion"]
    if isinstance(raw.get("subject"), str) and raw["subject"].strip():
        plan["subject"] = raw["subject"].strip()[:80]
    # v11 art-director fields — all whitelisted/clamped like the rest
    if isinstance(raw.get("subtext"), str):
        plan["subtext"] = raw["subtext"].strip()[:120]
    if isinstance(raw.get("commercial_angle"), str) and \
            raw["commercial_angle"].strip():
        plan["commercial_angle"] = raw["commercial_angle"].strip()[:240]
    if raw.get("buyer_category") in BUYER_CATEGORIES:
        plan["buyer_category"] = raw["buyer_category"]
    cols = raw.get("colors")
    if isinstance(cols, dict):
        for src, dst in (("primary", "color_primary"),
                         ("accent", "color_accent"),
                         ("background", "color_bg")):
            v = cols.get(src)
            if isinstance(v, str) and _HEX_RE.match(v):
                plan[dst] = v
    plan["source"] = "ai"
    return plan


def _apply_image_colors(plan, raw, prompt):
    """v10: map the AI-read dominant image colours into the plan's custom
    colours — but only when the prompt itself names no theme/colour (the
    user's words always win over the image palette)."""
    cols = raw.get("dominant_colors") if isinstance(raw, dict) else None
    if not isinstance(cols, list):
        return plan
    cols = [c for c in cols if isinstance(c, str) and _HEX_RE.match(c)][:3]
    if not cols:
        return plan
    plan["image_colors"] = cols
    if not _prompt_names_colour(prompt):
        plan["color_primary"] = cols[0]
        if len(cols) > 1:
            plan["color_accent"] = cols[1]
    return plan


def ai_interpret(provider, api_key, prompt, image_path=None,
                 model=None, base_url=None):
    """Ask the user's own provider for a plan; validate + fall back per-field.
    Raises ValueError/RuntimeError on hard failures (caller decides —
    v11 render routes STOP on failure instead of silently falling back).
    `model`/`base_url` (v11): the shared mgfx key panel's optional model
    and a Custom provider's base URL."""
    import base64
    import os
    provider = (provider or "gemini").strip().lower()
    if provider not in ai_hub.PROVIDERS:
        raise ValueError("Unknown provider.")
    cfg = ai_hub.PROVIDERS[provider]
    if not (api_key or "").strip():
        raise ValueError(f"Paste your {cfg['label']} API key first "
                         f"(free: {cfg['get_key']}).")
    if provider == "huggingface":
        raise ValueError("Hugging Face has no vision chat here — use "
                         "Gemini (free), Groq (free), Grok or OpenRouter.")
    base_plan = interpret_prompt(prompt, has_image=bool(image_path))
    text_prompt = _AI_INSTRUCTION + "\n\nUser prompt: " + (prompt or "")
    b64 = mime = None
    if image_path and os.path.isfile(image_path):
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        ext = os.path.splitext(image_path)[1].lower().lstrip(".")
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                "png": "image/png", "webp": "image/webp"}.get(ext,
                                                              "image/png")
    try:
        if cfg["kind"] == "gemini":
            mdl = (model or "").strip() or cfg["default_model"]
            url = ("https://generativelanguage.googleapis.com/v1beta/models/"
                   + urllib.parse.quote(mdl) + ":generateContent?key="
                   + urllib.parse.quote(api_key.strip()))
            parts = [{"text": text_prompt}]
            if b64:
                parts.append({"inline_data": {"mime_type": mime, "data": b64}})
            data = ai_hub._post_json(url, {"contents": [{"parts": parts}]},
                                     timeout=120)
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        else:
            base = (base_url or "").strip() or cfg["base"]
            if not base:
                raise ValueError("Custom provider needs a base URL — set "
                                 "it in Settings (AI provider base URL) "
                                 "or pick a built-in provider.")
            mdl = (model or "").strip() or cfg["default_model"]
            if image_path and not (model or "").strip():
                if provider == "groq":
                    mdl = "meta-llama/llama-4-scout-17b-16e-instruct"
                elif provider == "grok":
                    mdl = "grok-2-vision-1212"
                elif provider == "openrouter":
                    mdl = "meta-llama/llama-3.2-11b-vision-instruct:free"
            content = [{"type": "text", "text": text_prompt}]
            if b64:
                content.append({"type": "image_url", "image_url":
                                  {"url": f"data:{mime};base64,{b64}"}})
            data = ai_hub._post_json(
                base.rstrip("/") + "/chat/completions",
                {"model": mdl, "messages": [{"role": "user",
                                             "content": content}]},
                headers={"Authorization": f"Bearer {api_key.strip()}"},
                timeout=120)
            text = data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{cfg['label']} error {e.code}: "
                           + e.read().decode("utf-8", "ignore")[:250])
    m = re.search(r"\{.*\}", text or "", re.DOTALL)
    if not m:
        raise RuntimeError("The AI did not return a usable plan.")
    raw = json.loads(m.group(0))
    plan = _validate_plan(raw, base_plan)
    # v10: the image was in the request — surface what the AI saw in it
    # (subject + dominant colours) and map the colours into the plan.
    return _apply_image_colors(plan, raw, prompt)


def interpret(prompt, provider=None, api_key=None, image_path=None,
              has_image=True, model=None, base_url=None):
    """Best plan available: AI when a key is supplied, else built-in.
    Never raises for AI problems — the failure reason travels in the
    plan as `ai_note` and the UI shows it visibly (no silent fallback:
    the render route STOPS on ai_note unless the user explicitly picks
    the built-in interpreter)."""
    plan = interpret_prompt(prompt, has_image=has_image)
    if provider and (api_key or "").strip():
        try:
            plan = ai_interpret(provider, api_key, prompt,
                                image_path=image_path, model=model,
                                base_url=base_url)
            plan["provider"] = provider
        except Exception as exc:  # noqa: BLE001
            plan = dict(plan)
            plan["ai_note"] = f"AI interpretation unavailable ({exc})"
    return plan


def validate_plan_fields(d, has_image=True):
    """v11: validate a plan EDITED in the AI Motion Plan card. Same
    whitelist as _validate_plan — whatever survives this function is
    exactly what the render uses. Accepts the card's field names
    (headline == text)."""
    if not isinstance(d, dict):
        raise ValueError("Plan must be a JSON object.")
    fallback = interpret_prompt("", has_image=has_image)
    plan = _validate_plan(d, fallback)
    if d.get("source") in ("ai", "builtin"):
        plan["source"] = d["source"]
    if d.get("provider"):
        plan["provider"] = str(d["provider"])[:24]
    if isinstance(d.get("text"), str):
        plan["text"] = d["text"].strip()[:90]
    elif isinstance(d.get("headline"), str):
        plan["text"] = d["headline"].strip()[:90]
    for key in ("color_primary", "color_accent", "color_bg"):
        v = d.get(key)
        if isinstance(v, str) and _HEX_RE.match(v):
            plan[key] = v
        elif v in (None, ""):
            plan[key] = None
    cols = d.get("image_colors")
    if isinstance(cols, list):
        plan["image_colors"] = [c for c in cols
                                if isinstance(c, str) and _HEX_RE.match(c)][:3]
    if isinstance(d.get("subject"), str):
        plan["subject"] = d["subject"].strip()[:80]
    return plan
