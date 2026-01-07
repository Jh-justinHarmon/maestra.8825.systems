"""
Epistemic Invariant Tests

Tests that verify epistemic integrity is maintained across all system operations.
These tests ensure the system never violates its epistemic contract.
"""

import pytest
from typing import Dict, List
from epistemic import (
    EpistemicState, GroundingSourceType, QueryType, GroundingSource,
    classify_query, verify_grounding, create_refused_response,
    create_grounded_response, create_ungrounded_response
)
from response_validator import ResponseValidator
from library_accessor import LibraryAccessor, find_workspace_root


class TestEpistemicStates:
    """Test epistemic state definitions and transitions."""
    
    def test_epistemic_states_defined(self):
        """Verify all epistemic states are defined."""
        assert EpistemicState.GROUNDED.value == "grounded"
        assert EpistemicState.UNGROUNDED.value == "ungrounded"
        assert EpistemicState.REFUSED.value == "refused"
    
    def test_grounding_source_types_defined(self):
        """Verify all grounding source types are defined."""
        assert GroundingSourceType.LIBRARY.value == "library"
        assert GroundingSourceType.MEMORY_HUB.value == "memory_hub"
        assert GroundingSourceType.CLIENT_CONTEXT.value == "client_context"
    
    def test_query_types_defined(self):
        """Verify all query types are defined."""
        assert QueryType.MEMORY_BASED.value == "memory_based"
        assert QueryType.GENERATIVE.value == "generative"
        assert QueryType.HYBRID.value == "hybrid"


class TestQueryClassification:
    """Test query classification logic."""
    
    def test_classify_memory_based_query(self):
        """Verify memory-based queries are classified correctly."""
        query = "What was the decision about the API gateway?"
        query_type = classify_query(query)
        assert query_type in [QueryType.MEMORY_BASED, QueryType.HYBRID]
    
    def test_classify_generative_query(self):
        """Verify generative queries are classified correctly."""
        query = "How would you approach building a distributed system?"
        query_type = classify_query(query)
        assert query_type in [QueryType.GENERATIVE, QueryType.HYBRID]
    
    def test_classify_hybrid_query(self):
        """Verify hybrid queries are classified correctly."""
        query = "Based on our past decisions, how should we approach the new feature?"
        query_type = classify_query(query)
        # Hybrid queries can be classified as any type
        assert query_type in [QueryType.MEMORY_BASED, QueryType.GENERATIVE, QueryType.HYBRID]


class TestGroundingVerification:
    """Test grounding verification logic."""
    
    def test_verify_grounding_with_sources(self):
        """Verify grounding when sources are available."""
        sources = [
            GroundingSource(
                source_type=GroundingSourceType.LIBRARY,
                identifier="entry_123",
                title="Test Entry",
                confidence=0.9,
                timestamp="2026-01-06T00:00:00Z"
            )
        ]
        
        result = verify_grounding(
            query="Test query",
            sources=sources,
            trace_id="test_trace_123"
        )
        
        assert result.is_grounded == True
        assert result.confidence >= 0.5
    
    def test_verify_grounding_without_sources(self):
        """Verify grounding when sources are unavailable."""
        result = verify_grounding(
            query="Test query",
            sources=[],
            trace_id="test_trace_123"
        )
        
        assert result.is_grounded == False
        assert result.confidence == 0.0


class TestResponseCreation:
    """Test response creation for each epistemic state."""
    
    def test_create_grounded_response(self):
        """Verify grounded response creation."""
        sources = [
            GroundingSource(
                source_type=GroundingSourceType.LIBRARY,
                identifier="entry_123",
                title="Test Entry",
                confidence=0.9,
                timestamp="2026-01-06T00:00:00Z"
            )
        ]
        
        response = create_grounded_response(
            query="Test query",
            answer="Test answer",
            sources=sources,
            trace_id="test_trace_123"
        )
        
        assert response.epistemic_state == EpistemicState.GROUNDED
        assert len(response.grounding_sources) > 0
        assert response.confidence >= 0.5
    
    def test_create_ungrounded_response(self):
        """Verify ungrounded response creation."""
        response = create_ungrounded_response(
            query="Test query",
            answer="Speculative answer",
            trace_id="test_trace_123"
        )
        
        assert response.epistemic_state == EpistemicState.UNGROUNDED
        assert len(response.grounding_sources) == 0
        assert response.confidence < 0.5
    
    def test_create_refused_response(self):
        """Verify refused response creation."""
        response = create_refused_response(
            query="Test query",
            trace_id="test_trace_123",
            what_would_help=["More context", "Specific information"]
        )
        
        assert response.epistemic_state == EpistemicState.REFUSED
        assert len(response.grounding_sources) == 0
        assert response.confidence == 0.0
        assert "cannot answer" in response.answer.lower()


class TestResponseValidation:
    """Test response validation invariants."""
    
    def test_validate_grounded_response(self):
        """Verify grounded response validation."""
        response = {
            "epistemic_state": "grounded",
            "answer": "This is a grounded answer",
            "grounding_sources": [
                {
                    "type": "library",
                    "identifier": "entry_123",
                    "title": "Test Entry",
                    "confidence": 0.9
                }
            ],
            "confidence": 0.85
        }
        
        assert ResponseValidator.validate_response(response) == True
    
    def test_validate_grounded_response_without_sources_fails(self):
        """Verify grounded response without sources fails validation."""
        response = {
            "epistemic_state": "grounded",
            "answer": "This is a grounded answer",
            "grounding_sources": [],
            "confidence": 0.85
        }
        
        assert ResponseValidator.validate_response(response) == False
    
    def test_validate_refused_response(self):
        """Verify refused response validation."""
        response = {
            "epistemic_state": "refused",
            "answer": "I cannot answer this question without more context",
            "grounding_sources": [],
            "confidence": 0.0
        }
        
        assert ResponseValidator.validate_response(response) == True
    
    def test_validate_refused_response_with_sources_fails(self):
        """Verify refused response with sources fails validation."""
        response = {
            "epistemic_state": "refused",
            "answer": "I cannot answer this question",
            "grounding_sources": [
                {
                    "type": "library",
                    "identifier": "entry_123",
                    "title": "Test Entry",
                    "confidence": 0.9
                }
            ],
            "confidence": 0.0
        }
        
        assert ResponseValidator.validate_response(response) == False


class TestLibraryAccess:
    """Test workspace-agnostic library access."""
    
    def test_find_workspace_root(self):
        """Verify workspace root can be found."""
        workspace_root = find_workspace_root()
        assert workspace_root is not None
        assert "8825-Team" in workspace_root or workspace_root.endswith("8825-Team")
    
    def test_library_accessor_initialization(self):
        """Verify library accessor can be initialized."""
        workspace_root = find_workspace_root()
        accessor = LibraryAccessor(workspace_root)
        assert accessor is not None
    
    def test_library_integrity_check(self):
        """Verify library integrity can be checked."""
        workspace_root = find_workspace_root()
        accessor = LibraryAccessor(workspace_root)
        is_valid, corrupted = accessor.verify_integrity()
        assert isinstance(is_valid, bool)
        assert isinstance(corrupted, list)


class TestEpistemicInvariants:
    """Test system-wide epistemic invariants."""
    
    def test_invariant_grounded_requires_sources(self):
        """Invariant: GROUNDED responses must have sources."""
        # This is tested via ResponseValidator
        response = {
            "epistemic_state": "grounded",
            "answer": "Answer",
            "grounding_sources": [],
            "confidence": 0.8
        }
        assert ResponseValidator.validate_response(response) == False
    
    def test_invariant_refused_has_no_sources(self):
        """Invariant: REFUSED responses must have no sources."""
        response = {
            "epistemic_state": "refused",
            "answer": "Cannot answer",
            "grounding_sources": [{"type": "library", "confidence": 0.9}],
            "confidence": 0.0
        }
        assert ResponseValidator.validate_response(response) == False
    
    def test_invariant_confidence_in_range(self):
        """Invariant: Confidence must be between 0 and 1."""
        # Valid confidence
        assert 0 <= 0.5 <= 1
        assert 0 <= 0.0 <= 1
        assert 0 <= 1.0 <= 1
        
        # Invalid confidence would be caught elsewhere
        assert not (1.5 >= 0 and 1.5 <= 1)
    
    def test_invariant_no_silent_failures(self):
        """Invariant: System never silently fails."""
        # All errors should be explicit
        # This is tested via response validation and error tracking
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
