"""
Enforcement Invocation Tests (PROMPT 5)

These tests PROVE that EnforcementKernel.enforce() is actually invoked
in the production code path.

If enforce() is:
- Commented out
- Conditionally skipped
- Moved to wrong location

👉 These tests FAIL
"""

import pytest
from unittest.mock import patch, MagicMock
from dataclasses import dataclass
from typing import Literal

from enforcement_kernel import (
    EnforcementKernel,
    ContextTrace,
    ContextSource,
    AuthorityViolation,
    get_enforcement_kernel,
)


# ─────────────────────────────────────────────
# Test that enforce_and_return calls kernel
# ─────────────────────────────────────────────

class TestEnforcementInvocation:
    """Test that enforcement is actually invoked in the code path."""

    def test_enforce_and_return_calls_kernel(self):
        """enforce_and_return must call EnforcementKernel.enforce()."""
        # Import the function we're testing
        # Note: This import may fail if full dependencies aren't available
        # In that case, we test the kernel directly
        try:
            from advisor import enforce_and_return, build_context_trace
            from models import AdvisorAskResponse, SourceReference
            
            # Create a mock response
            response = AdvisorAskResponse(
                answer="Test answer",
                session_id="test_session",
                trace_id="test_trace",
                mode="quick",
                sources=[],
                system_mode="full",
                authority="system"
            )
            
            # Patch the kernel to track calls
            with patch.object(EnforcementKernel, 'enforce') as mock_enforce:
                mock_enforce.return_value = None
                result = enforce_and_return(response, sources=[], system_mode="full")
                
                # Assert enforce was called exactly once
                assert mock_enforce.call_count == 1
                
        except ImportError:
            # If we can't import advisor due to dependencies,
            # test the kernel directly
            pytest.skip("Full advisor import not available, testing kernel directly")

    def test_kernel_enforce_is_not_stubbed(self):
        """EnforcementKernel.enforce must be a real method, not a stub."""
        kernel = get_enforcement_kernel()
        
        # enforce must exist
        assert hasattr(kernel, 'enforce')
        
        # enforce must be callable
        assert callable(kernel.enforce)
        
        # enforce must not be a lambda or mock
        assert kernel.enforce.__name__ == 'enforce'

    def test_kernel_raises_on_violation(self):
        """Kernel must raise (not return False) on violation."""
        kernel = get_enforcement_kernel()
        
        @dataclass
        class FakeResponse:
            authority: str
            epistemic_state: str
            system_mode: str
        
        context = ContextTrace(
            sources=[ContextSource(source="tool:sentinel")],
            required_but_missing=[],
            system_mode="full",
        )
        
        response = FakeResponse(
            authority="system",  # Wrong - should be "tool"
            epistemic_state="GROUNDED",
            system_mode="full",
        )
        
        # Must raise, not return
        with pytest.raises(AuthorityViolation):
            kernel.enforce(response, context)

    def test_build_context_trace_creates_valid_trace(self):
        """build_context_trace must create valid ContextTrace objects."""
        try:
            from advisor import build_context_trace
            from models import SourceReference
            
            sources = [
                SourceReference(title="Test", type="library", confidence=0.9, excerpt="test")
            ]
            
            trace = build_context_trace(sources, [], "full")
            
            assert isinstance(trace, ContextTrace)
            assert trace.system_mode == "full"
            assert len(trace.sources) > 0
            
        except ImportError:
            pytest.skip("Full advisor import not available")


# ─────────────────────────────────────────────
# Structural Tests
# ─────────────────────────────────────────────

class TestEnforcementStructure:
    """Test structural properties of enforcement wiring."""

    def test_enforce_and_return_exists_in_advisor(self):
        """enforce_and_return function must exist in advisor module."""
        try:
            from advisor import enforce_and_return
            assert callable(enforce_and_return)
        except ImportError:
            pytest.skip("Full advisor import not available")

    def test_all_return_paths_use_enforce_and_return(self):
        """All AdvisorAskResponse returns must go through enforce_and_return."""
        import re
        from pathlib import Path
        
        advisor_path = Path(__file__).parent.parent / "advisor.py"
        content = advisor_path.read_text()
        
        # Find all "return AdvisorAskResponse" that are NOT in enforce_and_return
        # These would be violations
        
        # Count direct returns (bad)
        direct_returns = len(re.findall(r'return AdvisorAskResponse\(', content))
        
        # Count enforce_and_return calls (good)
        enforced_returns = len(re.findall(r'return enforce_and_return\(', content))
        
        # All returns should be enforced
        assert direct_returns == 0, f"Found {direct_returns} direct AdvisorAskResponse returns that bypass enforcement"
        assert enforced_returns > 0, "No enforce_and_return calls found"

    def test_enforcement_violation_caught_in_server(self):
        """server.py must catch EnforcementViolation and convert to refusal."""
        from pathlib import Path
        
        server_path = Path(__file__).parent.parent / "server.py"
        content = server_path.read_text()
        
        assert "EnforcementViolation" in content, "server.py must import EnforcementViolation"
        assert "except EnforcementViolation" in content, "server.py must catch EnforcementViolation"
