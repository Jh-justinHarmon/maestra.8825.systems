# Maestra Enforcement Kernel v0.1 (LOCKED)

**Status:** 🔒 **LOCKED — normative**  
**File:** `backend/enforcement_kernel.py`  
**Effective:** 2026-01-28

---

## Purpose

The Enforcement Kernel is a **speech firewall**. It prevents Maestra from emitting responses that misrepresent provenance, authority, or capability.

It answers ONE question only:

> "Is Maestra allowed to speak this response truthfully?"

---

## MUST

- Be invoked **exactly once** per response
- Run **immediately before** response return
- **Raise on violation** (never return False)
- Be **non-bypassable** (no flags, no degraded modes)

---

## MUST NOT

- Choose tools
- Route queries
- Assemble context
- Evaluate answer quality
- Retry or fallback
- Log-and-continue
- Support escape hatches

---

## Enforcement Rules (Blocking)

All violations result in **REFUSAL**.

### Rule 1 — Authority Consistency

Response must claim the authority that matches its context sources.

| Context Sources | Required Authority |
|-----------------|-------------------|
| Any `tool:*` source | `"tool"` |
| `library` or `memory` | `"memory"` |
| `system` only | `"system"` |

**Violation:** `AuthorityViolation`

### Rule 2 — Required Context Availability

If context was required but missing, speech is not allowed.

**Violation:** `ContextUnavailable`

### Rule 3 — Mode Honesty

Response must accurately report the system mode (`full`, `minimal`, `local_power`).

**Violation:** `ModeViolation`

### Rule 4 — Refusal Integrity

Refusals must claim `authority="none"`.

**Violation:** `RefusalAuthorityViolation`

---

## Placement Requirement

The enforcement kernel must be called at the **single exit point** of response generation:

```python
response = assemble_response(...)
context_trace = build_context_trace(...)

# 🔴 ENFORCEMENT KERNEL — NON-BYPASSABLE
enforcement_kernel.enforce(response, context_trace)

return response
```

No other return paths are allowed past this point.

---

## Non-Goals

The Enforcement Kernel does NOT:

- Decide what tools to use
- Determine if an answer is "good enough"
- Provide fallback behavior
- Support partial enforcement
- Allow configuration-based bypass

---

## Exception Hierarchy

```
EnforcementViolation (base)
├── AuthorityViolation
├── ContextUnavailable
├── ModeViolation
└── RefusalAuthorityViolation
```

All exceptions are **blocking by design**. They must propagate and result in refusal.

---

## Why This Cannot Regress

| Anti-Pattern | How Kernel Prevents It |
|--------------|----------------------|
| Import but don't invoke | CI tests assert enforce() is called |
| Return False instead of raise | enforce() returns None, violations raise |
| Add bypass flag | CI tests assert no bypass methods exist |
| Log-and-continue | No logging in kernel, only raises |
| Conditional enforcement | No config flags, no mode checks |

---

## Contract Status

| Property | Status |
|----------|--------|
| Scope locked | ✅ |
| Non-bypassable | ✅ |
| Raises, not returns | ✅ |
| Prevents silent degradation | ✅ |
| Prevents advisory semantics | ✅ |
| Preserves capability freedom | ✅ |

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| v0.1 | 2026-01-28 | Initial locked contract |
