#!/bin/bash
# Maestra Backend - CANONICAL STARTUP SCRIPT
# This is the ONLY blessed way to start the Maestra backend locally.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEM_DIR="/Users/justinharmon/Hammer Consulting Dropbox/Justin Harmon/8825-Team/8825/system"

echo "🚀 Starting Maestra Backend (Canonical)"
echo "   Backend: $SCRIPT_DIR"
echo "   System:  $SYSTEM_DIR"
echo ""

# Validate canonical location
EXPECTED_PATH="/Users/justinharmon/Hammer Consulting Dropbox/Justin Harmon/8825-Team/8825/apps/maestra.8825.systems/backend"
if [ "$SCRIPT_DIR" != "$EXPECTED_PATH" ]; then
    echo "❌ FATAL: This script must be run from the canonical backend directory."
    echo "   Expected: $EXPECTED_PATH"
    echo "   Actual:   $SCRIPT_DIR"
    exit 1
fi

# Set required PYTHONPATH
export PYTHONPATH="$SYSTEM_DIR:$PYTHONPATH"

# Change to backend directory
cd "$SCRIPT_DIR"

# Start uvicorn
echo "✅ Starting uvicorn on port 8825..."
exec python3 -m uvicorn server:app --host 0.0.0.0 --port 8825
