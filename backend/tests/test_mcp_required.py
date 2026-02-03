#!/usr/bin/env python3
"""
Test REQUIRED vs OPTIONAL MCP contract enforcement.

Verifies that:
1. library_bridge absence fails startup
2. context_builder absence fails startup
3. Removing REQUIRED MCPs breaks CI
"""

import pytest
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_library_bridge_is_required():
    """Test that library_bridge is marked as REQUIRED."""
    from mcp_chain import REQUIRED_MCPS
    
    assert "library_bridge" in REQUIRED_MCPS, \
        "library_bridge must be in REQUIRED_MCPS"


def test_context_builder_is_required():
    """Test that context_builder is marked as REQUIRED."""
    from mcp_chain import REQUIRED_MCPS
    
    assert "context_builder" in REQUIRED_MCPS, \
        "context_builder must be in REQUIRED_MCPS"


def test_required_mcps_exist():
    """Test that all REQUIRED MCPs exist at expected paths."""
    from mcp_chain import validate_required_mcps
    
    # Should not raise if all REQUIRED MCPs exist
    try:
        validate_required_mcps()
    except RuntimeError as e:
        pytest.fail(f"REQUIRED MCP validation failed: {e}")


def test_missing_library_bridge_fails_startup():
    """Test that missing library_bridge causes startup failure."""
    import tempfile
    import shutil
    from unittest.mock import patch
    
    # Create temp workspace without library_bridge
    with tempfile.TemporaryDirectory() as tmpdir:
        mcp_dir = Path(tmpdir) / "mcp_servers"
        mcp_dir.mkdir()
        
        # Create context_builder but NOT library_bridge
        context_builder = mcp_dir / "context-builder"
        context_builder.mkdir()
        (context_builder / "server.js").write_text("// stub")
        
        # Mock workspace root to point to temp dir
        with patch('mcp_chain.find_workspace_root', return_value=tmpdir):
            from mcp_chain import validate_required_mcps
            
            with pytest.raises(RuntimeError, match="library_bridge"):
                validate_required_mcps()


def test_missing_context_builder_fails_startup():
    """Test that missing context_builder causes startup failure."""
    import tempfile
    from unittest.mock import patch
    
    # Create temp workspace without context_builder
    with tempfile.TemporaryDirectory() as tmpdir:
        mcp_dir = Path(tmpdir) / "mcp_servers"
        mcp_dir.mkdir()
        
        # Create library_bridge but NOT context_builder
        library_bridge = mcp_dir / "library-bridge"
        library_bridge.mkdir()
        (library_bridge / "server.js").write_text("// stub")
        
        # Mock workspace root to point to temp dir
        with patch('mcp_chain.find_workspace_root', return_value=tmpdir):
            from mcp_chain import validate_required_mcps
            
            with pytest.raises(RuntimeError, match="context_builder"):
                validate_required_mcps()


def test_optional_mcps_can_be_missing():
    """Test that OPTIONAL MCPs can be missing without failing startup."""
    import tempfile
    from unittest.mock import patch
    
    # Create temp workspace with only REQUIRED MCPs
    with tempfile.TemporaryDirectory() as tmpdir:
        mcp_dir = Path(tmpdir) / "mcp_servers"
        mcp_dir.mkdir()
        
        # Create REQUIRED MCPs
        for mcp_name in ["library-bridge", "context-builder"]:
            mcp_path = mcp_dir / mcp_name
            mcp_path.mkdir()
            (mcp_path / "server.js").write_text("// stub")
        
        # Do NOT create deep_research or project_planning (OPTIONAL)
        
        # Mock workspace root to point to temp dir
        with patch('mcp_chain.find_workspace_root', return_value=tmpdir):
            from mcp_chain import validate_required_mcps
            
            # Should not raise - OPTIONAL MCPs can be missing
            try:
                validate_required_mcps()
            except RuntimeError as e:
                pytest.fail(f"Startup failed with only REQUIRED MCPs present: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
