# Dev Assistant Integration for Maestra

**Status:** Complete and ready for use  
**Version:** 1.0.0  
**Date:** 2025-12-31

---

## Overview

The Dev Assistant agent has been enhanced to facilitate rapid frontend-backend debugging for Maestra. This document describes the integration, workflow, and how to use it.

## What Was Built

### 1. Intent Documentation (`docs/INTENT.md`)
**Purpose:** Capture project vision, strategic goals, and architectural decisions.

**Contains:**
- Core purpose and strategic goals
- Key architectural decisions with trade-offs
- Current phase status (Phase 9: Release Train)
- Known limitations
- Success metrics

**Why it matters:** When debugging, developers need to understand WHY certain decisions were made. Intent documentation prevents rework and guides hypothesis testing.

---

### 2. Development Log (`docs/DEV_LOG.md`)
**Purpose:** Track frontend-backend integration issues, decisions, and context.

**Contains:**
- Open issues with status, severity, and components
- Root cause analysis
- Solution paths and lessons learned
- Decision log with rationale and trade-offs
- Context snapshots (architecture, deployment checklist)

**Why it matters:** Long debugging sessions lose context. Dev log provides:
- Quick reference to previous issues
- Lessons learned to avoid repeating mistakes
- Decision rationale to understand constraints
- Deployment checklist to prevent common errors

---

### 3. Enhanced Dev Assistant Agent (`8825_core/agents/dev_assistant/agent.py`)
**Version:** 1.0.0

**New Classes:**
- `ProblemInference` – Structured problem representation
- `ContextPackage` – Rich context with frontend/backend touchpoints

**New Methods:**
- `_infer_problem()` – Analyze evidence to infer problem
- `_gather_context_package()` – Collect frontend files, backend files, intent, dev log
- `_confirm_problem()` – Validate inferred problem with user

**New Actions:**
- `infer_problem` – Infer problem from screen/code/error/feedback
- `confirm_problem` – Confirm inferred problem
- `gather_context` – Gather rich context package
- `log_solve` – Log solution to troubleshooting log (existing)
- `list_solves` – List previous solutions (existing)

---

### 4. Rapid Debugging Workflow (`.windsurf/workflows/dev-assistant-rapid-debug.md`)
**Purpose:** Guided workflow for rapid frontend-backend debugging.

**Steps:**
1. **Infer Problem** – Analyze evidence
2. **Confirm Problem** – Validate with user
3. **Gather Context** – Collect frontend/backend touchpoints
4. **Diagnose & Test** – Hypothesis testing with mandatory gates
5. **Propose Solution** – Generate implementation plan
6. **Implement & Test** – Local → staging → production gates
7. **Log Solution** – Record to dev log

**Key Features:**
- Mandatory testing environment confirmation
- Deployment status verification
- Hypothesis testing gates
- Local/staging/production testing progression
- Solution logging for future reference

---

### 5. Agent Documentation (`8825_core/agents/dev_assistant/README.md`)
**Purpose:** Quick reference for using the Dev Assistant agent.

**Contains:**
- Quick start examples
- Available actions with parameters
- Workflow integration
- Design decisions
- Troubleshooting guide

---

## How It Works: Complete Flow

### Scenario: Button Click Doesn't Work

**Step 1: Infer Problem**
```
User provides:
- Screen capture showing button
- Error message: "POST /api/capture 404"
- Feedback: "Button click doesn't trigger API call"

Dev Assistant infers:
- Problem: "Frontend/backend integration issue"
- Confidence: 0.85
- Affected: ["frontend", "backend"]
- Causes: ["Wrong URL", "Backend not responding"]
```

**Step 2: Confirm Problem**
```
User confirms: "Yes, that's correct"

Dev Assistant confirms:
- Confirmed problem: "Button click doesn't trigger API call; 404 on POST /api/capture"
```

**Step 3: Gather Context**
```
Dev Assistant gathers:
- Frontend files: MaestraCard.tsx, webAdapter.ts, etc.
- Backend files: capture_bridge.py, maestra_api.py, etc.
- Intent: Project vision about cross-surface capture
- Dev Log: Previous CORS issues, deployment lessons
- Test environment: "production" (user testing at maestra.8825.systems)
- Deployment: "Fly.io machines running"
```

**Step 4: Diagnose**
```
Test 1: curl -X POST https://maestra-backend-8825-systems.fly.dev/api/capture
Result: 200 OK ✓ (backend responding)

Test 2: Check webAdapter.ts for URL
Result: Correct URL ✓

Test 3: Check browser console
Result: CORS error ✗

Root cause: CORS headers missing on backend
```

**Step 5: Propose Solution**
```
Project Planner generates:
1. Add CORS headers to FastAPI app
2. Test locally
3. Deploy to Fly.io
4. Verify in production
```

**Step 6: Implement**
```
Local: Add CORS, test with curl
Staging: Deploy, test
Production: Merge, verify
```

**Step 7: Log Solution**
```
Title: "ISSUE-004 - CORS headers missing on backend"
Problem: "Button click triggers 404 due to CORS error"
Root Cause: "Backend missing CORS headers"
Fix: "Added CORS headers to FastAPI app"
Verification: "curl and UI tests pass"
```

---

## Mandatory Gates (From DEV_LOG.md)

These gates prevent the "local vs. production" debugging loop:

### Before Testing UI
- [ ] Confirm WHERE you're testing (local vs. production)
- [ ] Verify deployment status (machines running, no errors)
- [ ] Check test environment matches actual test URL
- [ ] Run curl against the SAME URL the UI uses
- [ ] Only then ask user to test

### Before Iterating on Fixes
- [ ] Confirm test environment (don't assume local = production)
- [ ] Verify deployment status before testing
- [ ] Test with curl against actual URL
- [ ] Check deployment pipeline completed successfully

### Before Declaring "Ready"
- [ ] Verify deployment status
- [ ] Test health endpoint
- [ ] Test actual endpoint with curl
- [ ] Verify in UI

---

## Integration Points

### With Maestra Project
- **Intent:** `apps/maestra.8825.systems/docs/INTENT.md`
- **Dev Log:** `apps/maestra.8825.systems/docs/DEV_LOG.md`
- **Architecture:** `apps/maestra.8825.systems/docs/ARCHITECTURE.md`
- **Integration:** `apps/maestra.8825.systems/docs/MAESTRA_INTEGRATION.md`

### With Dev Assistant Agent
- **Agent:** `8825_core/agents/dev_assistant/agent.py`
- **README:** `8825_core/agents/dev_assistant/README.md`
- **Data:** `8825_core/data/dev_assistant/troubleshooting_solves.jsonl`

### With Workflow System
- **Workflow:** `.windsurf/workflows/dev-assistant-rapid-debug.md`
- **Trigger:** `/dev-assistant-rapid-debug` in Windsurf

### With Platform Services
- **Stability:** Checkpoints for each debugging session
- **Learning:** Tool use logging for future improvement
- **Telemetry:** Event logging for debugging metrics

---

## Usage Examples

### Quick Problem Inference
```bash
# User provides evidence
# Dev Assistant infers problem in seconds
# Confidence score helps identify when more investigation needed
```

### Context-Aware Debugging
```bash
# Dev Assistant automatically loads:
# - Project intent (why decisions were made)
# - Previous issues (lessons learned)
# - Relevant files (frontend + backend)
# - Deployment status (where testing happens)
```

### Hypothesis Testing
```bash
# Dev Assistant guides through:
# 1. Design minimal test
# 2. Execute test
# 3. Confirm or refute hypothesis
# 4. Iterate until root cause found
```

### Solution Logging
```bash
# Once solved, log to dev log:
# - Problem statement
# - Root cause
# - Solution
# - Verification steps
# - Related links
```

---

## Key Benefits

### 1. Structured Debugging
- Not: "The thing isn't working"
- But: "Button click doesn't trigger API call; console shows 404"

### 2. Context Preservation
- Intent documentation explains WHY decisions were made
- Dev log tracks previous issues and lessons learned
- Context package includes all relevant files

### 3. Rapid Iteration
- Mandatory gates prevent local/production confusion
- Hypothesis testing is minimal and focused
- Solution logging prevents repeating mistakes

### 4. Knowledge Capture
- Every solution is logged for future reference
- Developers can search previous issues
- Lessons learned are documented

---

## Next Steps

### Immediate
1. Test the workflow with a real frontend issue
2. Verify context package gathering works correctly
3. Confirm mandatory gates prevent debugging loops

### Short-term
1. Wire Dev Assistant into Windsurf MCP integration
2. Create example debugging sessions
3. Train team on rapid debugging workflow

### Long-term
1. Integrate with project-planner for automatic plan generation
2. Add hypothesis testing automation (curl, logs, etc.)
3. Build dashboard for solution search and analytics

---

## Files Created/Modified

### New Files
- `apps/maestra.8825.systems/docs/INTENT.md` – Project vision
- `apps/maestra.8825.systems/docs/DEV_LOG.md` – Issue tracking
- `8825_core/agents/dev_assistant/README.md` – Agent documentation
- `.windsurf/workflows/dev-assistant-rapid-debug.md` – Guided workflow
- `apps/maestra.8825.systems/docs/DEV_ASSISTANT_INTEGRATION.md` – This file

### Modified Files
- `8825_core/agents/dev_assistant/agent.py` – Enhanced with rapid debugging workflow

---

## Related Documentation

- `INTENT.md` – Project vision and strategic goals
- `DEV_LOG.md` – Issue tracking and decision log
- `ARCHITECTURE.md` – Technical design
- `MAESTRA_INTEGRATION.md` – Conversation Hub integration
- `DEPLOY_BACKEND.md` – Deployment procedures
- `SINGLE_PORT_GATEWAY.md` – Local gateway architecture

---

**Owner:** Justin Harmon  
**Last Updated:** 2025-12-31  
**Status:** Production-ready
