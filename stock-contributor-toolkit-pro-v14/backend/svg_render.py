"""
SVG -> PNG rasterising WITHOUT the Cairo native library.

v6: the primary engine is now **resvg** (a professional Rust SVG engine
shipped as a normal pip wheel — no DLLs, no system installs), which
correctly renders modern stock-style SVGs (gradients, opacity, blur/glass
filters) that the older chain failed on. Fallbacks remain: cairosvg,
FFmpeg/librsvg, and a hardened Edge/Chrome headless screenshot.

Used by SVG->Video and by Motion Studio / AI Image->Video SVG inputs.
"""

import os
import shutil
import subprocess
import tempfile
import urllib.parse


def _try_resvg(src, png, w, h, bg):
    import resvg_py
    data = resvg_py.svg_to_bytes(svg_path=src, width=int(w), height=int(h),
                                  background=bg or "#ffffff")
    with open(png, "wb") as f:
        f.write(data)
    return os.path.isfile(png) and os.path.getsize(png) > 0


def _try_cairosvg(src, png, w, h, bg):
    import cairosvg
    cairosvg.svg2png(url=src, write_to=png, output_width=w, output_height=h,
                     background_color=bg)
    return os.path.isfile(png) and os.path.getsize(png) > 0


def _try_ffmpeg(src, png, w, h, bg):
    ff = shutil.which("ffmpeg")
    if not ff:
        return False
    hexcol = (bg or "#ffffff").lstrip("#")
    filt = ("[1:v]scale=%d:%d:force_original_aspect_ratio=decrease[r];"
            "[0][r]overlay=(W-w)/2:(H-h)/2,format=rgba" % (w, h))
    cmd = [ff, "-hide_banner", "-loglevel", "error", "-y",
           "-f", "lavfi", "-i", f"color=c=0x{hexcol}:s={w}x{h}",
           "-i", src, "-filter_complex", filt, "-frames:v", "1", png]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return r.returncode == 0 and os.path.isfile(png) and os.path.getsize(png) > 0


def _try_browser(src, png, w, h, bg):
    candidates = []
    for env in ("ProgramFiles(x86)", "ProgramFiles", "LocalAppData"):
        base = os.environ.get(env)
        if base:
            candidates += [os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe"),
                           os.path.join(base, "Google", "Chrome", "Application", "chrome.exe")]
    candidates += [shutil.which("msedge"), shutil.which("chrome"),
                   shutil.which("google-chrome"), shutil.which("chromium"),
                   shutil.which("chromium-browser")]
    exe = next((c for c in candidates if c and os.path.isfile(c)), None)
    if not exe:
        return False
    uri = "file:///" + urllib.parse.quote(os.path.abspath(src).replace("\\", "/"))
    html = (f"<html><head><style>html,body{{margin:0;background:{bg or '#ffffff'}}}"
            f"img{{width:100vw;height:100vh;object-fit:contain}}</style></head>"
            f"<body><img src=\"{uri}\"></body></html>")
    with tempfile.TemporaryDirectory() as td:
        page = os.path.join(td, "wrap.html")
        with open(page, "w", encoding="utf-8") as f:
            f.write(html)
        out = os.path.join(td, "shot.png")
        page_url = "file:///" + urllib.parse.quote(page.replace("\\", "/"))
        for headless in ("--headless=new", "--headless"):
            cmd = [exe, headless, "--disable-gpu", "--no-sandbox",
                   "--hide-scrollbars", "--disable-dev-shm-usage",
                   f"--user-data-dir={os.path.join(td, 'prof')}",
                   f"--screenshot={out}", f"--window-size={w},{h}",
                   "--virtual-time-budget=8000",
                   "--default-background-color=0xffffffff", page_url]
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            except Exception:  # noqa: BLE001
                continue
            if r.returncode == 0 and os.path.isfile(out) and os.path.getsize(out) > 0:
                shutil.copyfile(out, png)
                return True
    return False


def render_svg_to_png(src, png, w, h, bg="#ffffff"):
    """Rasterise an SVG file to a PNG at w×h. Returns the method used."""
    errors = []
    for name, fn in (("resvg", _try_resvg), ("cairosvg", _try_cairosvg),
                     ("ffmpeg", _try_ffmpeg), ("browser", _try_browser)):
        try:
            if fn(src, png, w, h, bg):
                return name
        except Exception as e:  # noqa: BLE001
            errors.append(f"{name}: {str(e)[:60]}")
    raise RuntimeError(
        "Could not render that SVG on this computer (tried: "
        + "; ".join(errors) + "). Quick option: convert the SVG to PNG/JPG "
        "free at cloudconvert.com and upload that instead — everything else "
        "in the app works normally.")


def clean_error(msg):
    """Turn raw library dumps into a short user-friendly message."""
    s = str(msg or "")
    if "cairo" in s.lower() or "libcairo" in s.lower():
        return ("That SVG needs a renderer this PC doesn't have yet. "
                "Convert it to PNG/JPG (free at cloudconvert.com) or install the free "
                "GTK3 Runtime — all other tools work normally.")
    return s[:300]
