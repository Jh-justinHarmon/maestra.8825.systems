# Advisor Contract (Authoritative)

**Status**: Authoritative  
**Created**: 2026-01-27  
**Purpose**: Document the canonical Advisor API contract

---

## Canonical Endpoint

**`POST /api/maestra/advisor/ask`**

This is the primary endpoint for all Maestra surfaces to interact with the advisor intelligence layer.

**Legacy alias**: `POST /advisor/ask` (maintained for backward compatibility)

---

## Request Schema

### `AdvisorAskRequest`

```json
{
  "session_id": "string",
  "user_id": "string",
  "question": "string (optional, legacy)",
  "message": "string (optional, preferred)",
  "mode": "quick | deep",
  "context_hints": ["string"],
  "client_context": {
    "key": "value"
  }
}
```

### Required Fields

#### `session_id`
- **Type**: `string`
- **Default**: `"default"`
- **Description**: Session identifier for context continuity
- **Example**: `"550e8400-e29b-41d4-a716-446655440000"`

#### `user_id`
- **Type**: `string`
- **Default**: `"anonymous"`
- **Description**: User identifier
- **Example**: `"user_jh"`, `"alpha_sm"`

### Optional Fields

#### `message` (preferred) or `question` (legacy)
- **Type**: `string`
- **Description**: The question to ask the advisor
- **Note**: `message` is the preferred field name; `question` is maintained for backward compatibility
- **Example**: `"What did we decide about the API design?"`

#### `mode`
- **Type**: `"quick" | "deep"`
- **Default**: `"quick"`
- **Description**: Response mode
  - `"quick"`: Instant response using existing knowledge
  - `"deep"`: Research job with external search and synthesis
- **Example**: `"quick"`

#### `context_hints`
- **Type**: `array[string]`
- **Default**: `[]`
- **Description**: Optional hints to guide context retrieval
- **Example**: `["project_alpha", "api_design"]`

#### `client_context`
- **Type**: `object`
- **Default**: `null`
- **Description**: Optional client-provided context payload
- **Purpose**: Surfaces can include additional context not captured in the question
- **Examples**:
  - Web page: `{"url": "https://example.com", "title": "Example", "selection": "..."}`
  - Figma: `{"file_name": "Design System", "page": "Components", "selection": [...]}`
  - Browser extension: `{"tab_url": "...", "page_title": "..."}`

---

## Response Schema

### `AdvisorAskResponse`

```json
{
  "schema_version": "1",
  "answer": "string",
  "session_id": "string",
  "job_id": "string | null",
  "sources": [
    {
      "title": "string",
      "type": "knowledge | decision | pattern | protocol | external",
      "confidence": 0.0-1.0,
      "excerpt": "string | null",
      "url": "string | null"
    }
  ],
  "trace_id": "string",
  "mode": "quick | deep",
  "processing_time_ms": 0,
  "conversation_id": "string | null",
  "turns": [{...}] | null,
  "agent": {
    "agent_id": "string",
    "display_name": "string"
  } | null
}
```

### Required Fields

#### `schema_version`
- **Type**: `string`
- **Default**: `"1"`
- **Description**: API schema version for compatibility tracking

#### `answer`
- **Type**: `string`
- **Description**: The advisor's answer to the question
- **Example**: `"Based on our previous discussion, we decided to use REST for the public API..."`

#### `session_id`
- **Type**: `string`
- **Description**: Session ID for follow-up questions (may be newly created)

#### `trace_id`
- **Type**: `string`
- **Description**: Unique trace ID for debugging and observability
- **Example**: `"trace_20260127_153045_abc123"`

#### `mode`
- **Type**: `string`
- **Description**: Mode used to generate this response (`"quick"` or `"deep"`)

### Optional Fields

#### `job_id`
- **Type**: `string | null`
- **Description**: Research job ID if `mode=deep` (for polling status)
- **Example**: `"research_20260127_153045"`

#### `sources`
- **Type**: `array[SourceReference]`
- **Default**: `[]`
- **Description**: Sources used to generate the answer
- **Source types**:
  - `knowledge`: Library knowledge entry
  - `decision`: Recorded decision
  - `pattern`: Behavioral pattern
  - `protocol`: System protocol
  - `external`: External search result

#### `processing_time_ms`
- **Type**: `integer`
- **Default**: `0`
- **Description**: Processing time in milliseconds

#### `conversation_id`
- **Type**: `string | null`
- **Description**: Loaded conversation ID (if loading a conversation)

#### `turns`
- **Type**: `array[object] | null`
- **Description**: Conversation turns (if loading a conversation)

#### `agent`
- **Type**: `object | null`
- **Description**: Agent that generated this response
- **Fields**:
  - `agent_id`: Agent identifier (`"assistant"`, `"analyst"`)
  - `display_name`: Human-readable name

---

## Role of `client_context`

The `client_context` field allows surfaces to provide additional context that cannot be captured in the question text alone.

**Purpose**:
- Enrich the advisor's understanding without requiring verbose questions
- Provide surface-specific metadata (URLs, file names, selections)
- Enable context-aware responses without changing the question format

**Guidelines**:
- Keep `client_context` minimal and relevant
- Do not include sensitive data unless necessary
- Structure should be surface-specific but documented

**Examples**:

### Web App
```json
{
  "client_context": {
    "url": "https://example.com/docs",
    "title": "Documentation",
    "selection": "API endpoints section"
  }
}
```

### Browser Extension
```json
{
  "client_context": {
    "tab_url": "https://github.com/org/repo",
    "page_title": "Pull Request #123",
    "selection": "function calculateTotal() { ... }"
  }
}
```

### Figma Plugin
```json
{
  "client_context": {
    "file_name": "Design System v2",
    "page_name": "Components",
    "selected_nodes": [
      {"type": "FRAME", "name": "Button/Primary"}
    ]
  }
}
```

---

## Supported Modes

### Quick Mode (`mode: "quick"`)
- **Response time**: < 2 seconds
- **Sources**: Internal knowledge only (Library, Memory, Protocols)
- **Use case**: Fast answers to known questions
- **Epistemic grounding**: Applied (refuses if insufficient knowledge)

### Deep Mode (`mode: "deep"`)
- **Response time**: 20-75 minutes (async)
- **Sources**: Internal + external search + synthesis
- **Use case**: Research questions requiring external information
- **Returns**: `job_id` for polling status via `/api/maestra/research/{job_id}`

---

## Error Responses

### Standard Error Format
```json
{
  "detail": "Error message"
}
```

### Common Errors
- `400 Bad Request`: Invalid request schema
- `401 Unauthorized`: Authentication failure (if auth enabled)
- `404 Not Found`: Session or resource not found
- `500 Internal Server Error`: Backend failure
- `503 Service Unavailable`: Backend overloaded or unavailable

---

## Contract Compatibility

**All production surfaces MUST use this contract.**

Surfaces that use different endpoints or schemas are experimental and cannot be promoted to production.

**Known incompatible surfaces**:
- Figma Surface v1 (uses `/api/reasoning` instead of `/api/maestra/advisor/ask`)

---

## Example Request/Response

### Request
```json
POST /api/maestra/advisor/ask
Content-Type: application/json

{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user_jh",
  "message": "What did we decide about the API design?",
  "mode": "quick",
  "context_hints": ["project_alpha", "api_design"],
  "client_context": {
    "url": "https://github.com/org/repo/pull/123"
  }
}
```

### Response
```json
{
  "schema_version": "1",
  "answer": "Based on our previous discussion, we decided to use REST for the public API with the following constraints: versioning via URL path (/v1/), JSON-only responses, and OAuth2 for authentication.",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "job_id": null,
  "sources": [
    {
      "title": "API Design Decision - 2026-01-15",
      "type": "decision",
      "confidence": 0.95,
      "excerpt": "We decided to use REST for the public API..."
    }
  ],
  "trace_id": "trace_20260127_153045_abc123",
  "mode": "quick",
  "processing_time_ms": 1247,
  "conversation_id": null,
  "turns": null,
  "agent": {
    "agent_id": "analyst",
    "display_name": "Analyst"
  }
}
```

---

**This document is descriptive of the current implementation. It reflects the actual API contract as implemented in `backend/models.py` and `backend/advisor.py`.**
