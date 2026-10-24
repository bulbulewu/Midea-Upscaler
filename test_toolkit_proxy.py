import unittest
import json
import time
from app import app, _ensure_toolkit_running

class TestToolkitProxy(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_toolkit_url_route(self):
        res = self.client.get("/api/toolkit-url")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["url"], "/toolkit/")

    def test_toolkit_proxy_integration(self):
        # Trigger background start and test endpoint
        started = _ensure_toolkit_running()
        self.assertTrue(started, "Failed to start toolkit background process")

        # Give it up to 5 seconds to bind
        max_attempts = 10
        success = False
        for _ in range(max_attempts):
            res = self.client.get("/toolkit/")
            if res.status_code == 200 and len(res.data) > 50000:
                success = True
                break
            time.sleep(0.5)

        self.assertTrue(success, f"Toolkit proxy failed to load HTML: status={res.status_code}")
        # Verify fetch interceptor was injected
        self.assertIn(b"origFetch", res.data)
        self.assertIn(b"/toolkit", res.data)

        # Test toolkit API route via proxy
        res_api = self.client.get("/toolkit/api/tracker/seasons")
        self.assertEqual(res_api.status_code, 200)
        data_api = json.loads(res_api.data.decode("utf-8"))
        self.assertIn("events", data_api)

if __name__ == "__main__":
    unittest.main()
