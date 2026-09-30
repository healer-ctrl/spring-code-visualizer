#!/usr/bin/env bash
# ───────────────────────────────────────────────
#  Spring Canvas IDE  –  one-click launcher
# ───────────────────────────────────────────────
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Install deps if needed
if ! python3 -c "import flask" 2>/dev/null; then
    echo "📦  Installing dependencies..."
    pip3 install -r requirements.txt -q
fi

PORT=${1:-5000}
echo ""
echo "  ╔═══════════════════════════════════════╗"
echo "  ║       Spring Canvas IDE               ║"
echo "  ║   http://127.0.0.1:$PORT               ║"
echo "  ╚═══════════════════════════════════════╝"
echo ""
echo "  Paste your project absolute path in the browser."
echo "  Press Ctrl+C to stop."
echo ""

python3 app.py $PORT
