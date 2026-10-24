"""
AI Image-to-Video (Phase 5) — three engines, honest about what each is:

1) local  (FREE, unlimited, no key) — "2.5D Depth Parallax":
   Estimates a pseudo-depth map from the photo (brightness + sharpness),
   splits it into background / mid / foreground layers and moves them at
   different rates while the virtual camera pushes in / drifts. This is
   cinematic camera motion, NOT generative AI — objects don't morph,
   but stills gain real depth. Great for stock b-roll from photos.

2) replicate (your own Replicate token; new accounts get trial credit) —
   True generative image-to-video via Stable Video Diffusion on
   Replicate's API: POST /v1/predictions, poll, download the MP4.
   Model version is editable (defaults to a public SVD version field —
   paste the current version hash from the model's Replicate page).

3) huggingface (your free HF token) — POSTs the image to the HF Inference
   API for the model ID you give. Many video models are NOT hosted on the
   free inference tier; if the model isn't available you get a clear
   error, and the local engine remains the free fallback.

Keys are never stored — per-request only, same pattern as the AI Hub.
"""

import base64
import io
import json
import mimetypes
import os
import shutil
import subprocess
import time
import urllib.request

from PIL import Image, ImageFilter

RESOLUTIONS = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080), "4:5": (1080, 1350)}


def _ffmpeg():
    ff = shutil.which("ffmpeg")
    if not ff:
        raise RuntimeError("FFmpeg not found.")
    return ff


def _cover(img, w, h):
    img = img.convert("RGB")
    s = max(w / img.width, h / img.height)
    img = img.resize((max(w, int(img.width * s + 0.5)), max(h, int(img.height * s + 0.5))))
    x, y = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))


def _scale_crop(img, w, h, scale, dx=0.0, dy=0.0):
    """Resize img by `scale` (>=1) then crop w×h around centre+offset."""
    nw, nh = int(w * scale + 0.5), int(h * scale + 0.5)
    r = img.resize((nw, nh), Image.BICUBIC)
    cx = (nw - w) // 2 + int(dx * w)
    cy = (nh - h) // 2 + int(dy * h)
    cx = min(max(cx, 0), nw - w); cy = min(max(cy, 0), nh - h)
    return r.crop((cx, cy, cx + w, cy + h))


def local_parallax_video(image_path, dst, *, duration=5.0, fps=24, ratio="16:9",
                         move="push-in", strength=1.0, progress_cb=None):
    duration = min(max(float(duration), 2), 15)
    fps = int(fps) if int(fps) in (24, 25, 30) else 24
    w, h = RESOLUTIONS.get(ratio, RESOLUTIONS["16:9"])
    base = _cover(Image.open(image_path), w, h)
    # ---- pseudo-depth: bright + sharp areas read as "near" (heuristic) ----
    gray = base.convert("L")
    sharp = gray.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(6))
    depth = Image.blend(gray, sharp, 0.45).filter(ImageFilter.GaussianBlur(10))
    lo, hi = depth.getextrema()
    depth = depth.point(lambda v: int((v - lo) * 255 / max(hi - lo, 1)))
    mask_fg = depth.point(lambda v: 255 if v > 168 else 0).filter(ImageFilter.GaussianBlur(14))
    mask_mid = depth.point(lambda v: 255 if v > 84 else 0).filter(ImageFilter.GaussianBlur(14))
    layer_bg = base.filter(ImageFilter.GaussianBlur(2))
    frames = int(duration * fps)
    drift = {"push-in": (0.0, 0.0), "drift-left": (-0.02, 0.0), "drift-right": (0.02, 0.0),
             "drift-up": (0.0, -0.015), "drift-down": (0.0, 0.015)}.get(move, (0.0, 0.0))
    ff = _ffmpeg()
    cmd = [ff, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
           "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-", "-an",
           "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", dst]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE)
    try:
        for i in range(frames):
            p = i / max(frames - 1, 1)
            s = strength
            img = _scale_crop(layer_bg, w, h, 1.0 + 0.05 * p * s, drift[0] * p * 0.4, drift[1] * p * 0.4)
            mid = _scale_crop(base, w, h, 1.0 + 0.11 * p * s, drift[0] * p * 0.8, drift[1] * p * 0.8)
            m_mid = _scale_crop(mask_mid, w, h, 1.0 + 0.11 * p * s, drift[0] * p * 0.8, drift[1] * p * 0.8)
            img = Image.composite(mid, img, m_mid)
            fg = _scale_crop(base, w, h, 1.0 + 0.19 * p * s, drift[0] * p * 1.3, drift[1] * p * 1.3)
            m_fg = _scale_crop(mask_fg, w, h, 1.0 + 0.19 * p * s, drift[0] * p * 1.3, drift[1] * p * 1.3)
            img = Image.composite(fg, img, m_fg)
            proc.stdin.write(img.tobytes())
            if progress_cb and i % 12 == 0:
                progress_cb((i + 1) / frames, {"stage": "parallax"})
        proc.stdin.close()
        err = proc.stderr.read().decode() if proc.stderr else ""
        rc = proc.wait(timeout=900)
    except Exception:
        proc.kill(); raise
    if rc != 0 or not os.path.isfile(dst):
        raise RuntimeError("Parallax render failed: " + (err or "")[:300])
    if progress_cb:
        progress_cb(1.0, {"stage": "done"})
    return {"engine": "local-2.5d-parallax", "width": w, "height": h, "ratio": ratio,
            "fps": fps, "duration": round(duration, 1), "move": move,
            "size_mb": round(os.path.getsize(dst) / 1048576, 2)}


def _download(url, dst, timeout=300):
    req = urllib.request.Request(url, headers={"User-Agent": "stock-toolkit-pro/ai-video"})
    with urllib.request.urlopen(req, timeout=timeout) as r, open(dst, "wb") as f:
        shutil.copyfileobj(r, f)


def replicate_i2v(image_path, dst, token, *, model_version="", progress_cb=None,
                  poll_seconds=240):
    token = (token or "").strip()
    if not token:
        raise ValueError("Paste your Replicate API token (never stored). Get one at replicate.com/account/api-tokens — new accounts receive trial credit.")
    if not (model_version or "").strip():
        raise ValueError("Paste the SVD model version hash from its Replicate page (stability-ai/stable-video-diffusion → API tab → version).")
    mime = mimetypes.guess_type(image_path)[0] or "image/jpeg"
    with open(image_path, "rb") as f:
        data_uri = f"data:{mime};base64," + base64.b64encode(f.read()).decode()
    payload = {"version": model_version.strip(),
               "input": {"image": data_uri, "motion_bucket_id": 127,
                         "cond_aug": 0.02, "decoding_t": 14, "video_length": "25_frames_with_svd_xt"}}
    req = urllib.request.Request(
        "https://api.replicate.com/v1/predictions",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Token {token}", "Content-Type": "application/json",
                 "User-Agent": "stock-toolkit-pro/ai-video"})
    with urllib.request.urlopen(req, timeout=60) as r:
        pred = json.loads(r.read().decode())
    get_url = (pred.get("urls") or {}).get("get")
    if not get_url:
        raise RuntimeError("Replicate did not return a polling URL.")
    deadline = time.time() + poll_seconds
    while time.time() < deadline:
        req = urllib.request.Request(get_url, headers={"Authorization": f"Token {token}"})
        with urllib.request.urlopen(req, timeout=60) as r:
            pred = json.loads(r.read().decode())
        st = pred.get("status")
        if progress_cb:
            progress_cb(0.5, {"stage": f"replicate: {st}"})
        if st == "succeeded":
            out = pred.get("output")
            url = out if isinstance(out, str) else (out[0] if isinstance(out, list) and out else None)
            if not url:
                raise RuntimeError("Replicate finished but returned no video URL.")
            _download(url, dst)
            return {"engine": "replicate-svd", "size_mb": round(os.path.getsize(dst) / 1048576, 2)}
        if st in ("failed", "canceled"):
            raise RuntimeError("Replicate generation failed: " + str(pred.get("error"))[:200])
        time.sleep(5)
    raise RuntimeError("Replicate timed out after 4 minutes — check your Replicate dashboard; the video may still finish there.")


def hf_i2v(image_path, dst, token, *, model="", progress_cb=None):
    token = (token or "").strip()
    model = (model or "").strip()
    if not token:
        raise ValueError("Paste your Hugging Face token (never stored).")
    if not model:
        raise ValueError("Enter a Hugging Face image-to-video model ID.")
    with open(image_path, "rb") as f:
        raw = f.read()
    req = urllib.request.Request(
        "https://api-inference.huggingface.co/models/" + model,
        data=raw, headers={"Authorization": f"Bearer {token}",
                           "Content-Type": mimetypes.guess_type(image_path)[0] or "image/jpeg"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            ctype = r.headers.get("Content-Type", "")
            data = r.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")[:220]
        raise RuntimeError(f"Hugging Face returned HTTP {e.code}: {body} — this model is likely not hosted on the free Inference API. Use the free Local engine or Replicate.")
    if "video" not in ctype and not data[:4] == b"\x00\x00\x00\x18":
        raise RuntimeError("That HF endpoint did not return a video (free Inference rarely hosts video models). Use Local or Replicate engine.")
    with open(dst, "wb") as f:
        f.write(data)
    if progress_cb:
        progress_cb(1.0, {"stage": "done"})
    return {"engine": "huggingface", "model": model,
            "size_mb": round(os.path.getsize(dst) / 1048576, 2)}
