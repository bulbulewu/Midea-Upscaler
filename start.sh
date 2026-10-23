#!/bin/bash
# Media Toolkit Pro V3 — Linux/macOS Startup
# Made By Munajat International

set -e
cd "$(dirname "$0")"

echo "========================================================"
echo "  Media Toolkit Pro V3 — Multi-Marketplace Studio"
echo "  Made By Munajat International"
echo "========================================================"

if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 could not be found. Please install Python 3.10+."
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "[Setup] Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    echo "[Setup] Installing dependencies..."
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

echo "[Launch] Starting server..."
python3 app.py
