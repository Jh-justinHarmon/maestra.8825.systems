"""
A/B Test Logic for Personalization Features

Handles group assignment and decision logic for controlled experiments.
"""

import hashlib
from typing import Literal

GroupAssignment = Literal["A", "B"]


def assign_group(session_id: str, test_percentage: int = 50) -> GroupAssignment:
    """
    Deterministically assign a session to Group A (control) or Group B (treatment).
    
    Uses MD5 hash of session_id for deterministic, sticky assignment.
    Same session_id always gets same group.
    
    Args:
        session_id: Unique session identifier
        test_percentage: Percentage of sessions in Group B (0-100)
        
    Returns:
        "A" for control group, "B" for treatment group
    """
    # Hash session_id to get deterministic value
    hash_value = int(hashlib.md5(session_id.encode()).hexdigest(), 16)
    
    # Convert to percentage (0-99)
    bucket = hash_value % 100
    
    # Assign based on test_percentage
    # If test_percentage=50, buckets 0-49 go to B, 50-99 go to A
    return "B" if bucket < test_percentage else "A"


def should_apply_structure(
    tools_requested: bool,
    mediator_structure: str,
    mediator_confidence: float,
    session_id: str,
    feature_enabled: bool = True,
    test_percentage: int = 50
) -> tuple[bool, GroupAssignment]:
    """
    Determine if structured formatting should be applied.
    
    Returns True only if:
    - Feature flag enabled
    - Session in Group B (treatment)
    - Activation rule matches (tools_requested OR high-confidence structured)
    
    Args:
        tools_requested: Whether user requested artifacts/tools
        mediator_structure: Mediator's structure decision ("conversational" or "structured")
        mediator_confidence: Mediator's confidence score (0.0-1.0)
        session_id: Session identifier for group assignment
        feature_enabled: Feature flag state
        test_percentage: Percentage in treatment group
        
    Returns:
        tuple: (should_apply: bool, group: GroupAssignment)
    """
    # Assign group (deterministic based on session_id)
    group = assign_group(session_id, test_percentage)
    
    # Feature flag check
    if not feature_enabled:
        return False, group
    
    # Group check (only Group B gets treatment)
    if group != "B":
        return False, group
    
    # Activation rule
    if tools_requested:
        return True, group
    elif mediator_structure == "structured" and mediator_confidence >= 0.7:
        return True, group
    else:
        return False, group
