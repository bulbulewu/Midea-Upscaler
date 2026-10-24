"""
Market scan cache (v12, Prompt #5 Part B.6).

RA Graphic Studio's rule — "the same search is free within 15 minutes" —
minus its credit system (this app has no credits): an identical scan
(same mode + query + category + AI filter + limit + actor) repeated
within 15 minutes is served from this server-side cache and costs NO
Apify call. After 15 minutes it fetches live again; a "force fresh"
toggle bypasses the cache. If a live scan fails and a stale entry exists,
the route offers it explicitly — never silently.

Store: data/market_scan_cache.json (overridable with the
TOOLKIT_MARKET_CACHE env var for tests). The cache key is a SHA-256 of
the scan parameters only — the Apify TOKEN IS NEVER part of the key and
NEVER written to the file. All IO is defensive: a broken cache file must
never break scanning.
"""

import hashlib
import json
import os
import threading
import time

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PATH = os.environ.get("TOOLKIT_MARKET_CACHE") or os.path.join(
    _BASE, "data", "market_scan_cache.json")
_lock = threading.Lock()
TTL_SECONDS = 15 * 60


def _blank():
    return {"entries": {}, "meta": {"hits": 0, "fetches": 0,
                                    "apify_calls": 0, "scans": 0}}


def _load():
    try:
        with open(_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            return _blank()
        data.setdefault("entries", {})
        data.setdefault("meta", _blank()["meta"])
        for k, v in _blank()["meta"].items():
            data["meta"].setdefault(k, v)
        return data
    except (OSError, ValueError):
        return _blank()


def _save(data):
    try:
        os.makedirs(os.path.dirname(_PATH), exist_ok=True)
        tmp = _PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, _PATH)
    except OSError:
        pass  # cache must never break the feature


def key_for(params):
    """Stable key from scan parameters (never the token)."""
    canon = {
        "mode": (params.get("mode") or "keyword").strip().lower(),
        "query": (params.get("query") or "").strip().lower(),
        "category": (params.get("category") or "all").strip().lower(),
        "ai_filter": (params.get("ai_filter") or "all").strip().lower(),
        "limit": int(params.get("limit") or 50),
        "actor": (params.get("actor") or "").strip(),
        "demo": bool(params.get("demo")),
    }
    raw = json.dumps(canon, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24], canon


def get(params, allow_stale=False):
    """Return {ts, payload, age_s} when an entry exists (and is fresh,
    unless allow_stale). A fresh hit is counted in meta."""
    key, _ = key_for(params)
    with _lock:
        data = _load()
        entry = data["entries"].get(key)
        if not entry:
            return None
        age = time.time() - entry.get("ts", 0)
        if age > TTL_SECONDS and not allow_stale:
            return None
        if age <= TTL_SECONDS:
            data["meta"]["hits"] += 1
            data["meta"]["scans"] += 1
            _save(data)
        return {"ts": entry["ts"], "payload": entry["payload"],
                "age_s": int(age)}


def get_stale(params):
    return get(params, allow_stale=True)


def put(params, payload, apify_call=False):
    key, canon = key_for(params)
    with _lock:
        data = _load()
        data["entries"][key] = {"ts": time.time(), "params": canon,
                                "payload": payload}
        data["meta"]["fetches"] += 1
        data["meta"]["scans"] += 1
        if apify_call:
            data["meta"]["apify_calls"] += 1
        _save(data)


def note_scan():
    with _lock:
        data = _load()
        data["meta"]["scans"] += 1
        _save(data)


def stats():
    with _lock:
        data = _load()
        return {"cached_entries": len(data["entries"]),
                "hits": data["meta"]["hits"],
                "fetches": data["meta"]["fetches"],
                "apify_calls": data["meta"]["apify_calls"],
                "scans": data["meta"]["scans"],
                "ttl_seconds": TTL_SECONDS}


def clear():
    with _lock:
        data = _load()
        n = len(data["entries"])
        data["entries"] = {}
        _save(data)
        return n
