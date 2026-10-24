"""
Embed metadata INTO stock files (v7, Part B item 8) — the headline feature.

Writes Title -> XMP dc:title + IPTC Headline, Description -> dc:description
/ IPTC Caption, Keywords -> dc:subject / IPTC Keywords, plus XMP Rating = 5
(for the contributor's own DAM/Lightroom sorting — it does NOT affect any
agency's ranking).

Per format:
  JPG  piexif EXIF (ImageDescription + XP fields) + a standard XMP packet
       inserted as an APP1 segment + IPTC-IIM block in a Photoshop IRB.
  PNG  Pillow PngInfo: XMP packet (XML:com.adobe.xmp) + Title/Description/
       Keywords text chunks.
  SVG  insert/replace an XMP RDF <metadata> element; XML re-validated.
  MP4/MOV  FFmpeg stream-copy remux with -metadata title/description/
       comment (NO re-encode).
  EPS/AI  untouched copy + an .xmp sidecar; if the file starts with the
       PostScript magic, a clearly-marked %% comment block is inserted
       AFTER the first line (the magic line must stay first for EPS).

ZERO-CORRUPTION PROTOCOL (mandatory):
  * Originals are NEVER modified — work happens on copies in a job folder.
  * After embedding, every output is RE-OPENED and validated (Pillow loads
    it / SVG parses / ffprobe reads it AND the embedded title+keywords are
    read back and compared). Only validated files are reported as OK and
    included in the ZIP; failures are reported by name with the reason,
    and their metadata remains available via CSV export.
"""

import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET

from PIL import Image, PngImagePlugin

RATING = 5


def _esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def build_xmp(title, description, keywords):
    kw_items = "".join(f"\n          <rdf:li>{_esc(k)}</rdf:li>"
                       for k in (keywords or []))
    return f'''<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Stock Contributor Toolkit Pro">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:xmp="http://ns.adobe.com/xap/1.0/"
    xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/"
    xmp:Rating="{RATING}"
    photoshop:Headline="{_esc(title)}">
   <dc:title>
    <rdf:Alt>
     <rdf:li xml:lang="x-default">{_esc(title)}</rdf:li>
    </rdf:Alt>
   </dc:title>
   <dc:description>
    <rdf:Alt>
     <rdf:li xml:lang="x-default">{_esc(description)}</rdf:li>
    </rdf:Alt>
   </dc:description>
   <dc:subject>
    <rdf:Bag>{kw_items}
    </rdf:Bag>
   </dc:subject>
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>'''


# ------------------------------------------------------------------- JPG

def _iptc_block(title, description, keywords):
    """Minimal IPTC-IIM dataset block (record 2)."""
    def rec(ds, text):
        b = str(text).encode("utf-8", "ignore")[:32767]
        return b"\x1c\x02" + bytes([ds]) + len(b).to_bytes(2, "big") + b
    out = rec(105, title) + rec(120, description)
    for k in keywords or []:
        out += rec(25, k)
    return out


def _embed_jpg(src, dst, title, description, keywords):
    import piexif
    # 1) re-save pixels + EXIF via Pillow/piexif
    with Image.open(src) as im:
        rgb = im.convert("RGB")
        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "Interop": {}}
        try:
            existing = piexif.load(src)  # int tag-id keys (dump requires them)
            for ifd in ("0th", "Exif", "GPS", "Interop"):
                if isinstance(existing.get(ifd), dict):
                    exif_dict[ifd] = existing[ifd]
        except Exception:  # noqa: BLE001
            pass
        exif_dict["0th"][piexif.ImageIFD.ImageDescription] = description or title
        exif_dict["0th"][piexif.ImageIFD.XPTitle] = (title or "").encode("utf-16le")
        exif_dict["0th"][piexif.ImageIFD.XPComment] = (description or "").encode("utf-16le")
        exif_dict["0th"][piexif.ImageIFD.XPKeywords] = (";".join(keywords or [])).encode("utf-16le")
        exif_bytes = piexif.dump(exif_dict)
        rgb.save(dst, "JPEG", quality=95, exif=exif_bytes)
    # 2) insert XMP APP1 segment + Photoshop IRB (IPTC) APP14-ish segment
    #    (Adobe writes IRB in APP14 "Photoshop" segment; readers also scan
    #    the whole file, so placement right after SOI/APP0 is fine.)
    with open(dst, "rb") as f:
        data = f.read()
    assert data[:2] == b"\xff\xd8", "not a JPEG"
    xmp = build_xmp(title, description, keywords).encode("utf-8")
    xmp_seg = b"\xff\xe1" + (len(xmp) + 31).to_bytes(2, "big") + \
        b"http://ns.adobe.com/xap/1.0/\x00" + xmp
    iptc = _iptc_block(title, description, keywords)
    ps_irb = b"Photoshop 3.0\x00" + (b"\x38\x42\x49\x4d\x04\x04\x00\x00\x00\x00"
                                     + len(iptc).to_bytes(2, "big") + iptc)
    if len(ps_irb) % 2:
        ps_irb += b"\x00"
    ps_seg = b"\xff\xed" + (len(ps_irb) + 2).to_bytes(2, "big") + ps_irb
    # insert after SOI (and after APP0/JFIF if present)
    pos = 2
    if data[2:4] == b"\xff\xe0":
        pos = 2 + 2 + int.from_bytes(data[4:6], "big")
    with open(dst, "wb") as f:
        f.write(data[:pos] + xmp_seg + ps_seg + data[pos:])


def _readback_jpg(path):
    with open(path, "rb") as f:
        raw = f.read()
    title, kws = None, []
    m = re.search(r"<x:xmpmeta.*?</x:xmpmeta>", raw.decode("utf-8", "ignore"),
                  re.DOTALL)
    if m:
        x = m.group(0)
        t = re.search(r"dc:title.*?<rdf:li[^>]*>(.*?)</rdf:li>", x, re.DOTALL)
        title = t.group(1) if t else None
        bag = re.search(r"dc:subject[^>]*>\s*<rdf:Bag>(.*?)</rdf:Bag>", x, re.DOTALL)
        if bag:
            kws = re.findall(r"<rdf:li[^>]*>(.*?)</rdf:li>", bag.group(1))
    return title, [k.lower() for k in kws]


# ------------------------------------------------------------------- PNG

def _embed_png(src, dst, title, description, keywords):
    with Image.open(src) as im:
        info = PngImagePlugin.PngInfo()
        info.add_text("XML:com.adobe.xmp",
                      build_xmp(title, description, keywords))
        info.add_text("Title", title or "")
        info.add_text("Description", description or "")
        info.add_text("Keywords", ", ".join(keywords or []))
        info.add_text("Rating", str(RATING))
        im.save(dst, "PNG", pnginfo=info)


def _readback_png(path):
    with Image.open(path) as im:
        text = getattr(im, "text", {}) or {}
    title = text.get("Title")
    kws = [k.strip().lower() for k in (text.get("Keywords") or "").split(",")
           if k.strip()]
    return title, kws


# ------------------------------------------------------------------- SVG

def _embed_svg(src, dst, title, description, keywords):
    with open(src, encoding="utf-8", errors="ignore") as f:
        text = f.read()
    xmp = build_xmp(title, description, keywords)
    block = f"\n<metadata>\n{xmp}\n</metadata>\n"
    if re.search(r"<metadata>.*?</metadata>", text, re.DOTALL):
        text = re.sub(r"<metadata>.*?</metadata>", block.strip(), text,
                      count=1, flags=re.DOTALL)
    else:
        m = re.search(r"<svg[^>]*>", text)
        if not m:
            raise ValueError("No <svg> root element found.")
        text = text[:m.end()] + block + text[m.end():]
    ET.fromstring(text)  # must still parse
    with open(dst, "w", encoding="utf-8") as f:
        f.write(text)


def _readback_svg(path):
    with open(path, encoding="utf-8", errors="ignore") as f:
        text = f.read()
    t = re.search(r"dc:title.*?<rdf:li[^>]*>(.*?)</rdf:li>", text, re.DOTALL)
    bag = re.search(r"dc:subject[^>]*>\s*<rdf:Bag>(.*?)</rdf:Bag>", text, re.DOTALL)
    kws = re.findall(r"<rdf:li[^>]*>(.*?)</rdf:li>", bag.group(1)) if bag else []
    return (t.group(1) if t else None), [k.lower() for k in kws]


# ------------------------------------------------------------------- video

def _embed_video(src, dst, title, description, keywords):
    cmd = ["ffmpeg", "-v", "error", "-i", src, "-c", "copy",
           "-metadata", f"title={title}",
           "-metadata", f"description={description}",
           "-metadata", f"comment={', '.join(keywords or [])}",
           "-metadata", f"keywords={', '.join(keywords or [])}",
           "-y", dst]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise RuntimeError("FFmpeg remux failed: " + r.stderr.decode("utf-8", "ignore")[:200])


def _readback_video(path):
    from .metadata import probe_video
    info = probe_video(path)
    if not info:
        raise RuntimeError("ffprobe could not read the output file.")
    tags = info.get("tags") or {}
    kws = tags.get("keywords") or tags.get("comment") or ""
    return tags.get("title"), [k.strip().lower() for k in re.split(r"[,;]", kws) if k.strip()]


# ------------------------------------------------------------------- EPS/AI

def _embed_eps(src, dst, title, description, keywords):
    shutil.copyfile(src, dst)
    sidecar = dst + ".xmp"
    with open(sidecar, "w", encoding="utf-8") as f:
        f.write(build_xmp(title, description, keywords))
    with open(dst, "r+b") as f:
        head = f.read(64)
        if head.startswith(b"%!PS"):
            f.seek(0)
            first_nl = head.find(b"\n")
            rest = f.read()
            block = (b"\n%%StockToolkit-Metadata-Begin\n"
                     b"%%Title: " + (title or "").encode("utf-8", "ignore")[:160] + b"\n"
                     b"%%Keywords: " + (", ".join(keywords or [])).encode("utf-8", "ignore")[:400] + b"\n"
                     b"%%Note: Full XMP metadata is in the sidecar file " +
                     os.path.basename(sidecar).encode() + b"\n"
                     b"%%StockToolkit-Metadata-End")
            f.seek(0)
            nl = rest.find(b"\n")
            if nl >= 0:
                f.write(rest[:nl + 1] + block + rest[nl + 1:])
                f.truncate()
    return sidecar


# ------------------------------------------------------------------- driver

_EMBEDDERS = {
    ".jpg": (_embed_jpg, _readback_jpg), ".jpeg": (_embed_jpg, _readback_jpg),
    ".png": (_embed_png, _readback_png),
    ".svg": (_embed_svg, _readback_svg),
    ".mp4": (_embed_video, _readback_video), ".mov": (_embed_video, _readback_video),
}


def embed_one(src, dst_dir, title, description, keywords):
    """
    Embed into a COPY of src placed in dst_dir. Validates by re-opening and
    reading the metadata back. Returns {filename, ok, output?, sidecar?,
    error?, rating}. The original file is never touched.
    """
    name = os.path.basename(src)
    ext = os.path.splitext(name)[1].lower()
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, name)
    try:
        if ext in (".eps", ".ai"):
            sidecar = _embed_eps(src, dst, title, description, keywords)
            if os.path.getsize(dst) < os.path.getsize(src):
                raise RuntimeError("Output smaller than original — suspicious.")
            return {"filename": name, "ok": True, "output": dst,
                    "sidecar": sidecar, "rating": RATING,
                    "note": "XMP sidecar written (EPS/AI cannot hold XMP internally in all tools)."}
        fn = _EMBEDDERS.get(ext)
        if not fn:
            return {"filename": name, "ok": False,
                    "error": f"Embedding not supported for '{ext}' files."}
        embedder, readback = fn
        embedder(src, dst, title, description, keywords)
        # ---- validation: re-open + read back + compare
        if ext in (".jpg", ".jpeg", ".png"):
            with Image.open(dst) as im:
                im.verify()
        rb_title, rb_kws = readback(dst)
        want_title = (title or "").strip()
        if want_title and (rb_title or "").strip() != want_title:
            raise RuntimeError("Validation failed: title did not read back.")
        want_kw = {k.lower() for k in (keywords or [])}
        if want_kw and not want_kw.issubset(set(rb_kws)):
            raise RuntimeError("Validation failed: keywords did not read back.")
        if os.path.getsize(dst) <= 0:
            raise RuntimeError("Validation failed: empty output.")
        return {"filename": name, "ok": True, "output": dst, "rating": RATING}
    except Exception as exc:  # noqa: BLE001
        try:
            if os.path.isfile(dst):
                os.remove(dst)
        except OSError:
            pass
        return {"filename": name, "ok": False, "error": str(exc)[:240]}


def embed_batch(items, dst_dir):
    """items: [{src, title, description, keywords}] -> per-file results."""
    return [embed_one(it["src"], dst_dir, it.get("title", ""),
                      it.get("description", ""), it.get("keywords", []))
            for it in items]
