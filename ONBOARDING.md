# Maestra Developer Onboarding

Welcome to Maestra development. Before you begin, read this carefully.

## Rule #1: Prove Runtime Identity First

**"If /health does not prove identity, assume you are debugging the wrong system."**

This rule overrides intuition, logs, and assumptions.

This rule exists because:
- Multiple backend copies existed in the codebase
- Developers wasted hours debugging the wrong backend
- Fixes were applied to shadow backends that never loaded

### How to Prove Runtime Identity

Run this command:
```bash
./apps/maestra.8825.systems/backend/verify_runtime.sh
```

Expected output:
```
✅ PASS: All runtime identity checks passed
This is the canonical Maestra backend.
```

If you see anything else, **STOP** and read `CANONICAL_REALITY.md`.

## Rule #2: One Backend, One Truth

**Canonical backend location:**
```
apps/maestra.8825.systems/backend/
```

**This is the ONLY backend you may edit or run locally.**

All other backends are:
- Deprecated (system/maestra/)
- Deployment-only (system/tools/maestra_backend/)
- Poisoned to crash on import

## Rule #3: One Startup Method

**Canonical startup command:**
```bash
./apps/maestra.8825.systems/backend/start.sh
```

**No other startup method is supported.**

Do NOT:
- Run `python3 -m uvicorn server:app` directly
- Start from a different directory
- Omit PYTHONPATH
- Use any other startup script

## Required Reading

Before making any changes:

1. **[CANONICAL_REALITY.md](../../CANONICAL_REALITY.md)** - Authoritative backend documentation
2. **[START_BACKEND.md](backend/START_BACKEND.md)** - Startup instructions
3. **[verify_runtime.sh](backend/verify_runtime.sh)** - Runtime verification

## Enforcement

These rules are enforced by:

1. **Startup guards** - Backend crashes if started from wrong location
2. **PYTHONPATH guards** - Backend crashes if system/ not in PYTHONPATH
3. **Pre-commit hooks** - Commits blocked if shadow backends detected
4. **CI tests** - Build fails if shadow backends are importable
5. **Runtime identity** - Health endpoint exposes exact paths and PID

## What Happens If You Violate These Rules

- Your commit will be rejected by pre-commit hook
- CI will fail
- The backend will crash on startup
- Your debugging session will be wasted

## Getting Help

If you're stuck:

1. Run `./apps/maestra.8825.systems/backend/verify_runtime.sh`
2. If it fails, read the error message
3. If still stuck, read `CANONICAL_REALITY.md`
4. If STILL stuck, ask for help with the verification output

**Do NOT skip step 1.**

---

Last updated: 2026-02-02
