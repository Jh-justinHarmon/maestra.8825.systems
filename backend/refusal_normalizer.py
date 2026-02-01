"""
Refusal Normalizer — HR-1 Implementation

Converts soft refusals into explicit hard refusals with:
- authority = "none"
- epistemic_state = "REFUSED"

This runs BEFORE enforcement kernel and BEFORE response return.

Rules (NON-NEGOTIABLE):
If ALL of the following are true:
1. Answer text expresses inability / lack of access
2. No grounding sources were used
3. No tool context was successfully invoked

THEN:
- authority = "none"
- epistemic_state = REFUSED
- Response must include retry guidance
"""

import re
import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Refusal Language Triggers
# ─────────────────────────────────────────────

SOFT_REFUSAL_PATTERNS = [
    r"i don'?t have access",
    r"i do not have access",
    r"cannot determine",
    r"not available",
    r"unable to find",
    r"no information about",
    r"i can'?t see",
    r"i cannot see",
    r"does not include",
    r"do not have .* information",
    r"no .* available",
    r"cannot provide",
    r"i'm unable to",
    r"i am unable to",
    r"don't have .* to answer",
    r"do not have .* to answer",
    r"currently do not have",
    r"currently don't have",
    r"no specific .* about",
    r"does not provide specific",
    r"do not provide specific",
    r"sources do not provide",
    r"available sources do not",
    r"cannot find",
    r"i cannot find",
]

# Compile patterns for efficiency
SOFT_REFUSAL_REGEX = re.compile(
    "|".join(SOFT_REFUSAL_PATTERNS),
    re.IGNORECASE
)


# ─────────────────────────────────────────────
# Retry Guidance Templates
# ─────────────────────────────────────────────

RETRY_GUIDANCE = """

**What would help:**
- Provide specific document names or dates
- Ask about topics covered in the personal library
- Try a more general question about the topic
"""


# ─────────────────────────────────────────────
# Normalization Result
# ─────────────────────────────────────────────

@dataclass
class NormalizationResult:
    """Result of refusal normalization."""
    is_soft_refusal: bool
    normalized_authority: str
    normalized_epistemic_state: str
    normalized_answer: str
    reason: Optional[str] = None


# ─────────────────────────────────────────────
# Core Normalization Function
# ─────────────────────────────────────────────

def detect_soft_refusal(answer: str) -> Tuple[bool, Optional[str]]:
    """
    Detect if an answer contains soft refusal language.
    
    Args:
        answer: The answer text to check
    
    Returns:
        Tuple of (is_soft_refusal, matched_pattern)
    """
    match = SOFT_REFUSAL_REGEX.search(answer.lower())
    if match:
        return True, match.group()
    return False, None


def normalize_refusal(
    answer: str,
    sources: List,
    authority: str,
    epistemic_state: str,
    tool_context_used: bool = False
) -> NormalizationResult:
    """
    Normalize a potential soft refusal into a hard refusal.
    
    This function runs BEFORE enforcement kernel.
    
    Args:
        answer: The answer text
        sources: List of grounding sources used
        authority: Current claimed authority
        epistemic_state: Current epistemic state
        tool_context_used: Whether any tool context was successfully invoked
    
    Returns:
        NormalizationResult with potentially updated values
    """
    # Check condition 1: Answer expresses inability
    is_soft_refusal, matched_pattern = detect_soft_refusal(answer)
    
    if not is_soft_refusal:
        # Not a soft refusal, return unchanged
        return NormalizationResult(
            is_soft_refusal=False,
            normalized_authority=authority,
            normalized_epistemic_state=epistemic_state,
            normalized_answer=answer,
            reason=None
        )
    
    # Check condition 2: No grounding sources used
    has_sources = sources and len(sources) > 0
    
    # Check condition 3: No tool context successfully invoked
    has_tool_context = tool_context_used
    
    # If we have real sources or tool context, this is a grounded answer
    # that happens to acknowledge limitations — don't downgrade it
    if has_sources or has_tool_context:
        logger.info(
            f"Soft refusal detected but has sources ({len(sources) if sources else 0}) "
            f"or tool context ({has_tool_context}), not normalizing"
        )
        return NormalizationResult(
            is_soft_refusal=True,
            normalized_authority=authority,
            normalized_epistemic_state=epistemic_state,
            normalized_answer=answer,
            reason="Has sources or tool context, keeping original authority"
        )
    
    # All conditions met — normalize to hard refusal
    logger.critical(
        f"🔴 SOFT_REFUSAL_NORMALIZED | pattern='{matched_pattern}' | "
        f"old_authority='{authority}' | new_authority='none'"
    )
    
    # Add retry guidance if not already present
    normalized_answer = answer
    if "what would help" not in answer.lower():
        normalized_answer = answer.rstrip() + RETRY_GUIDANCE
    
    return NormalizationResult(
        is_soft_refusal=True,
        normalized_authority="none",
        normalized_epistemic_state="REFUSED",
        normalized_answer=normalized_answer,
        reason=f"Soft refusal detected: '{matched_pattern}'"
    )


def should_normalize_to_refusal(
    answer: str,
    sources: List,
    tool_context_used: bool = False
) -> bool:
    """
    Quick check if an answer should be normalized to a refusal.
    
    Args:
        answer: The answer text
        sources: List of grounding sources
        tool_context_used: Whether tool context was used
    
    Returns:
        True if this should become a hard refusal
    """
    is_soft_refusal, _ = detect_soft_refusal(answer)
    
    if not is_soft_refusal:
        return False
    
    has_sources = sources and len(sources) > 0
    
    return not has_sources and not tool_context_used
