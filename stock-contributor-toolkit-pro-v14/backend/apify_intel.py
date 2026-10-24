"""
Apify integration — OPTIONAL upgrade, using YOUR OWN free Apify token.

Original app had NO Apify code at all. It used only:
  - Datamuse (free, no key) for keyword expansion
  - Google News RSS (free, no key) for Trend Intel
  - Optional Gemini key for Metadata Studio

This module adds Apify as an opt-in enhancer, exactly like the Gemini
pattern already in the app:

  * Token is NEVER stored server-side. It is sent per-request from the
    browser, OR read from the server env var APIFY_TOKEN if you set it
    on your own host (e.g. Render env vars).
  * Get a free token: https://console.apify.com/settings/integrations
    (Apify Console -> Settings -> API & Integrations -> Personal API token)
    Apify's free plan gives monthly platform credits, no card required.
  * If no token / actor fails / credits exhausted -> callers fall back
    silently to the free built-in engines. The app stays 100% free and
    functional without Apify.

What Apify adds (best results):
  1. Google Search results for a keyword via the well-known Actor
     `apify/google-search-scraper` — real SERP titles, related searches
     and people-also-ask style queries buyers actually type.
  2. A generic Actor runner: paste ANY Actor ID from the Apify Store
     (e.g. a stock-site, Instagram, TikTok, Pinterest or Google Trends
     scraper you choose) and run it with JSON input, get dataset items.

Apify API used (v2, documented):
  GET  /v2/users/me
  POST /v2/acts/{username}~{actor}/run-sync-get-dataset-items
  Auth: Authorization: Bearer <token>
"""

import json
import os
import re
import urllib.parse
import urllib.request

API_BASE = "https://api.apify.com/v2"

# Presets the UI offers. Actor IDs are user-editable in the UI, so if
# Apify renames one or you prefer another scraper, just change it there.
PRESETS = {
    "google_search": {
        "label": "Google Search Scraper (related searches + SERP)",
        "actor": "apify~google-search-scraper",
        "build_input": lambda kw, n: {
            "queries": kw, "maxPagesPerQuery": 1,
            "resultsPerPage": min(max(int(n or 10), 3), 25),
            "languageCode": "en",
        },
    },
    "google_trends": {
        "label": "Google Trends Scraper (interest over time)",
        "actor": "apify~google-trends-scraper",
        "build_input": lambda kw, n: {"searchTerm": kw},
    },
}


def resolve_token(supplied=None):
    """Per-request token wins; else server env APIFY_TOKEN; else None."""
    t = (supplied or "").strip()
    return t or (os.environ.get("APIFY_TOKEN") or "").strip() or None


def _request(method, path, token, payload=None, timeout=120):
    url = API_BASE + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json",
                 "User-Agent": "stock-toolkit-pro/apify"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8") or "null"
        return json.loads(raw)


def check_token(token, timeout=20):
    """Validate a token. Returns {ok, username, plan, error?} — never raises."""
    token = resolve_token(token)
    if not token:
        return {"ok": False, "error": "No Apify token supplied."}
    try:
        data = _request("GET", "/users/me", token, timeout=timeout)
        u = data.get("data") or {}
        return {"ok": True, "username": u.get("username"),
                "plan": (u.get("plan") or {}).get("id") if isinstance(u.get("plan"), dict) else u.get("plan"),
                "source": "apify"}
    except urllib.error.HTTPError as e:
        msg = "Token rejected by Apify (401/403). Check you copied the full Personal API token." if e.code in (401, 403) else f"Apify returned HTTP {e.code}."
        return {"ok": False, "error": msg}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"Could not reach Apify: {e}"}


def run_actor_sync(token, actor_id, actor_input, timeout=180):
    """
    Run any Actor synchronously and return dataset items (list).
    actor_id may be 'username/actor', 'username~actor' or just 'actor'
    (assumes apify/ namespace). Raises on HTTP failure — callers fallback.
    """
    token = resolve_token(token)
    if not token:
        raise ValueError("No Apify token supplied.")
    actor = (actor_id or "").strip()
    if "/" in actor:
        actor = actor.replace("/", "~", 1)
    if "~" not in actor:
        actor = "apify~" + actor
    actor = urllib.parse.quote(actor, safe="~")
    items = _request("POST", f"/acts/{actor}/run-sync-get-dataset-items",
                     token, payload=actor_input or {}, timeout=timeout)
    if isinstance(items, dict):  # some endpoints wrap in data
        items = items.get("data") or items.get("items") or []
    return items if isinstance(items, list) else []


def _clean_words(items):
    """Extract buyer-style phrases from Google Search actor output."""
    out, seen = [], set()

    def add(text):
        t = re.sub(r"\s+", " ", str(text or "")).strip().lower()
        if 3 <= len(t) <= 60 and t not in seen:
            seen.add(t); out.append(t)

    for it in items or []:
        if not isinstance(it, dict):
            continue
        for k in ("relatedSearches", "relatedQueries", "peopleAlsoAsk"):
            v = it.get(k)
            if isinstance(v, list):
                for x in v:
                    add(x.get("query") or x.get("title") or x if isinstance(x, dict) else x)
            elif isinstance(v, str):
                add(v)
        for r in (it.get("organicResults") or []):
            if isinstance(r, dict):
                # titles give phrase ideas; keep short noun-ish chunks
                add(r.get("title", "").split("|")[0].split(" - ")[0])
        add(it.get("query")); add(it.get("searchQuery"))
    return out[:40]


def enrich_keyword(keyword, token, max_results=10, timeout=180):
    """
    Best-results keyword/trend enrichment via Apify Google Search.
    Returns dict; on any failure returns {ok: False, error, fallback: True}.
    """
    token = resolve_token(token)
    if not token:
        return {"ok": False, "fallback": True, "error": "No Apify token — using free built-in engine."}
    preset = PRESETS["google_search"]
    try:
        items = run_actor_sync(token, preset["actor"],
                               preset["build_input"](keyword, max_results),
                               timeout=timeout)
        phrases = _clean_words(items)
        serp = []
        for it in items or []:
            for r in (it.get("organicResults") or [])[:10]:
                if isinstance(r, dict) and r.get("title"):
                    serp.append({"title": r.get("title"), "url": r.get("url", ""), "description": r.get("description", "")})
        return {"ok": True, "source": "apify/google-search-scraper",
                "items_count": len(items), "related_phrases": phrases,
                "serp_results": serp[:10]}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "fallback": True,
                "error": f"Apify run failed ({e}) — fell back to free engine. Check token/credits or Actor ID."}
