"""
AI Stock Rejection Inspector Module
Evaluates images and media thumbnails for microstock pre-submission compliance:
- Trademark & Logo Detection (Apple, Nike, car emblems, branded clothing, tech)
- Recognizable Human Faces & Model Release requirements
- Copyrighted Architecture, Modern Monuments & Property Release requirements
- Actionable commercial stock remediation advice for Adobe Stock, Shutterstock, Freepik
"""

import os
import json
import base64
import mimetypes
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

DEFAULT_GEMINI_MODEL = "gemini-1.5-flash"
API_STORE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "ai_config.json")


def load_ai_config() -> Dict[str, Any]:
    """Load saved AI API configuration."""
    os.makedirs(os.path.dirname(API_STORE_PATH), exist_ok=True)
    if os.path.exists(API_STORE_PATH):
        try:
            with open(API_STORE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # Fallback to environment variable if present
    env_gemini = os.environ.get("GEMINI_API_KEY", "")
    return {
        "gemini_api_key": env_gemini,
        "grok_api_key": os.environ.get("GROK_API_KEY", ""),
        "provider": "gemini",
        "model": DEFAULT_GEMINI_MODEL,
        "check_trademarks": True,
        "check_model_release": True,
        "check_property_release": True
    }


def save_ai_config(config: Dict[str, Any]) -> bool:
    """Save AI API configuration to disk."""
    try:
        os.makedirs(os.path.dirname(API_STORE_PATH), exist_ok=True)
        with open(API_STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as exc:
        print(f"[AI Inspector] Failed to save AI config: {exc}")
        return False


def get_masked_key(key: str) -> str:
    """Mask key for safe display in UI."""
    if not key or len(key) < 8:
        return ""
    return key[:4] + "•" * (len(key) - 8) + key[-4:]


def inspect_with_gemini(
    image_path: str,
    api_key: str,
    model: str = "gemini-1.5-flash",
    check_trademarks: bool = True,
    check_model_release: bool = True,
    check_property_release: bool = True,
) -> Dict[str, Any]:
    """
    Inspect an image using Google Gemini Vision API.
    """
    if not api_key or not api_key.strip():
        return {
            "success": False,
            "error": "No Gemini API key provided. Please configure your free Google Gemini API key in Settings.",
            "is_config_needed": True
        }

    if not os.path.exists(image_path):
        return {"success": False, "error": f"Image file not found: {image_path}"}

    # Encode image to base64
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type or not mime_type.startswith("image/"):
        mime_type = "image/jpeg"

    with open(image_path, "rb") as img_file:
        img_b64 = base64.b64encode(img_file.read()).decode("utf-8")

    prompt = (
        "You are an elite commercial microstock compliance inspector for Adobe Stock, Shutterstock, Getty Images, and Freepik.\n"
        "Carefully inspect the provided image for potential commercial stock rejection causes:\n\n"
        f"1. Trademark & Brand Logos (Active: {check_trademarks}): Look for any visible logos, brand names, brand insignias (e.g. Nike swoosh, Apple logo, car manufacturer emblems, tech brands, designer fashion logos, copyrighted characters, recognizable app icons).\n"
        f"2. Recognizable Faces & People (Active: {check_model_release}): Are there any recognizable human faces or identifiable persons (visible facial features, distinctive tattoos, unique silhouettes) requiring a signed commercial Model Release?\n"
        f"3. Copyrighted Architecture & Artwork (Active: {check_property_release}): Are there any copyrighted modern buildings, private estates, modern public sculptures, murals, graffiti, or distinctive private architecture requiring a Property Release?\n"
        "4. Commercial Recommendation: Provide an overall verdict and actionable editing instructions (e.g. 'Clone stamp the small emblem on the sleeve', 'Submit with Model Release', or 'Commercial Ready').\n\n"
        "Return ONLY a valid JSON object with EXACTLY this structure:\n"
        "{\n"
        '  "verdict": "PASS" | "CAUTION" | "REJECT",\n'
        '  "summary": "Short 1-2 sentence commercial readiness summary.",\n'
        '  "trademarks": [\n'
        '    {"name": "Brand Name or Logo", "location": "e.g. Top-left of jacket", "severity": "HIGH|MEDIUM|LOW", "fix": "e.g. Blur or clone-stamp before submitting"}\n'
        '  ],\n'
        '  "model_release_needed": true|false,\n'
        '  "faces_detected": [\n'
        '    {"description": "e.g. Adult female smiling", "requires_release": true|false, "reason": "..."}\n'
        '  ],\n'
        '  "property_release_needed": true|false,\n'
        '  "properties_detected": [\n'
        '    {"description": "e.g. Recognizable modern building facade", "requires_release": true|false, "reason": "..."}\n'
        '  ],\n'
        '  "recommendations": [\n'
        '    "Actionable step 1",\n'
        '    "Actionable step 2"\n'
        '  ]\n'
        "}"
    )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key.strip()}"
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": img_b64
                        }
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "response_mime_type": "application/json"
        }
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            
        candidates = data.get("candidates", [])
        if not candidates:
            return {"success": False, "error": "Gemini API returned no analysis candidates."}
        
        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            return {"success": False, "error": "Empty response from Gemini vision model."}

        text_content = parts[0].get("text", "").strip()
        # Clean potential markdown wrapping
        if text_content.startswith("```json"):
            text_content = text_content[7:]
        elif text_content.startswith("```"):
            text_content = text_content[3:]
        if text_content.endswith("```"):
            text_content = text_content[:-3]
        text_content = text_content.strip()

        parsed = json.loads(text_content)
        parsed["success"] = True
        parsed["provider"] = "Google Gemini"
        parsed["model"] = model
        return parsed

    except urllib.error.HTTPError as http_err:
        err_msg = http_err.read().decode("utf-8", errors="ignore")
        try:
            err_json = json.loads(err_msg)
            api_msg = err_json.get("error", {}).get("message", err_msg)
        except Exception:
            api_msg = err_msg
        return {"success": False, "error": f"Gemini API Error ({http_err.code}): {api_msg}"}
    except Exception as exc:
        return {"success": False, "error": f"Failed to execute AI inspection: {str(exc)}"}


def inspect_with_grok(
    image_path: str,
    api_key: str,
    model: str = "grok-vision-beta",
    check_trademarks: bool = True,
    check_model_release: bool = True,
    check_property_release: bool = True,
) -> Dict[str, Any]:
    """
    Inspect an image using xAI Grok Vision API.
    """
    if not api_key or not api_key.strip():
        return {
            "success": False,
            "error": "No Grok API key provided. Please configure your xAI Grok API key in Settings.",
            "is_config_needed": True
        }

    if not os.path.exists(image_path):
        return {"success": False, "error": f"Image file not found: {image_path}"}

    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type or not mime_type.startswith("image/"):
        mime_type = "image/jpeg"

    with open(image_path, "rb") as img_file:
        img_b64 = base64.b64encode(img_file.read()).decode("utf-8")

    data_url = f"data:{mime_type};base64,{img_b64}"

    prompt = (
        "You are an expert commercial microstock compliance inspector for Adobe Stock, Shutterstock, and Freepik.\n"
        "Inspect the image for: 1. Trademarks/Logos, 2. Recognizable human faces requiring Model Release, 3. Copyrighted Architecture requiring Property Release.\n"
        "Return ONLY a JSON object with: {verdict: 'PASS'|'CAUTION'|'REJECT', summary: string, trademarks: [{name, location, severity, fix}], model_release_needed: bool, faces_detected: [{description, requires_release, reason}], property_release_needed: bool, properties_detected: [{description, requires_release, reason}], recommendations: [string]}"
    )

    url = "https://api.x.ai/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}}
                ]
            }
        ],
        "temperature": 0.1
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key.strip()}"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        
        choices = data.get("choices", [])
        if not choices:
            return {"success": False, "error": "Grok returned no response."}

        text = choices[0].get("message", {}).get("content", "").strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        parsed = json.loads(text.strip())
        parsed["success"] = True
        parsed["provider"] = "xAI Grok"
        parsed["model"] = model
        return parsed
    except Exception as exc:
        return {"success": False, "error": f"Grok API Error: {str(exc)}"}


def inspect_media_for_stock(
    image_path: str,
    custom_api_key: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main dispatch function for AI Stock Rejection Inspection.
    Uses saved configuration if custom_api_key is not supplied.
    """
    config = load_ai_config()
    chosen_provider = provider or config.get("provider", "gemini")
    
    if chosen_provider == "grok":
        key = custom_api_key or config.get("grok_api_key", "")
        chosen_model = model or config.get("model", "grok-vision-beta")
        return inspect_with_grok(
            image_path,
            api_key=key,
            model=chosen_model,
            check_trademarks=config.get("check_trademarks", True),
            check_model_release=config.get("check_model_release", True),
            check_property_release=config.get("check_property_release", True)
        )
    else:
        # Default to Gemini
        key = custom_api_key or config.get("gemini_api_key", "")
        chosen_model = model or config.get("model", DEFAULT_GEMINI_MODEL)
        return inspect_with_gemini(
            image_path,
            api_key=key,
            model=chosen_model,
            check_trademarks=config.get("check_trademarks", True),
            check_model_release=config.get("check_model_release", True),
            check_property_release=config.get("check_property_release", True)
        )
