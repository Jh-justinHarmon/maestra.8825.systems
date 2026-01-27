# Maestra Architecture

**Last Updated**: 2026-01-27  
**Purpose**: Document current and intended structure of Maestra surfaces and contracts

---

## Definition of Surface

A **surface** is a user-facing interface that provides access to Maestra's intelligence layer. Surfaces are thin clients that:

- Capture user intent and context
- Send requests to the Maestra backend
- Display responses to the user
- Maintain session continuity

Surfaces do NOT contain intelligence, memory, or decision-making logic. All reasoning happens in the backend.

---

## Current Surfaces

### 1. Web App (Canonical)

**Location**: `src/`  
**Status**: Production  
**Platform**: Browser (React/TypeScript)

**Capabilities**:
- Full chat interface
- Session management
- Quad-core detection
- Mode selection
- Agent transparency
- Context capture

**Contract**: Advisor-compatible ✅

---

### 2. Browser Extension (Canonical)

**Location**: `extension/`  
**Status**: Production  
**Platform**: Chrome/Firefox (Manifest V3)

**Capabilities**:
- Web page context capture
- Overlay chat interface
- Background service worker
- Content script injection

**Contract**: Advisor-compatible ✅ (with missing endpoints)

**Known gaps**:
- Expects `/api/maestra/capture` (not implemented)
- Expects `/api/maestra/conversation/{id}` (not implemented)

---

### 3. Figma v2 (Planned)

**Location**: `surfaces/figma-v2/`  
**Status**: Planned  
**Platform**: Figma/FigJam plugin

**Capabilities** (intended):
- Whiteboard context capture
- Design file metadata
- Selection-aware queries
- Advisor-compatible requests

**Contract**: Advisor-compatible ✅ (by design)

---

## Experimental Surfaces

### Figma Surface v1 (Experimental)

**Location**: `8825/experiments/maestra/figma-surface-v1/` (to be moved)  
**Status**: Experimental  
**Platform**: Figma/FigJam plugin

**Contract**: Advisor-incompatible ❌

**Reason**: Uses custom `/api/reasoning` endpoint not present in canonical backend.

**Preservation**: Kept for reference, not for production use.

---

## Surface Contract Requirements

**All production surfaces must speak the Advisor contract.**

This means:
- Use canonical endpoint: `POST /api/maestra/advisor/ask`
- Send `AdvisorAskRequest` schema
- Receive `AdvisorAskResponse` schema
- Include `session_id`, `question`, `mode`, `client_context`

Surfaces that do not speak the Advisor contract are experimental and cannot be promoted to production.

---

## Directory Structure

```
apps/maestra.8825.systems/
├── backend/              # Maestra business logic
├── src/                  # Web app surface (canonical)
├── extension/            # Browser extension surface (canonical)
├── surfaces/             # Additional surfaces
│   └── figma-v2/         # Figma v2 surface (planned)
├── contracts/            # API contracts
│   ├── advisor.md        # Advisor contract (authoritative)
│   └── session.md        # Session contract
└── ARCHITECTURE.md       # This file
```

---

## Backend Architecture

### Layer 1: Gateway
**Location**: `8825/system/backend_8825/`  
**Role**: HTTP routing, auth, observability

### Layer 2: Maestra Business Logic
**Location**: `backend/`  
**Role**: Advisor intelligence, epistemic grounding, quad-core, orchestration

### Layer 3: Shared Infrastructure
**Location**: `8825/system/`  
**Role**: Identity, memory, agents, routing

---

## Design Principles

1. **Surfaces are thin clients** - No local intelligence
2. **Backend is the brain** - All reasoning happens server-side
3. **Contracts are authoritative** - Surfaces must conform to backend contracts
4. **Sessions are surface-agnostic** - Session state is backend-managed
5. **One advisor contract** - All production surfaces use the same API

---

## Adding a New Surface

To add a new production surface:

1. Create directory under `surfaces/{surface-name}/`
2. Document contract in `surfaces/{surface-name}/CONTRACT.md`
3. Ensure Advisor contract compatibility
4. Add to this document's "Current Surfaces" section
5. Update `surfaces/{surface-name}/status.json`

Experimental surfaces should be placed in `8825/experiments/maestra/`.

---

**This document describes current and intended structure. It is not aspirational beyond explicitly planned surfaces.**
