"""
Promo Maker v9 — AI Promo Script Builder + Script-to-Promo (InVideo/VEED
pattern, reimplemented for this local BYOK app).

generate_script(brief, provider, key, ...) — with the user's own key it
asks their provider (backend/ai_hub.py — keys per-request, never stored)
for STRICT JSON scenes (Hook -> Benefits -> Offer -> CTA). With NO key it
uses built-in fill-in formulas (3 tone variants per scene role) and the
result is labelled source="basic" so the UI can say "Basic script (no AI
key)" honestly.

split_script(text, ...) — VEED-style paste-a-script: with a key the AI
splits it; without a key, sentences/paragraphs are merged locally under a
per-scene word budget.
"""

import json
import re

from . import ai_hub

LANGUAGES = ["English", "Bangla", "Hindi", "Arabic", "Spanish", "French",
             "German", "Urdu", "Portuguese", "Turkish"]
TONES = ["Exciting", "Premium", "Friendly", "Urgent", "Funny"]
PLATFORMS = {"YouTube": "16:9", "YouTube Shorts": "9:16", "Reels": "9:16",
             "TikTok": "9:16", "Instagram Feed": "1:1",
             "Instagram 4:5": "4:5", "Facebook": "4:5", "Amazon": "16:9"}

_SYSTEM = (
    "You are a senior short-form ad copywriter. Return STRICT JSON ONLY — "
    "an array of scene objects, no markdown fences, no commentary. Each "
    "object: {\"on_screen_text\": <=40 chars, \"voiceover_line\": one spoken "
    "sentence, \"visual_note\": short description of the visual}. Structure: "
    "scene 1 = Hook, then 2-3 Benefit scenes, then the Offer scene, last = "
    "Call To Action. Size the scene count and voiceover length to the "
    "target length (about 2.2 spoken words per second).")


def _ai_chat(provider, key, model, base_url, prompt, timeout=120):
    """One raw chat completion through ai_hub's provider plumbing."""
    provider = (provider or "gemini").strip().lower()
    if provider not in ai_hub.PROVIDERS:
        raise ValueError(f"Unknown provider '{provider}'.")
    if not (key or "").strip():
        raise ValueError(f"Paste your {ai_hub.PROVIDERS[provider]['label']} "
                         "API key first — it is never stored.")
    if ai_hub.PROVIDERS[provider]["kind"] == "gemini":
        return ai_hub._gemini(key.strip(), model, prompt, timeout)
    return ai_hub._openai_style(provider, key.strip(), model, prompt,
                                base_url, timeout)


def _parse_scenes(text):
    """Extract a JSON array of scene dicts from a provider response."""
    if not text:
        raise RuntimeError("The provider returned an empty response.")
    t = text.strip()
    t = re.sub(r"^```(?:json)?|```$", "", t, flags=re.M).strip()
    lo, hi = t.find("["), t.rfind("]")
    if lo < 0 or hi <= lo:
        raise RuntimeError("The provider did not return a scene list — try again.")
    data = json.loads(t[lo:hi + 1])
    scenes = []
    for s in data:
        if not isinstance(s, dict):
            continue
        scenes.append({
            "on_screen_text": str(s.get("on_screen_text", ""))[:60],
            "voiceover_line": str(s.get("voiceover_line", ""))[:220],
            "visual_note": str(s.get("visual_note", ""))[:160],
        })
    if not scenes:
        raise RuntimeError("The provider returned no usable scenes — try again.")
    return scenes


def _assign_durations(scenes, target_seconds):
    """Distribute target length: hook/CTA a touch shorter, benefits equal."""
    n = len(scenes)
    if n == 0:
        return scenes
    weights = []
    for i in range(n):
        weights.append(0.85 if i in (0, n - 1) and n > 2 else 1.0)
    tot = sum(weights)
    for s, wgt in zip(scenes, weights):
        s["duration"] = round(max(2.0, target_seconds * wgt / tot), 1)
    return scenes


# ------------------------------------------------- built-in (no-key) mode
_HOOKS = {
    "Exciting": ["Stop scrolling — {offer} at {business}!",
                 "This is BIG: {offer}, only at {business}!",
                 "You asked, we delivered — {offer} is here!"],
    "Premium": ["Crafted for those who notice — {business}.",
                "The {product} edit everyone will ask about.",
                "Quiet luxury, loud results — discover {business}."],
    "Friendly": ["Hey friend — {offer} at {business} is on!",
                 "Good news: your favourites just got better.",
                 "Made with love, priced with love — {business}."],
    "Urgent": ["Last chance — {offer} ends soon!",
               "Don't wait: {offer} at {business}, while stock lasts!",
               "Final hours for {offer}. Seriously."],
    "Funny": ["Your wallet said no. {offer} said YES.",
              "Warning: extreme {product} happiness ahead.",
              "We broke the price button again — {offer}!"],
}
_BENEFITS = [
    "Premium quality you can feel from the first touch.",
    "Loved by happy customers — {audience} approved.",
    "Made to last, designed to turn heads.",
    "Fast delivery and easy returns, zero stress.",
]
_OFFER = ["Get {offer} — yes, really, {offer}.",
          "The deal: {offer}. No catch, just value.",
          "{offer} — today at {business}."]
_CTA = ["Tap Shop Now before it's gone!",
        "Order today at {business} — link in bio!",
        "Message us now to claim yours!"]


def _fill(tpl, brief):
    product = brief.get("product") or brief.get("business") or "this"
    return (tpl.replace("{business}", brief.get("business") or "our store")
               .replace("{product}", product)
               .replace("{offer}", brief.get("offer") or "a special offer")
               .replace("{audience}", brief.get("audience") or "everyone"))


def builtin_script(brief):
    """Deterministic formula script — works offline, no AI key."""
    import random
    tone = brief.get("tone") if brief.get("tone") in TONES else "Exciting"
    rnd = random.Random(hash((brief.get("business", ""), tone)) & 0xFFFF)
    name = brief.get("business") or "Your Business"
    scenes = [
        {"on_screen_text": _fill(rnd.choice(_HOOKS[tone]), brief)[:40],
         "voiceover_line": _fill(rnd.choice(_HOOKS[tone]), brief),
         "visual_note": "Hero product shot, bold headline in"},
        {"on_screen_text": "Premium quality, made to last",
         "voiceover_line": _fill(rnd.choice(_BENEFITS), brief),
         "visual_note": "Close-up detail shot of the product"},
        {"on_screen_text": "Loved by customers",
         "voiceover_line": _fill(rnd.choice(_BENEFITS), brief),
         "visual_note": "Lifestyle shot / second product angle"},
        {"on_screen_text": (_fill("{offer}", brief))[:40],
         "voiceover_line": _fill(rnd.choice(_OFFER), brief),
         "visual_note": "Price badge pops in, offer headline"},
        {"on_screen_text": "Shop Now",
         "voiceover_line": _fill(rnd.choice(_CTA), brief),
         "visual_note": f"End card — {name} logo and CTA button"},
    ]
    if (brief.get("target_seconds") or 30) <= 20:
        scenes = [scenes[0], scenes[1], scenes[3], scenes[4]]
    return scenes


def generate_script(brief, provider=None, key=None, model=None, base_url=None):
    """brief: {business, product, audience, offer, tone, language,
    target_seconds, platform}. Returns {scenes, source, ratio_hint}."""
    target = int(brief.get("target_seconds") or 30)
    ratio_hint = PLATFORMS.get(brief.get("platform") or "", "16:9")
    if key and provider:
        desc = (f"Business: {brief.get('business','')}\n"
                f"Promoting: {brief.get('product','')}\n"
                f"Audience: {brief.get('audience','')}\n"
                f"Offer: {brief.get('offer','')}\nTone: {brief.get('tone','Exciting')}\n"
                f"Language: {brief.get('language','English')}\n"
                f"Target length: {target} seconds\nPlatform: {brief.get('platform','')}")
        text = _ai_chat(provider, key, model, base_url, _SYSTEM + "\n\n" + desc)
        scenes = _assign_durations(_parse_scenes(text), target)
        return {"scenes": scenes, "source": "ai", "ratio_hint": ratio_hint,
                "label": f"AI script via {provider}"}
    scenes = _assign_durations(builtin_script(brief), target)
    return {"scenes": scenes, "source": "basic", "ratio_hint": ratio_hint,
            "label": "Basic script (no AI key)"}


_SLOGANS = [
    "{business} — {offer}!",
    "Discover {product} at {business} today!",
    "{business}: quality you can trust.",
    "Don't miss {offer} — only at {business}!",
    "{product}, made for you — by {business}.",
]


def slogan_ideas(brief, provider=None, key=None, model=None, base_url=None):
    """Jingle/AI-helper: 3 short slogan lines (AI with key, formulas without)."""
    if key and provider:
        prompt = (f"Write exactly 3 short advertising slogan lines (each under "
                  f"100 chars) for: business={brief.get('business','')}, "
                  f"product={brief.get('product','')}, offer={brief.get('offer','')}. "
                  f"One per line, no numbering, no quotes.")
        text = _ai_chat(provider, key, model, base_url, prompt)
        lines = [ln.strip(" -•\t") for ln in text.splitlines() if ln.strip()]
        lines = [ln for ln in lines if 3 <= len(ln) <= 125][:3]
        if lines:
            return {"lines": lines, "source": "ai"}
    import random
    rnd = random.Random(hash(brief.get("business", "")) & 0xFFFF)
    picks = rnd.sample(_SLOGANS, 3)
    return {"lines": [_fill(p, brief)[:125] for p in picks], "source": "basic"}


# ------------------------------------------------- paste-a-script (VEED)
def split_script_local(text, target_seconds=30):
    """Sentence/paragraph split with a per-scene word budget (~2.2 w/s)."""
    text = (text or "").strip()
    if not text:
        raise ValueError("Paste a script first.")
    budget = max(6, int(target_seconds * 2.2 / max(1, round(target_seconds / 5))))
    parts = []
    for para in re.split(r"\n\s*\n", text):
        for sent in re.split(r"(?<=[.!?।])\s+", para.replace("\n", " ")):
            if sent.strip():
                parts.append(sent.strip())
    scenes, cur = [], ""
    for p in parts:
        trial = (cur + " " + p).strip()
        if len(trial.split()) <= budget or not cur:
            cur = trial
        else:
            scenes.append(cur)
            cur = p
    if cur:
        scenes.append(cur)
    out = [{"on_screen_text": (s[:40] + "…") if len(s) > 41 else s,
            "voiceover_line": s, "visual_note": "Assigned photo / themed background"}
           for s in scenes[:12]]
    return _assign_durations(out, target_seconds)


def split_script(text, target_seconds=30, provider=None, key=None,
                 model=None, base_url=None):
    if key and provider:
        prompt = (_SYSTEM + f"\n\nSplit this pasted script into scenes for a "
                  f"{target_seconds}-second promo, keeping the wording:\n\n"
                  + (text or "")[:4000])
        scenes = _assign_durations(_parse_scenes(
            _ai_chat(provider, key, model, base_url, prompt)), target_seconds)
        return {"scenes": scenes, "source": "ai"}
    return {"scenes": split_script_local(text, target_seconds), "source": "basic"}
