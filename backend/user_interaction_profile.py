"""
User Interaction Profile - Read-only personalization signals from library and sessions

This module exposes behavioral signals inferred from personal library metadata
and session patterns WITHOUT making personalization decisions.

CRITICAL: Profile is inferred, not user-editable. Never affects enforcement or authority.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class UserInteractionProfile:
    """
    Read-only profile inferred from interaction patterns.
    
    IMPORTANT: This is observation-only. No enforcement or authority decisions
    should depend on this profile.
    """
    user_id: str
    
    # Library signals (inferred from personal library metadata)
    most_accessed_tags: List[str] = field(default_factory=list)  # Top 5 tags
    preferred_entry_types: Dict[str, float] = field(default_factory=dict)  # knowledge/decision/pattern weights
    avg_doc_length: Optional[float] = None  # Average document length in chars
    update_frequency: Optional[float] = None  # Docs updated per week
    cross_reference_density: Optional[float] = None  # Avg references per doc
    
    # Session signals (inferred from conversation patterns)
    avg_message_length: Optional[float] = None  # Chars per user message
    avg_follow_up_depth: Optional[float] = None  # Turns per topic
    tool_usage_rate: Optional[float] = None  # MCP calls per session
    
    # Metadata
    first_seen: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    sample_size: int = 0  # Number of sessions analyzed
    confidence: float = 0.0  # 0.0-1.0 based on sample size
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class UserProfileBuilder:
    """
    Builds UserInteractionProfile from library metadata and session data.
    
    This is a read-only aggregation layer - it observes but does not decide.
    """
    
    def __init__(self):
        self.profiles: Dict[str, UserInteractionProfile] = {}
    
    def build_from_library(
        self,
        user_id: str,
        library_entries: List[Dict[str, Any]]
    ) -> UserInteractionProfile:
        """
        Build profile from personal library metadata.
        
        Args:
            user_id: User identifier
            library_entries: List of library entry dicts with metadata
        
        Returns:
            UserInteractionProfile (read-only)
        """
        if not library_entries:
            return UserInteractionProfile(user_id=user_id)
        
        # Extract signals from library metadata
        all_tags = []
        entry_types = []
        doc_lengths = []
        
        for entry in library_entries:
            # Tags
            tags = entry.get("tags", [])
            if tags:
                all_tags.extend(tags)
            
            # Entry type
            entry_type = entry.get("entry_type")
            if entry_type:
                entry_types.append(entry_type)
            
            # Document length
            content = entry.get("content", "")
            if content:
                doc_lengths.append(len(content))
        
        # Compute most accessed tags (top 5)
        tag_counts = Counter(all_tags)
        most_accessed_tags = [tag for tag, _ in tag_counts.most_common(5)]
        
        # Compute entry type distribution
        type_counts = Counter(entry_types)
        total_types = sum(type_counts.values())
        preferred_entry_types = {
            entry_type: count / total_types
            for entry_type, count in type_counts.items()
        } if total_types > 0 else {}
        
        # Compute average document length
        avg_doc_length = sum(doc_lengths) / len(doc_lengths) if doc_lengths else None
        
        # Build profile
        profile = UserInteractionProfile(
            user_id=user_id,
            most_accessed_tags=most_accessed_tags,
            preferred_entry_types=preferred_entry_types,
            avg_doc_length=avg_doc_length,
            sample_size=len(library_entries),
            confidence=min(1.0, len(library_entries) / 20.0)  # Confidence increases with sample size
        )
        
        self.profiles[user_id] = profile
        logger.info(f"Built profile for {user_id}: {len(library_entries)} entries, confidence={profile.confidence:.2f}")
        
        return profile
    
    def update_from_sessions(
        self,
        user_id: str,
        session_turns: List[Dict[str, Any]]
    ) -> UserInteractionProfile:
        """
        Update profile with session interaction patterns.
        
        Args:
            user_id: User identifier
            session_turns: List of conversation turns with metadata
        
        Returns:
            Updated UserInteractionProfile
        """
        profile = self.profiles.get(user_id, UserInteractionProfile(user_id=user_id))
        
        if not session_turns:
            return profile
        
        # Extract user messages
        user_messages = [
            turn for turn in session_turns
            if turn.get("type") == "user_query"
        ]
        
        if not user_messages:
            return profile
        
        # Compute average message length
        message_lengths = [
            len(turn.get("content", ""))
            for turn in user_messages
        ]
        profile.avg_message_length = sum(message_lengths) / len(message_lengths)
        
        # Compute tool usage rate
        assistant_turns = [
            turn for turn in session_turns
            if turn.get("type") == "assistant_response"
        ]
        tools_used_count = sum(
            1 for turn in assistant_turns
            if turn.get("metadata", {}).get("tools_used")
        )
        profile.tool_usage_rate = tools_used_count / len(assistant_turns) if assistant_turns else 0.0
        
        # Update metadata
        profile.last_updated = datetime.utcnow().isoformat()
        profile.sample_size += len(session_turns)
        profile.confidence = min(1.0, profile.sample_size / 50.0)  # Confidence increases with sample size
        
        self.profiles[user_id] = profile
        logger.info(f"Updated profile for {user_id}: {len(session_turns)} turns, confidence={profile.confidence:.2f}")
        
        return profile
    
    def get_profile(self, user_id: str) -> Optional[UserInteractionProfile]:
        """
        Get profile for a user (read-only).
        
        Returns None if insufficient data.
        """
        profile = self.profiles.get(user_id)
        
        # Only return profile if confidence is sufficient
        if profile and profile.confidence >= 0.3:
            return profile
        
        return None


# Global profile builder instance
_profile_builder = UserProfileBuilder()


def get_profile_builder() -> UserProfileBuilder:
    """Get the global profile builder instance."""
    return _profile_builder


def get_user_profile(user_id: str) -> Optional[UserInteractionProfile]:
    """
    Get user interaction profile (read-only).
    
    Returns None if insufficient data or confidence < 0.3.
    """
    return _profile_builder.get_profile(user_id)
