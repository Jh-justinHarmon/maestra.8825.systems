#!/bin/bash

# Maestra Quad-Core Sidecar Startup Script
# Runs on localhost:8826 to provide Quad-Core capabilities

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🟢 Starting Maestra Quad-Core Sidecar..."
echo "   Port: 8826"
echo "   Project: $PROJECT_ROOT"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3."
    exit 1
fi

# Install dependencies if needed
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv "$SCRIPT_DIR/venv"
fi

# Activate virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# Install requirements
echo "📦 Installing dependencies..."
pip install -q -r "$SCRIPT_DIR/requirements.txt"

# Set environment variables
export LIBRARY_PATH="/Users/justinharmon/Hammer Consulting Dropbox/Justin Harmon/8825-Team/shared/8825-library"
export FLASK_APP="$SCRIPT_DIR/server.py"
export FLASK_ENV="production"

# Start the sidecar
echo "✅ Sidecar ready. Starting Flask server..."
python3 "$SCRIPT_DIR/server.py"
