# Figma v2 Surface (Planned)

**Status**: Planned  
**Created**: 2026-01-27  
**Purpose**: Advisor-compatible whiteboard surface for Figma/FigJam

---

## Purpose

Provide an **Advisor-compatible whiteboard surface** that allows users to interact with Maestra intelligence directly from Figma and FigJam design files.

This surface will speak the canonical Advisor contract (`POST /api/maestra/advisor/ask`) and integrate seamlessly with other Maestra surfaces (web app, browser extension).

---

## Differences from Web App

### Richer Selection Context

**Web App Context**:
- URL
- Page title
- Text selection

**Figma v2 Context**:
- File name
- Page/canvas name
- Selected nodes (frames, components, text, shapes)
- Node properties (name, type, dimensions)
- Layer hierarchy
- FigJam sticky notes and connectors

**Why this matters**: Figma context is inherently visual and structural. The advisor needs to understand design artifacts, not just text.

### Board Visibility

**Web App**: Linear chat interface, no spatial awareness

**Figma v2**: 
- Anchored to canvas
- Aware of visible viewport
- Can reference specific nodes by name
- Understands spatial relationships

**Why this matters**: Design work is spatial. Questions like "What's the purpose of this component?" require understanding what the user is looking at.

---

## Explicit Non-Goals

### ❌ No New Intelligence

Figma v2 will NOT introduce new intelligence or reasoning capabilities. It uses the same Advisor backend as all other surfaces.

**Rationale**: Intelligence lives in the backend, not the surface. Adding surface-specific intelligence creates fragmentation and maintenance burden.

### ❌ No Separate Backend

Figma v2 will NOT have its own backend or API endpoints. It uses the canonical Maestra backend at `POST /api/maestra/advisor/ask`.

**Rationale**: All surfaces must speak the same contract to ensure session continuity and consistent behavior.

### ❌ No Local Data Storage

Figma v2 will NOT store conversation history, user preferences, or any persistent data locally.

**Rationale**: Sessions are backend-managed and surface-agnostic. Local storage breaks cross-surface continuity.

### ❌ No Autonomous Actions

Figma v2 will NOT modify design files without explicit user confirmation.

**Rationale**: Design tools require user control. Autonomous changes violate user trust and Figma plugin guidelines.

### ❌ No Custom Protocols

Figma v2 will NOT introduce custom request/response formats or communication protocols.

**Rationale**: All surfaces must use the Advisor contract. Custom protocols create incompatibility and technical debt.

---

## Implementation Principles

### 1. Thin Client Architecture
- UI and context capture only
- All intelligence in backend
- No local decision-making

### 2. Advisor Contract Compliance
- Use `POST /api/maestra/advisor/ask`
- Send `AdvisorAskRequest`
- Receive `AdvisorAskResponse`
- Include Figma context in `client_context` field

### 3. Read-Only by Default
- Read Figma API for context
- No writes without user confirmation
- Explicit user intent required for modifications

### 4. Session Continuity
- Use backend-managed sessions
- Support cross-surface session access
- No local session state

---

## Example Context Payload

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user_jh",
  "message": "What's the purpose of this component?",
  "mode": "quick",
  "client_context": {
    "surface": "figma_v2",
    "file_name": "Design System v2",
    "page_name": "Components",
    "editor_type": "figma",
    "selected_nodes": [
      {
        "id": "123:456",
        "type": "FRAME",
        "name": "Button/Primary",
        "width": 120,
        "height": 40
      }
    ],
    "viewport": {
      "x": 0,
      "y": 0,
      "zoom": 1.0
    }
  }
}
```

---

## Success Criteria

Figma v2 is successful when:

1. ✅ Uses canonical Advisor contract (no custom endpoints)
2. ✅ Sessions work across web app, extension, and Figma
3. ✅ Context includes Figma-specific metadata
4. ✅ No local intelligence or storage
5. ✅ Read-only by default, writes require confirmation
6. ✅ Passes Figma plugin review guidelines

---

## Related Documents

- **Advisor Contract**: `../../contracts/advisor.md`
- **Session Contract**: `../../contracts/session.md`
- **Surface Taxonomy**: `../../ARCHITECTURE.md`
- **Figma v1 (Reference)**: `../../../experiments/maestra/figma-surface-v1/`

---

**This is intent documentation only. No implementation has started.**
