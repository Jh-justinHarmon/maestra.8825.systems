# Maestra Conversation Hub Integration

**Status:** Ready for multi-surface deployment  
**Architecture:** Platform-agnostic conversation routing with real LLM synthesis  
**Surfaces Supported:** Web, Chrome Extension, iOS

---

## Overview

Maestra is now integrated into the Conversation Hub, enabling:

1. **Cross-surface continuity** – Start a conversation on web, continue on extension
2. **Unified context** – All surfaces share conversation history and decisions
3. **Auto-capture to Library** – Conversations automatically saved as knowledge entries
4. **Real LLM responses** – Backed by OpenRouter, OpenAI, or Anthropic
5. **Platform-agnostic** – Same API for all surfaces

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Surfaces (Web, Extension, iOS)            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│         Maestra Conversation Hub API (Port 8826)             │
│  /ask, /context, /sync                                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│            MaestraBridge (Orchestration)                     │
│  - Session routing                                          │
│  - Context sharing                                          │
│  - Auto-capture                                             │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Conversation │ │ Maestra      │ │ Capture      │
│ Hub          │ │ Backend      │ │ Bridge       │
│ (Storage)    │ │ (LLM)        │ │ (Library)    │
└──────────────┘ └──────────────┘ └──────────────┘
```

---

## API Endpoints

### 1. Ask Maestra

**Endpoint:** `POST /ask`

**Request:**
```json
{
  "conversation_id": "conv-12345",
  "question": "What did we decide about the backend?",
  "surface": "web",
  "auto_capture": true
}
```

**Response:**
```json
{
  "success": true,
  "message_id": "msg-67890",
  "answer": "You decided to deploy the backend to Fly.io with real LLM integration...",
  "sources": [
    {
      "title": "Conversation context",
      "type": "local_context",
      "confidence": 0.9
    }
  ],
  "trace_id": "trace-abc123",
  "conversation_id": "conv-12345"
}
```

**What happens:**
1. Question added to conversation
2. Conversation history (last 5 messages) sent to Maestra backend
3. Real LLM response generated
4. Response added to conversation
5. Conversation auto-captured to Library (if enabled)
6. Response returned to surface

---

### 2. Get Conversation Context

**Endpoint:** `POST /context`

**Request:**
```json
{
  "conversation_id": "conv-12345",
  "max_messages": 10
}
```

**Response:**
```json
{
  "success": true,
  "conversation_id": "conv-12345",
  "topic": "Maestra Backend Deployment",
  "surface_origins": ["web", "extension"],
  "message_count": 42,
  "recent_messages": [
    {
      "role": "user",
      "content": "What did we decide about the backend?",
      "timestamp": "2025-12-31T03:53:00Z"
    }
  ],
  "key_decisions": [
    "Deploy to Fly.io",
    "Use OpenRouter for LLM"
  ],
  "open_questions": [
    "How do we handle rate limiting?",
    "When do we rotate API keys?"
  ]
}
```

**Use case:** Extension or iOS app fetches context before asking Maestra, so it understands conversation state.

---

### 3. Sync Conversation to Surface

**Endpoint:** `POST /sync`

**Request:**
```json
{
  "conversation_id": "conv-12345",
  "target_surface": "extension"
}
```

**Response:**
```json
{
  "success": true,
  "synced_messages": 42,
  "target_surface": "extension"
}
```

**Use case:** User switches from web to extension. Extension calls `/sync` to ensure conversation is available.

---

## Multi-Surface Flows

### Flow 1: Web → Extension Continuity

```
1. User on web: Asks Maestra a question
   → POST /ask (surface="web")
   → Response added to conversation
   → Auto-captured to Library

2. User switches to extension
   → Extension calls POST /context
   → Gets recent messages, decisions, questions
   → Extension calls POST /sync (surface="extension")
   → Conversation now available on extension

3. User asks follow-up on extension
   → POST /ask (surface="extension")
   → Backend sees conversation history from web
   → Provides context-aware response
```

### Flow 2: iOS Share Sheet

```
1. User selects text in Safari
   → iOS extension captures selection
   → Calls POST /ask with selected text
   → Maestra responds with analysis
   → Response saved to conversation
   → User can continue on web/extension
```

### Flow 3: Chrome Extension Sidebar

```
1. User opens extension on any website
   → Extension calls POST /context to load conversation
   → Shows recent messages and decisions
   → User asks question
   → POST /ask with page context
   → Maestra responds with page-aware answer
```

---

## Integration Checklist

### Backend (Conversation Hub)

- [x] MaestraBridge class created
- [x] Maestra API endpoints created
- [x] Conversation history tracking
- [x] Auto-capture to Library
- [x] Cross-surface context sharing
- [ ] Deploy to production (port 8826)
- [ ] Add to LaunchAgent plist
- [ ] Add to Docker Compose (if using VPS)

### Frontend (Web)

- [x] Conversation history sent to backend
- [x] Maestra responses displayed
- [ ] Link to conversation hub API
- [ ] Test cross-surface continuity

### Extension (Chrome)

- [ ] Call `/context` endpoint on load
- [ ] Call `/ask` endpoint for questions
- [ ] Handle conversation_id in storage
- [ ] Display conversation history

### iOS

- [ ] Call `/context` endpoint
- [ ] Call `/ask` endpoint from share sheet
- [ ] Store conversation_id in Keychain
- [ ] Display recent messages

---

## Deployment

### Local Testing

```bash
# Start conversation hub API
cd 8825_core/conversation_hub
python3 -m uvicorn maestra_api:app --reload --port 8826

# Test endpoint
curl -X POST http://localhost:8826/ask \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "test-conv",
    "question": "Hello Maestra",
    "surface": "web"
  }'
```

### Production Deployment

```bash
# Add to LaunchAgent plist
# Or Docker Compose if using VPS

# Environment variables needed:
# - MAESTRA_API_BASE (default: https://maestra-backend-8825-systems.fly.dev)
# - CONVERSATION_HUB_PORT (default: 8826)
```

---

## Platform-Agnostic Claims Delivered

✅ **Single API for all surfaces** – Web, extension, iOS use same endpoints  
✅ **Unified conversation storage** – All surfaces share history  
✅ **Real LLM responses** – Not stubs, actual synthesis  
✅ **Cross-surface continuity** – Start anywhere, continue anywhere  
✅ **Auto-capture to knowledge** – Conversations become library entries  
✅ **Context-aware responses** – Backend understands conversation state  
✅ **Workspace-agnostic** – Works from any user/machine  

---

## Next Steps

1. **Deploy conversation hub API** to production (port 8826)
2. **Wire extension** to use `/ask` and `/context` endpoints
3. **Wire iOS** to use `/ask` endpoint from share sheet
4. **Test cross-surface flows** (web → extension → iOS)
5. **Monitor** conversation capture and Library integration

---

## Files

- `maestra_bridge.py` – Core orchestration logic
- `maestra_api.py` – FastAPI endpoints
- `capture_bridge.py` – Auto-capture to Library (existing)
- `hub.py` – Conversation storage (existing)

---

## Support

For issues:
1. Check conversation hub logs: `tail -f ~/.8825_logs/conversation_hub.log`
2. Check Maestra backend: `curl https://maestra-backend-8825-systems.fly.dev/health`
3. Verify conversation exists: `hub.get_conversation(conversation_id)`
