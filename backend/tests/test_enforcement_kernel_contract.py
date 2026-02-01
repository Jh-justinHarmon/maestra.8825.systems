"""
Enforcement Kernel Contract Tests (CI KILL TESTS)

These tests PROVE the enforcement kernel cannot be bypassed.
They test STRUCTURAL IMPOSSIBILITY OF LYING, not behavior.

If anyone:
- Removes enforcement
- Returns False
- Adds a bypass flag
- Softens a rule

👉 CI fails immediately
"""

import pytest
from dataclasses import dataclass
from typing import Literal

from enforcement_kernel import (
    EnforcementKernel,
    ContextTrace,
    ContextSource,
    EnforcementViolation,
    AuthorityViolation,
    ContextUnavailable,
    ModeViolation,
    RefusalAuthorityViolation,
    get_enforcement_kernel,
)


# ─────────────────────────────────────────────
# Test Fixtures
# ─────────────────────────────────────────────

@dataclass
class FakeResponse:
    """Minimal response object for testing."""
    authority: Literal["system", "memory", "tool", "none"]
    epistemic_state: Literal["GROUNDED", "UNGROUNDED", "REFUSED"]
    system_mode: Literal["full", "minimal", "local_power"]


@pytest.fixture
def kernel():
    return EnforcementKernel()


# ─────────────────────────────────────────────
# Rule 1: Authority Consistency Tests
# ─────────────────────────────────────────────

class TestAuthorityConsistency:
    """Test that authority must match derived authority from context."""

    def test_tool_context_requires_tool_authority(self, kernel):
        """Tool sources require tool authority."""
        context = ContextTrace(
            sources=[ContextSource(source="tool:sentinel")],
            required_but_missing=[],
            system_mode="full",
        )
        response = FakeResponse(
            authority="system",  # WRONG - should be "tool"
            epistemic_state="GROUNDED",
            system_mode="full",
        )
        with pytest.raises(AuthorityViolation):
            kernel.enforce(response, context)

    def test_tool_context_with_tool_authority_passes(self, kernel):
        """Tool sources with tool authority passes."""
        context = ContextTrace(
            sources=[ContextSource(source="tool:sentinel")],
            required_but_missing=[],
            system_mode="full",
        )
        response = FakeResponse(
            authority="tool",
            epistemic_state="GROUNDED",
            system_mode="full",
        )
        result = kernel.enforce(response, context)
        assert result is None

    def test_memory_context_requires_memory_authority(self, kernel):
        """Memory/library sources require memory authority."""
        context = ContextTrace(
            sources=[ContextSource(source="library", identifier="K-00001")],
            required_but_missing=[],
            system_mode="full",
        )
        response = FakeResponse(
            authority="system",  # WRONG - should be "memory"
            epistemic_state="GROUNDED",
            system_mode="full",
        )
        with pytest.raises(AuthorityViolation):
            kernel.enforce(response, context)

    def test_memory_context_with_memory_authority_passes(self, kernel):
        """Memory sources with memory authority passes."""
        context = ContextTrace(
            sources=[ContextSource(source="memory")],
            required_but_missing=[],
            system_mode="full",
        )
        response = FakeResponse(
            authority="memory",
            epistemic_state="GROUNDED",
            system_mode="full",
        )
        result = kernel.enforce(response, context)
        assert result is None

    def test_system_only_context_requires_system_authority(self, kernel):
        """System-only sources require system authority."""
        context = ContextTrace(
            sources=[ContextSource(source="system")],
            required_but_missing=[],
            system_mode="full",
        )
        response = FakeResponse(
            authority="memory",  # WRONG - should be "system"
            epistemic_state="GROUNDED",
            system_mode="full",
        )
        with pytest.raises(AuthorityViolation):
            kernel.enforce(response, context)

    def test_empty_context_requires_system_authority(self, kernel):
        """Empty context defaults to system authority."""
        context = ContextTrace(
            sources=[],
            required_but_missing=[],
            system_mode="full",
        )
        response = FakeResponse(
            authority="system",
            epistemic_state="GROUNDED",
            system_mode="full",
        )
        result = kernel.enforce(response, context)
        assert result is None

    def test_mixed_tool_and_memory_requires_tool(self, kernel):
        """Mixed tool + memory sources require tool authority (tool wins)."""
        context = ContextTrace(
            sources=[
                ContextSource(source="memory"),
                ContextSource(source="tool:sentinel"),
            ],
            required_but_missing=[],
            system_mode="full",
        )
        response = FakeResponse(
            authority="memory",  # WRONG - tool wins
            epistemic_state="GROUNDED",
            system_mode="full",
        )
        with pytest.raises(AuthorityViolation):
            kernel.enforce(response, context)


# ─────────────────────────────────────────────
# Rule 2: Required Context Availability Tests
# ─────────────────────────────────────────────

class TestContextAvailability:
    """Test that missing required context blocks speech."""

    def test_missing_required_context_blocks(self, kernel):
        """Missing required context raises ContextUnavailable."""
        context = ContextTrace(
            sources=[],
            required_but_missing=["sentinel"],
            system_mode="full",
        )
        response = FakeResponse(
            authority="system",
            epistemic_state="GROUNDED",
            system_mode="full",
        )
        with pytest.raises(ContextUnavailable):
            kernel.enforce(response, context)

    def test_multiple_missing_context_blocks(self, kernel):
        """Multiple missing contexts all reported."""
        context = ContextTrace(
            sources=[],
            required_but_missing=["sentinel", "deep_research", "library"],
            system_mode="full",
        )
        response = FakeResponse(
            authority="system",
            epistemic_state="GROUNDED",
            system_mode="full",
        )
        with pytest.raises(ContextUnavailable) as exc_info:
            kernel.enforce(response, context)
        assert "sentinel" in str(exc_info.value)

    def test_no_missing_context_passes(self, kernel):
        """No missing context allows speech."""
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
        assert result is None


# ─────────────────────────────────────────────
# Rule 3: Mode Honesty Tests
# ─────────────────────────────────────────────

class TestModeHonesty:
    """Test that response must accurately report system mode."""

    def test_mode_mismatch_raises(self, kernel):
        """Claiming wrong mode raises ModeViolation."""
        context = ContextTrace(
            sources=[ContextSource(source="system")],
            required_but_missing=[],
            system_mode="minimal",
        )
        response = FakeResponse(
            authority="system",
            epistemic_state="GROUNDED",
            system_mode="full",  # WRONG - actual is minimal
        )
        with pytest.raises(ModeViolation):
            kernel.enforce(response, context)

    def test_mode_match_passes(self, kernel):
        """Matching mode passes."""
        context = ContextTrace(
            sources=[ContextSource(source="system")],
            required_but_missing=[],
            system_mode="local_power",
        )
        response = FakeResponse(
            authority="system",
            epistemic_state="GROUNDED",
            system_mode="local_power",
        )
        result = kernel.enforce(response, context)
        assert result is None


# ─────────────────────────────────────────────
# Rule 4: Refusal Integrity Tests
# ─────────────────────────────────────────────

class TestRefusalIntegrity:
    """Test that refusals must claim authority='none'."""

    def test_refusal_with_authority_raises(self, kernel):
        """Refusal claiming authority raises RefusalAuthorityViolation."""
        context = ContextTrace(
            sources=[],
            required_but_missing=[],
            system_mode="full",
        )
        response = FakeResponse(
            authority="system",  # WRONG - refusals must be "none"
            epistemic_state="REFUSED",
            system_mode="full",
        )
        with pytest.raises(RefusalAuthorityViolation):
            kernel.enforce(response, context)

    def test_refusal_with_none_authority_passes(self, kernel):
        """Refusal with authority='none' passes."""
        context = ContextTrace(
            sources=[],
            required_but_missing=["library"],  # Missing context is OK for refusals
            system_mode="full",
        )
        response = FakeResponse(
            authority="none",
            epistemic_state="REFUSED",
            system_mode="full",
        )
        result = kernel.enforce(response, context)
        assert result is None


# ─────────────────────────────────────────────
# Structural Non-Bypass Tests
# ─────────────────────────────────────────────

class TestNonBypassStructure:
    """Test that bypass mechanisms cannot exist."""

    def test_no_bypass_flag_exists(self, kernel):
        """No bypass flags or soft enforcement methods exist."""
        kernel_methods = dir(kernel)
        forbidden = [
            "allow_degraded",
            "bypass",
            "soft_enforce",
            "skip",
            "disable",
            "ignore",
            "lenient",
            "permissive",
        ]
        for name in forbidden:
            assert name not in kernel_methods, f"Forbidden method '{name}' found on kernel"

    def test_enforce_returns_none_not_bool(self, kernel):
        """enforce() returns None on success, not True."""
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
        assert result is None
        assert result is not True
        assert result is not False

    def test_enforce_raises_not_returns_false(self, kernel):
        """Violations raise exceptions, never return False."""
        context = ContextTrace(
            sources=[ContextSource(source="tool:sentinel")],
            required_but_missing=[],
            system_mode="full",
        )
        response = FakeResponse(
            authority="system",  # Wrong authority
            epistemic_state="GROUNDED",
            system_mode="full",
        )
        # Must raise, not return False
        with pytest.raises(EnforcementViolation):
            kernel.enforce(response, context)

    def test_all_violations_inherit_from_base(self):
        """All violation types inherit from EnforcementViolation."""
        assert issubclass(AuthorityViolation, EnforcementViolation)
        assert issubclass(ContextUnavailable, EnforcementViolation)
        assert issubclass(ModeViolation, EnforcementViolation)
        assert issubclass(RefusalAuthorityViolation, EnforcementViolation)

    def test_singleton_returns_same_instance(self):
        """get_enforcement_kernel() returns singleton."""
        k1 = get_enforcement_kernel()
        k2 = get_enforcement_kernel()
        assert k1 is k2


# ─────────────────────────────────────────────
# Authority Derivation Tests
# ─────────────────────────────────────────────

class TestAuthorityDerivation:
    """Test derive_required_authority() logic."""

    def test_tool_source_derives_tool(self):
        """Any tool:* source derives tool authority."""
        context = ContextTrace(
            sources=[ContextSource(source="tool:deep_research")],
            required_but_missing=[],
            system_mode="full",
        )
        assert context.derive_required_authority() == "tool"

    def test_library_derives_memory(self):
        """Library source derives memory authority."""
        context = ContextTrace(
            sources=[ContextSource(source="library")],
            required_but_missing=[],
            system_mode="full",
        )
        assert context.derive_required_authority() == "memory"

    def test_memory_derives_memory(self):
        """Memory source derives memory authority."""
        context = ContextTrace(
            sources=[ContextSource(source="memory")],
            required_but_missing=[],
            system_mode="full",
        )
        assert context.derive_required_authority() == "memory"

    def test_system_derives_system(self):
        """System source derives system authority."""
        context = ContextTrace(
            sources=[ContextSource(source="system")],
            required_but_missing=[],
            system_mode="full",
        )
        assert context.derive_required_authority() == "system"

    def test_empty_derives_system(self):
        """Empty sources derive system authority."""
        context = ContextTrace(
            sources=[],
            required_but_missing=[],
            system_mode="full",
        )
        assert context.derive_required_authority() == "system"

    def test_tool_wins_over_memory(self):
        """Tool sources take precedence over memory."""
        context = ContextTrace(
            sources=[
                ContextSource(source="library"),
                ContextSource(source="tool:sentinel"),
                ContextSource(source="memory"),
            ],
            required_but_missing=[],
            system_mode="full",
        )
        assert context.derive_required_authority() == "tool"

    def test_memory_wins_over_system(self):
        """Memory sources take precedence over system."""
        context = ContextTrace(
            sources=[
                ContextSource(source="system"),
                ContextSource(source="library"),
            ],
            required_but_missing=[],
            system_mode="full",
        )
        assert context.derive_required_authority() == "memory"
