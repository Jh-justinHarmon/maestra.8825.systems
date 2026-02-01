# Turn Instrumentation - Example Output

## Example 1: Explore Query with Depth Request

**User Query:** "Why did we separate trust from capability in the enforcement architecture?"

### User Turn Metadata
```json
{
  "query_type": "explore",
  "depth_requested": true,
  "alignment_signal": false,
  "tools_requested": false,
  "query_length": 72,
  "instrumented_at": "2026-01-29T04:00:00.000Z",
  "start_time_ms": 1738119600000,
  "mode": "quick"
}
```

### Assistant Turn Metadata
```json
{
  "response_length": 1847,
  "instrumented_at": "2026-01-29T04:00:03.245Z",
  "latency_ms": 3245,
  "query_type": "explore",
  "tools_used": ["memory_search"],
  "confidence": 0.92,
  "mode": "quick",
  "routing_pattern": "memory_required",
  "sources_count": 5,
  "epistemic_state": "grounded"
}
```

---

## Example 2: Execute Query with Tool Request

**User Query:** "Create a script to validate all enforcement invariants"

### User Turn Metadata
```json
{
  "query_type": "execute",
  "depth_requested": false,
  "alignment_signal": false,
  "tools_requested": true,
  "query_length": 54,
  "instrumented_at": "2026-01-29T04:05:00.000Z",
  "start_time_ms": 1738119900000,
  "mode": "quick"
}
```

### Assistant Turn Metadata
```json
{
  "response_length": 2341,
  "instrumented_at": "2026-01-29T04:05:04.892Z",
  "latency_ms": 4892,
  "query_type": "execute",
  "tools_used": ["sentinel", "context_required"],
  "confidence": 0.85,
  "mode": "quick",
  "routing_pattern": "context_required",
  "sources_count": 3,
  "epistemic_state": "grounded"
}
```

---

## Example 3: Reflect Query with Alignment Signal

**User Query:** "Does this approach feel right, or am I overthinking the isolation guarantees?"

### User Turn Metadata
```json
{
  "query_type": "reflect",
  "depth_requested": false,
  "alignment_signal": true,
  "tools_requested": false,
  "query_length": 81,
  "instrumented_at": "2026-01-29T04:10:00.000Z",
  "start_time_ms": 1738120200000,
  "mode": "quick"
}
```

### Assistant Turn Metadata
```json
{
  "response_length": 1124,
  "instrumented_at": "2026-01-29T04:10:02.156Z",
  "latency_ms": 2156,
  "query_type": "reflect",
  "tools_used": null,
  "confidence": 0.78,
  "mode": "quick",
  "routing_pattern": "general",
  "sources_count": 0,
  "epistemic_state": "ungrounded"
}
```

---

## Complete ConversationTurn Object Example

```python
ConversationTurn(
    turn_id="trace_abc123_user",
    type="user_query",
    timestamp="2026-01-29T04:00:00.000Z",
    content="Why did we separate trust from capability in the enforcement architecture?",
    metadata={
        "query_type": "explore",
        "depth_requested": True,
        "alignment_signal": False,
        "tools_requested": False,
        "query_length": 72,
        "instrumented_at": "2026-01-29T04:00:00.000Z",
        "start_time_ms": 1738119600000,
        "mode": "quick"
    }
)

ConversationTurn(
    turn_id="trace_abc123",
    type="assistant_response",
    timestamp="2026-01-29T04:00:03.245Z",
    content="We separated trust from capability to create a clean architectural boundary...",
    metadata={
        "response_length": 1847,
        "instrumented_at": "2026-01-29T04:00:03.245Z",
        "latency_ms": 3245,
        "query_type": "explore",
        "tools_used": ["memory_search"],
        "confidence": 0.92,
        "mode": "quick",
        "routing_pattern": "memory_required",
        "sources_count": 5,
        "epistemic_state": "grounded"
    }
)
```

---

## Key Observations

### Signal Capture (No Behavior Change)
- ✅ All metadata is **descriptive**, not prescriptive
- ✅ No branching logic depends on these fields
- ✅ Response generation is unchanged
- ✅ Enforcement kernel untouched
- ✅ Authority logic untouched

### Metadata Schema
**User Turn Fields:**
- `query_type`: "explore" | "execute" | "reflect"
- `depth_requested`: boolean
- `alignment_signal`: boolean
- `tools_requested`: boolean
- `query_length`: integer (chars)
- `start_time_ms`: integer (epoch ms)

**Assistant Turn Fields:**
- `response_length`: integer (chars)
- `latency_ms`: integer
- `query_type`: string (from user turn)
- `tools_used`: list[string] | null
- `confidence`: float | null

### Isolation Guarantees
- ✅ Session-scoped (via session_id)
- ✅ Per-user isolated (via session isolation)
- ✅ No cross-session leakage
- ✅ In-memory only (lost on restart)
