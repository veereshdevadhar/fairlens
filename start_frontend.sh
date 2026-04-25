#!/bin/bash
set -e
echo "============================================"
echo "  FairLens v2 — Frontend Startup"
echo "============================================"
cd "$(dirname "$0")/frontend"

if ! command -v node &> /dev/null; then
  echo "ERROR: Node.js not found. Install from https://nodejs.org"
  exit 1
fi

echo "Node: $(node --version)  NPM: $(npm --version)"
echo ""
echo "[1/2] Installing npm packages..."
npm install

echo "[2/2] Starting React on http://localhost:3000"
echo ""
npm start
