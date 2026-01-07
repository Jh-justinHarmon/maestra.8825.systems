"""
Maestra Backend - Context Logic

Handles /context/{session_id} endpoint logic.
Retrieves session context from Memory Hub or session continuity.
"""
import os
import sys
import logging
import time
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime
import subprocess
import json

# Add parent paths for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import ContextSummaryResponse
from epistemic import GroundingSource, GroundingSourceType

logger = logging.getLogger(__name__)

# Memory Hub endpoint
MEMORY_HUB_URL = os.getenv("MEMORY_HUB_URL", "http://localhost:5070")


async def get_memory_context(session_id: str, focus: list = None) -> Tuple[Dict[str, Any], List[GroundingSource], bool]:
    """
    Get context from Memory Hub for a session.
    
    Returns: (context_data, grounding_sources, sources_found)
    - context_data: Dictionary with recent_decisions, open_loops, etc.
    - grounding_sources: List of GroundingSource objects
    - sources_found: True if any sources were found, False if empty
    """
    if focus is None:
        focus = ["recent_decisions", "open_loops", "recent_knowledge"]
    
    logger.info(f"Requesting context from Memory Hub for session {session_id}")
    
    try:
        # Try to call Memory Hub MCP
        result = subprocess.run(
            [
                "curl", "-X", "POST",
                f"{MEMORY_HUB_URL}/context/get",
                "-H", "Content-Type: application/json",
                "-d", json.dumps({
                    "session_id": session_id,
                    "focus": focus
                })
            ],
            capture_output=True,
            timeout=5,
            text=True
        )
        
        if result.returncode == 0:
            try:
                response = json.loads(result.stdout)
                
                # Convert to grounding sources
                sources = []
                if response.get("success"):
                    source = GroundingSource(
                        source_type=GroundingSourceType.MEMORY_HUB,
                        identifier=f"memory_hub_{session_id}",
                        title="Memory Hub Context",
                        confidence=response.get("confidence", 0.8),
                        timestamp=datetime.now().isoformat()
                    )
                    sources.append(source)
                    
                    logger.info(f"Memory Hub returned context for {session_id}")
                    return response.get("context", {}), sources, True
                else:
                    logger.warning(f"Memory Hub returned no context for {session_id}")
                    return {}, [], False
            
            except json.JSONDecodeError as e:
                logger.error(f"Memory Hub response invalid JSON: {e}")
                return {}, [], False
        else:
            logger.warning(f"Memory Hub call failed: {result.stderr}")
            return {}, [], False
    
    except subprocess.TimeoutExpired:
        logger.error(f"Memory Hub call timed out for {session_id}")
        return {}, [], False
    except Exception as e:
        logger.error(f"Memory Hub call failed: {e}")
        return {}, [], False


async def get_session_context(session_id: str) -> Tuple[ContextSummaryResponse, List[GroundingSource], bool]:
    """
    Get a summary of a session's context.
    
    Retrieves recent decisions, open loops, and knowledge from Memory Hub.
    
    Returns: (context_response, grounding_sources, sources_found)
    """
    logger.info(f"Getting context for session: {session_id}")
    
    # Get context from Memory Hub
    context, sources, sources_found = await get_memory_context(
        session_id=session_id,
        focus=["recent_decisions", "open_loops", "recent_knowledge", "patterns"]
    )
    
    # Extract components
    decisions = context.get("recent_decisions", [])
    open_loops = context.get("open_loops", [])
    knowledge = context.get("recent_knowledge", [])
    patterns = context.get("patterns", [])
    
    # Generate summary
    summary_parts = []
    
    if decisions:
        summary_parts.append(f"Made {len(decisions)} key decisions")
    if open_loops:
        summary_parts.append(f"{len(open_loops)} items pending")
    if knowledge:
        summary_parts.append(f"Captured {len(knowledge)} knowledge entries")
    
    summary = ". ".join(summary_parts) if summary_parts else "No activity recorded for this session."
    
    # Extract topics from knowledge and decisions
    topics = []
    for item in decisions + knowledge:
        # Simple topic extraction - in production, use NLP
        if "export" in item.lower():
            topics.append("Export")
        if "api" in item.lower() or "gateway" in item.lower():
            topics.append("API Gateway")
        if "pdf" in item.lower() or "docx" in item.lower():
            topics.append("Document Rendering")
    
    topics = list(set(topics))  # Deduplicate
    
    return ContextSummaryResponse(
        session_id=session_id,
        summary=summary,
        key_decisions=decisions,
        open_loops=open_loops,
        topics_discussed=topics,
        last_activity=datetime.utcnow()
    )
