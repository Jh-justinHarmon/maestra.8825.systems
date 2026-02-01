# PROMPT 10: A/B Test Plan — `structure` Lever Activation

## Experiment Definition

**Lever Under Test:** `structure` (conversational vs structured formatting)

**What Changes:** Presentation only. Never content.
- Bullets, headings, code blocks vs prose
- No prompt changes
- No reasoning exposure
- No authority changes
- No tool behavior changes
- No refusal behavior changes

**Hypothesis:** Structured formatting for artifact requests improves user experience without degrading trust or clarity.

---

## Group Design

### Group A — Control (Shadow Only)
- Shadow mediator runs
- `structure` decisions logged
- Output **unchanged** (current behavior)
- Baseline for comparison

### Group B — Treatment (Structure Active)
- Shadow mediator runs
- `structure` applied when rule matches
- Output formatted accordingly
- Test group

### Assignment Strategy
```python
# Sticky per session_id (no cross-contamination)
import hashlib

def assign_group(session_id: str) -> str:
    """Deterministic assignment based on session_id hash."""
    hash_value = int(hashlib.md5(session_id.encode()).hexdigest(), 16)
    return "B" if hash_value % 2 == 0 else "A"
```

**Distribution:** 50% Group A, 50% Group B

**Sticky:** Once assigned, session stays in same group for entire conversation

---

## Activation Rule (Final)

```python
# Feature flag (global toggle)
ENABLE_STRUCTURE_ADAPTATION = True  # Set to False for instant rollback

def should_apply_structure(
    tools_requested: bool,
    mediator_structure: str,
    mediator_confidence: float,
    session_group: str
) -> bool:
    """
    Determine if structured formatting should be applied.
    
    Returns True only if:
    - Feature flag enabled
    - Session in Group B (treatment)
    - Activation rule matches
    """
    # Feature flag check
    if not ENABLE_STRUCTURE_ADAPTATION:
        return False
    
    # Group check (only Group B gets treatment)
    if session_group != "B":
        return False
    
    # Activation rule
    if tools_requested:
        return True
    elif mediator_structure == "structured" and mediator_confidence >= 0.7:
        return True
    else:
        return False
```

**Guardrails:**
- ✅ Confidence threshold enforced (≥ 0.7)
- ✅ Feature flag enforced
- ✅ Group assignment enforced
- ✅ No other mediator outputs applied

---

## Metrics Dashboard

### Primary Metrics (Must Not Degrade)

**1. Follow-up Rate**
```python
follow_up_rate = (turns_with_follow_up / total_turns) * 100

# Target: Flat or decrease
# Red line: >5% increase
```

**2. Time-to-Next-Action**
```python
avg_time_to_next_turn = mean(turn_timestamps[i+1] - turn_timestamps[i])

# Target: Flat or decrease
# Red line: >20% increase
```

**3. Refusal Rate**
```python
refusal_rate = (refused_queries / total_queries) * 100

# Target: Identical between groups
# Red line: Any difference >1%
```

**4. Authority Distribution**
```python
authority_dist = {
    "memory": count_memory / total,
    "system": count_system / total,
    "refused": count_refused / total
}

# Target: Identical between groups
# Red line: Any difference >2%
```

---

### Secondary Metrics (Signal of Improvement)

**1. Artifact Reuse**
```python
# Proxy: Did user copy code? (can't measure directly)
# Signal: Short confirmations after artifact delivery
artifact_satisfaction = count("got it", "perfect", "thanks") / artifact_responses

# Target: Increase in Group B
# Good signal: >10% increase
```

**2. Clarification Prompts**
```python
clarification_rate = count("reformat", "can you", "instead") / total_turns

# Target: Decrease in Group B
# Good signal: >15% decrease
```

**3. Implicit Satisfaction**
```python
short_confirmations = count(turns_with_length < 20 and positive_sentiment) / total_turns

# Target: Increase in Group B
# Good signal: >5% increase
```

---

### Red-Line Metrics (Immediate Rollback)

**Trigger rollback if ANY of these occur:**

1. **>5% increase in clarification questions**
   ```python
   if group_b_clarification_rate > group_a_clarification_rate * 1.05:
       ROLLBACK()
   ```

2. **Any trust boundary regression**
   ```python
   if group_b_refusal_rate != group_a_refusal_rate:
       ROLLBACK()
   ```

3. **Any enforcement invariant violation**
   ```python
   if group_b_authority_dist != group_a_authority_dist:
       ROLLBACK()
   ```

4. **Any user complaint about formatting**
   ```python
   if count_complaints("robotic", "weird formatting", "too formal") > 0:
       ROLLBACK()
   ```

**Rollback Procedure:**
```bash
# 1. Set feature flag to False
export ENABLE_STRUCTURE_ADAPTATION=false

# 2. Redeploy (instant)
fly deploy -c apps/maestra.8825.systems/backend/fly.toml

# 3. Verify
curl -s https://maestra-backend-8825-systems.fly.dev/health | jq '.feature_flags.structure_adaptation'
# Should return: false

# Done. No migrations. No cleanup.
```

---

## Telemetry Schema

### Per-Turn Logging

```json
{
  "session_id": "session_abc123",
  "turn_id": "turn_456",
  "timestamp": "2026-01-29T05:00:00.000Z",
  "group": "A" | "B",
  "structure_applied": true | false,
  "mediator_decision": {
    "structure": "conversational" | "structured",
    "confidence": 0.72,
    "signals_used": ["tools_requested"]
  },
  "query_metadata": {
    "tools_requested": true,
    "query_type": "execute",
    "query_length": 45
  },
  "response_metadata": {
    "response_length": 1234,
    "latency_ms": 2500,
    "epistemic_state": "grounded",
    "sources_count": 3
  }
}
```

**Privacy Guarantees:**
- ❌ Do NOT log user content
- ❌ Do NOT log raw messages
- ✅ Only log metadata and decisions
- ✅ Session-scoped, no cross-user aggregation

---

## Evaluation Window

### Minimum Viable Test
- **Duration:** 48 hours
- **Sample Size:** ≥ 100 sessions total (50 per group)
- **Confidence:** Low, but sufficient for safety check

### Ideal Test
- **Duration:** 1 week
- **Sample Size:** ≥ 500 sessions total (250 per group)
- **Confidence:** High, sufficient for decision

### Early Stopping Criteria
**Stop early if:**
- Red-line metric triggered (rollback immediately)
- Clear positive signal after 200 sessions (proceed to next lever)
- No signal after 500 sessions (neutral = keep, but don't rush next lever)

---

## Decision Matrix

| Outcome | Primary Metrics | Secondary Metrics | Decision |
|---------|----------------|-------------------|----------|
| **Success** | Flat or improved | Improved | Keep structure on, proceed to lever 2 |
| **Neutral** | Flat | Flat | Keep structure on, wait before lever 2 |
| **Mixed** | Flat | Some improved, some worse | Refine activation rule, re-test |
| **Failure** | Degraded | N/A | Roll back, document learning |

### Success Criteria (Proceed to Lever 2)
- ✅ Primary metrics flat or improved
- ✅ Secondary metrics show improvement
- ✅ No red-line triggers
- ✅ No user complaints
- ✅ Sample size ≥ 250 per group

### Neutral Criteria (Keep, Wait)
- ✅ Primary metrics flat
- ⚠️ Secondary metrics flat
- ✅ No red-line triggers
- ✅ No user complaints
- **Decision:** Keep structure on, but gather more data before next lever

### Refinement Criteria (Adjust Rule)
- ✅ Primary metrics flat
- ⚠️ Secondary metrics mixed (some good, some bad)
- ✅ No red-line triggers
- **Decision:** Adjust confidence threshold or activation rule, re-test

### Failure Criteria (Rollback)
- ❌ Primary metrics degraded
- OR: Red-line metric triggered
- **Decision:** Rollback immediately, document what we learned

---

## Learning Framework (Even If It Fails)

### If Structure Succeeds
**What we learn:**
- Structured formatting improves artifact delivery
- Users prefer explicit formatting for code/tools
- Mediator confidence calibration is accurate
- Safe to proceed to next lever

**Next steps:**
1. Keep `ENABLE_STRUCTURE_ADAPTATION = true`
2. Proceed to PROMPT 11 (activate `ask_clarifying_question`)
3. Same discipline, same process

---

### If Structure Fails
**What we learn:**
- Users prefer consistent formatting (no adaptation)
- OR: Activation rule too aggressive
- OR: Confidence threshold too low
- OR: Structured formatting feels "robotic"

**Next steps:**
1. Rollback: `ENABLE_STRUCTURE_ADAPTATION = false`
2. Document failure mode in telemetry
3. Analyze: Was it the rule or the lever itself?
4. Options:
   - Refine activation rule (higher confidence threshold)
   - Skip to next lever (`ask_clarifying_question`)
   - Pause personalization, focus on other improvements

**Still a win:** We learned the boundary safely, without breaking trust.

---

### If Structure is Neutral
**What we learn:**
- Structured formatting doesn't hurt, doesn't help
- Users are indifferent to formatting choices
- Mediator is accurate but impact is minimal

**Next steps:**
1. Keep `ENABLE_STRUCTURE_ADAPTATION = true` (no harm)
2. Gather more data (extend test to 1000 sessions)
3. Proceed cautiously to next lever
4. Consider: Is personalization worth the complexity?

---

## Pre-Mortem: Failure Cases

### Failure Case 1: Users Complain About "Robotic" Formatting
**Symptom:** Feedback like "too formal", "feels like a bot", "weird bullets"

**Root Cause:** Structured formatting breaks conversational flow

**Learning:** Users value natural conversation over explicit structure

**Response:** Rollback immediately, skip structure lever, proceed to `ask_clarifying_question`

---

### Failure Case 2: Increased Follow-Up Questions
**Symptom:** Group B has >5% more follow-ups than Group A

**Root Cause:** Structured formatting obscures key information

**Learning:** Bullets/headings make users miss important details

**Response:** Rollback, refine rule to only apply for explicit artifact requests (tools_requested=true only)

---

### Failure Case 3: Confidence Miscalibration
**Symptom:** Structure applied when it shouldn't be (false positives)

**Root Cause:** Confidence threshold too low (0.7)

**Learning:** Need higher threshold for formatting changes

**Response:** Increase threshold to 0.8, re-test

---

### Failure Case 4: No Measurable Signal
**Symptom:** All metrics identical between groups

**Root Cause:** Sample size too small OR formatting doesn't matter

**Learning:** Either need more data or structure is not impactful

**Response:** Extend test to 1000 sessions, if still neutral, keep but deprioritize

---

## Implementation Checklist

### Phase 1: Code Changes
- [ ] Add `ENABLE_STRUCTURE_ADAPTATION` feature flag to config
- [ ] Implement `assign_group(session_id)` function
- [ ] Implement `should_apply_structure()` function
- [ ] Wire structure decision into context injection
- [ ] Add telemetry logging for structure decisions
- [ ] Add group assignment to session metadata

### Phase 2: Deployment
- [ ] Deploy to staging with flag=false
- [ ] Verify telemetry logging works
- [ ] Test Group A (shadow only)
- [ ] Test Group B (structure active)
- [ ] Verify rollback procedure works

### Phase 3: Production Activation
- [ ] Set `ENABLE_STRUCTURE_ADAPTATION=true` in production
- [ ] Deploy to production
- [ ] Verify 50/50 group split
- [ ] Monitor metrics dashboard
- [ ] Set up alerts for red-line metrics

### Phase 4: Monitoring (First 48 Hours)
- [ ] Check metrics every 6 hours
- [ ] Watch for user complaints
- [ ] Verify no trust boundary violations
- [ ] Verify no enforcement violations
- [ ] Check sample size (target: 100 sessions)

### Phase 5: Evaluation (After 1 Week)
- [ ] Analyze primary metrics (must not degrade)
- [ ] Analyze secondary metrics (signal of improvement)
- [ ] Check red-line metrics (immediate rollback triggers)
- [ ] Review user feedback (if any)
- [ ] Make decision: Success / Neutral / Refinement / Failure

---

## Metrics Dashboard Spec

### Real-Time View (Every 6 Hours)

```
================================================================================
STRUCTURE A/B TEST — Real-Time Metrics
================================================================================

Sample Size:
  Group A (Control):   127 sessions, 543 turns
  Group B (Treatment): 131 sessions, 567 turns

Primary Metrics (Must Not Degrade):
  Follow-up Rate:
    Group A: 23.4%
    Group B: 22.1%  ✅ (-1.3%, GOOD)
  
  Avg Time-to-Next-Turn:
    Group A: 45.2s
    Group B: 43.8s  ✅ (-3.1%, GOOD)
  
  Refusal Rate:
    Group A: 2.1%
    Group B: 2.1%  ✅ (0.0%, IDENTICAL)
  
  Authority Distribution:
    Group A: memory=45%, system=53%, refused=2%
    Group B: memory=45%, system=53%, refused=2%  ✅ (IDENTICAL)

Secondary Metrics (Signal of Improvement):
  Artifact Satisfaction:
    Group A: 34.2%
    Group B: 41.7%  ✅ (+7.5%, GOOD)
  
  Clarification Rate:
    Group A: 8.3%
    Group B: 6.9%  ✅ (-1.4%, GOOD)
  
  Short Confirmations:
    Group A: 12.1%
    Group B: 14.3%  ✅ (+2.2%, GOOD)

Red-Line Metrics:
  Clarification Increase: -1.4%  ✅ (threshold: +5%)
  Trust Boundary Regression: None  ✅
  Enforcement Violations: None  ✅
  User Complaints: 0  ✅

Status: ✅ ALL METRICS GREEN — Continue test
================================================================================
```

---

## Rollback Checklist

### Immediate Rollback (Red-Line Triggered)

1. **Set feature flag to false**
   ```bash
   # In fly.toml or environment
   ENABLE_STRUCTURE_ADAPTATION=false
   ```

2. **Deploy immediately**
   ```bash
   fly deploy -c apps/maestra.8825.systems/backend/fly.toml --now
   ```

3. **Verify rollback**
   ```bash
   curl -s https://maestra-backend-8825-systems.fly.dev/health | jq '.feature_flags'
   ```

4. **Notify team**
   ```
   Subject: Structure A/B Test Rolled Back
   
   Red-line metric triggered: [METRIC_NAME]
   Group A: [VALUE]
   Group B: [VALUE]
   
   Feature flag disabled. All sessions now in control mode.
   
   Next steps: Analyze telemetry, document learning, decide on refinement vs skip.
   ```

5. **Document learning**
   - What triggered rollback?
   - What did we learn?
   - Should we refine and re-test, or skip this lever?

**No migrations. No cleanup. Just flip the flag.**

---

## Success Statement

> **"Even if this fails, we learned something valuable without breaking trust."**

This is the correct mindset for experimentation:
- Failure is data, not disaster
- Rollback is instant and safe
- Learning compounds regardless of outcome
- Trust boundary never violated

---

## Status

✅ A/B test plan complete
✅ Metrics defined
✅ Rollback procedure documented
✅ Learning framework established

**Ready for implementation when you give the word.**

---

## What Comes Next

### If You Want to Execute:
1. Implement feature flag and group assignment
2. Wire structure decision into context injection
3. Add telemetry logging
4. Deploy to staging for verification
5. Activate in production with monitoring

### If You Want to Review First:
1. Sanity-check metrics (are they measurable?)
2. Simulate failure cases (pre-mortem)
3. Verify rollback procedure (can we actually flip the flag instantly?)

### If You Want to Pause:
1. Document this plan
2. Let instrumentation run quietly
3. Gather more shadow data
4. Activate when ready

**Your call. The plan is ready.**
