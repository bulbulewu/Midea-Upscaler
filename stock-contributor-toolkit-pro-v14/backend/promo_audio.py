"""
Promo Maker v9 — audio: voiceover TTS, captions/SRT, SFX and jingles.

Voiceover routes (all OPTIONAL — Promo Maker works fully without them):
  (a) edge-tts — free, no key, needs the `edge-tts` pip package AND
      internet access to Microsoft's speech service. The import is
      guarded: if the package is missing, only voiceover is disabled.
  (b) own-key OpenAI-compatible TTS endpoint (ai_hub "custom" pattern):
      POST {base_url}/audio/speech {model, voice, input} -> audio bytes.
  (c) the user's own recorded voice file (MP3/WAV upload).

Captions are generated from the script + scene timings — no speech
recognition needed. Word timings distribute words evenly across each
scene's narration window.

Jingle Maker: spoken line + music bed + intro/outro SFX, mixed locally.
The synthesised voice file is CACHED (hash of text+voice+rate+pitch) so
a Remix with a different bed/SFX never re-calls the TTS service.
"""

import asyncio
import hashlib
import json
import math
import os
import struct
import subprocess
import urllib.request
import wave

# ------------------------------------------------------------ edge voices
# Curated well-known Microsoft Edge neural voices (edge-tts). Listing is
# static so the UI works offline; synthesis itself needs internet.
EDGE_VOICES = {
    "en-US": [("en-US-AvaNeural", "Ava — female, warm"),
              ("en-US-AndrewNeural", "Andrew — male, warm"),
              ("en-US-EmmaNeural", "Emma — female, friendly"),
              ("en-US-BrianNeural", "Brian — male, deep")],
    "en-GB": [("en-GB-SoniaNeural", "Sonia — female"),
              ("en-GB-RyanNeural", "Ryan — male")],
    "en-IN": [("en-IN-NeerjaNeural", "Neerja — female"),
              ("en-IN-PrabhatNeural", "Prabhat — male")],
    "bn-BD": [("bn-BD-NabanitaNeural", "Nabanita — female (Bangla BD)"),
              ("bn-BD-PradeepNeural", "Pradeep — male (Bangla BD)")],
    "bn-IN": [("bn-IN-TanishaaNeural", "Tanishaa — female (Bangla IN)"),
              ("bn-IN-BashkarNeural", "Bashkar — male (Bangla IN)")],
    "hi-IN": [("hi-IN-SwaraNeural", "Swara — female (Hindi)"),
              ("hi-IN-MadhurNeural", "Madhur — male (Hindi)")],
    "ar-SA": [("ar-SA-ZariyahNeural", "Zariyah — female (Arabic)"),
              ("ar-SA-HamedNeural", "Hamed — male (Arabic)")],
    "es-ES": [("es-ES-ElviraNeural", "Elvira — female (Spanish)"),
              ("es-ES-AlvaroNeural", "Alvaro — male (Spanish)")],
    "ur-PK": [("ur-PK-UzmaNeural", "Uzma — female (Urdu)"),
              ("ur-PK-AsadNeural", "Asad — male (Urdu)")],
}


def edge_tts_available():
    try:
        import edge_tts  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def _ffmpeg():
    import shutil
    return shutil.which("ffmpeg")


def _ffprobe():
    import shutil
    return shutil.which("ffprobe")


def probe_duration(path):
    """Seconds (float) or 0.0 if unreadable."""
    fp = _ffprobe()
    if not fp or not path or not os.path.isfile(path):
        return 0.0
    try:
        out = subprocess.run([fp, "-v", "error", "-show_entries", "format=duration",
                              "-of", "csv=p=0", path],
                             capture_output=True, text=True, timeout=30)
        return float((out.stdout or "0").strip() or 0)
    except Exception:  # noqa: BLE001
        return 0.0


# ------------------------------------------------------------ TTS engines
def synth_edge_tts(text, voice, rate_pct=0, pitch_hz=0, out_path=None):
    """Free voiceover via Microsoft Edge voices. Raises RuntimeError with
    a friendly message on any failure (missing package / no network)."""
    try:
        import edge_tts
    except Exception:  # noqa: BLE001
        raise RuntimeError(
            "Voiceover needs the free edge-tts package: pip install edge-tts "
            "(then restart the app). Everything else works without it.")
    rate = f"{int(rate_pct):+d}%"
    pitch = f"{int(pitch_hz):+d}Hz"

    async def _run():
        comm = edge_tts.Communicate(text, voice or "en-US-AvaNeural",
                                    rate=rate, pitch=pitch)
        await comm.save(out_path)

    try:
        asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "edge-tts could not reach Microsoft's free speech service "
            f"(internet required): {str(exc)[:140]}")
    if not os.path.isfile(out_path) or os.path.getsize(out_path) < 200:
        raise RuntimeError("edge-tts returned no audio — check your internet connection.")
    return out_path


def synth_openai_tts(base_url, key, model, voice, text, out_path):
    """Own-key OpenAI-compatible TTS: POST {base}/audio/speech."""
    base = (base_url or "").strip().rstrip("/")
    if not base:
        raise ValueError("Paste your TTS endpoint base URL (e.g. https://api.openai.com/v1).")
    if not (key or "").strip():
        raise ValueError("Paste your TTS API key — it is sent per-request and never stored.")
    payload = json.dumps({"model": model or "tts-1", "voice": voice or "alloy",
                          "input": text, "response_format": "mp3"}).encode()
    req = urllib.request.Request(base + "/audio/speech", data=payload, method="POST",
                                 headers={"Authorization": f"Bearer {key.strip()}",
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"TTS endpoint failed: {str(exc)[:160]}")
    if len(data) < 200:
        raise RuntimeError("TTS endpoint returned no audio.")
    with open(out_path, "wb") as f:
        f.write(data)
    return out_path


def synth_voice(engine, text, out_path, *, voice="en-US-AvaNeural", rate_pct=0,
                pitch_hz=0, base_url=None, api_key=None, model=None):
    """Dispatch to the chosen engine. engine: edge | openai."""
    if engine == "openai":
        return synth_openai_tts(base_url, api_key, model, voice, text, out_path)
    return synth_edge_tts(text, voice, rate_pct, pitch_hz, out_path)


# ------------------------------------------------------------ captions
CAPTION_STYLES = ("karaoke", "hormozi", "bold-pop", "clean-outline",
                  "clean-minimal", "comics")


def build_captions(scenes_timing, source="voiceover"):
    """scenes_timing: [{start, end, voiceover_line, on_screen_text}].
    Returns cues [{start, end, text, words: [(word, w_start, w_end)]}].
    Words are distributed evenly across the cue window (word-by-word mode).
    """
    cues = []
    for sc in scenes_timing:
        text = (sc.get("voiceover_line") or "").strip()
        if not text and source != "voiceover":
            text = (sc.get("on_screen_text") or "").strip()
        if not text:
            continue
        start, end = float(sc["start"]), float(sc["end"])
        if end <= start:
            end = start + 0.5
        words = text.split()
        step = (end - start) / max(len(words), 1)
        wt = [(wd, round(start + i * step, 3), round(start + (i + 1) * step, 3))
              for i, wd in enumerate(words)]
        cues.append({"start": round(start, 3), "end": round(end, 3),
                     "text": text, "words": wt})
    cues.sort(key=lambda c: c["start"])
    return cues


def _srt_ts(sec):
    sec = max(0.0, float(sec))
    ms = int(round((sec - int(sec)) * 1000))
    s = int(sec) % 60
    m = (int(sec) // 60) % 60
    h = int(sec) // 3600
    if ms == 1000:
        ms, s = 0, s + 1
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(cues, path):
    lines = []
    for i, c in enumerate(cues, 1):
        lines.append(str(i))
        lines.append(f"{_srt_ts(c['start'])} --> {_srt_ts(c['end'])}")
        lines.append(c["text"])
        lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


# ------------------------------------------------------------ SFX synth
SR = 22050


def _write_wav(path, samples):
    frames = bytearray()
    for x in samples:
        v = max(-1.0, min(1.0, x))
        frames += struct.pack("<h", int(v * 32767))
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(bytes(frames))


def synth_sfx(kind, out_path):
    """Short locally-synthesised intro/outro sounds. kind: chime|whoosh|sting."""
    n = int(SR * 1.1)
    buf = [0.0] * n
    if kind == "chime":
        for j, f in enumerate((1318.5, 1568.0, 2093.0)):  # E6 G6 C7 sparkle
            t0 = int(j * 0.09 * SR)
            for i in range(n - t0):
                tt = i / SR
                buf[t0 + i] += 0.30 * math.exp(-tt * 5) * math.sin(2 * math.pi * f * tt)
    elif kind == "whoosh":
        import random
        rnd = random.Random(7)
        lp = 0.0
        for i in range(n):
            tt = i / SR
            env = math.sin(math.pi * min(tt / 1.1, 1.0)) ** 2
            lp += 0.25 * ((rnd.random() * 2 - 1) - lp)  # crude low-pass sweep
            buf[i] = 0.55 * env * lp * 3
    elif kind == "sting":  # news-style major stab
        for f in (261.63, 329.63, 392.0, 523.25):
            for i in range(n):
                tt = i / SR
                buf[i] += 0.16 * math.exp(-tt * 3.2) * (
                    math.sin(2 * math.pi * f * tt) + 0.5 * math.sin(2 * math.pi * f * 2 * tt))
    else:
        raise ValueError(f"Unknown SFX '{kind}'.")
    peak = max(abs(x) for x in buf) or 1.0
    _write_wav(out_path, [x * 0.85 / peak for x in buf])
    return out_path


# ------------------------------------------------------------ jingle
JINGLE_PRESETS = {
    "business": {"label": "Business Jingle", "seconds": 15},
    "audio-promo": {"label": "Audio Promo (15–60s)", "seconds": 30},
    "sale-sting": {"label": "Sale Sting (5s)", "seconds": 5},
    "sonic-logo": {"label": "End-card Sonic Logo (3s)", "seconds": 3},
}


def _voice_cache_key(text, voice, rate_pct, pitch_hz, engine):
    raw = f"{engine}|{voice}|{rate_pct}|{pitch_hz}|{text.strip().lower()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:20]


def make_jingle(line, workdir, *, engine="edge", voice="en-US-AvaNeural",
                rate_pct=0, pitch_hz=0, base_url=None, api_key=None, model=None,
                bed_path=None, intro="chime", outro="chime", preset="business"):
    """Build a jingle: [intro SFX] + voice over ducked bed + [outro SFX].

    Returns {mp3, wav, duration, voice_cached, voice_seconds}.
    The voice file is cached in workdir/voice_cache — a Remix (same line +
    voice, different bed/intro/outro) reuses it without re-calling TTS.
    """
    ff = _ffmpeg()
    if not ff:
        raise RuntimeError("FFmpeg not found.")
    line = (line or "").strip()
    if not line:
        raise ValueError("Write the jingle line first.")
    os.makedirs(workdir, exist_ok=True)
    cache_dir = os.path.join(workdir, "voice_cache")
    os.makedirs(cache_dir, exist_ok=True)
    key = _voice_cache_key(line, voice, rate_pct, pitch_hz, engine)
    voice_mp3 = os.path.join(cache_dir, key + ".mp3")
    cached = os.path.isfile(voice_mp3) and os.path.getsize(voice_mp3) > 200
    if not cached:
        tmp = os.path.join(workdir, f"jingle_voice_{key}.mp3")
        synth_voice(engine, line, tmp, voice=voice, rate_pct=rate_pct,
                    pitch_hz=pitch_hz, base_url=base_url, api_key=api_key,
                    model=model)
        os.replace(tmp, voice_mp3)
    vdur = probe_duration(voice_mp3)

    parts = []  # (path, kind) in order: intro, bed+voice, outro built via ffmpeg
    intro_wav = outro_wav = None
    if intro and intro != "none":
        intro_wav = os.path.join(workdir, f"sfx_{intro}.wav")
        if not os.path.isfile(intro_wav):
            synth_sfx(intro, intro_wav)
    if outro and outro != "none":
        outro_wav = os.path.join(workdir, f"sfx_{outro}_o.wav")
        if not os.path.isfile(outro_wav):
            synth_sfx(outro, outro_wav)
    intro_d = probe_duration(intro_wav) if intro_wav else 0.0
    outro_d = probe_duration(outro_wav) if outro_wav else 0.0
    total = intro_d + vdur + outro_d + 0.35

    inputs, filters = [], []
    idx = 0
    if intro_wav:
        inputs += ["-i", intro_wav]; intro_i = idx; idx += 1
    else:
        intro_i = None
    inputs += ["-i", voice_mp3]; voice_i = idx; idx += 1
    if bed_path and os.path.isfile(bed_path):
        inputs += ["-stream_loop", "-1", "-i", bed_path]; bed_i = idx; idx += 1
    else:
        bed_i = None
    if outro_wav:
        inputs += ["-i", outro_wav]; outro_i = idx; idx += 1
    else:
        outro_i = None

    # voice delayed past the intro; bed ducked under voice via
    # sidechaincompress (fallback handled by caller-visible retry below).
    chains = []
    if intro_i is not None:
        chains.append(f"[{intro_i}:a]aformat=sample_rates=44100:channel_layouts=stereo[intro]")
    chains.append(f"[{voice_i}:a]aformat=sample_rates=44100:channel_layouts=stereo,"
                  f"adelay={int(intro_d*1000)}|{int(intro_d*1000)}[voice]")
    labels = ["[intro]"] if intro_i is not None else []
    labels.append("[voice]")
    if outro_i is not None:
        od = int((intro_d + vdur + 0.15) * 1000)
        chains.append(f"[{outro_i}:a]aformat=sample_rates=44100:channel_layouts=stereo,"
                      f"adelay={od}|{od}[outro]")
        labels.append("[outro]")
    if bed_i is not None:
        chains.append(f"[{bed_i}:a]aformat=sample_rates=44100:channel_layouts=stereo[bedraw]")
        # the voice feeds BOTH the sidechain key and the final mix — split it
        chains.append("[voice]asplit=2[voicemix][voicekey]")
        labels[labels.index("[voice]")] = "[voicemix]"
        duck = ("[bedraw][voicekey]sidechaincompress=threshold=0.02:ratio=10:"
                "attack=15:release=320[bed]")
        mix_in = "".join(labels)
        filters = chains + [duck,
                            f"{mix_in}[bed]amix=inputs={len(labels)+1}:duration=longest:"
                            f"dropout_transition=0,apad,atrim=0:{total:.2f},"
                            f"afade=t=out:st={max(total-0.5,0):.2f}:d=0.5,"
                            "loudnorm=I=-15:TP=-1.2:LRA=11[aout]"]
    else:
        mix_in = "".join(labels)
        filters = chains + [
            f"{mix_in}amix=inputs={len(labels)}:duration=longest:dropout_transition=0,"
            f"apad,atrim=0:{total:.2f},afade=t=out:st={max(total-0.5,0):.2f}:d=0.5,"
            "loudnorm=I=-15:TP=-1.2:LRA=11[aout]"]

    mix_key = hashlib.sha256(
        f"{bed_path}|{intro}|{outro}|{preset}".encode()).hexdigest()[:8]
    out_mp3 = os.path.join(workdir, f"jingle_{key}_{preset}_{mix_key}.mp3")
    out_wav = os.path.join(workdir, f"jingle_{key}_{preset}_{mix_key}.wav")
    cmd = [ff, "-hide_banner", "-loglevel", "error", "-y", *inputs,
           "-filter_complex", ";".join(filters), "-map", "[aout]",
           "-t", f"{total:.2f}", "-codec:a", "libmp3lame", "-b:a", "192k", out_mp3]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        # fallback: plain volume ducking instead of sidechaincompress
        filters2 = [f.replace("[bedraw][voicekey]sidechaincompress=threshold=0.02:"
                              "ratio=10:attack=15:release=320[bed]",
                              "[bedraw]volume=0.30[bed]") for f in filters]
        cmd[cmd.index("-filter_complex") + 1] = ";".join(filters2)
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            raise RuntimeError("Jingle mix failed: " + (r.stderr or "")[:240])
    subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-y", "-i", out_mp3,
                    "-codec:a", "pcm_s16le", out_wav],
                   capture_output=True, timeout=120)
    dur = probe_duration(out_mp3)
    return {"mp3": out_mp3, "wav": out_wav, "duration": round(dur, 2),
            "voice_cached": cached, "voice_seconds": round(vdur, 2),
            "mixer": "sidechaincompress"}


def mix_voice_track(clips_timing, total_dur, workdir, name="voice_track.m4a"):
    """Assemble per-scene voice clips into ONE track aligned to scene starts.
    clips_timing: [{path, start}]. Returns path or None."""
    ff = _ffmpeg()
    if not ff or not clips_timing:
        return None
    inputs, chains = [], []
    for i, c in enumerate(clips_timing):
        inputs += ["-i", c["path"]]
        d = int(float(c["start"]) * 1000)
        chains.append(f"[{i}:a]aformat=sample_rates=44100:channel_layouts=stereo,"
                      f"adelay={d}|{d}[v{i}]")
    mix = "".join(f"[v{i}]" for i in range(len(clips_timing)))
    chains.append(f"{mix}amix=inputs={len(clips_timing)}:duration=longest:"
                  f"dropout_transition=0,apad,atrim=0:{total_dur:.2f}[aout]")
    out = os.path.join(workdir, name)
    r = subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-y", *inputs,
                        "-filter_complex", ";".join(chains), "-map", "[aout]",
                        "-codec:a", "aac", out], capture_output=True, text=True,
                       timeout=300)
    if r.returncode != 0 or not os.path.isfile(out):
        return None
    return out
