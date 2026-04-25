#!/bin/bash
set -e
echo "============================================"
echo "  FairLens v2 — Backend Startup"
echo "============================================"
cd "$(dirname "$0")/backend"

if ! command -v python3 &> /dev/null; then
  echo "ERROR: python3 not found. Install Python 3.9+"
  exit 1
fi

echo "[1/2] Installing dependencies..."
pip3 install -r requirements.txt --break-system-packages -q

echo "[2/2] Starting FastAPI on http://localhost:8000"
echo "      Docs: http://localhost:8000/docs"
echo ""
echo "  Tip: set GEMINI_API_KEY env var for full AI chat"
echo ""
python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
