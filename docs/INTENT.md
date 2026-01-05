# Maestra Project Intent & Vision

## Core Purpose
Maestra is a reusable, versioned conversation UI that works across web, Chrome extension, and iOS. It enables rapid context capture and synthesis across surfaces while maintaining a unified conversation history.

## Strategic Goals

### 1. Platform-Agnostic Conversation
- Single React component (`MaestraCard`) works on all surfaces
- Versioned API contract (`schema_version: "1"`) ensures consistency
- ISO 8601 timestamps for JSON safety
- No surface-specific hacks in core logic

### 2. Intelligent Context Capture
- Mode Registry detects page context (Replit, generic web, etc.)
- Confidence scoring for mode selection
- Surface-specific adapters (web, extension, iOS)
- Auto-capture to 8825 Library

### 3. Cross-Surface Continuity
- Start conversation on web, continue on extension
- Conversation Hub API syncs state across surfaces
- Unified conversation history
- Real LLM responses (OpenRouter, OpenAI, Anthropic)

### 4. Developer Experience
- Clear separation of concerns (Card, Adapters, Modes)
- Golden fixtures for regression testing
- CI/CD validation (TypeScript, build, fixtures)
- Performance budget: ≤200 KB gzip (currently 52.7 KB)

## Key Architectural Decisions

### Decision 1: Card + Adapter Pattern
**Why:** Single component works everywhere; surface-specific logic isolated in adapters.
**Trade-off:** More files, but cleaner separation.
**Validation:** All surfaces use same MaestraCard, different adapters.

### Decision 2: Versioned Contract
**Why:** JSON-safe, backward-compatible, enables multi-surface consistency.
**Trade-off:** Schema changes require migration planning.
**Validation:** All fixtures validate against schema v1.

### Decision 3: Mode Registry
**Why:** Deterministic, testable mode selection; no ad-hoc logic.
**Trade-off:** Adding new modes requires registry update.
**Validation:** Mode selection is pure function of page context.

### Decision 4: Local-First Testing
**Why:** Mock backend for UI testing; real backend for integration.
**Trade-off:** Mock responses don't reflect real performance.
**Validation:** E2E tests use mock backend; integration tests use real backend.

## Current Phase (Phase 9: Release Train)

- ✅ Core UI (MaestraCard) complete
- ✅ Mode Registry (default + Replit)
- ✅ Error Boundaries + Analytics
- ✅ Extension scaffolding (manifest + background worker)
- ✅ iOS architecture documented
- ✅ E2E tests (Playwright smoke tests)
- ✅ Golden fixtures (9 canonical fixtures)
- ⏳ Extension React compact card (Phase 6 continuation)
- ⏳ iOS Share Sheet implementation (Phase 7 continuation)
- ⏳ Storybook for component docs (Phase 9 continuation)

## Known Limitations

### Frontend
- Mock backend returns stub data (no real chat quality)
- No performance testing (load testing framework needed)
- Extension UI is placeholder (needs React compact card)
- iOS is architecture only (needs Xcode implementation)

### Backend
- Conversation Hub API (port 8826) not yet deployed
- No rate limiting on LLM calls
- No conversation cleanup/archival
- No multi-user isolation

## Next Immediate Actions

1. **Deploy Conversation Hub API** to production (port 8826)
2. **Build React compact card** for extension (Phase 6)
3. **Implement iOS Share Sheet** in Xcode (Phase 7)
4. **Add Storybook** for component documentation (Phase 9)
5. **Test cross-surface flows** (web → extension → iOS)

## Success Metrics

- ✅ Single codebase for all surfaces
- ✅ < 200 KB gzip bundle size
- ✅ Zero hardcoded paths (workspace-agnostic)
- ✅ All fixtures validate against schema v1
- ✅ CI/CD passes on every commit
- ⏳ E2E tests pass on all surfaces
- ⏳ Cross-surface continuity works (start web, continue extension)
- ⏳ Real LLM responses (not stubs)

## Related Documentation

- `ARCHITECTURE.md` – Technical design and data flow
- `MAESTRA_INTEGRATION.md` – Conversation Hub integration
- `DEPLOY_BACKEND.md` – Backend deployment guide
- `SINGLE_PORT_GATEWAY.md` – Local gateway architecture
- `REPO_LAYOUT.md` – File organization

---

**Last Updated:** 2025-12-31  
**Version:** 1.0.0  
**Owner:** Justin Harmon
