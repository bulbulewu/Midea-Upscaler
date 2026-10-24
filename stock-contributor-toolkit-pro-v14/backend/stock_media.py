"""
Promo Maker v9 — stock media picker (Promo.com's library, the honest
local way): search Pexels or Pixabay with the USER'S OWN free API key
(per-request, never stored). Results show the photographer's name —
attribution guidance from both APIs is respected in the UI.

  Pexels : https://www.pexels.com/api/  (free key: pexels.com/api)
  Pixabay: https://pixabay.com/api/docs/ (free key: pixabay.com/api/docs/)
"""

import json
import os
import urllib.parse
import urllib.request


def _get_json(url, headers=None, timeout=45):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def search_pexels(key, query, media="photo", per_page=18):
    key = (key or "").strip()
    if not key:
        raise ValueError("Paste your free Pexels API key first — get one at pexels.com/api (never stored).")
    q = urllib.parse.urlencode({"query": query, "per_page": per_page})
    if media == "video":
        data = _get_json(f"https://api.pexels.com/videos/search?{q}",
                         {"Authorization": key})
        out = []
        for v in data.get("videos", []):
            files = v.get("video_files") or []
            pick = next((f for f in files if f.get("quality") == "hd"), files[0] if files else {})
            out.append({"id": v.get("id"), "type": "video",
                        "thumb": (v.get("image") or ""),
                        "download": pick.get("link", ""),
                        "photographer": (v.get("user") or {}).get("name", ""),
                        "page": v.get("url", ""), "source": "Pexels"})
        return out
    data = _get_json(f"https://api.pexels.com/v1/search?{q}", {"Authorization": key})
    return [{"id": p.get("id"), "type": "photo",
             "thumb": (p.get("src") or {}).get("medium", ""),
             "download": (p.get("src") or {}).get("large2x") or (p.get("src") or {}).get("original", ""),
             "photographer": p.get("photographer", ""),
             "page": p.get("url", ""), "source": "Pexels"}
            for p in data.get("photos", [])]


def search_pixabay(key, query, media="photo", per_page=18):
    key = (key or "").strip()
    if not key:
        raise ValueError("Paste your free Pixabay API key first — get one at pixabay.com/api/docs/ (never stored).")
    q = urllib.parse.urlencode({"key": key, "q": query, "per_page": per_page,
                                "image_type": "photo", "safesearch": "true"})
    if media == "video":
        q = urllib.parse.urlencode({"key": key, "q": query, "per_page": per_page,
                                    "safesearch": "true"})
        data = _get_json(f"https://pixabay.com/api/videos/?{q}")
        out = []
        for v in data.get("hits", []):
            files = v.get("videos") or {}
            pick = files.get("large") or files.get("medium") or {}
            out.append({"id": v.get("id"), "type": "video",
                        "thumb": "", "download": pick.get("url", ""),
                        "photographer": v.get("user", ""),
                        "page": v.get("pageURL", ""), "source": "Pixabay"})
        return out
    data = _get_json(f"https://pixabay.com/api/?{q}")
    return [{"id": p.get("id"), "type": "photo",
             "thumb": p.get("previewURL", ""),
             "download": p.get("largeImageURL") or p.get("webformatURL", ""),
             "photographer": p.get("user", ""),
             "page": p.get("pageURL", ""), "source": "Pixabay"}
            for p in data.get("hits", [])]


def search(provider, key, query, media="photo"):
    query = (query or "").strip()
    if not query:
        raise ValueError("Type what to search for (e.g. 'leather wallet product').")
    if provider == "pixabay":
        return search_pixabay(key, query, media)
    return search_pexels(key, query, media)


def download(url, dst):
    if not url or not url.startswith("https://"):
        raise ValueError("That result has no downloadable file.")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 ToolkitPro"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
    if len(data) < 1000:
        raise RuntimeError("Downloaded file looks empty — try another result.")
    with open(dst, "wb") as f:
        f.write(data)
    return dst
