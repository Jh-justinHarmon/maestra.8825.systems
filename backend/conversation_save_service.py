"""
Conversation Save Service - Unified save mechanism for Maestra

Handles:
1. Save button clicks in Maestra UI
2. "Save this convo" NL triggers in Cascade
3. Captures to 8825 Library via unified_capture
4. Generates metadata and verification
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ConversationMessage:
    """Single message in conversation"""
    role: str  # user, assistant, system
    content: str
    timestamp: str  # ISO 8601
    source: str  # maestra, cascade, chatgpt, claude, etc.


@dataclass
class ConversationMetadata:
    """Conversation metadata for save"""
    conversation_id: str
    title: str
    created_at: str
    updated_at: str
    source_platform: str  # maestra, cascade, chatgpt, claude
    message_count: int
    tags: List[str]
    user_id: Optional[str] = None
    session_id: Optional[str] = None


class ConversationSaveService:
    """
    Unified conversation save service
    
    Handles saving conversations from any platform to 8825 Library
    with full metadata and verification.
    """
    
    def __init__(self, library_path: Optional[str] = None):
        """
        Initialize save service
        
        Args:
            library_path: Path to 8825_core/library directory
        """
        self.library_path = Path(library_path) if library_path else self._find_library_path()
        self.unified_capture = self._load_unified_capture()
        logger.info(f"ConversationSaveService initialized with library at {self.library_path}")
    
    def _find_library_path(self) -> Path:
        """Find 8825_core/library directory"""
        candidates = [
            Path.home() / "Hammer Consulting Dropbox/Justin Harmon/8825-Team/users/justin_harmon/8825-Jh/8825_core/library",
            Path("/Users/justinharmon/Hammer Consulting Dropbox/Justin Harmon/8825-Team/users/justin_harmon/8825-Jh/8825_core/library"),
            Path.cwd().parent.parent.parent / "8825_core/library",
        ]
        
        for candidate in candidates:
            if (candidate / "unified_capture.py").exists():
                logger.info(f"Found library at {candidate}")
                return candidate
        
        raise FileNotFoundError("Could not find 8825_core/library directory")
    
    def _load_unified_capture(self):
        """Load unified_capture module"""
        import importlib.util
        
        spec = importlib.util.spec_from_file_location(
            "unified_capture",
            self.library_path / "unified_capture.py"
        )
        
        if not spec or not spec.loader:
            raise ImportError("Failed to load unified_capture.py")
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        return module
    
    def save_conversation(
        self,
        conversation_id: str,
        title: str,
        messages: List[Dict[str, Any]],
        source_platform: str = "maestra",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Save conversation to 8825 Library
        
        Args:
            conversation_id: Unique conversation ID
            title: Conversation title
            messages: List of message dicts with role, content, timestamp
            source_platform: Platform (maestra, cascade, chatgpt, claude)
            metadata: Optional additional metadata
            
        Returns:
            Save result with entry_id and verification_query
        """
        try:
            # Build conversation envelope
            conversation_data = {
                "conversation_id": conversation_id,
                "title": title,
                "source_platform": source_platform,
                "saved_at": datetime.utcnow().isoformat(),
                "message_count": len(messages),
                "messages": messages,
            }
            
            if metadata:
                conversation_data["metadata"] = metadata
            
            # Determine tags based on platform
            tags = ["conversation", source_platform]
            if metadata and "tags" in metadata:
                tags.extend(metadata["tags"])
            
            # Capture to library
            result = self.unified_capture.capture(
                content=json.dumps(conversation_data, indent=2),
                source=source_platform,
                capture_type="conversation",
                metadata={
                    "conversation_id": conversation_id,
                    "title": title,
                    "platform": source_platform,
                    "message_count": len(messages),
                    "tags": tags,
                },
                library_scope="personal"
            )
            
            if not result.get("success"):
                logger.error(f"Save failed for {conversation_id}: {result}")
                return {
                    "success": False,
                    "error": "Save failed",
                    "conversation_id": conversation_id,
                }
            
            logger.info(
                f"Saved conversation {conversation_id} ({source_platform}) "
                f"to library entry {result.get('entry_id')}"
            )
            
            return {
                "success": True,
                "conversation_id": conversation_id,
                "entry_id": result.get("entry_id"),
                "verification_query": result.get("verification_query"),
                "evidence": result.get("evidence"),
                "message_count": len(messages),
            }
            
        except Exception as e:
            logger.error(f"Conversation save failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "conversation_id": conversation_id,
            }
    
    def save_from_maestra(
        self,
        conversation_id: str,
        title: str,
        messages: List[Dict[str, Any]],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Save conversation from Maestra UI
        
        Args:
            conversation_id: Conversation ID
            title: Conversation title
            messages: List of messages
            user_id: Optional user ID
            session_id: Optional session ID
            
        Returns:
            Save result
        """
        metadata = {}
        if user_id:
            metadata["user_id"] = user_id
        if session_id:
            metadata["session_id"] = session_id
        
        return self.save_conversation(
            conversation_id=conversation_id,
            title=title,
            messages=messages,
            source_platform="maestra",
            metadata=metadata,
        )
    
    def save_from_cascade(
        self,
        conversation_id: str,
        title: str,
        messages: List[Dict[str, Any]],
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Save conversation from Cascade NL trigger
        
        Args:
            conversation_id: Conversation ID
            title: Conversation title
            messages: List of messages
            user_id: Optional user ID
            
        Returns:
            Save result
        """
        metadata = {"triggered_by": "cascade_nl"}
        if user_id:
            metadata["user_id"] = user_id
        
        return self.save_conversation(
            conversation_id=conversation_id,
            title=title,
            messages=messages,
            source_platform="cascade",
            metadata=metadata,
        )
    
    def save_from_external_llm(
        self,
        conversation_id: str,
        title: str,
        messages: List[Dict[str, Any]],
        llm_platform: str,  # chatgpt, claude, gemini, etc.
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Save conversation from external LLM (ChatGPT, Claude, etc.)
        
        Args:
            conversation_id: Conversation ID
            title: Conversation title
            messages: List of messages
            llm_platform: LLM platform name
            user_id: Optional user ID
            
        Returns:
            Save result
        """
        metadata = {"llm_platform": llm_platform}
        if user_id:
            metadata["user_id"] = user_id
        
        return self.save_conversation(
            conversation_id=conversation_id,
            title=title,
            messages=messages,
            source_platform=llm_platform,
            metadata=metadata,
        )


# Global service instance
_service = None


def get_save_service(library_path: Optional[str] = None) -> ConversationSaveService:
    """Get or create global save service instance"""
    global _service
    if _service is None:
        _service = ConversationSaveService(library_path)
    return _service


def save_conversation_from_maestra(
    conversation_id: str,
    title: str,
    messages: List[Dict[str, Any]],
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convenience function: Save from Maestra UI
    
    Args:
        conversation_id: Conversation ID
        title: Conversation title
        messages: List of messages
        user_id: Optional user ID
        session_id: Optional session ID
        
    Returns:
        Save result with entry_id and verification
    """
    service = get_save_service()
    return service.save_from_maestra(
        conversation_id=conversation_id,
        title=title,
        messages=messages,
        user_id=user_id,
        session_id=session_id,
    )


def save_conversation_from_cascade(
    conversation_id: str,
    title: str,
    messages: List[Dict[str, Any]],
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convenience function: Save from Cascade NL trigger
    
    Args:
        conversation_id: Conversation ID
        title: Conversation title
        messages: List of messages
        user_id: Optional user ID
        
    Returns:
        Save result with entry_id and verification
    """
    service = get_save_service()
    return service.save_from_cascade(
        conversation_id=conversation_id,
        title=title,
        messages=messages,
        user_id=user_id,
    )
