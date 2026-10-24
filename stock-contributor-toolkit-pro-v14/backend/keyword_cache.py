"""
Keyword Research result cache (v11, Prompt #4 Job D).

Pattern adapted from the RA-Tracker desktop app the owner supplied
(cache.py + fetch_worker.py): check the disk cache BEFORE calling the
network; on a miss, fetch, then save. Re-searching the same seed is then
instant and spends NO Apify credit.

Store: data/keyword_cache.json (app-local; overridable with the
TOOLKIT_KW_CACHE env var for tests). Entries are keyed by
"<normalised seed>|<sources used>" so a no-token result never masquerades
as an Apify-boosted one. All IO is defensive — a broken cache file must
never break keyword research (same rule as RA-Tracker's cache.py).
"""

import json
import os
import threading
from datetime import datetime

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PATH = os.environ.get("TOOLKIT_KW_CACHE") or os.path.join(
    _BASE, "data", "keyword_cache.json")
_lock = threading.Lock()


def _blank():
    return {"entries": {}, "meta": {"hits": 0, "fetches": 0,
                                     "searches": 0, "last_search": None}}


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


def _key(seed, sources):
    return f"{(seed or '').strip().lower()}|{sources}"


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def get(seed, sources):
    """Return the cache entry {ts, payload} or None. A hit is counted."""
    with _lock:
        data = _load()
        entry = data["entries"].get(_key(seed, sources))
        if entry:
            data["meta"]["hits"] += 1
            data["meta"]["searches"] += 1
            data["meta"]["last_search"] = _now()
            _save(data)
            return entry
        return None


def put(seed, sources, payload):
    with _lock:
        data = _load()
        data["entries"][_key(seed, sources)] = {
            "seed": (seed or "").strip().lower(), "sources": sources,
            "ts": _now(), "payload": payload}
        data["meta"]["fetches"] += 1
        data["meta"]["searches"] += 1
        data["meta"]["last_search"] = _now()
        _save(data)


def stats():
    with _lock:
        data = _load()
        return {"cached_entries": len(data["entries"]),
                "hits": data["meta"]["hits"],
                "fetches": data["meta"]["fetches"],
                "searches": data["meta"]["searches"],
                "last_search": data["meta"]["last_search"]}


def clear():
    with _lock:
        data = _load()
        n = len(data["entries"])
        data["entries"] = {}
        _save(data)
        return n
