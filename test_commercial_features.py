"""
Unit tests for Commercial & Administration features:
- License key generation, activation, revocation
- Admin policies & users
- Settings management
- Auth session and security
"""

import unittest
import uuid
from app import app
from backend.license_manager import license_mgr


class TestCommercialFeatures(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        # Log in as Master Admin for admin endpoint tests
        self.client.post("/api/auth/login", json={
            "email": "bulbulworka1@gmail.com",
            "password": "bulbul2026"
        })

    def test_01_auth_session(self):
        res = self.client.get("/api/auth/session")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("logged_in", data)
        self.assertTrue(data.get("is_admin"))

    def test_01b_unauthenticated_admin_blocked(self):
        guest_client = app.test_client()
        res = guest_client.get("/api/admin/keys?status=All")
        self.assertEqual(res.status_code, 403)
        gen_res = guest_client.post("/api/admin/keys/generate", json={
            "email": "hacker@test.com", "period": 30, "daily_limit": 50
        })
        self.assertEqual(gen_res.status_code, 403)

    def test_02_generate_license_key(self):
        u_email = f"contributor_{uuid.uuid4().hex[:6]}@munajat.com"
        res = self.client.post("/api/admin/keys/generate", json={
            "email": u_email,
            "period": 60,
            "daily_limit": 100,
            "note": "bKash TrxID #88219"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertTrue(data["key"]["key"].startswith("MTK-PRO-"))
        self.assertEqual(data["key"]["assigned_email"], u_email)

    def test_03_get_license_keys(self):
        res = self.client.get("/api/admin/keys?status=All")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("keys", data)
        self.assertGreater(data["total"], 0)

    def test_04_activate_license_key(self):
        u_email = f"buyer_{uuid.uuid4().hex[:6]}@munajat.com"
        # Generate a key first
        gen_res = self.client.post("/api/admin/keys/generate", json={
            "email": u_email,
            "period": 30,
            "daily_limit": 50,
            "note": "Test activation"
        })
        key_str = gen_res.get_json()["key"]["key"]

        # Activate the key
        act_res = self.client.post("/api/license/activate", json={
            "key": key_str,
            "email": u_email,
            "hwid": "PC-TEST-DEVICE-001"
        })
        self.assertEqual(act_res.status_code, 200)
        act_data = act_res.get_json()
        self.assertTrue(act_data.get("success"))

    def test_05_admin_users_list_and_add(self):
        u_email = f"artist_{uuid.uuid4().hex[:6]}@munajat.com"
        # Add user
        add_res = self.client.post("/api/admin/users/add", json={
            "email": u_email,
            "name": "Munajat Graphic Artist",
            "role": "Pro Contributor",
            "daily_limit": 80
        })
        self.assertEqual(add_res.status_code, 200)

        # List users
        users_res = self.client.get("/api/admin/users")
        self.assertEqual(users_res.status_code, 200)
        users = users_res.get_json().get("users", [])
        self.assertGreaterEqual(len(users), 1)

    def test_06_admin_policies(self):
        # GET policies
        get_res = self.client.get("/api/admin/policies")
        self.assertEqual(get_res.status_code, 200)
        policies = get_res.get_json()
        self.assertIn("default_access_period_days", policies)

        # POST update policy
        post_res = self.client.post("/api/admin/policies", json={
            "default_access_period_days": 45,
            "default_daily_limit": 75,
            "max_video_duration_sec": 180,
            "master_admin_email": "bulbulworka1@gmail.com"
        })
        self.assertEqual(post_res.status_code, 200)

    def test_07_storage_metrics(self):
        res = self.client.get("/api/admin/stats")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("uploads_size_mb", data)
        self.assertIn("outputs_size_mb", data)
        self.assertIn("total_keys", data)

    def test_08_backup_export(self):
        res = self.client.get("/api/admin/backup")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("version", data)
        self.assertIn("keys", data)
        self.assertIn("policies", data)

    def test_09_settings_agencies(self):
        # GET
        get_res = self.client.get("/api/settings/agencies")
        self.assertEqual(get_res.status_code, 200)
        agencies = get_res.get_json()
        self.assertIn("adobe_stock", agencies)

        # POST
        adobe = agencies["adobe_stock"]
        adobe["title_max_chars"] = 190
        post_res = self.client.post("/api/settings/agencies/adobe_stock", json=adobe)
        self.assertEqual(post_res.status_code, 200)

    def test_10_settings_studio(self):
        # GET
        get_res = self.client.get("/api/settings/studio")
        self.assertEqual(get_res.status_code, 200)
        s = get_res.get_json()
        self.assertIn("theme", s)

        # POST
        s["theme"] = "obsidian_oled"
        post_res = self.client.post("/api/settings/studio", json=s)
        self.assertEqual(post_res.status_code, 200)

    def test_11_user_registration_trial(self):
        u_email = f"trial_{uuid.uuid4().hex[:6]}@gmail.com"
        reg_res = self.client.post("/api/auth/register", json={
            "email": u_email,
            "password": "pass_trial_123",
            "name": "Trial User"
        })
        self.assertEqual(reg_res.status_code, 200)
        reg_data = reg_res.get_json()
        self.assertTrue(reg_data["success"])
        self.assertFalse(reg_data["session"]["is_admin"])


if __name__ == "__main__":
    unittest.main()
