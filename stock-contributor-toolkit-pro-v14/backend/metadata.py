"""
Metadata engine for stock contributors.

Free built-in pipeline (no API key):
  image analysis (PIL) -> filename parsing -> Datamuse keyword expansion
  -> ordered keyword list (max 49, first-10 weighted) -> title (<=70 chars)
  -> description -> CSV export (Adobe Stock format).

Optional AI upgrade: user supplies their own Gemini API key per request
(never stored server-side) for image-grounded title/keywords.
"""

import base64
import csv
import io
import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from PIL import Image, ImageStat

# ---------------------------------------------------------------- constants

MAX_KEYWORDS = 49          # Adobe Stock maximum
MIN_KEYWORDS = 5           # Adobe Stock minimum
TITLE_MAX = 70             # Adobe recommended title length
FIRST_N_WEIGHTED = 10      # first N keywords carry the most ranking weight

STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "in", "on", "at", "to", "for",
    "with", "by", "from", "is", "are", "was", "were", "it", "its", "this",
    "that", "as", "be", "up", "out", "img", "image", "photo", "picture",
    "png", "jpg", "jpeg", "final", "copy", "new", "untitled", "dsc", "px",
}

COLOR_NAMES = [
    ("red", (200, 40, 40)), ("orange", (230, 130, 30)), ("yellow", (230, 210, 60)),
    ("green", (60, 170, 80)), ("teal", (50, 160, 160)), ("blue", (60, 120, 210)),
    ("purple", (130, 80, 180)), ("pink", (230, 130, 180)), ("brown", (130, 90, 60)),
    ("white", (235, 235, 235)), ("gray", (140, 140, 140)), ("black", (35, 35, 35)),
]

MOODS = [
    ("bright", lambda b: b > 175), ("dark", lambda b: b < 70),
    ("high contrast", None), ("soft light", None),
]

DATAMUSE = "https://api.datamuse.com/words"


# ---------------------------------------------------------------- image analysis

def _nearest_color(rgb):
    best, best_d = "multicolor", 1e9
    for name, crgb in COLOR_NAMES:
        d = sum((a - b) ** 2 for a, b in zip(rgb, crgb))
        if d < best_d:
            best, best_d = name, d
    return best


def analyze_image(path):
    """Return visual facts: size, orientation, dominant colors, brightness."""
    with Image.open(path) as im:
        w, h = im.size
        rgb = im.convert("RGB")
        small = rgb.resize((64, 64))
        stat = ImageStat.Stat(small)
        brightness = sum(stat.mean) / 3
        # dominant colors via quantization
        q = small.quantize(colors=6, method=Image.Quantize.MEDIANCUT)
        palette = q.getpalette()[:18]
        counts = sorted(q.getcolors(), reverse=True)
        dom = []
        for cnt, idx in counts[:3]:
            r, g, b = palette[idx * 3:idx * 3 + 3]
            dom.append(_nearest_color((r, g, b)))
        dom = [c for c in dict.fromkeys(dom) if c != "multicolor"][:3]

    orientation = "landscape" if w > h * 1.15 else "portrait" if h > w * 1.15 else "square"
    mood = "bright" if brightness > 175 else "dark" if brightness < 70 else "neutral"
    return {
        "width": w, "height": h, "orientation": orientation,
        "brightness": round(brightness, 1), "mood": mood,
        "colors": dom, "filename": os.path.basename(path),
    }


# ---------------------------------------------------------------- filename -> seeds

def keywords_from_filename(filename):
    stem = os.path.splitext(os.path.basename(filename))[0]
    stem = re.sub(r"(20\d{2}|19\d{2})", " ", stem)          # years
    stem = re.sub(r"\d{3,}", " ", stem)                     # long numbers (dsc_0042)
    tokens = re.split(r"[_\-\.\s,;|]+", stem.lower())
    words = []
    for t in tokens:
        t = re.sub(r"[^a-z]", "", t)
        if len(t) > 2 and t not in STOPWORDS and t not in words:
            words.append(t)
    return words[:12]


# ---------------------------------------------------------------- datamuse expansion

def _datamuse(params, timeout=12):
    url = DATAMUSE + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "stock-toolkit/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8") or "[]")
    except Exception:
        return []


def expand_keywords(seeds, per_seed=6, timeout=12):
    """
    Expand seed words into related buyer-facing keywords via Datamuse
    (free, no key). Returns ordered unique suggestions.
    """
    out, seen = [], set()
    for seed in seeds[:8]:
        for rel in ({"ml": seed}, {"rel_trg": seed}):
            for item in _datamuse({**rel, "max": per_seed}, timeout):
                w = item.get("word", "").lower().strip()
                if not w or w in seen or w in STOPWORDS:
                    continue
                if not re.fullmatch(r"[a-z][a-z \-']*", w):
                    continue
                seen.add(w)
                out.append(w)
                if len(out) >= 60:
                    return out
    return out


# ---------------------------------------------------------------- assembly

def _dedupe(words):
    seen, out = set(), []
    for w in words:
        k = w.lower().strip()
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return out


def build_title(keyword_list, analysis):
    """Natural sentence-style title, <= TITLE_MAX chars."""
    seeds = [k for k in keyword_list if " " not in k][:6]
    if not seeds:
        seeds = (analysis.get("colors") or []) + [analysis.get("orientation", "")]
    subject = seeds[0] if seeds else "abstract background"
    rest = " ".join(s for s in seeds[1:4] if s)
    mood = analysis.get("mood")
    mood_bit = {"bright": "in bright light", "dark": "in moody low light"}.get(mood, "")
    parts = [p for p in (subject, rest, mood_bit) if p]
    title = " ".join(parts).strip().capitalize()
    if len(title) > TITLE_MAX:
        title = title[:TITLE_MAX].rsplit(" ", 1)[0]
    return title


def build_description(title, keyword_list, analysis):
    core = ", ".join(keyword_list[:6])
    orient = analysis.get("orientation", "")
    return (f"{title}. Stock {orient} image featuring {core}. "
            f" ideal for commercial use, advertising and editorial design.")


def order_keywords(seeds, expanded, analysis):
    """
    Adobe-style ordering: strongest subject terms first (first 10 weighted),
    then attributes (color/mood/orientation), then supporting concepts.
    """
    attrs = (analysis.get("colors") or []) + [analysis.get("mood"), analysis.get("orientation")]
    attrs = [a for a in attrs if a and a != "neutral"]
    ordered = _dedupe(seeds + attrs + expanded)
    return ordered[:MAX_KEYWORDS]


def generate_metadata(image_path, extra_seeds=None, gemini_key=None):
    """
    Full pipeline for one image. Returns dict with title, description,
    keywords, analysis, and engine used.
    """
    analysis = analyze_image(image_path)
    seeds = keywords_from_filename(image_path)
    if extra_seeds:
        seeds = _dedupe([s.lower() for s in extra_seeds] + seeds)

    ai_used = False
    ai_title, ai_desc, ai_kw = None, None, None
    if gemini_key:
        try:
            ai_title, ai_desc, ai_kw = gemini_generate(image_path, gemini_key)
            ai_used = True
        except Exception:
            ai_used = False  # fall back to built-in engine silently

    if ai_used:
        keywords = _dedupe(ai_kw)[:MAX_KEYWORDS]
        title, desc = ai_title, ai_desc
    else:
        expanded = expand_keywords(seeds)
        keywords = order_keywords(seeds, expanded, analysis)
        title = build_title(keywords, analysis)
        desc = build_description(title, keywords, analysis)

    return {
        "filename": os.path.basename(image_path),
        "title": title,
        "description": desc,
        "keywords": keywords,
        "keyword_count": len(keywords),
        "analysis": analysis,
        "engine": "gemini" if ai_used else "builtin",
    }


# ---------------------------------------------------------------- gemini (optional, user key)

def gemini_generate(image_path, api_key, timeout=60):
    """
    Ask Gemini to produce stock metadata for the image. The key is used
    only for this request and never stored.
    """
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    ext = os.path.splitext(image_path)[1].lower()
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
            "webp": "image/webp"}.get(ext.lstrip("."), "image/jpeg")
    payload = {
        "contents": [{
            "parts": [
                {"inline_data": {"mime_type": mime, "data": b64}},
                {"text": (
                    "You are a microstock metadata expert. Analyze this image and return "
                    "STRICT JSON only: {\"title\": \"natural sentence <= 70 chars, no commas\", "
                    "\"description\": \"one factual sentence\", "
                    "\"keywords\": [\"up to 45 single-concept lowercase keywords ordered by relevance, "
                    "strongest first\"]}. No markdown, no extra text."
                )},
            ]
        }],
        "generationConfig": {"response_mime_type": "application/json",
                             "temperature": 0.4},
    }
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           "gemini-2.0-flash:generateContent?key=" + urllib.parse.quote(api_key))
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 "User-Agent": "stock-toolkit/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode())
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    parsed = json.loads(text)
    kws = [k.lower().strip() for k in parsed.get("keywords", []) if k.strip()]
    return (parsed.get("title", "")[:TITLE_MAX],
            parsed.get("description", ""),
            _dedupe(kws)[:MAX_KEYWORDS])


# ================================================================ v7 SEO Studio
# Part B of Prompt #2: marketplace rules, Auto-Extract, trademark shield,
# multi-format pipeline (EPS/SVG/AI/MP4/MOV), BYOK vision providers,
# multi-agency CSV, Image to Prompt. The v1 pipeline above is untouched
# and remains the default when no marketplace is requested.

import subprocess

SEO_EXTS = {".eps", ".svg", ".ai", ".mp4", ".mov"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}

# Per-agency rules from each agency's published contributor specs at build
# date (Oct 2026). Title/keyword numbers drive BOTH generation targets and
# the UI's green/amber/red validation. CSV column layouts follow the
# agencies' documented upload templates; where an exact template could not
# be verified offline, the closest documented layout is used (see README).
MARKETPLACE_RULES = {
    "adobe": {
        "label": "Adobe Stock", "title_min": 50, "title_max": 80,
        "max_keywords": 49, "use_description": True, "keyword_sep": ", ",
        "csv_fields": ["Filename", "Title", "Keywords", "Category", "Description"],
    },
    "shutterstock": {
        "label": "Shutterstock", "title_min": 25, "title_max": 200,
        "max_keywords": 50, "use_description": True, "keyword_sep": ", ",
        # Shutterstock's contributor CSV uses Description as the title field.
        "csv_fields": ["Filename", "Description", "Keywords", "Categories",
                       "Editorial", "Illustration", "Mature content", "Location"],
    },
    "pond5": {
        "label": "Pond5", "title_min": 10, "title_max": 100,
        "max_keywords": 50, "use_description": True, "keyword_sep": ", ",
        "csv_fields": ["Filename", "Title", "Description", "Keywords", "Price"],
    },
    "freepik": {
        "label": "Freepik / Magnific", "title_min": 10, "title_max": 100,
        "max_keywords": 50, "use_description": False, "keyword_sep": ", ",
        "csv_fields": ["Filename", "Title", "Keywords"],
    },
    "dreamstime": {
        "label": "Dreamstime", "title_min": 8, "title_max": 70,
        "max_keywords": 50, "use_description": True, "keyword_sep": ", ",
        "csv_fields": ["Filename", "Title", "Description", "Keywords", "Category"],
    },
    "vecteezy": {
        "label": "Vecteezy", "title_min": 10, "title_max": 100,
        "max_keywords": 50, "use_description": False, "keyword_sep": ", ",
        "csv_fields": ["Filename", "Title", "Keywords", "License"],
    },
    "depositphotos": {
        "label": "Depositphotos", "title_min": 10, "title_max": 100,
        "max_keywords": 50, "use_description": True, "keyword_sep": ", ",
        "csv_fields": ["Filename", "Title", "Description", "Keywords", "Categories"],
    },
    "rf123": {
        "label": "123RF", "title_min": 10, "title_max": 100,
        "max_keywords": 50, "use_description": True, "keyword_sep": ", ",
        "csv_fields": ["Filename", "Title", "Description", "Keywords"],
    },
    "universal": {
        "label": "Universal (All)", "title_min": 25, "title_max": 100,
        "max_keywords": 50, "use_description": True, "keyword_sep": ", ",
        "csv_fields": ["Filename", "Title", "Keywords", "Category", "Description"],
    },
}


def _rules(marketplace):
    return MARKETPLACE_RULES.get(marketplace or "adobe", MARKETPLACE_RULES["adobe"])


def fit_title(title, rules, keywords=None):
    """Fit a title into the marketplace's char range: truncate at a word
    boundary when too long; pad with strongest keyword phrases when short."""
    title = re.sub(r"\s+", " ", (title or "").strip())
    mx, mn = rules["title_max"], rules["title_min"]
    if len(title) > mx:
        title = title[:mx].rsplit(" ", 1)[0].rstrip(",;:")
    if len(title) < mn and keywords:
        extra = [k for k in keywords if k.lower() not in title.lower()]
        for k in extra:
            cand = f"{title} with {k}" if title else k.capitalize()
            if len(cand) > mx:
                break
            title = cand
            if len(title) >= mn:
                break
    return title


# ---------------------------------------------------------------- trademarks

_TRADEMARK_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "data", "trademarks.txt")
_TRADEMARKS = None


def load_trademarks():
    global _TRADEMARKS
    if _TRADEMARKS is None:
        terms = []
        try:
            with open(_TRADEMARK_PATH, encoding="utf-8") as f:
                for line in f:
                    t = line.strip().lower()
                    if t and not t.startswith("#"):
                        terms.append(t)
        except OSError:
            terms = []
        # longest first so multi-word brands match before single words
        _TRADEMARKS = sorted(set(terms), key=len, reverse=True)
    return _TRADEMARKS


def _contains_term(text, term):
    return re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])",
                     (text or "").lower()) is not None


def screen_trademarks(title, keywords):
    """
    Trademark shield: remove blacklisted brand terms from keywords and
    title, return (title, keywords, removed_terms). Stock agencies reject
    or de-rank assets naming brands the contributor doesn't own.
    """
    removed = []
    kept = []
    for kw in keywords or []:
        hit = next((t for t in load_trademarks() if _contains_term(kw, t)), None)
        if hit:
            if hit not in removed:
                removed.append(hit)
        else:
            kept.append(kw)
    new_title = title or ""
    for t in load_trademarks():
        if _contains_term(new_title, t):
            if t not in removed:
                removed.append(t)
            new_title = re.sub(r"(?<![A-Za-z0-9])" + re.escape(t) + r"(?![A-Za-z0-9])",
                               "", new_title, flags=re.IGNORECASE)
    new_title = re.sub(r"\s{2,}", " ", new_title).strip(" ,;-").strip()
    if new_title:
        new_title = new_title[0].upper() + new_title[1:]
    return new_title, kept, removed


# ---------------------------------------------------------------- extract

def _xmp_fields(xmp_text):
    """Pull dc:title / dc:description / dc:subject / xmp:Rating from an XMP packet."""
    out = {}
    if not xmp_text:
        return out
    def _alt(tag):
        m = re.search(tag + r".*?<rdf:li[^>]*>(.*?)</rdf:li>", xmp_text, re.DOTALL)
        return m.group(1).strip() if m else None
    t = _alt(r"dc:title")
    if t:
        out["title"] = t
    d = _alt(r"dc:description")
    if d:
        out["description"] = d
    subs = re.findall(r"dc:subject.*?<rdf:li[^>]*>(.*?)</rdf:li>", xmp_text, re.DOTALL)
    # the regex above returns group-less matches; do it properly:
    m = re.search(r"dc:subject[^>]*>\s*<rdf:Bag>(.*?)</rdf:Bag>", xmp_text, re.DOTALL)
    if m:
        out["keywords"] = [re.sub(r"<[^>]+>", "", x).strip()
                           for x in re.findall(r"<rdf:li[^>]*>(.*?)</rdf:li>", m.group(1))]
    m = re.search(r'xmp:Rating="(\d)"', xmp_text)
    if m:
        out["rating"] = int(m.group(1))
    return out


def _extract_iptc_iim(raw):
    """Best-effort IPTC-IIM scan (JPEG Photoshop IRB blocks): dataset
    2:105 headline, 2:120 caption, 2:25 keywords (repeatable)."""
    out = {"keywords": []}
    i = 0
    while True:
        j = raw.find(b"\x1c\x02", i)
        if j < 0 or j + 5 > len(raw):
            break
        ds = raw[j + 2]
        ln = int.from_bytes(raw[j + 3:j + 5], "big")
        if ln > 4096 or j + 5 + ln > len(raw):
            i = j + 2
            continue
        val = raw[j + 5:j + 5 + ln].decode("utf-8", "ignore").strip()
        if ds == 105 and val:
            out["title"] = val
        elif ds == 120 and val:
            out["description"] = val
        elif ds == 25 and val:
            out["keywords"].append(val.lower())
        i = j + 5 + ln
    if not out["keywords"]:
        out.pop("keywords")
    return out


def extract_metadata(path):
    """
    Auto-Extract: read metadata already embedded in the file.
    Returns {} or {title?, description?, keywords?, rating?, source}.
    Sources: XMP packet, EXIF (piexif/Pillow), IPTC-IIM (JPEG), SVG
    <metadata>/<title>/<desc>, MP4/MOV ffmpeg tags.
    """
    ext = os.path.splitext(path)[1].lower()
    found = {}
    try:
        if ext in (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"):
            with open(path, "rb") as f:
                raw = f.read(4 * 1024 * 1024)
            m = re.search(r"<x:xmpmeta.*?</x:xmpmeta>", raw.decode("utf-8", "ignore"),
                          re.DOTALL)
            if m:
                found.update(_xmp_fields(m.group(0)))
            if ext in (".jpg", ".jpeg"):
                found_iptc = _extract_iptc_iim(raw)
                for k, v in found_iptc.items():
                    found.setdefault(k, v)
            try:
                import piexif
                ex = piexif.load(path, key_is_name=True)
                zeroth = ex.get("0th", {})
                desc = zeroth.get("ImageDescription")
                if desc and "description" not in found:
                    found["description"] = str(desc).strip()
            except Exception:  # noqa: BLE001
                pass
            try:
                with Image.open(path) as im:
                    if ext == ".png" and getattr(im, "text", None):
                        for k in ("Title", "Description", "Comment"):
                            if im.text.get(k) and k.lower() not in found:
                                found[k.lower()] = im.text[k]
            except Exception:  # noqa: BLE001
                pass
        elif ext in (".svg",):
            with open(path, encoding="utf-8", errors="ignore") as f:
                text = f.read(2 * 1024 * 1024)
            found.update(_xmp_fields(text))
            for tag, key in (("title", "title"), ("desc", "description")):
                m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", text, re.DOTALL)
                if m and key not in found:
                    found[key] = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        elif ext in (".mp4", ".mov"):
            info = probe_video(path)
            tags = info.get("tags") or {}
            if tags.get("title"):
                found["title"] = tags["title"]
            if tags.get("description") or tags.get("comment"):
                found["description"] = tags.get("description") or tags.get("comment")
            kw = tags.get("keywords") or tags.get("comment")
            if kw and kw != found.get("description"):
                found["keywords"] = [k.strip().lower() for k in re.split(r"[,;]", kw) if k.strip()]
    except Exception:  # noqa: BLE001
        return {}
    found = {k: v for k, v in found.items() if v}
    if found:
        found["source"] = "extracted"
    return found


def probe_video(path):
    """ffprobe: duration / resolution / format tags for MP4/MOV."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_format", "-show_streams",
             "-of", "json", path], capture_output=True, text=True, timeout=30)
        data = json.loads(out.stdout or "{}")
    except Exception:  # noqa: BLE001
        return {}
    info = {"tags": (data.get("format") or {}).get("tags") or {}}
    try:
        info["duration"] = round(float((data.get("format") or {}).get("duration", 0)), 1)
    except Exception:  # noqa: BLE001
        info["duration"] = 0
    for st in data.get("streams", []):
        if st.get("codec_type") == "video":
            info["width"], info["height"] = st.get("width", 0), st.get("height", 0)
            break
    return info


def video_frame_png(path, out_png, at_seconds=1):
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(at_seconds), "-i", path,
                        "-frames:v", "1", "-y", out_png],
                       capture_output=True, text=True, timeout=60)
    return r.returncode == 0 and os.path.isfile(out_png)


def file_kind(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext in (".svg", ".eps", ".ai"):
        return "vector"
    if ext in (".mp4", ".mov"):
        return "video"
    return "unknown"


def preview_data_url(path, workdir):
    """Small JPEG preview (data URL) for vectors/videos; None for images
    (browser uses the file itself) or when rendering is impossible."""
    ext = os.path.splitext(path)[1].lower()
    png = os.path.join(workdir, "prev_" + os.path.basename(path) + ".png")
    try:
        if ext == ".svg":
            from .svg_render import render_svg_to_png
            render_svg_to_png(path, png, 480, 480)
        elif ext in (".mp4", ".mov"):
            if not video_frame_png(path, png):
                return None
        else:
            return None
        with Image.open(png) as im:
            im = im.convert("RGB")
            im.thumbnail((420, 420))
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=72)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:  # noqa: BLE001
        return None
    finally:
        try:
            os.remove(png)
        except OSError:
            pass


def analysis_for(path, workdir):
    """Visual analysis for any supported file kind (best effort)."""
    kind = file_kind(path)
    base = {"width": 0, "height": 0, "orientation": "", "mood": "",
            "colors": [], "filename": os.path.basename(path), "kind": kind}
    try:
        if kind == "image":
            return {**analyze_image(path), "kind": "image"}
        if kind == "video":
            info = probe_video(path)
            base.update({"width": info.get("width", 0), "height": info.get("height", 0),
                         "duration": info.get("duration", 0)})
            thumb = os.path.join(workdir, "th_" + os.path.basename(path) + ".png")
            if video_frame_png(path, thumb):
                try:
                    a = analyze_image(thumb)
                    base.update({k: a[k] for k in ("orientation", "mood", "colors")})
                finally:
                    os.remove(thumb)
            return base
        if kind == "vector" and path.lower().endswith(".svg"):
            png = os.path.join(workdir, "an_" + os.path.basename(path) + ".png")
            from .svg_render import render_svg_to_png
            render_svg_to_png(path, png, 640, 640)
            try:
                a = analyze_image(png)
                return {**a, "kind": "vector"}
            finally:
                os.remove(png)
    except Exception:  # noqa: BLE001
        pass
    return base


# ---------------------------------------------------------------- csv export

ADOBE_CSV_FIELDS = ["Filename", "Title", "Keywords", "Category", "Description"]


def to_csv(rows):
    """rows: list of dicts with filename/title/keywords/category/description."""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=ADOBE_CSV_FIELDS, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        kws = r.get("keywords", [])
        if isinstance(kws, list):
            kws = ", ".join(kws)
        w.writerow({
            "Filename": r.get("filename", ""),
            "Title": r.get("title", ""),
            "Keywords": kws,
            "Category": r.get("category", ""),
            "Description": r.get("description", ""),
        })
    return buf.getvalue()


# ---------------------------------------------------------------- v7 pipeline

def _builtin_generate(path, extra_seeds, analysis, rules, isolated):
    seeds = keywords_from_filename(path)
    if extra_seeds:
        seeds = _dedupe([s.lower() for s in extra_seeds] + seeds)
    if isolated:
        seeds = _dedupe(["isolated"] + seeds)
    expanded = expand_keywords(seeds)
    keywords = order_keywords(seeds, expanded, analysis)[:rules["max_keywords"]]
    if isolated:
        for extra_kw in ("isolated on transparent background", "cut out",
                         "isolated", "transparent background"):
            if extra_kw not in keywords:
                keywords.append(extra_kw)
        keywords = keywords[:rules["max_keywords"] + 4][:rules["max_keywords"]]
    title = fit_title(build_title(keywords, analysis), rules, keywords)
    desc = build_description(title, keywords, analysis)
    if isolated:
        desc += " Isolated on a transparent background, cut out and ready to composite."
    return title, desc, keywords


def _vision_prompt(rules, isolated):
    iso = (" The asset is an isolated object on a transparent background — say so "
           "in the title and include isolated/cut-out keywords.") if isolated else ""
    return (
        "You are a microstock SEO expert. Analyse this asset and return STRICT JSON only: "
        "{\"title\": \"natural sentence, " + f'{rules["title_min"]}-{rules["title_max"]}' + " chars, no brand names\", "
        "\"description\": \"one factual sentence\", "
        "\"keywords\": [\"up to " + str(rules["max_keywords"]) + " single-concept lowercase keywords "
        "ordered by buyer relevance, strongest first 10, no brand/trademark names\"]}."
        + iso + " No markdown, no extra text.")


def provider_generate(path, provider, key, model=None, base_url=None,
                      rules=None, isolated=False, timeout=90):
    """
    BYOK vision metadata via ai_hub providers (Gemini / Groq / Mistral /
    OpenRouter / Grok / Ollama). Key is per-request, never stored.
    Returns (title, description, keywords). Raises on failure so the
    caller can fall back to the built-in engine and say so.
    """
    from . import ai_hub
    rules = rules or _rules("adobe")
    if provider not in ai_hub.PROVIDERS:
        raise ValueError(f"Unknown provider '{provider}'.")
    cfg = ai_hub.PROVIDERS[provider]
    key = (key or "").strip()
    if provider == "ollama" and not key:
        key = "ollama"
    if not key:
        raise ValueError("No API key supplied.")
    # vision needs a raster: render vectors / grab a video frame to PNG
    raster = path
    tmp = None
    ext = os.path.splitext(path)[1].lower()
    if ext == ".svg" or file_kind(path) == "video":
        tmp = path + ".vision.png"
        if ext == ".svg":
            from .svg_render import render_svg_to_png
            render_svg_to_png(path, tmp, 768, 768)
        elif not video_frame_png(path, tmp):
            raise ValueError("Could not extract a frame for vision analysis.")
        raster = tmp
    try:
        with open(raster, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        rext = os.path.splitext(raster)[1].lower().lstrip(".")
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                "webp": "image/webp"}.get(rext, "image/png")
        prompt = _vision_prompt(rules, isolated)
        mdl = (model or cfg["default_model"]).strip()
        if cfg["kind"] == "gemini":
            url = ("https://generativelanguage.googleapis.com/v1beta/models/"
                   + urllib.parse.quote(mdl) + ":generateContent?key="
                   + urllib.parse.quote(key))
            data = ai_hub._post_json(url, {"contents": [{"parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": mime, "data": b64}}]}],
                "generationConfig": {"response_mime_type": "application/json",
                                     "temperature": 0.4}}, timeout=timeout)
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        else:
            base = (base_url or cfg["base"]).rstrip("/")
            if not base:
                raise ValueError("Enter the API base URL for this provider.")
            if provider == "groq" and "vision" not in mdl and "llama-4" not in mdl:
                mdl = "meta-llama/llama-4-scout-17b-16e-instruct"
            if provider == "grok" and "vision" not in mdl:
                mdl = "grok-2-vision-1212"
            if provider == "ollama" and not any(v in mdl for v in ("llava", "vl", "vision", "gemma", "bakllava")):
                raise ValueError("Ollama model is text-only — pick a vision model like llava or qwen2.5-vl.")
            data = ai_hub._post_json(base + "/chat/completions",
                                     {"model": mdl, "messages": [{"role": "user", "content": [
                                         {"type": "text", "text": prompt},
                                         {"type": "image_url",
                                          "image_url": {"url": f"data:{mime};base64,{b64}"}}]}],
                                      "temperature": 0.4},
                                     headers={"Authorization": f"Bearer {key}"},
                                     timeout=timeout)
            text = data["choices"][0]["message"]["content"]
    finally:
        if tmp:
            try:
                os.remove(tmp)
            except OSError:
                pass
    m = re.search(r"\{.*\}", text or "", re.DOTALL)
    if not m:
        raise RuntimeError("Provider did not return usable JSON.")
    parsed = json.loads(m.group(0))
    kws = _dedupe([str(k).lower().strip() for k in parsed.get("keywords", []) if str(k).strip()])
    return (fit_title(parsed.get("title", ""), rules, kws),
            parsed.get("description", ""), kws[:rules["max_keywords"]])


def process_asset(path, workdir, *, marketplace=None, extra_seeds=None,
                  auto_extract=True, auto_seo=True, isolated=False,
                  provider=None, api_key=None, model=None, base_url=None,
                  category="", trademark_shield=True):
    """
    SEO Studio pipeline for ONE file of any supported kind.
    Backward-compat note: generate_metadata() above is unchanged for the
    legacy flow; this function adds extraction, marketplace rules, the
    trademark shield and provider BYOK on top.
    """
    rules = _rules(marketplace or "adobe")
    kind = file_kind(path)
    # --- readability guard: a corrupt file becomes an isolated error row,
    # never a silently invented result, and never aborts the batch.
    _unreadable = None
    try:
        if kind == "image":
            with Image.open(path) as _im:
                _im.verify()
        elif kind == "vector" and path.lower().endswith(".svg"):
            ET.parse(path)
        elif kind == "video":
            _info = probe_video(path)
            if not _info or not _info.get("duration"):
                _unreadable = "ffprobe could not read this video file."
    except Exception as exc:  # noqa: BLE001
        _unreadable = f"Could not read file ({exc.__class__.__name__})."
    if _unreadable:
        return {"filename": os.path.basename(path), "error": _unreadable,
                "type": kind, "source": "generated"}
    analysis = analysis_for(path, workdir)
    extracted = extract_metadata(path) if auto_extract else {}
    title = description = ""
    keywords = []
    source = "generated"
    engine = "builtin"

    if extracted and (extracted.get("title") or extracted.get("keywords")):
        title = extracted.get("title", "")
        description = extracted.get("description", "")
        keywords = _dedupe([k.lower() for k in extracted.get("keywords", [])])
        source = "extracted"
        engine = "extracted"
    if auto_seo and (not title or not keywords):
        ai_error = None
        if provider and provider != "builtin":
            try:
                t2, d2, k2 = provider_generate(
                    path, provider, api_key, model=model, base_url=base_url,
                    rules=rules, isolated=isolated)
                title, description, keywords = t2 or title, d2 or description, k2 or keywords
                engine = provider
            except Exception as exc:  # noqa: BLE001
                ai_error = str(exc)
        if engine in ("builtin", "extracted") and (not title or not keywords):
            t2, d2, k2 = _builtin_generate(path, extra_seeds, analysis, rules, isolated)
            title, description, keywords = t2 or title, d2 or description, k2 or keywords
            if source != "extracted":
                engine = "builtin"
        if ai_error and engine == "builtin":
            engine = "builtin (AI unavailable: " + ai_error[:90] + ")"
    if not title:
        title = fit_title(build_title(keywords or keywords_from_filename(path), analysis),
                          rules, keywords)
    if not description and rules["use_description"]:
        description = build_description(title, keywords, analysis)
    keywords = _dedupe(keywords)[:rules["max_keywords"]]

    # v8 Settings → AI Inspector: the "Detect Trademark & Brand Logos" rule
    # can switch the shield off (default ON, exactly the v7 behaviour).
    if trademark_shield:
        title, keywords, removed = screen_trademarks(title, keywords)
    else:
        removed = []
    title = fit_title(title, rules, keywords)
    return {
        "filename": os.path.basename(path),
        "title": title,
        "description": description if rules["use_description"] else "",
        "keywords": keywords,
        "keyword_count": len(keywords),
        "category": category,
        "analysis": analysis,
        "engine": engine,
        "source": source,
        "type": kind,
        "marketplace": marketplace or "adobe",
        "title_min": rules["title_min"], "title_max": rules["title_max"],
        "max_keywords": rules["max_keywords"],
        "trademark_removed": removed,
        "preview": preview_data_url(path, workdir),
    }


# ---------------------------------------------------------------- image to prompt

_PROMPT_SYSTEM = (
    "You are an expert prompt engineer for text-to-image generators. Study the "
    "attached asset and write ONE detailed generation prompt that could recreate "
    "a similar asset: main subject and action, style/medium, composition and "
    "camera angle, lighting, colour palette, background, mood, and important "
    "details. End with a short 'Negative:' list of things to avoid. Plain text "
    "only, no headings, 120-220 words.")


def image_to_prompt(path, workdir, provider=None, key=None, model=None,
                    base_url=None, timeout=90):
    """Reverse-engineer a generation prompt. With a BYOK vision key it uses
    the provider; without one it assembles a structured prompt from the
    built-in analysis and labels it basic."""
    analysis = analysis_for(path, workdir)
    if provider and provider != "builtin":
        from . import ai_hub
        if provider not in ai_hub.PROVIDERS:
            raise ValueError(f"Unknown provider '{provider}'.")
        cfg = ai_hub.PROVIDERS[provider]
        key = (key or "").strip()
        if provider == "ollama" and not key:
            key = "ollama"
        if not key:
            raise ValueError("No API key supplied.")
        raster, tmp = path, None
        ext = os.path.splitext(path)[1].lower()
        if ext == ".svg" or file_kind(path) == "video":
            tmp = path + ".vision.png"
            if ext == ".svg":
                from .svg_render import render_svg_to_png
                render_svg_to_png(path, tmp, 768, 768)
            elif not video_frame_png(path, tmp):
                raise ValueError("Could not extract a frame.")
            raster = tmp
        try:
            with open(raster, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            mdl = (model or cfg["default_model"]).strip()
            if cfg["kind"] == "gemini":
                url = ("https://generativelanguage.googleapis.com/v1beta/models/"
                       + urllib.parse.quote(mdl) + ":generateContent?key="
                       + urllib.parse.quote(key))
                data = ai_hub._post_json(url, {"contents": [{"parts": [
                    {"text": _PROMPT_SYSTEM},
                    {"inline_data": {"mime_type": "image/png", "data": b64}}]}]},
                    timeout=timeout)
                text = data["candidates"][0]["content"]["parts"][0]["text"]
            else:
                base = (base_url or cfg["base"]).rstrip("/")
                data = ai_hub._post_json(base + "/chat/completions",
                                         {"model": mdl, "messages": [{"role": "user", "content": [
                                             {"type": "text", "text": _PROMPT_SYSTEM},
                                             {"type": "image_url",
                                              "image_url": {"url": f"data:image/png;base64,{b64}"}}]}],
                                          "temperature": 0.6},
                                         headers={"Authorization": f"Bearer {key}"},
                                         timeout=timeout)
                text = data["choices"][0]["message"]["content"]
            return {"prompt": (text or "").strip(), "engine": provider, "basic": False}
        finally:
            if tmp:
                try:
                    os.remove(tmp)
                except OSError:
                    pass
    # basic fallback — built from built-in analysis
    seeds = keywords_from_filename(path)
    colors = ", ".join(analysis.get("colors") or []) or "mixed tones"
    subject = " ".join(seeds) if seeds else "main subject of the asset"
    prompt = (f"{subject}, professional stock {analysis.get('kind', 'image')}, "
              f"{analysis.get('orientation', '')} composition, {analysis.get('mood', 'balanced')} "
              f"lighting, dominant colours: {colors}, clean uncluttered background, "
              f"high detail, commercial advertising quality. "
              f"Negative: watermarks, text artefacts, distorted hands, low resolution, noise.")
    return {"prompt": prompt, "engine": "builtin", "basic": True}


# ---------------------------------------------------------------- multi CSV

def _csv_row_for(row, agency):
    rules = MARKETPLACE_RULES[agency]
    kws = row.get("keywords", [])
    if isinstance(kws, list):
        kws = rules["keyword_sep"].join(kws)
    base = {
        "Filename": row.get("filename", ""),
        "Title": row.get("title", ""),
        # Shutterstock's contributor CSV has no Title column — its
        # "Description" field IS the displayed asset title, so the title
        # goes there (falling back to the description if no title).
        "Description": (row.get("title", "") or row.get("description", ""))
        if agency == "shutterstock" else row.get("description", ""),
        "Keywords": kws,
        "Category": row.get("category", ""),
        "Categories": row.get("category", ""),
        "Editorial": "no", "Illustration": "no", "Mature content": "no",
        "Location": "", "Price": "", "License": "",
    }
    return {f: base.get(f, "") for f in rules["csv_fields"]}


def to_csv_for(rows, agency):
    """CSV in one agency's documented layout. The Adobe layout delegates to
    the original to_csv() so legacy output stays byte-compatible."""
    if agency not in MARKETPLACE_RULES:
        raise ValueError(f"Unknown marketplace '{agency}'.")
    if agency == "adobe":
        return to_csv(rows)
    fields = MARKETPLACE_RULES[agency]["csv_fields"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(_csv_row_for(r, agency))
    return buf.getvalue()
