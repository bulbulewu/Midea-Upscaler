"""
Media Toolkit Pro V3 — Automated End-to-End Test Suite
Tests all v3 multi-marketplace features, pre-flight checks, codecs, and API endpoints
Made By Munajat International
"""

import os
import sys
import tempfile
import unittest
import subprocess
from PIL import Image
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from backend.upscaler_video import find_ffmpeg, probe as probe_video, upscale as upscale_video
from backend.upscaler_image import upscale_image, probe_image
from backend.png_to_psd import png_to_psd
from backend.stock_validator import preflight_video_check, preflight_image_check


class TestMediaToolkitProV3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.temp_dir = tempfile.mkdtemp()
        cls.ff, cls.fp = find_ffmpeg()

        # 1. Test image
        cls.test_png = os.path.join(cls.temp_dir, "test_alpha.png")
        img = Image.new("RGBA", (150, 100), (0, 0, 0, 0))
        arr = np.array(img)
        arr[20:80, 20:100] = [0, 210, 255, 255]
        Image.fromarray(arr).save(cls.test_png)

        # 2. Test video (1s, 24fps)
        cls.test_vid = os.path.join(cls.temp_dir, "test_clip.mp4")
        cmd = [
            cls.ff, "-y",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=640x360:rate=24",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=1",
            "-c:v", "libx264", "-c:a", "aac",
            cls.test_vid
        ]
        subprocess.run(cmd, check=True, capture_output=True)

    def test_01_health_and_marketplaces(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["ffmpeg_ok"])
        self.assertEqual(data["version"], "3.0.0")
        self.assertIn("adobe_stock", data["marketplaces_supported"])
        self.assertIn("shutterstock", data["marketplaces_supported"])
        print("PASS: [1/8] Health check & marketplace discovery verified.")

    def test_02_stock_preflight_checks(self):
        v_meta = probe_video(self.test_vid)
        v_report = preflight_video_check(v_meta, "adobe_stock")
        self.assertEqual(v_report["marketplace"], "Adobe Stock")
        self.assertTrue(len(v_report["checks"]) >= 4)

        i_meta = probe_image(self.test_png)
        i_report = preflight_image_check(i_meta, "shutterstock")
        self.assertEqual(i_report["marketplace"], "Shutterstock")
        print("PASS: [2/8] Stock pre-flight compliance rules verified.")

    def test_03_preflight_api_endpoints(self):
        with open(self.test_vid, "rb") as f:
            resp = self.client.post("/api/preflight/video", data={"file": f, "marketplace": "universal"}, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("report", resp.get_json())

        with open(self.test_png, "rb") as f:
            resp = self.client.post("/api/preflight/image", data={"file": f, "marketplace": "adobe_stock"}, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("report", resp.get_json())
        print("PASS: [3/8] Pre-flight inspection API endpoints verified.")

    def test_04_video_upscaler_h264_master(self):
        dst = os.path.join(self.temp_dir, "out_h264.mp4")
        res = upscale_video(self.test_vid, dst, target="4k", quality="stock", codec="h264", marketplace="adobe_stock", keep_audio=False)
        self.assertEqual(res["output"]["width"], 3840)
        self.assertEqual(res["output"]["height"], 2160)
        self.assertEqual(res["output"]["fps"], 24.0)
        self.assertEqual(res["output"]["color_space"], "bt709")
        print("PASS: [4/8] Video 4K H.264 Master pipeline verified.")

    def test_05_video_upscaler_prores_master(self):
        dst = os.path.join(self.temp_dir, "out_prores.mov")
        res = upscale_video(self.test_vid, dst, target="4k", quality="stock", codec="prores", marketplace="pond5", keep_audio=False)
        self.assertEqual(res["output"]["width"], 3840)
        self.assertEqual(res["output"]["height"], 2160)
        self.assertEqual(res["output"]["codec"], "prores")
        self.assertTrue(os.path.exists(dst))
        print("PASS: [5/8] Video Apple ProRes 422 Broadcast Master pipeline verified.")

    def test_06_image_upscaler_megapixel_enforcement(self):
        dst = os.path.join(self.temp_dir, "out_stock.jpg")
        res = upscale_image(self.test_png, dst, scale="8x", output_format="jpg", dpi=300, auto_denoise=True)
        self.assertEqual(res["output"]["width"], 1200)
        self.assertEqual(res["output"]["height"], 800)
        self.assertEqual(res["output"]["dpi"], "300 DPI")
        self.assertTrue(res["output"]["auto_denoise"])
        print("PASS: [6/8] Image Upscaler with 300 DPI & Auto-Denoise verified.")

    def test_07_png_to_layered_psd(self):
        dst = os.path.join(self.temp_dir, "out_master.psd")
        res = png_to_psd(self.test_png, dst, layer_name="Commercial Asset", background="transparent", dpi=300)
        self.assertEqual(res["output"]["layer_name"], "Commercial Asset")
        self.assertTrue(res["output"]["transparency"])
        self.assertEqual(res["output"]["dpi"], "300 DPI")
        self.assertTrue(os.path.exists(dst))
        print("PASS: [7/8] PNG to Layered PSD conversion verified.")

    def test_08_api_video_and_download_lifecycle(self):
        with open(self.test_vid, "rb") as f:
            resp = self.client.post("/api/jobs", data={
                "file": f, "target": "4k", "quality": "stock", "codec": "h264", "marketplace": "adobe_stock", "keep_audio": "false"
            }, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 200)
        job_id = resp.get_json()["id"]

        import time
        for _ in range(50):
            st = self.client.get(f"/api/jobs/{job_id}").get_json()
            if st["state"] in ("done", "error"):
                break
            time.sleep(0.3)
        self.assertEqual(st["state"], "done")

        dl = self.client.get(f"/api/download/{job_id}")
        self.assertEqual(dl.status_code, 200)
        print("PASS: [8/8] Full API Job Lifecycle & Download verified.")


if __name__ == "__main__":
    unittest.main()
