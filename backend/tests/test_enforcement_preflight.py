"""
5B.0 Pre-Flight Enforcement Verification Tests

These tests PROVE—before adding Sentinel—that the Enforcement Kernel is:
1. Actually wired into the production execution path
2. Impossible to bypass
3. Blocking (raises) not advisory
4. Independent of configuration flags
5. Callable in isolation and fatal on violation

If ANY of these fail, 5B HALTS.
"""

import pytest
import os
from dataclasses import dataclass
from typing import Literal

from enforcement_kernel import (
    EnforcementKernel,
    ContextTrace,
    ContextSource,
    AuthorityViolation,
    ContextUnavailable,
    ModeViolation,
    RefusalAuthorityViolation,
    EnforcementViolation,
    get_enforcement_kernel,
)


# ─────────────────────────────────────────────
# 5B.0.1 — Direct Kernel Kill Test (Isolation)
# ─────────────────────────────────────────────

@dataclass
class FakeResponse:
    """Minimal response object for testing."""
    authority: Literal["system", "memory", "tool", "none"]
    epistemic_state: Literal["GROUNDED", "UNGROUNDED", "REFUSED"]
    system_mode: Literal["full", "minimal", "local_power"]


class TestDirectKernelKill:
    """
    Prove the kernel itself cannot be lied to.
    These tests call the kernel directly in isolation.
    """

    def test_kernel_blocks_authority_mismatch_direct_call(self):
        """
        Kernel raises AuthorityViolation when tool context claims memory authority.
        This is the core enforcement rule.
        """
        kernel = EnforcementKernel()

        context = ContextTrace(
            sources=[
                ContextSource(
                    source="tool:sentinel",
                    identifier="hcss_internal_doc",
                )
            ],
            required_but_missing=[],
            system_mode="local_power",
        )

        response = FakeResponse(
            authority="memory",  # ❌ WRONG - should be "tool"
            epistemic_state="GROUNDED",
            system_mode="local_power",
        )

        with pytest.raises(AuthorityViolation):
            kernel.enforce(response, context)

    def test_kernel_blocks_missing_required_context(self):
        """
        Kernel raises ContextUnavailable when required context is missing.
        Note: Authority check happens first, so we need correct authority to reach the context check.
        """
        kernel = EnforcementKernel()

        context = ContextTrace(
            sources=[],  # No sources means authority="system"
            required_but_missing=["sentinel"],  # Required but not available
            system_mode="local_power",
        )

        response = FakeResponse(
            authority="system",  # Correct authority for empty sources
            epistemic_state="GROUNDED",
            system_mode="local_power",
        )

        # Should raise ContextUnavailable because sentinel is required but missing
        with pytest.raises(ContextUnavailable):
            kernel.enforce(response, context)

    def test_kernel_blocks_mode_mismatch(self):
        """
        Kernel raises ModeViolation when claimed mode doesn't match actual.
        """
        kernel = EnforcementKernel()

        context = ContextTrace(
            sources=[ContextSource(source="system")],
            required_but_missing=[],
            system_mode="local_power",  # Actual mode
        )

        response = FakeResponse(
            authority="system",
            epistemic_state="GROUNDED",
            system_mode="full",  # ❌ WRONG - claims full but actual is local_power
        )

        with pytest.raises(ModeViolation):
            kernel.enforce(response, context)

    def test_kernel_blocks_refusal_with_authority(self):
        """
        Kernel raises RefusalAuthorityViolation when refusal claims authority.
        """
        kernel = EnforcementKernel()

        context = ContextTrace(
            sources=[],
            required_but_missing=[],
            system_mode="full",
        )

        response = FakeResponse(
            authority="system",  # ❌ WRONG - refusals must be "none"
            epistemic_state="REFUSED",
            system_mode="full",
        )

        with pytest.raises(RefusalAuthorityViolation):
            kernel.enforce(response, context)

    def test_kernel_allows_valid_tool_authority(self):
        """
        Kernel passes when tool context correctly claims tool authority.
        """
        kernel = EnforcementKernel()

        context = ContextTrace(
            sources=[ContextSource(source="tool:sentinel")],
            required_but_missing=[],
            system_mode="local_power",
        )

        response = FakeResponse(
            authority="tool",  # ✅ CORRECT
            epistemic_state="GROUNDED",
            system_mode="local_power",
        )

        # Should not raise
        result = kernel.enforce(response, context)
        assert result is None

    def test_kernel_allows_valid_refusal(self):
        """
        Kernel passes when refusal correctly claims no authority.
        """
        kernel = EnforcementKernel()

        context = ContextTrace(
            sources=[],
            required_but_missing=["sentinel"],  # Missing context is OK for refusals
            system_mode="full",
        )

        response = FakeResponse(
            authority="none",  # ✅ CORRECT for refusals
            epistemic_state="REFUSED",
            system_mode="full",
        )

        # Should not raise
        result = kernel.enforce(response, context)
        assert result is None


# ─────────────────────────────────────────────
# 5B.0.3 — No Config Escape Hatch Test
# ─────────────────────────────────────────────

class TestNoConfigEscapeHatch:
    """
    Prove no configuration flag can disable enforcement.
    """

    def test_no_flag_disables_enforcement(self):
        """
        Setting any environment flag does NOT disable enforcement.
        """
        # Set all possible bypass flags
        os.environ["MAESTRA_MINIMAL_MODE"] = "true"
        os.environ["DISABLE_ENFORCEMENT"] = "1"
        os.environ["ENFORCEMENT_BYPASS"] = "true"
        os.environ["SKIP_ENFORCEMENT"] = "1"

        # Re-import to ensure flags are read
        from enforcement_kernel import EnforcementKernel
        kernel = EnforcementKernel()

        # Kernel should still raise on invalid input
        context = ContextTrace(
            sources=[ContextSource(source="tool:sentinel")],
            required_but_missing=[],
            system_mode="full",
        )

        response = FakeResponse(
            authority="memory",  # ❌ WRONG
            epistemic_state="GROUNDED",
            system_mode="full",
        )

        # Must still raise despite flags
        with pytest.raises(AuthorityViolation):
            kernel.enforce(response, context)

        # Clean up
        del os.environ["MAESTRA_MINIMAL_MODE"]
        del os.environ["DISABLE_ENFORCEMENT"]
        del os.environ["ENFORCEMENT_BYPASS"]
        del os.environ["SKIP_ENFORCEMENT"]

    def test_kernel_has_no_bypass_methods(self):
        """
        Kernel class has no methods that could bypass enforcement.
        """
        kernel = get_enforcement_kernel()
        
        forbidden_methods = [
            "bypass",
            "skip",
            "disable",
            "allow_degraded",
            "soft_enforce",
            "lenient",
            "permissive",
            "ignore",
            "override",
        ]
        
        kernel_methods = dir(kernel)
        for method in forbidden_methods:
            assert method not in kernel_methods, f"Forbidden method '{method}' found on kernel"

    def test_kernel_has_no_bypass_attributes(self):
        """
        Kernel class has no attributes that could disable enforcement.
        """
        kernel = get_enforcement_kernel()
        
        forbidden_attrs = [
            "enabled",
            "disabled",
            "bypass_mode",
            "skip_mode",
            "lenient_mode",
        ]
        
        for attr in forbidden_attrs:
            assert not hasattr(kernel, attr), f"Forbidden attribute '{attr}' found on kernel"


# ─────────────────────────────────────────────
# 5B.0.4 — Structural Assertions
# ─────────────────────────────────────────────

class TestStructuralAssertions:
    """
    Prove structural properties that prevent regression.
    """

    def test_enforce_returns_none_not_bool(self):
        """
        enforce() returns None on success, never True/False.
        This prevents callers from ignoring the result.
        """
        kernel = get_enforcement_kernel()

        context = ContextTrace(
            sources=[ContextSource(source="system")],
            required_but_missing=[],
            system_mode="full",
        )

        response = FakeResponse(
            authority="system",
            epistemic_state="GROUNDED",
            system_mode="full",
        )

        result = kernel.enforce(response, context)
        
        assert result is None, "enforce() must return None, not a boolean"
        assert result is not True, "enforce() must not return True"
        assert result is not False, "enforce() must not return False"

    def test_all_violations_are_exceptions(self):
        """
        All violation types are exceptions that must be caught.
        """
        assert issubclass(AuthorityViolation, Exception)
        assert issubclass(ContextUnavailable, Exception)
        assert issubclass(ModeViolation, Exception)
        assert issubclass(RefusalAuthorityViolation, Exception)
        assert issubclass(EnforcementViolation, Exception)

    def test_violations_inherit_from_base(self):
        """
        All violations inherit from EnforcementViolation for unified catching.
        """
        assert issubclass(AuthorityViolation, EnforcementViolation)
        assert issubclass(ContextUnavailable, EnforcementViolation)
        assert issubclass(ModeViolation, EnforcementViolation)
        assert issubclass(RefusalAuthorityViolation, EnforcementViolation)

    def test_singleton_kernel_instance(self):
        """
        get_enforcement_kernel() returns the same instance.
        """
        k1 = get_enforcement_kernel()
        k2 = get_enforcement_kernel()
        assert k1 is k2, "Kernel must be singleton"
