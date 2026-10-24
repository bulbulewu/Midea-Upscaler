"""
Unit tests for Commercial & Administration features:
- License key generation, activation, revocation
- Admin policies & users
- Settings management
- Auth session
"""

import unittest
from app import app
from backend.license_manager import license_mgr


class TestCommercialFeatures(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_01_auth_session(self):
        res = self.client.get("/api/auth/session")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("logged_in", data)

    def test_02_generate_license_key(self):
        res = self.client.post("/api/admin/keys/generate", json={
            "email": "contributor_test@munajat.com",
            "period": 60,
            "daily_limit": 100,
            "note": "bKash TrxID #88219"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertTrue(data["key"]["key"].startswith("MTK-PRO-"))
        self.assertEqual(data["key"]["assigned_email"], "contributor_test@munajat.com")

    def test_03_get_license_keys(self):
        res = self.client.get("/api/admin/keys?status=All")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("keys", data)
        self.assertGreater(data["total"], 0)

    def test_04_activate_license_key(self):
        # Generate a key first
        gen_res = self.client.post("/api/admin/keys/generate", json={
            "email": "buyer1@munajat.com",
            "period": 30,
            "daily_limit": 50,
            "note": "Test activation"
        })
        key_str = gen_res.get_json()["key"]["key"]

        # Activate
        act_res = self.client.post("/api/license/activate", json={
            "key": key_str,
            "email": "buyer1@munajat.com",
            "hwid": "HWID-TEST-DESKTOP"
        })
        self.assertEqual(act_res.status_code, 200)
        data = act_res.get_json()
        self.assertTrue(data.get("success"))

    def test_05_admin_users(self):
        res = self.client.get("/api/admin/users")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("users", data)
        self.assertGreater(data["total"], 0)

    def test_06_admin_policies(self):
        res = self.client.get("/api/admin/policies")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("default_daily_limit", data)

    def test_07_agency_settings(self):
        res = self.client.get("/api/settings/agencies")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("adobe_stock", data)
        self.assertEqual(data["adobe_stock"]["title_min_chars"], 15)

    def test_08_backup_export(self):
        res = self.client.get("/api/admin/backup")
        self.assertEqual(res.status_code, 200)
        self.assertIn("application/json", res.content_type)

    def test_09_edit_user(self):
        # Add user first
        add_res = self.client.post("/api/admin/users/add", json={
            "email": "edit_target@munajat.com",
            "name": "Target User",
            "role": "Pro Contributor",
            "daily_limit": 50
        })
        user_id = add_res.get_json()["user"]["id"]

        # Edit user
        res = self.client.post("/api/admin/users/edit", json={
            "user_id": user_id,
            "name": "Target Updated",
            "daily_limit": 150,
            "license_period_days": 90,
            "status": "Active"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data["user"]["name"], "Target Updated")

    def test_10_export_csv(self):
        res = self.client.get("/api/admin/users/export-csv")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/csv", res.content_type)
        self.assertIn("Email,Name,Role", res.get_data(as_text=True))

    def test_11_admin_stats(self):
        res = self.client.get("/api/admin/stats")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("total_keys", data)
        self.assertIn("uploads_size_mb", data)

    def test_12_purge_cache(self):
        res = self.client.post("/api/admin/purge-cache")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))

    def test_13_delete_user(self):
        res = self.client.post("/api/admin/users/delete", json={
            "user_id": "edit_target@munajat.com"
        })
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json().get("success"))


if __name__ == "__main__":
    unittest.main()
