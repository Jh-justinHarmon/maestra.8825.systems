#!/bin/bash
# Maestra Backend Launcher
# Loads team LLM environment variables and starts uvicorn
# Usage: ./maestra_backend_launch.sh

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Find 8825 root (up 4 levels: backend -> maestra.8825.systems -> apps -> 8825-Team)
TEAM_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Load team LLM environment variables
SYSTEM_DIR="$TEAM_ROOT/users/justin_harmon/8825-Jh/8825_core/system"
if [ -f "$SYSTEM_DIR/load_llm_env.sh" ]; then
  source "$SYSTEM_DIR/load_llm_env.sh"
else
  echo "Warning: Could not find load_llm_env.sh at $SYSTEM_DIR" >&2
fi

# Start uvicorn
cd "$SCRIPT_DIR"
exec python3 -m uvicorn server:app --host 0.0.0.0 --port 8825
