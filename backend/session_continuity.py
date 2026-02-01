"""
Maestra Backend - Session Continuity Tracker

Maintains conversation state, open loops, and context across multiple turns.
Enables multi-turn intelligence with memory of previous decisions and context.

Features:
- Turn-by-turn conversation history
- Open loops tracking (unresolved questions)
- Context accumulation (what we've learned)
- Decision history (what was decided)
- Capability state (which MCPs are available)
"""

import logging
import time
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class TurnType(str, Enum):
    USER_QUERY = "user_query"
    ASSISTANT_RESPONSE = "assistant_response"
    SYSTEM_EVENT = "system_event"

@dataclass
class ConversationTurn:
    """Single turn in a conversation."""
    turn_id: str
    type: str  # TurnType
    timestamp: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class OpenLoop:
    """Unresolved question or decision."""
    id: str
    title: str
    created_at: str
    last_mentioned: str
    status: str = "open"  # open, resolved, deferred
    context: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class ContextAccumulation:
    """Accumulated knowledge from conversation."""
    key: str
    value: Any
    source: str  # Which turn introduced this
    confidence: float
    timestamp: str
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class SessionContinuity:
    """Complete session state."""
    session_id: str
    turns: List[ConversationTurn] = field(default_factory=list)
    open_loops: List[OpenLoop] = field(default_factory=list)
    context_accumulation: Dict[str, ContextAccumulation] = field(default_factory=dict)
    decision_history: List[Dict[str, Any]] = field(default_factory=list)
    capabilities_available: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_activity: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "turns": [t.to_dict() for t in self.turns],
            "open_loops": [l.to_dict() for l in self.open_loops],
            "context_accumulation": {
                k: v.to_dict() for k, v in self.context_accumulation.items()
            },
            "decision_history": self.decision_history,
            "capabilities_available": self.capabilities_available,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
        }

class SessionContinuityTracker:
    """Tracks and manages session continuity."""
    
    def __init__(self):
        self.sessions: Dict[str, SessionContinuity] = {}
    
    def get_or_create_session(self, session_id: str) -> SessionContinuity:
        """Get existing session or create new one."""
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionContinuity(session_id=session_id)
            logger.info(f"Created new session: {session_id}")
        return self.sessions[session_id]
    
    def add_turn(
        self,
        session_id: str,
        turn_id: str,
        turn_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationTurn:
        """Add a turn to the conversation."""
        session = self.get_or_create_session(session_id)
        
        turn = ConversationTurn(
            turn_id=turn_id,
            type=turn_type,
            timestamp=datetime.utcnow().isoformat(),
            content=content,
            metadata=metadata or {}
        )
        
        session.turns.append(turn)
        session.last_activity = datetime.utcnow().isoformat()
        
        logger.info(f"Added turn {turn_id} to session {session_id}")
        return turn
    
    def add_open_loop(
        self,
        session_id: str,
        loop_id: str,
        title: str,
        context: str = ""
    ) -> OpenLoop:
        """Add an open loop to the session."""
        session = self.get_or_create_session(session_id)
        
        loop = OpenLoop(
            id=loop_id,
            title=title,
            created_at=datetime.utcnow().isoformat(),
            last_mentioned=datetime.utcnow().isoformat(),
            context=context
        )
        
        session.open_loops.append(loop)
        session.last_activity = datetime.utcnow().isoformat()
        
        logger.info(f"Added open loop {loop_id} to session {session_id}")
        return loop
    
    def resolve_open_loop(self, session_id: str, loop_id: str) -> bool:
        """Mark an open loop as resolved."""
        session = self.get_or_create_session(session_id)
        
        for loop in session.open_loops:
            if loop.id == loop_id:
                loop.status = "resolved"
                loop.last_mentioned = datetime.utcnow().isoformat()
                session.last_activity = datetime.utcnow().isoformat()
                logger.info(f"Resolved open loop {loop_id} in session {session_id}")
                return True
        
        return False
    
    def accumulate_context(
        self,
        session_id: str,
        key: str,
        value: Any,
        source: str,
        confidence: float = 0.8
    ) -> ContextAccumulation:
        """Accumulate context from a turn."""
        session = self.get_or_create_session(session_id)
        
        context = ContextAccumulation(
            key=key,
            value=value,
            source=source,
            confidence=confidence,
            timestamp=datetime.utcnow().isoformat()
        )
        
        session.context_accumulation[key] = context
        session.last_activity = datetime.utcnow().isoformat()
        
        logger.info(f"Accumulated context {key} in session {session_id}")
        return context
    
    def record_decision(
        self,
        session_id: str,
        decision: str,
        rationale: str,
        alternatives: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Record a decision made in the session."""
        session = self.get_or_create_session(session_id)
        
        decision_record = {
            "decision": decision,
            "rationale": rationale,
            "alternatives": alternatives or [],
            "timestamp": datetime.utcnow().isoformat(),
            "turn_count": len(session.turns)
        }
        
        session.decision_history.append(decision_record)
        session.last_activity = datetime.utcnow().isoformat()
        
        logger.info(f"Recorded decision in session {session_id}")
        return decision_record
    
    def set_capabilities(self, session_id: str, capabilities: List[str]) -> None:
        """Set available capabilities for the session."""
        session = self.get_or_create_session(session_id)
        session.capabilities_available = capabilities
        session.last_activity = datetime.utcnow().isoformat()
        logger.info(f"Set capabilities for session {session_id}: {capabilities}")
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Get a summary of the session state."""
        session = self.get_or_create_session(session_id)
        
        return {
            "session_id": session_id,
            "turn_count": len(session.turns),
            "open_loops_count": len([l for l in session.open_loops if l.status == "open"]),
            "context_keys": list(session.context_accumulation.keys()),
            "decision_count": len(session.decision_history),
            "capabilities": session.capabilities_available,
            "created_at": session.created_at,
            "last_activity": session.last_activity,
            "duration_minutes": (
                (datetime.fromisoformat(session.last_activity) - 
                 datetime.fromisoformat(session.created_at)).total_seconds() / 60
            )
        }
    
    def get_session_state(self, session_id: str) -> SessionContinuity:
        """Get complete session state."""
        return self.get_or_create_session(session_id)
    
    def get_context_for_next_turn(self, session_id: str) -> Dict[str, Any]:
        """Get context to pass to next turn."""
        session = self.get_or_create_session(session_id)
        
        return {
            "recent_turns": [t.to_dict() for t in session.turns[-15:]],  # Last 15 turns
            "open_loops": [l.to_dict() for l in session.open_loops if l.status == "open"],
            "accumulated_context": {
                k: v.to_dict() for k, v in session.context_accumulation.items()
            },
            "recent_decisions": session.decision_history[-2:] if session.decision_history else [],
            "capabilities": session.capabilities_available,
        }

# Global tracker instance
continuity_tracker = SessionContinuityTracker()

def get_or_create_session(session_id: str) -> SessionContinuity:
    """Get or create a session."""
    return continuity_tracker.get_or_create_session(session_id)

def add_turn(
    session_id: str,
    turn_id: str,
    turn_type: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None
) -> ConversationTurn:
    """Add a turn to the conversation."""
    return continuity_tracker.add_turn(session_id, turn_id, turn_type, content, metadata)

def get_session_summary(session_id: str) -> Dict[str, Any]:
    """Get session summary."""
    return continuity_tracker.get_session_summary(session_id)

def get_context_for_next_turn(session_id: str) -> Dict[str, Any]:
    """Get context for next turn."""
    return continuity_tracker.get_context_for_next_turn(session_id)

def accumulate_context(
    session_id: str,
    key: str,
    value: Any,
    source: str,
    confidence: float = 0.8
) -> ContextAccumulation:
    """Accumulate context from a turn."""
    return continuity_tracker.accumulate_context(session_id, key, value, source, confidence)

def record_decision(
    session_id: str,
    decision: str,
    rationale: str,
    alternatives: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Record a decision made in the session."""
    return continuity_tracker.record_decision(session_id, decision, rationale, alternatives)
