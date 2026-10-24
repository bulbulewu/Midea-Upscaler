#!/bin/bash
cd "$(dirname "$0")"
echo "Stock Contributor Toolkit Pro - Launcher"
command -v python3 >/dev/null || { echo "Install Python 3 first: https://www.python.org/downloads/"; exit 1; }
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
command -v ffmpeg >/dev/null || echo "NOTE: FFmpeg not found (video tools need it): sudo apt install ffmpeg  /  brew install ffmpeg"
echo "Open http://127.0.0.1:5000 in your browser (Ctrl+C stops the app)"
python app.py
