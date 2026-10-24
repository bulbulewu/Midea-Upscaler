"""
Media Toolkit Pro — Version 3.0.0
Multi-Marketplace Studio Engine (Adobe Stock, Shutterstock, Getty, Pond5, Freepik)
Made By Munajat International
"""

import argparse
import json
import os
import threading
import time
import uuid
import webbrowser
from datetime import datetime, timedelta, timezone

from flask import Flask, jsonify, render_template, request, send_file, Response
from werkzeug.utils import secure_filename

from backend.upscaler_video import (
    TARGETS, QUALITY_PRESETS, CODECS, find_ffmpeg, nvenc_available,
    probe as probe_video, upscale as upscale_video,
)
from backend.upscaler_image import (
    upscale_image, probe_image, SCALE_CHOICES, OUTPUT_FORMATS,
    ALLOWED_EXTS as IMG_EXTS,
)
from backend.png_to_psd import png_to_psd, ALLOWED_EXTS as PSD_EXTS
from backend.stock_validator import (
    STOCK_MARKETPLACES, preflight_video_check, preflight_image_check,
)
from backend.license_manager import license_mgr

BASE = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE, "uploads")
OUTPUT_DIR = os.path.join(BASE, "outputs")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi"}

app = Flask(
    __name__,
    template_folder=os.path.join(BASE, "templates"),
    static_folder=os.path.join(BASE, "static"),
)
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024 * 1024  # 4 GB max upload

jobs = {}
jobs_lock = threading.Lock()


def _new_job_id():
    return uuid.uuid4().hex[:12]


def _save_upload(f, allowed, what):
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in allowed:
        raise ValueError(
            f"Unsupported {what} type '{ext}'. Allowed extensions: {', '.join(sorted(allowed))}"
        )
    job_id = _new_job_id()
    src = os.path.join(UPLOAD_DIR, f"{job_id}_{secure_filename(f.filename)}")
    f.save(src)
    return job_id, src


def _run_job(job_id):
    with jobs_lock:
        job = jobs[job_id]
    job["state"] = "running"

    def _cb(frac, _meta=None):
        with jobs_lock:
            job["progress"] = round(frac * 100, 1)

    try:
        kind = job["kind"]
        if kind == "video":
            meta = upscale_video(
                job["src"],
                job["dst"],
                target=job["target"],
                quality=job["quality"],
                codec=job.get("codec", "h264"),
                marketplace=job.get("marketplace", "universal"),
                keep_audio=job["keep_audio"],
                progress_cb=_cb,
            )
        elif kind == "image":
            meta = upscale_image(
                job["src"],
                job["dst"],
                scale=job["scale"],
                output_format=job["out_format"],
                jpg_quality=job["jpg_quality"],
                dpi=job.get("dpi", 300),
                auto_denoise=job.get("auto_denoise", True),
                progress_cb=_cb,
            )
        elif kind == "psd":
            meta = png_to_psd(
                job["src"],
                job["dst"],
                layer_name=job["layer_name"],
                background=job.get("background", "transparent"),
                dpi=job.get("dpi", 300),
                progress_cb=_cb,
            )
        else:
            raise ValueError(f"Unknown job kind: {kind}")

        with jobs_lock:
            job["state"] = "done"
            job["progress"] = 100.0
            job["meta"] = meta
            job["finished_at"] = datetime.now(timezone.utc).isoformat()
    except Exception as exc:  # noqa: BLE001
        with jobs_lock:
            job["state"] = "error"
            job["error"] = str(exc)


def _start_job(job):
    with jobs_lock:
        jobs[job["id"]] = job
    threading.Thread(target=_run_job, args=(job["id"],), daemon=True).start()
    return {"id": job["id"], "source": job["source"]}


def _cleanup_old_files():
    """Background cleanup worker removing files older than 24 hours."""
    while True:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        for folder in (UPLOAD_DIR, OUTPUT_DIR):
            if not os.path.exists(folder):
                continue
            for name in os.listdir(folder):
                p = os.path.join(folder, name)
                try:
                    if datetime.fromtimestamp(os.path.getmtime(p), tz=timezone.utc) < cutoff:
                        os.remove(p)
                except OSError:
                    pass
        time.sleep(3600)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template(
        "index.html",
        marketplaces=STOCK_MARKETPLACES,
        targets=TARGETS,
        qualities=QUALITY_PRESETS,
        codecs=CODECS,
        img_scales=list(SCALE_CHOICES),
        img_formats=OUTPUT_FORMATS,
    )


@app.route("/api/preflight/video", methods=["POST"])
def preflight_video():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "No video file provided."}), 400
    marketplace = request.form.get("marketplace", "universal")
    try:
        job_id, src = _save_upload(f, VIDEO_EXTS, "video")
        info = probe_video(src)
        report = preflight_video_check(info, marketplace)
        # Clean uploaded temp probe file
        if os.path.exists(src):
            os.remove(src)
        return jsonify({"source": info, "report": report})
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 400


@app.route("/api/preflight/image", methods=["POST"])
def preflight_image():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "No image file provided."}), 400
    marketplace = request.form.get("marketplace", "universal")
    try:
        job_id, src = _save_upload(f, IMG_EXTS, "image")
        info = probe_image(src)
        report = preflight_image_check(info, marketplace)
        if os.path.exists(src):
            os.remove(src)
        return jsonify({"source": info, "report": report})
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 400


@app.route("/api/jobs", methods=["POST"])
def create_video_job():
    f = request.files.get("file")
    if f is None or not f.filename:
        return jsonify({"error": "No file uploaded."}), 400

    target = request.form.get("target", "4k")
    quality = request.form.get("quality", "stock")
    codec = request.form.get("codec", "h264")
    marketplace = request.form.get("marketplace", "universal")
    keep_audio = request.form.get("keep_audio", "false").lower() == "true"

    if target not in TARGETS:
        return jsonify({"error": f"Unknown target resolution: {target}"}), 400
    if quality not in QUALITY_PRESETS:
        return jsonify({"error": f"Unknown quality preset: {quality}"}), 400
    if codec not in CODECS:
        return jsonify({"error": f"Unknown codec: {codec}"}), 400

    try:
        job_id, src = _save_upload(f, VIDEO_EXTS, "video")
        info = probe_video(src)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 400

    stem = os.path.splitext(secure_filename(f.filename))[0]
    ext = CODECS[codec]["ext"]
    dst = os.path.join(OUTPUT_DIR, f"{job_id}_{stem}_{target}_{codec}.{ext}")

    return jsonify(_start_job({
        "id": job_id,
        "kind": "video",
        "src": src,
        "dst": dst,
        "filename": f.filename,
        "target": target,
        "quality": quality,
        "codec": codec,
        "marketplace": marketplace,
        "keep_audio": keep_audio,
        "state": "queued",
        "progress": 0.0,
        "source": info,
        "meta": None,
        "error": None,
        "download_name": f"{stem}_{target}_{marketplace}_master.{ext}",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }))


@app.route("/api/image-jobs", methods=["POST"])
def create_image_job():
    f = request.files.get("file")
    if f is None or not f.filename:
        return jsonify({"error": "No file uploaded."}), 400

    scale = request.form.get("scale", "4x")
    out_format = request.form.get("format", "jpg").lower().replace("jpeg", "jpg")
    try:
        jpg_quality = int(request.form.get("quality", 95))
    except ValueError:
        jpg_quality = 95

    try:
        dpi = int(request.form.get("dpi", 300))
    except ValueError:
        dpi = 300

    auto_denoise = request.form.get("auto_denoise", "true").lower() == "true"

    if scale not in SCALE_CHOICES:
        return jsonify({"error": f"Unknown scale: {scale}"}), 400
    if out_format not in OUTPUT_FORMATS:
        return jsonify({"error": f"Unknown format: {out_format}"}), 400

    try:
        job_id, src = _save_upload(f, IMG_EXTS, "image")
        info = probe_image(src)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 400

    stem = os.path.splitext(secure_filename(f.filename))[0]
    dst = os.path.join(OUTPUT_DIR, f"{job_id}_{stem}_{scale}.{out_format}")

    return jsonify(_start_job({
        "id": job_id,
        "kind": "image",
        "src": src,
        "dst": dst,
        "filename": f.filename,
        "scale": scale,
        "out_format": out_format,
        "jpg_quality": jpg_quality,
        "dpi": dpi,
        "auto_denoise": auto_denoise,
        "state": "queued",
        "progress": 0.0,
        "source": info,
        "meta": None,
        "error": None,
        "download_name": f"{stem}_{scale}_master.{out_format}",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }))


@app.route("/api/psd-jobs", methods=["POST"])
def create_psd_job():
    f = request.files.get("file")
    if f is None or not f.filename:
        return jsonify({"error": "No file uploaded."}), 400

    layer_name = (request.form.get("layer_name") or "Artwork Layer").strip()[:60]
    background = request.form.get("background", "transparent")
    try:
        dpi = int(request.form.get("dpi", 300))
    except ValueError:
        dpi = 300

    try:
        job_id, src = _save_upload(f, PSD_EXTS, "image")
        info = probe_image(src)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 400

    stem = os.path.splitext(secure_filename(f.filename))[0]
    dst = os.path.join(OUTPUT_DIR, f"{job_id}_{stem}.psd")

    return jsonify(_start_job({
        "id": job_id,
        "kind": "psd",
        "src": src,
        "dst": dst,
        "filename": f.filename,
        "layer_name": layer_name or "Artwork Layer",
        "background": background,
        "dpi": dpi,
        "state": "queued",
        "progress": 0.0,
        "source": info,
        "meta": None,
        "error": None,
        "download_name": f"{stem}_layered_master.psd",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }))


@app.route("/api/jobs/<job_id>")
def job_status(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
        if job is None:
            return jsonify({"error": "Job not found."}), 404
        out = {k: job[k] for k in ("id", "kind", "filename", "state",
                                  "progress", "source", "meta", "error")
               if k in job}
    return jsonify(out)


@app.route("/api/download/<job_id>")
def download(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
        if job is None or job["state"] != "done":
            return jsonify({"error": "Result file is not ready yet."}), 404
        dst, name = job["dst"], job["download_name"]

    mimetype = "image/vnd.adobe.photoshop" if name.endswith(".psd") else (
        "video/quicktime" if name.endswith(".mov") else None
    )
    return send_file(dst, as_attachment=True, download_name=name, mimetype=mimetype)


@app.route("/api/health")
def health():
    try:
        ff, _ = find_ffmpeg()
        ok = True
        nvenc = nvenc_available(ff)
    except RuntimeError:
        ff, ok, nvenc = None, False, False

    return jsonify({
        "status": "healthy" if ok else "degraded",
        "ffmpeg": ff,
        "ffmpeg_ok": ok,
        "nvenc_available": nvenc,
        "brand": "Made By Munajat International",
        "version": "3.0.0",
        "marketplaces_supported": list(STOCK_MARKETPLACES.keys()),
    })


# ---------------------------------------------------------------------------
# Auth, Licensing, Admin Panel & Settings API
# ---------------------------------------------------------------------------

@app.route("/api/auth/session")
def auth_session():
    return jsonify(license_mgr.get_active_session())


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json(silent=True) or request.form
    email = data.get("email", "")
    password = data.get("password", "")
    res = license_mgr.login(email, password)
    return jsonify(res), (200 if res.get("success") else 401)


@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    data = request.get_json(silent=True) or request.form
    email = data.get("email", "")
    password = data.get("password", "")
    name = data.get("name", "")
    try:
        res = license_mgr.register_user(email, password, name)
        return jsonify(res), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    license_mgr.logout()
    return jsonify({"success": True})


@app.route("/api/license/activate", methods=["POST"])
def license_activate():
    data = request.get_json(silent=True) or request.form
    key = data.get("key", "")
    email = data.get("email", "")
    hwid = data.get("hwid", "PC-LOCAL-ID")
    res = license_mgr.activate_key(key, email, hwid)
    return jsonify(res), (200 if res.get("success") else 400)


@app.route("/api/admin/keys", methods=["GET"])
def admin_get_keys():
    status = request.args.get("status", "All")
    search = request.args.get("search", "")
    keys = license_mgr.get_license_keys(status, search)
    return jsonify({"keys": keys, "total": len(keys)})


@app.route("/api/admin/keys/generate", methods=["POST"])
def admin_generate_key():
    data = request.get_json(silent=True) or request.form
    email = data.get("email", "")
    period = data.get("period", 30)
    limit = data.get("daily_limit", 50)
    note = data.get("note", "")
    try:
        new_key = license_mgr.generate_license_key(email, period, limit, note)
        return jsonify({"success": True, "key": new_key})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/admin/keys/revoke", methods=["POST"])
def admin_revoke_key():
    data = request.get_json(silent=True) or request.form
    key = data.get("key", "")
    ok = license_mgr.revoke_license_key(key)
    return jsonify({"success": ok})


@app.route("/api/admin/keys/delete", methods=["DELETE", "POST"])
def admin_delete_key():
    data = request.get_json(silent=True) or request.form
    key = data.get("key", "")
    ok = license_mgr.delete_license_key(key)
    return jsonify({"success": ok})


@app.route("/api/admin/users", methods=["GET"])
def admin_get_users():
    users = license_mgr.get_users()
    return jsonify({"users": users, "total": len(users)})


@app.route("/api/admin/users/add", methods=["POST"])
def admin_add_user():
    data = request.get_json(silent=True) or request.form
    email = data.get("email", "")
    name = data.get("name", "")
    role = data.get("role", "Pro Contributor")
    limit = data.get("daily_limit", 50)
    try:
        user = license_mgr.add_user(email, name, role, limit)
        return jsonify({"success": True, "user": user})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/admin/users/status", methods=["POST"])
def admin_user_status():
    data = request.get_json(silent=True) or request.form
    user_id = data.get("user_id", "")
    status = data.get("status", "Active")
    ok = license_mgr.update_user_status(user_id, status)
    return jsonify({"success": ok})


@app.route("/api/admin/users/reset-hwid", methods=["POST"])
def admin_user_reset_hwid():
    data = request.get_json(silent=True) or request.form
    user_id = data.get("user_id", "")
    ok = license_mgr.reset_user_hwid(user_id)
    return jsonify({"success": ok})


@app.route("/api/admin/users/edit", methods=["POST"])
def admin_edit_user():
    data = request.get_json(silent=True) or request.form
    user_id = data.get("user_id", "")
    try:
        user = license_mgr.edit_user(user_id, data)
        return jsonify({"success": True, "user": user})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/admin/users/delete", methods=["DELETE", "POST"])
def admin_delete_user():
    data = request.get_json(silent=True) or request.form
    user_id = data.get("user_id", "")
    ok = license_mgr.delete_user(user_id)
    return jsonify({"success": ok})


@app.route("/api/admin/users/export-csv")
def admin_export_users_csv():
    csv_text = license_mgr.export_users_csv()
    return Response(
        csv_text,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=media_toolkit_registered_users.csv"}
    )


@app.route("/api/admin/stats")
def admin_stats():
    stats = license_mgr.get_storage_stats(UPLOAD_DIR, OUTPUT_DIR)
    return jsonify(stats)


@app.route("/api/admin/purge-cache", methods=["POST"])
def admin_purge_cache():
    cleaned = license_mgr.purge_cache(UPLOAD_DIR, OUTPUT_DIR)
    return jsonify({"success": True, "files_removed": cleaned})


@app.route("/api/admin/factory-reset", methods=["POST"])
def admin_factory_reset():
    license_mgr.factory_reset()
    return jsonify({"success": True, "message": "System store reset to initial commercial defaults."})


@app.route("/api/open-folder/<job_id>", methods=["POST"])
def open_folder(job_id):
    import subprocess, sys
    with jobs_lock:
        job = jobs.get(job_id)
        if not job or "dst" not in job:
            return jsonify({"error": "Job output not found"}), 404
        dst = job["dst"]

    try:
        if sys.platform.startswith("win"):
            subprocess.Popen(f'explorer.exe /select,"{os.path.abspath(dst)}"')
        else:
            folder = os.path.dirname(os.path.abspath(dst))
            webbrowser.open(f"file://{folder}")
        return jsonify({"success": True})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/admin/policies", methods=["GET", "POST"])
def admin_policies():
    if request.method == "POST":
        data = request.get_json(silent=True) or request.form
        saved = license_mgr.save_policies(data)
        return jsonify({"success": True, "policies": saved})
    return jsonify(license_mgr.get_policies())


@app.route("/api/admin/backup", methods=["GET"])
def admin_backup_export():
    data = license_mgr.export_backup_json()
    return Response(
        json.dumps(data, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment;filename=media_toolkit_pro_backup.json"}
    )


@app.route("/api/admin/restore", methods=["POST"])
def admin_backup_restore():
    f = request.files.get("backup_file")
    if not f:
        return jsonify({"error": "No backup file provided."}), 400
    try:
        data = json.load(f)
        license_mgr.import_backup_json(data)
        return jsonify({"success": True, "message": "Database restored successfully."})
    except Exception as exc:
        return jsonify({"error": f"Failed to restore: {str(exc)}"}), 400


@app.route("/api/settings/agencies", methods=["GET"])
def get_agency_settings():
    return jsonify(license_mgr.get_agency_settings())


@app.route("/api/settings/agencies/<agency_key>", methods=["POST"])
def save_agency_settings(agency_key):
    data = request.get_json(silent=True) or request.form
    saved = license_mgr.save_agency_settings(agency_key, data)
    return jsonify({"success": True, "settings": saved})


@app.route("/api/settings/studio", methods=["GET", "POST"])
def studio_settings():
    if request.method == "POST":
        data = request.get_json(silent=True) or request.form
        saved = license_mgr.save_studio_settings(data)
        return jsonify({"success": True, "settings": saved})
    return jsonify(license_mgr.get_studio_settings())


def main():
    ap = argparse.ArgumentParser(description="Media Toolkit Pro V3 by Munajat International")
    ap.add_argument("--port", type=int, default=None)
    ap.add_argument("--host", default=None)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    env_port = int(os.environ.get("PORT", 5000))
    port = args.port if args.port is not None else env_port

    env_host = "0.0.0.0" if ("PORT" in os.environ or "RENDER" in os.environ) else "127.0.0.1"
    host = args.host if args.host is not None else env_host

    try:
        ff, _ = find_ffmpeg()
        print(f"[Media Toolkit Pro V3] FFmpeg detected: {ff}")
    except RuntimeError as exc:
        print(f"[Media Toolkit Pro V3] WARNING: {exc}")

    threading.Thread(target=_cleanup_old_files, daemon=True).start()

    url = f"http://{'127.0.0.1' if host == '0.0.0.0' else host}:{port}"
    print(f"\n=======================================================")
    print(f"  Media Toolkit Pro v3.0 — Made By Munajat International")
    print(f"  Multi-Marketplace Engine (Adobe, Shutterstock, Getty)")
    print(f"  Live Server: {url}")
    print(f"=======================================================\n")

    is_cloud = "RENDER" in os.environ or "PORT" in os.environ
    if not args.no_browser and not is_cloud:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()

    app.run(host=host, port=port, threaded=True)


if __name__ == "__main__":
    main()
