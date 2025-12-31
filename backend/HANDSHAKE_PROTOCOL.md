# Maestra Handshake Protocol v1

**Status:** Draft  
**Version:** 1.0  
**Last Updated:** 2025-12-30

---

## Overview

The Handshake Protocol enables secure, authenticated communication between:
- **Maestra UI** (public on Fly.io, or local dev at localhost:5000)
- **Local Companion Service** (user's machine, port 8826)
- **Maestra Backend** (Fly.io production, or local single-port gateway at localhost:8825)

This allows alpha users with local 8825 libraries to unlock advanced features while maintaining security (no raw library/Dropbox exposure).

### Single-Port Gateway Update (v1.1)

With the consolidated single-port local gateway, development workflows now support:
- **Local Development:** UI (localhost:5000) → Backend (localhost:8825) → Conversation Hub
- **Production:** UI (maestra.8825.systems) → Backend (Fly.io) → Conversation Hub
- **Local Companion:** Always on localhost:8826 (independent of backend location)

---

## Architecture

### Production Setup

```
┌─────────────────────────────────────┐
│  Maestra UI                         │
│  (maestra.8825.systems on Fly.io)   │
└──────────┬──────────────────────────┘
           │
           ├─→ Request 1: POST /handshake (to localhost:8826)
           │   (parallel, non-blocking)
           │
           └─→ Request 2: POST /api/maestra/advisor/ask (to Fly.io)
               (parallel, required)

┌──────────────────────────────────────────────────────────────┐
│ Local Machine (User's Computer)                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Local Companion Service (port 8826)                    │ │
│  │                                                        │
│  │ - Reads 8825 library (iCloud SQLite)                  │ │
│  │ - Accesses Jh Brain (port 5160)                       │ │
│  │ - Runs MCPs (stdio)                                   │ │
│  │ - Returns summaries (not raw data)                    │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ Fly.io (Hosted Backend)                                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Maestra Backend (maestra-backend-8825-systems.fly.dev) │ │
│  │                                                        │
│  │ - Verifies JWT from handshake                         │ │
│  │ - Tracks session capabilities                         │ │
│  │ - Calls LLM with context from local companion         │ │
│  │ - Persists conversations to Conversation Hub          │ │
│  │ - Returns response to UI                              │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Local Development Setup (Single-Port Gateway)

```
┌──────────────────────────────────────┐
│  Maestra UI (Dev)                    │
│  (localhost:5000)                    │
└──────────┬───────────────────────────┘
           │
           ├─→ Request 1: POST /handshake (to localhost:8826)
           │   (parallel, non-blocking)
           │
           └─→ Request 2: POST /api/maestra/advisor/ask (to localhost:8825)
               (parallel, required)

┌──────────────────────────────────────────────────────────────┐
│ Local Machine (Developer's Computer)                         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Local Companion Service (port 8826)                    │ │
│  │ - Reads 8825 library (iCloud SQLite)                  │ │
│  │ - Accesses Jh Brain (port 5160)                       │ │
│  │ - Runs MCPs (stdio)                                   │ │
│  │ - Returns summaries (not raw data)                    │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Single-Port Local Gateway (port 8825)                  │ │
│  │ - Maestra Backend (FastAPI)                           │ │
│  │ - ConversationHub integration                         │ │
│  │ - /conversation/* endpoints                           │ │
│  │ - /api/maestra/advisor/ask endpoint                   │ │
│  │ - Loads team LLM env (OpenRouter, OpenAI, Anthropic)  │ │
│  │ - Persists to ~/.8825/conversations/                  │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ ConversationHub Storage                                │ │
│  │ - ~/.8825/conversations/main.json                      │ │
│  │ - ~/.8825/conversations/index.json                     │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Handshake Flow

### Step 1: UI Detects Local Companion & Backend

**Trigger:** User opens Maestra UI (production or local dev)

**Backend Detection:**
```javascript
// Determine backend URL based on environment
const API_BASE = 
  process.env.VITE_MAESTRA_API ||  // Set to localhost:8825 for local dev
  'https://maestra-backend-8825-systems.fly.dev';  // Default to production

// For local development:
// export VITE_MAESTRA_API=http://localhost:8825
```

**UI Action:**
```javascript
// Try to reach local companion (non-blocking, 1s timeout)
const handshakePromise = fetch('http://localhost:8826/handshake', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    version: '1',
    user_agent: 'maestra-ui/1.0'
  }),
  signal: AbortSignal.timeout(1000)
})
  .then(r => r.json())
  .catch(() => null); // Timeout or error = no local companion

// Fire backend request in parallel (doesn't wait for local)
const backendPromise = fetch(`${API_BASE}/api/maestra/advisor/ask`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    session_id: sessionId,
    question: userMessage,
    mode: 'quick'
  })
});

// Wait for both (or timeout on local)
const [handshakeResult, backendResponse] = await Promise.all([
  handshakePromise,
  backendPromise
]);
```

**Key Points:**
- Backend URL is configurable via `VITE_MAESTRA_API` environment variable
- Local companion detection is always non-blocking (1s timeout)
- Backend request is required; local companion is optional
- Works identically in production and local development

### Step 2: Local Companion Responds

**Endpoint:** `POST http://localhost:8826/handshake`

**Request:**
```json
{
  "version": "1",
  "user_agent": "maestra-ui/1.0"
}
```

**Response (200 OK):**
```json
{
  "library_id": "lib_sha256_abc123def456",
  "jwt": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "capabilities": [
    "context_for_query",
    "open_loops",
    "proactive_suggestions",
    "capture_ingest"
  ],
  "version": "1",
  "timestamp": "2025-12-30T22:30:00Z"
}
```

**Response (timeout/error):**
```
null  // UI treats as "no local companion"
```

### Step 3: UI Forwards Handshake to Backend

**Endpoint:** `PUT https://maestra-backend-8825-systems.fly.dev/session/{session_id}/capabilities`

**Request:**
```json
{
  "library_id": "lib_sha256_abc123def456",
  "jwt": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "capabilities": [
    "context_for_query",
    "open_loops",
    "proactive_suggestions",
    "capture_ingest"
  ]
}
```

**Response (200 OK):**
```json
{
  "session_id": "sess_xyz789",
  "status": "authenticated",
  "library_id": "lib_sha256_abc123def456",
  "capabilities_enabled": [
    "context_for_query",
    "open_loops",
    "proactive_suggestions",
    "capture_ingest"
  ]
}
```

### Step 4: Backend Uses Local Context

When processing advisor requests for authenticated sessions, backend:

1. Checks if session has `context_for_query` capability
2. If yes, calls local companion: `GET http://localhost:8826/context-for-query?q=<query>`
3. Receives K-ID pointers + summary
4. Injects into LLM prompt
5. Returns enhanced response

---

## JWT Structure

**Algorithm:** HS256  
**Secret:** Stored in local companion (never transmitted)  
**Payload:**

```json
{
  "iss": "maestra-local-companion",
  "sub": "library_id",
  "library_id": "lib_sha256_abc123def456",
  "version": "1",
  "iat": 1735689000,
  "exp": 1735775400,
  "capabilities": [
    "context_for_query",
    "open_loops",
    "proactive_suggestions",
    "capture_ingest"
  ]
}
```

**Verification:**
- Backend has public key (or shared secret) for verification
- Checks `exp` (1-day TTL)
- Checks `library_id` matches request

---

## Local Companion Endpoints

### `POST /handshake`

Returns JWT + capabilities. Called once per session.

**Response:** See Step 2 above.

---

### `GET /context-for-query?q=<query>`

Returns relevant K-IDs and summary for a query.

**Request:**
```
GET http://localhost:8826/context-for-query?q=PDF+rendering
```

**Response (200 OK):**
```json
{
  "query": "PDF rendering",
  "relevant_k_ids": ["K-123", "K-456"],
  "relevant_d_ids": ["D-789"],
  "summary": "Last discussed PDF rendering on Dec 22. Decided against WeasyPrint, considering Typst.",
  "confidence": 0.85,
  "timestamp": "2025-12-30T22:30:00Z"
}
```

**Response (timeout/error):**
```
null  // Backend continues without local context
```

---

### `GET /open-loops`

Returns open loops for session continuity.

**Request:**
```
GET http://localhost:8826/open-loops
```

**Response (200 OK):**
```json
{
  "open_loops": [
    {
      "id": "L-001",
      "title": "Finalize PDF library choice",
      "created_at": "2025-12-22T10:00:00Z",
      "last_mentioned": "2025-12-30T15:30:00Z"
    },
    {
      "id": "L-002",
      "title": "Configure DNS for api.8825.systems",
      "created_at": "2025-12-28T14:00:00Z",
      "last_mentioned": "2025-12-30T20:00:00Z"
    }
  ],
  "timestamp": "2025-12-30T22:30:00Z"
}
```

---

### `GET /proactive-suggestions`

Returns suggestions based on recent work.

**Request:**
```
GET http://localhost:8826/proactive-suggestions
```

**Response (200 OK):**
```json
{
  "suggestions": [
    {
      "title": "You've been working on PDF rendering",
      "action": "Compare Typst vs WeasyPrint",
      "confidence": 0.9,
      "source": "Recent decisions"
    },
    {
      "title": "DNS configuration pending",
      "action": "Finalize api.8825.systems setup",
      "confidence": 0.8,
      "source": "Open loops"
    }
  ],
  "timestamp": "2025-12-30T22:30:00Z"
}
```

---

## Error Handling

### Local Companion Unavailable

**Scenario:** User's machine is offline or companion service crashed.

**Behavior:**
- UI timeout (1 second) on `/handshake` call
- Backend receives `null` from UI
- Session continues without local context
- Backend returns stub responses (graceful degradation)
- UI shows "Offline mode" indicator

### JWT Verification Fails

**Scenario:** JWT is expired, tampered, or invalid.

**Behavior:**
- Backend rejects JWT
- Session reverts to anonymous mode
- User can continue but without enhanced features
- Backend logs security event

### Network Latency

**Scenario:** Local companion responds slowly.

**Timeout:** 1 second (UI side)  
**Fallback:** Backend continues without local context

---

## Security Considerations

1. **JWT Secret:** Stored locally, never transmitted over network
2. **No Raw Data:** Local companion returns only summaries (K-IDs, not content)
3. **HTTPS Only:** Backend enforces HTTPS for all requests
4. **CORS:** Local companion allows only localhost:* origins
5. **TTL:** JWT expires after 1 day (forces re-handshake)
6. **Audit:** All handshakes logged with timestamp + library_id

---

## Local Development Setup

### Single-Port Gateway Configuration

For local development with the consolidated single-port gateway:

**1. Start the local backend (port 8825):**
```bash
cd 8825_core/tools/maestra_backend
launchctl load ~/Library/LaunchAgents/com.8825.maestra-backend.plist
# Or manually:
python3 -m uvicorn server:app --host 0.0.0.0 --port 8825
```

**2. Configure UI to use local backend:**
```bash
cd apps/maestra.8825.systems
export VITE_MAESTRA_API=http://localhost:8825
npm run dev
# UI will be available at http://localhost:5000
```

**3. Verify local backend is running:**
```bash
curl http://localhost:8825/openapi.json | jq '.info.title'
# Expected: "8825 Backend"
```

**4. Test single-port gateway endpoints:**
```bash
# Test /conversation/ask
curl -s -X POST http://localhost:8825/conversation/ask \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "main",
    "message": "test",
    "user_id": "dev",
    "surface_id": "web",
    "mode": "quick"
  }' | jq .

# Test /conversation/context
curl -s -X POST http://localhost:8825/conversation/context \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "main", "max_messages": 5}' | jq .
```

### Environment Variables

**Frontend (.env.local):**
```bash
VITE_MAESTRA_API=http://localhost:8825  # Local backend
# or
VITE_MAESTRA_API=https://maestra-backend-8825-systems.fly.dev  # Production
```

**Backend (8825-Team/config/secrets/llm.env):**
```bash
OPENROUTER_API_KEY=sk-or-...
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
LLM_PROVIDER=openrouter
LLM_MODEL=openrouter/meta-llama/llama-3.1-70b-instruct
```

### Conversation Persistence

Conversations are stored locally during development:
```bash
# View conversation storage
ls -la ~/.8825/conversations/

# Inspect a conversation
cat ~/.8825/conversations/main.json | jq .

# Clear conversations (if needed)
rm -rf ~/.8825/conversations/*
```

### Debugging

**Check backend logs:**
```bash
tail -f /tmp/maestra_backend.log
tail -f /tmp/maestra_backend.error.log
```

**Verify local companion (if available):**
```bash
curl -s -X POST http://localhost:8826/handshake \
  -H "Content-Type: application/json" \
  -d '{"version": "1", "user_agent": "test"}' | jq .
```

**Check conversation hub import:**
```bash
python3 -c "from conversation_hub import ConversationHub; print('OK')"
```

---

## Implementation Checklist

### Local Companion (Port 8826)
- [ ] `/handshake` endpoint (returns JWT + capabilities)
- [ ] `/context-for-query` endpoint (returns K-IDs + summary)
- [ ] `/open-loops` endpoint (returns open loops)
- [ ] `/proactive-suggestions` endpoint (returns suggestions)

### Backend (Port 8825 local / Fly.io production)
- [x] JWT verification in session management
- [x] `PUT /session/{id}/capabilities` endpoint
- [x] `/api/maestra/advisor/ask` endpoint (canonical)
- [x] `/conversation/ask` endpoint (single-port gateway)
- [x] `/conversation/context` endpoint (single-port gateway)
- [x] `/conversation/sync` endpoint (single-port gateway)
- [x] ConversationHub integration
- [x] Team LLM env loading

### UI (Frontend)
- [x] Parallel handshake + advisor request
- [x] Backend URL configuration via VITE_MAESTRA_API
- [x] Conversation history passing in client_context
- [x] Graceful degradation without local companion
- [ ] "Offline mode" indicator (future)

### Testing
- [ ] E2E handshake flow (local + production)
- [ ] JWT expiration handling
- [ ] Network timeout handling
- [ ] Local development workflow
- [ ] Cross-surface conversation continuity

---

## Future Enhancements

- [ ] Refresh token for long-lived sessions
- [ ] Capability negotiation (client requests, server grants)
- [ ] MCP chaining (local companion chains multiple MCPs)
- [ ] Shared context across alpha users (anonymized)
- [ ] Offline mode (local companion works without internet)
