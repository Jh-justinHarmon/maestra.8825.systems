# PROMPT 9: First Lever Selection — Risk-Minimized Evaluation

## Evaluation Framework

Each lever scored on 6 dimensions (0-5 scale):
- **Accuracy**: How often is this decision correct?
- **User Harm**: If wrong, how annoying/confusing is it?
- **Trust Risk**: Could this affect authority, truth, or refusals?
- **Reversibility**: Can we turn it off instantly without side effects?
- **Detectability**: Would users notice if it misfires?
- **Signal Clarity**: Does activation generate clear success/failure signal?

---

## LEVER 1: `structure` (conversational vs structured)

### Scorecard

```
LEVER: structure

Accuracy:        5/5  (100% in PROMPT 7, universal in PROMPT 8)
User Harm:       1/5  (minimal - just formatting difference)
Trust Risk:      0/5  (zero - does not affect content or authority)
Reversibility:   5/5  (instant - just changes formatting)
Detectability:   2/5  (low - users may not notice)
Signal Clarity:  4/5  (good - can measure structured vs conversational preference)

Total Risk Profile: VERY LOW
Overall Score: 17/30 (harm-adjusted: excellent)
```

### Failure Mode Analysis

**What happens if this fires when it shouldn't?**
- User asks conversational question, gets structured response (bullets, numbered lists)
- OR: User asks for artifact, gets conversational response

**How would a casual user experience the mistake?**
- **Scenario 1:** User asks "Tell me about enforcement" → Gets bullet points instead of paragraph
  - **Impact:** Mildly unexpected but not confusing
  - **Self-correcting:** User can easily read either format
  
- **Scenario 2:** User asks "Create a script" → Gets conversational explanation instead of code block
  - **Impact:** More noticeable, user might ask again
  - **Self-correcting:** User will clarify "just give me the code"

**Is the mistake self-correcting next turn?**
- **Yes** - User can easily clarify format preference
- **Yes** - No persistent state, next turn starts fresh

### Safety Verdict

**SAFE**

**Reasoning:**
- 100% accuracy in testing
- Universal across all archetypes
- Zero trust risk (formatting only)
- Instantly reversible
- Mistakes are cosmetic, not semantic
- Self-correcting within 1 turn

**Activation Rule:**
- Activate when `tools_requested = true` OR `structure = "structured"`
- No confidence threshold needed (100% accuracy)
- Feature flag: `ENABLE_STRUCTURE_ADAPTATION`

---

## LEVER 2: `ask_clarifying_question`

### Scorecard

```
LEVER: ask_clarifying_question

Accuracy:        4/5  (93.3% in PROMPT 7)
User Harm:       3/5  (moderate - could feel patronizing if wrong)
Trust Risk:      1/5  (low - could delay answer but doesn't change content)
Reversibility:   5/5  (instant - just adds a question)
Detectability:   4/5  (high - users will notice extra question)
Signal Clarity:  5/5  (excellent - user response shows if helpful)

Total Risk Profile: MODERATE
Overall Score: 22/30 (harm-adjusted: good but risky)
```

### Failure Mode Analysis

**What happens if this fires when it shouldn't?**
- User asks clear question, system asks for clarification unnecessarily

**How would a casual user experience the mistake?**
- **Scenario 1:** User asks "Deploy to staging" → System asks "Which environment?"
  - **Impact:** Annoying - question was clear
  - **User reaction:** "I just said staging"
  
- **Scenario 2:** User asks "What's the difference between X and Y?" → System asks "Which aspect are you interested in?"
  - **Impact:** Patronizing - user wants general answer
  - **User reaction:** Frustration or ignoring the question

**Is the mistake self-correcting next turn?**
- **Partially** - User can ignore the question and repeat original query
- **Risk:** User might abandon conversation if feels patronized

### Safety Verdict

**SAFE WITH CONFIDENCE THRESHOLD**

**Reasoning:**
- 93.3% accuracy when confident
- Moderate harm if wrong (patronizing)
- Low trust risk (doesn't change content)
- Highly detectable (good for learning)
- Excellent signal clarity (user response shows value)

**Activation Rule:**
- Activate when `alignment_signal = true` AND `confidence ≥ 0.75`
- Feature flag: `ENABLE_CLARIFYING_QUESTIONS`
- **Defer to second lever** - too risky for first activation

---

## LEVER 3: `show_reasoning`

### Scorecard

```
LEVER: show_reasoning

Accuracy:        4/5  (90% in PROMPT 7)
User Harm:       2/5  (low-moderate - extra text if wrong)
Trust Risk:      2/5  (low-moderate - could expose uncertainty)
Reversibility:   4/5  (mostly instant, but response already sent)
Detectability:   3/5  (moderate - users notice extra explanation)
Signal Clarity:  3/5  (moderate - hard to measure if helpful)

Total Risk Profile: MODERATE
Overall Score: 18/30 (harm-adjusted: moderate)
```

### Failure Mode Analysis

**What happens if this fires when it shouldn't?**
- User asks simple question, gets verbose explanation with reasoning

**How would a casual user experience the mistake?**
- **Scenario 1:** User asks "What's the status?" → Gets detailed explanation of how status was determined
  - **Impact:** Too verbose, user wanted quick answer
  - **User reaction:** Skips to end, ignores reasoning
  
- **Scenario 2:** User asks "Deploy to staging" → Gets explanation of deployment process
  - **Impact:** Annoying, user wanted action not explanation
  - **User reaction:** "Just do it"

**Is the mistake self-correcting next turn?**
- **No** - Response already sent with extra reasoning
- **Partially** - User can ask "just give me the answer" next time
- **Risk:** Casual users might find system too verbose

### Safety Verdict

**SAFE WITH CONFIDENCE THRESHOLD**

**Reasoning:**
- 90% accuracy when confident
- Low-moderate harm (extra text, not wrong content)
- Low-moderate trust risk (could expose uncertainty inappropriately)
- Not fully reversible (response already sent)
- Moderate detectability
- Hard to measure success (did reasoning help?)

**Activation Rule:**
- Activate when `depth_requested = true` AND `confidence ≥ 0.75`
- Feature flag: `ENABLE_REASONING_DISPLAY`
- **Defer to third lever** - trust risk and measurement difficulty

---

## LEVER 4: `verbosity`

### Scorecard

```
LEVER: verbosity

Accuracy:        3/5  (73.3% in PROMPT 7)
User Harm:       4/5  (high - wrong verbosity is very noticeable)
Trust Risk:      1/5  (low - doesn't change content truth)
Reversibility:   3/5  (moderate - response already sent)
Detectability:   5/5  (very high - users definitely notice)
Signal Clarity:  2/5  (low - hard to measure optimal verbosity)

Total Risk Profile: HIGH
Overall Score: 18/30 (harm-adjusted: risky)
```

### Failure Mode Analysis

**What happens if this fires when it shouldn't?**
- User gets response that's too terse or too verbose for their needs

**How would a casual user experience the mistake?**
- **Scenario 1:** User asks "Why did we choose X?" → Gets terse "Because Y" (verbosity=low)
  - **Impact:** Frustrating - user wanted explanation
  - **User reaction:** Asks follow-up "Can you explain more?"
  
- **Scenario 2:** User asks "What's the status?" → Gets 3 paragraphs (verbosity=high)
  - **Impact:** Annoying - user wanted quick answer
  - **User reaction:** Skips to end, frustrated by length

**Is the mistake self-correcting next turn?**
- **No** - Response already sent at wrong verbosity
- **Partially** - User can ask "shorter" or "more detail"
- **Risk:** Repeated mistakes could drive users away

### Safety Verdict

**DEFER**

**Reasoning:**
- Only 73.3% accuracy (lowest of all levers)
- High user harm (very noticeable when wrong)
- Not fully reversible (response already sent)
- Very high detectability (users will complain)
- Low signal clarity (hard to know optimal verbosity)
- Highest variance across archetypes (PROMPT 8)

**Activation Rule:**
- **DO NOT ACTIVATE as first lever**
- Requires confidence ≥ 0.80 (higher than others)
- Defer until after safer levers validated
- Feature flag: `ENABLE_VERBOSITY_ADAPTATION` (disabled)

---

## Comparative Analysis

### Risk Profile Ranking (Lowest to Highest)

1. **`structure`** - VERY LOW risk
   - 100% accuracy, universal, cosmetic only
   - Mistakes are formatting, not content
   - Instantly reversible, self-correcting
   
2. **`show_reasoning`** - MODERATE risk
   - 90% accuracy, low-moderate harm
   - Mistakes add extra text (annoying but not wrong)
   - Partially reversible, trust risk present
   
3. **`ask_clarifying_question`** - MODERATE risk
   - 93.3% accuracy, moderate harm
   - Mistakes feel patronizing
   - Highly detectable, excellent signal clarity
   
4. **`verbosity`** - HIGH risk
   - 73.3% accuracy, high harm
   - Mistakes very noticeable
   - Hard to measure success

### "If this were wrong 10% of the time, I'd still ship it" Test

**`structure`:**
- ✅ **YES** - 10% wrong = occasional bullet points vs paragraphs
- Impact: Cosmetic, users won't care
- **I'd ship it**

**`ask_clarifying_question`:**
- ⚠️ **MAYBE** - 10% wrong = 1 in 10 unnecessary questions
- Impact: Mildly annoying, could feel patronizing
- **I'd ship it with confidence ≥ 0.75**

**`show_reasoning`:**
- ⚠️ **MAYBE** - 10% wrong = occasional verbose explanations
- Impact: Extra text, users skip it
- **I'd ship it with confidence ≥ 0.75**

**`verbosity`:**
- ❌ **NO** - 10% wrong = 1 in 10 responses too terse or verbose
- Impact: Frustrating, users complain
- **I would NOT ship it yet**

---

## DECISION

### ✅ RECOMMENDED LEVER: `structure`

**Lever Name:** `structure` (conversational vs structured)

**Exact Activation Rule:**
```python
if tools_requested == True:
    use_structured_format = True
elif mediator_decision.structure == "structured" and confidence >= 0.7:
    use_structured_format = True
else:
    use_structured_format = False
```

**Feature Flag:** `ENABLE_STRUCTURE_ADAPTATION = true`

**Confidence Threshold:** ≥ 0.7 (for mediator-driven decisions)

**Required Signals:** `tools_requested = true` OR (`structure = "structured"` AND `confidence ≥ 0.7`)

---

### Why This Lever?

1. **Boringly Safe**
   - 100% accuracy in testing
   - Universal across all archetypes
   - Zero trust risk (formatting only)
   - Instantly reversible

2. **Minimal Harm**
   - Mistakes are cosmetic (bullets vs paragraphs)
   - Users can read either format easily
   - Self-correcting within 1 turn

3. **Clean Signal**
   - Easy to measure: Did user ask for artifact? Did they get structured format?
   - Clear success metric: Artifact requests get code blocks
   - Clear failure metric: Conversational queries stay conversational

4. **No Controversy**
   - No one complains about formatting choices
   - No personality implications
   - No trust boundary violations

---

### Why NOT the Other Three?

#### `ask_clarifying_question` - DEFERRED (Second Lever)
**Why tempting:**
- 93.3% accuracy (excellent)
- Excellent signal clarity (user response shows value)
- High value when correct (prevents misunderstandings)

**Why deferred:**
- Moderate harm if wrong (patronizing)
- More noticeable than structure
- Better as second lever after structure validated

**When to activate:** After `structure` proves safe, activate with confidence ≥ 0.75

---

#### `show_reasoning` - DEFERRED (Third Lever)
**Why tempting:**
- 90% accuracy (good)
- Aligns with user's explicit depth requests
- Could improve understanding

**Why deferred:**
- Trust risk (could expose uncertainty inappropriately)
- Hard to measure success (did reasoning help?)
- Not fully reversible (response already sent)
- Better after clarifying questions validated

**When to activate:** After `ask_clarifying_question` proves safe, activate with confidence ≥ 0.75

---

#### `verbosity` - DEFERRED (Fourth Lever or Never)
**Why tempting:**
- Could significantly improve UX
- Adapts to user preferences

**Why deferred:**
- Only 73.3% accuracy (too low for first lever)
- High harm when wrong (very noticeable)
- Highest variance across archetypes
- Requires more data to calibrate

**When to activate:** Only after all other levers validated, requires confidence ≥ 0.80, may need per-user calibration

---

## Activation Checklist

Before activating `structure`:

1. ✅ Add feature flag `ENABLE_STRUCTURE_ADAPTATION`
2. ✅ Wire flag into context injection
3. ✅ Add telemetry for structure decisions
4. ✅ Create rollback procedure (set flag to false)
5. ✅ Define success metrics (artifact requests get structured format)
6. ✅ Define failure metrics (conversational queries stay conversational)
7. ✅ Set up A/B test (50% shadow, 50% active)

---

## Success Criteria

After 1 week of activation, we should see:

**Success Signals:**
- Artifact requests (tools_requested=true) get structured format 100% of time
- No user complaints about formatting
- No increase in follow-up questions about format
- Telemetry shows structure decisions align with user intent

**Failure Signals:**
- Users complain about bullet points when they wanted paragraphs
- Increase in "just give me the answer" follow-ups
- Telemetry shows structure decisions misaligned with user intent

**Rollback Triggers:**
- >5% of users complain about formatting
- >10% increase in follow-up questions
- Any trust boundary violations detected

---

## Statement of Confidence

> **"If this lever were wrong 10% of the time, I'd still ship it."**

**YES.** 

10% wrong for `structure` means:
- 1 in 10 responses has bullets instead of paragraphs (or vice versa)
- Users can still read and understand the content
- No semantic changes, no trust violations
- Self-correcting within 1 turn

This is **cosmetic variance**, not **semantic error**.

**I would ship it.**

---

## READY FOR PROMPT 10

With `structure` selected as first lever, we can now design:
- A/B test methodology
- Metrics dashboard
- Rollback procedure
- Learning framework (even if it fails)

**Status:** ✅ First lever selected. Ready for PROMPT 10 (A/B Test Design).
