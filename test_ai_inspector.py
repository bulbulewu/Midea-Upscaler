import unittest
import json
import io
import os
from PIL import Image
from app import app
from backend.ai_inspector import load_ai_config, save_ai_config, get_masked_key

class TestAiInspector(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_masked_key(self):
        self.assertEqual(get_masked_key(""), "")
        self.assertEqual(get_masked_key("short"), "")
        masked = get_masked_key("AIzaSyB1234567890abcdef")
        self.assertTrue(masked.startswith("AIza"))
        self.assertTrue(masked.endswith("cdef"))
        self.assertIn("•", masked)

    def test_ai_config_endpoint(self):
        # GET config
        res = self.client.get("/api/ai/config")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("provider", data)
        self.assertIn("model", data)

        # POST config
        post_data = {
            "gemini_api_key": "AIzaSyTestKey1234567890",
            "provider": "gemini",
            "model": "gemini-1.5-flash",
            "check_trademarks": "true",
            "check_model_release": "true",
            "check_property_release": "true"
        }
        res_post = self.client.post(
            "/api/ai/config",
            data=json.dumps(post_data),
            content_type="application/json"
        )
        self.assertEqual(res_post.status_code, 200)
        d_post = res_post.get_json()
        self.assertTrue(d_post["success"])
        self.assertTrue(d_post["has_gemini"])

    def test_ai_inspect_no_file(self):
        res = self.client.post("/api/ai/inspect")
        self.assertEqual(res.status_code, 400)

    def test_ai_inspect_with_image(self):
        # Create a small in-memory image
        img = Image.new("RGB", (200, 200), color=(100, 150, 200))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)

        # With mock/dummy key (will hit Gemini and return error or response)
        res = self.client.post(
            "/api/ai/inspect",
            data={"file": (buf, "test_check.jpg")},
            content_type="multipart/form-data"
        )
        # Should return a valid JSON response (either result or API error)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("success", data)

if __name__ == "__main__":
    unittest.main()
