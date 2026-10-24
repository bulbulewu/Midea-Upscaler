"""
Motion Video Studio — commercial-grade, 100% free (local FFmpeg only).

Inspired by MotionHero / EffectCraft / PaperLayer / Smooth.video /
GizzMotion / EffectSnap class tools: turn still images (JPG/PNG/WEBP/SVG)
into polished motion videos — no watermark, no subscription, no API cost.

Pipeline (all local):
  per image -> scale/crop to canvas -> zoompan (Ken Burns / pan / parallax)
            -> colour grade -> segment MP4
  segments  -> xfade transitions (fade/slide/wipe/blur-ish fadeblack etc.)
  overlay   -> animated title + subtitle (drawtext, fade in/out)
  audio     -> optional user music track, looped/trimmed, fade-out
  export    -> H.264 MP4 (yuv420p, +faststart) for stock / social / clients,
               plus optional GIF preview

Resolutions: 1920x1080 (16:9), 1080x1920 (9:16), 1080x1080 (1:1), 1080x1350 (4:5)
Effects: zoom-in, zoom-out, pan-left/right/up/down, parallax (zoom+pan),
         static, pulse
Transitions (xfade): fade, fadeblack, fadewhite, slideleft, slideright,
         slideup, slidedown, wipeleft, circleopen, dissolve, none (concat)
Grades: none, cinematic, vibrant, warm, cool, mono
"""

import os
import re
import shutil
import subprocess

RESOLUTIONS = {
    "16:9": (1920, 1080), "9:16": (1080, 1920),
    "1:1": (1080, 1080), "4:5": (1080, 1350),
}
EFFECTS = {"zoom-in", "zoom-out", "pan-left", "pan-right", "pan-up", "pan-down", "parallax", "static", "pulse"}
TRANSITIONS = {"fade", "fadeblack", "fadewhite", "slideleft", "slideright", "slideup", "slidedown", "wipeleft", "circleopen", "dissolve", "none"}
GRADES = {
    "none": None,
    "cinematic": "eq=contrast=1.12:saturation=0.88:brightness=-0.02,vignette=PI/5",
    "vibrant": "eq=contrast=1.08:saturation=1.35",
    "warm": "colorbalance=rs=0.12:gs=0.04:bs=-0.12,eq=saturation=1.08",
    "cool": "colorbalance=rs=-0.10:gs=0.02:bs=0.14,eq=saturation=1.02",
    "mono": "hue=s=0,eq=contrast=1.10",
}
TEMPLATES = {
    "stock-broll":      {"effect": "zoom-in",    "transition": "fade",      "grade": "cinematic", "per_slide": 5},
    "social-reel":      {"effect": "parallax",   "transition": "slideleft", "grade": "vibrant",   "per_slide": 3},
    "product-showcase": {"effect": "pulse",      "transition": "fadewhite", "grade": "none",      "per_slide": 4},
    "slideshow-pro":    {"effect": "pan-right",  "transition": "dissolve",  "grade": "warm",      "per_slide": 5},
    "logo-sting":       {"effect": "zoom-out",   "transition": "fadeblack", "grade": "cinematic", "per_slide": 4},
    "minimal":          {"effect": "static",     "transition": "fade",      "grade": "none",      "per_slide": 4},
}


def find_ffmpeg():
    p = shutil.which("ffmpeg")
    if p:
        return p
    d = os.environ.get("FFMPEG_DIR")
    if d and os.path.isfile(os.path.join(d, "ffmpeg")):
        return os.path.join(d, "ffmpeg")
    raise RuntimeError("FFmpeg not found. Install ffmpeg (free) — on Render/Docker it is in the Dockerfile.")


def _font():
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"):
        if os.path.isfile(p):
            return p
    return None  # drawtext will use fontconfig default 'Sans'


def _esc(text):
    return (text or "").replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'").replace("%", "\\%")


def _zoompan(effect, frames, w, h):
    # zoompan works on the up-scaled input; x/y are in input pixels.
    cx, cy = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    if effect == "zoom-in":
        z, x, y = f"min(1+0.18*on/{frames},1.30)", cx, cy
    elif effect == "zoom-out":
        z, x, y = f"max(1.30-0.18*on/{frames},1.0)", cx, cy
    elif effect == "pan-left":
        z, x, y = "1.25", f"(iw-iw/zoom)*(1-on/{frames})", cy
    elif effect == "pan-right":
        z, x, y = "1.25", f"(iw-iw/zoom)*(on/{frames})", cy
    elif effect == "pan-up":
        z, x, y = "1.25", cx, f"(ih-ih/zoom)*(1-on/{frames})"
    elif effect == "pan-down":
        z, x, y = "1.25", cx, f"(ih-ih/zoom)*(on/{frames})"
    elif effect == "parallax":  # zoom + diagonal drift = pseudo-parallax
        z, x, y = f"min(1.08+0.16*on/{frames},1.30)", f"(iw-iw/zoom)*(on/{frames})", f"(ih-ih/zoom)*(on/{frames})"
    elif effect == "pulse":
        z, x, y = f"1.12+0.05*sin(on/{frames}*3.14159)", cx, cy
    else:  # static
        z, x, y = "1.10", cx, cy
    return f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={w}x{h}:fps={{fps}}"


def create_motion_video(image_paths, dst, *, template="stock-broll", effect=None,
                        transition=None, grade=None, ratio="16:9", per_slide=4.0,
                        fps=30, title="", subtitle="", audio_path=None,
                        bg="#000000", progress_cb=None):
    if not image_paths:
        raise ValueError("Upload at least one image.")
    tpl = TEMPLATES.get(template, TEMPLATES["stock-broll"])
    effect = effect if effect in EFFECTS else tpl["effect"]
    transition = transition if transition in TRANSITIONS else tpl["transition"]
    grade = grade if grade in GRADES else tpl["grade"]
    per_slide = min(max(float(per_slide or tpl["per_slide"]), 1.5), 15.0)
    fps = int(fps) if int(fps) in (24, 25, 30, 60) else 30
    w, h = RESOLUTIONS.get(ratio, RESOLUTIONS["16:9"])
    ff = find_ffmpeg()
    work = dst + ".work"; os.makedirs(work, exist_ok=True)
    segments = []
    try:
        # ---------- per-image segments ----------
        for i, src in enumerate(image_paths):
            frames = max(1, int(per_slide * fps))
            # SVG inputs: rasterise first if cairosvg available
            img = src
            if src.lower().endswith(".svg"):
                from .svg_render import render_svg_to_png
                img = os.path.join(work, f"in{i}.png")
                render_svg_to_png(src, img, w * 2, h * 2, bg)
            vf = (f"scale={w*2}:{h*2}:force_original_aspect_ratio=increase,"
                  f"crop={w*2}:{h*2}," + _zoompan(effect, frames, w, h).format(fps=fps))
            if GRADES.get(grade):
                vf += "," + GRADES[grade]
            vf += ",format=yuv420p"
            seg = os.path.join(work, f"seg{i}.mp4")
            cmd = [ff, "-hide_banner", "-loglevel", "error", "-y",
                   "-loop", "1", "-i", img, "-vf", vf, "-frames:v", str(frames),
                   "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-r", str(fps), seg]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
            if r.returncode != 0 or not os.path.isfile(seg):
                raise RuntimeError("Render failed on image %d: %s" % (i + 1, (r.stderr or "")[:300]))
            segments.append(seg)
            if progress_cb:
                progress_cb(0.15 + 0.55 * (i + 1) / len(image_paths), {"stage": f"slide {i+1}/{len(image_paths)}"})

        # ---------- join with transitions ----------
        joined = os.path.join(work, "joined.mp4")
        if len(segments) == 1 or transition == "none":
            if len(segments) == 1:
                shutil.copyfile(segments[0], joined)
            else:
                lst = os.path.join(work, "list.txt")
                with open(lst, "w") as f:
                    for s in segments:
                        f.write(f"file '{s}'\n")
                r = subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined],
                                   capture_output=True, text=True, timeout=600)
                if r.returncode != 0:
                    raise RuntimeError("Join failed: " + (r.stderr or "")[:300])
            xfade_used = "none"
        else:
            # chained xfade: offset accumulates per_slide - transition_dur
            td = 0.8
            inputs, filt, prev = [], [], "0:v"
            for s in segments:
                inputs += ["-i", s]
            cur_dur = per_slide
            for idx in range(1, len(segments)):
                offset = cur_dur - td
                out_lbl = f"xf{idx}"
                filt.append(f"[{prev}][{idx}:v]xfade=transition={transition}:duration={td}:offset={offset:.3f}[{out_lbl}]")
                prev = out_lbl; cur_dur += per_slide - td
            cmd = [ff, "-hide_banner", "-loglevel", "error", "-y"] + inputs + \
                  ["-filter_complex", ";".join(filt), "-map", f"[{prev}]",
                   "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-r", str(fps), joined]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
            if r.returncode != 0 or not os.path.isfile(joined):
                # safe fallback: plain concat if a build lacks a transition
                lst = os.path.join(work, "list.txt")
                with open(lst, "w") as f:
                    for s in segments:
                        f.write(f"file '{s}'\n")
                subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined],
                               capture_output=True, text=True, timeout=600)
                xfade_used = "fade (fallback)"
            else:
                xfade_used = transition
        if progress_cb:
            progress_cb(0.78, {"stage": "joined"})

        total = per_slide * len(segments) - (0.8 * (len(segments) - 1) if len(segments) > 1 and transition != "none" else 0)

        # ---------- title overlay + audio ----------
        final_filters = []
        font = _font()
        font_arg = f"fontfile='{font}':" if font else ""
        if title.strip():
            final_filters.append(
                f"drawtext={font_arg}text='{_esc(title.strip()[:80])}':fontsize={int(h*0.055)}:fontcolor=white:"
                f"borderw=2:bordercolor=black@0.45:shadowcolor=black@0.5:shadowx=2:shadowy=2:"
                f"x=(w-text_w)/2:y=h*0.78:alpha='if(lt(t,0.6),t/0.6,if(gt(t,{max(total-0.8,1):.1f}),( {total:.1f}-t)/0.8,1))'")
        if subtitle.strip():
            final_filters.append(
                f"drawtext={font_arg}text='{_esc(subtitle.strip()[:110])}':fontsize={int(h*0.032)}:fontcolor=white:"
                f"borderw=1:bordercolor=black@0.4:x=(w-text_w)/2:y=h*0.86:"
                f"alpha='if(lt(t,1.0),max(0,(t-0.4)/0.6),if(gt(t,{max(total-0.8,1):.1f}),({total:.1f}-t)/0.8,1))'")
        cmd = [ff, "-hide_banner", "-loglevel", "error", "-y", "-i", joined]
        if audio_path and os.path.isfile(audio_path):
            cmd += ["-stream_loop", "-1", "-i", audio_path]
        if final_filters:
            cmd += ["-vf", ",".join(final_filters)]
        cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p"]
        if audio_path and os.path.isfile(audio_path):
            fade_start = max(total - 2.0, 0)
            cmd += ["-map", "0:v", "-map", "1:a", "-af", f"afade=t=out:st={fade_start:.1f}:d=2,atrim=0:{total:.1f}", "-c:a", "aac", "-b:a", "160k"]
        cmd += ["-movflags", "+faststart", "-t", f"{total:.2f}", dst]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if r.returncode != 0 or not os.path.isfile(dst):
            raise RuntimeError("Final render failed: " + (r.stderr or "")[:400])
        if progress_cb:
            progress_cb(1.0, {"stage": "done"})
        return {"width": w, "height": h, "ratio": ratio, "fps": fps,
                "duration": round(total, 1), "slides": len(image_paths),
                "effect": effect, "transition": xfade_used if len(segments) > 1 else "—",
                "grade": grade, "template": template,
                "audio": bool(audio_path), "title": bool(title.strip()),
                "size_mb": round(os.path.getsize(dst) / 1048576, 2)}
    finally:
        shutil.rmtree(work, ignore_errors=True)
