"""
Subtopic Creator (v11, Prompt #4 Job C) — the owner's brainstorming
workflow: ONE main topic in -> EXACTLY 50 subtopics out.

Sources, in order (buyer-first ranking):
  1. Apify — real Google related searches / related queries for the
     topic via the existing enrichment path (apify_intel.enrich_keyword),
     using the USER's own free Apify token when one is supplied.
  2. Datamuse — the app's existing free keyword expansion
     (metadata.expand_keywords).
  3. Pattern filler — if unique candidates are still < 50, a
     code-visible modifier library completes the list
     ("{topic} background", "{topic} seamless pattern", ...).

`engine` in the result states honestly which sources contributed.
A supplied-but-failing Apify token never blocks the result: the column
is still filled from the free sources and `apify_failed` is True so the
UI can show the warning (the app's no-silent-fallback rule).
"""

import re

from . import apify_intel
from .metadata import expand_keywords

TARGET = 50

# Code-visible modifier library (>= 40 templates). "{t}" = the topic.
# Extra words per template are kept <= 3 so topic + modifier stays
# inside the 2-6 word subtopic rule for typical 1-3 word topics.
MODIFIER_TEMPLATES = [
    "{t} background", "{t} seamless pattern", "{t} flat vector illustration",
    "{t} watercolor", "{t} 3d render", "{t} isolated on white",
    "{t} for kids", "{t} mockup scene", "{t} greeting card",
    "{t} poster design", "{t} banner template", "{t} social media post",
    "{t} logo design", "{t} icon set", "{t} sticker pack",
    "{t} t-shirt design", "{t} mug design", "{t} phone wallpaper",
    "{t} desktop wallpaper", "{t} pattern texture", "{t} border frame",
    "{t} ornament design", "{t} label design", "{t} badge design",
    "{t} invitation card", "{t} party decoration", "{t} gift wrapping",
    "{t} sale banner", "{t} discount poster", "{t} advertising background",
    "{t} website hero", "{t} presentation background", "{t} book cover",
    "{t} youtube thumbnail", "{t} instagram story", "{t} facebook cover",
    "{t} business card", "{t} flyer template", "{t} menu design",
    "{t} packaging design", "{t} fabric print", "{t} nursery decor",
    "{t} wedding invitation", "{t} birthday card", "{t} calendar design",
    "{t} notebook cover", "{t} tote bag print", "{t} pillow print",
    "{t} canvas wall art", "{t} digital paper", "{t} clipart set",
    "{t} sublimation design", "{t} laser cut design", "{t} embroidery pattern",
]

# Single-word suffixes for the guarantee round ("{t} design", ...).
_SUFFIX_WORDS = [
    "design", "art", "concept", "theme", "style", "decor", "print",
    "card", "poster", "banner", "cover", "template", "pattern",
    "texture", "wallpaper", "illustration", "vector", "drawing",
    "painting", "sketch", "clipart", "icon", "logo", "sticker",
    "label", "badge", "frame", "border", "ornament", "motif",
    "scene", "mockup", "photo", "image", "graphic", "element",
    "set", "collection", "bundle", "ideas", "inspiration",
]


def _clean(text):
    t = re.sub(r"[^a-z0-9\s\-']", " ", str(text or "").lower())
    return re.sub(r"\s+", " ", t).strip(" -'")


def _ok(phrase, topic):
    words = phrase.split()
    return 2 <= len(words) <= 6 and phrase != topic


def generate_subtopics(topic, token=None, exclude=None):
    """Return {topic, subtopics: [EXACTLY 50], engine, apify_failed,
    sources}. Never raises for source failures."""
    topic = _clean(topic)
    if not topic:
        raise ValueError("Enter a main topic first.")
    seen = {_clean(e) for e in (exclude or []) if _clean(e)}
    seen.add(topic)
    out = []
    used = {"apify": False, "datamuse": False, "patterns": False}

    def add(phrase, source):
        ph = _clean(phrase)
        if ph and ph not in seen and _ok(ph, topic):
            seen.add(ph)
            out.append(ph)
            used[source] = True
            return True
        return False

    # 1) Apify first — real related searches buyers type
    apify_failed = False
    token = apify_intel.resolve_token(token)
    if token:
        res = apify_intel.enrich_keyword(topic, token, max_results=25)
        if res.get("ok"):
            for ph in res.get("related_phrases", []):
                add(ph, "apify")
        else:
            apify_failed = True

    # 2) Datamuse expansion (free, no key) — merged, buyer-first order
    dm = expand_keywords([topic], per_seed=10)
    for w in dm:
        add(w, "datamuse")
        if len(w.split()) == 1:
            add(f"{topic} {w}", "datamuse")

    # 3) pattern filler from the modifier library
    for tpl in MODIFIER_TEMPLATES:
        if len(out) >= TARGET:
            break
        add(tpl.format(t=topic), "patterns")
    # guarantee round 1: datamuse candidates + short modifiers
    if len(out) < TARGET:
        for w in dm[:20]:
            for mod in ("background", "illustration", "design", "pattern",
                        "vector", "art"):
                if len(out) >= TARGET:
                    break
                add(f"{w} {mod}", "patterns")
            if len(out) >= TARGET:
                break
    # guarantee round 2: topic + suffix words, then suffix + topic
    if len(out) < TARGET:
        for w in _SUFFIX_WORDS:
            if len(out) >= TARGET:
                break
            add(f"{topic} {w}", "patterns")
    if len(out) < TARGET:
        for w in _SUFFIX_WORDS:
            if len(out) >= TARGET:
                break
            add(f"{w} {topic}", "patterns")

    parts = []
    if used["apify"]:
        parts.append("apify")
    if used["datamuse"]:
        parts.append("datamuse")
    if used["patterns"]:
        parts.append("patterns")
    engine = " + ".join(parts) if parts else "patterns"
    if not token:
        engine += " (no Apify token)"
    elif apify_failed:
        engine += " (Apify failed — free sources used)"
    return {"topic": topic, "subtopics": out[:TARGET], "engine": engine,
            "apify_failed": apify_failed, "sources": parts}
