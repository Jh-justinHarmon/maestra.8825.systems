"""
Stub routed memory for MAESTRA_MINIMAL_MODE.

Provides minimal memory interface without requiring full system infrastructure.
Always returns empty results (no memory available).
"""
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)


class GroundingSource:
    """Minimal grounding source representation."""
    def __init__(self, title: str, confidence: float, excerpt: str = ""):
        self.title = title
        self.confidence = confidence
        self.excerpt = excerpt


def search_memory(
    session_id: str,
    query: str,
    max_entries: int = 5
) -> Tuple[List[GroundingSource], bool]:
    """
    Stub memory search - always returns empty.
    
    In minimal mode, we have no memory system.
    This ensures refusal logic fires for memory-required queries.
    
    Returns: (grounding_sources, sources_found)
    """
    logger.info(f"[STUB_MEMORY] search_memory called for query: {query[:50]}")
    logger.info(f"[STUB_MEMORY] Returning empty (minimal mode - no memory available)")
    return [], False
