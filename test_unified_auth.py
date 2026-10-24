import unittest
import json
from app import app
from backend.license_manager import license_mgr

class TestUnifiedAuthAndTheme(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_admin_login_with_username_or_email(self):
        # 1. Login with username 'admin' and password 'bulbul2026'
        resp = self.client.post("/api/auth/login", json={"email": "admin", "password": "bulbul2026"})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data["session"]["role"], "Master Admin")
        self.assertTrue(data["session"]["is_admin"])

        # 2. Login with email 'bulbulworka1@gmail.com' and password 'bulbul2026'
        resp2 = self.client.post("/api/auth/login", json={"email": "bulbulworka1@gmail.com", "password": "bulbul2026"})
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.get_json()
        self.assertTrue(data2.get("success"))

    def test_sso_login_and_theme_sync(self):
        # SSO Login
        resp = self.client.post("/api/auth/sso-login", json={"sso_user": "admin", "sso_token": "token123"})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertTrue(data["session"]["is_admin"])

        # Set user theme
        resp_theme = self.client.post("/api/user/theme", json={"theme": "cyber_neon"})
        self.assertEqual(resp_theme.status_code, 200)
        self.assertEqual(resp_theme.get_json()["theme"], "cyber_neon")

if __name__ == "__main__":
    unittest.main()
