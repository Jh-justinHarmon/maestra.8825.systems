# SYSTEM MEMORY ANCHOR — READ CAREFULLY

This document prevents context drift and false "everything is broken" diagnosis.

## Canonical Paths

**Canonical root:**
```
~/Hammer Consulting Dropbox/Justin Harmon/8825-Team/8825
```

**Canonical Maestra app:**
```
8825/apps/maestra.8825.systems/
```

**Out of scope (never reference):**
- `CascadeProjects/*`
- `figma-maestra-surface/*`
- `users/*/sandbox/*`
- Any duplicate `maestra.8825.systems` outside `8825/`

---

## Architecture Truth

**Backend:**
- FastAPI application running via uvicorn
- Port: **8825**
- Entry point: `backend/server.py`
- Must have `PYTHONPATH` including `8825/system` for routing imports
- Runs in minimal mode locally: `MAESTRA_MINIMAL_MODE=true`

**Frontend:**
- Vite dev server
- Port: **5001** (or auto-assigned if 5000 occupied)
- Entry point: `src/main.tsx`
- Connects to backend via `VITE_MAESTRA_API` env var

---

## Quad-Core Detection Contract

**Detection is RESPONSE-DRIVEN:**
- Frontend reads `sources[]` array from backend response
- OR reads `mode` field from backend response
- Activates when: `sources[]` contains "personal:" prefix OR `mode === "system_plus_personal"`

**What does NOT control quad-core:**
- NOT `/health` endpoint responses
- NOT `/debug/session` endpoint (dev only)
- NOT polling or timers
- NOT localStorage flags
- NOT session handshake responses

---

## Stop Condition (Binary Test)

**The system is WORKING if:**

```bash
curl -s -X POST http://localhost:8825/api/maestra/advisor/ask \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test","question":"hello","mode":"quick"}' \
  | jq -r '.answer'
```

Returns: Non-empty text (not HTML, not 404)

**If this passes, the system is NOT broken.**

---

## Common False Alarms

### "Maestra isn't working"

**Before diagnosing logic:**
1. Run port ownership check: `python3 8825/scripts/assert_port_8825.py`
2. Verify stop condition passes
3. Check browser DevTools Network tab for actual HTTP responses

**Most common cause:** Wrong process on port 8825 (Flask sidecar vs FastAPI backend)

### "Quad-core not activating"

**Check in order:**
1. Does backend response contain `sources[]` with "personal:" entries?
2. Does backend response contain `mode: "system_plus_personal"`?
3. Check browser console for activation log: `[Maestra] Quad-Core ACTIVE`

**If response has personal sources but badge doesn't show:** UI polish issue, not system failure

### "Everything feels broken"

**Reality check:**
- Is `/api/maestra/advisor/ask` returning JSON?
- Is the response schema correct (`answer`, `mode`, `sources`, `authority`)?
- Is exactly ONE process on port 8825?

**If all yes:** Nothing is broken. Investigate UI/UX separately.

---

## Guardrails

**Port ownership sentinel:**
```bash
python3 8825/scripts/assert_port_8825.py
```

Run this before debugging to eliminate the #1 failure mode.

---

## Never Assume

- Never assume architecture is broken unless stop condition fails
- Never assume quad-core logic is broken unless response data is missing
- Never assume frontend is broken unless Network tab shows errors
- Never assume "everything needs rebuilding" without evidence

---

## Recovery Protocol

If you find yourself thinking "Maestra is completely broken":

1. **STOP**
2. Run: `python3 8825/scripts/assert_port_8825.py`
3. Run: Stop condition test (curl command above)
4. Check: Browser DevTools Network tab
5. **Only then** investigate logic

Most issues are runtime/environment, not code.
