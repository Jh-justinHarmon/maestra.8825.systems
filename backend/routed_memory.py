"""
Router-Enforced Memory Access for Maestra Backend

This module replaces direct LibraryAccessor usage with router-enforced
memory access via the Context Router.

CRITICAL: Maestra consumes router state, it never creates or mutates it.
Sessions must be initialized externally before Maestra can read memory.

Usage:
    from routed_memory import (
        initialize_session,
        search_memory,
        get_session_router_state
    )
    
    # At session start (called by session manager, not Maestra)
    initialize_session(session_id)
    
    # During response generation
    results = search_memory(session_id, query)
"""

import sys
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Add routing module to path
ROUTING_PATH = Path(__file__).parent.parent.parent.parent / "system" / "routing"
sys.path.insert(0, str(ROUTING_PATH))

from context_router import (
    ContextRouterState,
    RouterMode,
    RouterIssuer,
    create_session,
    get_context_router,
    set_context_router,
    elevate_to_personal,
    revoke_personal,
    RouterMissingError,
    RouterSecurityError
)
from memory_gate import MemoryGate, get_memory_gate
from maestra_memory import MaestraMemory, MaestraMemoryError

# Also import epistemic types for grounding sources
from epistemic import GroundingSource, GroundingSourceType

logger = logging.getLogger(__name__)


# =============================================================================
# SESSION INITIALIZATION (Called by session manager, NOT by Maestra)
# =============================================================================

def initialize_session(session_id: str) -> ContextRouterState:
    """
    Initialize a session with default system-only router.
    
    This MUST be called before Maestra can access memory for this session.
    Typically called by session manager at session creation.
    
    Returns the created router state.
    """
    router = create_session(session_id)
    logger.info(f"Session initialized: {session_id} [mode={router.mode.value}]")
    return router


def ensure_session_initialized(session_id: str) -> ContextRouterState:
    """
    Ensure session has a router, creating one if needed.
    
    This is a safety fallback - sessions SHOULD be explicitly initialized.
    """
    router = get_context_router(session_id)
    if router is None:
        logger.warning(f"Session {session_id} had no router, initializing default")
        router = initialize_session(session_id)
    return router


# =============================================================================
# MEMORY SEARCH (Router-Enforced)
# =============================================================================

def search_memory(
    session_id: str,
    query: str,
    max_entries: int = 5
) -> Tuple[List[GroundingSource], bool]:
    """
    Search memory with router enforcement.
    
    This replaces the old search_8825_library() function.
    Returns: (grounding_sources, sources_found)
    
    IMPORTANT: Will crash if session has no router (as intended).
    """
    # Ensure session is initialized (safety fallback)
    router = ensure_session_initialized(session_id)
    
    # CRITICAL: Log router state for debugging
    logger.critical(f"🔴 ROUTER_STATE | session_id={session_id} | mode={router.mode.value} | authenticated={router.authenticated} | personal_enabled={router.is_personal_enabled()} | personal_scope={'exists' if router.personal_scope else 'MISSING'}")
    
    # Use MaestraMemory interface (enforces router)
    memory = MaestraMemory(session_id)
    
    try:
        context = memory.get_context(query, max_results=max_entries)
        
        if not context["entries"]:
            logger.info(f"Memory search found no entries for: {query[:50]}")
            return [], False
        
        # Convert to GroundingSource objects
        sources = []
        for entry in context["entries"]:
            source = GroundingSource(
                source_type=GroundingSourceType.LIBRARY,
                identifier=entry["id"],
                title=entry.get("context", ""),  # context field has title
                confidence=entry.get("confidence", 0.7),
                excerpt=entry["content"][:200] if entry.get("content") else None,
                timestamp=entry.get("created_at")
            )
            sources.append(source)
        
        logger.info(
            f"Memory search found {len(sources)} entries for: {query[:50]} "
            f"[mode={context['mode']}, sources={context['sources']}]"
        )
        return sources, True
    
    except RouterMissingError as e:
        logger.error(f"Router missing for session {session_id}: {e}")
        raise
    except MaestraMemoryError as e:
        logger.error(f"Maestra memory error: {e}")
        raise
    except Exception as e:
        logger.error(f"Memory search error: {e}")
        return [], False


def get_session_router_state(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Get current router state for a session (read-only).
    
    Returns None if session has no router.
    """
    router = get_context_router(session_id)
    if router is None:
        return None
    return router.to_dict()


def is_personal_enabled(session_id: str) -> bool:
    """Check if personal memory is enabled for this session."""
    router = get_context_router(session_id)
    if router is None:
        return False
    return router.is_personal_enabled()


# =============================================================================
# PERSONAL ACCESS ELEVATION (Called by quadcore/user, NOT by Maestra)
# =============================================================================

def enable_personal_access(
    session_id: str,
    owner_id: str,
    libraries: List[str],
    ttl_minutes: int = 30,
    issued_by: str = "quadcore"
) -> ContextRouterState:
    """
    Elevate session to personal memory access.
    
    This is NOT called by Maestra - only by quadcore or user.
    
    Args:
        session_id: Session to elevate
        owner_id: Whose personal memory (e.g., "jh")
        libraries: Whitelist of libraries to access
        ttl_minutes: Time until auto-revoke
        issued_by: "quadcore" or "user"
    """
    issuer = RouterIssuer.QUADCORE if issued_by == "quadcore" else RouterIssuer.USER
    
    router = elevate_to_personal(
        session_id=session_id,
        owner_id=owner_id,
        libraries=libraries,
        ttl_minutes=ttl_minutes,
        issued_by=issuer
    )
    
    logger.info(
        f"Personal access enabled: {session_id} -> {owner_id} "
        f"[libraries={libraries}, ttl={ttl_minutes}min, by={issued_by}]"
    )
    return router


def disable_personal_access(session_id: str) -> ContextRouterState:
    """
    Revoke personal access, revert to system-only.
    
    This can be called by anyone - it's always safe.
    """
    router = revoke_personal(session_id)
    logger.info(f"Personal access revoked: {session_id}")
    return router


# =============================================================================
# BACKWARD COMPATIBILITY (Transitional)
# =============================================================================

def search_8825_library_routed(
    query: str,
    session_id: str,
    max_entries: int = 5
) -> Tuple[List[GroundingSource], bool]:
    """
    Drop-in replacement for search_8825_library() that uses router.
    
    This maintains the same signature for easy migration.
    """
    return search_memory(session_id, query, max_entries)
