"""
TRACK 1 STEP 2: Boot Contract Test (No Silent Success)

This test ensures:
1. The server module can be imported without crashing
2. Uvicorn import graph is valid
3. No "it deploys but crashes later" bullshit

If any startup validation fails → CI fails.
"""
import os
import sys
from pathlib import Path


def test_server_import_succeeds():
    """Server module must import without errors in full mode"""
    # Ensure full mode
    os.environ["MAESTRA_MINIMAL_MODE"] = "false"
    
    # Add paths for imports
    backend_dir = Path(__file__).parent.parent
    system_dir = backend_dir.parent.parent.parent / "system"
    
    sys.path.insert(0, str(backend_dir))
    sys.path.insert(0, str(system_dir))
    sys.path.insert(0, str(system_dir / "agents"))
    
    try:
        # This triggers the full import chain including validation
        import server
        assert hasattr(server, 'app'), "❌ server.app not found"
    except Exception as e:
        raise AssertionError(f"❌ Boot contract failed - server import error:\n{e}")


def test_advisor_import_succeeds():
    """Advisor module must import without errors in full mode"""
    os.environ["MAESTRA_MINIMAL_MODE"] = "false"
    
    backend_dir = Path(__file__).parent.parent
    system_dir = backend_dir.parent.parent.parent / "system"
    
    sys.path.insert(0, str(backend_dir))
    sys.path.insert(0, str(system_dir))
    sys.path.insert(0, str(system_dir / "agents"))
    
    try:
        import advisor
        assert hasattr(advisor, 'ask_advisor'), "❌ advisor.ask_advisor not found"
    except Exception as e:
        raise AssertionError(f"❌ Boot contract failed - advisor import error:\n{e}")
