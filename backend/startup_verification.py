"""
Startup Invariants - System Integrity Verification

Verifies system is in valid state before accepting requests.
Crashes on missing dependencies (production) or warns loudly (development).
"""

import os
import sys
import logging
from typing import List, Tuple
from library_accessor import LibraryAccessor, find_workspace_root
from epistemic import StartupInvariant

logger = logging.getLogger(__name__)


class StartupVerification:
    """Comprehensive startup verification for Maestra backend."""
    
    def __init__(self, production_mode: bool = False):
        """
        Initialize startup verification.
        
        Args:
            production_mode: If True, crash on failures. If False, warn only.
        """
        self.production_mode = production_mode
        self.failures: List[str] = []
        self.warnings: List[str] = []
    
    def verify_all(self) -> bool:
        """
        Run all startup invariants.
        
        Returns:
            True if all critical checks pass, False otherwise
        """
        logger.info("=" * 60)
        logger.info("MAESTRA STARTUP VERIFICATION")
        logger.info("=" * 60)
        
        # Run all checks
        self._verify_workspace()
        self._verify_library_access()
        self._verify_session_management()
        self._verify_critical_mcps()
        self._verify_authentication()
        
        # Report results
        return self._report_results()
    
    def _verify_workspace(self) -> None:
        """Verify workspace is accessible."""
        logger.info("\n[1/5] Verifying workspace...")
        
        try:
            workspace_root = find_workspace_root()
            logger.info(f"  ✓ Workspace found: {workspace_root}")
            
            # Verify key directories exist
            required_dirs = [
                "shared/8825-library",
                "ucma/extracted_knowledge",
                "apps/maestra.8825.systems/backend"
            ]
            
            for dir_name in required_dirs:
                dir_path = os.path.join(workspace_root, dir_name)
                if os.path.exists(dir_path):
                    logger.info(f"  ✓ {dir_name} exists")
                else:
                    self.failures.append(f"Directory missing: {dir_name}")
                    logger.error(f"  ✗ {dir_name} missing")
        
        except Exception as e:
            self.failures.append(f"Workspace verification failed: {e}")
            logger.error(f"  ✗ Workspace verification failed: {e}")
    
    def _verify_library_access(self) -> None:
        """Verify library is accessible and valid."""
        logger.info("\n[2/5] Verifying library access...")
        
        try:
            workspace_root = find_workspace_root()
            library = LibraryAccessor(workspace_root)
            
            # Check library integrity
            is_valid, corrupted = library.verify_integrity()
            
            if is_valid:
                entry_count = library.get_entry_count()
                logger.info(f"  ✓ Library valid with {entry_count} entries")
            else:
                self.failures.append(f"Library has {len(corrupted)} corrupted files")
                logger.error(f"  ✗ Library corrupted: {len(corrupted)} files")
                for file in corrupted[:3]:  # Show first 3
                    logger.error(f"    - {file}")
        
        except Exception as e:
            self.failures.append(f"Library access failed: {e}")
            logger.error(f"  ✗ Library access failed: {e}")
    
    def _verify_session_management(self) -> None:
        """Verify session management is operational."""
        logger.info("\n[3/5] Verifying session management...")
        
        try:
            # Check if session manager can be imported
            from session_manager import SessionManager
            
            session_mgr = SessionManager()
            logger.info("  ✓ Session manager initialized")
            
            # Verify in-memory storage is working
            test_session_id = "startup_test_session"
            session_mgr.register_session(
                session_id=test_session_id,
                user_id="test_user",
                capabilities=["library", "context_builder"]
            )
            
            if session_mgr.has_session(test_session_id):
                logger.info("  ✓ Session storage working")
                session_mgr.remove_session(test_session_id)
            else:
                self.failures.append("Session storage not working")
                logger.error("  ✗ Session storage not working")
        
        except ImportError:
            self.warnings.append("Session manager not available (optional)")
            logger.warning("  ⚠ Session manager not available")
        except Exception as e:
            self.failures.append(f"Session management failed: {e}")
            logger.error(f"  ✗ Session management failed: {e}")
    
    def _verify_critical_mcps(self) -> None:
        """Verify critical MCPs are reachable."""
        logger.info("\n[4/5] Verifying critical MCPs...")
        
        critical_mcps = {
            "context_builder": "http://localhost:3000/health",
            "library_bridge": "http://localhost:3001/health",
        }
        
        reachable_count = 0
        
        for mcp_name, endpoint in critical_mcps.items():
            try:
                import subprocess
                result = subprocess.run(
                    ["curl", "-s", endpoint],
                    capture_output=True,
                    timeout=2
                )
                
                if result.returncode == 0:
                    logger.info(f"  ✓ {mcp_name} reachable")
                    reachable_count += 1
                else:
                    self.warnings.append(f"{mcp_name} not responding")
                    logger.warning(f"  ⚠ {mcp_name} not responding")
            
            except Exception as e:
                self.warnings.append(f"{mcp_name} unreachable: {e}")
                logger.warning(f"  ⚠ {mcp_name} unreachable")
        
        if reachable_count == 0 and self.production_mode:
            self.failures.append("No critical MCPs reachable")
            logger.error("  ✗ No critical MCPs reachable")
    
    def _verify_authentication(self) -> None:
        """Verify authentication system is operational."""
        logger.info("\n[5/5] Verifying authentication...")
        
        try:
            # Check if quad-core delegation is available
            from quad_core_delegation import get_router
            
            router = get_router()
            
            if router.__class__.__name__ == "QuadCoreCapabilityRouter":
                logger.info("  ✓ Quad-core capability delegation available")
            else:
                logger.warning("  ⚠ Using degraded mode (direct file access)")
                self.warnings.append("Quad-core sidecar unavailable, using degraded mode")
        
        except Exception as e:
            self.failures.append(f"Authentication verification failed: {e}")
            logger.error(f"  ✗ Authentication verification failed: {e}")
    
    def _report_results(self) -> bool:
        """Report verification results and determine if startup should proceed."""
        logger.info("\n" + "=" * 60)
        logger.info("VERIFICATION RESULTS")
        logger.info("=" * 60)
        
        if self.failures:
            logger.error(f"\n❌ CRITICAL FAILURES ({len(self.failures)}):")
            for failure in self.failures:
                logger.error(f"  - {failure}")
        
        if self.warnings:
            logger.warning(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                logger.warning(f"  - {warning}")
        
        if not self.failures:
            logger.info("\n✅ All critical checks passed")
            logger.info("=" * 60)
            return True
        else:
            if self.production_mode:
                logger.error("\n🛑 STARTUP FAILED - Production mode requires all checks to pass")
                logger.error("=" * 60)
                return False
            else:
                logger.warning("\n⚠️  STARTUP PROCEEDING - Development mode allows failures")
                logger.warning("=" * 60)
                return True


def verify_startup(production_mode: bool = False) -> bool:
    """
    Run startup verification.
    
    Args:
        production_mode: If True, crash on failures. If False, warn only.
    
    Returns:
        True if startup should proceed, False otherwise
    """
    verifier = StartupVerification(production_mode=production_mode)
    return verifier.verify_all()


def crash_if_startup_fails(production_mode: bool = False) -> None:
    """
    Run startup verification and crash if it fails (production mode).
    
    Args:
        production_mode: If True, crash on failures
    """
    if not verify_startup(production_mode=production_mode):
        if production_mode:
            logger.error("\n🛑 STARTUP FAILED - Exiting")
            sys.exit(1)
