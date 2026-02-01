# User Interaction Profile - Example Output

## Example Profile (Sufficient Data)

**User ID:** `justin_harmon`

### Profile Data
```json
{
  "user_id": "justin_harmon",
  "most_accessed_tags": [
    "enforcement",
    "architecture",
    "personalization",
    "memory",
    "trust"
  ],
  "preferred_entry_types": {
    "knowledge": 0.52,
    "decision": 0.31,
    "pattern": 0.17
  },
  "avg_doc_length": 1847.3,
  "update_frequency": null,
  "cross_reference_density": null,
  "avg_message_length": 142.7,
  "avg_follow_up_depth": null,
  "tool_usage_rate": 0.38,
  "first_seen": "2026-01-15T10:00:00.000Z",
  "last_updated": "2026-01-29T04:35:00.000Z",
  "sample_size": 47,
  "confidence": 0.94
}
```

### Signal Interpretation

**Library Signals:**
- **most_accessed_tags**: User frequently works with enforcement, architecture, personalization
- **preferred_entry_types**: 52% knowledge entries, 31% decisions, 17% patterns
- **avg_doc_length**: ~1850 chars per document (medium-length documentation)

**Session Signals:**
- **avg_message_length**: ~143 chars per message (concise communicator)
- **tool_usage_rate**: 38% of responses use tools (moderate tool reliance)

**Confidence:**
- **sample_size**: 47 data points (library entries + session turns)
- **confidence**: 0.94 (high confidence - sufficient data)

---

## Example Profile (Insufficient Data)

**User ID:** `new_user_123`

### Profile Data
```json
{
  "user_id": "new_user_123",
  "most_accessed_tags": ["test"],
  "preferred_entry_types": {
    "knowledge": 1.0
  },
  "avg_doc_length": 234.0,
  "update_frequency": null,
  "cross_reference_density": null,
  "avg_message_length": 87.0,
  "avg_follow_up_depth": null,
  "tool_usage_rate": 0.0,
  "first_seen": "2026-01-29T04:30:00.000Z",
  "last_updated": "2026-01-29T04:35:00.000Z",
  "sample_size": 3,
  "confidence": 0.15
}
```

### Signal Interpretation

**Insufficient Data:**
- **sample_size**: Only 3 data points
- **confidence**: 0.15 (too low - profile not returned)
- `get_user_profile("new_user_123")` returns `None`

**Minimum Threshold:**
- Confidence must be >= 0.3 to return profile
- Requires ~15 data points for minimum confidence

---

## Profile Schema

### Library Signals (from personal library metadata)
```python
most_accessed_tags: List[str]  # Top 5 tags by frequency
preferred_entry_types: Dict[str, float]  # knowledge/decision/pattern distribution
avg_doc_length: Optional[float]  # Average document length in chars
update_frequency: Optional[float]  # Docs updated per week (not yet implemented)
cross_reference_density: Optional[float]  # Avg references per doc (not yet implemented)
```

### Session Signals (from conversation patterns)
```python
avg_message_length: Optional[float]  # Chars per user message
avg_follow_up_depth: Optional[float]  # Turns per topic (not yet implemented)
tool_usage_rate: Optional[float]  # MCP calls per session
```

### Metadata
```python
first_seen: str  # ISO timestamp
last_updated: str  # ISO timestamp
sample_size: int  # Number of data points analyzed
confidence: float  # 0.0-1.0 based on sample size
```

---

## How Signals Are Derived

### From Library Entries
```python
# Extract from library_entries list
for entry in library_entries:
    tags = entry.get("tags", [])  # → most_accessed_tags
    entry_type = entry.get("entry_type")  # → preferred_entry_types
    content = entry.get("content", "")  # → avg_doc_length
```

### From Session Turns
```python
# Extract from session_turns list
user_messages = [turn for turn in session_turns if turn["type"] == "user_query"]
avg_message_length = mean([len(turn["content"]) for turn in user_messages])

assistant_turns = [turn for turn in session_turns if turn["type"] == "assistant_response"]
tools_used_count = sum(1 for turn in assistant_turns if turn["metadata"].get("tools_used"))
tool_usage_rate = tools_used_count / len(assistant_turns)
```

---

## Where Profile is Available (Read-Only)

### Advisor Access
```python
from user_interaction_profile import get_user_profile

# In advisor.py - read-only access
profile = get_user_profile(user_id)

if profile and profile.confidence > 0.7:
    # Use as HINTS only, never enforcement
    if profile.avg_message_length < 100:
        logger.info(f"User prefers concise responses (avg: {profile.avg_message_length} chars)")
    
    if profile.tool_usage_rate > 0.5:
        logger.info(f"User frequently uses tools ({profile.tool_usage_rate:.0%} of responses)")
```

### Component Access Rules

**Allowed to READ:**
- `advisor.py` - For context calibration hints only
- `context_injection.py` - For prompt framing hints only
- `conversation_mediator.py` - For decision confidence adjustment only

**NEVER allowed to access:**
- `enforcement_kernel.py` - No personalization in enforcement
- `routed_memory.py` - No personalization in memory routing
- `auth.py` - No personalization in authentication

---

## Constraints

### Read-Only Profile
- ✅ Profile is inferred, not user-editable
- ✅ No user-facing preferences UI
- ✅ No personality presets
- ✅ No mode forcing

### No Behavior Changes
- ✅ Profile never affects enforcement
- ✅ Profile never affects authority determination
- ✅ Profile never affects refusal semantics
- ✅ Profile used as hints only, never rules

### Isolation Guarantees
- ✅ Scoped per user_id
- ✅ Separate from session state
- ✅ No cross-user aggregation
- ✅ Explicit user_id required for access

---

## Example Usage (Hints Only)

### In Advisor (Hypothetical - Not Yet Implemented)
```python
# Get profile (returns None if insufficient data)
profile = get_user_profile(request.user_id)

# Use as hints for context, never enforcement
context_hints = []

if profile and profile.confidence > 0.7:
    # Hint 1: Verbosity preference
    if profile.avg_message_length < 100:
        context_hints.append("user_prefers_concise")
    
    # Hint 2: Tool reliance
    if profile.tool_usage_rate < 0.2:
        context_hints.append("user_prefers_memory_over_tools")
    
    # Hint 3: Topic interests
    if "enforcement" in profile.most_accessed_tags:
        context_hints.append("user_interested_in_enforcement")

# Hints could be passed to mediator or context injection
# BUT: Not yet wired - this is observation-only for now
```

### In Shadow Mediator (Future Enhancement)
```python
def compute_decision(self, query, recent_turns, query_metadata, profile=None):
    # If profile available, use as additional signal
    if profile and profile.confidence > 0.7:
        # Adjust verbosity based on user's typical message length
        if profile.avg_message_length < 100 and verbosity == "high":
            verbosity = "medium"
            signals_used.append("user_prefers_concise")
```

---

## Current Status

### Implemented
- ✅ Profile schema defined
- ✅ Profile builder implemented
- ✅ Library signal extraction
- ✅ Session signal extraction
- ✅ Confidence scoring
- ✅ Read-only access pattern

### Not Yet Wired
- ❌ Profile not yet populated from actual library
- ❌ Profile not yet updated from sessions
- ❌ Profile not yet passed to advisor
- ❌ Profile not yet used by mediator

### Next Steps (When Ready)
1. Wire profile builder to library accessor
2. Update profile from session turns
3. Pass profile to shadow mediator
4. Test with A/B comparison
5. Validate no enforcement/authority changes
