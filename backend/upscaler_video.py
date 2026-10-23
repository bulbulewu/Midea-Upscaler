"""
Video Upscaler Pipeline - Version 3 Studio Engine
Made By Munajat International

Marketplace Master Compliance:
  - Adobe Stock, Shutterstock, Getty Images, Pond5, Freepik, Universal Master
  - Frame rate preservation: 23.976, 24, 25, 29.97, 30, 50, 59.94, 60 fps
  - Dual Codec Mastery: H.264 High@5.1 (MP4) and Apple ProRes 422 (MOV)
  - Colorspace: Rec.709 BT.709 television gamut
  - Container optimization: +faststart moov atom at beginning of file
  - Performance: -threads 0 full multi-core CPU threading & auto NVENC acceleration
"""

import json
import os
import re
import shutil
import subprocess
import sys
import threading

STOCK_FPS = (23.976, 24.0, 25.0, 29.97, 30.0, 50.0, 59.94, 60.0)
FPS_TOLERANCE = 0.02
FALLBACK_FPS = 30.0

TARGETS = {
    "4k": {
        "label": "4K UHD (3840×2160)",
        "width": 3840,
        "height": 2160,
        "bitrate": "60M",
        "maxrate": "75M",
        "bufsize": "120M",
    },
    "1440p": {
        "label": "QHD 2K (2560×1440)",
        "width": 2560,
        "height": 1440,
        "bitrate": "32M",
        "maxrate": "40M",
        "bufsize": "65M",
    },
    "1080p": {
        "label": "Full HD (1920×1080)",
        "width": 1920,
        "height": 1080,
        "bitrate": "20M",
        "maxrate": "26M",
        "bufsize": "40M",
    },
}

QUALITY_PRESETS = {
    "stock":    {"label": "Stock Agency Master (~60 Mbps)", "mult": 1.0,  "nvenc_preset": "p6", "x264_preset": "medium"},
    "high":     {"label": "High Definition (~38 Mbps)",     "mult": 0.65, "nvenc_preset": "p5", "x264_preset": "medium"},
    "balanced": {"label": "Balanced Fast (~20 Mbps)",       "mult": 0.35, "nvenc_preset": "p4", "x264_preset": "fast"},
}

CODECS = {
    "h264": {"label": "H.264 High@5.1 Master (MP4)", "ext": "mp4"},
    "prores": {"label": "Apple ProRes 422 Master (MOV)", "ext": "mov"},
}


def _exe_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def find_ffmpeg():
    """Locate FFmpeg and FFprobe binaries."""
    candidates = []
    meipass = getattr(sys, "_MEIPASS", None)
    base = _exe_dir()
    for d in [os.environ.get("FFMPEG_DIR"), meipass and os.path.join(meipass, "bin"),
              os.path.join(base, "bin"), base]:
        if d:
            suffix = ".exe" if os.name == "nt" else ""
            candidates.append((os.path.join(d, "ffmpeg" + suffix),
                               os.path.join(d, "ffprobe" + suffix)))
    for ff, fp in candidates:
        if ff and os.path.isfile(ff):
            return ff, (fp if os.path.isfile(fp) else "ffprobe")
    ff = shutil.which("ffmpeg")
    if ff:
        return ff, shutil.which("ffprobe") or "ffprobe"
    raise RuntimeError(
        "FFmpeg not found. Please install FFmpeg or ensure ffmpeg/ffprobe is on your system PATH."
    )


_NVENC_OK = None


def nvenc_available(ffmpeg):
    """Check if NVENC hardware acceleration is active."""
    global _NVENC_OK
    if _NVENC_OK is not None:
        return _NVENC_OK
    cmd = [
        ffmpeg, "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "nullsrc=s=64x64:d=0.1",
        "-c:v", "h264_nvenc", "-f", "null", "-",
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, timeout=5)
        _NVENC_OK = (res.returncode == 0)
    except Exception:
        _NVENC_OK = False
    return _NVENC_OK


def _parse_rational(val):
    if not val or val == "0/0":
        return None
    if "/" in str(val):
        num, den = val.split("/", 1)
        try:
            return float(num) / float(den) if float(den) != 0 else None
        except ValueError:
            return None
    try:
        return float(val)
    except ValueError:
        return None


def probe(path):
    """Return dictionary of video technical metadata."""
    _, ffprobe = find_ffmpeg()
    cmd = [
        ffprobe, "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        path,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(res.stdout)

    v_stream = next((s for s in data.get("streams", [])
                     if s.get("codec_type") == "video"), None)
    if not v_stream:
        raise ValueError("The provided file does not contain a valid video stream.")

    a_stream = next((s for s in data.get("streams", [])
                     if s.get("codec_type") == "audio"), None)

    fps = _parse_rational(v_stream.get("avg_frame_rate"))
    if not fps or fps < 1 or fps > 240:
        fps = _parse_rational(v_stream.get("r_frame_rate"))
    if not fps:
        fps = 30.0

    fmt = data.get("format", {})
    dur = float(fmt.get("duration") or v_stream.get("duration") or 0.0)
    frames = int(v_stream.get("nb_frames") or 0)
    if not frames and dur > 0 and fps > 0:
        frames = int(round(dur * fps))

    bitrate = float(fmt.get("bit_rate") or v_stream.get("bit_rate") or 0.0)

    return {
        "width": int(v_stream.get("width", 0)),
        "height": int(v_stream.get("height", 0)),
        "fps": round(fps, 3),
        "duration": round(dur, 2),
        "frames": frames,
        "codec": v_stream.get("codec_name", "unknown"),
        "profile": v_stream.get("profile", "unknown"),
        "pix_fmt": v_stream.get("pix_fmt", "unknown"),
        "color_space": v_stream.get("color_space") or v_stream.get("color_primaries") or "bt709",
        "bitrate_kbps": round(bitrate / 1000.0, 1),
        "has_audio": a_stream is not None,
        "audio_codec": a_stream.get("codec_name") if a_stream else None,
        "size_mb": round(os.path.getsize(path) / (1024 * 1024), 2),
        "filename": os.path.basename(path),
    }


def _match_stock_fps(src_fps):
    for target in STOCK_FPS:
        if abs(src_fps - target) <= FPS_TOLERANCE:
            return target, True
    return FALLBACK_FPS, False


def _scale_filter(src_w, src_h, target_w, target_h):
    if src_w <= 0 or src_h <= 0:
        return f"scale={target_w}:{target_h}:flags=lanczos"
    src_ar = src_w / src_h
    tgt_ar = target_w / target_h
    if abs(src_ar - tgt_ar) < 0.01:
        return f"scale={target_w}:{target_h}:flags=lanczos"
    if src_ar > tgt_ar:
        return (f"scale={target_w}:-2:flags=lanczos,"
                f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:black")
    return (f"scale=-2:{target_h}:flags=lanczos,"
            f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:black")


def _scale_bitrate(rate_str, multiplier):
    m = re.match(r"^(\d+(?:\.\d+)?)([kKmMgG]?)$", rate_str)
    if not m:
        return rate_str
    val, unit = float(m.group(1)), m.group(2)
    val = round(val * multiplier, 1)
    if val.is_integer():
        val = int(val)
    return f"{val}{unit}"


def build_command(ffmpeg, src, dst, target="4k", quality="stock",
                  codec="h264", marketplace="universal", keep_audio=False, use_nvenc=None):
    """Build multi-platform FFmpeg command with performance flags."""
    info = probe(src)
    t = TARGETS.get(target, TARGETS["4k"])
    q = QUALITY_PRESETS.get(quality, QUALITY_PRESETS["stock"])

    if use_nvenc is None:
        use_nvenc = nvenc_available(ffmpeg) if codec == "h264" else False

    target_fps, fps_preserved = _match_stock_fps(info["fps"])

    pix_fmt = "yuv422p10le" if codec == "prores" else "yuv420p"
    vf_parts = [
        _scale_filter(info["width"], info["height"], t["width"], t["height"]),
        f"format={pix_fmt}",
    ]
    vf_str = ",".join(vf_parts)

    cmd = [
        ffmpeg, "-y", "-hide_banner", "-stats",
        "-threads", "0",  # Max multi-core CPU utilization
        "-i", src,
        "-vf", vf_str,
    ]

    if not fps_preserved:
        cmd.extend(["-r", f"{target_fps:g}"])

    if codec == "prores":
        cmd.extend([
            "-c:v", "prores_ks",
            "-profile:v", "3",  # ProRes 422 HQ
            "-vendor", "apl0",
            "-bits_per_mb", "8000",
        ])
        encoder_label = "Apple ProRes 422 HQ"
        b_val = "ProRes VBR High"
    else:
        b_val = _scale_bitrate(t["bitrate"], q["mult"])
        max_val = _scale_bitrate(t["maxrate"], q["mult"])
        buf_val = _scale_bitrate(t["bufsize"], q["mult"])

        if use_nvenc:
            cmd.extend([
                "-c:v", "h264_nvenc",
                "-preset", q["nvenc_preset"],
                "-profile:v", "high",
                "-level:v", "5.1",
                "-rc:v", "vbr",
                "-b:v", b_val,
                "-maxrate:v", max_val,
                "-bufsize:v", buf_val,
                "-spatial-aq", "1",
                "-temporal-aq", "1",
            ])
            encoder_label = f"NVIDIA NVENC ({q['nvenc_preset']})"
        else:
            cmd.extend([
                "-c:v", "libx264",
                "-preset", q["x264_preset"],
                "-profile:v", "high",
                "-level:v", "5.1",
                "-b:v", b_val,
                "-maxrate", max_val,
                "-bufsize", buf_val,
            ])
            encoder_label = f"libx264 Multi-Threaded ({q['x264_preset']})"

    # Broadcast standard color tagging
    cmd.extend([
        "-colorspace", "bt709",
        "-color_primaries", "bt709",
        "-color_trc", "bt709",
        "-color_range", "tv",
    ])

    if keep_audio and info["has_audio"]:
        cmd.extend(["-c:a", "aac", "-b:a", "320k"])
        audio_label = "Preserved (AAC 320k Broadcast)"
    else:
        cmd.append("-an")
        audio_label = "Stripped (Stock Agency Compliant)"

    if codec == "h264":
        cmd.extend(["-movflags", "+faststart"])

    cmd.append(dst)

    plan = {
        "source": info,
        "target": t["label"],
        "target_key": target,
        "quality": q["label"],
        "codec": CODECS.get(codec, CODECS["h264"])["label"],
        "codec_key": codec,
        "encoder": encoder_label,
        "video_bitrate": b_val,
        "marketplace": marketplace,
        "fps_plan": f"{target_fps:g}" + (" (Preserved)" if fps_preserved else " (Conformed)"),
        "fps_preserved": fps_preserved,
        "audio": audio_label,
    }
    return cmd, plan


_TIME_RE = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")


def upscale(src, dst, target="4k", quality="stock", codec="h264",
            marketplace="universal", keep_audio=False, progress_cb=None):
    """Execute high performance video upscale pipeline."""
    ffmpeg, _ = find_ffmpeg()
    cmd, plan = build_command(
        ffmpeg, src, dst, target=target, quality=quality, codec=codec,
        marketplace=marketplace, keep_audio=keep_audio
    )

    total_dur = plan["source"]["duration"]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1,
    )

    err_tail = []

    def _read_stderr():
        buf = ""
        while True:
            chunk = proc.stderr.read(1)
            if not chunk:
                break
            if chunk in ("\r", "\n"):
                if buf:
                    err_tail.append(buf)
                    if len(err_tail) > 40:
                        err_tail.pop(0)
                    m = _TIME_RE.search(buf)
                    if m and total_dur > 0 and progress_cb:
                        hh, mm, ss = map(float, m.groups())
                        cur = hh * 3600 + mm * 60 + ss
                        frac = min(0.99, max(0.0, cur / total_dur))
                        progress_cb(frac, {"stage": "encoding", "seconds": cur})
                    buf = ""
            else:
                buf += chunk

    t_read = threading.Thread(target=_read_stderr, daemon=True)
    t_read.start()
    try:
        proc.wait()
        t_read.join()
    finally:
        if proc.stdout:
            proc.stdout.close()
        if proc.stderr:
            proc.stderr.close()

    if proc.returncode != 0:
        tail_msg = "\n".join(err_tail[-15:])
        raise RuntimeError(f"FFmpeg pipeline exited with code {proc.returncode}:\n{tail_msg}")

    if progress_cb:
        progress_cb(1.0, {"stage": "done"})

    plan["output"] = probe(dst)
    return plan
