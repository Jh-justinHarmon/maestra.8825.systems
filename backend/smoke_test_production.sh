#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-https://maestra-backend-8825-systems.fly.dev}"

echo "== Maestra Backend Smoke Test =="
echo "Base: ${BASE_URL}"

echo "\n[1/3] Health"
health_json="$(curl -sS "${BASE_URL}/health")"
echo "$health_json" | head -c 400; echo

echo "\n[2/3] Advisor ask"
ask_json="$(curl -sS -X POST "${BASE_URL}/api/maestra/advisor/ask" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"smoke","question":"Summarize what this app does in 2 sentences.","mode":"quick"}')"

echo "$ask_json" | head -c 600; echo

echo "\n[3/3] Stub / misconfig detection"
if echo "$ask_json" | grep -qi "Context retrieved for:"; then
  echo "FAIL: stub marker detected (Context retrieved for:)" >&2
  exit 1
fi
if echo "$ask_json" | grep -qi "Guidance for:"; then
  echo "FAIL: stub marker detected (Guidance for:)" >&2
  exit 1
fi
if echo "$ask_json" | grep -qi "offline mode"; then
  echo "FAIL: offline mode response detected" >&2
  exit 1
fi

# If the API returns a 503 JSON with detail, curl will still succeed; detect that too.
if echo "$ask_json" | grep -qi "No LLM provider configured"; then
  echo "FAIL: LLM not configured" >&2
  exit 1
fi

echo "PASS"
