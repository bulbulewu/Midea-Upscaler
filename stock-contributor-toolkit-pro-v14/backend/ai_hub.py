"""
AI Creativity Hub (Phase 4) — bring your OWN free / free-tier AI API keys.

Providers (all optional, keys are NEVER stored server-side — sent
per-request from your browser only, exactly like Gemini/Apify before):

  gemini       Google Gemini — genuine free tier via AI Studio
               https://aistudio.google.com/apikey
  grok         Grok by xAI — uses your xAI key (xAI runs promos/credits;
               a permanent free tier is NOT guaranteed — the app works
               with whatever credits your key has)
               https://console.x.ai
  groq         Groq (different company from Grok!) — free tier, very fast
               Llama / Mixtral models
               https://console.groq.com/keys
  openrouter   OpenRouter — many models tagged `:free` cost $0
               https://openrouter.ai/keys
  huggingface  Hugging Face Inference — free token, thousands of models
               https://huggingface.co/settings/tokens
  custom       Any OpenAI-compatible endpoint you paste (base URL + key)

Also built-in, no key at all:
  Pollinations concept-art URLs (free image generation) — handled in UI.

What it creates, aimed at commercial stock demand (international buyers):
  stock-brief     : shoot/produce brief for a topic buyers search for
  metadata-pack   : Adobe Stock title (<=70c) + description + 49 keywords
  motion-concept  : motion-graphics/video concept + script + on-screen text
  social-pack     : captions + hashtags for Reel/TikTok/Shorts/Pinterest
  titles-keywords : 10 commercial titles + keyword sets for a niche
Output language is selectable (English default — stock's buying language —
plus Bangla, Hindi, Spanish, Arabic, French, German, Portuguese…).
"""

import json
import urllib.parse
import urllib.request

# provider -> (kind, default model, signup hint)
PROVIDERS = {
    "gemini": {
        "label": "Google Gemini (free tier)",
        "kind": "gemini",
        "default_model": "gemini-2.0-flash",
        "get_key": "aistudio.google.com/apikey",
    },
    "grok": {
        "label": "Grok — xAI (your key/credits)",
        "kind": "openai",
        "base": "https://api.x.ai/v1",
        "default_model": "grok-3-mini",
        "get_key": "console.x.ai",
    },
    "groq": {
        "label": "Groq (free tier, fast Llama)",
        "kind": "openai",
        "base": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "get_key": "console.groq.com/keys",
    },
    "openrouter": {
        "label": "OpenRouter (:free models = $0)",
        "kind": "openai",
        "base": "https://openrouter.ai/api/v1",
        "default_model": "meta-llama/llama-3.3-70b-instruct:free",
        "get_key": "openrouter.ai/keys",
    },
    "huggingface": {
        "label": "Hugging Face (free token)",
        "kind": "openai",
        "base": "https://router.huggingface.co/v1",
        "default_model": "meta-llama/Llama-3.1-8B-Instruct",
        "get_key": "huggingface.co/settings/tokens",
    },
    "custom": {
        "label": "Custom OpenAI-compatible API",
        "kind": "openai",
        "base": "",
        "default_model": "",
        "get_key": "your provider",
    },
    "mistral": {
        "label": "Mistral AI (free tier, Pixtral vision)",
        "kind": "openai",
        "base": "https://api.mistral.ai/v1",
        "default_model": "pixtral-12b-2409",
        "get_key": "console.mistral.ai/api-keys",
    },
    "ollama": {
        "label": "Ollama — local / your VPS (no key needed)",
        "kind": "openai",
        "base": "http://localhost:11434/v1",
        "default_model": "llava",
        "get_key": "ollama.com (runs locally)",
    },
}

TASKS = {
    "stock-brief": (
        "Create a COMMERCIAL STOCK PRODUCTION BRIEF for the topic below, aimed at "
        "international buyers on Adobe Stock / Shutterstock / Freepik. Include: "
        "1) buyer demand angle (who buys this and why), 2) 5 concrete shoot/design "
        "concepts, 3) composition, lighting and colour direction to international "
        "standard, 4) props/wardrobe/location checklist, 5) pitfalls & legal notes "
        "(model/property releases, trademarks), 6) best formats & orientations to deliver."),
    "metadata-pack": (
        "Create an ADOBE STOCK METADATA PACK for the asset described below: "
        "a title of at most 70 characters (natural sentence, no commas), a one-sentence "
        "factual description, then EXACTLY 49 single-concept lowercase keywords ordered "
        "by buyer relevance (strongest first 10). No brand/trademark terms."),
    "motion-concept": (
        "Create a MOTION GRAPHICS / STOCK VIDEO CONCEPT for the topic below that a "
        "freelancer could produce with a template-based editor: hook in first 2 seconds, "
        "shot-by-shot storyboard with timings, on-screen text (exact words), motion style "
        "(Ken Burns/parallax/kinetic type etc.), music mood, export specs for 16:9, 9:16 "
        "and 1:1, plus Adobe Stock title + 20 keywords for the finished clip."),
    "social-pack": (
        "Create a SOCIAL SELLING PACK for the stock asset/topic below: 3 caption options "
        "(professional, friendly, sales), 25 hashtags mixing reach + niche buyer tags, "
        "best posting times (GMT + US/EU), and a Pinterest pin title + description."),
    "titles-keywords": (
        "For the niche below, list 10 COMMERCIAL STOCK CONCEPTS. For each: a sellable "
        "title (<=70 chars), why international buyers need it, and 15 buyer keywords. "
        "Focus on proven business demand: business, technology, health, education, "
        "finance, sustainability, festivals and remote work."),
}


def _post_json(url, payload, headers=None, timeout=90):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 "User-Agent": "stock-toolkit-pro/ai-hub", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8") or "{}")


def _gemini(key, model, prompt, timeout=90):
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           + urllib.parse.quote(model or PROVIDERS["gemini"]["default_model"])
           + ":generateContent?key=" + urllib.parse.quote(key))
    data = _post_json(url, {"contents": [{"parts": [{"text": prompt}]}],
                            "generationConfig": {"temperature": 0.8}}, timeout=timeout)
    parts = data["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in parts).strip()


def _openai_style(provider, key, model, prompt, base_override=None, timeout=90):
    cfg = PROVIDERS[provider]
    base = (base_override or cfg["base"]).rstrip("/")
    if not base:
        raise ValueError("Enter the custom API base URL (e.g. https://api.example.com/v1).")
    data = _post_json(base + "/chat/completions",
                      {"model": model or cfg["default_model"],
                       "messages": [{"role": "user", "content": prompt}],
                       "temperature": 0.8},
                      headers={"Authorization": f"Bearer {key}"}, timeout=timeout)
    return (data["choices"][0]["message"]["content"] or "").strip()


def generate(provider, key, task, topic, *, model=None, language="English",
             base_url=None, timeout=90):
    provider = (provider or "gemini").strip().lower()
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown provider '{provider}'.")
    key = (key or "").strip()
    if not key:
        raise ValueError(f"Paste your {PROVIDERS[provider]['label']} API key first — it is never stored.")
    if task not in TASKS:
        raise ValueError(f"Unknown task '{task}'.")
    topic = (topic or "").strip()
    if not topic:
        raise ValueError("Describe your topic / asset / niche first.")
    prompt = (f"{TASKS[task]}\n\nTopic / asset / niche: {topic}\n"
              f"Write the answer in {language or 'English'}. Be specific and practical; "
              f"format with clear headings. This is for a professional stock contributor "
              f"who sells internationally.")
    if PROVIDERS[provider]["kind"] == "gemini":
        text = _gemini(key, model, prompt, timeout)
    else:
        text = _openai_style(provider, key, model, prompt, base_url, timeout)
    if not text:
        raise RuntimeError("The provider returned an empty response — try again or another model.")
    return {"provider": provider, "label": PROVIDERS[provider]["label"],
            "model": model or PROVIDERS[provider]["default_model"],
            "task": task, "language": language or "English", "text": text}


def test_key(provider, key, model=None, base_url=None, timeout=45):
    """Minimal real call. Returns {ok, label, model, error?} — never raises."""
    provider = (provider or "gemini").strip().lower()
    if provider not in PROVIDERS:
        return {"ok": False, "error": f"Unknown provider '{provider}'."}
    if provider == "ollama" and not (key or "").strip():
        key = "ollama"  # local Ollama ignores auth; placeholder so the call runs
    if not (key or "").strip():
        return {"ok": False, "error": "No key pasted."}
    try:
        if PROVIDERS[provider]["kind"] == "gemini":
            out = _gemini(key.strip(), model, "Reply with exactly: OK", timeout)
        else:
            out = _openai_style(provider, key.strip(), model, "Reply with exactly: OK",
                                 base_url, timeout)
        return {"ok": True, "label": PROVIDERS[provider]["label"],
                "model": model or PROVIDERS[provider]["default_model"],
                "reply": out[:40]}
    except urllib.error.HTTPError as e:
        hint = {401: "Key rejected (401) — check the key / provider.",
                403: "Forbidden (403) — key has no access to this model, try another model.",
                404: "Model not found (404) — check the model name.",
                429: "Rate limit / free quota hit (429) — key works, just wait or check quota."}
        ok = e.code == 429  # 429 proves the key authenticated
        return {"ok": ok, "error": hint.get(e.code, f"HTTP {e.code} from provider."),
                "label": PROVIDERS[provider]["label"]}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"Could not complete test: {e}",
                "label": PROVIDERS[provider]["label"]}


# ---------------------------------------------------------------------------
# v5: reference-image analysis ("AI brain" for Motion Graphics)

_REF_PROMPT = """You are a senior motion-graphics art director for stock marketplaces (Adobe Stock, Shutterstock).
Analyse the attached reference image / screenshot and design a matching motion graphic.
Reply with ONLY a JSON object, no markdown, with keys:
{"kind": one of KINDS, "theme": one of THEMES, "headline": "short main text (max 6 words)", "subtext": "short tagline (max 10 words)", "brief": "2-3 sentence art-direction brief: colours, mood, how the motion should feel, and why it fits stock buyers"}
KINDS = bg-gradient, bg-particles, bg-bokeh, bg-waves, bg-confetti, bg-geometric, bg-light-trails, bg-hexwave, bg-equalizer, bg-vortex, bg-burst, title-cinematic, title-bold, lower-third, logo-reveal, intro-sting, greeting-card
THEMES = gold, teal, violet, crimson, ocean, rose"""


def analyze_reference(provider, api_key, model, image_path):
    """Vision analysis of a reference image -> motion-graphics design suggestion.
    Returns dict(kind, theme, headline, subtext, brief). Key never stored."""
    import base64, os, re  # noqa
    provider = (provider or "gemini").strip().lower()
    if provider not in PROVIDERS:
        raise ValueError("Unknown provider.")
    cfg = PROVIDERS[provider]
    if not (api_key or "").strip():
        raise ValueError(f"Paste your {cfg['label']} API key first (free: {cfg['get_key']}).")
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    ext = os.path.splitext(image_path)[1].lower().lstrip(".")
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
            "webp": "image/webp", "gif": "image/gif"}.get(ext, "image/png")
    try:
        if cfg["kind"] == "gemini":
            mdl = (model or cfg["default_model"]).strip()
            url = ("https://generativelanguage.googleapis.com/v1beta/models/"
                   + urllib.parse.quote(mdl) + ":generateContent?key="
                   + urllib.parse.quote(api_key.strip()))
            data = _post_json(url, {"contents": [{"parts": [
                {"text": _REF_PROMPT},
                {"inline_data": {"mime_type": mime, "data": b64}}]}]}, timeout=120)
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        elif provider == "huggingface":
            raise ValueError("Hugging Face free rarely hosts vision models - use Gemini (free), Groq (free), Grok or OpenRouter.")
        elif provider == "custom":
            raise ValueError("Custom endpoints vary - use Gemini, Groq, Grok or OpenRouter for image analysis.")
        else:
            mdl = (model or cfg["default_model"]).strip()
            if provider == "groq" and "vision" not in mdl and "llama-4" not in mdl:
                mdl = "meta-llama/llama-4-scout-17b-16e-instruct"
            if provider == "grok" and "vision" not in mdl:
                mdl = "grok-2-vision-1212"
            data = _post_json(cfg["base"].rstrip("/") + "/chat/completions",
                              {"model": mdl, "messages": [{"role": "user", "content": [
                                  {"type": "text", "text": _REF_PROMPT},
                                  {"type": "image_url",
                                   "image_url": {"url": f"data:{mime};base64,{b64}"}}]}]},
                              headers={"Authorization": f"Bearer {api_key.strip()}"},
                              timeout=120)
            text = data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{cfg['label']} error {e.code}: {e.read().decode('utf-8', 'ignore')[:250]}")
    m = re.search(r"\{.*\}", text or "", re.DOTALL)
    if not m:
        raise RuntimeError("The AI did not return a usable design. Try again or pick a template manually.")
    d = json.loads(m.group(0))
    from . import mgfx
    if d.get("kind") not in mgfx.CATALOG:
        d["kind"] = "bg-gradient"
    if d.get("theme") not in mgfx.THEMES:
        d["theme"] = "gold"
    return {"kind": d["kind"], "theme": d["theme"],
            "headline": str(d.get("headline", ""))[:80],
            "subtext": str(d.get("subtext", ""))[:120],
            "brief": str(d.get("brief", ""))[:600]}
