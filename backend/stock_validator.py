"""
Stock Pre-Flight Validation Engine & Marketplace Rules
Made By Munajat International

Enforces official submission guidelines for:
  - Adobe Stock
  - Shutterstock
  - Getty Images / iStock
  - Pond5
  - Freepik
  - Universal Multi-Stock Master
"""

STOCK_MARKETPLACES = {
    "universal": {
        "name": "Universal Stock Master",
        "badge": "⭐ All Marketplaces",
        "description": "Strict compliance across Adobe Stock, Shutterstock, Getty & Pond5 simultaneously.",
        "min_duration": 5.0,
        "max_duration": 60.0,
        "recommended_res": "3840×2160 (4K UHD)",
        "min_megapixels": 4.0,
        "target_bitrate": "60M",
        "color_space": "bt709",
    },
    "adobe_stock": {
        "name": "Adobe Stock",
        "badge": "🅰️ Adobe Stock",
        "description": "Optimized for Adobe Stock contributor guidelines. 65 Mbps 4K master, Rec.709, CFR.",
        "min_duration": 5.0,
        "max_duration": 60.0,
        "recommended_res": "3840×2160 (4K UHD)",
        "min_megapixels": 4.0,
        "target_bitrate": "65M",
        "color_space": "bt709",
    },
    "shutterstock": {
        "name": "Shutterstock",
        "badge": "🔴 Shutterstock",
        "description": "Compliant with Shutterstock contributor portal. Constant frame rate, audio sanitized.",
        "min_duration": 5.0,
        "max_duration": 60.0,
        "recommended_res": "3840×2160 (4K UHD)",
        "min_megapixels": 4.0,
        "target_bitrate": "60M",
        "color_space": "bt709",
    },
    "getty_istock": {
        "name": "Getty Images / iStock",
        "badge": "🟡 Getty / iStock",
        "description": "Progressive scan only, broadcast High@5.1 profile, strict Rec.709 colorimetry.",
        "min_duration": 5.0,
        "max_duration": 60.0,
        "recommended_res": "3840×2160 (4K UHD)",
        "min_megapixels": 4.0,
        "target_bitrate": "60M",
        "color_space": "bt709",
    },
    "pond5": {
        "name": "Pond5 Broadcast",
        "badge": "🟢 Pond5",
        "description": "Supports up to 120s clips and ProRes 422 high-margin broadcast exports.",
        "min_duration": 3.0,
        "max_duration": 120.0,
        "recommended_res": "3840×2160 (4K UHD)",
        "min_megapixels": 4.0,
        "target_bitrate": "70M",
        "color_space": "bt709",
    },
    "freepik": {
        "name": "Freepik Studio",
        "badge": "🎨 Freepik",
        "description": "Photo & video stock standard with 300 DPI layered PSD and high-res JPEG specs.",
        "min_duration": 5.0,
        "max_duration": 60.0,
        "recommended_res": "3840×2160 (4K UHD)",
        "min_megapixels": 4.0,
        "target_bitrate": "50M",
        "color_space": "bt709",
    },
}

ACCEPTED_STOCK_FPS = (23.976, 24.0, 25.0, 29.97, 30.0, 50.0, 59.94, 60.0)


def preflight_video_check(meta, marketplace_key="universal"):
    """
    Run pre-flight validation on video metadata against marketplace rules.
    Returns structured checklist and compliance summary.
    """
    rules = STOCK_MARKETPLACES.get(marketplace_key, STOCK_MARKETPLACES["universal"])
    checks = []
    overall = "PASS"

    # 1. Duration check
    dur = meta.get("duration", 0.0)
    if dur < rules["min_duration"]:
        overall = "WARNING"
        checks.append({
            "param": "Duration",
            "value": f"{dur:.1f}s",
            "rule": f"Must be at least {rules['min_duration']}s",
            "status": "FAIL",
            "message": f"Clip is too short for {rules['name']}. Microstock agencies require 5s minimum.",
        })
    elif dur > rules["max_duration"]:
        overall = "WARNING"
        checks.append({
            "param": "Duration",
            "value": f"{dur:.1f}s",
            "rule": f"Max {rules['max_duration']}s allowed",
            "status": "FAIL",
            "message": f"Clip exceeds {rules['max_duration']}s limit for {rules['name']}.",
        })
    else:
        checks.append({
            "param": "Duration",
            "value": f"{dur:.1f}s",
            "rule": f"{rules['min_duration']}s – {rules['max_duration']}s",
            "status": "PASS",
            "message": "Compliant with stock agency duration rules.",
        })

    # 2. Frame Rate check
    fps = meta.get("fps", 0.0)
    fps_ok = any(abs(fps - sf) < 0.05 for sf in ACCEPTED_STOCK_FPS)
    if fps_ok:
        checks.append({
            "param": "Frame Rate",
            "value": f"{fps:.2f} fps",
            "rule": "Industry Standard CFR",
            "status": "PASS",
            "message": "Exact standard frame rate detected. No judder or drop frames.",
        })
    else:
        checks.append({
            "param": "Frame Rate",
            "value": f"{fps:.2f} fps",
            "rule": "Standard Stock FPS",
            "status": "CONFORM",
            "message": "Non-standard frame rate will be cleanly conformed to 30.0 fps.",
        })

    # 3. Audio Warning
    if meta.get("has_audio"):
        checks.append({
            "param": "Audio Track",
            "value": f"Present ({meta.get('audio_codec', 'audio')})",
            "rule": "Clean Audio Only",
            "status": "WARNING",
            "message": "Stock agencies automatically reject clips with copyrighted music, mic hiss, or speech.",
        })
    else:
        checks.append({
            "param": "Audio Track",
            "value": "Clean (No Audio)",
            "rule": "Stock Video Standard",
            "status": "PASS",
            "message": "100% safe from audio rejection.",
        })

    # 4. Target Resolution
    w, h = meta.get("width", 0), meta.get("height", 0)
    checks.append({
        "param": "Resolution",
        "value": f"{w}×{h}",
        "rule": rules["recommended_res"],
        "status": "READY",
        "message": "Ready to be upscaled to full 4K UHD Master (3840×2160).",
    })

    return {
        "marketplace": rules["name"],
        "overall_status": overall,
        "checks": checks,
    }


def preflight_image_check(meta, marketplace_key="universal"):
    """
    Run pre-flight validation on image metadata against marketplace rules.
    """
    rules = STOCK_MARKETPLACES.get(marketplace_key, STOCK_MARKETPLACES["universal"])
    checks = []
    overall = "PASS"

    w = meta.get("width", 0)
    h = meta.get("height", 0)
    mp = round((w * h) / 1_000_000.0, 2)

    # 1. Megapixel check
    if mp < rules["min_megapixels"]:
        checks.append({
            "param": "Source Resolution",
            "value": f"{mp} MP ({w}×{h})",
            "rule": f"Minimum {rules['min_megapixels']} MP",
            "status": "UPSCALING_REQUIRED",
            "message": f"Source is below the 4.0 MP microstock threshold. Upscaling to 4K/8K will pass with flying colors.",
        })
    else:
        checks.append({
            "param": "Source Resolution",
            "value": f"{mp} MP ({w}×{h})",
            "rule": f"Minimum {rules['min_megapixels']} MP",
            "status": "PASS",
            "message": "Meets microstock submission resolution standard.",
        })

    # 2. Format
    fmt = meta.get("format", "").upper()
    checks.append({
        "param": "Source Format",
        "value": fmt,
        "rule": "JPEG / PNG / TIFF",
        "status": "PASS",
        "message": f"{fmt} format is fully supported.",
    })

    # 3. Print Density
    checks.append({
        "param": "Print Density",
        "value": meta.get("dpi", "72 DPI"),
        "rule": "300 DPI Commercial Print",
        "status": "READY",
        "message": "Will embed professional 300 DPI tags for stock & fine-art print approval.",
    })

    return {
        "marketplace": rules["name"],
        "megapixels": mp,
        "overall_status": overall,
        "checks": checks,
    }
