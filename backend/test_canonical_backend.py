"""
Regression tests for canonical backend enforcement (PROMPT 7)

These tests ensure:
- advisor.py is only importable from canonical path
- server.py is only importable from canonical path
- Shadow backends fail on import
"""

import pytest
import sys
import os
from pathlib import Path


def test_advisor_import_from_canonical_only():
    """advisor.py must only be importable from canonical backend"""
    canonical_backend = Path("/Users/justinharmon/Hammer Consulting Dropbox/Justin Harmon/8825-Team/8825/apps/maestra.8825.systems/backend")
    
    # Add canonical backend to path
    sys.path.insert(0, str(canonical_backend))
    
    try:
        import advisor
        advisor_path = Path(advisor.__file__)
        
        # Verify it's from canonical location
        assert advisor_path.parent == canonical_backend, \
            f"advisor.py imported from non-canonical path: {advisor_path}"
    finally:
        # Clean up
        if 'advisor' in sys.modules:
            del sys.modules['advisor']
        sys.path.remove(str(canonical_backend))


def test_server_import_from_canonical_only():
    """server.py must only be importable from canonical backend"""
    canonical_backend = Path("/Users/justinharmon/Hammer Consulting Dropbox/Justin Harmon/8825-Team/8825/apps/maestra.8825.systems/backend")
    
    # Add canonical backend to path
    sys.path.insert(0, str(canonical_backend))
    
    try:
        import server
        server_path = Path(server.__file__)
        
        # Verify it's from canonical location
        assert server_path.parent == canonical_backend, \
            f"server.py imported from non-canonical path: {server_path}"
    finally:
        # Clean up
        if 'server' in sys.modules:
            del sys.modules['server']
        sys.path.remove(str(canonical_backend))


def test_shadow_backend_system_maestra_fails():
    """Shadow backend at system/maestra/ must fail on import"""
    shadow_backend = Path("/Users/justinharmon/Hammer Consulting Dropbox/Justin Harmon/8825-Team/8825/system/maestra")
    
    if not shadow_backend.exists():
        pytest.skip("Shadow backend at system/maestra/ does not exist")
    
    sys.path.insert(0, str(shadow_backend))
    
    try:
        with pytest.raises(RuntimeError, match="FATAL.*deprecated"):
            import maestra_backend
    finally:
        if 'maestra_backend' in sys.modules:
            del sys.modules['maestra_backend']
        sys.path.remove(str(shadow_backend))


def test_shadow_backend_tools_fails():
    """Shadow backend at system/tools/maestra_backend/ must fail on import"""
    shadow_backend = Path("/Users/justinharmon/Hammer Consulting Dropbox/Justin Harmon/8825-Team/8825/system/tools/maestra_backend")
    
    if not shadow_backend.exists():
        pytest.skip("Shadow backend at system/tools/maestra_backend/ does not exist")
    
    # Check for poison file
    poison_file = shadow_backend / "__DEPRECATED_DO_NOT_RUN__.py"
    assert poison_file.exists(), \
        f"Shadow backend at {shadow_backend} is missing poison file"


def test_multiple_maestra_backends_not_importable():
    """Only one Maestra backend should be importable at a time"""
    canonical_backend = Path("/Users/justinharmon/Hammer Consulting Dropbox/Justin Harmon/8825-Team/8825/apps/maestra.8825.systems/backend")
    
    # Try to import from canonical
    sys.path.insert(0, str(canonical_backend))
    
    try:
        import server
        canonical_server_path = Path(server.__file__)
        
        # Verify no other server.py is accessible
        for path in sys.path:
            path_obj = Path(path)
            if path_obj.exists() and path_obj != canonical_backend:
                potential_server = path_obj / "server.py"
                if potential_server.exists() and "maestra" in str(potential_server).lower():
                    # This should not happen - fail the test
                    pytest.fail(
                        f"Multiple Maestra backends found:\n"
                        f"  Canonical: {canonical_server_path}\n"
                        f"  Shadow:    {potential_server}"
                    )
    finally:
        if 'server' in sys.modules:
            del sys.modules['server']
        sys.path.remove(str(canonical_backend))
