"""
Turn Instrumentation - Non-invasive metadata capture for personalization

This module populates ConversationTurn.metadata with descriptive signals
WITHOUT changing any response behavior.

CRITICAL: This is observation-only. No branching logic should depend on these fields.
"""

import logging
import re
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def classify_query_type(query: str) -> str:
    """
    Classify query into explore/execute/reflect.
    
    - explore: Questions, investigations, "what if", research
    - execute: Commands, requests for action, "create", "do"
    - reflect: Meta-questions, alignment checks, "does this feel right"
    """
    query_lower = query.lower()
    
    # Reflect signals
    reflect_patterns = [
        r'\bdoes this (feel|seem|look|sound)\b',
        r'\bis this (right|correct|good|ok|okay)\b',
        r'\bam i (missing|wrong|off)\b',
        r'\bshould (i|we) be\b',
        r'\bwhat do you think\b',
        r'\bmake sense\b',
    ]
    if any(re.search(pattern, query_lower) for pattern in reflect_patterns):
        return "reflect"
    
    # Execute signals
    execute_patterns = [
        r'\b(create|make|build|generate|write|add|update|delete|remove)\b',
        r'\b(run|execute|do|perform|apply|implement)\b',
        r'\b(fix|repair|correct|change)\b',
        r'\b(deploy|publish|ship|launch)\b',
        r'\blet\'s\b',
        r'\bgo ahead\b',
    ]
    if any(re.search(pattern, query_lower) for pattern in execute_patterns):
        return "execute"
    
    # Default to explore
    return "explore"


def detect_depth_requested(query: str) -> bool:
    """
    Detect if user is asking for reasoning, analysis, or investigation.
    
    Returns True if query contains depth signals like:
    - "why", "how", "explain"
    - "analyze", "investigate", "audit"
    - "show me", "walk me through"
    """
    query_lower = query.lower()
    
    depth_patterns = [
        r'\b(why|how|explain|describe)\b',
        r'\b(analyze|investigate|audit|examine|inspect)\b',
        r'\b(show me|walk me through|break down)\b',
        r'\b(reasoning|rationale|logic)\b',
        r'\b(deep dive|in depth|detailed)\b',
        r'\bprompt\b.*\b(for|to)\b',  # "prompt for X"
    ]
    
    return any(re.search(pattern, query_lower) for pattern in depth_patterns)


def detect_alignment_signal(query: str) -> bool:
    """
    Detect if user is expressing uncertainty or questioning intent.
    
    Returns True for:
    - "does this feel right"
    - "am I missing something"
    - "should I be worried"
    - "is this the right approach"
    """
    query_lower = query.lower()
    
    alignment_patterns = [
        r'\b(uncertain|unsure|confused|lost)\b',
        r'\bdoes this (feel|seem|look|sound)\b',
        r'\bam i (missing|wrong|off|overthinking)\b',
        r'\bshould (i|we) be (worried|concerned)\b',
        r'\bis this (right|correct|the right)\b',
        r'\bmake sense\b',
    ]
    
    return any(re.search(pattern, query_lower) for pattern in alignment_patterns)


def detect_tools_requested(query: str) -> bool:
    """
    Detect if user is explicitly asking for prompts, tools, scripts, or artifacts.
    
    Returns True for:
    - "give me a prompt"
    - "create a script"
    - "generate a tool"
    """
    query_lower = query.lower()
    
    tool_patterns = [
        r'\b(prompt|prompts)\b.*\b(for|to|that)\b',
        r'\b(script|tool|artifact|template)\b',
        r'\b(generate|create|write|make)\b.*\b(prompt|script|tool)\b',
    ]
    
    return any(re.search(pattern, query_lower) for pattern in tool_patterns)


def instrument_user_turn(
    query: str,
    follow_up_to: Optional[str] = None,
    start_time_ms: Optional[int] = None,
    epistemic_query_type: Optional[str] = None,
    tool_required: Optional[bool] = None,
    tool_name: Optional[str] = None,
    classification_confidence: Optional[float] = None
) -> Dict[str, Any]:
    """
    Generate metadata for a user query turn.
    
    Args:
        query: User query text
        follow_up_to: Optional turn_id this is a follow-up to
        start_time_ms: Optional start timestamp for latency calculation
        epistemic_query_type: Optional QueryType from epistemic.classify_query()
        tool_required: Optional boolean if tool assertion detected
        tool_name: Optional tool name if tool assertion detected
        classification_confidence: Optional confidence score from classifier
    
    Returns:
        Metadata dict to attach to ConversationTurn
    """
    metadata = {
        "query_type": classify_query_type(query),
        "depth_requested": detect_depth_requested(query),
        "alignment_signal": detect_alignment_signal(query),
        "tools_requested": detect_tools_requested(query),
        "query_length": len(query),
        "instrumented_at": datetime.utcnow().isoformat(),
    }
    
    # Add epistemic classification results if provided
    if epistemic_query_type:
        metadata["epistemic_query_type"] = epistemic_query_type
    
    if tool_required is not None:
        metadata["tool_required"] = tool_required
    
    if tool_name:
        metadata["tool_name"] = tool_name
    
    if classification_confidence is not None:
        metadata["classification_confidence"] = classification_confidence
    
    if follow_up_to:
        metadata["follow_up_to"] = follow_up_to
    
    if start_time_ms:
        metadata["start_time_ms"] = start_time_ms
    
    logger.debug(f"Instrumented user turn: {metadata}")
    return metadata


def instrument_assistant_turn(
    response: str,
    start_time_ms: Optional[int] = None,
    query_type: Optional[str] = None,
    tools_used: Optional[list] = None,
    confidence: Optional[float] = None
) -> Dict[str, Any]:
    """
    Generate metadata for an assistant response turn.
    
    Args:
        response: Assistant response text
        start_time_ms: Optional start timestamp for latency calculation
        query_type: Optional query type from user turn
        tools_used: Optional list of tools/MCPs used
        confidence: Optional confidence score
    
    Returns:
        Metadata dict to attach to ConversationTurn
    """
    metadata = {
        "response_length": len(response),
        "instrumented_at": datetime.utcnow().isoformat(),
    }
    
    if start_time_ms:
        latency_ms = int((datetime.utcnow().timestamp() * 1000) - start_time_ms)
        metadata["latency_ms"] = latency_ms
    
    if query_type:
        metadata["query_type"] = query_type
    
    if tools_used:
        metadata["tools_used"] = tools_used
    
    if confidence is not None:
        metadata["confidence"] = confidence
    
    logger.debug(f"Instrumented assistant turn: {metadata}")
    return metadata
