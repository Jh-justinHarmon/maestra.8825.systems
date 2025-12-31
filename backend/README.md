# Maestra Backend

FastAPI service powering the Maestra browser extension.

## Overview

The Maestra Backend provides AI-powered assistance through:
- **Quick Mode**: Instant answers using Jh Brain context and 8825 philosophy
- **Deep Mode**: Thorough research via deep-research MCP

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Maestra        │────▶│  API Gateway    │────▶│  Maestra        │
│  Extension      │     │  (port 8000)    │     │  Backend        │
│  (browser)      │     │                 │     │  (port 8825)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                        ┌───────────────────────────────┼───────────────────────────────┐
                        │                               │                               │
                        ▼                               ▼                               ▼
                ┌─────────────────┐             ┌─────────────────┐             ┌─────────────────┐
                │  Jh Brain       │             │  Memory Hub     │             │  Deep Research  │
                │  (context)      │             │  (sessions)     │             │  (research)     │
                └─────────────────┘             └─────────────────┘             └─────────────────┘
```

## Endpoints

### `POST /api/maestra/advisor/ask`

Ask the advisor a question.

**Request:**
```json
{
  "session_id": "sess_abc123",
  "user_id": "justin",
  "question": "What's the best approach for PDF rendering?",
  "mode": "quick",
  "context_hints": ["export", "rendering"]
}
```

**Response:**
```json
{
  "answer": "Based on 8825 knowledge...",
  "session_id": "sess_abc123",
  "job_id": null,
  "sources": [
    {"title": "Jh Brain Context", "type": "knowledge", "confidence": 0.8}
  ],
  "trace_id": "trace_xyz789",
  "mode": "quick",
  "processing_time_ms": 150
}
```

### `GET /api/maestra/context/{session_id}`

Get session context summary.

**Response:**
```json
{
  "session_id": "sess_abc123",
  "summary": "Made 2 key decisions. 1 item pending.",
  "key_decisions": ["Decided to use Typst for PDF rendering"],
  "open_loops": ["Need to configure DNS"],
  "topics_discussed": ["Export", "API Gateway"],
  "last_activity": "2024-12-21T06:30:00Z"
}
```

### `GET /api/maestra/research/{job_id}`

Get research job status.

**Response:**
```json
{
  "job_id": "research_abc123",
  "status": "done",
  "progress": 1.0,
  "title": "PDF rendering comparison",
  "summary": "Research findings...",
  "current_phase": null,
  "error": null,
  "created_at": "2024-12-21T06:00:00Z",
  "completed_at": "2024-12-21T06:30:00Z"
}
```

### `GET /health`

Health check endpoint.

## Local Development

### Prerequisites

- Python 3.10+
- pip

### Setup

```bash
cd 8825_core/tools/8825_backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Run the server
python server.py
```

Server runs on `http://localhost:8825`.

### Testing

```bash
# Health check
curl http://localhost:8825/health

# Ask advisor (quick mode)
curl -X POST http://localhost:8825/api/maestra/advisor/ask \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session",
    "question": "What is 8825?",
    "mode": "quick"
  }'

# Get context
curl http://localhost:8825/api/maestra/context/test-session

# Ask advisor (deep mode)
curl -X POST http://localhost:8825/api/maestra/advisor/ask \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session",
    "question": "Compare PDF rendering libraries",
    "mode": "deep"
  }'
```

## Production Deployment

In production, the Maestra Backend runs behind the API Gateway:

1. **API Gateway** handles:
   - Token authentication
   - Scope authorization (`maestra:advisor:ask`, `maestra:context:read`, `maestra:research:read`)
   - Rate limiting (60 req/min for maestra template)
   - Audit logging
   - CORS headers

2. **Maestra Backend** handles:
   - Business logic
   - MCP integrations (Jh Brain, Memory Hub, Deep Research)

### Token Creation

```bash
cd 8825_core/tools/api_gateway
python token_cli.py create --template maestra
```

This creates a token with scopes:
- `maestra:advisor:ask`
- `maestra:context:read`
- `maestra:research:read`

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `JH_BRAIN_URL` | `http://localhost:8825` | Jh Brain MCP URL |
| `MEMORY_HUB_URL` | `http://localhost:8826` | Memory Hub MCP URL |
| `DEEP_RESEARCH_URL` | `http://localhost:8827` | Deep Research MCP URL |

## Files

```
8825_backend/
├── __init__.py       # Package init
├── server.py         # FastAPI app + routes
├── models.py         # Pydantic request/response models
├── advisor.py        # /advisor/ask logic
├── context.py        # /context/{session_id} logic
├── research.py       # /research/{job_id} logic
├── requirements.txt  # Python dependencies
└── README.md         # This file
```
