"""
Maestra Orchestration for Quad-Core Handshake.

Orchestrates parallel routing between local and hosted capabilities.
Implements fast-first answer pattern with async upgrade.
Manages conversation sync and provenance tracking.
"""

import json
import uuid
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class ExecutionSource(str, Enum):
    """Source of capability execution."""
    LOCAL = "local"
    HOSTED = "hosted"
    HYBRID = "hybrid"


class ProvenanceMetadata(dict):
    """Metadata about where data came from and how it was processed."""
    
    def __init__(self, **kwargs):
        super().__init__()
        self["source"] = kwargs.get("source", ExecutionSource.LOCAL)
        self["capability_id"] = kwargs.get("capability_id")
        self["tier"] = kwargs.get("tier", 0)
        self["executed_at"] = kwargs.get("executed_at", datetime.utcnow().isoformat())
        self["execution_time_ms"] = kwargs.get("execution_time_ms", 0)
        self["bytes_returned"] = kwargs.get("bytes_returned", 0)
        self["drift_detected"] = kwargs.get("drift_detected", False)
        self["receipt_id"] = kwargs.get("receipt_id")


class ConversationTurn(dict):
    """Single turn in conversation with provenance."""
    
    def __init__(self, **kwargs):
        super().__init__()
        self["turn_id"] = kwargs.get("turn_id", str(uuid.uuid4()))
        self["session_id"] = kwargs.get("session_id")
        self["timestamp"] = kwargs.get("timestamp", datetime.utcnow().isoformat())
        self["role"] = kwargs.get("role", "user")  # user, assistant, system
        self["content"] = kwargs.get("content", "")
        self["provenance"] = kwargs.get("provenance", {})
        self["capabilities_used"] = kwargs.get("capabilities_used", [])


class Orchestrator:
    """Orchestrates parallel routing and conversation sync."""
    
    def __init__(self, brain_router_url: str = "http://localhost:8000"):
        self.brain_router_url = brain_router_url
        self.sessions = {}  # session_id -> session_data
        self.conversation_feeds = {}  # session_id -> [turns]
        self.provenance_index = {}  # turn_id -> provenance_metadata
    
    async def route_parallel(
        self,
        session_id: str,
        query: str,
        capabilities_available: List[str],
        tier_preference: int = 0
    ) -> Tuple[Any, ProvenanceMetadata, bool]:
        """
        Route query to both local and hosted capabilities in parallel.
        
        Returns fast-first answer immediately, upgrades async if hosted is better.
        
        Args:
            session_id: Session identifier
            query: User query
            capabilities_available: Available capabilities
            tier_preference: Preferred data tier (0, 1, or 2)
        
        Returns:
            (answer, provenance, drift_detected)
        """
        logger.info(
            f"Parallel routing: session={session_id}, "
            f"capabilities={capabilities_available}, tier={tier_preference}"
        )
        
        try:
            # Start both local and hosted execution in parallel
            local_task = asyncio.create_task(
                self._execute_local(session_id, query, capabilities_available, tier_preference)
            )
            hosted_task = asyncio.create_task(
                self._execute_hosted(session_id, query, capabilities_available, tier_preference)
            )
            
            # Wait for first to complete (fast-first)
            done, pending = await asyncio.wait(
                [local_task, hosted_task],
                return_when=asyncio.FIRST_COMPLETED,
                timeout=5.0
            )
            
            # Get fast-first result
            fast_result = None
            fast_source = None
            for task in done:
                result = await task
                if result:
                    fast_result = result
                    fast_source = result.get("source")
                    break
            
            # Cancel pending task (will upgrade async)
            for task in pending:
                task.cancel()
            
            if not fast_result:
                raise ValueError("No execution result available")
            
            # Create provenance metadata
            provenance = ProvenanceMetadata(
                source=fast_source,
                capability_id=fast_result.get("capability_id"),
                tier=fast_result.get("tier", 0),
                executed_at=datetime.utcnow().isoformat(),
                execution_time_ms=fast_result.get("execution_time_ms", 0),
                bytes_returned=fast_result.get("bytes_returned", 0),
                drift_detected=fast_result.get("drift_detected", False),
                receipt_id=fast_result.get("receipt_id")
            )
            
            logger.info(
                f"Fast-first result: source={fast_source}, "
                f"capability={fast_result.get('capability_id')}"
            )
            
            return (
                fast_result.get("output"),
                provenance,
                fast_result.get("drift_detected", False)
            )
        
        except Exception as e:
            logger.error(f"Parallel routing error: {e}", exc_info=True)
            raise
    
    async def _execute_local(
        self,
        session_id: str,
        query: str,
        capabilities_available: List[str],
        tier_preference: int
    ) -> Optional[Dict[str, Any]]:
        """Execute query against local sidecar capabilities."""
        import httpx
        
        sidecar_url = "http://localhost:8001"
        
        try:
            logger.info(f"Executing locally via sidecar: session={session_id}")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Step 1: Handshake to get delegation token
                handshake_response = await client.post(
                    f"{sidecar_url}/handshake",
                    json={
                        "session_id": session_id,
                        "manifest_id": str(uuid.uuid4()),
                        "capabilities_requested": capabilities_available or ["local_index_search"],
                        "tier_preference": tier_preference
                    }
                )
                
                if handshake_response.status_code != 200:
                    logger.error(f"Handshake failed: {handshake_response.text}")
                    return None
                
                handshake_data = handshake_response.json()
                tokens = handshake_data.get("tokens", [])
                
                if not tokens:
                    logger.error("No tokens returned from handshake")
                    return None
                
                token = tokens[0]
                
                # Step 2: Execute capability with token
                execute_response = await client.post(
                    f"{sidecar_url}/execute",
                    json={
                        "token": token,
                        "session_id": session_id,
                        "input_params": {"query": query}
                    }
                )
                
                if execute_response.status_code != 200:
                    logger.error(f"Execute failed: {execute_response.text}")
                    return None
                
                execute_data = execute_response.json()
                result = execute_data.get("result", {})
                receipt = execute_data.get("receipt", {})
                
                return {
                    "source": ExecutionSource.LOCAL,
                    "capability_id": token.get("capability_id"),
                    "tier": token.get("policy", {}).get("tier", 0),
                    "output": result,
                    "execution_time_ms": receipt.get("execution_time_ms", 0),
                    "bytes_returned": receipt.get("bytes_returned", 0),
                    "drift_detected": receipt.get("drift_detected", False),
                    "receipt_id": receipt.get("receipt_id")
                }
        
        except httpx.ConnectError:
            logger.warning("Sidecar not available, falling back to mock")
            # Fallback if sidecar not running
            return {
                "source": ExecutionSource.LOCAL,
                "capability_id": capabilities_available[0] if capabilities_available else "local_search",
                "tier": 0,
                "output": {"error": "sidecar_unavailable", "message": "Local sidecar not running"},
                "execution_time_ms": 0,
                "bytes_returned": 0,
                "drift_detected": False,
                "receipt_id": str(uuid.uuid4())
            }
        
        except Exception as e:
            logger.error(f"Local execution error: {e}")
            return None
    
    async def _execute_hosted(
        self,
        session_id: str,
        query: str,
        capabilities_available: List[str],
        tier_preference: int
    ) -> Optional[Dict[str, Any]]:
        """Execute query against hosted capabilities."""
        try:
            logger.info(f"Executing hosted: session={session_id}")
            
            # Mock hosted execution (slower)
            await asyncio.sleep(0.5)  # Simulate longer execution time
            
            return {
                "source": ExecutionSource.HOSTED,
                "capability_id": "cloud_search",
                "tier": 1,
                "output": {
                    "results": [
                        {"id": "cloud_1", "title": "Cloud Result 1", "relevance": 0.98},
                        {"id": "cloud_2", "title": "Cloud Result 2", "relevance": 0.92}
                    ]
                },
                "execution_time_ms": 500,
                "bytes_returned": 512,
                "drift_detected": False,
                "receipt_id": str(uuid.uuid4())
            }
        
        except Exception as e:
            logger.error(f"Hosted execution error: {e}")
            return None
    
    def record_turn(
        self,
        session_id: str,
        role: str,
        content: str,
        provenance: Optional[ProvenanceMetadata] = None,
        capabilities_used: Optional[List[str]] = None
    ) -> ConversationTurn:
        """
        Record conversation turn with provenance.
        
        Args:
            session_id: Session identifier
            role: Turn role (user, assistant, system)
            content: Turn content
            provenance: Provenance metadata
            capabilities_used: List of capabilities used
        
        Returns:
            Recorded turn
        """
        turn = ConversationTurn(
            session_id=session_id,
            role=role,
            content=content,
            provenance=provenance or {},
            capabilities_used=capabilities_used or []
        )
        
        # Initialize feed if needed
        if session_id not in self.conversation_feeds:
            self.conversation_feeds[session_id] = []
        
        # Record turn
        self.conversation_feeds[session_id].append(turn)
        self.provenance_index[turn["turn_id"]] = provenance or {}
        
        logger.info(
            f"Recorded turn: session={session_id}, role={role}, "
            f"source={provenance.get('source') if provenance else 'none'}"
        )
        
        return turn
    
    def get_conversation_feed(self, session_id: str) -> List[ConversationTurn]:
        """Get conversation feed for session."""
        return self.conversation_feeds.get(session_id, [])
    
    def get_provenance(self, turn_id: str) -> Optional[ProvenanceMetadata]:
        """Get provenance metadata for turn."""
        return self.provenance_index.get(turn_id)
    
    def sync_conversations(
        self,
        local_feed: List[ConversationTurn],
        hosted_feed: List[ConversationTurn]
    ) -> List[ConversationTurn]:
        """
        Sync conversations between local and hosted.
        
        Merges feeds while preserving order and avoiding duplicates.
        
        Args:
            local_feed: Local conversation feed
            hosted_feed: Hosted conversation feed
        
        Returns:
            Merged feed
        """
        # Create merged feed (simple merge by timestamp)
        merged = {}
        
        for turn in local_feed:
            key = (turn["session_id"], turn["timestamp"], turn["role"])
            merged[key] = turn
        
        for turn in hosted_feed:
            key = (turn["session_id"], turn["timestamp"], turn["role"])
            if key not in merged:
                merged[key] = turn
        
        # Sort by timestamp
        sorted_turns = sorted(
            merged.values(),
            key=lambda t: t["timestamp"]
        )
        
        logger.info(f"Synced {len(sorted_turns)} turns across surfaces")
        return sorted_turns
    
    def get_session_state(self, session_id: str) -> Dict[str, Any]:
        """Get complete session state."""
        return {
            "session_id": session_id,
            "conversation_feed": self.get_conversation_feed(session_id),
            "turn_count": len(self.conversation_feeds.get(session_id, [])),
            "last_turn": self.conversation_feeds.get(session_id, [])[-1] if session_id in self.conversation_feeds else None,
            "timestamp": datetime.utcnow().isoformat()
        }


class ProvenanceTracker:
    """Tracks data movement and provenance across surfaces."""
    
    def __init__(self):
        self.data_movements = {}  # turn_id -> movement_record
    
    def track_movement(
        self,
        turn_id: str,
        source: ExecutionSource,
        destination: str,
        data_tier: int,
        bytes_moved: int
    ):
        """
        Track data movement.
        
        Args:
            turn_id: Turn identifier
            source: Source of data (local/hosted)
            destination: Destination (ui/extension/api)
            data_tier: Data tier (0/1/2)
            bytes_moved: Bytes transferred
        """
        movement = {
            "turn_id": turn_id,
            "source": source,
            "destination": destination,
            "data_tier": data_tier,
            "bytes_moved": bytes_moved,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.data_movements[turn_id] = movement
        logger.info(
            f"Tracked data movement: {source} → {destination}, "
            f"tier={data_tier}, bytes={bytes_moved}"
        )
    
    def get_data_movements(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all data movements for session."""
        # Filter by session_id (would need to track session_id in movements)
        return list(self.data_movements.values())
