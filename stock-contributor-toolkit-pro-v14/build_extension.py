"""Zip the browser extension for one-click download from the app UI."""
import os
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "extension")
OUT = os.path.join(BASE, "static", "stockmeta-helper.zip")

with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk(SRC):
        for f in files:
            if f.endswith((".png", ".json", ".html", ".js", ".md")):
                full = os.path.join(root, f)
                z.write(full, os.path.relpath(full, SRC))
print("wrote", OUT, os.path.getsize(OUT), "bytes")
