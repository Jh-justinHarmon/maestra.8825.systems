# Maestra Handshake Protocol v1

**Status:** Draft  
**Version:** 1.0  
**Last Updated:** 2025-12-30

---

## Overview

The Handshake Protocol enables secure, authenticated communication between:
- **Hosted Maestra** (public, on Fly.io)
- **Local Companion Service** (user's machine, port 8826)
- **Maestra Backend** (Fly.io, validates handshakes)

This allows alpha users with local 8825 libraries to unlock advanced features while maintaining security (no raw library/Dropbox exposure).

---

## Architecture

```
┌─────────────────────┐
│  Maestra UI         │
│  (Fly.io)           │
└──────────┬──────────┘
           │
           ├─→ Request 1: POST /handshake (to localhost:8826)
           │   (parallel)
           │
           └─→ Request 2: POST /api/maestra/advisor/ask (to Fly.io)
               (parallel)

┌──────────────────────────────────────────────────────────────┐
│ Local Machine                                                │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Local Companion Service (port 8826)                    │ │
│  │                                                        │ │
│  │ - Reads 8825 library (iCloud SQLite)                  │ │
│  │ - Accesses Jh Brain (port 5160)                       │ │
│  │ - Runs MCPs (stdio)                                   │ │
│  │ - Returns summaries (not raw data)                    │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ Fly.io (Hosted)                                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Maestra Backend                                        │ │
│  │                                                        │ │
│  │ - Verifies JWT from handshake                         │ │
│  │ - Tracks session capabilities                         │ │
│  │ - Calls LLM with context from local companion         │ │
│  │ - Streams response back to UI                         │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Handshake Flow

### Step 1: UI Detects Local Companion

**Trigger:** User opens maestra.8825.systems

**UI Action:**
```javascript
// Try to reach local companion (non-blocking)
const handshakePromise = fetch('http://localhost:8826/handshake', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    version: '1',
    user_agent: 'maestra-ui/1.0'
  })
})
  .then(r => r.json())
  .catch(() => null); // Timeout or error = no local companion

// Fire backend request in parallel (doesn't wait for local)
const backendPromise = fetch('https://maestra-backend-8825-systems.fly.dev/api/maestra/advisor/ask', {
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

## Implementation Checklist

- [ ] Local companion: `/handshake` endpoint
- [ ] Local companion: `/context-for-query` endpoint
- [ ] Local companion: `/open-loops` endpoint
- [ ] Local companion: `/proactive-suggestions` endpoint
- [ ] Backend: JWT verification in `session_manager.py`
- [ ] Backend: `PUT /session/{id}/capabilities` endpoint
- [ ] UI: Parallel handshake + advisor request
- [ ] UI: Context forwarding to streaming connection
- [ ] UI: "Offline mode" indicator
- [ ] Tests: E2E handshake flow
- [ ] Tests: JWT expiration handling
- [ ] Tests: Network timeout handling

---

## Future Enhancements

- [ ] Refresh token for long-lived sessions
- [ ] Capability negotiation (client requests, server grants)
- [ ] MCP chaining (local companion chains multiple MCPs)
- [ ] Shared context across alpha users (anonymized)
- [ ] Offline mode (local companion works without internet)
