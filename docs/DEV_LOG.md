# Maestra Development Log

This document tracks frontend-backend integration issues, decisions, and context for rapid debugging.

## Format

Each entry follows this structure:
```
### [Date] [Issue ID] - [Brief Title]
**Status:** [Open | In Progress | Resolved]
**Severity:** [Critical | High | Medium | Low]
**Components:** [Frontend | Backend | Both]

**Problem Statement:**
[What is broken or unclear]

**Root Cause (if known):**
[Why it's happening]

**Context:**
- Conversation thread: [link or ID]
- Related files: [list]
- Related decisions: [list]

**Solution Path:**
[What we tried, what worked]

**Lessons Learned:**
[What to remember for next time]

---
```

## Open Issues

### [2025-12-30] ISSUE-001 - Frontend-Backend Communication Loop
**Status:** In Progress  
**Severity:** High  
**Components:** Both

**Problem Statement:**
Frontend and backend debugging sessions get very long. When issues arise, we lose track of:
- What the original intent was
- What we've already tried
- Why certain architectural decisions were made
- What the current state actually is vs. what we think it is

**Root Cause:**
Lack of structured context capture during debugging. Conversations meander through multiple hypothesis without clear confirmation gates.

**Context:**
- Related to E2E test failures and deployment mismatches
- Affects rapid iteration on features
- Impacts developer confidence in system state

**Solution Path:**
1. Create intent documentation (INTENT.md) ✅
2. Create dev-log for tracking issues (this file) ✅
3. Enhance dev-assistant agent with structured workflow
4. Wire context gathering to include intent + dev-log
5. Add confirmation gates before hypothesis testing

**Lessons Learned:**
- Always confirm WHERE testing is happening (local vs. production)
- Always verify deployment status before testing
- Document assumptions about system state
- Use structured problem statements, not narrative descriptions

---

### [2025-12-30] ISSUE-002 - Local vs. Production Testing Confusion
**Status:** Resolved  
**Severity:** Critical  
**Components:** Both

**Problem Statement:**
UI tests failed 5+ times while backend was working. Root cause: UI was configured for localhost but user was testing against production URL (maestra.8825.systems).

**Root Cause:**
Never asked WHERE the user was testing. Assumed local dev environment. Kept iterating on backend fixes when the real issue was deployment/configuration mismatch.

**Context:**
- Occurred during E2E test validation phase
- Wasted ~30 minutes on unnecessary backend changes
- Revealed gap in debugging protocol

**Solution Path:**
1. Added mandatory "WHERE are you testing?" question to dev-assistant
2. Created deployment verification checklist
3. Implemented test environment detection
4. Added curl verification against actual test URL before UI testing

**Lessons Learned:**
- **MANDATORY:** Confirm test environment (local vs. production) FIRST
- **MANDATORY:** Verify deployment status before testing
- **MANDATORY:** Test with curl against the SAME URL the UI uses
- Don't assume local testing reflects production behavior
- Iterate on fixes only after confirming test environment

---

### [2025-12-30] ISSUE-003 - Deployment Dependency Mismatches
**Status:** Resolved  
**Severity:** High  
**Components:** Backend

**Problem Statement:**
Backend crashed on Fly.io with:
- `ModuleNotFoundError: No module named 'jwt'`
- `ModuleNotFoundError: No module named 'smart_pdf_export'`

Code worked locally but failed in Docker container.

**Root Cause:**
1. `pyjwt` package missing from `requirements.txt`
2. Optional imports in `smart_pdf_handler.py` weren't wrapped in try/except
3. Fly.io `fly.toml` had `min_machines_running = 0` (machines auto-stopped when idle)

**Context:**
- Occurred during Maestra backend deployment
- Revealed local-vs-production dependency mismatch pattern
- Fly.io auto-stop behavior not documented

**Solution Path:**
1. Added `pyjwt>=2.8.0` to requirements.txt
2. Wrapped optional imports in try/except blocks
3. Changed fly.toml: `min_machines_running = 1`, `auto_stop_machines = 'off'`
4. Tested Docker build locally before deploying

**Lessons Learned:**
- **MANDATORY:** Run `docker build -t test .` locally before deploying
- **MANDATORY:** Run `pip freeze > requirements.txt` to capture ALL dependencies
- Wrap optional imports in try/except for graceful degradation
- Check Fly.io auto-stop settings for production apps
- Use `flyctl logs --no-tail` to see actual error messages
- Test with curl against production URL to verify fixes

---

## Resolved Issues (Archive)

[Resolved issues will be moved here with summary]

---

## Decision Log

### Decision: Maestra as Card + Adapter Pattern
**Date:** 2025-12-30  
**Status:** Validated  
**Rationale:** Single component works on all surfaces; surface-specific logic isolated in adapters.

**Trade-offs:**
- More files to maintain
- Cleaner separation of concerns
- Easier to test each surface independently

**Validation:** All surfaces (web, extension, iOS) use same MaestraCard with different adapters.

---

### Decision: Versioned Contract (schema_version: "1")
**Date:** 2025-12-30  
**Status:** Validated  
**Rationale:** JSON-safe, backward-compatible, enables multi-surface consistency.

**Trade-offs:**
- Schema changes require migration planning
- All fixtures must validate against schema
- Timestamp format locked to ISO 8601

**Validation:** All 9 golden fixtures validate against schema v1.

---

### Decision: Local-First Testing with Mock Backend
**Date:** 2025-12-30  
**Status:** Validated (with caveats)  
**Rationale:** Mock backend for UI testing; real backend for integration.

**Trade-offs:**
- Mock responses don't reflect real performance
- Can't test error handling without real backend
- Need separate integration test suite

**Validation:** E2E tests use mock backend; integration tests use real backend.

**Caveat:** Always verify deployment status before testing against production.

---

## Context Snapshots

### Snapshot: Current Frontend-Backend Architecture (2025-12-30)

**Frontend (Web):**
- React + Vite
- MaestraCard component with mode detection
- Mock adapter for local testing
- Web adapter for production
- Bundle size: 52.7 KB gzip

**Backend:**
- Conversation Hub API (port 8826, not yet deployed)
- Maestra backend (Fly.io, deployed)
- Mock backend (localhost:3001, for E2E tests)

**Integration Points:**
- Web app → Maestra backend (real LLM)
- Web app → Mock backend (local testing)
- Extension → Conversation Hub API (when deployed)
- iOS → Conversation Hub API (when deployed)

**Known Gaps:**
- Conversation Hub API not deployed to production
- Extension doesn't call Conversation Hub yet
- iOS is architecture only

---

### Snapshot: Deployment Checklist (2025-12-30)

**Before deploying to Fly.io:**
- [ ] Run `pip freeze > requirements.txt`
- [ ] Test Docker build locally: `docker build -t test .`
- [ ] Check for optional imports and wrap in try/except
- [ ] Verify fly.toml has `min_machines_running = 1`
- [ ] Verify fly.toml has `auto_stop_machines = 'off'`

**After deploying:**
- [ ] Check `flyctl status` shows machines in "started" state
- [ ] Check `flyctl logs --no-tail` for import errors
- [ ] Test health endpoint: `curl https://[app].fly.dev/health`
- [ ] Test actual endpoint: `curl -X POST https://[app].fly.dev/api/...`

---

## Related Documentation

- `INTENT.md` – Project vision and strategic goals
- `ARCHITECTURE.md` – Technical design
- `MAESTRA_INTEGRATION.md` – Conversation Hub integration
- `DEPLOY_BACKEND.md` – Backend deployment guide

---

**Last Updated:** 2025-12-31  
**Version:** 1.0.0
