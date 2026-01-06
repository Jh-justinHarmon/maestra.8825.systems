#!/bin/bash

# Maestra Development Environment Startup Script
# Uses persistent port registry to prevent conflicts and ensure reproducibility

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SYSTEM_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Source root finder
source "$SYSTEM_ROOT/8825_core/system/detect_root.sh"

echo "🚀 Starting Maestra Development Environment"
echo "   Project: $PROJECT_ROOT"
echo "   System:  $8825_ROOT"
echo ""

# Load port registry
python3 "$8825_ROOT/8825_core/system/port_manager.py" list

echo ""
echo "📋 Checking service availability..."
echo ""

# Check Maestra Frontend Dev (port 5173)
if python3 -c "from port_manager import PortManager; import sys; sys.path.insert(0, '$8825_ROOT/8825_core/system'); pm = PortManager(); sys.exit(0 if pm.is_available('maestra_frontend_dev') else 1)" 2>/dev/null; then
    FRONTEND_PORT=5173
    echo "✅ Maestra Frontend Dev (5173) - Available"
else
    echo "❌ Maestra Frontend Dev (5173) - In use"
    FRONTEND_PORT=$(python3 -c "from port_manager import PortManager; import sys; sys.path.insert(0, '$8825_ROOT/8825_core/system'); pm = PortManager(); print(pm.get_next_available_port(5174))" 2>/dev/null || echo "5173")
    echo "   Using fallback port: $FRONTEND_PORT"
fi

# Check Maestra Backend (port 8825)
if python3 -c "from port_manager import PortManager; import sys; sys.path.insert(0, '$8825_ROOT/8825_core/system'); pm = PortManager(); sys.exit(0 if pm.is_available('maestra_backend') else 1)" 2>/dev/null; then
    echo "✅ Maestra Backend (8825) - Available"
else
    echo "⚠️  Maestra Backend (8825) - Already running (expected)"
fi

# Check Maestra Sidecar (port 8826)
if python3 -c "from port_manager import PortManager; import sys; sys.path.insert(0, '$8825_ROOT/8825_core/system'); pm = PortManager(); sys.exit(0 if pm.is_available('maestra_sidecar') else 1)" 2>/dev/null; then
    echo "⚠️  Maestra Sidecar (8826) - Not running (start with: ./sidecar/start.sh)"
else
    echo "✅ Maestra Sidecar (8826) - Running"
fi

echo ""
echo "🎯 Starting Maestra Frontend Dev Server..."
echo "   Port: $FRONTEND_PORT"
echo "   URL:  http://localhost:$FRONTEND_PORT"
echo ""

# Kill any existing dev servers
pkill -f "vite.*maestra" 2>/dev/null || true
sleep 1

# Start Vite dev server
cd "$PROJECT_ROOT"
npm run dev -- --port "$FRONTEND_PORT" 2>&1 &
DEV_PID=$!

echo "✅ Dev server started (PID: $DEV_PID)"
echo ""
echo "📝 Services:"
echo "   Frontend:  http://localhost:$FRONTEND_PORT"
echo "   Backend:   http://localhost:8825"
echo "   Sidecar:   http://localhost:8826"
echo ""
echo "💡 Tips:"
echo "   - Start sidecar in another terminal: ./sidecar/start.sh"
echo "   - View port registry: python3 8825_core/system/port_manager.py list"
echo "   - Stop all: pkill -f 'vite.*maestra' && pkill -f 'python.*sidecar'"
echo ""

wait $DEV_PID
