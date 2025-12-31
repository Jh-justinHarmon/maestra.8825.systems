# Backend Synchronization Protocol v1
## Bidirectional Trust, State Continuity, and Seamless Telemetry

**Status:** Design  
**Version:** 1.0  
**Last Updated:** 2025-12-31

---

## Problem Statement

Current architecture has a gap: **local and hosted backends operate independently**, creating:
- **State divergence:** Conversations stored locally don't sync to hosted backend
- **Telemetry fragmentation:** Local operations invisible to hosted observability
- **Trust asymmetry:** No cryptographic proof that local backend is legitimate
- **Capability mismatch:** UI doesn't know which backend has which capabilities

**Goal:** Create a **locked-in relationship** where:
1. Local and hosted backends authenticate each other
2. State stays synchronized (conversations, sessions, decisions)
3. Operations are asymmetric (local-first for speed, hosted for scale)
4. Telemetry flows seamlessly in both directions

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                          Maestra UI                             │
│                    (localhost:5002 or hosted)                   │
└────────────────────┬────────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
    ┌─────────────┐         ┌──────────────────┐
    │   Local     │         │     Hosted       │
    │  Backend    │◄───────►│     Backend      │
    │ :8825       │ SYNC    │   (Fly.io)       │
    └─────────────┘         └──────────────────┘
         │                       │
         ├─ Conversations        ├─ Conversations
         ├─ Sessions             ├─ Sessions
         ├─ Telemetry            ├─ Telemetry
         └─ State                └─ State
```

---

## Core Concepts

### 1. Backend Identity & Cryptographic Binding

Each backend has a unique identity:

```python
# Local Backend Identity
{
  "backend_id": "local_sha256_<machine_id>",
  "backend_type": "local",
  "public_key": "-----BEGIN PUBLIC KEY-----\n...",
  "version": "1.0",
  "capabilities": ["offline", "fast_context", "local_capture"],
  "created_at": "2025-12-31T00:00:00Z"
}

# Hosted Backend Identity
{
  "backend_id": "hosted_sha256_fly_io",
  "backend_type": "hosted",
  "public_key": "-----BEGIN PUBLIC KEY-----\n...",
  "version": "1.0",
  "capabilities": ["scale", "persistence", "global_telemetry"],
  "created_at": "2025-12-31T00:00:00Z"
}
```

### 2. Session Binding Token (SBT)

When UI detects both backends, it creates a **Session Binding Token** that cryptographically links them:

```python
SBT = {
  "session_id": "sess_<uuid>",
  "local_backend_id": "local_sha256_<machine_id>",
  "hosted_backend_id": "hosted_sha256_fly_io",
  "user_id": "<user>",
  "created_at": "2025-12-31T00:00:00Z",
  "expires_at": "2025-12-31T08:00:00Z",  # 8-hour session
  "signature": "HMAC-SHA256(secret, all_above_fields)"
}
```

**Key property:** Both backends must validate the SBT signature to prove they're part of the same session.

### 3. Asymmetric Operations

**Local Backend (Primary for user interactions):**
- Fast context retrieval (instant, no network)
- Conversation persistence (local SQLite)
- Capture processing (direct library access)
- Offline capability

**Hosted Backend (Primary for scale/sharing):**
- Global telemetry aggregation
- Cross-user analytics
- Long-term persistence
- API gateway for external integrations

---

## Handshake Flow (Enhanced)

### Phase 1: UI Detects Both Backends

```javascript
// 1. Detect local backend
const localBackend = await fetch('http://localhost:8825/identity', {
  signal: AbortSignal.timeout(500)
}).then(r => r.json()).catch(() => null);

// 2. Detect hosted backend
const hostedBackend = await fetch(
  'https://maestra-backend-8825-systems.fly.dev/identity'
).then(r => r.json());

// 3. Create Session Binding Token
const sbt = {
  session_id: generateUUID(),
  local_backend_id: localBackend?.backend_id,
  hosted_backend_id: hostedBackend.backend_id,
  user_id: getCurrentUser(),
  created_at: new Date().toISOString(),
  expires_at: new Date(Date.now() + 8*3600*1000).toISOString()
};

// 4. Sign SBT with shared secret (from handshake)
sbt.signature = HMAC_SHA256(sharedSecret, JSON.stringify(sbt));
```

### Phase 2: Local Backend Registers with Hosted

```python
# Local backend calls hosted backend
POST https://maestra-backend-8825-systems.fly.dev/register-peer

{
  "backend_id": "local_sha256_<machine_id>",
  "public_key": "-----BEGIN PUBLIC KEY-----\n...",
  "capabilities": ["offline", "fast_context", "local_capture"],
  "sbt": {
    "session_id": "sess_<uuid>",
    "local_backend_id": "local_sha256_<machine_id>",
    "hosted_backend_id": "hosted_sha256_fly_io",
    "signature": "HMAC-SHA256(...)"
  }
}

# Hosted backend responds
{
  "status": "registered",
  "peer_id": "peer_<uuid>",
  "sync_endpoint": "https://maestra-backend-8825-systems.fly.dev/sync/peer_<uuid>",
  "telemetry_endpoint": "https://maestra-backend-8825-systems.fly.dev/telemetry/peer_<uuid>",
  "sync_interval_ms": 5000
}
```

### Phase 3: Hosted Backend Registers with Local

```python
# Hosted backend calls local backend (via UI relay or direct if accessible)
POST http://localhost:8825/register-peer

{
  "backend_id": "hosted_sha256_fly_io",
  "public_key": "-----BEGIN PUBLIC KEY-----\n...",
  "capabilities": ["scale", "persistence", "global_telemetry"],
  "sbt": { ... }
}

# Local backend responds
{
  "status": "registered",
  "peer_id": "peer_<uuid>",
  "sync_endpoint": "http://localhost:8825/sync/peer_<uuid>",
  "telemetry_endpoint": "http://localhost:8825/telemetry/peer_<uuid>"
}
```

---

## State Synchronization Protocol

### Conversation Sync (Bidirectional)

**Local → Hosted (every 5 seconds or on change):**

```python
POST https://maestra-backend-8825-systems.fly.dev/sync/peer_<uuid>

{
  "sync_id": "sync_<uuid>",
  "timestamp": "2025-12-31T00:05:00Z",
  "conversations": [
    {
      "conversation_id": "main",
      "version": 4,  # Lamport clock
      "messages": [
        {
          "id": "m1",
          "role": "user",
          "content": "What is dev assistant?",
          "timestamp": "2025-12-31T00:01:00Z",
          "surface": "web"
        },
        {
          "id": "m2",
          "role": "assistant",
          "content": "Dev assistant is...",
          "timestamp": "2025-12-31T00:01:05Z",
          "surface": "web",
          "source_backend": "local"  # ← Mark origin
        }
      ],
      "surfaces": ["web", "ios"],
      "last_modified": "2025-12-31T00:05:00Z"
    }
  ],
  "signature": "HMAC-SHA256(...)"
}

# Hosted backend responds
{
  "status": "synced",
  "acked_sync_id": "sync_<uuid>",
  "conflicts": [],  # If version mismatch
  "next_sync_in_ms": 5000
}
```

**Hosted → Local (on demand or periodic):**

```python
GET http://localhost:8825/sync/peer_<uuid>?since=<timestamp>

# Local backend responds
{
  "conversations": [ ... ],
  "last_sync": "2025-12-31T00:05:00Z"
}
```

### Conflict Resolution (CRDT-style)

If both backends modified the same conversation:

```python
# Conflict detected
{
  "conversation_id": "main",
  "local_version": 5,
  "hosted_version": 6,
  "conflict_type": "diverged_messages",
  "resolution_strategy": "merge_by_timestamp"
}

# Resolution: Merge messages by timestamp, keep both if different
# Mark with source_backend to track origin
```

---

## Telemetry Streaming (Asymmetric)

### Local → Hosted (Real-time Events)

Local backend streams telemetry to hosted backend:

```python
# WebSocket connection (persistent)
WS wss://maestra-backend-8825-systems.fly.dev/telemetry/peer_<uuid>

# Local backend sends events
{
  "event_type": "advisor_ask",
  "session_id": "main",
  "timestamp": "2025-12-31T00:05:00Z",
  "latency_ms": 1200,
  "model": "gpt-4",
  "tokens_used": 150,
  "cost_usd": 0.0045,
  "source_backend": "local"
}

{
  "event_type": "conversation_sync",
  "conversation_id": "main",
  "message_count": 4,
  "timestamp": "2025-12-31T00:05:05Z",
  "source_backend": "local"
}
```

### Hosted → Local (Aggregated Insights)

Hosted backend sends back aggregated telemetry:

```python
# Periodic (every 60 seconds)
POST http://localhost:8825/telemetry/insights

{
  "period": "2025-12-31T00:00:00Z to 2025-12-31T01:00:00Z",
  "global_stats": {
    "total_users": 42,
    "total_conversations": 156,
    "avg_latency_ms": 1050,
    "total_cost_usd": 12.34
  },
  "local_peer_stats": {
    "peer_id": "peer_<uuid>",
    "events_received": 45,
    "sync_success_rate": 0.98,
    "last_sync": "2025-12-31T00:59:00Z"
  }
}
```

---

## Capability Negotiation

When backends register, they declare capabilities:

```python
# Local backend capabilities
{
  "offline": true,           # Can operate without network
  "fast_context": true,      # Sub-100ms context retrieval
  "local_capture": true,     # Direct library access
  "conversation_storage": "sqlite",
  "max_concurrent_sessions": 10
}

# Hosted backend capabilities
{
  "offline": false,
  "fast_context": false,
  "local_capture": false,
  "conversation_storage": "postgres",
  "max_concurrent_sessions": 1000,
  "global_telemetry": true,
  "cross_user_analytics": true
}

# UI uses this to route requests
if (localBackend.capabilities.fast_context) {
  // Use local for context
} else {
  // Fall back to hosted
}
```

---

## Security Model

### Mutual Authentication

1. **Backend Identity:** Each backend has a unique `backend_id` (SHA256 of machine/deployment)
2. **Public Key Exchange:** Backends exchange public keys during registration
3. **SBT Signature:** Session Binding Token is signed with shared secret
4. **Message Signing:** All sync/telemetry messages are HMAC-signed

### Token Expiration & Refresh

```python
# SBT expires after 8 hours
if sbt.expires_at < now():
  # UI must re-handshake
  # Backends lose sync relationship
  # Forces re-authentication
```

### Revocation

If local backend is compromised:

```python
# Hosted backend can revoke peer
DELETE https://maestra-backend-8825-systems.fly.dev/peers/peer_<uuid>

# Local backend is immediately de-registered
# No more sync or telemetry
```

---

## Implementation Checklist

- [ ] **Local Backend:** Add `/identity` endpoint
- [ ] **Local Backend:** Add `/register-peer` endpoint
- [ ] **Local Backend:** Add `/sync/peer_<uuid>` endpoint
- [ ] **Local Backend:** Add `/telemetry/peer_<uuid>` endpoint
- [ ] **Hosted Backend:** Add `/register-peer` endpoint
- [ ] **Hosted Backend:** Add `/sync/peer_<uuid>` endpoint
- [ ] **Hosted Backend:** Add `/telemetry/peer_<uuid>` endpoint (WebSocket)
- [ ] **UI:** Detect both backends and create SBT
- [ ] **UI:** Pass SBT to both backends during registration
- [ ] **Conversation Hub:** Support `source_backend` field in messages
- [ ] **Telemetry:** Stream events from local to hosted
- [ ] **Conflict Resolution:** Implement CRDT-style merge
- [ ] **Tests:** End-to-end sync with both backends running

---

## Example Flow: User Sends Message

```
1. UI sends message to local backend (fast path)
   POST http://localhost:8825/api/maestra/advisor/ask
   
2. Local backend processes immediately
   - Retrieves context from local companion
   - Calls LLM (OpenRouter)
   - Stores in local SQLite
   - Returns response to UI (1.2s total)

3. Local backend syncs to hosted backend (background)
   POST https://maestra-backend-8825-systems.fly.dev/sync/peer_<uuid>
   - Sends conversation state
   - Hosted backend merges into Postgres
   
4. Local backend streams telemetry
   WS wss://maestra-backend-8825-systems.fly.dev/telemetry/peer_<uuid>
   - Sends event: advisor_ask, latency_ms: 1200, cost: $0.0045
   
5. Hosted backend aggregates telemetry
   - Adds to global stats
   - Sends insights back to local
   
6. If user opens UI on another device
   - Connects to hosted backend
   - Hosted backend has full conversation history
   - Seamless continuity
```

---

## Benefits

✅ **Locked-in Relationship:** Cryptographic binding via SBT  
✅ **State Continuity:** Bidirectional sync keeps conversations in sync  
✅ **Asymmetric Operations:** Local for speed, hosted for scale  
✅ **Seamless Telemetry:** Real-time events + aggregated insights  
✅ **Security:** Mutual authentication, token expiration, revocation  
✅ **Offline Capability:** Local backend works without hosted  
✅ **Multi-device:** Hosted backend enables cross-device continuity
