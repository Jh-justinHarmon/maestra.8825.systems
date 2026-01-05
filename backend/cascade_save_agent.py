"""
Cascade Save Agent - Natural language trigger for conversation saving

Listens for "save this convo" and similar triggers in Cascade
and invokes the unified save service.
"""

import logging
import re
from typing import Dict, Any, Optional, List
from conversation_save_service import save_conversation_from_cascade

logger = logging.getLogger(__name__)


class CascadeSaveAgent:
    """
    Agent that listens for save triggers in Cascade conversations
    
    Recognizes patterns like:
    - "save this convo"
    - "save this conversation"
    - "save conversation"
    - "capture this"
    - "save to library"
    - "archive this"
    """
    
    # Patterns that trigger save
    SAVE_TRIGGERS = [
        r"save\s+(?:this\s+)?convo(?:rsation)?",
        r"save\s+(?:this\s+)?(?:chat|conversation|discussion)",
        r"capture\s+(?:this|the)\s+(?:chat|conversation|convo|discussion)",
        r"archive\s+(?:this|the)\s+(?:chat|conversation|convo|discussion)",
        r"save\s+to\s+library",
        r"store\s+(?:this|the)\s+(?:chat|conversation|convo|discussion)",
        r"preserve\s+(?:this|the)\s+(?:chat|conversation|convo|discussion)",
        r"save\s+(?:the\s+)?(?:chat|conversation|convo|discussion|file)",
    ]
    
    def __init__(self):
        """Initialize the save agent"""
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.SAVE_TRIGGERS]
        logger.info("CascadeSaveAgent initialized")
    
    def should_save(self, message: str) -> bool:
        """
        Check if message contains save trigger
        
        Args:
            message: User message to check
            
        Returns:
            True if save trigger detected
        """
        for pattern in self.compiled_patterns:
            if pattern.search(message):
                logger.info(f"Save trigger detected: {message[:50]}...")
                return True
        return False
    
    def extract_conversation_context(
        self,
        messages: List[Dict[str, Any]],
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extract conversation context for saving
        
        Args:
            messages: List of messages in conversation
            user_id: Optional user ID
            
        Returns:
            Conversation context dict
        """
        if not messages:
            return {
                "conversation_id": "cascade_empty",
                "title": "Empty Conversation",
                "messages": [],
            }
        
        # Generate conversation ID from first message
        first_msg = messages[0].get("content", "")[:50]
        conversation_id = f"cascade_{hash(first_msg) % 10000:04d}"
        
        # Extract title from first user message
        title = "Cascade Conversation"
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                title = content[:60] if content else "Cascade Conversation"
                break
        
        return {
            "conversation_id": conversation_id,
            "title": title,
            "messages": messages,
            "user_id": user_id,
        }
    
    def handle_save_trigger(
        self,
        message: str,
        messages: List[Dict[str, Any]],
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Handle save trigger in Cascade
        
        Args:
            message: Trigger message
            messages: Conversation messages
            user_id: Optional user ID
            
        Returns:
            Save result with entry_id and verification
        """
        try:
            # Check if this is a save trigger
            if not self.should_save(message):
                return {
                    "success": False,
                    "error": "Not a save trigger",
                }
            
            # Extract conversation context
            context = self.extract_conversation_context(messages, user_id)
            
            logger.info(f"Saving conversation from Cascade: {context['conversation_id']}")
            
            # Save to library
            result = save_conversation_from_cascade(
                conversation_id=context["conversation_id"],
                title=context["title"],
                messages=context["messages"],
                user_id=user_id,
            )
            
            if result.get("success"):
                logger.info(f"Cascade save successful: {result.get('entry_id')}")
                return {
                    "success": True,
                    "entry_id": result.get("entry_id"),
                    "verification_query": result.get("verification_query"),
                    "message": f"Conversation saved to library (ID: {result.get('entry_id')})",
                }
            else:
                logger.error(f"Cascade save failed: {result.get('error')}")
                return {
                    "success": False,
                    "error": result.get("error", "Save failed"),
                }
            
        except Exception as e:
            logger.error(f"Cascade save agent error: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    def get_help_text(self) -> str:
        """Get help text for save triggers"""
        return """
Save Trigger Examples:
- "save this convo"
- "save this conversation"
- "capture this chat"
- "archive this discussion"
- "save to library"
- "store this conversation"

Your conversation will be saved to the 8825 Library with full metadata and verification.
"""


# Global agent instance
_agent = None


def get_cascade_save_agent() -> CascadeSaveAgent:
    """Get or create global agent instance"""
    global _agent
    if _agent is None:
        _agent = CascadeSaveAgent()
    return _agent


def handle_cascade_message(
    message: str,
    messages: List[Dict[str, Any]],
    user_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Process Cascade message and handle save triggers
    
    Args:
        message: User message
        messages: Conversation messages
        user_id: Optional user ID
        
    Returns:
        Save result if trigger detected, None otherwise
    """
    agent = get_cascade_save_agent()
    
    if agent.should_save(message):
        return agent.handle_save_trigger(message, messages, user_id)
    
    return None
