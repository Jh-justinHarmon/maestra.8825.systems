"""
Advisor Integration with Quad-Core Orchestration.

Updates Maestra advisor to use orchestrator for parallel routing and conversation sync.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio

from orchestration import Orchestrator, ProvenanceTracker, ExecutionSource

logger = logging.getLogger(__name__)


class OrchestratedAdvisor:
    """Advisor with quad-core orchestration support."""
    
    def __init__(self, orchestrator: Optional[Orchestrator] = None):
        self.orchestrator = orchestrator or Orchestrator()
        self.provenance_tracker = ProvenanceTracker()
        self.session_capabilities = {}  # session_id -> capabilities_available
    
    async def process_question_with_orchestration(
        self,
        session_id: str,
        question: str,
        capabilities_available: Optional[List[str]] = None,
        tier_preference: int = 0
    ) -> Dict[str, Any]:
        """
        Process user question with parallel routing.
        
        Args:
            session_id: Session identifier
            question: User question
            capabilities_available: Available capabilities (defaults to all)
            tier_preference: Preferred data tier (0, 1, or 2)
        
        Returns:
            Response with provenance metadata
        """
        logger.info(
            f"Processing question with orchestration: "
            f"session={session_id}, tier={tier_preference}"
        )
        
        try:
            # Default capabilities if not specified
            if not capabilities_available:
                capabilities_available = [
                    "local_index_search",
                    "local_file_read",
                    "cloud_search"
                ]
            
            # Record user turn
            user_turn = self.orchestrator.record_turn(
                session_id=session_id,
                role="user",
                content=question,
                capabilities_used=capabilities_available
            )
            
            # Route in parallel
            answer, provenance, drift_detected = await self.orchestrator.route_parallel(
                session_id=session_id,
                query=question,
                capabilities_available=capabilities_available,
                tier_preference=tier_preference
            )
            
            # Record assistant turn with provenance
            assistant_turn = self.orchestrator.record_turn(
                session_id=session_id,
                role="assistant",
                content=str(answer),
                provenance=provenance,
                capabilities_used=[provenance.get("capability_id")]
            )
            
            # Track data movement
            self.provenance_tracker.track_movement(
                turn_id=assistant_turn["turn_id"],
                source=ExecutionSource(provenance.get("source", ExecutionSource.LOCAL)),
                destination="ui",
                data_tier=provenance.get("tier", 0),
                bytes_moved=provenance.get("bytes_returned", 0)
            )
            
            return {
                "answer": answer,
                "turn_id": assistant_turn["turn_id"],
                "provenance": provenance,
                "drift_detected": drift_detected,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Orchestration error: {e}", exc_info=True)
            raise
    
    def get_conversation_with_provenance(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Get conversation feed with full provenance information.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Conversation with provenance metadata
        """
        feed = self.orchestrator.get_conversation_feed(session_id)
        
        # Enrich with provenance
        enriched_feed = []
        for turn in feed:
            turn_copy = dict(turn)
            turn_copy["provenance"] = self.orchestrator.get_provenance(turn["turn_id"])
            enriched_feed.append(turn_copy)
        
        return {
            "session_id": session_id,
            "turns": enriched_feed,
            "turn_count": len(enriched_feed),
            "data_movements": self.provenance_tracker.get_data_movements(session_id),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def sync_across_surfaces(
        self,
        session_id: str,
        local_feed: List[Dict[str, Any]],
        hosted_feed: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Sync conversation across local and hosted surfaces.
        
        Args:
            session_id: Session identifier
            local_feed: Local conversation feed
            hosted_feed: Hosted conversation feed
        
        Returns:
            Merged and synced feed
        """
        logger.info(f"Syncing conversations: session={session_id}")
        
        merged = self.orchestrator.sync_conversations(local_feed, hosted_feed)
        
        # Update orchestrator's feed
        self.orchestrator.conversation_feeds[session_id] = merged
        
        return merged
    
    def get_session_state(self, session_id: str) -> Dict[str, Any]:
        """Get complete session state with provenance."""
        state = self.orchestrator.get_session_state(session_id)
        state["data_movements"] = self.provenance_tracker.get_data_movements(session_id)
        return state


# Integration with existing advisor
class AdvisorWithOrchestration:
    """Wraps existing advisor with orchestration capabilities."""
    
    def __init__(self, original_advisor, orchestrator: Optional[Orchestrator] = None):
        self.original_advisor = original_advisor
        self.orchestrated = OrchestratedAdvisor(orchestrator)
    
    async def ask(
        self,
        session_id: str,
        question: str,
        use_orchestration: bool = True,
        capabilities_available: Optional[List[str]] = None,
        tier_preference: int = 0
    ) -> Dict[str, Any]:
        """
        Ask advisor a question, optionally with orchestration.
        
        Args:
            session_id: Session identifier
            question: User question
            use_orchestration: Whether to use quad-core orchestration
            capabilities_available: Available capabilities
            tier_preference: Preferred data tier
        
        Returns:
            Response with optional provenance
        """
        if use_orchestration:
            return await self.orchestrated.process_question_with_orchestration(
                session_id=session_id,
                question=question,
                capabilities_available=capabilities_available,
                tier_preference=tier_preference
            )
        else:
            # Fall back to original advisor
            return await self.original_advisor.ask(session_id, question)
    
    def get_conversation(self, session_id: str, with_provenance: bool = True) -> Dict[str, Any]:
        """Get conversation, optionally with provenance."""
        if with_provenance:
            return self.orchestrated.get_conversation_with_provenance(session_id)
        else:
            return self.original_advisor.get_conversation(session_id)
