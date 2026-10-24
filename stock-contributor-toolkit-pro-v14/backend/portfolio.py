"""
Portfolio Tracker - manual sales/download logging for contributors.

No scraping: contributors paste numbers from their Adobe Stock /
Shutterstock dashboards whenever they like. The toolkit stores them in
a local JSON file and renders totals, per-asset and per-platform stats,
and simple time-series for the dashboard.

Data lives in data/portfolio.json (gitignored).

v11 (Prompt #4, Job E2) upgrades — data file + API shapes stay
compatible (new fields only):
  * CSV import with flexible header mapping + bulk paste,
  * decision analytics: totals by platform AND asset type AND month,
    earnings/download, earnings/asset, views->download conversion %,
    Top 10 / Bottom 10, monthly earnings series,
  * "sleeping assets" (0 downloads after 60+ days) for re-optimising,
  * monthly goals + month-end pace projection (labelled estimate),
  * JSON backup export / restore.
"""

import csv
import datetime
import io
import json
import os
import re
import threading
import uuid
from calendar import monthrange

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE, "data")
DATA_FILE = os.path.join(DATA_DIR, "portfolio.json")
os.makedirs(DATA_DIR, exist_ok=True)

_lock = threading.Lock()

PLATFORMS = ["Adobe Stock", "Shutterstock", "Pond5", "Getty", "Other"]


def _blank():
    return {"assets": [], "entries": [],
            "goals": {"downloads": 0, "earnings": 0.0}}


def _load():
    if not os.path.isfile(DATA_FILE):
        return _blank()
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            d = json.load(f)
        d.setdefault("assets", [])
        d.setdefault("entries", [])
        d.setdefault("goals", {"downloads": 0, "earnings": 0.0})
        return d
    except (json.JSONDecodeError, OSError):
        return _blank()


def _save(d):
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1)
    os.replace(tmp, DATA_FILE)


def list_assets():
    with _lock:
        return _load()["assets"]


def add_asset(title, platform, asset_type="image", upload_date=None):
    asset = {
        "id": uuid.uuid4().hex[:10],
        "title": (title or "").strip() or "Untitled",
        "platform": platform if platform in PLATFORMS else "Other",
        "type": asset_type if asset_type in ("image", "video", "vector") else "image",
        "upload_date": upload_date or datetime.date.today().isoformat(),
        "created_at": datetime.datetime.utcnow().isoformat(),
    }
    with _lock:
        d = _load()
        d["assets"].append(asset)
        _save(d)
    return asset


def delete_asset(asset_id):
    with _lock:
        d = _load()
        d["assets"] = [a for a in d["assets"] if a["id"] != asset_id]
        d["entries"] = [e for e in d["entries"] if e["asset_id"] != asset_id]
        _save(d)
    return True


def log_entry(asset_id, date=None, downloads=0, views=0, earnings=0.0):
    with _lock:
        d = _load()
        if not any(a["id"] == asset_id for a in d["assets"]):
            raise ValueError("Unknown asset.")
        entry = {
            "id": uuid.uuid4().hex[:10],
            "asset_id": asset_id,
            "date": date or datetime.date.today().isoformat(),
            "downloads": max(0, int(downloads)),
            "views": max(0, int(views)),
            "earnings": max(0.0, float(earnings)),
        }
        d["entries"].append(entry)
        _save(d)
    return entry


def stats():
    """Totals, per-platform, per-asset, and 30-day series.
    v11 adds: by_type, by_month, earnings/download + /asset, per-asset
    conversion %, earnings series per month, top10/bottom10, sleeping
    assets, goals + pace projection. All additive."""
    with _lock:
        d = _load()
    assets = {a["id"]: a for a in d["assets"]}
    entries = d["entries"]

    total_dl = sum(e["downloads"] for e in entries)
    total_views = sum(e["views"] for e in entries)
    total_earn = round(sum(e["earnings"] for e in entries), 2)

    by_platform = {}
    by_type = {}
    by_month = {}
    for e in entries:
        a = assets.get(e["asset_id"])
        p = (a or {}).get("platform", "Other")
        b = by_platform.setdefault(p, {"downloads": 0, "views": 0, "earnings": 0.0})
        b["downloads"] += e["downloads"]
        b["views"] += e["views"]
        b["earnings"] = round(b["earnings"] + e["earnings"], 2)
        t = (a or {}).get("type", "image")
        bt = by_type.setdefault(t, {"downloads": 0, "views": 0, "earnings": 0.0})
        bt["downloads"] += e["downloads"]
        bt["views"] += e["views"]
        bt["earnings"] = round(bt["earnings"] + e["earnings"], 2)
        m = (e.get("date") or "")[:7]
        if re.fullmatch(r"\d{4}-\d{2}", m or ""):
            bm = by_month.setdefault(m, {"downloads": 0, "views": 0, "earnings": 0.0})
            bm["downloads"] += e["downloads"]
            bm["views"] += e["views"]
            bm["earnings"] = round(bm["earnings"] + e["earnings"], 2)

    today = datetime.date.today()
    by_asset = []
    sleeping = []
    for a in d["assets"]:
        es = [e for e in entries if e["asset_id"] == a["id"]]
        dl = sum(e["downloads"] for e in es)
        vw = sum(e["views"] for e in es)
        er = round(sum(e["earnings"] for e in es), 2)
        row = {
            "id": a["id"], "title": a["title"], "platform": a["platform"],
            "type": a["type"], "upload_date": a["upload_date"],
            "downloads": dl, "views": vw, "earnings": er,
            "entries": len(es),
            "conversion": round(100.0 * dl / vw, 1) if vw else None,
            "earn_per_dl": round(er / dl, 2) if dl else None,
        }
        by_asset.append(row)
        try:
            up = datetime.date.fromisoformat(a["upload_date"])
        except (ValueError, TypeError):
            up = today
        days_old = (today - up).days
        if dl == 0 and days_old >= 60:
            sleeping.append({**row, "days_old": days_old})
    by_asset.sort(key=lambda x: (-x["downloads"], -x["earnings"]))
    top10 = by_asset[:10]
    bottom10 = sorted(by_asset,
                      key=lambda x: (x["downloads"], x["earnings"]))[:10]
    sleeping.sort(key=lambda x: -x["days_old"])

    days = [(today - datetime.timedelta(days=i)).isoformat() for i in range(29, -1, -1)]
    per_day = {day: {"downloads": 0, "earnings": 0.0} for day in days}
    for e in entries:
        if e["date"] in per_day:
            per_day[e["date"]]["downloads"] += e["downloads"]
            per_day[e["date"]]["earnings"] = round(
                per_day[e["date"]]["earnings"] + e["earnings"], 2)
    series = [{"date": day, **per_day[day]} for day in days]

    months_sorted = sorted(by_month)
    earnings_monthly = [{"month": m, **by_month[m]} for m in months_sorted]

    goals = d.get("goals") or {"downloads": 0, "earnings": 0.0}
    cur_key = today.strftime("%Y-%m")
    cur = by_month.get(cur_key, {"downloads": 0, "earnings": 0.0})
    dim = monthrange(today.year, today.month)[1]
    pace_dl = cur["downloads"] * dim // today.day if today.day else 0
    pace_er = round(cur["earnings"] * dim / today.day, 2) if today.day else 0.0
    goal_block = {
        "goals": {"downloads": int(goals.get("downloads") or 0),
                  "earnings": float(goals.get("earnings") or 0.0)},
        "month": cur_key,
        "current": {"downloads": cur["downloads"],
                    "earnings": cur["earnings"]},
        "pct_downloads": (round(100.0 * cur["downloads"] / goals["downloads"], 1)
                          if goals.get("downloads") else None),
        "pct_earnings": (round(100.0 * cur["earnings"] / goals["earnings"], 1)
                         if goals.get("earnings") else None),
        "projection": {"downloads": pace_dl, "earnings": pace_er,
                       "label": "estimate — month-end at current pace"},
    }

    return {
        "totals": {"assets": len(d["assets"]), "downloads": total_dl,
                   "views": total_views, "earnings": total_earn},
        "by_platform": by_platform,
        "by_asset": by_asset,
        "series_30d": series,
        # ---- v11 additions ----
        "by_type": by_type,
        "by_month": by_month,
        "earnings_monthly": earnings_monthly,
        "earnings_per_download": round(total_earn / total_dl, 2)
                                 if total_dl else 0.0,
        "earnings_per_asset": round(total_earn / len(d["assets"]), 2)
                              if d["assets"] else 0.0,
        "top10": top10,
        "bottom10": bottom10,
        "sleeping": sleeping,
        "goals": goal_block,
    }


# ------------------------------------------------------- v11: goals

def get_goals():
    with _lock:
        d = _load()
    return d.get("goals") or {"downloads": 0, "earnings": 0.0}


def set_goals(downloads=0, earnings=0.0):
    with _lock:
        d = _load()
        d["goals"] = {"downloads": max(0, int(downloads or 0)),
                      "earnings": max(0.0, float(earnings or 0.0))}
        _save(d)
        return d["goals"]


# ------------------------------------------------- v11: CSV import

_SYNONYMS = {
    "title": ["title", "asset", "name", "file", "description"],
    "platform": ["platform", "agency", "site", "marketplace", "store"],
    "type": ["type", "media", "format", "kind"],
    "date": ["date", "day", "uploaded", "sold", "period"],
    "downloads": ["downloads", "download", "sales", "sold", "licenses",
                  "qty", "quantity"],
    "views": ["views", "view", "impressions", "seen"],
    "earnings": ["earnings", "earning", "revenue", "income", "amount",
                 "royalties", "royalty", "usd", "$", "total"],
}


def detect_mapping(headers):
    """Map canonical field -> actual header (or None). Detection is by
    header synonyms; the UI shows this mapping to the contributor."""
    norm = {h: re.sub(r"[^a-z$]", "", (h or "").lower()) for h in headers}
    mapping = {}
    for field, words in _SYNONYMS.items():
        best = None
        for h in headers:
            hn = norm[h]
            if any(w.replace("$", "\\$") and (w == hn or w in hn)
                   for w in words):
                best = h
                break
        mapping[field] = best
    return mapping


def _num(value, cast):
    try:
        s = str(value or "").replace(",", "").replace("$", "").strip()
        return cast(float(s)) if cast is float else int(float(s))
    except (TypeError, ValueError):
        return cast(0)


def _norm_date(value):
    s = str(value or "").strip()[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return datetime.date.today().isoformat()


def _norm_platform(value):
    s = str(value or "").strip().lower()
    for p in PLATFORMS:
        if p.lower() in s or s in p.lower():
            return p
    if "adobe" in s:
        return "Adobe Stock"
    if "shutter" in s:
        return "Shutterstock"
    if "pond" in s:
        return "Pond5"
    if "getty" in s or "istock" in s:
        return "Getty"
    return "Other"


def _norm_type(value):
    s = str(value or "").strip().lower()
    if "video" in s or "footage" in s or "clip" in s:
        return "video"
    if "vector" in s or "eps" in s or "illustration" in s:
        return "vector"
    return "image"


def import_csv(text):
    """Import contributor-dashboard CSV. Assets are auto-created (keyed
    by title + platform); each row becomes one dated log entry. Returns
    {mapping, created_assets, entries, skipped, headers}."""
    reader = csv.DictReader(io.StringIO(text or ""))
    if not reader.fieldnames:
        raise ValueError("No CSV header row found.")
    headers = [h for h in reader.fieldnames if h]
    mapping = detect_mapping(headers)
    if not mapping.get("title"):
        raise ValueError("Could not find a title column. Headers seen: " +
                         ", ".join(headers))
    created, entries_made, skipped = [], 0, 0
    with _lock:
        d = _load()
        index = {(a["title"].lower(), a["platform"]): a for a in d["assets"]}
        for row in reader:
            title = str(row.get(mapping["title"]) or "").strip()
            if not title:
                skipped += 1
                continue
            platform = _norm_platform(row.get(mapping["platform"])) \
                if mapping.get("platform") else "Adobe Stock"
            key = (title.lower(), platform)
            asset = index.get(key)
            if asset is None:
                asset = {
                    "id": uuid.uuid4().hex[:10], "title": title,
                    "platform": platform,
                    "type": _norm_type(row.get(mapping["type"]))
                            if mapping.get("type") else "image",
                    "upload_date": _norm_date(row.get(mapping["date"]))
                                   if mapping.get("date")
                                   else datetime.date.today().isoformat(),
                    "created_at": datetime.datetime.utcnow().isoformat(),
                }
                d["assets"].append(asset)
                index[key] = asset
                created.append(asset["title"])
            d["entries"].append({
                "id": uuid.uuid4().hex[:10], "asset_id": asset["id"],
                "date": _norm_date(row.get(mapping["date"]))
                        if mapping.get("date")
                        else datetime.date.today().isoformat(),
                "downloads": _num(row.get(mapping["downloads"]), int)
                             if mapping.get("downloads") else 0,
                "views": _num(row.get(mapping["views"]), int)
                         if mapping.get("views") else 0,
                "earnings": _num(row.get(mapping["earnings"]), float)
                            if mapping.get("earnings") else 0.0,
            })
            entries_made += 1
        _save(d)
    return {"mapping": {k: v for k, v in mapping.items()},
            "headers": headers, "created_assets": created,
            "entries": entries_made, "skipped": skipped}


def import_paste(text):
    """Bulk paste: one asset per line, tab- or comma-separated:
    Title [, Platform] [, Downloads] [, Views] [, Earnings].
    Converted to CSV and fed through import_csv so mapping/analytics
    behave identically."""
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    if not lines:
        raise ValueError("Nothing to import — paste at least one line.")
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["title", "platform", "downloads", "views", "earnings"])
    for ln in lines:
        parts = [p.strip() for p in re.split(r"\t|,", ln)]
        title = parts[0]
        platform = parts[1] if len(parts) > 1 and parts[1] else "Adobe Stock"
        nums = parts[2:5] + ["0"] * (5 - len(parts))
        w.writerow([title, platform, nums[0] or "0", nums[1] or "0",
                    nums[2] or "0"])
    return import_csv(out.getvalue())


# ------------------------------------------------- v11: backup

def export_backup():
    with _lock:
        return _load()


def import_backup(data):
    if not isinstance(data, dict) or not isinstance(data.get("assets"), list) \
            or not isinstance(data.get("entries"), list):
        raise ValueError("Not a Portfolio backup file "
                         "(needs assets + entries lists).")
    with _lock:
        d = _blank()
        d["assets"] = data["assets"]
        d["entries"] = data["entries"]
        if isinstance(data.get("goals"), dict):
            d["goals"] = {"downloads": int(data["goals"].get("downloads") or 0),
                          "earnings": float(data["goals"].get("earnings") or 0.0)}
        _save(d)
    return {"assets": len(d["assets"]), "entries": len(d["entries"])}
