"""State Synchronization - Bidirectional conversation sync between backends"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import httpx

logger = logging.getLogger(__name__)


@dataclass
class SyncPayload:
    """
    Payload for syncing conversations between backends
    
    Uses Last-Write-Wins conflict resolution based on message timestamps
    """
    
    # Sync metadata
    sync_id: str  # Unique sync operation ID
    source_backend_id: str
    target_backend_id: str
    timestamp: str  # ISO 8601
    
    # Conversation data
    conversations: List[Dict[str, Any]]  # List of conversation envelopes
    
    def to_dict(self) -> Dict:
        """Export as dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "SyncPayload":
        """Create from dictionary"""
        return cls(**data)


class ConversationSyncer:
    """
    Handles bidirectional conversation synchronization between backends
    
    Uses Last-Write-Wins (LWW) conflict resolution:
    - Compare message timestamps
    - Keep the most recent version
    - Mark messages with source_backend for tracking
    """
    
    def __init__(self, conversation_hub, identity, peer_registry):
        """
        Initialize syncer
        
        Args:
            conversation_hub: ConversationHub instance
            identity: BackendIdentity instance
            peer_registry: PeerRegistry instance
        """
        self.hub = conversation_hub
        self.identity = identity
        self.peer_registry = peer_registry
        self._sync_lock = asyncio.Lock()
    
    async def sync_with_peer(self, peer_backend_id: str) -> Dict[str, Any]:
        """
        Sync conversations with a peer backend
        
        Args:
            peer_backend_id: Peer's backend_id
            
        Returns:
            Sync result with statistics
        """
        async with self._sync_lock:
            peer = self.peer_registry.get_peer(peer_backend_id)
            if not peer:
                raise ValueError(f"Peer {peer_backend_id} not registered")
            
            # Get all local conversations
            local_convs = self.hub.list_conversations()
            
            # Create sync payload
            import uuid
            sync_payload = SyncPayload(
                sync_id=f"sync_{uuid.uuid4().hex[:16]}",
                source_backend_id=self.identity.backend_id,
                target_backend_id=peer_backend_id,
                timestamp=datetime.utcnow().isoformat(),
                conversations=[
                    self.hub.get_conversation(conv_id).dict()
                    for conv_id in local_convs
                ]
            )
            
            # Send to peer's /sync endpoint
            # Note: In production, this would use the peer's URL from registry
            # For now, we'll determine URL based on backend type
            peer_url = self._get_peer_url(peer)
            
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{peer_url}/sync",
                        json=sync_payload.to_dict()
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    logger.info(
                        f"Synced with {peer_backend_id}: "
                        f"{result.get('conversations_received', 0)} sent, "
                        f"{result.get('conversations_merged', 0)} received"
                    )
                    
                    return result
            except Exception as e:
                logger.error(f"Sync failed with {peer_backend_id}: {e}")
                raise
    
    def _get_peer_url(self, peer: Dict) -> str:
        """
        Get peer's base URL
        
        Args:
            peer: Peer information
            
        Returns:
            Base URL for peer backend
        """
        backend_id = peer['backend_id']
        
        if backend_id.startswith('local_'):
            return "http://localhost:8825"
        elif backend_id.startswith('hosted_'):
            return "https://maestra-backend-8825-systems.fly.dev"
        else:
            raise ValueError(f"Unknown backend type: {backend_id}")
    
    def merge_conversations(self, incoming_convs: List[Dict]) -> Dict[str, int]:
        """
        Merge incoming conversations using Last-Write-Wins
        
        Args:
            incoming_convs: List of conversation envelopes from peer
            
        Returns:
            Statistics: {merged: int, skipped: int, updated: int}
        """
        stats = {"merged": 0, "skipped": 0, "updated": 0}
        
        for incoming_conv in incoming_convs:
            conv_id = incoming_conv['conversation_id']
            
            try:
                # Check if conversation exists locally
                local_conv = self.hub.get_conversation(conv_id)
                
                # Merge messages using Last-Write-Wins
                merged = self._merge_messages(
                    local_conv.messages,
                    incoming_conv['messages']
                )
                
                if merged:
                    # Update local conversation with merged messages
                    local_conv.messages = merged
                    self.hub._save_conversation(local_conv)
                    stats['updated'] += 1
                else:
                    stats['skipped'] += 1
                    
            except FileNotFoundError:
                # Conversation doesn't exist locally, create it
                from conversation_hub import ConversationEnvelope
                new_conv = ConversationEnvelope(**incoming_conv)
                self.hub._save_conversation(new_conv)
                stats['merged'] += 1
        
        return stats
    
    def _merge_messages(
        self,
        local_messages: List[Dict],
        incoming_messages: List[Dict]
    ) -> Optional[List[Dict]]:
        """
        Merge message lists using Last-Write-Wins
        
        Args:
            local_messages: Local message list
            incoming_messages: Incoming message list
            
        Returns:
            Merged message list, or None if no changes
        """
        # Create message map by message_id
        message_map = {msg['message_id']: msg for msg in local_messages}
        
        changed = False
        
        for incoming_msg in incoming_messages:
            msg_id = incoming_msg['message_id']
            
            if msg_id not in message_map:
                # New message, add it
                message_map[msg_id] = incoming_msg
                changed = True
            else:
                # Message exists, compare timestamps
                local_ts = datetime.fromisoformat(
                    message_map[msg_id].get('timestamp', '1970-01-01T00:00:00')
                )
                incoming_ts = datetime.fromisoformat(
                    incoming_msg.get('timestamp', '1970-01-01T00:00:00')
                )
                
                if incoming_ts > local_ts:
                    # Incoming message is newer, replace
                    message_map[msg_id] = incoming_msg
                    changed = True
        
        if not changed:
            return None
        
        # Sort messages by timestamp
        merged = sorted(
            message_map.values(),
            key=lambda m: m.get('timestamp', '1970-01-01T00:00:00')
        )
        
        return merged


class SyncScheduler:
    """
    Automatic sync scheduler - syncs with all registered peers every N seconds
    """
    
    def __init__(
        self,
        syncer: ConversationSyncer,
        peer_registry,
        interval_seconds: int = 5
    ):
        """
        Initialize scheduler
        
        Args:
            syncer: ConversationSyncer instance
            peer_registry: PeerRegistry instance
            interval_seconds: Sync interval (default: 5 seconds)
        """
        self.syncer = syncer
        self.peer_registry = peer_registry
        self.interval = interval_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the sync scheduler"""
        if self._running:
            logger.warning("Sync scheduler already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._sync_loop())
        logger.info(f"Sync scheduler started (interval: {self.interval}s)")
    
    async def stop(self):
        """Stop the sync scheduler"""
        if not self._running:
            return
        
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("Sync scheduler stopped")
    
    async def _sync_loop(self):
        """Main sync loop"""
        while self._running:
            try:
                # Get all registered peers
                peers = self.peer_registry.list_peers()
                
                # Sync with each peer
                for peer in peers:
                    try:
                        await self.syncer.sync_with_peer(peer['backend_id'])
                    except Exception as e:
                        logger.error(
                            f"Failed to sync with {peer['backend_id']}: {e}"
                        )
                
                # Wait for next interval
                await asyncio.sleep(self.interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Sync loop error: {e}")
                await asyncio.sleep(self.interval)


# Global sync scheduler instance
_sync_scheduler: Optional[SyncScheduler] = None


def get_sync_scheduler() -> Optional[SyncScheduler]:
    """Get global sync scheduler instance"""
    return _sync_scheduler


def set_sync_scheduler(scheduler: SyncScheduler):
    """Set global sync scheduler instance"""
    global _sync_scheduler
    _sync_scheduler = scheduler
