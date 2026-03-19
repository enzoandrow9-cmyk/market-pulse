#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# launch.sh  —  Market Pulse Terminal launcher
# Usage: bash launch.sh
# ─────────────────────────────────────────────────────────────────────────────

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "═══════════════════════════════════════════════"
echo "  ◈  MARKET PULSE TERMINAL"
echo "═══════════════════════════════════════════════"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
  echo "ERROR: python3 not found. Install Python 3.9+."
  exit 1
fi

# Install / upgrade dependencies
echo "  Checking dependencies…"
pip3 install -r requirements.txt -q --break-system-packages 2>/dev/null || \
pip3 install -r requirements.txt -q

echo "  Dependencies OK ✓"
echo ""
echo "  Starting server at http://127.0.0.1:8050"
echo "  Press Ctrl+C to stop."
echo ""

python3 main.py
