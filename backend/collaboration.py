"""
Maestra Backend - Collaboration Layer

Enables shared context and document awareness across sessions.
Tracks which documents are being discussed, shared context between users,
and collaborative decision-making.

Features:
- Document tracking (what's being discussed)
- Shared context (cross-session knowledge)
- Collaborative decisions (group consensus)
- Context inheritance (new sessions inherit team context)
"""

import logging
import time
from typing import List, Dict, Optional, Any, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class DocumentType(str, Enum):
    CODE = "code"
    DOCUMENT = "document"
    DECISION = "decision"
    RESEARCH = "research"
    KNOWLEDGE = "knowledge"
    CONVERSATION = "conversation"

@dataclass
class DocumentReference:
    """Reference to a document being discussed."""
    doc_id: str
    title: str
    doc_type: str  # DocumentType
    url: Optional[str] = None
    excerpt: str = ""
    mentioned_in_sessions: List[str] = field(default_factory=list)
    last_mentioned: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    relevance_score: float = 0.8
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class SharedContext:
    """Context shared across multiple sessions."""
    context_id: str
    key: str
    value: Any
    source_session: str  # Which session created this
    created_at: str
    accessed_by_sessions: List[str] = field(default_factory=list)
    confidence: float = 0.8
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class CollaborativeDecision:
    """Decision made collaboratively across sessions."""
    decision_id: str
    title: str
    description: str
    created_by_session: str
    contributing_sessions: List[str] = field(default_factory=list)
    rationale: str = ""
    alternatives_considered: List[str] = field(default_factory=list)
    consensus_level: float = 0.8  # 0-1, how much agreement
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    status: str = "active"  # active, archived, superseded
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class TeamContext:
    """Aggregated context for a team/workspace."""
    team_id: str
    name: str
    documents: Dict[str, DocumentReference] = field(default_factory=dict)
    shared_contexts: Dict[str, SharedContext] = field(default_factory=dict)
    collaborative_decisions: Dict[str, CollaborativeDecision] = field(default_factory=dict)
    active_sessions: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_activity: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            "team_id": self.team_id,
            "name": self.name,
            "documents": {k: v.to_dict() for k, v in self.documents.items()},
            "shared_contexts": {k: v.to_dict() for k, v in self.shared_contexts.items()},
            "collaborative_decisions": {k: v.to_dict() for k, v in self.collaborative_decisions.items()},
            "active_sessions": self.active_sessions,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
        }

class CollaborationTracker:
    """Tracks collaboration and shared context."""
    
    def __init__(self):
        self.teams: Dict[str, TeamContext] = {}
        self.session_to_team: Dict[str, str] = {}  # Map sessions to teams
    
    def get_or_create_team(self, team_id: str, team_name: str = "Default Team") -> TeamContext:
        """Get or create a team."""
        if team_id not in self.teams:
            self.teams[team_id] = TeamContext(team_id=team_id, name=team_name)
            logger.info(f"Created team: {team_id}")
        return self.teams[team_id]
    
    def add_session_to_team(self, session_id: str, team_id: str) -> None:
        """Add a session to a team."""
        team = self.get_or_create_team(team_id)
        if session_id not in team.active_sessions:
            team.active_sessions.append(session_id)
            self.session_to_team[session_id] = team_id
            team.last_activity = datetime.utcnow().isoformat()
            logger.info(f"Added session {session_id} to team {team_id}")
    
    def track_document(
        self,
        team_id: str,
        doc_id: str,
        title: str,
        doc_type: str,
        session_id: str,
        url: Optional[str] = None,
        excerpt: str = ""
    ) -> DocumentReference:
        """Track a document being discussed."""
        team = self.get_or_create_team(team_id)
        
        if doc_id in team.documents:
            doc = team.documents[doc_id]
            if session_id not in doc.mentioned_in_sessions:
                doc.mentioned_in_sessions.append(session_id)
            doc.last_mentioned = datetime.utcnow().isoformat()
        else:
            doc = DocumentReference(
                doc_id=doc_id,
                title=title,
                doc_type=doc_type,
                url=url,
                excerpt=excerpt,
                mentioned_in_sessions=[session_id]
            )
            team.documents[doc_id] = doc
        
        team.last_activity = datetime.utcnow().isoformat()
        logger.info(f"Tracked document {doc_id} in team {team_id}")
        return doc
    
    def share_context(
        self,
        team_id: str,
        context_id: str,
        key: str,
        value: Any,
        source_session: str,
        tags: Optional[List[str]] = None,
        confidence: float = 0.8
    ) -> SharedContext:
        """Share context across team."""
        team = self.get_or_create_team(team_id)
        
        context = SharedContext(
            context_id=context_id,
            key=key,
            value=value,
            source_session=source_session,
            created_at=datetime.utcnow().isoformat(),
            accessed_by_sessions=[source_session],
            confidence=confidence,
            tags=tags or []
        )
        
        team.shared_contexts[context_id] = context
        team.last_activity = datetime.utcnow().isoformat()
        logger.info(f"Shared context {key} in team {team_id}")
        return context
    
    def access_shared_context(self, team_id: str, context_id: str, session_id: str) -> Optional[SharedContext]:
        """Access shared context from another session."""
        team = self.get_or_create_team(team_id)
        
        if context_id in team.shared_contexts:
            context = team.shared_contexts[context_id]
            if session_id not in context.accessed_by_sessions:
                context.accessed_by_sessions.append(session_id)
            team.last_activity = datetime.utcnow().isoformat()
            logger.info(f"Session {session_id} accessed shared context {context_id}")
            return context
        
        return None
    
    def record_collaborative_decision(
        self,
        team_id: str,
        decision_id: str,
        title: str,
        description: str,
        created_by_session: str,
        rationale: str = "",
        alternatives: Optional[List[str]] = None
    ) -> CollaborativeDecision:
        """Record a collaborative decision."""
        team = self.get_or_create_team(team_id)
        
        decision = CollaborativeDecision(
            decision_id=decision_id,
            title=title,
            description=description,
            created_by_session=created_by_session,
            contributing_sessions=[created_by_session],
            rationale=rationale,
            alternatives_considered=alternatives or [],
            created_at=datetime.utcnow().isoformat()
        )
        
        team.collaborative_decisions[decision_id] = decision
        team.last_activity = datetime.utcnow().isoformat()
        logger.info(f"Recorded collaborative decision {decision_id} in team {team_id}")
        return decision
    
    def contribute_to_decision(
        self,
        team_id: str,
        decision_id: str,
        session_id: str,
        contribution: str = ""
    ) -> bool:
        """Add a session's contribution to a collaborative decision."""
        team = self.get_or_create_team(team_id)
        
        if decision_id in team.collaborative_decisions:
            decision = team.collaborative_decisions[decision_id]
            if session_id not in decision.contributing_sessions:
                decision.contributing_sessions.append(session_id)
            team.last_activity = datetime.utcnow().isoformat()
            logger.info(f"Session {session_id} contributed to decision {decision_id}")
            return True
        
        return False
    
    def get_team_context_for_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get team context for a session."""
        team_id = self.session_to_team.get(session_id)
        if not team_id:
            return None
        
        team = self.teams.get(team_id)
        if not team:
            return None
        
        return {
            "team_id": team_id,
            "team_name": team.name,
            "active_sessions": len(team.active_sessions),
            "documents_count": len(team.documents),
            "shared_contexts_count": len(team.shared_contexts),
            "collaborative_decisions_count": len(team.collaborative_decisions),
            "recent_documents": [
                d.to_dict() for d in sorted(
                    team.documents.values(),
                    key=lambda x: x.last_mentioned,
                    reverse=True
                )[:5]
            ],
            "shared_context_keys": list(team.shared_contexts.keys()),
            "active_decisions": [
                d.to_dict() for d in team.collaborative_decisions.values()
                if d.status == "active"
            ]
        }
    
    def get_team_summary(self, team_id: str) -> Dict[str, Any]:
        """Get summary of team collaboration."""
        team = self.get_or_create_team(team_id)
        
        return {
            "team_id": team_id,
            "team_name": team.name,
            "active_sessions": team.active_sessions,
            "documents": len(team.documents),
            "shared_contexts": len(team.shared_contexts),
            "collaborative_decisions": len(team.collaborative_decisions),
            "created_at": team.created_at,
            "last_activity": team.last_activity,
        }

# Global collaboration tracker
collaboration_tracker = CollaborationTracker()

def get_or_create_team(team_id: str, team_name: str = "Default Team") -> TeamContext:
    """Get or create a team."""
    return collaboration_tracker.get_or_create_team(team_id, team_name)

def add_session_to_team(session_id: str, team_id: str) -> None:
    """Add session to team."""
    collaboration_tracker.add_session_to_team(session_id, team_id)

def track_document(
    team_id: str,
    doc_id: str,
    title: str,
    doc_type: str,
    session_id: str,
    url: Optional[str] = None,
    excerpt: str = ""
) -> DocumentReference:
    """Track a document."""
    return collaboration_tracker.track_document(team_id, doc_id, title, doc_type, session_id, url, excerpt)

def get_team_context_for_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get team context for session."""
    return collaboration_tracker.get_team_context_for_session(session_id)
