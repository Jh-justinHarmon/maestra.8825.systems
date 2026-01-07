"""
Epistemic Foundation for Maestra

Enforces truth verification at every layer.
No answer without verified grounding.
Silence is a first-class outcome.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
import hashlib
import json


class EpistemicState(str, Enum):
    """Three states: grounded, ungrounded, or refused."""
    GROUNDED = "grounded"
    UNGROUNDED = "ungrounded"
    REFUSED = "refused"


class GroundingSourceType(str, Enum):
    """Types of grounding sources."""
    LIBRARY = "library"
    MEMORY_HUB = "memory_hub"
    JH_BRAIN = "jh_brain"
    CLIENT_CONTEXT = "client_context"
    SESSION_CONTEXT = "session_context"
    DEEP_RESEARCH = "deep_research"
    EXTERNAL_API = "external_api"


class QueryType(str, Enum):
    """Query classification for determining grounding requirements."""
    MEMORY_REQUIRED = "memory_required"  # "What did we decide?"
    CONTEXT_REQUIRED = "context_required"  # "What am I looking at?"
    RESEARCH_REQUIRED = "research_required"  # "Research X"
    GENERATIVE_ALLOWED = "generative_allowed"  # "Brainstorm names"


@dataclass
class GroundingSource:
    """A single grounding source that contributed to an answer."""
    source_type: GroundingSourceType
    identifier: str  # Entry ID, URL, etc.
    title: str
    confidence: float  # 0.0 to 1.0
    excerpt: Optional[str] = None
    timestamp: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.source_type.value,
            "identifier": self.identifier,
            "title": self.title,
            "confidence": self.confidence,
            "excerpt": self.excerpt,
            "timestamp": self.timestamp
        }


@dataclass
class GroundingResult:
    """Result of grounding verification for a query."""
    query: str
    query_type: QueryType
    requires_grounding: bool
    sources_found: List[GroundingSource] = field(default_factory=list)
    sources_empty: bool = False
    confidence: float = 0.0
    trace_id: str = ""
    
    @property
    def is_grounded(self) -> bool:
        """True if grounding is sufficient."""
        if not self.requires_grounding:
            return True  # Generative queries don't need grounding
        return len(self.sources_found) > 0 and self.confidence >= 0.5
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "query_type": self.query_type.value,
            "requires_grounding": self.requires_grounding,
            "sources_found": [s.to_dict() for s in self.sources_found],
            "sources_empty": self.sources_empty,
            "confidence": self.confidence,
            "is_grounded": self.is_grounded,
            "trace_id": self.trace_id
        }


def classify_query(query: str) -> QueryType:
    """
    Classify query to determine if grounding is required.
    
    MEMORY_REQUIRED: "What did we decide?", "Why did we choose?", etc.
    CONTEXT_REQUIRED: "What am I looking at?", "What's on my screen?"
    RESEARCH_REQUIRED: "Research X", "Investigate Y"
    GENERATIVE_ALLOWED: "Brainstorm names", "Explain X", etc.
    """
    query_lower = query.lower()
    
    # Domain terms that indicate memory is required
    memory_indicators = [
        "what did we", "why did we", "how did we",
        "what did you", "why did you", "how did you",
        "what's the context", "what's the history",
        "what did we decide", "what did we choose",
        "what did we learn", "what did we try",
        "decision", "chose", "picked", "decided",
        "8825", "project", "team", "we "
    ]
    
    # Context terms that indicate client context is required
    context_indicators = [
        "what am i looking at", "what's on my screen",
        "what do you see", "can you see",
        "what's visible", "what's showing",
        "page", "website", "url", "domain"
    ]
    
    # Research terms
    research_indicators = [
        "research", "investigate", "look into",
        "find information", "search for", "explore"
    ]
    
    # Check for memory requirements
    for indicator in memory_indicators:
        if indicator in query_lower:
            return QueryType.MEMORY_REQUIRED
    
    # Check for context requirements
    for indicator in context_indicators:
        if indicator in query_lower:
            return QueryType.CONTEXT_REQUIRED
    
    # Check for research requirements
    for indicator in research_indicators:
        if indicator in query_lower:
            return QueryType.RESEARCH_REQUIRED
    
    # Default: generative (no grounding required)
    return QueryType.GENERATIVE_ALLOWED


def verify_grounding(
    query: str,
    sources: List[GroundingSource],
    trace_id: str = ""
) -> GroundingResult:
    """
    Verify if a query has sufficient grounding.
    
    Returns GroundingResult with:
    - is_grounded: True if grounding is sufficient
    - confidence: Overall confidence score
    - sources_found: List of actual sources
    """
    query_type = classify_query(query)
    
    # Determine if grounding is required
    requires_grounding = query_type in [
        QueryType.MEMORY_REQUIRED,
        QueryType.CONTEXT_REQUIRED,
        QueryType.RESEARCH_REQUIRED
    ]
    
    # Calculate confidence based on sources
    if sources:
        confidence = sum(s.confidence for s in sources) / len(sources)
    else:
        confidence = 0.0
    
    result = GroundingResult(
        query=query,
        query_type=query_type,
        requires_grounding=requires_grounding,
        sources_found=sources,
        sources_empty=len(sources) == 0,
        confidence=confidence,
        trace_id=trace_id
    )
    
    return result


def compute_verification_hash(data: Any) -> str:
    """
    Compute SHA256 hash of data for verification.
    
    Used to detect:
    - Data tampering
    - Cached stale data
    - Duplicate responses
    """
    if isinstance(data, dict):
        json_str = json.dumps(data, sort_keys=True, default=str)
    else:
        json_str = json.dumps(data, default=str)
    
    return hashlib.sha256(json_str.encode()).hexdigest()


@dataclass
class EpistemicResponse:
    """
    Response with full epistemic metadata.
    
    Every response from Maestra includes:
    - answer: The actual response
    - epistemic_state: GROUNDED, UNGROUNDED, or REFUSED
    - grounding_sources: List of sources that contributed
    - confidence: Overall confidence score
    - trace_id: For forensic tracing
    - verification_hash: Hash of sources for integrity
    """
    answer: str
    epistemic_state: EpistemicState
    grounding_sources: List[GroundingSource] = field(default_factory=list)
    confidence: float = 0.0
    trace_id: str = ""
    verification_hash: str = ""
    reason_if_refused: Optional[str] = None
    what_would_help: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "epistemic_state": self.epistemic_state.value,
            "grounding_sources": [s.to_dict() for s in self.grounding_sources],
            "confidence": self.confidence,
            "trace_id": self.trace_id,
            "verification_hash": self.verification_hash,
            "reason_if_refused": self.reason_if_refused,
            "what_would_help": self.what_would_help
        }


def create_refused_response(
    query: str,
    trace_id: str = "",
    what_would_help: Optional[List[str]] = None
) -> EpistemicResponse:
    """
    Create a REFUSED response when grounding is unavailable.
    
    Clear message explaining why and what would help.
    """
    if what_would_help is None:
        what_would_help = [
            "Library entries about this topic",
            "Recent decisions or context",
            "Project history or background"
        ]
    
    return EpistemicResponse(
        answer=f"I cannot answer this question because I don't have the required context. To help you, I would need: {', '.join(what_would_help)}",
        epistemic_state=EpistemicState.REFUSED,
        grounding_sources=[],
        confidence=0.0,
        trace_id=trace_id,
        verification_hash="",
        reason_if_refused="Query requires grounding but no sources available",
        what_would_help=what_would_help
    )


def create_grounded_response(
    answer: str,
    sources: List[GroundingSource],
    trace_id: str = ""
) -> EpistemicResponse:
    """
    Create a GROUNDED response with source attribution.
    """
    confidence = sum(s.confidence for s in sources) / len(sources) if sources else 0.0
    verification_hash = compute_verification_hash(
        [s.to_dict() for s in sources]
    )
    
    return EpistemicResponse(
        answer=answer,
        epistemic_state=EpistemicState.GROUNDED,
        grounding_sources=sources,
        confidence=confidence,
        trace_id=trace_id,
        verification_hash=verification_hash
    )


def create_ungrounded_response(
    answer: str,
    trace_id: str = ""
) -> EpistemicResponse:
    """
    Create an UNGROUNDED response (speculative, no grounding required).
    """
    return EpistemicResponse(
        answer=answer,
        epistemic_state=EpistemicState.UNGROUNDED,
        grounding_sources=[],
        confidence=0.0,
        trace_id=trace_id,
        verification_hash=""
    )


# Startup Invariants
class StartupInvariant:
    """Verify system is in valid state at startup."""
    
    @staticmethod
    def verify_library_accessible(library_path: str) -> bool:
        """Verify library path exists and is readable."""
        import os
        return os.path.exists(library_path) and os.access(library_path, os.R_OK)
    
    @staticmethod
    def verify_critical_mcps_reachable(mcp_endpoints: Dict[str, str]) -> bool:
        """Verify critical MCPs are reachable."""
        import subprocess
        for mcp_name, endpoint in mcp_endpoints.items():
            try:
                # Simple health check via subprocess
                result = subprocess.run(
                    ["curl", "-s", f"{endpoint}/health"],
                    capture_output=True,
                    timeout=2
                )
                if result.returncode != 0:
                    return False
            except Exception:
                return False
        return True
    
    @staticmethod
    def verify_session_management_working() -> bool:
        """Verify session management is operational."""
        # This would be implemented based on actual session manager
        return True
    
    @staticmethod
    def run_all_checks(
        library_path: str,
        mcp_endpoints: Dict[str, str],
        production_mode: bool = False
    ) -> tuple[bool, List[str]]:
        """
        Run all startup invariants.
        
        Returns: (all_passed, list_of_failures)
        """
        failures = []
        
        if not StartupInvariant.verify_library_accessible(library_path):
            failures.append("Library path not accessible")
        
        if not StartupInvariant.verify_session_management_working():
            failures.append("Session management not working")
        
        # MCPs are optional in dev, required in prod
        if production_mode:
            if not StartupInvariant.verify_critical_mcps_reachable(mcp_endpoints):
                failures.append("Critical MCPs not reachable")
        
        return len(failures) == 0, failures
