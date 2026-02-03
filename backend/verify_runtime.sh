#!/bin/bash
# Runtime Proof Command (PROMPT 16)
# The ONLY approved way to answer: "Which backend is running?"

set -e

BACKEND_URL="http://localhost:8825"
CANONICAL_BACKEND="/Users/justinharmon/Hammer Consulting Dropbox/Justin Harmon/8825-Team/8825/apps/maestra.8825.systems/backend"
CANONICAL_SYSTEM="/Users/justinharmon/Hammer Consulting Dropbox/Justin Harmon/8825-Team/8825/system"

echo "🔍 Maestra Backend Runtime Verification"
echo "========================================"
echo ""

# Check if backend is running
if ! curl -s -f "$BACKEND_URL/health" > /dev/null 2>&1; then
  echo "❌ FAIL: Backend not responding at $BACKEND_URL"
  echo ""
  echo "Start backend with:"
  echo "  ./apps/maestra.8825.systems/backend/start.sh"
  exit 1
fi

# Get health data
HEALTH_DATA=$(curl -s "$BACKEND_URL/health")

# Extract fields
CANONICAL=$(echo "$HEALTH_DATA" | jq -r '.canonical_backend // "null"')
PID=$(echo "$HEALTH_DATA" | jq -r '.pid // "null"')
SERVER_PATH=$(echo "$HEALTH_DATA" | jq -r '.server_path // "null"')
ADVISOR_PATH=$(echo "$HEALTH_DATA" | jq -r '.advisor_path // "null"')
SYSTEM_PATH=$(echo "$HEALTH_DATA" | jq -r '.system_path // "null"')

echo "Runtime Identity:"
echo "  canonical_backend: $CANONICAL"
echo "  pid:               $PID"
echo "  server_path:       $SERVER_PATH"
echo "  advisor_path:      $ADVISOR_PATH"
echo "  system_path:       $SYSTEM_PATH"
echo ""

# Verify canonical_backend flag
if [ "$CANONICAL" != "true" ]; then
  echo "❌ FAIL: canonical_backend is not true"
  echo ""
  echo "This backend is NOT the canonical backend."
  echo "See: CANONICAL_REALITY.md"
  exit 1
fi

# Verify server_path
if [[ "$SERVER_PATH" != "$CANONICAL_BACKEND"* ]]; then
  echo "❌ FAIL: server_path does not match canonical location"
  echo "  Expected: $CANONICAL_BACKEND/server.py"
  echo "  Actual:   $SERVER_PATH"
  exit 1
fi

# Verify advisor_path
if [[ "$ADVISOR_PATH" != "$CANONICAL_BACKEND"* ]]; then
  echo "❌ FAIL: advisor_path does not match canonical location"
  echo "  Expected: $CANONICAL_BACKEND/advisor.py"
  echo "  Actual:   $ADVISOR_PATH"
  exit 1
fi

# Verify system_path
if [[ "$SYSTEM_PATH" != "$CANONICAL_SYSTEM"* ]]; then
  echo "❌ FAIL: system_path does not match canonical location"
  echo "  Expected: $CANONICAL_SYSTEM/routing"
  echo "  Actual:   $SYSTEM_PATH"
  exit 1
fi

# Verify PID is running
if ! ps -p "$PID" > /dev/null 2>&1; then
  echo "⚠️  WARNING: PID $PID is not running (stale health data?)"
fi

echo "✅ PASS: All runtime identity checks passed"
echo ""
echo "This is the canonical Maestra backend."
exit 0
