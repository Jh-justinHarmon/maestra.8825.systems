"""
Track 5.3 — MCP Enforcement Kill Tests

CI tests proving MCP failures CANNOT produce answers.

TEST CASES:
1. Sentinel required + Sentinel down → ContextUnavailable raised
2. Sentinel required + answer attempted → FAIL
3. Sentinel returns artifacts + authority != "tool" → FAIL
4. Sentinel partial results + authority != "tool" → FAIL
5. Sentinel empty results + answer → FAIL unless explicitly framed as negative knowledge

These tests must fail if enforcement is bypassed.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from dataclasses import dataclass
from typing import List

from enforcement_kernel import (
    EnforcementKernel,
    ContextSource,
    ContextTrace,
    ContextUnavailable,
    AuthorityViolation,
    get_enforcement_kernel,
)
from tool_assertion_classifier import (
    classify_tool_assertion,
    query_requires_sentinel,
)


# ─────────────────────────────────────────────
# Test Fixtures
# ─────────────────────────────────────────────

@dataclass
class MockResponse:
    """Mock response for enforcement testing."""
    authority: str
    system_mode: str
    epistemic_state: str


def make_context_source(source_type: str, identifier: str = None) -> ContextSource:
    """Create a ContextSource for testing."""
    return ContextSource(source=source_type, identifier=identifier)


def make_context_trace(
    sources: List[ContextSource] = None,
    required_but_missing: List[str] = None,
    system_mode: str = "full"
) -> ContextTrace:
    """Create a ContextTrace for testing."""
    return ContextTrace(
        sources=sources or [],
        required_but_missing=required_but_missing or [],
        system_mode=system_mode
    )


# ─────────────────────────────────────────────
# Test 1: Sentinel Required + Sentinel Down
# ─────────────────────────────────────────────

class TestSentinelRequiredDown:
    """Tests for when Sentinel is required but unavailable."""

    def test_sentinel_required_and_missing_raises_context_unavailable(self):
        """
        If Sentinel is required but unavailable, ContextUnavailable MUST be raised.
        No answer can be produced.
        """
        kernel = get_enforcement_kernel()
        
        # Response attempts to answer with system authority (derived from empty sources)
        response = MockResponse(
            authority="system",
            system_mode="full",
            epistemic_state="GROUNDED"
        )
        
        # Context trace shows Sentinel was required but missing
        trace = make_context_trace(
            sources=[],
            required_but_missing=["sentinel"]
        )
        
        # Enforcement MUST block this
        with pytest.raises(ContextUnavailable):
            kernel.enforce(response, trace)

    def test_sentinel_required_empty_sources_refusal_passes(self):
        """
        If query requires Sentinel and sources are empty, refusal is allowed.
        Refusals are honest about having nothing.
        """
        kernel = get_enforcement_kernel()
        
        response = MockResponse(
            authority="none",
            system_mode="full",
            epistemic_state="REFUSED"
        )
        
        trace = make_context_trace(
            sources=[],
            required_but_missing=["sentinel"]
        )
        
        # Refusals pass - they're honest about having nothing
        # The required_but_missing check only blocks GROUNDED responses
        kernel.enforce(response, trace)  # Should NOT raise


# ─────────────────────────────────────────────
# Test 2: Sentinel Required + Answer Attempted
# ─────────────────────────────────────────────

class TestSentinelRequiredAnswerAttempted:
    """Tests for when Sentinel is required but answer is attempted without it."""

    def test_answer_without_sentinel_when_required_fails(self):
        """
        If Sentinel is required but not used, answering with memory MUST fail.
        """
        kernel = get_enforcement_kernel()
        
        # Response claims memory authority without Sentinel
        response = MockResponse(
            authority="memory",
            system_mode="full",
            epistemic_state="GROUNDED"
        )
        
        # Only memory sources, but Sentinel was required
        trace = make_context_trace(
            sources=[
                make_context_source("library", "lib_001")
            ],
            required_but_missing=["sentinel"]
        )
        
        # Enforcement MUST block this
        with pytest.raises(ContextUnavailable):
            kernel.enforce(response, trace)


# ─────────────────────────────────────────────
# Test 3: Sentinel Returns Artifacts + Wrong Authority
# ─────────────────────────────────────────────

class TestSentinelArtifactsWrongAuthority:
    """Tests for authority mismatch when Sentinel provides artifacts."""

    def test_sentinel_artifacts_require_tool_authority(self):
        """
        If Sentinel returns artifacts, authority MUST be "tool".
        Claiming "memory" is an AuthorityViolation.
        """
        kernel = get_enforcement_kernel()
        
        # Response claims memory authority
        response = MockResponse(
            authority="memory",  # WRONG - should be "tool"
            system_mode="full",
            epistemic_state="GROUNDED"
        )
        
        # But sources include tool:sentinel
        trace = make_context_trace(
            sources=[
                make_context_source("tool:sentinel", "sent_001")
            ]
        )
        
        # Enforcement MUST block this
        with pytest.raises(AuthorityViolation):
            kernel.enforce(response, trace)

    def test_sentinel_artifacts_with_tool_authority_passes(self):
        """
        If Sentinel returns artifacts and authority is "tool", enforcement passes.
        """
        kernel = get_enforcement_kernel()
        
        response = MockResponse(
            authority="tool",  # CORRECT
            system_mode="full",
            epistemic_state="GROUNDED"
        )
        
        trace = make_context_trace(
            sources=[
                make_context_source("tool:sentinel", "sent_001")
            ]
        )
        
        # Should NOT raise
        kernel.enforce(response, trace)


# ─────────────────────────────────────────────
# Test 4: Sentinel Partial Results + Wrong Authority
# ─────────────────────────────────────────────

class TestSentinelPartialResults:
    """Tests for partial Sentinel results."""

    def test_partial_sentinel_results_still_require_tool_authority(self):
        """
        Even partial Sentinel results require tool authority.
        """
        kernel = get_enforcement_kernel()
        
        response = MockResponse(
            authority="memory",  # WRONG
            system_mode="full",
            epistemic_state="GROUNDED"
        )
        
        # Partial results from Sentinel
        trace = make_context_trace(
            sources=[
                make_context_source("tool:sentinel", "sent_partial")
            ]
        )
        
        with pytest.raises(AuthorityViolation):
            kernel.enforce(response, trace)

    def test_mixed_sources_tool_wins(self):
        """
        If sources include both tool and memory, authority MUST be tool.
        """
        kernel = get_enforcement_kernel()
        
        response = MockResponse(
            authority="memory",  # WRONG - tool should win
            system_mode="full",
            epistemic_state="GROUNDED"
        )
        
        trace = make_context_trace(
            sources=[
                make_context_source("library", "lib_001"),
                make_context_source("tool:sentinel", "sent_001")
            ]
        )
        
        with pytest.raises(AuthorityViolation):
            kernel.enforce(response, trace)


# ─────────────────────────────────────────────
# Test 5: Sentinel Empty Results + Answer
# ─────────────────────────────────────────────

class TestSentinelEmptyResults:
    """Tests for empty Sentinel results."""

    def test_empty_sentinel_results_cannot_claim_tool_authority(self):
        """
        If Sentinel returns no artifacts, cannot claim tool authority.
        """
        kernel = get_enforcement_kernel()
        
        response = MockResponse(
            authority="tool",  # WRONG - no tool sources
            system_mode="full",
            epistemic_state="GROUNDED"
        )
        
        trace = make_context_trace(
            sources=[]
        )
        
        with pytest.raises(AuthorityViolation):
            kernel.enforce(response, trace)

    def test_empty_results_with_memory_sources_ok(self):
        """
        If Sentinel returns nothing but library has sources, memory authority is OK.
        """
        kernel = get_enforcement_kernel()
        
        response = MockResponse(
            authority="memory",
            system_mode="full",
            epistemic_state="GROUNDED"
        )
        
        trace = make_context_trace(
            sources=[
                make_context_source("library", "lib_001")
            ]
        )
        
        # Should NOT raise
        kernel.enforce(response, trace)


# ─────────────────────────────────────────────
# Test: Query Classification Integration
# ─────────────────────────────────────────────

class TestQueryClassificationIntegration:
    """Tests for query classification triggering tool requirements."""

    def test_sentinel_assertion_detected(self):
        """Queries asserting Sentinel are detected."""
        assert query_requires_sentinel("Based on Sentinel results, what happened?")
        assert query_requires_sentinel("From Sentinel results, show me the data.")
        assert query_requires_sentinel("According to Sentinel, what was decided?")

    def test_internal_docs_assertion_detected(self):
        """Queries asserting internal documents are detected."""
        result = classify_tool_assertion("From internal documents, summarize the meeting.")
        assert result.requires_tool is True
        assert result.tool_name == "internal_documents"

    def test_normal_query_no_tool_required(self):
        """Normal queries don't require tools."""
        assert not query_requires_sentinel("What is HCSS?")
        assert not query_requires_sentinel("Explain the 8825 architecture.")


# ─────────────────────────────────────────────
# Regression: No Silent Degradation
# ─────────────────────────────────────────────

class TestNoSilentDegradation:
    """Tests ensuring no silent degradation when tools fail."""

    def test_tool_failure_cannot_silently_fallback_to_memory(self):
        """
        If a tool was required and failed, cannot silently use memory.
        """
        kernel = get_enforcement_kernel()
        
        # Attempt to answer with memory after tool failure
        response = MockResponse(
            authority="memory",
            system_mode="full",
            epistemic_state="GROUNDED"
        )
        
        # Tool was required but missing
        trace = make_context_trace(
            sources=[
                make_context_source("library", "lib_fallback")
            ],
            required_but_missing=["sentinel"]
        )
        
        # MUST raise - no silent fallback allowed
        with pytest.raises(ContextUnavailable):
            kernel.enforce(response, trace)

    def test_explicit_refusal_when_tool_unavailable_passes(self):
        """
        When tool is unavailable, refusal is the valid response.
        Refusals pass enforcement because they're honest about having nothing.
        """
        kernel = get_enforcement_kernel()
        
        response = MockResponse(
            authority="none",
            system_mode="full",
            epistemic_state="REFUSED"
        )
        
        trace = make_context_trace(
            sources=[],
            required_but_missing=["sentinel"]
        )
        
        # Refusals pass - they're honest about having nothing
        # The caller must handle the refusal appropriately
        kernel.enforce(response, trace)  # Should NOT raise
