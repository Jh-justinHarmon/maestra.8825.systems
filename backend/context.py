"""
Maestra Backend - Context Logic

Handles /context/{session_id} endpoint logic.
Retrieves session context from Memory Hub.
"""
import os
import sys
import logging
import time
from typing import Optional, List, Tuple
from datetime import datetime

# Add parent paths for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import ContextSummaryResponse

logger = logging.getLogger(__name__)


async def get_memory_context(session_id: str, focus: list = None) -> dict:
    """
    Get context from Memory Hub for a session.
    
    In production, this calls mcp13_memory_get_context.
    """
    if focus is None:
        focus = ["recent_decisions", "open_loops", "recent_knowledge"]
    
    # Simulated response - in production, call Memory Hub MCP
    # This would be: result = await memory_get_context(session_id=session_id, focus=focus)
    
    return {
        "recent_decisions": [
            "Decided to use Typst for PDF rendering",
            "Chose FastAPI for API Gateway"
        ],
        "open_loops": [
            "Need to configure DNS for api.8825.systems",
            "Worker 404 issue pending investigation"
        ],
        "recent_knowledge": [
            "Export Appliance supports email, docx, pdf targets",
            "API Gateway uses scoped tokens for authorization"
        ],
        "patterns": [
            "Pattern-first capture for session summaries",
            "Minimal upstream fixes over downstream workarounds"
        ]
    }


async def get_session_context(session_id: str) -> ContextSummaryResponse:
    """
    Get a summary of a session's context.
    
    Retrieves recent decisions, open loops, and knowledge from Memory Hub.
    """
    logger.info(f"Getting context for session: {session_id}")
    
    # Get context from Memory Hub
    context = await get_memory_context(
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
