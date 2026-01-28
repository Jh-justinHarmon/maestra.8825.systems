"""
TRACK 1 STEP 1: CI Import Lock (Full Mode Only)

This test ensures:
1. CI runs with MAESTRA_MINIMAL_MODE=false
2. All required routing.* modules can be imported
3. Legacy/forbidden paths (gates.*, backend_8825.*) do NOT exist

If someone reintroduces old paths → CI explodes.
"""
import os
import importlib
import pytest


def test_full_mode_enforced():
    """CI must run with MAESTRA_MINIMAL_MODE=false"""
    mode = os.getenv("MAESTRA_MINIMAL_MODE", "false").lower()
    assert mode == "false", (
        f"❌ CI must run with MAESTRA_MINIMAL_MODE=false, got '{mode}'"
    )


def test_required_modules_importable():
    """These MUST exist and import successfully in full mode"""
    required_modules = [
        "routing.context_router",
        "routing.memory_gate",
        "routing.maestra_memory",
    ]

    for mod in required_modules:
        try:
            importlib.import_module(mod)
        except Exception as e:
            pytest.fail(f"❌ Required module failed to import: {mod}\n{e}")


def test_forbidden_legacy_paths_blocked():
    """These MUST NOT be importable - they are legacy/wrong paths"""
    forbidden_modules = [
        "gates.memory_gate",
        "backend_8825.maestra_memory",
    ]

    for mod in forbidden_modules:
        try:
            importlib.import_module(mod)
            pytest.fail(f"❌ Forbidden legacy module should NOT exist: {mod}")
        except ModuleNotFoundError:
            pass  # Expected - this is correct
        except Exception as e:
            # Other errors are also acceptable (means it doesn't work)
            pass


def test_response_contains_truth_fields():
    """
    TRACK 2: AdvisorAskResponse MUST contain truth-on-surface fields.
    These fields make system state visible to users - no silent lies.
    """
    from models import AdvisorAskResponse
    fields = AdvisorAskResponse.model_fields

    required_truth_fields = ["system_mode", "authority"]
    
    for field in required_truth_fields:
        assert field in fields, f"❌ Missing truth field: {field}"
    
    # Verify system_mode is a Literal type with correct values
    system_mode_annotation = fields["system_mode"].annotation
    assert "full" in str(system_mode_annotation), "❌ system_mode must include 'full'"
    assert "minimal" in str(system_mode_annotation), "❌ system_mode must include 'minimal'"
    
    # Verify authority is a Literal type with correct values
    authority_annotation = fields["authority"].annotation
    assert "system" in str(authority_annotation), "❌ authority must include 'system'"
    assert "memory" in str(authority_annotation), "❌ authority must include 'memory'"
    assert "none" in str(authority_annotation), "❌ authority must include 'none'"
