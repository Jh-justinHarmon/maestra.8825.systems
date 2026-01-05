# Single-Port Local Gateway: Complete Architecture Guide

## Overview

The single-port local gateway consolidates Maestra and Conversation Hub services under a single port (`localhost:8825`) for seamless local development and testing. This guide documents the complete wiring from frontend through backend, including deployment, conversation persistence, and cross-surface continuity.

**Key Achievement:** All `/conversation/*` endpoints now run on port 8825 with:
- ✅ Stable conversation IDs (e.g., "main")
- ✅ Real LLM responses (via team env keys)
- ✅ Persistent conversation history
- ✅ Cross-surface continuity

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      Frontend (React/TypeScript)                │
│                   maestra.8825.systems (Fly.io)                 │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ WebAdapter (src/adapters/WebAdapter.ts)                 │  │
│  │ - Detects local companion (localhost:8826)              │  │
│  │ - Sends messages to /api/maestra/advisor/ask            │  │
│  │ - Passes conversation history + context                 │  │
│  │ - Graceful degradation if local unavailable             │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP POST
                              │ /api/maestra/advisor/ask
                              │ (with client_context + conversation_history)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Backend (FastAPI) - Single Port 8825               │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ server.py (tools/maestra_backend/server.py)             │  │
│  │                                                          │  │
│  │ ✓ /api/maestra/advisor/ask (canonical endpoint)         │  │
│  │ ✓ /conversation/ask (single-port gateway)               │  │
│  │ ✓ /conversation/context (retrieve history)              │  │
│  │ ✓ /conversation/sync (mark surface active)              │  │
│  │                                                          │  │
│  │ Features:                                                │  │
│  │ - Loads team LLM env (llm_env_loader.py)               │  │
│  │ - Imports ConversationHub for persistence               │  │
│  │ - Routes to LLM via llm_router.py                       │  │
│  │ - Extracts decisions/questions from responses           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ├─────────────────────┐            │
│                              │                     │            │
│                              ▼                     ▼            │
│  ┌──────────────────────────┐  ┌──────────────────────────┐   │
│  │ ConversationHub          │  │ LLM Router               │   │
│  │ (conversation_hub/)      │  │ (llm_router.py)          │   │
│  │                          │  │                          │   │
│  │ - Manages conversations  │  │ - Routes to OpenRouter   │   │
│  │ - Persists to disk       │  │ - Fallback to OpenAI     │   │
│  │ - Indexes by ID          │  │ - Fallback to Anthropic  │   │
│  │ - Tracks surfaces        │  │ - Uses team env keys     │   │
│  │ - Extracts artifacts     │  │ - Enforces quota         │   │
│  └──────────────────────────┘  └──────────────────────────┘   │
│                              │                                  │
│                              └─────────────────────┐            │
│                                                    │            │
│                                                    ▼            │
│                          ┌──────────────────────────────────┐  │
│                          │ ~/.8825/conversations/           │  │
│                          │ - main.json (conversation data)  │  │
│                          │ - index.json (metadata)          │  │
│                          └──────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │
                    LaunchAgent Management
                    (com.8825.maestra-backend)
                    - Starts on boot
                    - Restarts on crash
                    - Logs to /tmp/
```

---

## Frontend Integration

### WebAdapter (`src/adapters/WebAdapter.ts`)

The frontend uses a unified adapter pattern for sending messages:

```typescript
// API endpoint configuration
const API_BASE = 
  process.env.VITE_MAESTRA_API || 
  'https://maestra-backend-8825-systems.fly.dev';

// Local companion detection (non-blocking, 1s timeout)
const LOCAL_COMPANION_BASE = 'http://localhost:8826';
```

#### Message Flow

1. **Handshake (parallel, non-blocking)**
   ```typescript
   POST http://localhost:8826/handshake
   {
     "version": "1",
     "user_agent": "maestra-ui/1.0"
   }
   ```
   - Returns JWT, library_id, capabilities
   - 1-second timeout (fails gracefully)
   - Enables local context features if available

2. **Local Context Fetch (parallel, 500ms timeout)**
   ```typescript
   GET http://localhost:8826/context-for-query?q=<message>
   ```
   - Retrieves local context if capability available
   - Falls back to empty context if unavailable
   - Non-blocking (doesn't delay main request)

3. **Backend Request (required)**
   ```typescript
   POST https://maestra-backend-8825-systems.fly.dev/api/maestra/advisor/ask
   {
     "session_id": "main",
     "question": "user message",
     "mode": "quick",
     "client_context": {
       "summary": "local context summary",
       "relevant": ["K-123", "K-456"],
       "selection": "user selection",
       "conversation_history": [
         { "role": "user", "content": "..." },
         { "role": "assistant", "content": "..." }
       ]
     }
   }
   ```

#### Key Features

- **Conversation History:** Last 5 messages passed as `client_context.conversation_history`
- **Graceful Degradation:** Works without local companion (falls back to empty context)
- **Non-blocking Handshake:** Local detection doesn't delay UX
- **Session Capabilities:** Registers capabilities for enhanced features

---

## Backend Endpoints

### Single-Port Gateway Endpoints

All endpoints run on `localhost:8825` (local) or `https://maestra-backend-8825-systems.fly.dev` (production).

#### 1. POST `/conversation/ask`

**Purpose:** Ask Maestra and persist to Conversation Hub

**Request:**
```json
{
  "conversation_id": "main",
  "message": "What is the 8825 philosophy?",
  "user_id": "justin_harmon",
  "surface_id": "web",
  "mode": "quick",
  "context_hints": [],
  "auto_capture": false
}
```

**Response:**
```json
{
  "success": true,
  "conversation_id": "main",
  "answer": "The 8825 philosophy emphasizes...",
  "sources": [
    {
      "title": "Jh Brain Context",
      "type": "knowledge",
      "confidence": 0.8,
      "excerpt": "..."
    }
  ],
  "trace_id": "e40aa1dd-07e1-4895-bfd9-019e3bf6af55",
  "mode": "quick",
  "processing_time_ms": 1013
}
```

**Implementation Details:**
- Creates conversation with caller-provided ID (stable IDs like "main")
- Uses `ConversationEnvelope` to persist with exact ID
- Appends user message to conversation
- Calls LLM via `advisor_ask` endpoint
- Appends assistant response
- Extracts trace_id and processing time

#### 2. POST `/conversation/context`

**Purpose:** Retrieve recent conversation history and derived insights

**Request:**
```json
{
  "conversation_id": "main",
  "max_messages": 10
}
```

**Response:**
```json
{
  "success": true,
  "conversation_id": "main",
  "topic": "What is the 8825 philosophy?",
  "surface_origins": ["web", "ios"],
  "message_count": 2,
  "recent_messages": [
    {
      "id": "m1",
      "role": "user",
      "surface": "web",
      "at": "2025-12-31T04:52:07.690974Z",
      "text": "What is the 8825 philosophy?",
      "links": [],
      "meta": { ... }
    },
    {
      "id": "m2",
      "role": "assistant",
      "surface": "web",
      "at": "2025-12-31T04:52:08.709558Z",
      "text": "The 8825 philosophy emphasizes...",
      "links": [],
      "meta": { ... }
    }
  ],
  "key_decisions": [],
  "open_questions": [
    "What specific aspects of the 8825 philosophy interest you?"
  ]
}
```

**Implementation Details:**
- Retrieves conversation by ID
- Returns recent messages (limited by `max_messages`)
- Extracts key decisions (assistant messages with decision keywords)
- Extracts open questions (assistant messages ending with "?")
- Shows all surfaces that have participated

#### 3. POST `/conversation/sync`

**Purpose:** Mark a surface as active on a conversation (enables cross-surface continuity)

**Request:**
```json
{
  "conversation_id": "main",
  "target_surface": "ios"
}
```

**Response:**
```json
{
  "success": true,
  "conversation_id": "main",
  "target_surface": "ios"
}
```

**Implementation Details:**
- Adds surface to conversation's surface list
- Updates `meta.updated_at` timestamp
- Preserves existing surfaces
- Non-destructive (idempotent)

### Canonical Endpoint (Production)

#### POST `/api/maestra/advisor/ask`

**Purpose:** Main endpoint for all Maestra queries (web, extension, iOS)

**Request:**
```json
{
  "session_id": "main",
  "question": "What is the 8825 philosophy?",
  "mode": "quick",
  "client_context": {
    "summary": "local context",
    "relevant": ["K-123"],
    "selection": "user selection",
    "conversation_history": [...]
  }
}
```

**Response:**
```json
{
  "answer": "The 8825 philosophy emphasizes...",
  "session_id": "main",
  "sources": [...],
  "trace_id": "...",
  "mode": "quick",
  "processing_time_ms": 1013
}
```

**Implementation Details:**
- Accepts `client_context` with conversation history
- Routes to LLM via `llm_router.py`
- Includes context in LLM prompt
- Returns sources and trace_id for debugging

---

## ConversationHub Integration

### Conversation Storage

Conversations are stored as JSON files in `~/.8825/conversations/`:

```
~/.8825/conversations/
├── main.json                 # Conversation data
├── index.json               # Metadata index
└── artifacts/               # Linked artifacts
```

### Conversation Structure

```json
{
  "id": "main",
  "session_id": "main",
  "topic": "What is the 8825 philosophy?",
  "messages": [
    {
      "id": "m1",
      "role": "user",
      "surface": "web",
      "at": "2025-12-31T04:52:07.690974Z",
      "text": "What is the 8825 philosophy?",
      "links": [],
      "meta": {
        "tokens": null,
        "model": null,
        "cost": null,
        "latency_ms": null,
        "extracted": false
      }
    }
  ],
  "meta": {
    "status": "active",
    "created_at": "2025-12-31T04:52:07.690974Z",
    "updated_at": "2025-12-31T04:52:08.709558Z",
    "tags": ["maestra"],
    "owner": "justin_harmon",
    "surfaces": ["web", "ios"],
    "extracted": false
  }
}
```

### Stable Conversation IDs

The single-port gateway uses caller-provided conversation IDs (e.g., "main") instead of generating UUIDs. This enables all surfaces to converge on the same conversation.

**Benefits:**
- All surfaces converge on same conversation
- Predictable conversation IDs
- No UUID collision issues
- Easy to reference in logs/debugging

---

## LLM Configuration

### Team Environment Variables

LLM keys are loaded from `8825-Team/config/secrets/llm.env`:

```bash
OPENROUTER_API_KEY=sk-or-...
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
LLM_PROVIDER=openrouter
LLM_MODEL=openrouter/meta-llama/llama-3.1-70b-instruct
DAILY_LLM_QUOTA=100
```

### Loading in Backend

The backend loads team env on startup via `llm_env_loader.py`, ensuring LLM keys are available without hardcoding.

### LLM Router

The `llm_router.py` module handles provider selection and fallback:

```
Priority order:
1. OpenRouter (if OPENROUTER_API_KEY set)
2. OpenAI (if OPENAI_API_KEY set)
3. Anthropic (if ANTHROPIC_API_KEY set)
4. Error (no provider configured)
```

---

## Deployment & LaunchAgent

### LaunchAgent Configuration

The `com.8825.maestra-backend` LaunchAgent starts the backend on boot and restarts on crash.

### Installation

```bash
# Copy plist to LaunchAgents
cp com.8825.maestra-backend.plist ~/Library/LaunchAgents/

# Load service
launchctl load ~/Library/LaunchAgents/com.8825.maestra-backend.plist

# Verify running
launchctl list | grep maestra-backend
```

### Management

```bash
# Check status
launchctl list com.8825.maestra-backend

# Restart
launchctl unload ~/Library/LaunchAgents/com.8825.maestra-backend.plist
launchctl load ~/Library/LaunchAgents/com.8825.maestra-backend.plist

# View logs
tail -f /tmp/maestra_backend.log
tail -f /tmp/maestra_backend.error.log
```

---

## Testing & Verification

### Smoke Tests

#### Test 1: /conversation/ask

```bash
curl -s -X POST http://localhost:8825/conversation/ask \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "main",
    "message": "test smoke",
    "user_id": "test_user",
    "surface_id": "web",
    "mode": "quick"
  }' | jq .
```

**Expected:**
- `"success": true`
- Real LLM response (not stub)
- `conversation_id: "main"`
- Processing time ~1000ms

#### Test 2: /conversation/context

```bash
curl -s -X POST http://localhost:8825/conversation/context \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "main",
    "max_messages": 5
  }' | jq .
```

**Expected:**
- `"success": true`
- Recent messages array
- Key decisions and open questions extracted
- Surface origins listed

#### Test 3: /conversation/sync

```bash
curl -s -X POST http://localhost:8825/conversation/sync \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "main",
    "target_surface": "ios"
  }' | jq .
```

**Expected:**
- `"success": true`
- `target_surface: "ios"`

#### Test 4: OpenAPI Schema

```bash
curl -s http://localhost:8825/openapi.json | jq '.paths | keys | map(select(startswith("/conversation")))'
```

**Expected:**
```json
[
  "/conversation/ask",
  "/conversation/context",
  "/conversation/sync",
  "/conversations/{conversation_id}"
]
```

---

## Common Issues & Solutions

### Issue: "Conversation Hub unavailable"

**Cause:** Import error during server startup

**Solution:**
1. Check `sys.path` includes `8825_core/`
2. Verify `conversation_hub/__init__.py` exists
3. Check for circular imports
4. Restart LaunchAgent

### Issue: "No LLM provider configured"

**Cause:** Team env file not found or keys missing

**Solution:**
1. Verify `8825-Team/config/secrets/llm.env` exists
2. Check keys are set: `echo $OPENROUTER_API_KEY`
3. Restart LaunchAgent to reload env
4. Check logs: `tail -f /tmp/maestra_backend.error.log`

### Issue: 404 on /conversation/* endpoints

**Cause:** Running old server process (before code changes)

**Solution:**
1. Restart LaunchAgent
2. Verify new code is loaded: `curl http://localhost:8825/openapi.json | jq '.paths | keys'`
3. Check logs for import errors

### Issue: Conversation ID not stable

**Cause:** Using `create_conversation()` instead of using `ConversationEnvelope` directly

**Solution:**
- Use `ConversationEnvelope` directly with caller-provided ID
- Call `hub._save_conversation()` and `hub._update_index()`
- Verify conversation file exists: `ls ~/.8825/conversations/main.json`

---

## Next Steps

1. **Local Companion Integration:** Update handshake expectations for consolidated port
2. **Cross-Surface Testing:** Test web → iOS → extension continuity
3. **Auto-Capture:** Implement auto-capture to Library on conversation completion
4. **Analytics:** Track conversation flows across surfaces
5. **Production Deployment:** Deploy to Fly.io with team env secrets

---

## See Also

- **ARCHITECTURE.md** - Overall Maestra v1 architecture
- **MAESTRA_INTEGRATION.md** - Multi-surface integration details
- **DEPLOY_BACKEND.md** - Backend deployment procedures
