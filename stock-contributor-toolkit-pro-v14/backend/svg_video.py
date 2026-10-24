"""
SVG to Video - turn a static SVG graphic into a stock-ready MP4 clip.

Pipeline: cairosvg renders the SVG at 2x -> ffmpeg `zoompan` applies a
smooth Ken Burns zoom -> H.264 1080p30 MP4 (yuv420p, faststart).

Great for animated thumbnails, logo stings, and motion backgrounds
from vector art contributors already own.
"""

import os
import shutil
import subprocess

from .svg_render import render_svg_to_png

OUT_W, OUT_H = 1920, 1080
RENDER_SCALE = 2  # render SVG at 2x for smooth zoompan


def find_ffmpeg():
    d = os.environ.get("FFMPEG_DIR")
    if d:
        p = os.path.join(d, "ffmpeg")
        if os.path.isfile(p):
            return p
    p = shutil.which("ffmpeg")
    if p:
        return p
    raise RuntimeError("FFmpeg not found. Install it: https://ffmpeg.org/download.html")


def _is_svg(path):
    try:
        with open(path, "rb") as f:
            head = f.read(4096).decode("utf-8", "ignore").lower()
        return "<svg" in head
    except OSError:
        return False


def svg_to_video(src, dst, duration=10, fps=30, zoom="in",
                 bg="#ffffff", progress_cb=None):
    """
    Convert an SVG file to an MP4 clip. zoom: 'in' | 'out' | 'static'.
    Returns dict with output info.
    """
    if not _is_svg(src):
        raise ValueError("That file doesn't look like an SVG.")
    duration = min(max(float(duration), 3), 60)
    fps = int(fps) if int(fps) in (24, 25, 30) else 30
    frames = int(duration * fps)

    rw, rh = OUT_W * RENDER_SCALE, OUT_H * RENDER_SCALE
    png = dst + ".frame.png"
    render_svg_to_png(src, png, rw, rh, bg)
    if progress_cb:
        progress_cb(0.25, {"stage": "rendered"})

    ff = find_ffmpeg()
    if zoom == "in":
        zexpr = f"min(1+0.12*on/{frames},1.35)"
    elif zoom == "out":
        zexpr = f"max(1.35-0.12*on/{frames},1.0)"
    else:
        zexpr = "1.0"
    vf = (f"zoompan=z='{zexpr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
          f"d={frames}:s={OUT_W}x{OUT_H}:fps={fps},format=yuv420p")

    cmd = [ff, "-hide_banner", "-loglevel", "error", "-y",
           "-loop", "1", "-i", png,
           "-vf", vf, "-frames:v", str(frames),
           "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-r", str(fps), "-movflags", "+faststart", dst]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    try:
        os.remove(png)
    except OSError:
        pass
    if r.returncode != 0 or not os.path.isfile(dst):
        raise RuntimeError("Video render failed: " + (r.stderr or "")[:300])
    if progress_cb:
        progress_cb(1.0, {"stage": "done"})
    return {
        "width": OUT_W, "height": OUT_H, "fps": fps,
        "duration": round(duration, 1), "zoom": zoom,
        "size_mb": round(os.path.getsize(dst) / (1024 * 1024), 2),
    }


if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("dst")
    ap.add_argument("--duration", type=float, default=10)
    ap.add_argument("--zoom", default="in", choices=["in", "out", "static"])
    args = ap.parse_args()
    print(json.dumps(svg_to_video(args.src, args.dst, args.duration, zoom=args.zoom), indent=2))
