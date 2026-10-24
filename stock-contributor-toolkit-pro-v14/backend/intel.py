"""
Trend Intel - free demand signals for stock keywords.

No API keys, no scraping of stock sites. Two honest signals:
  1. News pulse: Google News RSS article volume for a keyword
     (buyer/media attention proxy), computed over the last 7 days.
  2. Seasonality: maps the keyword onto the editorial trend calendar
     (upload-by deadlines + demand level).

Combined into an "opportunity brief" with a 0-100 demand score.
Results are cached in-memory for 10 minutes.
"""

import datetime
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

from .trends import EVENTS
from .metadata import expand_keywords

CACHE_TTL = 600
_cache = {}

NEWS_RSS = ("https://news.google.com/rss/search?q={q}"
            "&hl=en-US&gl=US&ceid=US:en")


def _fetch_rss(keyword, timeout=20):
    q = urllib.parse.quote(keyword)
    req = urllib.request.Request(NEWS_RSS.format(q=q),
                                 headers={"User-Agent": "stock-toolkit/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def news_pulse(keyword, timeout=20):
    """
    Returns {articles_7d, per_day:[{date, count}], headlines:[...], fetched_at}.
    Falls back to zeros on any failure (never raises).
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    week_ago = now - datetime.timedelta(days=7)
    per_day = {}
    headlines = []
    try:
        xml = _fetch_rss(keyword)
        root = ET.fromstring(xml)
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            pub = item.findtext("pubDate") or ""
            try:
                dt = parsedate_to_datetime(pub)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=datetime.timezone.utc)
            except (TypeError, ValueError):
                continue
            if dt < week_ago:
                continue
            day = dt.date().isoformat()
            per_day[day] = per_day.get(day, 0) + 1
            if len(headlines) < 5 and title:
                headlines.append({"title": title, "date": day})
    except Exception:
        pass
    days = [(now - datetime.timedelta(days=i)).date().isoformat() for i in range(6, -1, -1)]
    series = [{"date": d, "count": per_day.get(d, 0)} for d in days]
    return {"articles_7d": sum(per_day.values()), "per_day": series,
            "headlines": headlines, "fetched_at": now.isoformat()}


def _season_hits(keyword):
    kw = keyword.lower()
    hits = []
    for month, day, name, lead, demand, kws, note in EVENTS:
        if kw in name.lower() or any(kw in k or k in kw for k in kws):
            hits.append({"event": name, "demand": demand,
                         "upload_lead_weeks": lead,
                         "keywords": kws, "note": note})
    return hits


def opportunity_brief(keyword, timeout=20):
    keyword = keyword.strip()
    if not keyword:
        raise ValueError("Enter a keyword.")
    ck = keyword.lower()
    now = time.time()
    if ck in _cache and now - _cache[ck][0] < CACHE_TTL:
        return _cache[ck][1]

    pulse = news_pulse(keyword, timeout=timeout)
    seasons = _season_hits(keyword)
    related = expand_keywords([ck], per_seed=8)[:16]

    # demand score: news volume (0-60) + seasonality (0-40)
    vol = pulse["articles_7d"]
    vol_score = min(60, vol * 3)                      # 20+ articles/wk = max
    dem_map = {"very high": 40, "high": 30, "medium": 15}
    season_score = max([dem_map.get(s["demand"], 0) for s in seasons], default=0)
    score = min(100, vol_score + season_score)

    if score >= 70:
        verdict = "Strong signal — prioritize uploads on this topic now."
    elif score >= 40:
        verdict = "Moderate signal — good supporting topic for your portfolio."
    else:
        verdict = "Quiet right now — evergreen filler, upload anytime."

    brief = {
        "keyword": keyword,
        "demand_score": score,
        "verdict": verdict,
        "news": pulse,
        "seasonality": seasons,
        "related": related,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "note": ("Demand proxy: Google News article volume (last 7 days) + "
                 "editorial calendar. Not Adobe Stock download data."),
    }
    _cache[ck] = (now, brief)
    return brief
