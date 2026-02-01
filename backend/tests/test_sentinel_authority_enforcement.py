"""
5B.2 — Sentinel Authority Enforcement Tests

Prove enforcement works under real tool pressure.

Tests assert:
1. Sentinel context → authority MUST be "tool"
2. Sentinel missing → ContextUnavailable raised
3. Authority mismatch → AuthorityViolation raised
4. Sentinel success + wrong authority → blocked
"""

import pytest
from dataclasses import dataclass
from typing import Literal, List

from enforcement_kernel import (
    EnforcementKernel,
    ContextTrace,
    ContextSource,
    AuthorityViolation,
    ContextUnavailable,
    get_enforcement_kernel,
)
from local_sentinel_adapter import (
    LocalSentinelAdapter,
    SentinelResult,
    SentinelUnavailable,
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


@pytest.fixture
def sentinel_context_source():
    """A ContextSource from Sentinel."""
    return ContextSource(source="tool:sentinel", identifier="art_12345")


@pytest.fixture
def sentinel_result():
    """A SentinelResult for testing."""
    return SentinelResult(
        artifact_id="art_12345",
        title="HCSS Architecture Overview",
        excerpt="HCSS is a heavy civil construction software company...",
        confidence=0.85,
        source_path="/docs/hcss/architecture.md",
        artifact_type="document"
    )


# ─────────────────────────────────────────────
# Sentinel Context → Tool Authority Tests
# ─────────────────────────────────────────────

class TestSentinelRequiresToolAuthority:
    """
    Prove: Sentinel context → authority MUST be "tool"
    """

    def test_sentinel_context_requires_tool_authority(self, kernel, sentinel_context_source):
        """
        When Sentinel provides context, authority MUST be "tool".
        """
        context = ContextTrace(
            sources=[sentinel_context_source],
            required_but_missing=[],
            system_mode="local_power",
        )

        # Correct: tool authority
        response_correct = FakeResponse(
            authority="tool",
            epistemic_state="GROUNDED",
            system_mode="local_power",
        )
        
        # Should pass
        result = kernel.enforce(response_correct, context)
        assert result is None

    def test_sentinel_context_with_memory_authority_blocked(self, kernel, sentinel_context_source):
        """
        Sentinel context + memory authority → AuthorityViolation
        """
        context = ContextTrace(
            sources=[sentinel_context_source],
            required_but_missing=[],
            system_mode="local_power",
        )

        response = FakeResponse(
            authority="memory",  # ❌ WRONG
            epistemic_state="GROUNDED",
            system_mode="local_power",
        )

        with pytest.raises(AuthorityViolation):
            kernel.enforce(response, context)

    def test_sentinel_context_with_system_authority_blocked(self, kernel, sentinel_context_source):
        """
        Sentinel context + system authority → AuthorityViolation
        """
        context = ContextTrace(
            sources=[sentinel_context_source],
            required_but_missing=[],
            system_mode="local_power",
        )

        response = FakeResponse(
            authority="system",  # ❌ WRONG
            epistemic_state="GROUNDED",
            system_mode="local_power",
        )

        with pytest.raises(AuthorityViolation):
            kernel.enforce(response, context)

    def test_sentinel_context_with_none_authority_blocked(self, kernel, sentinel_context_source):
        """
        Sentinel context + none authority (non-refusal) → AuthorityViolation
        """
        context = ContextTrace(
            sources=[sentinel_context_source],
            required_but_missing=[],
            system_mode="local_power",
        )

        response = FakeResponse(
            authority="none",  # ❌ WRONG (only valid for REFUSED)
            epistemic_state="GROUNDED",
            system_mode="local_power",
        )

        with pytest.raises(AuthorityViolation):
            kernel.enforce(response, context)


# ─────────────────────────────────────────────
# Sentinel Missing → ContextUnavailable Tests
# ─────────────────────────────────────────────

class TestSentinelMissingBlocks:
    """
    Prove: Sentinel missing when required → ContextUnavailable
    """

    def test_sentinel_required_but_missing_blocks(self, kernel):
        """
        When Sentinel is required but missing, ContextUnavailable is raised.
        """
        context = ContextTrace(
            sources=[],  # No sources
            required_but_missing=["sentinel"],  # But Sentinel was required
            system_mode="local_power",
        )

        response = FakeResponse(
            authority="system",  # Correct for empty sources
            epistemic_state="GROUNDED",
            system_mode="local_power",
        )

        with pytest.raises(ContextUnavailable) as exc_info:
            kernel.enforce(response, context)
        
        assert "sentinel" in str(exc_info.value).lower()

    def test_multiple_required_sources_missing_blocks(self, kernel):
        """
        Multiple required sources missing → ContextUnavailable
        """
        context = ContextTrace(
            sources=[],
            required_but_missing=["sentinel", "deep_research"],
            system_mode="local_power",
        )

        response = FakeResponse(
            authority="system",
            epistemic_state="GROUNDED",
            system_mode="local_power",
        )

        with pytest.raises(ContextUnavailable) as exc_info:
            kernel.enforce(response, context)
        
        error_msg = str(exc_info.value).lower()
        assert "sentinel" in error_msg or "deep_research" in error_msg


# ─────────────────────────────────────────────
# Mixed Sources Tests
# ─────────────────────────────────────────────

class TestMixedSources:
    """
    Prove: Tool sources take precedence in authority derivation
    """

    def test_sentinel_plus_library_requires_tool_authority(self, kernel, sentinel_context_source):
        """
        Sentinel + library sources → tool authority required (tool wins)
        """
        context = ContextTrace(
            sources=[
                ContextSource(source="library", identifier="K-00001"),
                sentinel_context_source,  # Tool source
            ],
            required_but_missing=[],
            system_mode="local_power",
        )

        # Memory authority is wrong - tool wins
        response_wrong = FakeResponse(
            authority="memory",
            epistemic_state="GROUNDED",
            system_mode="local_power",
        )

        with pytest.raises(AuthorityViolation):
            kernel.enforce(response_wrong, context)

        # Tool authority is correct
        response_correct = FakeResponse(
            authority="tool",
            epistemic_state="GROUNDED",
            system_mode="local_power",
        )

        result = kernel.enforce(response_correct, context)
        assert result is None

    def test_sentinel_plus_system_requires_tool_authority(self, kernel, sentinel_context_source):
        """
        Sentinel + system sources → tool authority required (tool wins)
        """
        context = ContextTrace(
            sources=[
                ContextSource(source="system"),
                sentinel_context_source,
            ],
            required_but_missing=[],
            system_mode="local_power",
        )

        response = FakeResponse(
            authority="system",  # ❌ WRONG - tool wins
            epistemic_state="GROUNDED",
            system_mode="local_power",
        )

        with pytest.raises(AuthorityViolation):
            kernel.enforce(response, context)


# ─────────────────────────────────────────────
# SentinelResult → ContextSource Tests
# ─────────────────────────────────────────────

class TestSentinelResultConversion:
    """
    Prove: SentinelResult correctly converts to ContextSource
    """

    def test_sentinel_result_to_context_source(self, sentinel_result):
        """
        SentinelResult.to_context_source() returns correct type.
        """
        context_source = sentinel_result.to_context_source()
        
        assert context_source.source == "tool:sentinel"
        assert context_source.identifier == sentinel_result.artifact_id

    def test_sentinel_result_context_source_triggers_tool_authority(self, kernel, sentinel_result):
        """
        ContextSource from SentinelResult requires tool authority.
        """
        context_source = sentinel_result.to_context_source()
        
        context = ContextTrace(
            sources=[context_source],
            required_but_missing=[],
            system_mode="local_power",
        )

        # Tool authority required
        assert context.derive_required_authority() == "tool"


# ─────────────────────────────────────────────
# Local Power Mode Tests
# ─────────────────────────────────────────────

class TestLocalPowerMode:
    """
    Prove: Local Power Mode is correctly enforced
    """

    def test_local_power_mode_with_sentinel(self, kernel, sentinel_context_source):
        """
        Local power mode + Sentinel → valid configuration
        """
        context = ContextTrace(
            sources=[sentinel_context_source],
            required_but_missing=[],
            system_mode="local_power",
        )

        response = FakeResponse(
            authority="tool",
            epistemic_state="GROUNDED",
            system_mode="local_power",
        )

        # Should pass
        result = kernel.enforce(response, context)
        assert result is None

    def test_local_power_mode_mismatch_blocked(self, kernel, sentinel_context_source):
        """
        Claiming full mode when actual is local_power → ModeViolation
        """
        from enforcement_kernel import ModeViolation
        
        context = ContextTrace(
            sources=[sentinel_context_source],
            required_but_missing=[],
            system_mode="local_power",  # Actual mode
        )

        response = FakeResponse(
            authority="tool",
            epistemic_state="GROUNDED",
            system_mode="full",  # ❌ WRONG - claims full
        )

        with pytest.raises(ModeViolation):
            kernel.enforce(response, context)
