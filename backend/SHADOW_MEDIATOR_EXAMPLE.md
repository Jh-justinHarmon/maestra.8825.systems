# Shadow Conversation Mediator - Example Output

## Example 1: Explore Query with Depth Request

**User Query:** "Why did we separate trust from capability in the enforcement architecture?"

### Shadow Mediator Decision (Logged Only)
```json
{
  "verbosity": "medium",
  "structure": "conversational",
  "show_reasoning": true,
  "ask_clarifying_question": false,
  "confidence": 0.7,
  "signals_used": [
    "depth_requested",
    "query_type=explore"
  ],
  "reasoning": "User asked for depth (why/how/explain); Explore queries prefer balanced detail"
}
```

**Key Observations:**
- `show_reasoning: true` because user asked "why" (depth signal)
- `verbosity: medium` because query_type is "explore"
- `structure: conversational` (default, no artifact request)
- Decision is **logged only** - response generation unchanged

---

## Example 2: Execute Query (Terse Preference)

**User Query:** "Create a script to validate enforcement invariants"

### Shadow Mediator Decision (Logged Only)
```json
{
  "verbosity": "low",
  "structure": "structured",
  "show_reasoning": false,
  "ask_clarifying_question": false,
  "confidence": 0.7,
  "signals_used": [
    "tools_requested",
    "query_type=execute"
  ],
  "reasoning": "User asked for artifacts/tools; Execute queries prefer terse responses"
}
```

**Key Observations:**
- `verbosity: low` because query_type is "execute"
- `structure: structured` because user requested a script (artifact)
- `show_reasoning: false` (no depth signal)
- Decision is **logged only** - response generation unchanged

---

## Example 3: Reflect Query with Alignment Signal

**User Query:** "Does this approach feel right, or am I overthinking the isolation guarantees?"

### Shadow Mediator Decision (Logged Only)
```json
{
  "verbosity": "high",
  "structure": "conversational",
  "show_reasoning": false,
  "ask_clarifying_question": true,
  "confidence": 0.8,
  "signals_used": [
    "alignment_signal",
    "query_type=reflect"
  ],
  "reasoning": "User expressed uncertainty; Reflect queries benefit from dialogue"
}
```

**Key Observations:**
- `ask_clarifying_question: true` because user expressed uncertainty
- `verbosity: high` because query_type is "reflect"
- `structure: conversational` (no artifact request)
- Decision is **logged only** - response generation unchanged

---

## Example 4: Pattern Learning from Recent Turns

**User Query:** "Explain the benefits of separating trust from capability"

**Recent Turn Pattern:** User has sent 5 messages averaging 35 chars each (short messages)

### Shadow Mediator Decision (Logged Only)
```json
{
  "verbosity": "low",
  "structure": "conversational",
  "show_reasoning": true,
  "ask_clarifying_question": false,
  "confidence": 0.8,
  "signals_used": [
    "depth_requested",
    "query_type=explore",
    "short_user_messages"
  ],
  "reasoning": "User asked for depth (why/how/explain); Explore queries prefer balanced detail; User avg message length: 35 chars"
}
```

**Key Observations:**
- `verbosity: low` (downgraded from medium) because user writes short messages
- `show_reasoning: true` because user asked "explain"
- Pattern learning from conversation history
- Decision is **logged only** - response generation unchanged

---

## Example 5: Follow-Up After Refusal

**User Query:** "What about the enforcement architecture?"

**Previous Turn:** Assistant refused due to lack of grounding

### Shadow Mediator Decision (Logged Only)
```json
{
  "verbosity": "medium",
  "structure": "conversational",
  "show_reasoning": false,
  "ask_clarifying_question": true,
  "confidence": 0.85,
  "signals_used": [
    "query_type=explore",
    "previous_refusal"
  ],
  "reasoning": "Explore queries prefer balanced detail; Previous response was a refusal"
}
```

**Key Observations:**
- `ask_clarifying_question: true` because previous response was a refusal
- Mediator detects refusal pattern and suggests clarification
- Decision is **logged only** - response generation unchanged

---

## Assistant Turn Metadata (with Shadow Decision)

```json
{
  "response_length": 1847,
  "instrumented_at": "2026-01-29T04:30:00.000Z",
  "latency_ms": 3245,
  "query_type": "explore",
  "tools_used": ["memory_search"],
  "confidence": 0.92,
  "mode": "quick",
  "routing_pattern": "memory_required",
  "sources_count": 5,
  "epistemic_state": "grounded",
  "shadow_mediator_decision": {
    "verbosity": "medium",
    "structure": "conversational",
    "show_reasoning": true,
    "ask_clarifying_question": false,
    "confidence": 0.7,
    "signals_used": ["depth_requested", "query_type=explore"],
    "reasoning": "User asked for depth (why/how/explain); Explore queries prefer balanced detail"
  }
}
```

---

## Mediator Interface

### Where Invoked
**File:** `backend/advisor.py`
**Location:** Lines 1043-1052 (before prompt construction)

```python
# Shadow Mediator: Compute response-shaping decision (OBSERVATION ONLY - NOT APPLIED)
shadow_mediator = get_shadow_mediator()
mediator_decision = shadow_mediator.compute_decision(
    query=question,
    recent_turns=previous_context.get('recent_turns', []),
    query_metadata=user_metadata,
    session_context=previous_context
)
# Store decision in assistant metadata for telemetry (does NOT affect response)
mediator_decision_dict = mediator_decision.to_dict()
```

### Critical Constraints

**Response Generation MUST Ignore Mediator Output:**
- ✅ Mediator called **before** prompt construction
- ✅ Decision stored in metadata only
- ✅ `inject_context_into_prompt()` does NOT receive mediator decision
- ✅ No branching logic on mediator output
- ✅ No prompt changes based on mediator
- ✅ No UX changes

**Proof of Non-Effect:**
```python
# Use context injection to build messages with verified grounding
# NOTE: Mediator decision is NOT used here - response generation unchanged
messages = inject_context_into_prompt(
    query=question,
    chain_results=chain_results,
    grounding_sources=library_sources,
    epistemic_state=epistemic_state
)
```

---

## Aggregate Statistics

### Available via `get_decision_stats()`

```json
{
  "total_decisions": 47,
  "avg_confidence": 0.73,
  "verbosity_distribution": {
    "low": 0.21,
    "medium": 0.53,
    "high": 0.26
  },
  "structure_distribution": {
    "conversational": 0.74,
    "structured": 0.26
  },
  "show_reasoning_rate": 0.38,
  "ask_clarifying_rate": 0.19
}
```

**Insights from Stats:**
- Most queries prefer medium verbosity (53%)
- Conversational structure dominates (74%)
- Reasoning shown in 38% of cases (depth requests)
- Clarifying questions suggested in 19% (uncertainty/refusals)

---

## Behavior Guarantees

### Shadow System Properties
- ✅ Computes decisions without applying them
- ✅ All decisions logged for analysis
- ✅ Response generation completely unchanged
- ✅ No prompt modifications
- ✅ No UX changes
- ✅ Enforcement kernel untouched
- ✅ Authority logic untouched

### Telemetry Only
- ✅ Decisions stored in assistant turn metadata
- ✅ Aggregate stats available for analysis
- ✅ Session-scoped, per-user isolated
- ✅ No persistence beyond session lifetime

### Future Activation Path
When ready to activate mediator:
1. Wire `mediator_decision` into `inject_context_into_prompt()`
2. Add mediator hints to system prompt
3. Test with A/B comparison
4. Monitor for behavior changes
5. Validate enforcement/authority unchanged

**For now:** Observation only. No activation.
