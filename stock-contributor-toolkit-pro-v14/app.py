"""
Stock Contributor Toolkit Pro
Phase 1: Metadata Studio · Keyword Research · Trend Calendar · Title Optimizer · Extension
Phase 2: Trend Intel · Portfolio Tracker · SVG to Video · Vectorizer
Phase 3: Apify Boost (optional, your own free token) · Motion Video Studio

Deploy: Render.com (Docker) or any Python host. Free tier friendly.
"""

import argparse
import io
import os
import secrets
import subprocess
import sys
import threading
import uuid
import webbrowser
from datetime import datetime

from flask import (Flask, jsonify, render_template, request, send_file,
                   session)
from werkzeug.utils import secure_filename

from backend.metadata import (generate_metadata, expand_keywords, to_csv,
                              to_csv_for, process_asset, image_to_prompt,
                              MARKETPLACE_RULES)
from backend import tracker as tracker_mod
from backend import calendar_data
from backend import embed as embed_mod
from backend.trends import get_calendar
from backend import optimizer as optimizer_mod
from backend import keyword_cache
from backend import market_cache
from backend import subtopics as subtopics_mod
from backend.intel import opportunity_brief
from backend import portfolio
from backend.svg_video import svg_to_video
from backend import apify_intel
from backend.motion import create_motion_video, TEMPLATES as MOTION_TEMPLATES
from backend.mgfx import create_mgfx, CATALOG as MGFX_CATALOG
from backend import ai_hub
from backend import ai_video
from backend.promo import (create_promo, TEMPLATE_INFO as PROMO_TEMPLATES,
                           make_placeholders as promo_make_placeholders)
from backend import promo_audio, promo_script, stock_media
from backend import auth_store
from backend import prompt_motion

BASE = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE, "uploads")
OUTPUT_DIR = os.path.join(BASE, "outputs")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}

app = Flask(__name__,
            template_folder=os.path.join(BASE, "templates"),
            static_folder=os.path.join(BASE, "static"))
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB

# ------------------------------------------------------- v8: local accounts
# Auth store: data/auth_store.json (override with TOOLKIT_AUTH_FILE).
# Ships EMPTY — no user data in the ZIP. If the file is absent the app is
# in "not set up" mode and behaves exactly like v7 (open, unlimited).
AUTH_FILE = os.environ.get("TOOLKIT_AUTH_FILE") or os.path.join(
    BASE, "data", "auth_store.json")
auth_store.configure(AUTH_FILE)
_SECRET_FILE = AUTH_FILE + ".secret"
try:
    if os.path.isfile(_SECRET_FILE):
        with open(_SECRET_FILE, encoding="utf-8") as _f:
            app.secret_key = _f.read().strip()
    else:
        app.secret_key = secrets.token_hex(32)
        os.makedirs(os.path.dirname(_SECRET_FILE) or ".", exist_ok=True)
        with open(_SECRET_FILE, "w", encoding="utf-8") as _f:
            _f.write(app.secret_key)
except Exception:  # noqa: BLE001 — sessions are a bonus, never a blocker
    app.secret_key = secrets.token_hex(32)


def _session_user():
    """public_user dict for the logged-in session user, or None."""
    email = session.get("user_email")
    if not email:
        return None
    return auth_store.public_user(auth_store.get_user(email))


def _usage_gate():
    """v8 light enforcement (see backend/auth_store.check_and_count).
    Returns a Flask (response, status) tuple to return, or None to proceed.
    Admins, logged-out visitors and the not-set-up state are NEVER gated;
    internal errors fail open so a bug can never lock the owner out."""
    try:
        blocked = auth_store.check_and_count(session.get("user_email"))
    except Exception:  # noqa: BLE001
        return None
    if blocked:
        return jsonify({"error": blocked["error"]}), blocked["status"]
    return None

# ------------------------------------------------------------ job runner
jobs = {}
jobs_lock = threading.Lock()


def _start_job(kind, src, dst, params, filename):
    job_id = uuid.uuid4().hex[:12]
    job = {"id": job_id, "kind": kind, "src": src, "dst": dst,
           "params": params, "filename": filename,
           "state": "queued", "progress": 0.0, "meta": None, "error": None,
           "download_name": os.path.basename(dst),
           "created_at": datetime.utcnow().isoformat()}
    with jobs_lock:
        jobs[job_id] = job
    threading.Thread(target=_run_job, args=(job_id,), daemon=True).start()
    return {"id": job_id}


def _run_job(job_id):
    with jobs_lock:
        job = jobs[job_id]
    job["state"] = "running"

    def _cb(frac, _m=None):
        with jobs_lock:
            job["progress"] = round(frac * 100, 1)

    try:
        p = job["params"]
        if job["kind"] == "svg-video":
            meta = svg_to_video(job["src"], job["dst"], duration=p["duration"],
                                fps=p["fps"], zoom=p["zoom"], bg=p["bg"],
                                progress_cb=_cb)
        elif job["kind"] == "motion":
            meta = create_motion_video(
                job["src"], job["dst"], template=p.get("template", "stock-broll"),
                effect=p.get("effect"), transition=p.get("transition"),
                grade=p.get("grade"), ratio=p.get("ratio", "16:9"),
                per_slide=p.get("per_slide", 4), fps=p.get("fps", 30),
                title=p.get("title", ""), subtitle=p.get("subtitle", ""),
                audio_path=p.get("audio_path"), progress_cb=_cb)
        elif job["kind"] == "mgfx":
            meta = create_mgfx(
                job["dst"], kind=p.get("kind", "bg-gradient"), theme=p.get("theme", "gold"),
                text=p.get("text", ""), subtext=p.get("subtext", ""),
                ratio=p.get("ratio", "16:9"), duration=p.get("duration", 5),
                fps=p.get("fps", 30), image_path=p.get("image_path"),
                logo_path=p.get("logo_path"), quality=p.get("quality", "HD"),
                speed=p.get("speed", 1.0), intensity=p.get("intensity", 1.0),
                color_primary=p.get("color_primary"), color_accent=p.get("color_accent"),
                color_bg=p.get("color_bg"), fmt=p.get("format", "mp4"),
                preview=p.get("preview", False), progress_cb=_cb,
                art_motion=p.get("art_motion"), art_scale=p.get("art_scale"))
            if p.get("plan"):
                meta = {**meta, "plan": p["plan"]}
        elif job["kind"] == "ai-video":
            engine = p.get("engine", "local")
            if engine == "replicate":
                meta = ai_video.replicate_i2v(job["src"], job["dst"], p.get("token"),
                                              model_version=p.get("model", ""), progress_cb=_cb)
            elif engine == "huggingface":
                meta = ai_video.hf_i2v(job["src"], job["dst"], p.get("token"),
                                       model=p.get("model", ""), progress_cb=_cb)
            else:
                meta = ai_video.local_parallax_video(
                    job["src"], job["dst"], duration=p.get("duration", 5),
                    fps=p.get("fps", 24), ratio=p.get("ratio", "16:9"),
                    move=p.get("move", "push-in"), progress_cb=_cb)
        elif job["kind"] == "promo":
            v9 = dict(p.get("v9") or {})
            # v9 voiceover: synthesise per-scene clips here (async job) so a
            # slow TTS service never blocks the request thread.
            vspec = v9.pop("voice_spec", None)
            if vspec and v9.get("scenes"):
                clips, vfail = [], []
                for i, sc in enumerate(v9["scenes"]):
                    line = (sc.get("voiceover_line") or "").strip()
                    if not line:
                        clips.append(None)
                        continue
                    cp = os.path.join(UPLOAD_DIR, f"{job['id']}_vox{i}.mp3")
                    try:
                        promo_audio.synth_voice(
                            vspec.get("engine", "edge"), line, cp,
                            voice=vspec.get("voice", "en-US-AvaNeural"),
                            rate_pct=vspec.get("rate", 0), pitch_hz=vspec.get("pitch", 0),
                            base_url=vspec.get("base_url"), api_key=vspec.get("api_key"),
                            model=vspec.get("model"))
                        clips.append(cp)
                    except Exception as exc:  # noqa: BLE001
                        clips.append(None)
                        vfail.append(str(exc))
                if vfail and not any(clips):
                    raise RuntimeError(vfail[0])
                if any(clips):
                    v9["voice_clips"] = clips
                if vfail:
                    v9["_voice_warning"] = ("Some narration lines failed: "
                                            + vfail[0][:160])
            base_kwargs = dict(
                template=p.get("template", "sale-hero"), headline=p.get("headline", ""),
                cta=p.get("cta", ""), theme=p.get("theme", "crimson"),
                per_slide=p.get("per_slide", 3.5), fps=p.get("fps", 30),
                badge_text=p.get("badge_text", "SALE"),
                show_badge=p.get("show_badge", True), brand_text=p.get("brand_text", ""),
                anim=p.get("anim", "zoom-in"), band=p.get("band", "bottom"),
                end_card=p.get("end_card", False), audio_path=p.get("audio_path"))
            versions = p.get("versions") or [p.get("ratio", "16:9")]
            extras, metas = {}, {}
            for vi, vratio in enumerate(versions):
                vdst = job["dst"] if vi == 0 else \
                    os.path.splitext(job["dst"])[0] + f"_{vratio.replace(':', 'x')}" + \
                    os.path.splitext(job["dst"])[1]
                span = 1.0 / len(versions)
                def _vcb(frac, _m=None, _b=vi * span, _s=span):
                    _cb(_b + frac * _s)
                vmeta = create_promo(job["src"], p.get("products", []), vdst,
                                     ratio=vratio, progress_cb=_vcb,
                                     **base_kwargs, **v9)
                metas[vratio] = vmeta
                if vi == 0:
                    meta = vmeta
                    extras.update(vmeta.get("extra_files") or {})
                else:
                    extras[f"version_{vratio}"] = vdst
            job["extras"] = extras
            meta = dict(meta)
            meta["versions"] = {r: {"width": m["width"], "height": m["height"],
                                    "duration": m["duration"],
                                    "size_mb": m["size_mb"]}
                                for r, m in metas.items()}
            if v9.get("_voice_warning"):
                meta["warning"] = ((meta.get("warning") or "") + " "
                                   + v9["_voice_warning"]).strip()
        else:
            raise ValueError("Unknown job kind")
        with jobs_lock:
            job.update(state="done", progress=100.0, meta=meta,
                       finished_at=datetime.utcnow().isoformat())
    except Exception as exc:  # noqa: BLE001
        from backend.svg_render import clean_error
        with jobs_lock:
            job.update(state="error", error=clean_error(str(exc)))


@app.route("/")
def index():
    return render_template("index.html")


# ------------------------------------------------------- phase 1: metadata
SEO_EXTS = IMG_EXTS | {".svg", ".eps", ".ai", ".mp4", ".mov"}


@app.route("/api/metadata/analyze", methods=["POST"])
def analyze():
    gate = _usage_gate()
    if gate:
        return gate
    files = request.files.getlist("files") or ([request.files["file"]]
                                               if "file" in request.files else [])
    if not files:
        return jsonify({"error": "No files uploaded."}), 400
    gemini_key = (request.form.get("gemini_key") or "").strip() or None
    extra = [s.strip() for s in (request.form.get("extra_keywords") or "").split(",") if s.strip()]
    # ---- v7 SEO Studio params (all optional; absent = exact legacy flow)
    v7 = any(k in request.form for k in
             ("marketplace", "provider", "auto_extract", "auto_seo",
              "isolated", "api_key")) or \
        any(os.path.splitext(f.filename)[1].lower() in SEO_EXTS - IMG_EXTS
            for f in files)
    results = []
    for f in files[:50]:
        ext = os.path.splitext(f.filename)[1].lower()
        allowed = SEO_EXTS if v7 else IMG_EXTS
        if ext not in allowed:
            results.append({"filename": f.filename, "error": f"Unsupported type '{ext}'"})
            continue
        name = f"{uuid.uuid4().hex[:8]}_{secure_filename(f.filename)}"
        path = os.path.join(UPLOAD_DIR, name)
        f.save(path)
        try:
            if v7:
                provider = (request.form.get("provider") or "").strip() or None
                api_key = (request.form.get("api_key") or "").strip() or gemini_key
                if not provider and gemini_key:
                    provider = "gemini"
                results.append(process_asset(
                    path, UPLOAD_DIR,
                    marketplace=(request.form.get("marketplace") or "adobe"),
                    extra_seeds=extra,
                    auto_extract=(request.form.get("auto_extract", "1") == "1"),
                    auto_seo=(request.form.get("auto_seo", "1") == "1"),
                    isolated=(request.form.get("isolated", "0") == "1"),
                    provider=provider, api_key=api_key,
                    model=(request.form.get("model") or "").strip() or None,
                    base_url=(request.form.get("base_url") or "").strip() or None,
                    category=(request.form.get("category") or ""),
                    trademark_shield=(request.form.get(
                        "inspector_trademark", "1") != "0")))
                results[-1]["filename"] = f.filename
            else:
                results.append(generate_metadata(path, extra_seeds=extra, gemini_key=gemini_key))
        except Exception as exc:  # noqa: BLE001
            results.append({"filename": f.filename, "error": str(exc)})
        finally:
            try:
                os.remove(path)
            except OSError:
                pass
    return jsonify({"results": results})


@app.route("/api/metadata/csv-multi", methods=["POST"])
def csv_multi():
    """Multi-agency CSV: {rows, agency} -> that agency's CSV;
    agency='all' -> ZIP with one CSV per marketplace."""
    import zipfile
    data = request.get_json(force=True, silent=True) or {}
    rows = data.get("rows") or []
    if not rows:
        return jsonify({"error": "Nothing to export."}), 400
    agency = (data.get("agency") or "adobe").strip()
    stamp = f"{datetime.now():%Y%m%d_%H%M%S}"
    if agency == "all":
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for ag in MARKETPLACE_RULES:
                z.writestr(f"metadata_{ag}_{stamp}.csv",
                           to_csv_for(rows, ag).encode("utf-8-sig"))
        buf.seek(0)
        return send_file(buf, as_attachment=True,
                         download_name=f"metadata_all_agencies_{stamp}.zip",
                         mimetype="application/zip")
    if agency not in MARKETPLACE_RULES:
        return jsonify({"error": f"Unknown marketplace '{agency}'."}), 400
    buf = io.BytesIO(to_csv_for(rows, agency).encode("utf-8-sig"))
    return send_file(buf, as_attachment=True,
                     download_name=f"metadata_{agency}_{stamp}.csv",
                     mimetype="text/csv")


@app.route("/api/metadata/validate-key", methods=["POST"])
def metadata_validate_key():
    data = request.get_json(force=True, silent=True) or {}
    return jsonify(ai_hub.test_key(data.get("provider", "gemini"),
                                   data.get("key"),
                                   model=data.get("model") or None,
                                   base_url=data.get("base_url") or None))


@app.route("/api/metadata/prompt", methods=["POST"])
def metadata_prompt():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "No file uploaded."}), 400
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in SEO_EXTS:
        return jsonify({"error": f"Unsupported type '{ext}'"}), 400
    path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex[:8]}_{secure_filename(f.filename)}")
    f.save(path)
    try:
        provider = (request.form.get("provider") or "").strip() or None
        key = (request.form.get("api_key") or "").strip() or \
            (request.form.get("gemini_key") or "").strip() or None
        if not provider and key:
            provider = "gemini"
        out = image_to_prompt(path, UPLOAD_DIR, provider=provider, key=key,
                              model=(request.form.get("model") or "").strip() or None,
                              base_url=(request.form.get("base_url") or "").strip() or None)
        return jsonify(out)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Image to Prompt failed: {exc}"}), 502
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


@app.route("/api/metadata/embed", methods=["POST"])
def metadata_embed():
    """
    Embed & ZIP: multipart files[] + form field rows (JSON list aligned by
    filename). Originals are never modified; outputs land in a job folder
    and are validated before being reported OK (see backend/embed.py).
    """
    import json as _json
    files = [f for f in request.files.getlist("files") if f and f.filename]
    if not files:
        return jsonify({"error": "No files uploaded."}), 400
    try:
        rows = _json.loads(request.form.get("rows") or "[]")
    except Exception:
        rows = []
    by_name = {}
    for r in rows if isinstance(rows, list) else []:
        by_name[os.path.basename(r.get("filename", ""))] = r
    token = uuid.uuid4().hex[:12]
    src_dir = os.path.join(UPLOAD_DIR, f"embed_{token}")
    out_dir = os.path.join(OUTPUT_DIR, f"embed_{token}")
    os.makedirs(src_dir, exist_ok=True)
    items = []
    for f in files[:50]:
        dst_src = os.path.join(src_dir, secure_filename(f.filename))
        f.save(dst_src)
        r = by_name.get(os.path.basename(f.filename), {})
        items.append({"src": dst_src, "title": r.get("title", ""),
                      "description": r.get("description", ""),
                      "keywords": r.get("keywords", [])})
    results = embed_mod.embed_batch(items, out_dir)
    for res in results:
        res.pop("output", None)
        res.pop("sidecar", None)
    return jsonify({"token": token, "results": results})


@app.route("/api/metadata/embed-download/<token>", methods=["GET"])
def metadata_embed_zip(token):
    import zipfile
    out_dir = os.path.join(OUTPUT_DIR, f"embed_{token}")
    if not os.path.isdir(out_dir):
        return jsonify({"error": "Embed job not found."}), 404
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(os.listdir(out_dir)):
            z.write(os.path.join(out_dir, name), arcname=name)
    buf.seek(0)
    return send_file(buf, as_attachment=True,
                     download_name=f"embedded_metadata_{token}.zip",
                     mimetype="application/zip")


@app.route("/api/metadata/embed-download/<token>/<path:name>", methods=["GET"])
def metadata_embed_file(token, name):
    out_dir = os.path.join(OUTPUT_DIR, f"embed_{token}")
    path = os.path.join(out_dir, os.path.basename(name))
    if not os.path.isfile(path):
        return jsonify({"error": "File not found."}), 404
    return send_file(path, as_attachment=True, download_name=os.path.basename(name))


# ------------------------------------------------------- v7: Adobe Tracker
@app.route("/api/tracker/seasons", methods=["GET"])
def tracker_seasons():
    return jsonify({"events": tracker_mod.seasonality(),
                    "note": "Ramadan/Eid and Diwali dates are approximate (lunar calendars) — verify yearly. Buyers search 60-90 days ahead."})


@app.route("/api/tracker/month", methods=["GET"])
def tracker_month():
    """v10 — Month & Year Trend Explorer: festivals, world days and
    stock-valuable topics for any chosen month/year."""
    from datetime import date as _date
    today = _date.today()
    try:
        month = int(request.args.get("month", today.month))
        year = int(request.args.get("year", today.year))
    except (TypeError, ValueError):
        return jsonify({"error": "month and year must be numbers."}), 400
    if not 1 <= month <= 12:
        return jsonify({"error": "month must be 1-12."}), 400
    if not today.year - 1 <= year <= today.year + 3:
        return jsonify({"error": f"year must be {today.year - 1}–{today.year + 3}."}), 400
    out = calendar_data.month_events(month, year, today=today)
    out["note"] = ("Dates marked approx move yearly (lunar/religious "
                   "calendars) — verify before a big shoot.")
    return jsonify(out)


@app.route("/api/tracker/calendar", methods=["GET"])
def tracker_calendar():
    """v11 (Job A) — Full Year Calendar inside Adobe Tracker: the merged,
    deduped Trend Calendar (trends.get_calendar) + 64-occasion dataset
    (calendar_data.full_year_calendar), sorted by days-until, with
    upload-by deadlines and UPLOAD NOW / SUBMIT NOW / UPCOMING status."""
    return jsonify(calendar_data.full_year_calendar())


@app.route("/api/tracker/search", methods=["POST"])
def tracker_search():
    data = request.get_json(force=True, silent=True) or {}
    mode = data.get("mode", "keyword")
    query = (data.get("query") or "").strip()
    category = (data.get("category") or "all").strip().lower()
    sort = (data.get("sort") or "relevant").strip()
    ai_filter = (data.get("ai_filter") or "all").strip()
    try:
        limit = min(max(int(data.get("limit", 50)), 10), 200)
    except ValueError:
        limit = 50
    demo = bool(data.get("demo"))
    token = apify_intel.resolve_token(data.get("apify_token") or data.get("token"))
    # v14 (pre-delivery amendment): the Adobe Tracker tab's UI sends its
    # Actor ID as actor_id while this route originally read only actor —
    # so a filled-in Tracker form was silently treated as "no token
    # supplied". Accept both spellings.
    actor = (data.get("actor") or data.get("actor_id") or "").strip()
    # v14: reject an impossible Actor ID (e.g. a pasted screenshot file
    # name) BEFORE any Apify call, with a message that names the fix.
    if not demo and actor:
        actor_err = tracker_mod.actor_id_error(actor)
        if actor_err:
            return jsonify({"error": actor_err,
                            "invalid_actor": True}), 400
    records, source = None, None
    if not demo and token and actor and query:
        try:
            raw = apify_intel.run_actor_sync(
                token, actor,
                tracker_mod.build_actor_input(mode, query, category, sort,
                                              ai_filter, limit))
            records = tracker_mod.normalize_items(raw)
            source = f"apify:{actor}"
        except Exception as exc:  # noqa: BLE001
            if tracker_mod.is_actor_not_found(exc):
                return jsonify(
                    {"error": tracker_mod.actor_not_found_message(actor)}
                ), 502
            return jsonify({"error": f"Apify run failed: {exc}. "
                                     "Check the token, your credits, or the Actor ID — or switch Demo data on."}), 502
    if records is None:
        records = tracker_mod.load_sample()
        source = "demo"
        demo = True
        if query and mode == "keyword":
            toks = [t for t in query.lower().split() if len(t) > 2]
            matched = [r for r in records
                       if any(t in (r["title"] or "").lower() or
                              t in " ".join(r["keywords"]) for t in toks)]
            if matched:
                records = matched
    # filters
    if category != "all":
        records = [r for r in records if r["type"] == category]
    if ai_filter == "human":
        records = [r for r in records if not r["is_ai"]]
    elif ai_filter == "ai":
        records = [r for r in records if r["is_ai"]]
    # sorting
    if sort == "downloads":
        records.sort(key=lambda r: -(r["downloads"] or 0))
    elif sort == "views":
        records.sort(key=lambda r: -(r["views"] or 0))
    elif sort == "newest":
        records.sort(key=lambda r: str(r["upload_date"] or ""), reverse=True)
    elif sort == "oldest":
        records.sort(key=lambda r: str(r["upload_date"] or ""))
    elif sort == "gems":  # undiscovered: many views, few downloads
        records.sort(key=lambda r: -((r["views"] or 0) / ((r["downloads"] or 0) + 25)))
    records = records[:limit]
    return jsonify({
        "records": records, "demo": demo, "source": source,
        "kpis": tracker_mod.compute_kpis(records),
        "analytics": tracker_mod.analytics(records),
        "note": ("Demo data — fictional sample records for testing the tab. "
                 "Add your Apify token + an Adobe Stock scraper Actor ID for live results."
                 if demo else
                 "Live results via your Apify token. Numbers depend on the Actor used and are estimates."),
    })


def _expand_one_seed(seed, token):
    """One seed's expansion with per-keyword source attribution (v11).
    Apify related searches first (own token), then Datamuse (free)."""
    dm = expand_keywords([seed], per_seed=10)
    items = [{"w": w, "source": "Datamuse"} for w in dm]
    engine = "builtin (Datamuse, free)"
    apify_info = None
    if token:
        boost = apify_intel.enrich_keyword(seed, token)
        apify_info = boost
        if boost.get("ok"):
            ap = [{"w": w, "source": "Apify related"}
                  for w in boost.get("related_phrases", [])]
            seen = set()
            merged = []
            for it in ap + items:
                if it["w"] not in seen:
                    seen.add(it["w"])
                    merged.append(it)
            items = merged[:60]
            engine = "apify + builtin"
    return {"seed": seed, "suggestions": [i["w"] for i in items],
            "items": items, "engine": engine, "apify": apify_info}


@app.route("/api/keywords/expand", methods=["POST"])
def kw_expand():
    """v11 (Job D, RA-Tracker pattern): results are grouped per seed and
    cached server-side in data/keyword_cache.json — re-searching the same
    seed (+ same sources) returns instantly with cached=true and spends
    NO Apify credit. `force: true` (after Clear Cache) fetches fresh."""
    data = request.get_json(force=True, silent=True) or {}
    seed = (data.get("seed") or "").strip()
    if not seed:
        return jsonify({"error": "Enter a seed keyword."}), 400
    seeds = [s.strip().lower() for s in seed.split(",") if s.strip()][:3]
    token = apify_intel.resolve_token(data.get("apify_token"))
    sources = "apify+datamuse" if token else "datamuse"
    force = bool(data.get("force"))
    results = []
    for s in seeds:
        entry = None if force else keyword_cache.get(s, sources)
        if entry:
            payload = dict(entry["payload"])
            payload["cached"] = True
            payload["cached_at"] = entry["ts"]
            results.append(payload)
            continue
        payload = _expand_one_seed(s, token)
        keyword_cache.put(s, sources, payload)
        results.append({**payload, "cached": False})
    first = results[0]
    return jsonify({"seed": seed, "seeds": seeds, "results": results,
                    "suggestions": first["suggestions"],
                    "items": first["items"], "engine": first["engine"],
                    "cached": first.get("cached", False),
                    "stats": keyword_cache.stats()})


@app.route("/api/keywords/cache-stats", methods=["GET"])
def kw_cache_stats():
    return jsonify(keyword_cache.stats())


@app.route("/api/keywords/cache-clear", methods=["POST"])
def kw_cache_clear():
    return jsonify({"cleared": keyword_cache.clear(),
                    "stats": keyword_cache.stats()})


def _season_match(query):
    """v12 (B.8) — if the scanned query matches an upcoming calendar
    event, return {event, date, days_left, upload_by} for the banner."""
    import re as _re
    if not query:
        return None
    toks = [t for t in _re.split(r"[^a-z]+", query.lower()) if len(t) > 2]
    if not toks:
        return None
    try:
        events = calendar_data.full_year_calendar().get("events", [])
    except Exception:  # noqa: BLE001
        return None
    best = None
    for e in events:
        hay = (str(e.get("event", "")) + " "
               + " ".join(e.get("keywords") or [])).lower()
        if any(t in hay for t in toks):
            if best is None or e["days_until"] < best["days_until"]:
                best = e
    if not best:
        return None
    return {"event": best["event"], "date": best["date"],
            "days_left": best["days_until"], "upload_by": best["upload_by"]}


@app.route("/api/keywords/scan", methods=["POST"])
def kw_scan():
    """v12 (Prompt #5, Part B) — Keyword Research as a stock MARKET
    TRACKER. Same engine as /api/tracker/search (normaliser, KPIs,
    analytics in backend/tracker.py) plus the v12 market extensions
    (D/MO, est. revenue, lifecycle, Keyword Difficulty, winning
    keywords-30, contributor summary) and the 15-minute scan cache
    (backend/market_cache.py): an identical scan repeated within
    15 minutes costs NO Apify call; a failed live scan offers the stale
    cached result explicitly — never silently."""
    data = request.get_json(force=True, silent=True) or {}
    mode = data.get("mode", "keyword")
    query = (data.get("query") or "").strip()
    category = (data.get("category") or "all").strip().lower()
    sort = (data.get("sort") or "relevance").strip()
    ai_filter = (data.get("ai_filter") or "all").strip()
    try:
        limit = min(max(int(data.get("limit", 50)), 10), 200)
    except (TypeError, ValueError):
        limit = 50
    try:
        rate = float(data.get("rate") or 0.85)
        if rate <= 0:
            rate = 0.85
    except (TypeError, ValueError):
        rate = 0.85
    token = apify_intel.resolve_token(data.get("apify_token")
                                      or data.get("token"))
    actor = (data.get("actor") or data.get("actor_id") or "").strip()
    demo = bool(data.get("demo")) or not (token and actor)
    if not query:
        demo = True
    force = bool(data.get("force_fresh"))
    params = {"mode": mode, "query": query, "category": category,
              "ai_filter": ai_filter, "limit": limit, "actor": actor,
              "demo": demo}
    # v14: reject an impossible Actor ID (e.g. a pasted screenshot file
    # name) BEFORE the cache lookup and before any Apify call.
    if actor and not demo:
        actor_err = tracker_mod.actor_id_error(actor)
        if actor_err:
            return jsonify({"error": actor_err,
                            "invalid_actor": True}), 400
    if data.get("use_stale"):
        st = market_cache.get_stale(params)
        if not st:
            return jsonify({"error": "No cached result exists for this "
                                     "scan."}), 404
        payload = dict(st["payload"])
        payload.update({"cached": True, "stale": True,
                        "cache_age_s": st["age_s"]})
        return jsonify(payload)
    if not force:
        hit = market_cache.get(params)
        if hit:
            payload = dict(hit["payload"])
            payload.update({"cached": True, "stale": False,
                            "cache_age_s": hit["age_s"],
                            "cache_stats": market_cache.stats()})
            return jsonify(payload)
    records, source, live = None, None, False
    total_in_stock = None
    if not demo and token and actor and query:
        live = True
        try:
            raw = apify_intel.run_actor_sync(
                token, actor,
                tracker_mod.build_actor_input(mode, query, category, sort,
                                              ai_filter, limit))
            total_in_stock = tracker_mod.extract_total_count(raw)
            records = tracker_mod.normalize_items(raw)
            source = f"apify:{actor}"
            # v13 WRONG-ACTOR GUARD: a Google-search Actor returns
            # related-search phrases (titles, no downloads / asset URLs).
            # That data must NEVER render as market results and never be
            # cached as a successful scan — fail visibly instead.
            guard = tracker_mod.wrong_actor_check(records)
            if not guard["ok"]:
                return jsonify({
                    "error": "⚠ This Actor returned web-search phrases, "
                             "not Adobe Stock asset data. In Manage Apify "
                             "Key, set an Adobe Stock scraper Actor ID.",
                    "wrong_actor": True,
                    "items": guard["total"],
                    "asset_items": guard["assets"]}), 422
        except Exception as exc:  # noqa: BLE001
            # v14: an Apify 404 means the Actor ID itself doesn't
            # exist — say exactly that instead of the raw HTTP error.
            if tracker_mod.is_actor_not_found(exc):
                return jsonify(
                    {"error": tracker_mod.actor_not_found_message(actor),
                     "stale_available": False}), 502
            st = market_cache.get_stale(params)
            resp = {"error": f"Live scan failed: {exc}. Nothing was "
                             "charged inside this app (there are no "
                             "internal credits) — check the token, your "
                             "Apify credit, or the Actor ID.",
                    "stale_available": bool(st)}
            if st:
                resp["stale"] = {
                    "age_s": st["age_s"],
                    "assets": len(st["payload"].get("records", [])),
                    "opportunity_score": st["payload"].get(
                        "kpis", {}).get("opportunity_score")}
            return jsonify(resp), 502
    if records is None:
        records = tracker_mod.load_sample()
        source = "demo"
        demo = True
        params["demo"] = True
        if query and mode == "keyword":
            toks = [t for t in query.lower().split() if len(t) > 2]
            matched = [r for r in records
                       if any(t in (r["title"] or "").lower() or
                              t in " ".join(r["keywords"]) for t in toks)]
            if matched:
                records = matched
    if category != "all":
        records = [r for r in records if r["type"] == category]
    if ai_filter == "human":
        records = [r for r in records if not r["is_ai"]]
    elif ai_filter == "ai":
        records = [r for r in records if r["is_ai"]]
    records = records[:limit]
    enriched = tracker_mod.sort_market(
        tracker_mod.enrich_records(records, rate=rate), sort)
    kpis = tracker_mod.compute_kpis(enriched)
    kpis["avg_dmo"] = tracker_mod.avg_dmo(enriched)
    kpis["difficulty"] = tracker_mod.keyword_difficulty(enriched)
    # v13: Row-1 / Row-2 market summary (Total in Adobe Stock, Average
    # per Asset, Top Performing Asset, Opportunity verdict + advice,
    # numeric KD /100, Est. Market Revenue) — additive keys only.
    summary = tracker_mod.market_summary(enriched, rate=rate,
                                         total_in_stock=total_in_stock)
    kpis.update({
        "total_in_stock": summary["total_in_stock"],
        "average_per_asset": summary["average_per_asset"],
        "top_asset": summary["top_asset"],
        "opportunity_verdict": summary["opportunity_verdict"],
        "opportunity_advice": summary["opportunity_advice"],
        "ai_advice": summary["ai_advice"],
        "est_revenue_total": summary["est_revenue_total"],
        "est_revenue_per_asset": summary["est_revenue_per_asset"],
        "kd": summary["kd"],
    })
    payload = {
        "records": enriched, "demo": demo, "source": source,
        "kpis": kpis, "analytics": tracker_mod.analytics(enriched),
        "winning_keywords": tracker_mod.winning_keywords(enriched, 30),
        "season_event": _season_match(query) if mode == "keyword" else None,
        "rate": rate, "cached": False, "stale": False,
        "params": {"mode": mode, "query": query, "category": category,
                   "ai_filter": ai_filter, "limit": limit},
        "note": ("Demo data — fictional sample records. Add your Apify "
                 "key (Manage Apify Key) for live Adobe Stock data."
                 if demo else
                 "Live results via your own Apify token. All computed "
                 "numbers (Opportunity, Difficulty, D/MO, revenue, "
                 "lifecycle) are estimates/heuristics — see tooltips."),
    }
    if mode == "contributor":
        payload["contributor"] = tracker_mod.contributor_summary(
            enriched, rate=rate)
    market_cache.put(params, payload, apify_call=live)
    payload["cache_stats"] = market_cache.stats()
    return jsonify(payload)


@app.route("/api/keywords/radar", methods=["GET"])
def kw_radar():
    """v13 — Seasonality Radar strip inside Keyword Research: the same
    tracker.seasonality() feed the Adobe Tracker tab uses (no duplicated
    data), top 6 upcoming events, each enriched with concept suggestions
    from calendar_data topics when a matching occasion exists (the
    seasonality ideas are the fallback)."""
    import re
    events = tracker_mod.seasonality()[:6]
    topics_by_token = {}
    try:
        for e in calendar_data.full_year_calendar().get("events", []):
            for tok in re.split(r"[^a-z]+", str(e.get("event", "")).lower()):
                if len(tok) > 3 and tok not in topics_by_token:
                    topics_by_token[tok] = e.get("keywords") or []
    except Exception:  # noqa: BLE001
        topics_by_token = {}
    for ev in events:
        concepts = None
        for tok in re.split(r"[^a-z]+", ev["name"].lower()):
            if len(tok) > 3 and topics_by_token.get(tok):
                concepts = topics_by_token[tok]
                break
        ev["concepts"] = (concepts or ev.get("ideas") or [])[:3]
    return jsonify({"events": events})


@app.route("/api/keywords/asset-prompt", methods=["POST"])
def kw_asset_prompt():
    """v12 (B.4) — reverse-engineered generation prompt for one asset.
    With the user's own AI key: vision analysis of the thumbnail (when
    reachable) via the existing metadata image_to_prompt engine.
    Without a key (or when vision fails): a template prompt from title +
    top keywords, labelled basic — the fallback is always announced."""
    data = request.get_json(force=True, silent=True) or {}
    rec = data.get("record") or {}
    basic = tracker_mod.asset_prompt_basic(rec)
    provider = (data.get("provider") or "").strip().lower()
    key = (data.get("api_key") or "").strip()
    model = (data.get("model") or "").strip() or None
    if provider and key and provider in ai_hub.PROVIDERS:
        thumb = (rec.get("thumbnail_url") or "").strip()
        if not thumb.startswith("http"):
            return jsonify({"prompt": basic, "basic": True,
                            "source": "basic",
                            "note": "This asset has no reachable thumbnail "
                                    "for vision analysis — basic template "
                                    "prompt shown."})
        tmp = None
        try:
            import urllib.request
            tmp = os.path.join(UPLOAD_DIR,
                               f"mkprompt_{uuid.uuid4().hex[:10]}.img")
            req = urllib.request.Request(
                thumb, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as resp, \
                    open(tmp, "wb") as fh:
                fh.write(resp.read(8 * 1024 * 1024))
            out = image_to_prompt(tmp, UPLOAD_DIR, provider=provider,
                                  key=key, model=model)
            if not out.get("basic"):
                return jsonify({"prompt": out["prompt"], "basic": False,
                                "source": "ai",
                                "label": f"AI prompt · {provider} vision"})
            return jsonify({"prompt": basic, "basic": True,
                            "source": "basic",
                            "note": "The AI did not produce a vision prompt "
                                    "for this asset — basic template "
                                    "prompt shown."})
        except Exception as exc:  # noqa: BLE001
            return jsonify({"prompt": basic, "basic": True,
                            "source": "basic",
                            "note": f"AI vision failed ({exc}) — basic "
                                    "template prompt shown."})
        finally:
            if tmp:
                try:
                    os.remove(tmp)
                except OSError:
                    pass
    return jsonify({"prompt": basic, "basic": True, "source": "basic",
                    "label": "Basic prompt (add a free AI key for vision "
                             "analysis)"})


@app.route("/api/subtopics", methods=["POST"])
def subtopics_route():
    """v11 (Job C) — Subtopic Creator: one topic -> EXACTLY 50 subtopics
    (Apify related searches -> Datamuse -> pattern filler), deduped
    against everything already on screen (`exclude`)."""
    data = request.get_json(force=True, silent=True) or {}
    topic = (data.get("topic") or "").strip()
    if not topic:
        return jsonify({"error": "Enter a main topic first."}), 400
    try:
        out = subtopics_mod.generate_subtopics(
            topic, token=data.get("apify_token"),
            exclude=data.get("exclude") or [])
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(out)


# ------------------------------------------------------- phase 3: apify
@app.route("/api/apify/check", methods=["POST"])
def apify_check():
    data = request.get_json(force=True, silent=True) or {}
    return jsonify(apify_intel.check_token(data.get("apify_token")))


@app.route("/api/apify/run", methods=["POST"])
def apify_run():
    """Generic Actor runner: any Actor ID + JSON input from Apify Store."""
    import json as _json
    data = request.get_json(force=True, silent=True) or {}
    token = apify_intel.resolve_token(data.get("apify_token"))
    if not token:
        return jsonify({"error": "Paste your free Apify token first (Console > Settings > API & Integrations)."}), 400
    actor = (data.get("actor") or "").strip()
    if not actor:
        return jsonify({"error": "Enter an Actor ID, e.g. apify/google-search-scraper"}), 400
    actor_input = data.get("input") or {}
    if isinstance(actor_input, str):
        try:
            actor_input = _json.loads(actor_input)
        except Exception:
            return jsonify({"error": "Actor input must be valid JSON."}), 400
    try:
        items = apify_intel.run_actor_sync(token, actor, actor_input)
        return jsonify({"ok": True, "actor": actor, "count": len(items), "items": items[:100]})
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Apify run failed: {exc}"}), 502


@app.route("/api/metadata/csv", methods=["POST"])
def csv_export():
    data = request.get_json(force=True, silent=True) or {}
    rows = data.get("rows") or []
    if not rows:
        return jsonify({"error": "Nothing to export."}), 400
    buf = io.BytesIO(to_csv(rows).encode("utf-8-sig"))
    return send_file(buf, as_attachment=True,
                     download_name=f"metadata_{datetime.now():%Y%m%d_%H%M%S}.csv",
                     mimetype="text/csv")


@app.route("/api/trends")
def trends():
    return jsonify({"today": datetime.now().date().isoformat(),
                    "events": get_calendar()})


@app.route("/api/optimize", methods=["POST"])
def optimize_route():
    """v11 (Job E1): the optimizer now lives in SEO Studio; all limits
    come from MARKETPLACE_RULES via the `marketplace` field."""
    data = request.get_json(force=True, silent=True) or {}
    return jsonify(optimizer_mod.analyze(
        data.get("title", ""), data.get("keywords", ""),
        marketplace=data.get("marketplace", "adobe")))


@app.route("/api/optimize/fix", methods=["POST"])
def optimize_fix():
    """Auto-Fix: all fixes, or only the check ids in `only` (per-check
    buttons). Returns before -> after with every change listed."""
    data = request.get_json(force=True, silent=True) or {}
    only = data.get("only")
    if isinstance(only, str):
        only = [only]
    return jsonify(optimizer_mod.autofix(
        data.get("title", ""), data.get("keywords", ""),
        marketplace=data.get("marketplace", "adobe"), only=only))


@app.route("/api/optimize/suggest", methods=["POST"])
def optimize_suggest():
    """Suggest 3 better titles — AI with the user's SEO BYOK key, else
    one labelled template rewrite. Key arrives per-request, never stored."""
    data = request.get_json(force=True, silent=True) or {}
    return jsonify(optimizer_mod.suggest_titles(
        data.get("title", ""), data.get("keywords", ""),
        marketplace=data.get("marketplace", "adobe"),
        provider=data.get("provider"), key=data.get("api_key"),
        model=data.get("model"), base_url=data.get("base_url")))


@app.route("/download/extension")
def download_extension():
    path = os.path.join(BASE, "static", "stockmeta-helper.zip")
    if not os.path.isfile(path):
        return jsonify({"error": "Extension not built yet."}), 404
    return send_file(path, as_attachment=True,
                     download_name="stockmeta-helper.zip")


# ------------------------------------------------------- phase 2: intel
@app.route("/api/intel/brief", methods=["POST"])
def intel_brief():
    data = request.get_json(force=True, silent=True) or {}
    keyword = (data.get("keyword") or "").strip()
    if not keyword:
        return jsonify({"error": "Enter a keyword."}), 400
    try:
        brief = opportunity_brief(keyword)
        token = apify_intel.resolve_token(data.get("apify_token"))
        if token:
            brief["apify"] = apify_intel.enrich_keyword(keyword, token)
            if brief["apify"].get("ok"):
                extra = [p for p in brief["apify"].get("related_phrases", []) if p not in brief.get("related", [])]
                brief["related"] = (brief.get("related", []) + extra)[:24]
                brief["note"] += " Enhanced with live Google Search data via your Apify token."
        return jsonify(brief)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 500


# ------------------------------------------------------- phase 2: portfolio
@app.route("/api/portfolio", methods=["GET"])
def portfolio_get():
    return jsonify({"assets": portfolio.list_assets(), **portfolio.stats()})


@app.route("/api/portfolio/assets", methods=["POST"])
def portfolio_add():
    data = request.get_json(force=True, silent=True) or {}
    try:
        asset = portfolio.add_asset(data.get("title", ""), data.get("platform", "Adobe Stock"),
                                    data.get("type", "image"), data.get("upload_date"))
        return jsonify(asset)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 400


@app.route("/api/portfolio/assets/<asset_id>", methods=["DELETE"])
def portfolio_del(asset_id):
    portfolio.delete_asset(asset_id)
    return jsonify({"ok": True})


@app.route("/api/portfolio/log", methods=["POST"])
def portfolio_log():
    data = request.get_json(force=True, silent=True) or {}
    try:
        entry = portfolio.log_entry(data.get("asset_id"), data.get("date"),
                                    data.get("downloads", 0), data.get("views", 0),
                                    data.get("earnings", 0.0))
        return jsonify(entry)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 400


@app.route("/api/portfolio/import", methods=["POST"])
def portfolio_import():
    """v11 (Job E2): import a contributor-dashboard CSV (flexible column
    mapping) or bulk-paste lines. Accepts multipart file upload, or JSON
    {csv: "..."} / {paste: "..."}."""
    try:
        if request.files and request.files.get("file") is not None \
                and request.files["file"].filename:
            text = request.files["file"].read().decode("utf-8-sig",
                                                       errors="replace")
            out = portfolio.import_csv(text)
        else:
            data = request.get_json(force=True, silent=True) or {}
            if data.get("csv"):
                out = portfolio.import_csv(data["csv"])
            elif data.get("paste"):
                out = portfolio.import_paste(data["paste"])
            else:
                return jsonify({"error": "Upload a CSV file or paste lines."}), 400
        return jsonify(out)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/portfolio/goals", methods=["GET", "POST"])
def portfolio_goals():
    if request.method == "POST":
        data = request.get_json(force=True, silent=True) or {}
        try:
            g = portfolio.set_goals(data.get("downloads", 0),
                                    data.get("earnings", 0.0))
        except (TypeError, ValueError):
            return jsonify({"error": "Goals must be numbers."}), 400
        return jsonify({"goals": g})
    return jsonify({"goals": portfolio.get_goals()})


@app.route("/api/portfolio/backup", methods=["GET"])
def portfolio_backup():
    buf = io.BytesIO()
    import json as _json
    buf.write(_json.dumps(portfolio.export_backup(), indent=1).encode("utf-8"))
    buf.seek(0)
    return send_file(buf, as_attachment=True,
                     download_name=f"portfolio_backup_{datetime.now():%Y%m%d}.json",
                     mimetype="application/json")


@app.route("/api/portfolio/restore", methods=["POST"])
def portfolio_restore():
    data = request.get_json(force=True, silent=True) or {}
    try:
        return jsonify(portfolio.import_backup(data))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


# ------------------------------------------------------- phase 2: jobs
def _save_upload(f, allowed, what):
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in allowed:
        raise ValueError(f"Unsupported {what} type '{ext}'.")
    job_id = uuid.uuid4().hex[:12]
    src = os.path.join(UPLOAD_DIR, f"{job_id}_{secure_filename(f.filename)}")
    f.save(src)
    return job_id, src


@app.route("/api/jobs/svg-video", methods=["POST"])
def job_svg_video():
    gate = _usage_gate()
    if gate:
        return gate
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "No SVG uploaded."}), 400
    try:
        job_id, src = _save_upload(f, {".svg"}, "SVG")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    stem = os.path.splitext(secure_filename(f.filename))[0]
    dst = os.path.join(OUTPUT_DIR, f"{job_id}_{stem}_clip.mp4")
    try:
        duration = min(max(float(request.form.get("duration", 10)), 3), 60)
    except ValueError:
        duration = 10
    zoom = request.form.get("zoom", "in")
    params = {"duration": duration,
              "fps": int(request.form.get("fps", 30)),
              "zoom": zoom if zoom in ("in", "out", "static") else "in",
              "bg": (request.form.get("bg") or "#ffffff").strip() or "#ffffff"}
    return jsonify(_start_job("svg-video", src, dst, params, f.filename))


# ------------------------------------------------------- phase 5: AI image-to-video + promo
@app.route("/api/jobs/ai-video", methods=["POST"])
def job_ai_video():
    gate = _usage_gate()
    if gate:
        return gate
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "Upload one image."}), 400
    try:
        job_id, src = _save_upload(f, IMG_EXTS | {".svg"}, "image")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    dst = os.path.join(OUTPUT_DIR, f"{job_id}_aivideo.mp4")
    try:
        duration = min(max(float(request.form.get("duration", 5)), 2), 15)
    except ValueError:
        duration = 5
    params = {"engine": request.form.get("engine", "local"),
              "token": (request.form.get("token") or "").strip(),
              "model": (request.form.get("model") or "").strip(),
              "duration": duration, "fps": int(request.form.get("fps", 24) or 24),
              "ratio": request.form.get("ratio", "16:9"),
              "move": request.form.get("move", "push-in")}
    return jsonify(_start_job("ai-video", src, dst, params, f.filename))


@app.route("/api/jobs/promo", methods=["POST"])
def job_promo():
    gate = _usage_gate()
    if gate:
        return gate
    import json as _json

    def _jf(name, default=None):
        raw = request.form.get(name)
        if raw is None or raw == "":
            return default
        try:
            val = _json.loads(raw)
            return val
        except Exception:  # noqa: BLE001
            return default

    def _fb(name, default=False):
        return request.form.get(name, "1" if default else "0") == "1"

    files = [f for f in request.files.getlist("files") if f and f.filename][:12]
    template = request.form.get("template", "sale-hero")
    if not files and template not in ("testimonial", "event-sale", "audiogram"):
        return jsonify({"error": "Upload at least one product photo."}), 400
    job_id = uuid.uuid4().hex[:12]
    paths = []
    for i, f in enumerate(files):
        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in IMG_EXTS:
            return jsonify({"error": f"Unsupported type '{ext}'"}), 400
        src = os.path.join(UPLOAD_DIR, f"{job_id}_p{i}_{secure_filename(f.filename)}")
        f.save(src)
        paths.append(src)
    try:
        products = _json.loads(request.form.get("products") or "[]")
        if not isinstance(products, list):
            products = []
    except Exception:  # noqa: BLE001
        products = []
    fmt = request.form.get("format", "mp4")
    dst = os.path.join(OUTPUT_DIR, f"{job_id}_promo." + ("webm" if fmt == "webm" else "mp4"))
    try:
        per_slide = min(max(float(request.form.get("per_slide", 3.5)), 0.8), 30)
    except ValueError:
        per_slide = 3.5
    # ---- optional extra uploads: logo / badge image / screen recording / voice
    def _save_extra(field, exts, tag):
        f = request.files.get(field)
        if f and f.filename:
            ext = os.path.splitext(f.filename)[1].lower()
            if ext in exts:
                p = os.path.join(UPLOAD_DIR, f"{job_id}_{tag}{ext}")
                f.save(p)
                return p
        return None

    logo_path = _save_extra("logo", IMG_EXTS, "logo")
    badge_path = _save_extra("badge_img", IMG_EXTS, "badge")
    screen_video = _save_extra("screen_video", {".mp4", ".mov", ".webm"}, "screen")
    voice_file = _save_extra("voice_file", {".mp3", ".wav", ".m4a", ".ogg", ".aac"}, "voice")
    brand_kit = _jf("brand_kit") or None
    if brand_kit and logo_path:
        brand_kit["logo_path"] = logo_path
    # ---- music resolution: upload (legacy) / built-in bed / jingle file
    music_path = None
    bed = (request.form.get("music_bed") or "").strip()
    beds_dir = os.path.join(BASE, "assets", "music")
    if bed and os.path.isfile(os.path.join(beds_dir, bed + ".mp3")):
        music_path = os.path.join(beds_dir, bed + ".mp3")
    jingle_name = os.path.basename(request.form.get("music_file") or "")
    if jingle_name and os.path.isfile(os.path.join(OUTPUT_DIR, jingle_name)):
        music_path = os.path.join(OUTPUT_DIR, jingle_name)
    voice_spec = None
    vmode = request.form.get("voice_mode", "none")
    if vmode in ("edge", "openai"):
        voice_spec = {"engine": vmode,
                      "voice": request.form.get("voice_name", "en-US-AvaNeural"),
                      "rate": int(request.form.get("voice_rate", 0) or 0),
                      "pitch": int(request.form.get("voice_pitch", 0) or 0),
                      "base_url": (request.form.get("tts_base_url") or "").strip(),
                      "model": (request.form.get("tts_model") or "").strip(),
                      "api" + "_key": (request.form.get("tts_key") or "").strip()}
    scenes = _jf("scenes")
    versions = _jf("versions")
    if versions:
        versions = [r for r in versions if r in ("16:9", "9:16", "1:1", "4:5")][:4] or None
    v9 = {"scenes": scenes, "quality": request.form.get("quality", "1080p"),
          "text_style": request.form.get("text_style", "classic"),
          "font_role": request.form.get("font_role", "display"),
          "headline_scale": float(request.form.get("headline_scale", 1.0) or 1.0),
          "text_color": (request.form.get("text_color") or "").strip() or None,
          "highlight_color": (request.form.get("highlight_color") or "").strip() or None,
          "brand_kit": brand_kit,
          "outro": (request.form.get("outro") or "").strip() or None,
          "outro_seconds": float(request.form.get("outro_seconds", 2.5) or 2.5),
          "voice_track": voice_file, "voice_spec": voice_spec,
          "music_path": music_path,
          "captions": _fb("captions"), "caption_style": request.form.get("caption_style", "clean-outline"),
          "caption_pos": request.form.get("caption_pos", "bottom"),
          "caption_size": float(request.form.get("caption_size", 1.0) or 1.0),
          "caption_source": request.form.get("caption_source", "voiceover"),
          "make_gif": _fb("make_gif"), "gif_width": int(request.form.get("gif_width", 480) or 480),
          "make_poster": _fb("make_poster"), "fmt": fmt,
          "device": _jf("device"), "countdown_seconds": float(request.form.get("countdown_seconds", 600) or 600),
          "features": _jf("features"), "labels": _jf("labels"), "tap": _jf("tap"),
          "badge_image": badge_path, "screen_video": screen_video}
    params = {"template": template,
              "headline": (request.form.get("headline") or "")[:120],
              "cta": (request.form.get("cta") or "")[:40],
              "theme": request.form.get("theme", "crimson"),
              "ratio": request.form.get("ratio", "16:9"),
              "per_slide": per_slide, "fps": int(request.form.get("fps", 30) or 30),
              "badge_text": (request.form.get("badge_text") or "SALE")[:12],
              "show_badge": _fb("show_badge", True),
              "brand_text": (request.form.get("brand_text") or "")[:40],
              "anim": request.form.get("anim", "zoom-in"),
              "band": request.form.get("band", "bottom"),
              "end_card": _fb("end_card"),
              "audio_path": None, "products": products,
              "v9": v9, "versions": versions}
    af = request.files.get("audio")
    if af and af.filename:
        aext = os.path.splitext(af.filename)[1].lower()
        if aext in {".mp3", ".wav", ".m4a", ".ogg", ".aac"}:
            params["audio_path"] = os.path.join(UPLOAD_DIR, f"{job_id}_paudio{aext}")
            af.save(params["audio_path"])
    return jsonify(_start_job("promo", paths, dst, params, f"{len(paths)} product(s)"))


# ------------------------------------------------------- v9 promo extras
@app.route("/api/promo/templates")
def promo_templates():
    beds = []
    beds_dir = os.path.join(BASE, "assets", "music")
    if os.path.isdir(beds_dir):
        beds = sorted(f[:-4] for f in os.listdir(beds_dir) if f.endswith(".mp3"))
    return jsonify({"templates": PROMO_TEMPLATES,
                    "text_styles": ["classic", "pop-out", "ribbon", "highlight",
                                    "fade-up", "slide-in", "backdrop",
                                    "center-stage", "typewriter"],
                    "caption_styles": list(promo_audio.CAPTION_STYLES),
                    "voices": promo_audio.EDGE_VOICES,
                    "edge_tts_available": promo_audio.edge_tts_available(),
                    "music_beds": beds})


@app.route("/api/promo/preview", methods=["POST"])
def promo_preview():
    data = request.get_json(force=True, silent=True) or {}
    template = data.get("template", "sale-hero")
    if template not in PROMO_TEMPLATES:
        return jsonify({"error": f"Unknown template '{template}'."}), 400
    ratio = data.get("ratio") or PROMO_TEMPLATES[template]["ratios"][0]
    name = f"promo_preview_{template}_{ratio.replace(':', 'x')}.mp4"
    cache_path = os.path.join(OUTPUT_DIR, name)
    if os.path.isfile(cache_path) and os.path.getsize(cache_path) > 4000:
        return jsonify({"ready": True, "url": f"/api/promo-file/{name}",
                        "cached": True})
    ph_dir = os.path.join(UPLOAD_DIR, "promo_placeholders")
    paths = promo_make_placeholders(ph_dir, 3)
    from backend.promo import _PLACEHOLDER_PRODUCTS
    v9 = {"quality": "preview", "device": {"kind": "phone", "preset": "float"},
          "countdown_seconds": 300}
    params = {"template": template, "headline": "Mega Sale — Up To 50% Off",
              "cta": "Shop Now", "theme": "crimson", "ratio": ratio,
              "per_slide": 1.6, "fps": 24, "badge_text": "SALE",
              "show_badge": True, "brand_text": "Your Brand", "anim": "zoom-in",
              "band": "bottom", "end_card": False, "audio_path": None,
              "products": _PLACEHOLDER_PRODUCTS, "v9": v9, "versions": None}
    out = _start_job("promo", paths, cache_path, params, f"preview {template}")
    out["url"] = f"/api/promo-file/{name}"
    return jsonify(out)


@app.route("/api/promo/script", methods=["POST"])
def promo_script_gen():
    gate = _usage_gate()
    if gate:
        return gate
    data = request.get_json(force=True, silent=True) or {}
    brief = {"business": data.get("business", ""), "product": data.get("product", ""),
             "audience": data.get("audience", ""), "offer": data.get("offer", ""),
             "tone": data.get("tone", "Exciting"), "language": data.get("language", "English"),
             "target_seconds": int(data.get("target_seconds", 30) or 30),
             "platform": data.get("platform", "")}
    try:
        out = promo_script.generate_script(
            brief, provider=data.get("provider") or None,
            key=(data.get("key") or "").strip() or None,
            model=data.get("model") or None, base_url=data.get("base_url") or None)
        return jsonify(out)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Script AI failed: {exc}"}), 502


@app.route("/api/promo/split-script", methods=["POST"])
def promo_script_split():
    gate = _usage_gate()
    if gate:
        return gate
    data = request.get_json(force=True, silent=True) or {}
    try:
        out = promo_script.split_script(
            data.get("text", ""), int(data.get("target_seconds", 30) or 30),
            provider=data.get("provider") or None,
            key=(data.get("key") or "").strip() or None,
            model=data.get("model") or None, base_url=data.get("base_url") or None)
        return jsonify(out)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Split failed: {exc}"}), 502


@app.route("/api/promo/slogans", methods=["POST"])
def promo_slogans():
    data = request.get_json(force=True, silent=True) or {}
    brief = {"business": data.get("business", ""), "product": data.get("product", ""),
             "offer": data.get("offer", "")}
    try:
        return jsonify(promo_script.slogan_ideas(
            brief, provider=data.get("provider") or None,
            key=(data.get("key") or "").strip() or None,
            model=data.get("model") or None, base_url=data.get("base_url") or None))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Slogan AI failed: {exc}"}), 502


@app.route("/api/promo/voice-preview", methods=["POST"])
def promo_voice_preview():
    gate = _usage_gate()
    if gate:
        return gate
    text = (request.form.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Write a line to preview first."}), 400
    engine = request.form.get("engine", "edge")
    name = f"voice_preview_{uuid.uuid4().hex[:10]}.mp3"
    out = os.path.join(OUTPUT_DIR, name)
    kw = {"voice": request.form.get("voice_name", "en-US-AvaNeural"),
          "rate_pct": int(request.form.get("voice_rate", 0) or 0),
          "pitch_hz": int(request.form.get("voice_pitch", 0) or 0),
          "base_url": (request.form.get("tts_base_url") or "").strip() or None,
          "model": (request.form.get("tts_model") or "").strip() or None}
    kw["api" + "_key"] = (request.form.get("tts_key") or "").strip() or None
    try:
        promo_audio.synth_voice(engine, text[:300], out, **kw)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 400
    return jsonify({"url": f"/api/promo-file/{name}",
                    "seconds": round(promo_audio.probe_duration(out), 2)})


@app.route("/api/promo/jingle", methods=["POST"])
def promo_jingle():
    gate = _usage_gate()
    if gate:
        return gate
    line = (request.form.get("line") or "").strip()
    if not line:
        return jsonify({"error": "Write the jingle line first."}), 400
    bed_path = None
    bed = (request.form.get("bed") or "").strip()
    beds_dir = os.path.join(BASE, "assets", "music")
    if bed and os.path.isfile(os.path.join(beds_dir, bed + ".mp3")):
        bed_path = os.path.join(beds_dir, bed + ".mp3")
    bf = request.files.get("bed_file")
    if bf and bf.filename:
        ext = os.path.splitext(bf.filename)[1].lower()
        if ext in {".mp3", ".wav", ".m4a", ".ogg"}:
            bed_path = os.path.join(UPLOAD_DIR, f"jingle_bed_{uuid.uuid4().hex[:8]}{ext}")
            bf.save(bed_path)
    kw = {"engine": request.form.get("engine", "edge"),
          "voice": request.form.get("voice_name", "en-US-AvaNeural"),
          "rate_pct": int(request.form.get("voice_rate", 0) or 0),
          "pitch_hz": int(request.form.get("voice_pitch", 0) or 0),
          "base_url": (request.form.get("tts_base_url") or "").strip() or None,
          "model": (request.form.get("tts_model") or "").strip() or None,
          "bed_path": bed_path,
          "intro": request.form.get("intro", "chime"),
          "outro": request.form.get("outro", "chime"),
          "preset": request.form.get("preset", "business")}
    kw["api" + "_key"] = (request.form.get("tts_key") or "").strip() or None
    try:
        out = promo_audio.make_jingle(line, OUTPUT_DIR, **kw)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 400
    return jsonify({"mp3": os.path.basename(out["mp3"]),
                    "wav": os.path.basename(out["wav"]),
                    "url_mp3": f"/api/promo-file/{os.path.basename(out['mp3'])}",
                    "url_wav": f"/api/promo-file/{os.path.basename(out['wav'])}",
                    "duration": out["duration"], "voice_cached": out["voice_cached"],
                    "voice_seconds": out["voice_seconds"], "mixer": out["mixer"]})


@app.route("/api/promo/stock-search", methods=["POST"])
def promo_stock_search():
    data = request.get_json(force=True, silent=True) or {}
    try:
        results = stock_media.search(data.get("provider", "pexels"),
                                     (data.get("key") or "").strip(),
                                     data.get("query", ""),
                                     data.get("media", "photo"))
        return jsonify({"results": results})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Stock search failed: {exc}"}), 502


@app.route("/api/promo/stock-download", methods=["POST"])
def promo_stock_download():
    data = request.get_json(force=True, silent=True) or {}
    url = data.get("url", "")
    ext = ".mp4" if data.get("type") == "video" else ".jpg"
    name = f"stock_{uuid.uuid4().hex[:10]}{ext}"
    dst = os.path.join(UPLOAD_DIR, name)
    try:
        stock_media.download(url, dst)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 400
    return jsonify({"name": name, "url": f"/api/promo-upload/{name}"})


@app.route("/api/promo-upload/<name>")
def promo_upload_file(name):
    name = os.path.basename(name)
    path = os.path.join(UPLOAD_DIR, name)
    if not os.path.isfile(path):
        return jsonify({"error": "Not found."}), 404
    return send_file(path)


@app.route("/api/promo-file/<name>")
def promo_file(name):
    name = os.path.basename(name)
    path = os.path.join(OUTPUT_DIR, name)
    if not os.path.isfile(path):
        return jsonify({"error": "Not ready yet."}), 404
    return send_file(path, as_attachment=False)


@app.route("/api/download/<job_id>/<variant>")
def job_download_variant(job_id, variant):
    with jobs_lock:
        job = jobs.get(job_id)
        if job is None or job["state"] != "done":
            return jsonify({"error": "Result not ready."}), 404
        extras = job.get("extras") or {}
    path = extras.get(variant)
    if not path or not os.path.isfile(path):
        return jsonify({"error": "No such extra file for this job."}), 404
    return send_file(path, as_attachment=True, download_name=os.path.basename(path))



# ------------------------------------------------------- phase 4: AI creativity hub
@app.route("/api/ai/providers")
def ai_providers():
    return jsonify({"providers": {k: {"label": v["label"], "default_model": v["default_model"],
                                      "get_key": v["get_key"]} for k, v in ai_hub.PROVIDERS.items()},
                    "tasks": list(ai_hub.TASKS.keys())})


@app.route("/api/ai/test", methods=["POST"])
def ai_test():
    data = request.get_json(force=True, silent=True) or {}
    return jsonify(ai_hub.test_key(data.get("provider", "gemini"), data.get("key"),
                                   model=data.get("model") or None,
                                   base_url=data.get("base_url") or None))


@app.route("/api/ai/create", methods=["POST"])
def ai_create():
    data = request.get_json(force=True, silent=True) or {}
    try:
        out = ai_hub.generate(data.get("provider", "gemini"), data.get("key"),
                              data.get("task", "stock-brief"), data.get("topic", ""),
                              model=data.get("model") or None,
                              language=data.get("language", "English"),
                              base_url=data.get("base_url") or None)
        return jsonify(out)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"AI provider failed: {exc}"}), 502


@app.route("/api/ai/analyze", methods=["POST"])
def ai_analyze():
    """v5 AI brain: analyse a reference image/screenshot -> motion design."""
    imgf = request.files.get("image")
    if not imgf or not imgf.filename:
        return jsonify({"error": "Choose a reference image or screenshot first."}), 400
    ext = os.path.splitext(imgf.filename)[1].lower()
    if ext not in IMG_EXTS:
        return jsonify({"error": "Reference must be JPG/PNG/WEBP."}), 400
    tmp = os.path.join(UPLOAD_DIR, f"ref_{uuid.uuid4().hex[:10]}{ext}")
    imgf.save(tmp)
    try:
        out = ai_hub.analyze_reference(request.form.get("provider", "gemini"),
                                       request.form.get("key"),
                                       request.form.get("model") or None, tmp)
        return jsonify(out)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"AI analysis failed: {exc}"}), 502
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


# ------------------------------------------------------- phase 4: motion graphics
@app.route("/api/mgfx/catalog")
def mgfx_catalog():
    return jsonify({"catalog": MGFX_CATALOG,
                    "themes": ["gold", "teal", "violet", "crimson", "ocean", "rose"]})


@app.route("/api/jobs/mgfx", methods=["POST"])
def job_mgfx():
    gate = _usage_gate()
    if gate:
        return gate
    kind = (request.form.get("kind") or "bg-gradient").strip()
    if kind not in MGFX_CATALOG:
        return jsonify({"error": f"Unknown motion graphic '{kind}'."}), 400
    job_id = uuid.uuid4().hex[:12]
    image_path = logo_path = None
    imgf = request.files.get("image")
    if imgf and imgf.filename:
        ext = os.path.splitext(imgf.filename)[1].lower()
        if ext in IMG_EXTS or ext == ".svg":
            image_path = os.path.join(UPLOAD_DIR, f"{job_id}_bg{ext}")
            imgf.save(image_path)
    logof = request.files.get("logo")
    if logof and logof.filename:
        ext = os.path.splitext(logof.filename)[1].lower()
        if ext in IMG_EXTS:
            logo_path = os.path.join(UPLOAD_DIR, f"{job_id}_logo{ext}")
            logof.save(logo_path)
    _fmt = "mov" if request.form.get("format") == "mov" else "mp4"
    _preview = request.form.get("preview") == "1"
    dst = os.path.join(OUTPUT_DIR, f"{job_id}_mgfx{'-preview' if _preview else ''}.{_fmt}")
    try:
        duration = min(max(float(request.form.get("duration", 5)), 2), 20)
    except ValueError:
        duration = 5
    params = {"kind": kind, "theme": request.form.get("theme", "gold"),
              "text": (request.form.get("text") or "")[:90],
              "subtext": (request.form.get("subtext") or "")[:120],
              "ratio": request.form.get("ratio", "16:9"), "duration": duration,
              "fps": int(request.form.get("fps", 30) or 30),
              "quality": request.form.get("quality", "HD"),
              "speed": min(max(float(request.form.get("speed", 1.0) or 1.0), 0.25), 2.0),
              "intensity": min(max(float(request.form.get("intensity", 100) or 100), 10), 100) / 100.0,
              "color_primary": request.form.get("color_primary") or None,
              "color_accent": request.form.get("color_accent") or None,
              "color_bg": request.form.get("color_bg") or None,
              "format": _fmt, "preview": _preview,
              "image_path": image_path, "logo_path": logo_path}
    return jsonify(_start_job("mgfx", image_path or "", dst, params, MGFX_CATALOG[kind]["label"]))


# ------------------------------------------------------- phase 3: motion studio
@app.route("/api/motion/templates")
def motion_templates():
    return jsonify({"templates": MOTION_TEMPLATES})


@app.route("/api/jobs/motion", methods=["POST"])
def job_motion():
    gate = _usage_gate()
    if gate:
        return gate
    files = request.files.getlist("files") or ([request.files["file"]] if "file" in request.files else [])
    files = [f for f in files if f and f.filename][:10]
    if not files:
        return jsonify({"error": "Upload at least one image (JPG/PNG/WEBP/SVG)."}), 400
    job_id = uuid.uuid4().hex[:12]
    paths = []
    for i, f in enumerate(files):
        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in IMG_EXTS and ext != ".svg":
            return jsonify({"error": f"Unsupported type '{ext}' for {f.filename}"}), 400
        src = os.path.join(UPLOAD_DIR, f"{job_id}_m{i}_{secure_filename(f.filename)}")
        f.save(src); paths.append(src)
    audio_path = None
    af = request.files.get("audio")
    if af and af.filename:
        aext = os.path.splitext(af.filename)[1].lower()
        if aext in {".mp3", ".wav", ".m4a", ".ogg", ".aac"}:
            audio_path = os.path.join(UPLOAD_DIR, f"{job_id}_audio{aext}")
            af.save(audio_path)
    dst = os.path.join(OUTPUT_DIR, f"{job_id}_motion.mp4")
    def _f(name, default, lo, hi):
        try:
            return min(max(float(request.form.get(name, default)), lo), hi)
        except ValueError:
            return default
    params = {
        "template": request.form.get("template", "stock-broll"),
        "effect": request.form.get("effect") or None,
        "transition": request.form.get("transition") or None,
        "grade": request.form.get("grade") or None,
        "ratio": request.form.get("ratio", "16:9"),
        "per_slide": _f("per_slide", 4, 1.5, 15),
        "fps": int(request.form.get("fps", 30) or 30),
        "title": (request.form.get("title") or "")[:80],
        "subtitle": (request.form.get("subtitle") or "")[:110],
        "audio_path": audio_path,
    }
    # src is a LIST for motion jobs (handled in _run_job)
    return jsonify(_start_job("motion", paths, dst, params, f"{len(paths)} image(s)"))


@app.route("/api/jobs/<job_id>")
def job_status(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
        if job is None:
            return jsonify({"error": "Unknown job."}), 404
        out = {k: job[k] for k in ("id", "kind", "filename", "state",
                                  "progress", "meta", "error") if k in job}
    return jsonify(out)


@app.route("/api/download/<job_id>")
def job_download(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
        if job is None or job["state"] != "done":
            return jsonify({"error": "Result not ready."}), 404
        dst, name = job["dst"], job["download_name"]
    return send_file(dst, as_attachment=True, download_name=name)


# ------------------------------------------------------- v8: auth routes
@app.route("/api/auth/state")
def auth_state():
    return jsonify({"setup_needed": auth_store.setup_needed(),
                    "user": _session_user(),
                    "store_file": os.path.basename(AUTH_FILE)})


@app.route("/api/auth/setup-admin", methods=["POST"])
def auth_setup_admin():
    data = request.get_json(force=True, silent=True) or {}
    user, err = auth_store.create_admin(data.get("email"),
                                        data.get("password"))
    if err:
        return jsonify({"error": err}), 400
    session["user_email"] = user["email"]
    return jsonify({"ok": True, "user": user})


@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    data = request.get_json(force=True, silent=True) or {}
    user, err = auth_store.register(data.get("email"), data.get("password"))
    if err:
        return jsonify({"error": err}), 400
    session["user_email"] = user["email"]
    return jsonify({"ok": True, "user": user})


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json(force=True, silent=True) or {}
    user, err = auth_store.authenticate(data.get("email"),
                                        data.get("password"))
    if err:
        return jsonify({"error": err}), 401
    session["user_email"] = user["email"]
    return jsonify({"ok": True, "user": user})


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    session.pop("user_email", None)
    return jsonify({"ok": True})


# ------------------------------------------------------- v8: license
@app.route("/api/license/activate", methods=["POST"])
def license_activate():
    data = request.get_json(force=True, silent=True) or {}
    email = (data.get("email") or session.get("user_email") or "").strip()
    ok, msg = auth_store.activate_key(email, data.get("key"))
    if not ok:
        return jsonify({"error": msg}), 400
    return jsonify({"ok": True, "message": msg, "user": _session_user()})


@app.route("/api/license/status")
def license_status_route():
    user = _session_user()
    return jsonify({"user": user,
                    "setup_needed": auth_store.setup_needed()})


# ------------------------------------------------------- v8: admin (guarded)
def _require_admin():
    user = _session_user()
    if not user or not user.get("is_admin"):
        return jsonify({"error": "Admin access only. Sign in with the "
                                 "admin account first."}), 403
    return None


@app.route("/api/admin/keys", methods=["GET"])
def admin_keys_list():
    guard = _require_admin()
    if guard:
        return guard
    return jsonify({"keys": auth_store.list_keys()})


@app.route("/api/admin/keys", methods=["POST"])
def admin_keys_generate():
    guard = _require_admin()
    if guard:
        return guard
    data = request.get_json(force=True, silent=True) or {}
    try:
        period = int(data.get("period_days") or
                     auth_store.get_policy()["default_license_period"])
    except (TypeError, ValueError):
        return jsonify({"error": "Access period must be a number of days."}), 400
    limit = data.get("daily_limit", 50)
    if isinstance(limit, str) and limit.strip().lower() in ("", "unlimited",
                                                            "none"):
        limit = None
    else:
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            return jsonify({"error": "Daily limit must be a number or Unlimited."}), 400
    rec, err = auth_store.generate_key(data.get("email"), period, limit,
                                       note=data.get("note") or "")
    if err:
        return jsonify({"error": err}), 400
    return jsonify({"ok": True, "key": rec})


@app.route("/api/admin/keys/revoke", methods=["POST"])
def admin_keys_revoke():
    guard = _require_admin()
    if guard:
        return guard
    data = request.get_json(force=True, silent=True) or {}
    ok, msg = auth_store.revoke_key(data.get("key"))
    if not ok:
        return jsonify({"error": msg}), 400
    return jsonify({"ok": True, "message": msg})


@app.route("/api/admin/users", methods=["GET"])
def admin_users_list():
    guard = _require_admin()
    if guard:
        return guard
    return jsonify({"users": auth_store.list_users()})


@app.route("/api/admin/users/toggle", methods=["POST"])
def admin_users_toggle():
    guard = _require_admin()
    if guard:
        return guard
    data = request.get_json(force=True, silent=True) or {}
    if not auth_store.toggle_user(data.get("email"),
                                  bool(data.get("active", True))):
        return jsonify({"error": "User not found (or it is the admin "
                                 "account, which cannot be deactivated)."}), 400
    return jsonify({"ok": True, "users": auth_store.list_users()})


@app.route("/api/admin/policy", methods=["GET", "POST"])
def admin_policy():
    guard = _require_admin()
    if guard:
        return guard
    if request.method == "POST":
        data = request.get_json(force=True, silent=True) or {}
        return jsonify({"ok": True, "policy": auth_store.set_policy(data)})
    return jsonify({"policy": auth_store.get_policy()})


@app.route("/api/admin/backup", methods=["GET"])
def admin_backup():
    guard = _require_admin()
    if guard:
        return guard
    buf = io.BytesIO()
    import json as _json
    buf.write(_json.dumps(auth_store.export_store(), indent=1).encode())
    buf.seek(0)
    return send_file(buf, as_attachment=True,
                     download_name=f"toolkit_auth_backup_"
                                   f"{datetime.now():%Y%m%d_%H%M%S}.json",
                     mimetype="application/json")


@app.route("/api/admin/backup/import", methods=["POST"])
def admin_backup_import():
    guard = _require_admin()
    if guard:
        return guard
    import json as _json
    f = request.files.get("file")
    if not f:
        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({"error": "Upload a backup JSON file."}), 400
        payload = data
    else:
        try:
            payload = _json.loads(f.read().decode("utf-8"))
        except Exception:
            return jsonify({"error": "That file is not valid JSON."}), 400
    ok, msg = auth_store.import_store(payload)
    if not ok:
        return jsonify({"error": msg}), 400
    return jsonify({"ok": True, "message": msg})


# ------------------------------------------------------- v8: system info
@app.route("/api/system/info")
def system_info():
    ffmpeg = False
    version = ""
    try:
        out = subprocess.run(["ffmpeg", "-version"], capture_output=True,
                             text=True, timeout=10)
        ffmpeg = out.returncode == 0
        version = (out.stdout or "").splitlines()[0] if out.stdout else ""
    except Exception:  # noqa: BLE001
        ffmpeg = False
    return jsonify({"ffmpeg_available": ffmpeg, "ffmpeg_version": version,
                    "python_version": sys.version.split()[0],
                    "platform": sys.platform})


# ------------------------------------------- v8: motion from image + prompt
@app.route("/api/mgfx/interpret", methods=["POST"])
def mgfx_interpret():
    """Interpret a prompt into a whitelisted plan WITHOUT rendering.
    v10: also accepts multipart form data with the image attached, so the
    AI interpreter actually SEES the image (subject + dominant colours)
    when a key is supplied."""
    image_path = None
    if request.files and request.files.get("image") is not None \
            and request.files["image"].filename:
        imgf = request.files["image"]
        ext = os.path.splitext(imgf.filename)[1].lower()
        if ext not in IMG_EXTS and ext != ".svg":
            return jsonify({"error": f"Unsupported image type '{ext}'."}), 400
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        image_path = os.path.join(
            UPLOAD_DIR, f"interpret_{uuid.uuid4().hex[:10]}{ext}")
        imgf.save(image_path)
        prompt = (request.form.get("prompt") or "").strip()
        provider = (request.form.get("provider") or "").strip() or None
        api_key = (request.form.get("api_key") or "").strip() or None
        model = (request.form.get("model") or "").strip() or None
        base_url = (request.form.get("base_url") or "").strip() or None
        has_image = True
    else:
        data = request.get_json(force=True, silent=True) or {}
        prompt = (data.get("prompt") or "").strip()
        provider = data.get("provider") or None
        api_key = data.get("api_key") or None
        model = data.get("model") or None
        base_url = data.get("base_url") or None
        has_image = bool(data.get("has_image", True))
    if not prompt:
        return jsonify({"error": "Write a motion prompt first."}), 400
    plan = prompt_motion.interpret(
        prompt, provider=provider, api_key=api_key,
        image_path=image_path, has_image=has_image,
        model=model, base_url=base_url)
    return jsonify({"plan": plan})


@app.route("/api/jobs/mgfx-prompt", methods=["POST"])
def job_mgfx_prompt():
    gate = _usage_gate()
    if gate:
        return gate
    prompt = (request.form.get("prompt") or "").strip()
    plan_raw = (request.form.get("plan") or "").strip()
    use_builtin = (request.form.get("use_builtin") or "") == "1"
    if not prompt and not plan_raw:
        return jsonify({"error": "Write a motion prompt first, e.g. "
                                 "'slow zoom in with golden particles "
                                 "orbiting the logo'."}), 400
    job_id = uuid.uuid4().hex[:12]
    image_path = None
    imgf = request.files.get("image")
    if imgf and imgf.filename:
        ext = os.path.splitext(imgf.filename)[1].lower()
        if ext not in IMG_EXTS and ext != ".svg":
            return jsonify({"error": f"Unsupported image type '{ext}'."}), 400
        image_path = os.path.join(UPLOAD_DIR, f"{job_id}_pp{ext}")
        imgf.save(image_path)
    if plan_raw:
        # v11: the user reviewed/edited the AI Motion Plan card — the
        # FINAL card values are what renders (whitelist-validated).
        import json as _json
        try:
            plan = prompt_motion.validate_plan_fields(
                _json.loads(plan_raw), has_image=bool(image_path))
        except (ValueError, TypeError) as exc:
            return jsonify({"error": f"Invalid motion plan: {exc}"}), 400
    elif use_builtin:
        # the user explicitly chose the built-in interpreter (after an
        # AI failure, or no key) — labelled as such, never a surprise
        plan = prompt_motion.interpret_prompt(prompt,
                                              has_image=bool(image_path))
    else:
        plan = prompt_motion.interpret(
            prompt,
            provider=(request.form.get("provider") or "").strip() or None,
            api_key=(request.form.get("api_key") or "").strip() or None,
            image_path=image_path, has_image=bool(image_path),
            model=(request.form.get("model") or "").strip() or None,
            base_url=(request.form.get("base_url") or "").strip() or None)
        if plan.get("ai_note"):
            # v11 Job B rule: saved key but AI failed -> STOP, show the
            # error, offer Retry AI / Use built-in. NO silent fallback,
            # NO render started.
            return jsonify({
                "error": plan["ai_note"] +
                         " Nothing was rendered. Retry the AI, or choose "
                         "'Use built-in interpreter instead'.",
                "ai_failed": True, "plan": plan}), 409
    _fmt = "mov" if request.form.get("format") == "mov" else "mp4"
    dst = os.path.join(OUTPUT_DIR, f"{job_id}_mgfxprompt.{_fmt}")
    try:
        fps = int(request.form.get("fps", 30) or 30)
    except ValueError:
        fps = 30
    params = {"kind": plan["kind"], "theme": plan["theme"],
              "text": plan.get("text", ""),
              "subtext": (request.form.get("subtext")
                          or plan.get("subtext") or "")[:120],
              "ratio": request.form.get("ratio") or plan["ratio"],
              "duration": plan["duration"], "fps": fps,
              "quality": request.form.get("quality", "HD"),
              "speed": plan["speed"], "intensity": plan["intensity"],
              "color_primary": plan.get("color_primary"),
              "color_accent": plan.get("color_accent"),
              "color_bg": plan.get("color_bg"),
              "format": _fmt, "preview": False,
              # v10: the artwork itself animates + fills more of the frame
              "art_motion": plan.get("art_motion"),
              "art_scale": (0.88, 0.75) if plan["kind"].startswith("img-") else None,
              "image_path": image_path, "logo_path": None, "plan": plan}
    return jsonify(_start_job("mgfx", image_path or "", dst, params,
                              "Prompt motion: " + (prompt[:60] or
                                                   plan.get("text", "")[:60])))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()
    url = f"http://127.0.0.1:{args.port}"
    print(f"\n  Stock Contributor Toolkit Pro running at {url}\n")
    if not args.no_browser:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    app.run(host=args.host, port=args.port, threaded=True)


if __name__ == "__main__":
    main()
