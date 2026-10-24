"""
Adobe Tracker — market intelligence for Adobe Stock niches (v7, Part A).

Reimplemented from the *capabilities* of Adobe Tracker Pro / StockMetadata
Studio's tracker mode (their live results are gated, so this is built from
their visible UI + the normalised record shape specified in Prompt #2):

  * Search runs through the USER's own Apify token + a user-chosen Adobe
    Stock search scraper Actor (generic runner in apify_intel.py). No actor
    is hardcoded: the owner picks one in the Apify Store and pastes its ID.
  * Demo mode ships fictional sample data so the whole tab works offline.
  * Raw actor items are normalised defensively into one record shape:
      {id, title, creator, creator_url, asset_url, thumbnail_url, type,
       is_ai, downloads, views, upload_date, keywords[]}
    Missing fields become None — never a crash.

Opportunity Score (0-100) — an ESTIMATE, computed transparently:
    demand      = log10(1 + total_downloads) scaled so ~100k downloads = 60
                  plus log-scaled median downloads component (max ~20)
    competition = penalty for a crowded result set: assets/200 * 10 (max 10)
    saturation  = penalty for AI share: ai_share * 15 (max 15)
    score = clamp(demand - competition - saturation, 0, 100)
Rationale: a niche where assets already earn many downloads (demand) but the
result set is small and mostly human-made (low saturation) is a better
opportunity than a huge, AI-flooded one. It is a heuristic for prioritising
research — NOT verified Adobe data; the UI labels it "estimate".
"""

import json
import math
import os
import re
from datetime import date, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
SAMPLE_PATH = os.path.join(BASE, "tracker_sample.json")

CATEGORIES = ["all", "photo", "illustration", "vector", "video",
              "template", "3d", "audio"]


# ---------------------------------------------------------------- normalise

def _first(d, *keys):
    for k in keys:
        v = d.get(k)
        if v not in (None, ""):
            return v
    return None


def _to_int(v):
    try:
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return int(v)
        s = re.sub(r"[^0-9.]", "", str(v))
        return int(float(s)) if s else None
    except Exception:  # noqa: BLE001
        return None


def _to_bool_ai(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        return v.strip().lower() in ("yes", "true", "1", "ai", "generated", "ai-generated")
    return False


_TYPE_MAP = {
    "photo": "photo", "photos": "photo", "image": "photo", "images": "photo",
    "illustration": "illustration", "illustrations": "illustration",
    "vector": "vector", "vectors": "vector", "eps": "vector",
    "video": "video", "videos": "video", "footage": "video",
    "template": "template", "templates": "template",
    "3d": "3d", "audio": "audio", "music": "audio",
}


def _norm_type(v):
    if not v:
        return "photo"
    return _TYPE_MAP.get(str(v).strip().lower(), str(v).strip().lower())


def _norm_keywords(v):
    if v is None:
        return []
    if isinstance(v, str):
        parts = re.split(r"[,;]", v)
    elif isinstance(v, list):
        parts = []
        for x in v:
            if isinstance(x, dict):
                parts.append(x.get("name") or x.get("keyword") or x.get("text") or "")
            else:
                parts.append(str(x))
    else:
        return []
    out, seen = [], set()
    for p in parts:
        w = str(p).strip().lower()
        if w and w not in seen:
            seen.add(w)
            out.append(w)
    return out[:60]


def normalize_item(raw):
    """Map one raw scraper item (any of the common field namings) to the
    normalised record shape. Defensive: never raises."""
    if not isinstance(raw, dict):
        return None
    creator = _first(raw, "creator", "authorName", "author", "contributorName")
    creator_url = _first(raw, "creator_url", "authorUrl", "contributorUrl")
    contrib = raw.get("contributor")
    if isinstance(contrib, dict):
        creator = creator or contrib.get("name")
        creator_url = creator_url or contrib.get("url")
    rec = {
        "id": (str(_first(raw, "id", "assetId", "asset_id", "stockId") or "")
               or None),
        "title": _first(raw, "title", "assetTitle", "name", "headline"),
        "creator": creator,
        "creator_url": creator_url,
        "asset_url": _first(raw, "asset_url", "url", "link", "assetUrl"),
        "thumbnail_url": _first(raw, "thumbnail_url", "thumbnail", "preview",
                                "previewUrl", "image"),
        "type": _norm_type(_first(raw, "type", "mediaType", "contentType",
                                  "assetType", "category")),
        "is_ai": _to_bool_ai(_first(raw, "is_ai", "generativeAI", "isAIContent",
                                    "ai_generated", "aiGenerated")),
        "downloads": _to_int(_first(raw, "downloads", "nbDownloads",
                                    "downloadsCount", "downloadCount")),
        "views": _to_int(_first(raw, "views", "nbViews", "viewsCount",
                                "viewCount", "impressions")),
        "upload_date": _first(raw, "upload_date", "creationDate", "published",
                              "date", "uploadDate"),
        "keywords": _norm_keywords(_first(raw, "keywords", "tags", "keyword_list")),
    }
    if rec["id"] is None and rec["title"] is None and rec["asset_url"] is None:
        return None
    return rec


def normalize_items(raw_items):
    out = []
    for raw in raw_items or []:
        rec = normalize_item(raw)
        if rec:
            out.append(rec)
    return out


# ---------------------------------------------------------------- KPIs

def compute_kpis(records):
    """
    Opportunity Score formula (estimate — see module docstring):
      demand = 60 * log10(1+total_dl)/5  (so ~100k total downloads ≈ 60)
             + 20 * log10(1+median_dl)/3  (so ~1k median ≈ 20)
      competition penalty = min(10, assets/200*10)
      AI saturation penalty = ai_share * 15
      score = clamp(demand - penalties, 0, 100), rounded.
    """
    n = len(records)
    dls = sorted(r.get("downloads") or 0 for r in records)
    total_dl = sum(dls)
    total_vw = sum(r.get("views") or 0 for r in records)
    median_dl = dls[n // 2] if n else 0
    ai_share = (sum(1 for r in records if r.get("is_ai")) / n) if n else 0.0
    demand = 60 * (math.log10(1 + total_dl) / 5.0) + 20 * (math.log10(1 + median_dl) / 3.0)
    score = demand - min(10, n / 200 * 10) - ai_share * 15
    return {
        "assets": n,
        "total_downloads": total_dl,
        "total_views": total_vw,
        "median_downloads": median_dl,
        "ai_share": round(ai_share, 3),
        "opportunity_score": int(round(max(0.0, min(100.0, score)))),
        "score_note": "Estimate from demand vs competition — not verified Adobe data.",
    }


def analytics(records):
    """Lightweight chart data: distribution histogram, AI makeup, formats,
    top-20 keywords, top creators."""
    buckets = [0, 10, 50, 100, 500, 1000, 5000, 10 ** 9]
    labels = ["0-9", "10-49", "50-99", "100-499", "500-999", "1k-4.9k", "5k+"]
    hist = [0] * len(labels)
    for r in records:
        d = r.get("downloads") or 0
        for i in range(len(labels)):
            if buckets[i] <= d < buckets[i + 1]:
                hist[i] += 1
                break
    formats = {}
    for r in records:
        formats[r.get("type") or "photo"] = formats.get(r.get("type") or "photo", 0) + 1
    kw_count = {}
    for r in records:
        for k in r.get("keywords") or []:
            kw_count[k] = kw_count.get(k, 0) + 1
    top_kw = sorted(kw_count.items(), key=lambda kv: -kv[1])[:20]
    creators = {}
    for r in records:
        c = r.get("creator") or "Unknown"
        e = creators.setdefault(c, {"creator": c, "creator_url": r.get("creator_url"),
                                    "assets": 0, "total_downloads": 0})
        e["assets"] += 1
        e["total_downloads"] += r.get("downloads") or 0
    top_creators = sorted(creators.values(), key=lambda c: -c["total_downloads"])
    for c in top_creators:
        c["avg_downloads"] = round(c["total_downloads"] / c["assets"], 1) if c["assets"] else 0
    ai = sum(1 for r in records if r.get("is_ai"))
    return {
        "histogram": {"labels": labels, "values": hist},
        "ai_vs_human": {"ai": ai, "human": len(records) - ai},
        "formats": formats,
        "top_keywords": [{"keyword": k, "count": c} for k, c in top_kw],
        "top_creators": top_creators[:25],
    }


def load_sample():
    with open(SAMPLE_PATH, encoding="utf-8") as f:
        return json.load(f)["records"]


def build_actor_input(mode, query, category, sort, ai_filter, limit):
    """
    Generic input for an Adobe Stock search scraper Actor. Actor input
    schemas differ per Actor (their internals were not observable), so this
    sends the common field names; the owner's chosen Actor documentation
    wins — the UI lets them edit the Actor ID and this is a starting point.
    """
    return {
        "keyword" if mode == "keyword" else "contributor": query,
        "searchQuery": query,
        "category": category,
        "sortBy": sort,
        "aiFilter": ai_filter,
        "maxResults": int(limit),
        "limit": int(limit),
    }


# ---------------------------------------------------------------- seasonality
# Yearly recurring demand windows. Ramadan/Eid and Diwali dates move every
# year (Hijri / Hindu lunisolar calendars) — the constants below are
# APPROXIMATE for 2026/2027 and must be verified yearly. Edit freely.
EVENTS = [
    {"name": "Valentine's Day", "month": 2, "day": 14, "keyword": "valentine love romance",
     "ideas": ["Romantic couple silhouettes", "Heart bokeh backgrounds", "Valentine greeting cards"]},
    {"name": "Ramadan & Eid al-Fitr", "month": 3, "day": 20, "approx": True,
     "keyword": "ramadan eid lantern", "ideas": ["Lantern & crescent scenes", "Iftar food spreads", "Eid greeting designs"]},
    {"name": "Spring / Earth Day", "month": 4, "day": 22, "keyword": "spring nature earth day",
     "ideas": ["Fresh green growth close-ups", "Recycling & sustainability icons", "Garden lifestyle photos"]},
    {"name": "Eid al-Adha", "month": 5, "day": 27, "approx": True, "keyword": "eid al adha celebration",
     "ideas": ["Family celebration tables", "Mosque architecture", "Festive greeting cards"]},
    {"name": "Back to School", "month": 8, "day": 25, "keyword": "back to school education",
     "ideas": ["Kids with backpacks", "Classroom flat lays", "School supplies vectors"]},
    {"name": "Diwali", "month": 10, "day": 20, "approx": True, "keyword": "diwali festival lights",
     "ideas": ["Diya lamps & rangoli", "Festival bokeh", "Diwali greeting templates"]},
    {"name": "Halloween", "month": 10, "day": 31, "keyword": "halloween spooky pumpkin",
     "ideas": ["Pumpkin & haunted scenes", "Halloween party flyers", "Spooky typography backgrounds"]},
    {"name": "Black Friday", "special": "black_friday", "keyword": "black friday sale shopping",
     "ideas": ["Sale banners & price bursts", "Shopping crowd photos", "E-commerce promo videos"]},
    {"name": "Christmas", "month": 12, "day": 25, "keyword": "christmas winter holiday",
     "ideas": ["Cozy winter interiors", "Gift wrapping flat lays", "Christmas backgrounds & cards"]},
    {"name": "New Year", "month": 1, "day": 1, "keyword": "new year celebration fireworks",
     "ideas": ["Fireworks city skies", "Champagne celebration", "Goal-setting planner photos"]},
]


def _black_friday(year):
    # Day after US Thanksgiving (4th Thursday of November)
    d = date(year, 11, 1)
    thursdays = [d + timedelta(days=i) for i in range(30)
                 if (d + timedelta(days=i)).weekday() == 3]
    return thursdays[3] + timedelta(days=1)


def _next_occurrence(ev, today):
    if ev.get("special") == "black_friday":
        cand = _black_friday(today.year)
        if cand < today:
            cand = _black_friday(today.year + 1)
        return cand
    cand = date(today.year, ev["month"], ev["day"])
    if cand < today:
        cand = date(today.year + 1, ev["month"], ev["day"])
    return cand


def seasonality(today=None):
    """Event cards with days-left and golden-window status.
    Rule of thumb: stock buyers search 60-90 days before the event, so
    <=90 days = SUBMIT NOW, <=150 = PREP, else UPCOMING."""
    today = today or date.today()
    out = []
    for ev in EVENTS:
        nxt = _next_occurrence(ev, today)
        days = (nxt - today).days
        status = "SUBMIT NOW" if days <= 90 else "PREP" if days <= 150 else "UPCOMING"
        out.append({"name": ev["name"], "date": nxt.isoformat(), "days_left": days,
                    "status": status, "keyword": ev["keyword"], "ideas": ev["ideas"],
                    "approx": bool(ev.get("approx"))})
    return sorted(out, key=lambda e: e["days_left"])


# ================================================================ v12 (Prompt #5)
# Market-tracker extensions for the Keyword Research tab. ADDITIVE ONLY —
# nothing above this line changed; the Adobe Tracker tab uses the functions
# above and is unaffected. These helpers power the StockMetadata / RA
# Graphic Studio style cards in Keyword Research.
#
# Definitions (this app's own, documented — the references gate their
# internals; only D/MO and top-keywords are publicly defined by RA Graphic
# Studio, the rest are labelled estimates/heuristics in the UI):
#   D/MO (downloads per month) = lifetime downloads / max(1, months since
#       upload), 1 decimal — RA Graphic Studio's published definition.
#   Estimated revenue = lifetime downloads x per-download rate (the tab's
#       editable rate, default $0.99). An estimate, never Adobe data.
#   Lifecycle: "Seasonal" when the title/keywords match the seasonal term
#       set below (built from this app's calendar vocabulary — christmas,
#       halloween, ramadan, eid, diwali, valentine, summer…), else
#       "Evergreen". A keyword-matching heuristic, not a sales fact.
#   Keyword Difficulty: from the median downloads of the TOP-10 results
#       (M) and the result-set size (N):
#         M < 500            -> Easy
#         500 <= M < 2500    -> Moderate
#         2500 <= M < 10000  -> Hard
#         M >= 10000         -> Red Ocean (dominated by legacy
#                               high-download assets)
#       plus: a very large set (N >= 150) bumps Easy up to Moderate
#       (crowded shelf). Labelled "estimate" in the UI.
#   Undiscovered: assets <= 24 months old whose lifetime downloads are
#       BELOW the set median, ranked by D/MO descending — fast sellers
#       that are not yet saturated.

from datetime import datetime as _datetime  # noqa: E402

_SEASONAL_TERMS = {
    "christmas", "xmas", "halloween", "spooky", "ramadan", "eid", "iftar",
    "diwali", "deepavali", "holi", "valentine", "valentines", "easter",
    "thanksgiving", "black friday", "cyber monday", "new year", "new years",
    "hanukkah", "kwanzaa", "lunar new year", "chinese new year", "nowruz",
    "songkran", "oktoberfest", "carnival", "summer", "back to school",
    "independence day", "fourth of july", "st patrick", "st patricks",
    "mother's day", "mothers day", "father's day", "fathers day",
    "eid al fitr", "eid al adha", "passover", "vesak", "mid autumn",
    "day of the dead", "dia de los muertos",
}


def parse_upload_date(value):
    """Best-effort parse of an upload_date value -> date or None."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    s = str(value).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return _datetime.strptime(s[:19] if "T" in s or " " in s else s, fmt).date()
        except ValueError:
            continue
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def months_since_upload(upload_date, today=None):
    """Fractional months between upload and today (None if unparseable)."""
    d = parse_upload_date(upload_date)
    if d is None:
        return None
    today = today or date.today()
    days = (today - d).days
    if days < 0:
        days = 0
    return days / 30.4375  # average month length


def dmo(record, today=None):
    """Downloads per month: downloads / max(1, months since upload),
    1 decimal. None when downloads or upload date are unknown."""
    dl = record.get("downloads")
    months = months_since_upload(record.get("upload_date"), today=today)
    if dl is None or months is None:
        return None
    return round(dl / max(1.0, months), 1)


def age_label(upload_date, today=None):
    """'7 years ago' / '3 months ago' / '12 days ago' / '—'."""
    d = parse_upload_date(upload_date)
    if d is None:
        return "—"
    today = today or date.today()
    days = max(0, (today - d).days)
    if days < 30:
        return f"{days} day{'s' if days != 1 else ''} ago"
    months = days // 30
    if months < 12:
        return f"{months} month{'s' if months != 1 else ''} ago"
    years = round(days / 365.25, 1)
    years = int(years) if years == int(years) else years
    return f"{years} year{'s' if years != 1 else ''} ago"


def lifecycle(record):
    """Evergreen / Seasonal heuristic from title + keywords."""
    hay = " ".join([str(record.get("title") or "").lower()]
                   + [str(k).lower() for k in (record.get("keywords") or [])])
    tokens = set(re.split(r"[^a-z']+", hay))
    for term in _SEASONAL_TERMS:
        if " " in term:
            if term in hay:
                return "Seasonal"
        elif term in tokens:
            return "Seasonal"
    return "Evergreen"


def est_revenue(record, rate=0.99):
    """Estimated lifetime revenue = downloads x rate (None if unknown)."""
    dl = record.get("downloads")
    if dl is None:
        return None
    return round(dl * float(rate), 2)


def enrich_record(record, rate=0.99, today=None):
    """Copy of a normalised record + computed market fields."""
    out = dict(record)
    out["dmo"] = dmo(record, today=today)
    out["age"] = age_label(record.get("upload_date"), today=today)
    out["lifecycle"] = lifecycle(record)
    out["est_revenue"] = est_revenue(record, rate=rate)
    return out


def enrich_records(records, rate=0.99, today=None):
    return [enrich_record(r, rate=rate, today=today) for r in records]


def avg_dmo(records, today=None):
    vals = [dmo(r, today=today) for r in records]
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 1) if vals else None


def keyword_difficulty(records):
    """Transparent heuristic — see the v12 section header for thresholds."""
    n = len(records)
    if not n:
        return {"tier": "—", "label": "No data", "median_top10": 0,
                "assets": 0, "note": "No results to judge."}
    top10 = sorted((r.get("downloads") or 0 for r in records),
                   reverse=True)[:10]
    med = top10[len(top10) // 2]
    if med < 500:
        tier = "Easy"
    elif med < 2500:
        tier = "Moderate"
    elif med < 10000:
        tier = "Hard"
    else:
        tier = "Red Ocean"
    note = (f"Median of the top-10 downloads is {med:,}; "
            f"{n} assets in the set.")
    if tier == "Easy" and n >= 150:
        tier = "Moderate"
        note += " Bumped up: very large result set (crowded shelf)."
    if tier == "Red Ocean":
        note += " Dominated by legacy high-download assets."
    return {"tier": tier, "label": tier, "median_top10": med,
            "assets": n, "note": note}


def undiscovered(records, today=None):
    """Young (<=24 months), below-median-download assets ranked by D/MO
    descending — 'fast-selling but not yet saturated' (heuristic)."""
    if not records:
        return []
    dls = sorted(r.get("downloads") or 0 for r in records)
    median_dl = dls[len(dls) // 2]
    out = []
    for r in records:
        months = months_since_upload(r.get("upload_date"), today=today)
        if months is None or months > 24:
            continue
        if (r.get("downloads") or 0) >= median_dl:
            continue
        out.append(r)
    out.sort(key=lambda r: -(dmo(r, today=today) or 0))
    return out


def sort_market(records, sort, today=None):
    """Server-side initial ordering for scan results. 'relevance' and
    'featured' keep actor order (featured has no reliable flag in scraped
    data — the UI falls back to Relevance with a note, as specified)."""
    rows = list(records)
    if sort == "downloads":
        rows.sort(key=lambda r: -(r.get("downloads") or 0))
    elif sort == "newest":
        rows.sort(key=lambda r: str(r.get("upload_date") or ""), reverse=True)
    elif sort == "velocity":
        rows.sort(key=lambda r: -(dmo(r, today=today) or 0))
    elif sort == "undiscovered":
        rows = undiscovered(rows, today=today)
    return rows


def winning_keywords(records, limit=30):
    """Top-N keywords by frequency across the set (the 'top keywords'
    metric RA Graphic Studio publishes) — analytics() caps at 20, the
    Winning Keywords panel wants 30."""
    kw_count = {}
    for r in records:
        for k in r.get("keywords") or []:
            kw_count[k] = kw_count.get(k, 0) + 1
    top = sorted(kw_count.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    return [{"keyword": k, "count": c} for k, c in top]


def contributor_summary(records, rate=0.99, today=None):
    """Header summary for Contributor-mode scans (Part B.7)."""
    if not records:
        return None
    creators = {}
    for r in records:
        c = r.get("creator") or "Unknown"
        creators[c] = creators.get(c, 0) + 1
    creator = max(creators, key=creators.get)
    mine = [r for r in records if (r.get("creator") or "Unknown") == creator]
    total_dl = sum(r.get("downloads") or 0 for r in mine)
    best = max(mine, key=lambda r: r.get("downloads") or 0)
    formats = {}
    for r in mine:
        formats[r.get("type") or "photo"] = formats.get(r.get("type") or "photo", 0) + 1
    total_f = max(1, len(mine))
    mix = {t: round(n / total_f * 100) for t, n in
           sorted(formats.items(), key=lambda kv: -kv[1])}
    per_month = {}
    for r in mine:
        d = parse_upload_date(r.get("upload_date"))
        if d:
            k = d.strftime("%Y-%m")
            per_month[k] = per_month.get(k, 0) + 1
    rhythm = [{"month": k, "count": per_month[k]} for k in sorted(per_month)]
    ai_share = (sum(1 for r in mine if r.get("is_ai")) / total_f) if mine else 0.0
    return {
        "creator": creator,
        "creator_url": next((r.get("creator_url") for r in mine
                             if r.get("creator_url")), None),
        "assets": len(mine),
        "total_downloads": total_dl,
        "avg_dmo": avg_dmo(mine, today=today),
        "best_seller": {"title": best.get("title"),
                        "downloads": best.get("downloads") or 0},
        "format_mix": mix,
        "upload_rhythm": rhythm,
        "ai_share": round(ai_share, 3),
        "est_revenue": round(total_dl * float(rate), 2),
    }


# ================================================================ v13
# (Prompt #5 UPDATED) — sharpenings for the Keyword Research Market
# Tracker. ADDITIVE ONLY — everything above is unchanged and the Adobe
# Tracker tab is unaffected.
#
# WRONG-ACTOR GUARD: the owner's v11 screenshot showed a Google-search
# Actor's related-search phrases rendered as "results". A normalised
# record counts as a real Adobe Stock ASSET only when it has a title AND
# (a downloads value OR an asset URL). If fewer than half of a live scan's
# normalised records qualify, the scan is rejected as wrong-actor data.
#
# KEYWORD DIFFICULTY as a numeric KD /100 (ESTIMATE — reconstruction):
#     KD = round(clamp(100 * (0.6 * L(median downloads of the TOP-10
#                                  results, cap 100,000)
#                           + 0.25 * L(total results in Adobe Stock — the
#                                  actor-reported total, else the loaded
#                                  set size, cap 200,000,000)
#                           + 0.15 * L(median downloads of the FULL set,
#                                  cap 100,000)), 0, 100))
#     L(v, cap) = log10(1 + v) / log10(1 + cap)
# The updated Prompt #5 text names the first two terms and was truncated
# mid-formula; the third term (0.15 weight on the full-set median — the
# remaining competition signal, the result-set size being already used at
# 0.25 as the fallback total) is this app's documented reconstruction,
# also recorded in TESTING.md. Verdict bands: 0-39 EASY, 40-59 MODERATE,
# 60-79 HARD, 80-100 RED OCEAN (advice at >= 80: dominated by legacy
# high-download assets — focus on specific niche subtopics).
#
# Revenue default rate is $0.85/download in the Market Tracker tab
# (the reference's implied rate: $2,324 / 2,734 downloads ~ $0.85,
# confirmed against its published cards); the rate stays editable.


def _median_int(values):
    """Median with this module's convention: ascending sort, element at
    index n//2 (same convention as compute_kpis)."""
    vals = sorted(values)
    return vals[len(vals) // 2] if vals else 0


def _log_scale(v, cap):
    return math.log10(1 + max(0, v)) / math.log10(1 + cap)


def is_asset_record(record):
    """Wrong-actor guard predicate: title AND (downloads OR asset URL)."""
    if not record or not record.get("title"):
        return False
    return record.get("downloads") is not None or bool(record.get("asset_url"))


# ---- v14: Actor ID validation ---------------------------------------
# One rule, mirrored client-side in templates/index.html
# (apifyActorError): an Actor ID is either 'username/actor-name' or a
# bare Apify actor ID (10+ alphanumeric chars, no spaces). Anything
# containing spaces or ending in a file extension is NOT an Actor ID —
# the classic case is a pasted screenshot file name
# ('Screenshot 2026-10-24 163420.png'), which used to sail through to
# Apify and come back as a bare 'HTTP Error 404: Not Found'.
_ACTOR_SLUG_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*$")
_ACTOR_ID_RE = re.compile(r"^[A-Za-z0-9]{10,}$")
_ACTOR_FILE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".pdf",
                    ".zip")


def actor_id_error(actor):
    """None when `actor` is a plausible Apify Actor ID, else a plain
    message naming the problem and the expected format. An empty value
    returns None — callers handle 'no actor' as Demo / missing-field."""
    a = (actor or "").strip()
    if not a:
        return None
    if a.lower().endswith(_ACTOR_FILE_EXTS) or any(
            ch.isspace() for ch in a):
        return ("That doesn't look like an Actor ID — it looks like a "
                "file name. An Actor ID looks like "
                "`username/actor-name`; copy it from the Actor's page "
                "in the Apify Store.")
    if _ACTOR_SLUG_RE.match(a) or _ACTOR_ID_RE.match(a):
        return None
    return ("That doesn't look like an Actor ID. An Actor ID looks "
            "like `username/actor-name`; copy it from the Actor's "
            "page in the Apify Store.")


def is_actor_not_found(exc):
    """True when an Apify run exception is an HTTP 404 — i.e. the
    Actor ID does not exist on Apify (urllib HTTPError carries .code;
    fall back to the message text for wrapped errors)."""
    return getattr(exc, "code", None) == 404 or "404" in str(exc)


def actor_not_found_message(actor):
    return (f"Actor not found on Apify — the saved Actor ID '{actor}' "
            "doesn't exist. Paste the ID exactly as shown on the "
            "Actor's Apify Store page (Manage Apify Key / Adobe "
            "Tracker tab).")


def wrong_actor_check(records):
    """{total, assets, ratio, ok} for a normalised record list. An empty
    list passes (a legitimately empty result is not wrong-actor data)."""
    total = len(records or [])
    assets = sum(1 for r in records or [] if is_asset_record(r))
    ratio = (assets / total) if total else 1.0
    return {"total": total, "assets": assets, "ratio": round(ratio, 3),
            "ok": total == 0 or ratio >= 0.5}


_TOTAL_KEYS = ("totalResults", "total_results", "totalCount", "total_count",
               "resultsTotal", "totalAssets", "nbResults", "totalItems")


def extract_total_count(raw_items):
    """Best-effort 'total results in Adobe Stock' from raw Actor items.
    Some Actors emit a metadata item (or a nested meta block) carrying a
    total; asset items themselves never do. Returns int or None."""
    for raw in raw_items or []:
        if not isinstance(raw, dict):
            continue
        candidates = [raw]
        for nest in ("meta", "metadata", "stats", "summary"):
            if isinstance(raw.get(nest), dict):
                candidates.append(raw[nest])
        for cand in candidates:
            for key in _TOTAL_KEYS:
                v = _to_int(cand.get(key))
                if v:
                    return v
        # a bare "total" counts only on a metadata-style item (no title)
        if not raw.get("title"):
            v = _to_int(raw.get("total"))
            if v:
                return v
    return None


def kd_score(records, total_in_stock=None):
    """Numeric Keyword Difficulty /100 — see the v13 header for the
    formula, its bands and the reconstruction note. ESTIMATE."""
    n = len(records or [])
    if not n:
        return {"score": None, "verdict": "—", "advice": "No results to judge.",
                "median_top10": 0, "median_all": 0, "total_used": 0}
    dls = [r.get("downloads") or 0 for r in records]
    top10 = sorted(dls, reverse=True)[:10]
    med_top10 = _median_int(top10)
    med_all = _median_int(dls)
    total_used = total_in_stock if total_in_stock else n
    raw = 100 * (0.6 * _log_scale(med_top10, 100_000)
                 + 0.25 * _log_scale(total_used, 200_000_000)
                 + 0.15 * _log_scale(med_all, 100_000))
    score = int(round(max(0.0, min(100.0, raw))))
    if score >= 80:
        verdict = "RED OCEAN"
        advice = ("Dominated by legacy high-download assets — focus on "
                  "specific niche subtopics.")
    elif score >= 60:
        verdict = "HARD"
        advice = ("Strong legacy competition — target long-tail subtopics "
                  "and fresher angles.")
    elif score >= 40:
        verdict = "MODERATE"
        advice = ("Moderate competition — strong metadata and a clear "
                  "angle can still win.")
    else:
        verdict = "EASY"
        advice = ("Open shelf — low legacy competition; new quality "
                  "uploads can rank.")
    return {"score": score, "verdict": verdict, "advice": advice,
            "median_top10": med_top10, "median_all": med_all,
            "total_used": total_used,
            "formula": "KD = 100*(0.6*L(top-10 median DL, cap 100k) + "
                       "0.25*L(total in Adobe Stock, cap 200M) + "
                       "0.15*L(full-set median DL, cap 100k)), "
                       "L = log-scaled (reconstruction — see code)"}


def opportunity_verdict(score):
    """Verdict bands for the Opportunity Index (updated Prompt #5)."""
    if score is None:
        return "—"
    if score >= 80:
        return "VERY HIGH"
    if score >= 60:
        return "HIGH POTENTIAL"
    if score >= 40:
        return "MODERATE"
    return "LOW"


def market_advice(records, kpis, today=None):
    """Deterministic rule-based advice lines for the score cards.
    Returns {opportunity_advice, ai_advice}. The opportunity line picks
    the strongest signal in a fixed priority order: old top assets >
    low AI share > high AI share > strong velocity > balanced default."""
    ai_share = kpis.get("ai_share") or 0.0
    if ai_share <= 0.15:
        ai_advice = ("Low AI footprint — buyers here still get mostly "
                     "human-made work; authentic assets stand out.")
    elif ai_share < 0.4:
        ai_advice = ("AI work is a minority — human-made quality still "
                     "defines this shelf.")
    elif ai_share < 0.7:
        ai_advice = ("AI content is a large minority — originality and "
                     "craft decide who sells.")
    else:
        ai_advice = ("AI dominates this niche — expect heavy competition "
                     "and price pressure.")
    top10 = sorted(records or [], key=lambda r: -(r.get("downloads") or 0))[:10]
    ages = [months_since_upload(r.get("upload_date"), today=today)
            for r in top10]
    ages = [a for a in ages if a is not None]
    med_age = _median_int([round(a) for a in ages]) if ages else 0
    vel = avg_dmo(records or [], today=today) or 0
    if med_age >= 60:
        opp = ("Top assets are old — fresh uploads can break in with "
               "modern quality.")
    elif ai_share <= 0.15:
        opp = ("Low AI footprint — authentic work stands out here; a "
               "recommended niche for clean, original assets.")
    elif ai_share >= 0.6:
        opp = ("Saturated with AI content — enter only with a clearly "
               "different, specific angle.")
    elif vel >= 100:
        opp = ("Strong sales velocity — proven demand right now; move "
               "fast with quality uploads.")
    else:
        opp = ("Balanced market — enter with a specific subtopic angle "
               "rather than generic coverage.")
    return {"opportunity_advice": opp, "ai_advice": ai_advice}


def market_summary(records, rate=0.85, total_in_stock=None, today=None):
    """Row-1 / Row-2 market summary for the Market Tracker (v13):
    Total in Adobe Stock, Total Downloads, Average per Asset, Top
    Performing Asset, Opportunity verdict + advice, AI advice,
    Est. Market Revenue and numeric KD. Records may be raw-normalised or
    enriched; only downloads / upload_date / is_ai are read. ESTIMATES."""
    recs = list(records or [])
    n = len(recs)
    kpis = compute_kpis(recs)
    total_dl = kpis["total_downloads"]
    top = None
    if recs:
        best = max(recs, key=lambda r: r.get("downloads") or 0)
        top = {"id": best.get("id"), "title": best.get("title"),
               "creator": best.get("creator"),
               "downloads": best.get("downloads") or 0,
               "dmo": dmo(best, today=today),
               "thumbnail_url": best.get("thumbnail_url")}
    kd = kd_score(recs, total_in_stock=total_in_stock)
    adv = market_advice(recs, kpis, today=today)
    return {
        "total_in_stock": total_in_stock,
        "loaded": n,
        "total_downloads": total_dl,
        "total_views": kpis["total_views"],
        "median_downloads": kpis["median_downloads"],
        "avg_dmo": avg_dmo(recs, today=today),
        "average_per_asset": int(round(total_dl / n)) if n else 0,
        "top_asset": top,
        "opportunity_score": kpis["opportunity_score"],
        "opportunity_verdict": opportunity_verdict(kpis["opportunity_score"]),
        "opportunity_advice": adv["opportunity_advice"],
        "ai_share": kpis["ai_share"],
        "ai_advice": adv["ai_advice"],
        "est_revenue_total": round(total_dl * float(rate), 2),
        "est_revenue_per_asset": round(total_dl * float(rate) / n, 2) if n else 0.0,
        "rate": float(rate),
        "kd": kd,
    }


_BASIC_PROMPT_NEG = ("Negative: watermarks, text artefacts, distorted "
                     "hands, low resolution, noise.")


def asset_prompt_basic(record):
    """Template reverse-engineered prompt from title + top keywords.
    Used when no AI key is available (or vision failed) — always labelled
    'basic' by the caller; never presented as AI output."""
    title = (record.get("title") or "stock asset").strip()
    title = re.sub(r"\s*[—-]\s*royalty free.*$", "", title, flags=re.I).strip()
    kws = list(dict.fromkeys(record.get("keywords") or []))[:5]
    kw_txt = ", ".join(kws) if kws else "commercial subject"
    typ = (record.get("type") or "photo").replace("photo", "photograph")
    return (f"{title} — professional stock {typ}, {kw_txt}, "
            f"clean composition with copy space, natural commercial "
            f"lighting, high detail, advertising quality. "
            + _BASIC_PROMPT_NEG)
