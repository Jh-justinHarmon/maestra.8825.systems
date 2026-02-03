# Enforcement Regression Tests

## Purpose

These tests prevent regression of the Behavior Kernel and enforcement mechanisms.

## Test Files

### `test_enforcement_structural.py`
**Structural tests** - verify code structure, not runtime behavior.

Tests:
1. All `advisor.py` returns use `enforce_and_return()`
2. `server.py` exception handler uses `enforce_and_return()`
3. No bypass flags exist in enforcement code
4. `enforce()` raises exceptions (not returns False)
5. `enforce_and_return()` actually calls `kernel.enforce()`

**Why structural?** These tests fail if someone:
- Comments out enforcement
- Adds a bypass flag
- Returns `False` instead of raising
- Imports but never calls

### `test_enforcement_invocation.py`
**Invocation tests** - verify enforcement is actually called at runtime.

Tests:
1. `enforce_and_return()` calls `kernel.enforce()`
2. Kernel is not stubbed
3. Kernel raises on violation
4. `build_context_trace()` creates valid traces

### `test_mcp_required.py`
**MCP contract tests** - verify REQUIRED vs OPTIONAL semantics.

Tests:
1. `library_bridge` is marked REQUIRED
2. `context_builder` is marked REQUIRED
3. All REQUIRED MCPs exist at expected paths
4. Missing `library_bridge` fails startup
5. Missing `context_builder` fails startup
6. OPTIONAL MCPs can be missing without failure

## Running Tests

```bash
# All enforcement tests
cd apps/maestra.8825.systems/backend
pytest tests/test_enforcement_*.py tests/test_mcp_required.py -v

# Structural only (fast)
pytest tests/test_enforcement_structural.py -v

# MCP contract only
pytest tests/test_mcp_required.py -v
```

## CI Integration

Tests run on every push and PR via `.github/workflows/enforcement-tests.yml`.

**CI fails if:**
- Any structural test fails
- Enforcement is bypassed
- REQUIRED MCPs are missing
- Enforcement violations don't raise

## Anti-Patterns Prevented

1. **Import But Never Call** - Structural tests verify calls exist
2. **Return False Instead of Raise** - AST analysis checks return types
3. **Advisory Semantics** - Tests verify exceptions are raised
4. **Bypass Flags** - Pattern matching detects bypass keywords
5. **Missing REQUIRED MCPs** - Startup validation enforced

## Maintenance

**DO NOT:**
- Weaken these tests
- Add `pytest.skip()` without justification
- Mock out enforcement in production code paths
- Add bypass flags to make tests pass

**DO:**
- Add new structural tests for new return paths
- Update tests when adding new REQUIRED MCPs
- Keep tests fast (structural > behavioral)
- Fail loudly on violations
