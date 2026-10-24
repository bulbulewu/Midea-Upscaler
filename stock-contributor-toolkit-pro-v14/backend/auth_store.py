"""
v8 — Local accounts, license keys and usage policy (stdlib only).

Design (owner's local tool, modelled on the reference app's visible flows
but implemented securely and locally):
- Users / license keys / policy / per-day usage counters live in ONE JSON
  file (default: <app>/data/auth_store.json; override with the
  TOOLKIT_AUTH_FILE environment variable — used by the tests).
- Passwords are hashed with hashlib.pbkdf2_hmac (SHA-256, per-user random
  salt, 200k iterations). PLAINTEXT PASSWORDS ARE NEVER STORED, LOGGED OR
  DISPLAYED ANYWHERE. (The reference app showed a master password in its
  login dialog — that behaviour is deliberately NOT copied.)
- If the store file does not exist, the app runs in "not set up" mode:
  no admin exists, and nothing is gated (exactly like v7). The owner
  creates the admin account once from the Sign In dialog.
- Recovery: delete data/auth_store.json (and data/auth_store.json.secret)
  to reset all accounts, keys and counters.
"""

import hashlib
import hmac
import json
import os
import secrets
import threading
from datetime import date, timedelta

_LOCK = threading.Lock()
_PATH = None  # set by configure()

DEFAULT_POLICY = {"trial_days": 7, "trial_daily_limit": 50,
                  "default_license_period": 30}
_KEY_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # unambiguous (no 0/O/1/I)
_PBKDF2_ROUNDS = 200_000


def configure(path):
    global _PATH
    _PATH = path


def store_path():
    if _PATH:
        return _PATH
    env = os.environ.get("TOOLKIT_AUTH_FILE")
    if env:
        return env
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "data", "auth_store.json")


# ------------------------------------------------------------------ storage
def _blank():
    return {"users": {}, "keys": [], "policy": dict(DEFAULT_POLICY)}


def load():
    p = store_path()
    if not os.path.isfile(p):
        return _blank()
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "users" not in data:
            return _blank()
        data.setdefault("keys", [])
        pol = dict(DEFAULT_POLICY)
        pol.update(data.get("policy") or {})
        data["policy"] = pol
        return data
    except Exception:  # noqa: BLE001 — a corrupt store must not kill the app
        return _blank()


def save(data):
    p = store_path()
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, p)


# ---------------------------------------------------------------- passwords
def _hash(password, salt_hex):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                               bytes.fromhex(salt_hex),
                               _PBKDF2_ROUNDS).hex()


def _new_user(email, password, *, is_admin=False, trial_days=0,
              daily_limit=None):
    salt = secrets.token_hex(16)
    today = date.today()
    return {
        "email": email, "salt": salt, "pw_hash": _hash(password, salt),
        "is_admin": bool(is_admin), "active": True,
        "created": today.isoformat(),
        "trial_ends": (today + timedelta(days=trial_days)).isoformat()
                      if trial_days else None,
        "license_ends": None,
        "daily_limit": daily_limit,  # None = unlimited
        "usage": {},                 # {"YYYY-MM-DD": count}
    }


def _verify(user, password):
    return hmac.compare_digest(user.get("pw_hash", ""),
                               _hash(password, user.get("salt", "00")))


# ------------------------------------------------------------------- users
def _norm(email):
    return (email or "").strip().lower()


def setup_needed(data=None):
    data = data if data is not None else load()
    return not any(u.get("is_admin") for u in data["users"].values())


def create_admin(email, password):
    email = _norm(email)
    if not email or "@" not in email:
        return None, "Enter a valid admin email."
    if len(password or "") < 6:
        return None, "Password must be at least 6 characters."
    with _LOCK:
        data = load()
        if not setup_needed(data):
            return None, "An admin account already exists."
        if email in data["users"]:
            return None, "That email is already registered."
        user = _new_user(email, password, is_admin=True)
        data["users"][email] = user
        save(data)
    return public_user(user), None


def register(email, password):
    email = _norm(email)
    if not email or "@" not in email:
        return None, "Enter a valid email address."
    if len(password or "") < 6:
        return None, "Password must be at least 6 characters."
    with _LOCK:
        data = load()
        if email in data["users"]:
            return None, "That email is already registered — sign in instead."
        pol = data["policy"]
        user = _new_user(email, password,
                         trial_days=int(pol.get("trial_days", 7)),
                         daily_limit=pol.get("trial_daily_limit", 50))
        data["users"][email] = user
        save(data)
    return public_user(user), None


def authenticate(email, password):
    email = _norm(email)
    data = load()
    user = data["users"].get(email)
    if not user or not _verify(user, password or ""):
        return None, "Wrong email or password."
    if not user.get("active", True):
        return None, "This account has been deactivated by the admin."
    return public_user(user), None


def get_user(email):
    if not email:
        return None
    return load()["users"].get(_norm(email))


def license_status(user, today=None):
    """-> (status, days_left) where status is admin|licensed|trial|expired|none"""
    if not user:
        return "none", 0
    if user.get("is_admin"):
        return "admin", None
    today = today or date.today()
    for field, name in (("license_ends", "licensed"), ("trial_ends", "trial")):
        end = user.get(field)
        if end:
            try:
                d = date.fromisoformat(end)
            except ValueError:
                continue
            if d >= today:
                return name, (d - today).days
            return "expired", 0
    return "none", 0


def public_user(user, today=None):
    if not user:
        return None
    status, days = license_status(user, today)
    return {"email": user["email"], "is_admin": bool(user.get("is_admin")),
            "active": bool(user.get("active", True)),
            "created": user.get("created"),
            "license_status": status, "days_left": days,
            "trial_ends": user.get("trial_ends"),
            "license_ends": user.get("license_ends"),
            "daily_limit": user.get("daily_limit"),
            "usage_today": (user.get("usage") or {}).get(
                (today or date.today()).isoformat(), 0)}


def list_users():
    data = load()
    return [public_user(u) for u in
            sorted(data["users"].values(), key=lambda u: u.get("created", ""))]


def toggle_user(email, active):
    with _LOCK:
        data = load()
        user = data["users"].get(_norm(email))
        if not user:
            return False
        if user.get("is_admin") and not active:
            return False  # never lock the admin out
        user["active"] = bool(active)
        save(data)
    return True


# -------------------------------------------------------------------- keys
def new_key_code():
    groups = ["".join(secrets.choice(_KEY_CHARS) for _ in range(4))
              for _ in range(3)]
    return "MTK-PRO-" + "-".join(groups)


def generate_key(email, period_days, daily_limit, note=""):
    email = _norm(email)
    if not email or "@" not in email:
        return None, "Enter the user's email — keys are bound to one email."
    rec = {"key": new_key_code(), "email": email,
           "period_days": int(period_days),
           "daily_limit": daily_limit,  # None = unlimited
           "note": note or "", "status": "active",
           "created": date.today().isoformat(),
           "activated_by": None, "activated_at": None}
    with _LOCK:
        data = load()
        while any(k["key"] == rec["key"] for k in data["keys"]):
            rec["key"] = new_key_code()
        data["keys"].append(rec)
        save(data)
    return rec, None


def list_keys():
    return list(reversed(load()["keys"]))


def revoke_key(code):
    with _LOCK:
        data = load()
        for k in data["keys"]:
            if k["key"] == (code or "").strip().upper():
                if k["status"] == "used":
                    return False, "That key is already used and cannot be revoked."
                k["status"] = "revoked"
                save(data)
                return True, "Key revoked."
    return False, "Key not found."


def activate_key(email, code):
    email = _norm(email)
    code = (code or "").strip().upper()
    with _LOCK:
        data = load()
        rec = next((k for k in data["keys"] if k["key"] == code), None)
        if rec is None:
            return False, "License key not found. Check the key and try again."
        if rec["status"] == "revoked":
            return False, "This license key has been revoked by the admin."
        if rec["status"] == "used":
            return False, "This license key has already been used."
        if rec["email"] != email:
            return False, ("This key is assigned to a different email address. "
                           "Keys can only be activated by the user they were "
                           "generated for.")
        user = data["users"].get(email)
        if user is None:
            return False, ("No account with that email exists yet — register "
                           "first, then activate the key.")
        if not user.get("active", True):
            return False, "This account has been deactivated by the admin."
        ends = date.today() + timedelta(days=int(rec["period_days"]))
        user["license_ends"] = ends.isoformat()
        user["daily_limit"] = rec["daily_limit"]
        rec["status"] = "used"
        rec["activated_by"] = email
        rec["activated_at"] = date.today().isoformat()
        save(data)
        pub = public_user(user)
    return True, (f"License activated — full access until "
                  f"{pub['license_ends']}.")


# ------------------------------------------------------------------ policy
def get_policy():
    return dict(load()["policy"])


def set_policy(patch):
    with _LOCK:
        data = load()
        pol = data["policy"]
        for k in DEFAULT_POLICY:
            if k in patch and patch[k] is not None:
                try:
                    pol[k] = int(patch[k])
                except (TypeError, ValueError):
                    pass
        data["policy"] = pol
        save(data)
    return dict(pol)


# -------------------------------------------------------------- backup/rest.
def export_store():
    return load()


def import_store(payload):
    if not isinstance(payload, dict) or not isinstance(
            payload.get("users"), dict) or not isinstance(
            payload.get("keys"), list):
        return False, "That file is not a valid Toolkit backup."
    with _LOCK:
        data = _blank()
        data["users"] = payload["users"]
        data["keys"] = payload["keys"]
        pol = dict(DEFAULT_POLICY)
        pol.update(payload.get("policy") or {})
        data["policy"] = pol
        save(data)
    return True, "Backup restored."


# -------------------------------------------------------------- enforcement
def check_and_count(email):
    """
    Daily-limit gate for job/analyze endpoints. Returns None when the call
    may proceed (and counts it), or {"error":…, "status":…} when blocked.
    - nobody logged in / not set up / admin  -> always None (never limited)
    - non-admin with expired trial+license   -> 403 dict
    - non-admin over the finite daily limit -> 429 dict
    Callers must treat unexpected internal errors as "allow" (fail-open).
    """
    if not email:
        return None
    with _LOCK:
        data = load()
        user = data["users"].get(_norm(email))
        if user is None or user.get("is_admin"):
            return None
        if not user.get("active", True):
            return {"status": 403, "error":
                    "This account has been deactivated by the admin."}
        status, _days = license_status(user)
        if status not in ("licensed", "trial"):
            return {"status": 403, "error":
                    "Your free trial / license has expired — activate a "
                    "license key (top-right 🔑 Activate Key) to keep creating."}
        limit = user.get("daily_limit")
        if limit is None:
            return None  # unlimited plan
        today = date.today().isoformat()
        usage = user.setdefault("usage", {})
        count = int(usage.get(today, 0))
        if count >= int(limit):
            return {"status": 429, "error":
                    f"Daily limit reached ({limit} files/jobs per day on "
                    "your plan). It resets tomorrow, or ask the admin for "
                    "a higher-limit license key."}
        usage[today] = count + 1
        # keep the usage map small (last 14 days)
        if len(usage) > 14:
            for old in sorted(usage)[:-14]:
                usage.pop(old, None)
        save(data)
    return None
