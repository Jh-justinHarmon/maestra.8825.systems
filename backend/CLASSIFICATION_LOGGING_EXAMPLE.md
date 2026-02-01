# Query Classification Logging - Example Output

## Example 1: Memory-Required Query with Tool Assertion

**User Query:** "Search Sentinel for enforcement architecture decisions"

### User Turn Metadata (with classification)
```json
{
  "query_type": "execute",
  "depth_requested": false,
  "alignment_signal": false,
  "tools_requested": false,
  "query_length": 54,
  "instrumented_at": "2026-01-29T04:15:00.000Z",
  "start_time_ms": 1738120500000,
  "mode": "quick",
  "epistemic_query_type": "MEMORY_REQUIRED",
  "tool_required": true,
  "tool_name": "sentinel",
  "classification_confidence": 0.95
}
```

**Classification Breakdown:**
- `query_type`: "execute" (from turn_instrumentation pattern matching)
- `epistemic_query_type`: "MEMORY_REQUIRED" (from epistemic.classify_query)
- `tool_required`: true (from tool_assertion_classifier)
- `tool_name`: "sentinel" (explicit tool assertion detected)
- `classification_confidence`: 0.95 (high confidence in tool requirement)

---

## Example 2: Generative Query (No Tool Assertion)

**User Query:** "Explain the benefits of separating trust from capability"

### User Turn Metadata (with classification)
```json
{
  "query_type": "explore",
  "depth_requested": true,
  "alignment_signal": false,
  "tools_requested": false,
  "query_length": 59,
  "instrumented_at": "2026-01-29T04:20:00.000Z",
  "start_time_ms": 1738120800000,
  "mode": "quick",
  "epistemic_query_type": "GENERATIVE_ALLOWED",
  "tool_required": false,
  "tool_name": null,
  "classification_confidence": 0.3
}
```

**Classification Breakdown:**
- `query_type`: "explore" (from turn_instrumentation)
- `epistemic_query_type`: "GENERATIVE_ALLOWED" (no grounding required)
- `tool_required`: false (no explicit tool assertion)
- `tool_name`: null (no tool detected)
- `classification_confidence`: 0.3 (low confidence - no strong signals)

---

## Example 3: Context-Required Query

**User Query:** "What am I looking at on this page?"

### User Turn Metadata (with classification)
```json
{
  "query_type": "explore",
  "depth_requested": false,
  "alignment_signal": false,
  "tools_requested": false,
  "query_length": 35,
  "instrumented_at": "2026-01-29T04:25:00.000Z",
  "start_time_ms": 1738121100000,
  "mode": "quick",
  "epistemic_query_type": "CONTEXT_REQUIRED",
  "tool_required": false,
  "tool_name": null,
  "classification_confidence": 0.2
}
```

**Classification Breakdown:**
- `query_type`: "explore" (from turn_instrumentation)
- `epistemic_query_type`: "CONTEXT_REQUIRED" (needs client context)
- `tool_required`: false (no tool assertion)
- `tool_name`: null
- `classification_confidence`: 0.2 (low - no explicit tool)

---

## Metadata Fields Added

### From epistemic.classify_query()
- `epistemic_query_type`: "MEMORY_REQUIRED" | "CONTEXT_REQUIRED" | "RESEARCH_REQUIRED" | "GENERATIVE_ALLOWED"

### From tool_assertion_classifier.classify_tool_assertion()
- `tool_required`: boolean
- `tool_name`: string | null (e.g., "sentinel", "internal_documents")
- `classification_confidence`: float (0.0-1.0)

---

## Behavior Guarantees

### No Changes to Response Logic
- ✅ Classification happens **before** turn creation
- ✅ Results are **logged only**, not used for branching
- ✅ Existing classification calls remain unchanged
- ✅ Response generation unchanged
- ✅ Enforcement kernel untouched

### Telemetry Only
- ✅ All classification results captured in metadata
- ✅ Available for future analysis
- ✅ Session-scoped, per-user isolated
- ✅ No persistence beyond session lifetime

---

## Where Classification is Logged

**File:** `backend/advisor.py`

**Location:** Lines 672-684 (user turn creation)

```python
# Classify query early for metadata logging (behavior unchanged)
query_type_classification = classify_query(question)
tool_assertion_classification = classify_tool_assertion(question)

# Add user query to session continuity with instrumentation
user_metadata = instrument_user_turn(
    query=question,
    start_time_ms=start_time_ms,
    epistemic_query_type=query_type_classification.value,
    tool_required=tool_assertion_classification.requires_tool,
    tool_name=tool_assertion_classification.tool_name if tool_assertion_classification.requires_tool else None,
    classification_confidence=tool_assertion_classification.confidence
)
```

**Key Point:** Classification happens at the same time as before, but results are now captured in metadata for telemetry.
