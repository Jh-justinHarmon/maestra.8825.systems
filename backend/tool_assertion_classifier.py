"""
Tool Assertion Classifier — HR-2 Implementation

Detects queries that explicitly assert tool provenance and marks
those tools as REQUIRED (not optional).

If a query asserts tool provenance but the tool is unavailable,
the system MUST refuse — no fallback to library allowed.
"""

import re
import logging
from dataclasses import dataclass
from typing import Optional, List

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Tool Assertion Patterns
# ─────────────────────────────────────────────

TOOL_ASSERTION_PATTERNS = {
    "sentinel": [
        r"based on sentinel",
        r"from sentinel results?",
        r"according to sentinel",
        r"sentinel (says?|shows?|indicates?)",
        r"what (does|did) sentinel",
        r"sentinel results? (show|indicate|say)",
    ],
    "internal_documents": [
        r"from internal documents?",
        r"from archived files?",
        r"from internal emails?",
        r"in (the|our) internal",
        r"from (the|our) archives?",
        r"internal (docs?|documents?|files?) (show|say|indicate)",
        r"historical decisions?",
        r"what did we decide",
        r"according to internal docs?",
        r"from (the|our) records?",
    ],
    "deep_research": [
        r"based on (deep )?research",
        r"from (the|our) research",
        r"research (shows?|indicates?|says?)",
    ],
}

# Compile patterns
COMPILED_PATTERNS = {
    tool: re.compile("|".join(patterns), re.IGNORECASE)
    for tool, patterns in TOOL_ASSERTION_PATTERNS.items()
}


# ─────────────────────────────────────────────
# Classification Result
# ─────────────────────────────────────────────

@dataclass
class ToolAssertionResult:
    """Result of tool assertion classification."""
    requires_tool: bool
    required: bool  # True = MUST have tool, False = optional
    tool_name: Optional[str]
    matched_pattern: Optional[str]
    original_query: str
    confidence: float = 1.0  # Confidence in the classification


# ─────────────────────────────────────────────
# Core Classification Function
# ─────────────────────────────────────────────

def classify_tool_assertion(query: str) -> ToolAssertionResult:
    """
    Classify a query for explicit tool assertions.
    
    If a query explicitly mentions a tool (e.g., "Based on Sentinel results..."),
    that tool becomes REQUIRED — not optional.
    
    Args:
        query: The user query
    
    Returns:
        ToolAssertionResult with tool requirements
    """
    query_lower = query.lower()
    
    for tool_name, pattern in COMPILED_PATTERNS.items():
        match = pattern.search(query_lower)
        if match:
            logger.info(
                f"Tool assertion detected: tool={tool_name}, "
                f"pattern='{match.group()}', query='{query[:50]}...'"
            )
            return ToolAssertionResult(
                requires_tool=True,
                required=True,  # MUST have this tool
                tool_name=tool_name,
                matched_pattern=match.group(),
                original_query=query
            )
    
    # No tool assertion found
    return ToolAssertionResult(
        requires_tool=False,
        required=False,
        tool_name=None,
        matched_pattern=None,
        original_query=query
    )


def get_required_tools(query: str) -> List[str]:
    """
    Get list of tools required by a query.
    
    Args:
        query: The user query
    
    Returns:
        List of required tool names (empty if none required)
    """
    result = classify_tool_assertion(query)
    if result.requires_tool and result.tool_name:
        # Map tool names to actual tool identifiers
        tool_mapping = {
            "sentinel": "sentinel",
            "internal_documents": "sentinel",  # Internal docs = Sentinel
            "deep_research": "deep_research",
        }
        return [tool_mapping.get(result.tool_name, result.tool_name)]
    return []


def query_requires_sentinel(query: str) -> bool:
    """
    Quick check if a query requires Sentinel.
    
    Args:
        query: The user query
    
    Returns:
        True if Sentinel is required
    """
    result = classify_tool_assertion(query)
    return (
        result.requires_tool and 
        result.tool_name in ["sentinel", "internal_documents"]
    )
