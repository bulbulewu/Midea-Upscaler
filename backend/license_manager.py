"""
License and System Administration Manager
Media Toolkit Pro — Commercial Edition
Made By Munajat International

Provides:
- Cryptographic license key generation & verification
- User management and role-based policies
- Daily usage tracking and hardware lock binding
- Backup & restore of database state
- Agency platform settings persistence
"""

import json
import os
import random
import string
import time
import uuid
import hashlib
from datetime import datetime, timedelta, timezone

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_FILE = os.path.join(DATA_DIR, "system_store.json")


def _generate_key_string(tier="PRO"):
    chars = string.ascii_uppercase + string.digits
    chars = chars.replace("O", "").replace("0", "").replace("I", "").replace("1", "")  # Remove ambiguous chars
    part1 = "".join(random.choices(chars, k=4))
    part2 = "".join(random.choices(chars, k=4))
    part3 = "".join(random.choices(chars, k=4))
    return f"MTK-{tier}-{part1}-{part2}-{part3}"


DEFAULT_POLICIES = {
    "default_access_period_days": 30,
    "default_daily_limit": 50,
    "enforce_single_device": True,
    "watermark_unlicensed": False,
    "allow_offline_validation": True,
    "max_video_duration_sec": 120,
    "master_admin_email": "ahmeddesignhouse@gmail.com",
    "studio_currency": "USD",
}

DEFAULT_USERS = [
    {
        "id": "usr_master_admin",
        "email": "ahmeddesignhouse@gmail.com",
        "name": "Ahmed Design House (Master Admin)",
        "role": "Master Admin",
        "status": "Active",
        "created_date": "2026-01-01",
        "license_key": "MTK-MASTER-ADMIN-LIFETIME-KEY",
        "license_period_days": 3650,
        "daily_limit": 9999,
        "used_today": 0,
        "last_active": "2026-10-24",
        "hwid": "HWID-PRIMARY-ADMIN-PC",
    }
]

DEFAULT_AGENCY_SETTINGS = {
    "adobe_stock": {
        "name": "Adobe Stock",
        "csv_delimiter": ",",
        "last_verified": "03/15/2026",
        "title_min_chars": 15,
        "title_max_chars": 200,
        "title_min_words": 5,
        "keyword_min": 35,
        "keyword_max": 49,
        "ai_disclosure_mandatory": True,
        "ai_disclosure_text": "Mark 'Created using generative AI tools' toggle during upload. If realistic people/places, releases or editorial flags are required.",
        "special_notes": "First 10 keywords are strictly weighted in Adobe Stock search algorithm. Max 49 keywords.",
    },
    "shutterstock": {
        "name": "Shutterstock",
        "csv_delimiter": ",",
        "last_verified": "03/10/2026",
        "title_min_chars": 10,
        "title_max_chars": 200,
        "title_min_words": 3,
        "keyword_min": 25,
        "keyword_max": 50,
        "ai_disclosure_mandatory": True,
        "ai_disclosure_text": "AI-generated content must have the AI checkbox flagged upon submission. Realism guidelines apply.",
        "special_notes": "Requires at least 4.0 Megapixels for all raster images. Video frame rates must match standard CFR rates (23.98, 24, 25, 29.97, 30, 50, 60 fps).",
    },
    "freepik": {
        "name": "Freepik Studio",
        "csv_delimiter": ";",
        "last_verified": "03/18/2026",
        "title_min_chars": 5,
        "title_max_chars": 100,
        "title_min_words": 3,
        "keyword_min": 10,
        "keyword_max": 30,
        "ai_disclosure_mandatory": True,
        "ai_disclosure_text": "Categorize as 'Created with Artificial Intelligence' in contributor dashboard.",
        "special_notes": "Layered PSD files require neat organization and unlocked artwork layers. Minimum 300 DPI print canvas.",
    },
    "getty_istock": {
        "name": "Getty Images / iStock",
        "csv_delimiter": ",",
        "last_verified": "03/01/2026",
        "title_min_chars": 10,
        "title_max_chars": 250,
        "title_min_words": 4,
        "keyword_min": 15,
        "keyword_max": 50,
        "ai_disclosure_mandatory": False,
        "ai_disclosure_text": "Getty Images prohibits purely synthetic AI imagery in creative stock collection without pre-authorization.",
        "special_notes": "Supports Apple ProRes 422 HQ broadcast master clips. Strict Rec.709 color space tagging.",
    },
    "pond5": {
        "name": "Pond5 Broadcast",
        "csv_delimiter": ",",
        "last_verified": "03/05/2026",
        "title_min_chars": 5,
        "title_max_chars": 150,
        "title_min_words": 2,
        "keyword_min": 15,
        "keyword_max": 50,
        "ai_disclosure_mandatory": True,
        "ai_disclosure_text": "Tag AI footage clearly in description notes.",
        "special_notes": "Preferred codec is Apple ProRes 422 or H.264 high-profile MP4. Pristine frame rate accuracy.",
    },
    "vecteezy": {
        "name": "Vecteezy",
        "csv_delimiter": ",",
        "last_verified": "03/12/2026",
        "title_min_chars": 5,
        "title_max_chars": 100,
        "title_min_words": 3,
        "keyword_min": 10,
        "keyword_max": 35,
        "ai_disclosure_mandatory": True,
        "ai_disclosure_text": "Specify AI generator in metadata.",
        "special_notes": "PSD and vector templates must include layered components.",
    },
    "alamy": {
        "name": "Alamy",
        "csv_delimiter": ",",
        "last_verified": "02/28/2026",
        "title_min_chars": 10,
        "title_max_chars": 200,
        "title_min_words": 4,
        "keyword_min": 10,
        "keyword_max": 40,
        "ai_disclosure_mandatory": True,
        "ai_disclosure_text": "Label synthetic imagery as AI generated in caption tags.",
        "special_notes": "High quality standards. Full uncompressed JPEG/TIFF preferred.",
    },
    "depositphotos": {
        "name": "Depositphotos",
        "csv_delimiter": ",",
        "last_verified": "03/08/2026",
        "title_min_chars": 8,
        "title_max_chars": 150,
        "title_min_words": 3,
        "keyword_min": 15,
        "keyword_max": 50,
        "ai_disclosure_mandatory": True,
        "ai_disclosure_text": "AI checkbox required upon submission.",
        "special_notes": "Strict quality filtering against upscaling blur and artifacts.",
    },
}

DEFAULT_STUDIO_SETTINGS = {
    "theme": "dark_studio",
    "language": "en",
    "default_codec": "h264",
    "hardware_acceleration": "auto",
    "threading_mode": "max",
    "auto_denoise_default": True,
    "force_300_dpi": True,
    "auto_open_output_folder": False,
    "temp_cache_retention_hours": 24,
    "view_mode": "grid",
}


class LicenseManager:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self._ensure_db()

    def _ensure_db(self):
        if not os.path.exists(DB_FILE):
            initial_data = {
                "version": "3.0.0",
                "keys": [],
                "users": DEFAULT_USERS,
                "policies": DEFAULT_POLICIES,
                "agency_settings": DEFAULT_AGENCY_SETTINGS,
                "studio_settings": DEFAULT_STUDIO_SETTINGS,
                "active_session": {
                    "logged_in": True,
                    "user_email": "ahmeddesignhouse@gmail.com",
                    "role": "Master Admin",
                    "license_tier": "Master Lifetime Pro",
                    "expires_at": "2036-01-01",
                    "daily_limit": "Unlimited",
                },
            }
            self._write_db(initial_data)

    def _read_db(self):
        self._ensure_db()
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {
                "version": "3.0.0",
                "keys": [],
                "users": DEFAULT_USERS,
                "policies": DEFAULT_POLICIES,
                "agency_settings": DEFAULT_AGENCY_SETTINGS,
                "studio_settings": DEFAULT_STUDIO_SETTINGS,
                "active_session": {
                    "logged_in": True,
                    "user_email": "ahmeddesignhouse@gmail.com",
                    "role": "Master Admin",
                },
            }

    def _write_db(self, data):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ---------------- License Keys ----------------
    def generate_license_key(self, email, period_days=30, daily_limit=50, note=""):
        email = email.strip().lower()
        if not email:
            raise ValueError("User Email ID is required.")

        db = self._read_db()
        key_str = _generate_key_string(tier="PRO")

        # ensure unique
        existing_keys = {k["key"] for k in db.get("keys", [])}
        while key_str in existing_keys:
            key_str = _generate_key_string(tier="PRO")

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

        new_key = {
            "id": uuid.uuid4().hex[:8],
            "key": key_str,
            "assigned_email": email,
            "period_days": int(period_days),
            "daily_limit": "Unlimited" if str(daily_limit).lower() in ("unlimited", "-1") else int(daily_limit),
            "status": "Active",  # Active, Used, Revoked, Expired
            "created_date": now_str,
            "activated_at": None,
            "activated_hwid": None,
            "note": note.strip(),
        }

        db.setdefault("keys", []).insert(0, new_key)

        # Check if user already in users list, if not add as pending/registered user
        user_emails = {u["email"].lower() for u in db.get("users", [])}
        if email not in user_emails:
            db.setdefault("users", []).append({
                "id": "usr_" + uuid.uuid4().hex[:6],
                "email": email,
                "name": email.split("@")[0].capitalize(),
                "role": "Pro Contributor",
                "status": "Active",
                "created_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "license_key": key_str,
                "license_period_days": int(period_days),
                "daily_limit": new_key["daily_limit"],
                "used_today": 0,
                "last_active": "Not Activated",
                "hwid": None,
            })

        self._write_db(db)
        return new_key

    def get_license_keys(self, filter_status="All", search_query=""):
        db = self._read_db()
        keys = db.get("keys", [])

        if filter_status and filter_status != "All":
            keys = [k for k in keys if k["status"].lower() == filter_status.lower()]

        if search_query:
            sq = search_query.strip().lower()
            keys = [
                k for k in keys
                if sq in k["key"].lower() or sq in k["assigned_email"].lower() or sq in (k.get("note") or "").lower()
            ]

        return keys

    def revoke_license_key(self, key_str):
        db = self._read_db()
        found = False
        for k in db.get("keys", []):
            if k["key"] == key_str:
                k["status"] = "Revoked" if k["status"] != "Revoked" else "Active"
                found = True
                break
        if found:
            self._write_db(db)
        return found

    def delete_license_key(self, key_str):
        db = self._read_db()
        keys = [k for k in db.get("keys", []) if k["key"] != key_str]
        db["keys"] = keys
        self._write_db(db)
        return True

    def activate_key(self, key_str, user_email, hwid="PC-LOCAL-ID"):
        key_str = key_str.strip().upper()
        user_email = user_email.strip().lower()

        db = self._read_db()
        key_obj = None
        for k in db.get("keys", []):
            if k["key"].upper() == key_str:
                key_obj = k
                break

        # Check master admin lifetime key
        if key_str == "MTK-MASTER-ADMIN-LIFETIME-KEY":
            session = {
                "logged_in": True,
                "user_email": user_email,
                "role": "Master Admin",
                "license_tier": "Master Lifetime Commercial",
                "expires_at": "2036-01-01",
                "daily_limit": "Unlimited",
            }
            db["active_session"] = session
            self._write_db(db)
            return {"success": True, "message": "Master Admin Lifetime License Activated!", "session": session}

        if not key_obj:
            return {"success": False, "message": "Invalid license key. Please check and try again."}

        if key_obj["status"] == "Revoked":
            return {"success": False, "message": "This license key has been revoked by the administrator."}

        if key_obj["assigned_email"] and key_obj["assigned_email"].lower() != user_email:
            return {
                "success": False,
                "message": f"This key is specifically assigned to {key_obj['assigned_email']}. It cannot be activated with {user_email}.",
            }

        # Activate the key
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=key_obj["period_days"])
        key_obj["status"] = "Used"
        key_obj["activated_at"] = now.strftime("%Y-%m-%d %H:%M")
        key_obj["activated_hwid"] = hwid

        # Update or create user
        found_user = False
        for u in db.get("users", []):
            if u["email"].lower() == user_email:
                u["license_key"] = key_str
                u["license_period_days"] = key_obj["period_days"]
                u["daily_limit"] = key_obj["daily_limit"]
                u["status"] = "Active"
                u["last_active"] = now.strftime("%Y-%m-%d")
                u["hwid"] = hwid
                found_user = True
                break

        if not found_user:
            db.setdefault("users", []).append({
                "id": "usr_" + uuid.uuid4().hex[:6],
                "email": user_email,
                "name": user_email.split("@")[0].capitalize(),
                "role": "Pro Contributor",
                "status": "Active",
                "created_date": now.strftime("%Y-%m-%d"),
                "license_key": key_str,
                "license_period_days": key_obj["period_days"],
                "daily_limit": key_obj["daily_limit"],
                "used_today": 0,
                "last_active": now.strftime("%Y-%m-%d"),
                "hwid": hwid,
            })

        session = {
            "logged_in": True,
            "user_email": user_email,
            "role": "Pro Contributor",
            "license_tier": f"Pro Contributor ({key_obj['period_days']} Days)",
            "expires_at": expires.strftime("%Y-%m-%d"),
            "daily_limit": str(key_obj["daily_limit"]),
        }
        db["active_session"] = session
        self._write_db(db)
        return {"success": True, "message": "License Key Successfully Activated!", "session": session}

    # ---------------- Users ----------------
    def get_users(self):
        db = self._read_db()
        return db.get("users", [])

    def add_user(self, email, name="", role="Pro Contributor", daily_limit=50):
        email = email.strip().lower()
        if not email:
            raise ValueError("Email is required.")
        db = self._read_db()
        for u in db.get("users", []):
            if u["email"].lower() == email:
                raise ValueError("User with this email already exists.")

        new_user = {
            "id": "usr_" + uuid.uuid4().hex[:6],
            "email": email,
            "name": name or email.split("@")[0].capitalize(),
            "role": role,
            "status": "Active",
            "created_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "license_key": "Pending",
            "license_period_days": 30,
            "daily_limit": daily_limit,
            "used_today": 0,
            "last_active": "Never",
            "hwid": None,
        }
        db.setdefault("users", []).append(new_user)
        self._write_db(db)
        return new_user

    def update_user_status(self, user_id, status):
        db = self._read_db()
        for u in db.get("users", []):
            if u["id"] == user_id or u["email"].lower() == user_id.lower():
                u["status"] = status
                break
        self._write_db(db)
        return True

    def edit_user(self, user_id, updates):
        db = self._read_db()
        target = None
        for u in db.get("users", []):
            if u["id"] == user_id or u["email"].lower() == user_id.lower():
                target = u
                break
        if not target:
            raise ValueError(f"User {user_id} not found.")

        if "name" in updates:
            target["name"] = updates["name"].strip()
        if "role" in updates:
            target["role"] = updates["role"].strip()
        if "daily_limit" in updates:
            target["daily_limit"] = updates["daily_limit"]
        if "license_period_days" in updates:
            target["license_period_days"] = int(updates["license_period_days"])
        if "status" in updates:
            target["status"] = updates["status"]
        if "notes" in updates:
            target["notes"] = updates["notes"]

        self._write_db(db)
        return target

    def delete_user(self, user_id):
        db = self._read_db()
        users = [u for u in db.get("users", []) if u["id"] != user_id and u["email"].lower() != user_id.lower()]
        db["users"] = users
        self._write_db(db)
        return True

    def export_users_csv(self):
        db = self._read_db()
        users = db.get("users", [])
        lines = ["Email,Name,Role,Status,LicenseKey,PeriodDays,DailyLimit,RegisteredDate,DeviceHWID"]
        for u in users:
            lines.append(
                f'"{u.get("email","")}","{u.get("name","")}","{u.get("role","")}","{u.get("status","")}","{u.get("license_key","")}","{u.get("license_period_days","")}","{u.get("daily_limit","")}","{u.get("created_date","")}","{u.get("hwid","Unlocked")}"'
            )
        return "\n".join(lines)

    def get_storage_stats(self, upload_dir, output_dir):
        db = self._read_db()
        
        def _dir_stats(path):
            count, size = 0, 0
            if os.path.exists(path):
                for root, _, files in os.walk(path):
                    for f in files:
                        p = os.path.join(root, f)
                        try:
                            size += os.path.getsize(p)
                            count += 1
                        except OSError:
                            pass
            return count, round(size / (1024 * 1024), 2)

        up_cnt, up_mb = _dir_stats(upload_dir)
        out_cnt, out_mb = _dir_stats(output_dir)

        keys = db.get("keys", [])
        users = db.get("users", [])

        return {
            "uploads_count": up_cnt,
            "uploads_size_mb": up_mb,
            "outputs_count": out_cnt,
            "outputs_size_mb": out_mb,
            "total_disk_mb": round(up_mb + out_mb, 2),
            "total_keys": len(keys),
            "active_unclaimed_keys": sum(1 for k in keys if k["status"] == "Active"),
            "used_keys": sum(1 for k in keys if k["status"] == "Used"),
            "total_users": len(users),
            "active_users": sum(1 for u in users if u["status"] == "Active"),
        }

    def purge_cache(self, upload_dir, output_dir):
        removed_count = 0
        for d in (upload_dir, output_dir):
            if os.path.exists(d):
                for f in os.listdir(d):
                    p = os.path.join(d, f)
                    if os.path.isfile(p):
                        try:
                            os.remove(p)
                            removed_count += 1
                        except OSError:
                            pass
        return removed_count

    def factory_reset(self):
        initial_data = {
            "version": "3.0.0",
            "keys": [],
            "users": DEFAULT_USERS,
            "policies": DEFAULT_POLICIES,
            "agency_settings": DEFAULT_AGENCY_SETTINGS,
            "studio_settings": DEFAULT_STUDIO_SETTINGS,
            "active_session": {
                "logged_in": True,
                "user_email": "ahmeddesignhouse@gmail.com",
                "role": "Master Admin",
                "license_tier": "Master Lifetime Pro",
                "expires_at": "2036-01-01",
                "daily_limit": "Unlimited",
            },
        }
        self._write_db(initial_data)
        return True

    def reset_user_hwid(self, user_id):
        db = self._read_db()
        for u in db.get("users", []):
            if u["id"] == user_id or u["email"].lower() == user_id.lower():
                u["hwid"] = None
                break
        self._write_db(db)
        return True

    # ---------------- Policies ----------------
    def get_policies(self):
        db = self._read_db()
        return db.get("policies", DEFAULT_POLICIES)

    def save_policies(self, new_policies):
        db = self._read_db()
        policies = db.get("policies", DEFAULT_POLICIES)
        policies.update(new_policies)
        db["policies"] = policies
        self._write_db(db)
        return policies

    # ---------------- Settings ----------------
    def get_agency_settings(self):
        db = self._read_db()
        return db.get("agency_settings", DEFAULT_AGENCY_SETTINGS)

    def save_agency_settings(self, agency_key, settings):
        db = self._read_db()
        agencies = db.setdefault("agency_settings", DEFAULT_AGENCY_SETTINGS)
        agencies[agency_key] = settings
        self._write_db(db)
        return agencies[agency_key]

    def get_studio_settings(self):
        db = self._read_db()
        return db.get("studio_settings", DEFAULT_STUDIO_SETTINGS)

    def save_studio_settings(self, settings):
        db = self._read_db()
        current = db.setdefault("studio_settings", DEFAULT_STUDIO_SETTINGS)
        current.update(settings)
        self._write_db(db)
        return current

    # ---------------- Session & Auth ----------------
    def get_active_session(self):
        db = self._read_db()
        return db.get("active_session", {
            "logged_in": True,
            "user_email": "ahmeddesignhouse@gmail.com",
            "role": "Master Admin",
            "license_tier": "Master Lifetime Pro",
            "expires_at": "2036-01-01",
            "daily_limit": "Unlimited",
        })

    def login(self, email, password_or_pin=""):
        email = email.strip().lower()
        db = self._read_db()

        # Check if master admin
        if email == "ahmeddesignhouse@gmail.com":
            session = {
                "logged_in": True,
                "user_email": email,
                "role": "Master Admin",
                "license_tier": "Master Lifetime Pro",
                "expires_at": "2036-01-01",
                "daily_limit": "Unlimited",
            }
            db["active_session"] = session
            self._write_db(db)
            return {"success": True, "session": session}

        # Check user
        user = next((u for u in db.get("users", []) if u["email"].lower() == email), None)
        if not user:
            return {"success": False, "message": "User not registered. Please contact administrator or activate a license key."}

        session = {
            "logged_in": True,
            "user_email": user["email"],
            "role": user.get("role", "Pro Contributor"),
            "license_tier": f"Pro ({user.get('license_period_days', 30)}d)",
            "expires_at": "Active",
            "daily_limit": str(user.get("daily_limit", 50)),
        }
        db["active_session"] = session
        self._write_db(db)
        return {"success": True, "session": session}

    def logout(self):
        db = self._read_db()
        db["active_session"] = {
            "logged_in": False,
            "user_email": "Guest",
            "role": "Unregistered / Guest",
            "license_tier": "Trial Restricted",
            "expires_at": "Expired",
            "daily_limit": "0",
        }
        self._write_db(db)
        return True

    # ---------------- Backup & Restore ----------------
    def export_backup_json(self):
        return self._read_db()

    def import_backup_json(self, data):
        if not isinstance(data, dict) or "version" not in data:
            raise ValueError("Invalid backup structure. Must contain version and system tables.")
        self._write_db(data)
        return True


# Global singleton instance
license_mgr = LicenseManager()
