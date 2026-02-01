"""
HR-1 and HR-3 Tests — Refusal Normalization and Dogfooding Regression

These tests ensure:
1. Soft refusals become hard refusals (authority="none", epistemic_state="REFUSED")
2. Grounded answers are NOT downgraded
3. DF-5 and DF-6 failures are locked as regression tests
"""

import pytest
from refusal_normalizer import (
    detect_soft_refusal,
    normalize_refusal,
    should_normalize_to_refusal,
    NormalizationResult,
)
from tool_assertion_classifier import (
    classify_tool_assertion,
    get_required_tools,
    query_requires_sentinel,
    ToolAssertionResult,
)


# ─────────────────────────────────────────────
# HR-1: Soft Refusal Detection Tests
# ─────────────────────────────────────────────

class TestSoftRefusalDetection:
    """Test soft refusal pattern detection."""

    def test_detects_dont_have_access(self):
        answer = "I don't have access to internal emails about Project X."
        is_soft, pattern = detect_soft_refusal(answer)
        assert is_soft is True
        assert pattern is not None

    def test_detects_do_not_have_access(self):
        answer = "I do not have access to that information."
        is_soft, pattern = detect_soft_refusal(answer)
        assert is_soft is True

    def test_detects_cannot_determine(self):
        answer = "I cannot determine the answer from available sources."
        is_soft, pattern = detect_soft_refusal(answer)
        assert is_soft is True

    def test_detects_not_available(self):
        answer = "That information is not available in the library."
        is_soft, pattern = detect_soft_refusal(answer)
        assert is_soft is True

    def test_detects_unable_to_find(self):
        answer = "I was unable to find any documents about that topic."
        is_soft, pattern = detect_soft_refusal(answer)
        assert is_soft is True

    def test_detects_no_information_about(self):
        answer = "There is no information about Project X in the sources."
        is_soft, pattern = detect_soft_refusal(answer)
        assert is_soft is True

    def test_detects_currently_do_not_have(self):
        answer = "I currently do not have access to specific internal emails."
        is_soft, pattern = detect_soft_refusal(answer)
        assert is_soft is True

    def test_detects_does_not_provide_specific(self):
        answer = "The context does not provide specific details about that."
        is_soft, pattern = detect_soft_refusal(answer)
        assert is_soft is True

    def test_does_not_detect_normal_answer(self):
        answer = "HCSS is a consulting company founded by Becky Hammer."
        is_soft, pattern = detect_soft_refusal(answer)
        assert is_soft is False
        assert pattern is None

    def test_does_not_detect_partial_match(self):
        answer = "The system provides access to many documents."
        is_soft, pattern = detect_soft_refusal(answer)
        assert is_soft is False


# ─────────────────────────────────────────────
# HR-1: Refusal Normalization Tests
# ─────────────────────────────────────────────

class TestRefusalNormalization:
    """Test refusal normalization logic."""

    def test_soft_refusal_becomes_hard_refusal(self):
        """Core HR-1 test: soft refusal → hard refusal."""
        answer = "I don't have access to internal emails about Project X."
        sources = []

        result = normalize_refusal(
            answer=answer,
            sources=sources,
            authority="memory",
            epistemic_state="GROUNDED",
            tool_context_used=False
        )

        assert result.is_soft_refusal is True
        assert result.normalized_authority == "none"
        assert result.normalized_epistemic_state == "REFUSED"

    def test_soft_refusal_adds_retry_guidance(self):
        """Normalized refusals include retry guidance."""
        answer = "I cannot find that information."
        sources = []

        result = normalize_refusal(
            answer=answer,
            sources=sources,
            authority="memory",
            epistemic_state="GROUNDED",
            tool_context_used=False
        )

        assert "what would help" in result.normalized_answer.lower()

    def test_grounded_answer_not_downgraded(self):
        """Answers with sources are NOT downgraded."""
        answer = "Based on the documents, I don't have access to emails but here's what I found..."
        sources = [{"title": "Doc1", "type": "library"}]

        result = normalize_refusal(
            answer=answer,
            sources=sources,
            authority="memory",
            epistemic_state="GROUNDED",
            tool_context_used=False
        )

        # Should NOT be normalized because it has sources
        assert result.normalized_authority == "memory"
        assert result.normalized_epistemic_state == "GROUNDED"

    def test_tool_context_prevents_normalization(self):
        """Answers with tool context are NOT downgraded."""
        answer = "I don't have access to all files, but Sentinel found..."
        sources = []

        result = normalize_refusal(
            answer=answer,
            sources=sources,
            authority="tool",
            epistemic_state="GROUNDED",
            tool_context_used=True
        )

        # Should NOT be normalized because tool context was used
        assert result.normalized_authority == "tool"

    def test_normal_answer_unchanged(self):
        """Normal answers pass through unchanged."""
        answer = "HCSS is a consulting company."
        sources = [{"title": "About HCSS", "type": "library"}]

        result = normalize_refusal(
            answer=answer,
            sources=sources,
            authority="memory",
            epistemic_state="GROUNDED",
            tool_context_used=False
        )

        assert result.is_soft_refusal is False
        assert result.normalized_authority == "memory"
        assert result.normalized_answer == answer


# ─────────────────────────────────────────────
# HR-2: Tool Assertion Classification Tests
# ─────────────────────────────────────────────

class TestToolAssertionClassification:
    """Test tool assertion detection."""

    def test_based_on_sentinel_requires_tool(self):
        """'Based on Sentinel' requires Sentinel tool."""
        query = "Based on Sentinel results, what did we decide about RAL?"
        result = classify_tool_assertion(query)

        assert result.requires_tool is True
        assert result.required is True
        assert result.tool_name == "sentinel"

    def test_from_sentinel_results_requires_tool(self):
        query = "From Sentinel results, summarize Project X."
        result = classify_tool_assertion(query)

        assert result.requires_tool is True
        assert result.tool_name == "sentinel"

    def test_according_to_sentinel_requires_tool(self):
        query = "According to Sentinel, what is the architecture?"
        result = classify_tool_assertion(query)

        assert result.requires_tool is True
        assert result.tool_name == "sentinel"

    def test_from_internal_documents_requires_tool(self):
        query = "From internal documents, what was decided?"
        result = classify_tool_assertion(query)

        assert result.requires_tool is True
        assert result.tool_name == "internal_documents"

    def test_from_internal_emails_requires_tool(self):
        query = "From internal emails, summarize the discussion."
        result = classify_tool_assertion(query)

        assert result.requires_tool is True
        assert result.tool_name == "internal_documents"

    def test_normal_query_no_tool_required(self):
        query = "What is HCSS?"
        result = classify_tool_assertion(query)

        assert result.requires_tool is False
        assert result.tool_name is None

    def test_get_required_tools_sentinel(self):
        query = "Based on Sentinel, what did we decide?"
        tools = get_required_tools(query)

        assert "sentinel" in tools

    def test_query_requires_sentinel_true(self):
        query = "From Sentinel results, show me the data."
        assert query_requires_sentinel(query) is True

    def test_query_requires_sentinel_false(self):
        query = "What is the 8825 architecture?"
        assert query_requires_sentinel(query) is False


# ─────────────────────────────────────────────
# HR-3: Dogfooding Regression Tests
# ─────────────────────────────────────────────

class TestDogfoodingRegressions:
    """
    Regression tests for dogfooding failures.
    These tests replay exact failure scenarios.
    """

    def test_df5_internal_emails_refusal(self):
        """
        DF-5 Regression: "Summarize internal emails about Project X from 2021"
        
        This query should result in a hard refusal because:
        1. No such emails exist in the library
        2. Sentinel is unavailable
        3. The answer would be a soft refusal
        
        Expected: authority="none", epistemic_state="REFUSED"
        """
        answer = "I currently do not have access to specific internal emails about Project X from 2021."
        sources = []

        result = normalize_refusal(
            answer=answer,
            sources=sources,
            authority="memory",
            epistemic_state="GROUNDED",
            tool_context_used=False
        )

        assert result.normalized_authority == "none"
        assert result.normalized_epistemic_state == "REFUSED"

    def test_df6_sentinel_assertion_requires_tool(self):
        """
        DF-6 Regression: "Based on Sentinel results, what did we decide about RAL?"
        
        This query explicitly asserts Sentinel provenance.
        If Sentinel is unavailable, it MUST refuse.
        
        Expected: requires_tool=True, tool_name="sentinel"
        """
        query = "Based on Sentinel results, what did we decide about RAL?"
        result = classify_tool_assertion(query)

        assert result.requires_tool is True
        assert result.required is True
        assert result.tool_name == "sentinel"

    def test_df6_sentinel_assertion_internal_docs(self):
        """
        DF-6 Variant: "From internal documents, what was the decision?"
        
        Internal documents = Sentinel requirement.
        """
        query = "From internal documents, what was the decision about HCSS?"
        result = classify_tool_assertion(query)

        assert result.requires_tool is True
        assert result.tool_name == "internal_documents"

    def test_df2_hcss_decisions_soft_refusal(self):
        """
        DF-2 Regression: "What decisions were made about HCSS client work in late 2023?"
        
        If the answer is "sources do not provide specific details",
        this should become a hard refusal.
        """
        answer = "The available sources do not provide specific details about decisions made regarding HCSS client work in late 2023."
        sources = []  # Simulating no useful sources

        result = normalize_refusal(
            answer=answer,
            sources=sources,
            authority="memory",
            epistemic_state="GROUNDED",
            tool_context_used=False
        )

        assert result.normalized_authority == "none"
        assert result.normalized_epistemic_state == "REFUSED"
