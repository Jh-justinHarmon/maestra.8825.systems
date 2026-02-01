# Instrumentation Diagnostics - Example Output

## Example Session Analysis

**Session ID:** `session_abc123`
**Total Turns:** 12 (6 user, 6 assistant)

### CLI Output
```
============================================================
INSTRUMENTATION DIAGNOSTICS - Session session_abc123
============================================================

Total Turns: 12 (6 user, 6 assistant)

--- Query Type Distribution ---
  explore: 50.0%
  execute: 33.3%
  reflect: 16.7%

--- Epistemic Query Type Distribution ---
  MEMORY_REQUIRED: 50.0%
  GENERATIVE_ALLOWED: 33.3%
  CONTEXT_REQUIRED: 16.7%

--- Signal Frequencies ---
  depth_requested: 50.0%
  alignment_signal: 16.7%
  tools_requested: 33.3%
  tool_required: 16.7%

--- Response Metrics ---
  tool_usage_rate: 50.0%
  avg_response_length: 1547 chars
  avg_latency: 2834 ms

--- Shadow Mediator Decisions (Aggregated) ---
  total_decisions: 6
  verbosity.medium: 50.0%
  verbosity.low: 33.3%
  verbosity.high: 16.7%
  structure.conversational: 83.3%
  structure.structured: 16.7%
  show_reasoning_rate: 50.0%
  ask_clarifying_rate: 16.7%
  avg_confidence: 0.73

============================================================
```

---

## JSON Output (Programmatic Access)

```json
{
  "session_id": "session_abc123",
  "total_turns": 12,
  "user_turns": 6,
  "assistant_turns": 6,
  "timestamp": "2026-01-29T04:40:00.000Z",
  "query_type_distribution": {
    "explore": 0.5,
    "execute": 0.333,
    "reflect": 0.167
  },
  "epistemic_query_type_distribution": {
    "MEMORY_REQUIRED": 0.5,
    "GENERATIVE_ALLOWED": 0.333,
    "CONTEXT_REQUIRED": 0.167
  },
  "depth_requested_frequency": 0.5,
  "alignment_signal_frequency": 0.167,
  "tools_requested_frequency": 0.333,
  "tool_required_frequency": 0.167,
  "tool_usage_rate": 0.5,
  "avg_response_length": 1547.2,
  "avg_latency_ms": 2834.5,
  "mediator_decisions": {
    "total_decisions": 6,
    "verbosity_distribution": {
      "medium": 0.5,
      "low": 0.333,
      "high": 0.167
    },
    "structure_distribution": {
      "conversational": 0.833,
      "structured": 0.167
    },
    "show_reasoning_rate": 0.5,
    "ask_clarifying_rate": 0.167,
    "avg_confidence": 0.73
  }
}
```

---

## Usage Examples

### CLI Access
```bash
# From backend directory
python3 -c "
from instrumentation_diagnostics import print_session_summary
from session_continuity import get_or_create_session

# Get session turns
session = get_or_create_session('session_abc123')
turns = [t.to_dict() for t in session.turns]

# Analyze and print
from instrumentation_diagnostics import analyze_session
analyze_session('session_abc123', turns)
print_session_summary('session_abc123')
"
```

### Programmatic Access
```python
from instrumentation_diagnostics import get_session_stats, analyze_session
from session_continuity import get_or_create_session

# Get session
session = get_or_create_session('session_abc123')
turns = [t.to_dict() for t in session.turns]

# Analyze
stats = analyze_session('session_abc123', turns)

# Access specific metrics
print(f"Tool usage rate: {stats['tool_usage_rate']:.1%}")
print(f"Avg response length: {stats['avg_response_length']:.0f} chars")

# Access mediator decisions
mediator = stats['mediator_decisions']
print(f"Verbosity distribution: {mediator['verbosity_distribution']}")
```

---

## Insights from Example Session

### Query Patterns
- **50% explore queries** - User is investigating/learning
- **33% execute queries** - User is taking action
- **17% reflect queries** - User is checking alignment

### Grounding Requirements
- **50% memory-required** - Half of queries need grounding
- **33% generative-allowed** - Can answer without sources
- **17% context-required** - Need client context

### Interaction Signals
- **50% depth-requested** - User frequently asks "why/how"
- **17% alignment-signal** - Occasional uncertainty
- **33% tools-requested** - User asks for artifacts
- **17% tool-required** - Explicit tool assertions

### Response Characteristics
- **50% tool usage** - Half of responses use MCPs
- **1547 chars avg** - Medium-length responses
- **2834ms avg latency** - ~3 second response time

### Shadow Mediator Tendencies
- **50% medium verbosity** - Balanced detail level
- **83% conversational** - Mostly dialogue, not artifacts
- **50% show reasoning** - Half suggest showing depth
- **17% ask clarifying** - Occasional clarification suggestions
- **0.73 avg confidence** - Moderately confident decisions

---

## Developer Workflow

### 1. Run Session
```python
# User has conversation with Maestra
# Instrumentation automatically captures metadata
```

### 2. Analyze Session
```python
from instrumentation_diagnostics import analyze_session
from session_continuity import get_or_create_session

session = get_or_create_session('my_session_id')
turns = [t.to_dict() for t in session.turns]

stats = analyze_session('my_session_id', turns)
```

### 3. Review Patterns
```python
# Print summary to console
from instrumentation_diagnostics import print_session_summary
print_session_summary('my_session_id')

# Or access programmatically
print(f"User prefers: {stats['query_type_distribution']}")
print(f"Mediator suggests: {stats['mediator_decisions']['verbosity_distribution']}")
```

### 4. Iterate
```python
# Observe patterns across multiple sessions
# Identify personalization opportunities
# Validate shadow mediator accuracy
# Test before activating any mediator levers
```

---

## Constraints

### Developer-Only
- ✅ No UI exposure to users
- ✅ CLI or log-based output only
- ✅ Read-only, no side effects
- ✅ For observation and debugging only

### No Behavior Changes
- ✅ Diagnostics do not affect responses
- ✅ Analysis happens after-the-fact
- ✅ No real-time intervention
- ✅ Observation only

### Privacy & Isolation
- ✅ Session-scoped analysis
- ✅ No cross-user aggregation
- ✅ No persistent storage (in-memory only)
- ✅ Developer access only

---

## Next Steps (When Ready)

### Phase 1: Observation (Current)
- ✅ Capture metadata
- ✅ Log classifications
- ✅ Compute shadow decisions
- ✅ Analyze patterns
- ❌ Do NOT activate

### Phase 2: Validation (Future)
- Run diagnostics on real sessions
- Identify consistent patterns
- Validate mediator accuracy
- Compare shadow vs actual behavior

### Phase 3: Activation (Future)
- Wire ONE mediator lever
- A/B test with shadow baseline
- Monitor for behavior changes
- Validate enforcement unchanged

### Phase 4: Iteration (Future)
- Activate additional levers
- Refine based on telemetry
- Build UserInteractionProfile
- Enable personalization hints
