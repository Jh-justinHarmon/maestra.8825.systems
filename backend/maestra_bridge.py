#!/usr/bin/env python3
"""
Maestra Bridge
Integrates Maestra advisor into Conversation Hub for multi-surface platform.
Handles: session routing, context sharing, response capture, auto-library integration.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

try:
    from .hub import ConversationHub
    from .models import MessageRole, Message, Conversation, ConversationMeta
    from .capture_bridge import CaptureBridge
except ImportError:
    from hub import ConversationHub
    from models import MessageRole, Message, Conversation, ConversationMeta
    from capture_bridge import CaptureBridge

logger = logging.getLogger(__name__)


class MaestraBridge:
    """Bridge Maestra advisor into Conversation Hub for multi-surface integration"""
    
    def __init__(self):
        self.hub = ConversationHub()
        self.capture = CaptureBridge()
        self.maestra_api_base = "https://maestra-backend-8825-systems.fly.dev"
    
    def ask_maestra(
        self,
        conversation_id: str,
        question: str,
        surface: str = "web",
        auto_capture: bool = True
    ) -> Dict[str, Any]:
        """
        Ask Maestra a question within a conversation context.
        
        Args:
            conversation_id: Conversation to add question/answer to
            question: Question to ask Maestra
            surface: Surface origin (web, extension, ios)
            auto_capture: Auto-capture to Library after response
        
        Returns:
            {
                "success": bool,
                "message_id": str,  # ID of assistant response message
                "answer": str,
                "sources": List[Dict],
                "trace_id": str,
                "error": str (if failed)
            }
        """
        try:
            # 1. Load conversation
            conversation = self.hub.get_conversation(conversation_id)
            if not conversation:
                return {
                    "success": False,
                    "error": f"Conversation not found: {conversation_id}"
                }
            
            logger.info(f"[MaestraBridge] Asking Maestra in conversation: {conversation_id}")
            
            # 2. Add user question to conversation
            user_msg = Message(
                role=MessageRole.USER,
                text=question,
                timestamp=datetime.utcnow().isoformat(),
                surface=surface
            )
            conversation.messages.append(user_msg)
            
            # 3. Build context from conversation history (last 5 messages)
            conversation_history = [
                {
                    "role": "user" if msg.role == MessageRole.USER else "assistant",
                    "content": msg.text
                }
                for msg in conversation.messages[-5:]
            ]
            
            # 4. Call Maestra backend
            response = self._call_maestra_backend(
                session_id=conversation_id,
                question=question,
                conversation_history=conversation_history,
                surface=surface
            )
            
            if not response.get("success"):
                return {
                    "success": False,
                    "error": response.get("error", "Maestra backend error")
                }
            
            # 5. Add assistant response to conversation
            assistant_msg = Message(
                role=MessageRole.ASSISTANT,
                text=response["answer"],
                timestamp=datetime.utcnow().isoformat(),
                surface=surface,
                metadata={
                    "maestra_trace_id": response.get("trace_id"),
                    "maestra_sources": response.get("sources", []),
                    "maestra_mode": response.get("mode", "quick")
                }
            )
            conversation.messages.append(assistant_msg)
            
            # 6. Update conversation metadata
            conversation.meta.surfaces = list(set(conversation.meta.surfaces or []) | {surface})
            conversation.meta.updated_at = datetime.utcnow().isoformat()
            
            # 7. Save conversation
            self.hub._save_conversation(conversation)
            self.hub._update_index(conversation)
            
            logger.info(f"[MaestraBridge] Added Maestra response to conversation")
            
            # 8. Auto-capture if enabled
            if auto_capture:
                capture_result = self.capture.capture_conversation(
                    conversation_id=conversation_id,
                    use_pattern_first=True,
                    auto_approve=True
                )
                logger.info(f"[MaestraBridge] Auto-capture result: {capture_result.get('success')}")
            
            return {
                "success": True,
                "message_id": assistant_msg.id,
                "answer": response["answer"],
                "sources": response.get("sources", []),
                "trace_id": response.get("trace_id"),
                "conversation_id": conversation_id
            }
        
        except Exception as e:
            logger.error(f"[MaestraBridge] ask_maestra failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _call_maestra_backend(
        self,
        session_id: str,
        question: str,
        conversation_history: List[Dict],
        surface: str
    ) -> Dict[str, Any]:
        """Call Maestra backend API"""
        import requests
        
        try:
            url = f"{self.maestra_api_base}/api/maestra/advisor/ask"
            
            payload = {
                "session_id": session_id,
                "question": question,
                "mode": "quick",
                "context_hints": [],
                "client_context": {
                    "conversation_history": conversation_history,
                    "surface": surface,
                    "source": "conversation_hub"
                }
            }
            
            logger.info(f"[MaestraBridge] Calling {url}")
            
            response = requests.post(
                url,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Backend returned {response.status_code}: {response.text[:200]}"
                }
            
            data = response.json()
            
            return {
                "success": True,
                "answer": data.get("answer", ""),
                "sources": data.get("sources", []),
                "trace_id": data.get("trace_id"),
                "mode": data.get("mode", "quick")
            }
        
        except requests.Timeout:
            return {
                "success": False,
                "error": "Maestra backend timeout (30s)"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Backend call failed: {str(e)}"
            }
    
    def get_maestra_context(
        self,
        conversation_id: str,
        max_messages: int = 10
    ) -> Dict[str, Any]:
        """
        Get conversation context suitable for Maestra.
        Used by other surfaces to understand conversation state.
        
        Returns:
            {
                "conversation_id": str,
                "topic": str,
                "surface_origins": List[str],
                "message_count": int,
                "recent_messages": List[Dict],
                "key_decisions": List[str],
                "open_questions": List[str]
            }
        """
        try:
            conversation = self.hub.get_conversation(conversation_id)
            if not conversation:
                return {"success": False, "error": "Conversation not found"}
            
            # Extract recent messages
            recent_messages = [
                {
                    "role": "user" if msg.role == MessageRole.USER else "assistant",
                    "content": msg.text[:200],  # Truncate for context
                    "timestamp": msg.timestamp if hasattr(msg, 'timestamp') else msg.at if hasattr(msg, 'at') else ""
                }
                for msg in conversation.messages[-max_messages:]
            ]
            
            # Extract key decisions and questions
            key_decisions = []
            open_questions = []
            
            for msg in conversation.messages:
                text_lower = msg.text.lower()
                if any(word in text_lower for word in ["decided", "will", "should", "approved"]):
                    key_decisions.append(msg.text[:100])
                if "?" in msg.text:
                    open_questions.append(msg.text[:100])
            
            return {
                "success": True,
                "conversation_id": conversation_id,
                "topic": conversation.topic or "Untitled",
                "surface_origins": conversation.meta.surfaces or [],
                "message_count": len(conversation.messages),
                "recent_messages": recent_messages,
                "key_decisions": list(set(key_decisions))[:5],
                "open_questions": list(set(open_questions))[:5]
            }
        
        except Exception as e:
            logger.error(f"[MaestraBridge] get_maestra_context failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def sync_to_surface(
        self,
        conversation_id: str,
        target_surface: str
    ) -> Dict[str, Any]:
        """
        Sync conversation to another surface (e.g., web → extension).
        Enables cross-surface continuity.
        
        Returns:
            {
                "success": bool,
                "synced_messages": int,
                "error": str (if failed)
            }
        """
        try:
            conversation = self.hub.get_conversation(conversation_id)
            if not conversation:
                return {
                    "success": False,
                    "error": "Conversation not found"
                }
            
            # Mark surface as active
            if target_surface not in (conversation.meta.surfaces or []):
                conversation.meta.surfaces = list(set(conversation.meta.surfaces or []) | {target_surface})
                self.hub._save_conversation(conversation)
            
            logger.info(f"[MaestraBridge] Synced conversation to {target_surface}")
            
            return {
                "success": True,
                "synced_messages": len(conversation.messages),
                "target_surface": target_surface
            }
        
        except Exception as e:
            logger.error(f"[MaestraBridge] sync_to_surface failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
