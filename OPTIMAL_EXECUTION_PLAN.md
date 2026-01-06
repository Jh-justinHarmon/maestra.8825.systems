# Maestra Gold Standard - Optimal Execution Plan

## Overview

Transform Maestra into the **premium 8825 experience** with tri-state connection hierarchy, Memory-Native Auth, rich markdown rendering, and deep library integration.

**Total Duration:** 12 working days (aggressive) / 18 days (comfortable)  
**Dependencies:** Local Sidecar, Local Backend, Hosted Backend, 8825 Library

---

## Critical Path

```
Day 1-2: Connection Hierarchy (unlocks everything else)
    ↓
Day 3-4: Library Integration (the core value proposition)
    ↓
Day 5-6: Markdown Rendering (visible quality improvement)
    ↓
Day 7-8: Memory-Native Auth (security + personalization foundation)
    ↓
Day 9-10: Error UX + Basic Tests (production readiness)
    ↓
Day 11-12: Deploy + Validate (ship it)
```

---

## Day 1-2: Tri-State Connection Hierarchy

**Goal:** Eliminate silent failures. Always know what mode you're in.

### Day 1: Frontend Connection Logic

**File:** `apps/maestra.8825.systems/src/adapters/webAdapter.ts`

**Tasks:**
1. Refactor `getApiBase()` to implement priority cascade:
   ```
   1. Try Sidecar handshake (localhost:8826) → Quad-Core
   2. Try Local Backend ping (localhost:8825) → Local Mode  
   3. Fall back to Hosted (fly.dev) → Cloud Only
   ```
2. Add connection state type:
   ```typescript
   type ConnectionMode = 'quad-core' | 'local' | 'cloud-only';
   ```
3. Expose `getConnectionMode()` for UI consumption
4. Add auto-reconnect logic with exponential backoff

**Deliverable:** `webAdapter.ts` with tri-state logic

### Day 2: Status Indicator UI

**Files:** 
- `src/components/ConnectionStatus.tsx` (new)
- `src/components/Header.tsx` (update)

**Tasks:**
1. Create `ConnectionStatus` component:
   - 🟢 Quad-Core Active
   - 🟡 Local Mode
   - ⚪ Cloud Only
2. Add hover tooltip showing:
   - Active capabilities
   - Connected services
   - Last handshake time
3. Wire into Header component
4. Add connection change notifications (toast)

**Deliverable:** Visible, always-accurate connection status

**Acceptance Test:**
```bash
# Kill sidecar
pkill -f "sidecar"
# UI should show 🟡 Local Mode within 2s

# Kill local backend
pkill -f "8825.*backend"
# UI should show ⚪ Cloud Only within 2s
```

---

## Day 3-4: Library Integration

**Goal:** Real retrieval from 8825 Library. The core value.

### Day 3: Backend Library Endpoints

**File:** `apps/maestra.8825.systems/backend/server.py`

**Tasks:**
1. Finalize `/api/library/{entry_id}` endpoint (already started)
2. Add `/api/library/search` for K/D/P queries
3. Implement path resolution:
   ```python
   # Priority order:
   # 1. Environment variable LIBRARY_PATH
   # 2. Relative path from backend
   # 3. Hardcoded fallback (dev only)
   ```
4. Add entry validation and error handling

**File:** `apps/maestra.8825.systems/backend/advisor.py`

**Tasks:**
1. Detect Entry ID patterns in user messages (16-char hex)
2. Fetch entry content before LLM call
3. Inject entry content into prompt with clear markers
4. Add entry to sources list in response

**Deliverable:** Backend can fetch and use library entries

### Day 4: Frontend Library Integration

**File:** `src/adapters/webAdapter.ts`

**Tasks:**
1. Add `fetchLibraryEntry(entryId: string)` method
2. Route to appropriate backend based on connection mode:
   - Quad-Core: via Sidecar capability
   - Local: via localhost:8825
   - Cloud: return "unavailable" error
3. Add library entry to context before sending message

**File:** `src/components/SourceCard.tsx` (new)

**Tasks:**
1. Create source citation card component:
   ```
   📚 Referenced: "Entry Title"
   Mode: Quad-Core • Confidence: 0.9
   Entry ID: 5ce9e4d4f0f23d90
   ```
2. Render in message stream when entries are used

**Deliverable:** End-to-end library retrieval working

**Acceptance Test:**
```
User: "Use Entry ID: 5ce9e4d4f0f23d90"
Expected: Answer references entry content + source card appears
```

---

## Day 5-6: Markdown Rendering

**Goal:** Fix raw `**text**` rendering. Look premium.

### Day 5: Markdown Parser Integration

**File:** `src/components/MessageRenderer.tsx` (new or refactor)

**Tasks:**
1. Install `react-markdown` + `remark-gfm` + `rehype-highlight`
2. Create streaming-aware markdown renderer:
   - Handle incomplete syntax gracefully
   - Apply 8825 design tokens
3. Support:
   - Headings (H1-H6)
   - Bold/italic/strikethrough
   - Code blocks with syntax highlighting
   - Lists (ordered/unordered)
   - Links
   - Tables

**Deliverable:** Markdown renders correctly in all messages

### Day 6: Message Layout Polish

**Files:**
- `src/components/Message.tsx`
- `src/styles/messages.css` (or Tailwind classes)

**Tasks:**
1. Clear visual separation: user vs assistant messages
2. Proper typography:
   - Max line width (~70 chars)
   - Comfortable line height
   - Readable font sizes
3. Source panel integration:
   - Collapsible "Sources" section per message
   - Shows all library entries + context used
4. Responsive design for mobile

**Deliverable:** Visually polished message experience

**Acceptance Test:**
```
Paste markdown with headings, bullets, code blocks
→ Renders correctly with proper styling
→ No raw ** or ``` visible
```

---

## Day 7-8: Memory-Native Auth

**Goal:** Enforce authenticated context. Prevent "dumb Maestra" for registered users.

### Day 7: Auth Flow Implementation

**File:** `apps/maestra.8825.systems/backend/auth.py` (new or update)

**Tasks:**
1. Implement Memory-Native Auth validation:
   - Check for auth anchor K-entry via Sidecar
   - Validate anchor signature/freshness
2. Create `/api/auth/handshake` endpoint:
   - Input: device fingerprint, requested capabilities
   - Output: session token, granted capabilities, user profile
3. Add mode enforcement:
   - Registered users (Justin, Becky) → refuse Cloud Only
   - Guest users → allow Cloud Only with warning

**File:** `src/adapters/webAdapter.ts`

**Tasks:**
1. Call auth handshake on startup
2. Store session token for subsequent requests
3. Handle auth failures with clear messaging

**Deliverable:** Memory-Native Auth working end-to-end

### Day 8: Personalization Foundation

**File:** `apps/maestra.8825.systems/backend/advisor.py`

**Tasks:**
1. Fetch user learning profile K-entry on auth
2. Cache profile in session state
3. Inject style preferences into system prompt:
   ```
   User preferences:
   - Style: bullet points with examples
   - Pace: detailed explanations
   - Tone: technical but approachable
   ```

**Deliverable:** Answers adapt to user preferences

**Acceptance Test:**
```
With "bullets + examples" profile:
→ Answers come as short bullets with concrete examples
→ Not walls of prose
```

---

## Day 9-10: Error UX + Basic Tests

**Goal:** Graceful degradation. Never leave user confused.

### Day 9: Error Handling

**File:** `src/components/ErrorBanner.tsx` (new)

**Tasks:**
1. Create error banner component with:
   - Clear error message
   - Suggested action
   - Retry button (where applicable)
2. Error categories:
   - Connection errors → "Trying Local Backend..."
   - Library errors → "Entry not found. Check ID."
   - Auth errors → "Please re-authenticate."
3. Toast notifications for transient errors

**File:** `src/adapters/webAdapter.ts`

**Tasks:**
1. Add retry logic with exponential backoff
2. Proper error classification and propagation
3. Fallback paths for each error type

**Deliverable:** All errors have clear user messaging

### Day 10: Critical Path Tests

**File:** `apps/maestra.8825.systems/tests/` (new directory)

**Tasks:**
1. Connection hierarchy test:
   ```typescript
   test('falls back to Local when Sidecar offline')
   test('falls back to Cloud when Local offline')
   test('reconnects when services restored')
   ```
2. Library retrieval test:
   ```typescript
   test('fetches entry by ID and includes in response')
   test('shows error for invalid entry ID')
   ```
3. Auth flow test:
   ```typescript
   test('completes handshake in <1.5s')
   test('refuses Cloud Only for registered users')
   ```

**File:** `.github/workflows/ci.yml` (update)

**Tasks:**
1. Add test job to CI pipeline
2. Fail build if critical tests fail

**Deliverable:** CI gates prevent regressions

---

## Day 11-12: Deploy + Validate

**Goal:** Ship it. Verify in production.

### Day 11: Deployment

**Tasks:**
1. Push all changes to GitHub
2. Verify CI passes
3. Deploy backend to Fly.io:
   ```bash
   cd apps/maestra.8825.systems/backend
   fly deploy
   ```
4. Deploy frontend (if separate):
   ```bash
   cd apps/maestra.8825.systems
   npm run build && fly deploy
   ```
5. Verify DNS routing still works

### Day 12: Production Validation

**Tasks:**
1. **Connection Test:**
   - Open maestra.8825.systems
   - Verify Quad-Core status (with local services running)
   - Kill sidecar → verify Local Mode
   - Kill local backend → verify Cloud Only warning
2. **Library Test:**
   - Ask about Entry ID 5ce9e4d4f0f23d90
   - Verify answer uses entry content
   - Verify source card appears
3. **Rendering Test:**
   - Ask complex question
   - Verify markdown renders correctly
4. **Auth Test:**
   - Verify Memory-Native Auth completes
   - Verify personalization applied

**Deliverable:** Production Maestra working as designed

---

## Post-Launch (Days 13+)

### Week 3: Security Hardening
- mTLS for Sidecar ↔ Backend
- JWT scoping for capabilities
- Boundary enforcement

### Week 4: Advanced Features
- Conversation threading
- Auto-summarization
- Universal capture schema

### Week 5: Observability
- Telemetry integration
- Synthetic probes
- Performance dashboards

### Week 6: Polish
- Accessibility audit
- Mobile optimization
- Documentation

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Sidecar not running | Local Mode fallback works |
| Library path issues | Multiple fallback paths + clear errors |
| Auth anchor missing | Guest mode with warning |
| Fly.io deployment fails | Local testing validates before deploy |
| Markdown parser issues | Fallback to plain text |

---

## Success Metrics

**Day 12 (MVP):**
- [ ] Tri-state connection working with visible status
- [ ] Entry ID retrieval working end-to-end
- [ ] Markdown rendering correctly
- [ ] Memory-Native Auth completing
- [ ] No silent failures (all errors have messaging)

**Week 6 (Gold Standard):**
- [ ] 95%+ Quad-Core success rate for registered users
- [ ] <2s response time for Entry ID retrieval
- [ ] Zero accessibility violations
- [ ] Comprehensive test coverage
- [ ] Production observability in place

---

## Quick Start

```bash
# Day 1 - Start with connection hierarchy
cd apps/maestra.8825.systems
code src/adapters/webAdapter.ts

# Run local services for testing
# Terminal 1: Local Backend
cd backend && python server.py

# Terminal 2: Local Sidecar (if available)
cd 8825_core/tools/capability_sidecar && python server.py

# Terminal 3: Frontend dev
npm run dev
```

**First commit message:**
```
feat(maestra): implement tri-state connection hierarchy

- Add Quad-Core → Local → Hosted fallback logic
- Add ConnectionStatus component with mode indicators
- Add auto-reconnect with exponential backoff

Part of Maestra Gold Standard initiative
```
