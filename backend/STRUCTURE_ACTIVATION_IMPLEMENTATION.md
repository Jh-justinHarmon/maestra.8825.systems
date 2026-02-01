# Structure Adaptation — Implementation Complete

## What Was Implemented

Successfully implemented the feature flag and activation logic for the `structure` lever (first personalization lever from PROMPT 9).

### Files Created

1. **`config.py`** - Feature flag configuration
   - `ENABLE_STRUCTURE_ADAPTATION` - Global feature flag (env var)
   - `STRUCTURE_AB_TEST_PERCENTAGE` - A/B test split percentage (default: 50%)

2. **`ab_test.py`** - A/B test logic
   - `assign_group(session_id)` - Deterministic group assignment (A or B)
   - `should_apply_structure()` - Decision logic for structure activation

3. **`response_formatter.py`** - Response formatting utilities
   - `get_formatting_hint()` - Returns formatting hint for system prompt

### Files Modified

1. **`context_injection.py`** - Added formatting hint support
   - Added `formatting_hint` parameter to `inject_context_into_prompt()`
   - Formatting hint appended to system prompt when structure is enabled

2. **`advisor.py`** - Wired structure adaptation into main flow
   - Imported config, ab_test, and response_formatter modules
   - Compute structure decision using mediator + A/B test logic
   - Pass formatting hint to context injection
   - Log telemetry: `ab_test_group`, `structure_applied`, `structure_feature_enabled`

---

## How It Works

### 1. Group Assignment (A/B Test)
```python
# Deterministic assignment based on session_id hash
group = assign_group(session_id, test_percentage=50)
# Returns "A" (control) or "B" (treatment)
```

### 2. Structure Decision
```python
apply_structure, ab_group = should_apply_structure(
    tools_requested=user_metadata.get("tools_requested", False),
    mediator_structure=mediator_decision.structure,
    mediator_confidence=mediator_decision.confidence,
    session_id=request.session_id,
    feature_enabled=ENABLE_STRUCTURE_ADAPTATION,
    test_percentage=STRUCTURE_AB_TEST_PERCENTAGE
)
```

**Activation Rule:**
- Feature flag must be enabled
- Session must be in Group B (treatment)
- AND one of:
  - `tools_requested = True` (explicit artifact request)
  - `mediator.structure = "structured"` AND `confidence >= 0.7`

### 3. Formatting Hint Injection
```python
formatting_hint = get_formatting_hint(apply_structure)
# Returns formatting instructions for system prompt if apply_structure=True

messages = inject_context_into_prompt(
    query=question,
    chain_results=chain_results,
    grounding_sources=library_sources,
    epistemic_state=epistemic_state,
    formatting_hint=formatting_hint  # Added to system prompt
)
```

**Formatting Hint (when applied):**
```
Format your response with clear structure:
- Use bullet points for lists
- Use code blocks for code/scripts
- Use headings for sections
- Keep explanations concise
```

### 4. Telemetry Logging
Every response now logs:
```json
{
  "ab_test_group": "A" | "B",
  "structure_applied": true | false,
  "structure_feature_enabled": true | false,
  "shadow_mediator_decision": {
    "structure": "conversational" | "structured",
    "confidence": 0.72
  }
}
```

---

## Deployment Instructions

### Step 1: Deploy with Feature Flag OFF (Sanity Check)

```bash
# Set environment variables
export ENABLE_STRUCTURE_ADAPTATION=false
export STRUCTURE_AB_TEST_PERCENTAGE=50

# Deploy to staging
cd apps/maestra.8825.systems/backend
fly deploy -c fly.toml --app maestra-backend-staging

# Verify deployment
curl -s https://maestra-backend-staging.fly.dev/health | jq '.feature_flags'
# Should show: {"structure_adaptation": false, "structure_ab_test_percentage": 50}
```

**Test:**
- Send a few queries
- Verify responses are normal (no structured formatting)
- Check logs for telemetry (should show `structure_applied: false` for all)

---

### Step 2: Enable Feature Flag (Production A/B Test)

```bash
# Enable structure adaptation
export ENABLE_STRUCTURE_ADAPTATION=true
export STRUCTURE_AB_TEST_PERCENTAGE=50

# Deploy to production
fly deploy -c fly.toml --app maestra-backend-prod

# Verify deployment
curl -s https://maestra-backend-prod.fly.dev/health | jq '.feature_flags'
# Should show: {"structure_adaptation": true, "structure_ab_test_percentage": 50}
```

**What Happens:**
- 50% of sessions assigned to Group A (control, no structure)
- 50% of sessions assigned to Group B (treatment, structure when rule matches)
- Assignment is sticky per session_id
- Telemetry logs group assignment and structure decisions

---

### Step 3: Monitor Metrics (48-72 Hours)

**Check every 6 hours:**

1. **Sample Size**
   ```bash
   # Query session continuity logs
   # Count sessions in Group A vs Group B
   # Target: ~50/50 split
   ```

2. **Primary Metrics** (must not degrade)
   - Follow-up rate (Group A vs Group B)
   - Time-to-next-action
   - Refusal rate (should be identical)
   - Authority distribution (should be identical)

3. **Secondary Metrics** (signal of improvement)
   - Artifact satisfaction (short confirmations after code delivery)
   - Clarification prompts ("reformat this", "can you...")
   - User complaints about formatting

4. **Red-Line Triggers** (immediate rollback)
   - >5% increase in clarification questions
   - Any trust boundary regression
   - Any enforcement violation
   - User complaints about "robotic" or "weird formatting"

---

### Step 4: Rollback Procedure (If Needed)

```bash
# Disable feature flag
export ENABLE_STRUCTURE_ADAPTATION=false

# Redeploy immediately
fly deploy -c fly.toml --app maestra-backend-prod --now

# Verify rollback
curl -s https://maestra-backend-prod.fly.dev/health | jq '.feature_flags.structure_adaptation'
# Should return: false

# Done. No migrations. No cleanup.
```

---

## Verification Steps

### Test Case 1: Artifact Request (Should Trigger Structure)

**Query:** "Create a script to validate enforcement invariants"

**Expected (Group B):**
- System prompt includes formatting hint
- Response uses code blocks, bullets, headings
- Telemetry shows: `structure_applied: true`, `ab_test_group: "B"`

**Expected (Group A):**
- System prompt does NOT include formatting hint
- Response uses conversational formatting
- Telemetry shows: `structure_applied: false`, `ab_test_group: "A"`

---

### Test Case 2: Conversational Query (Should NOT Trigger Structure)

**Query:** "What's the difference between grounding and authority?"

**Expected (Both Groups):**
- System prompt does NOT include formatting hint
- Response uses conversational formatting
- Telemetry shows: `structure_applied: false` for both groups

---

### Test Case 3: Group Assignment Consistency

**Test:**
1. Send query with `session_id: "test_123"`
2. Check telemetry for group assignment (e.g., "B")
3. Send another query with same `session_id: "test_123"`
4. Verify group assignment is still "B" (sticky)

---

## Current State

✅ **Implementation Complete**
- Feature flag created (`ENABLE_STRUCTURE_ADAPTATION`)
- A/B test logic implemented (50/50 split)
- Structure decision wired into advisor flow
- Formatting hint injected into system prompt
- Telemetry logging added

⏸️ **Deployment Pending**
- Feature flag currently OFF (not deployed)
- Need to deploy to staging first (sanity check)
- Then deploy to production with flag ON

📊 **Monitoring Ready**
- Telemetry captures all required metrics
- Group assignment logged per session
- Structure decisions logged per turn
- Ready for 48-72 hour observation window

---

## What This Fixes

**Before (The Problem You Showed):**
- Verbose responses when you wanted concise
- No adaptation to user preferences
- No structure for artifact requests
- Instrumentation existed but wasn't applied

**After (With Structure Enabled):**
- Artifact requests get structured formatting (code blocks, bullets)
- Conversational queries stay conversational
- 50% A/B test to validate effectiveness
- Instant rollback if it doesn't work

---

## Next Steps

1. **Deploy to staging** with flag=false (sanity check)
2. **Test both groups** (verify A/B assignment works)
3. **Deploy to production** with flag=true
4. **Monitor for 48-72 hours** (check metrics every 6 hours)
5. **Evaluate results** (success / neutral / failure)
6. **If success:** Proceed to PROMPT 11 (`ask_clarifying_question`)
7. **If failure:** Rollback, document learning, refine or skip

---

## Status

✅ Code implementation complete
⏸️ Awaiting deployment approval
📊 Telemetry ready
🚨 Rollback procedure documented

**Ready to deploy when you give the word.**
