"""Conversation Hub - In-memory conversation storage for sync protocol"""

import json
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Single message in a conversation"""
    message_id: str
    content: str
    timestamp: str  # ISO 8601
    source_backend: str  # Which backend created this message
    role: str = "user"  # user, assistant, system
    
    def dict(self):
        return asdict(self)


@dataclass
class ConversationEnvelope:
    """Conversation envelope for sync"""
    conversation_id: str
    title: str
    created_at: str  # ISO 8601
    updated_at: str  # ISO 8601
    messages: List[Dict] = field(default_factory=list)
    
    def dict(self):
        return asdict(self)


class ConversationHub:
    """In-memory conversation storage"""
    
    def __init__(self):
        """Initialize conversation hub"""
        self.conversations: Dict[str, ConversationEnvelope] = {}
        logger.info("ConversationHub initialized")
    
    def create_conversation(self, title: str, source_backend: str) -> str:
        """
        Create new conversation
        
        Args:
            title: Conversation title
            source_backend: Backend that created it
            
        Returns:
            Conversation ID
        """
        conv_id = f"conv_{uuid.uuid4().hex[:16]}"
        now = datetime.utcnow().isoformat()
        
        self.conversations[conv_id] = ConversationEnvelope(
            conversation_id=conv_id,
            title=title,
            created_at=now,
            updated_at=now,
            messages=[]
        )
        
        logger.info(f"Created conversation: {conv_id}")
        return conv_id
    
    def add_message(
        self,
        conv_id: str,
        content: str,
        source_backend: str,
        role: str = "user"
    ) -> str:
        """
        Add message to conversation
        
        Args:
            conv_id: Conversation ID
            content: Message content
            source_backend: Backend that created message
            role: Message role (user/assistant)
            
        Returns:
            Message ID
        """
        if conv_id not in self.conversations:
            raise ValueError(f"Conversation not found: {conv_id}")
        
        msg_id = f"msg_{uuid.uuid4().hex[:16]}"
        now = datetime.utcnow().isoformat()
        
        message = {
            "message_id": msg_id,
            "content": content,
            "timestamp": now,
            "source_backend": source_backend,
            "role": role
        }
        
        self.conversations[conv_id].messages.append(message)
        self.conversations[conv_id].updated_at = now
        
        logger.info(f"Added message {msg_id} to {conv_id}")
        return msg_id
    
    def get_conversation(self, conv_id: str) -> ConversationEnvelope:
        """Get conversation by ID"""
        if conv_id not in self.conversations:
            raise FileNotFoundError(f"Conversation not found: {conv_id}")
        return self.conversations[conv_id]
    
    def list_conversations(self) -> List[str]:
        """List all conversation IDs"""
        return list(self.conversations.keys())
    
    def _save_conversation(self, conv: ConversationEnvelope):
        """Save/update conversation"""
        conv.updated_at = datetime.utcnow().isoformat()
        self.conversations[conv.conversation_id] = conv
        logger.info(f"Saved conversation: {conv.conversation_id}")
    
    def get_all_conversations(self) -> List[Dict]:
        """Get all conversations as dicts"""
        return [conv.dict() for conv in self.conversations.values()]


# Global instance
_hub = None


def get_conversation_hub() -> ConversationHub:
    """Get or create global conversation hub"""
    global _hub
    if _hub is None:
        _hub = ConversationHub()
    return _hub
