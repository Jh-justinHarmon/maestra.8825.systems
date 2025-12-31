#!/usr/bin/env python3
"""
Maestra Conversation Hub API
REST endpoints for multi-surface integration.
Surfaces (web, extension, iOS) call these endpoints to ask Maestra within conversations.
"""

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

try:
    from .maestra_bridge import MaestraBridge
except ImportError:
    from maestra_bridge import MaestraBridge

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Maestra Conversation Hub API",
    description="Multi-surface integration for Maestra advisor",
    version="1.0.0"
)

bridge = MaestraBridge()


# ============================================================================
# Request/Response Models
# ============================================================================

class AskMaestraRequest(BaseModel):
    """Ask Maestra within a conversation"""
    conversation_id: str
    question: str
    surface: str = "web"  # web, extension, ios
    auto_capture: bool = True


class AskMaestraResponse(BaseModel):
    """Response from Maestra"""
    success: bool
    message_id: Optional[str] = None
    answer: Optional[str] = None
    sources: Optional[List[Dict]] = None
    trace_id: Optional[str] = None
    conversation_id: Optional[str] = None
    error: Optional[str] = None


class ContextRequest(BaseModel):
    """Get conversation context for Maestra"""
    conversation_id: str
    max_messages: int = 10


class ContextResponse(BaseModel):
    """Conversation context"""
    success: bool
    conversation_id: Optional[str] = None
    topic: Optional[str] = None
    surface_origins: Optional[List[str]] = None
    message_count: Optional[int] = None
    recent_messages: Optional[List[Dict]] = None
    key_decisions: Optional[List[str]] = None
    open_questions: Optional[List[str]] = None
    error: Optional[str] = None


class SyncRequest(BaseModel):
    """Sync conversation to another surface"""
    conversation_id: str
    target_surface: str


class SyncResponse(BaseModel):
    """Sync result"""
    success: bool
    synced_messages: Optional[int] = None
    target_surface: Optional[str] = None
    error: Optional[str] = None


# ============================================================================
# Endpoints
# ============================================================================

@app.post("/ask", response_model=AskMaestraResponse)
async def ask_maestra(request: AskMaestraRequest) -> AskMaestraResponse:
    """
    Ask Maestra a question within a conversation.
    
    - Adds question to conversation
    - Calls Maestra backend with conversation history
    - Adds response to conversation
    - Auto-captures to Library (optional)
    - Returns response with sources and trace ID
    """
    result = bridge.ask_maestra(
        conversation_id=request.conversation_id,
        question=request.question,
        surface=request.surface,
        auto_capture=request.auto_capture
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Failed to ask Maestra")
        )
    
    return AskMaestraResponse(**result)


@app.post("/context", response_model=ContextResponse)
async def get_context(request: ContextRequest) -> ContextResponse:
    """
    Get conversation context for Maestra.
    
    Returns:
    - Recent messages
    - Key decisions
    - Open questions
    - Surface origins
    - Suitable for cross-surface context sharing
    """
    result = bridge.get_maestra_context(
        conversation_id=request.conversation_id,
        max_messages=request.max_messages
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=404,
            detail=result.get("error", "Conversation not found")
        )
    
    return ContextResponse(**result)


@app.post("/sync", response_model=SyncResponse)
async def sync_conversation(request: SyncRequest) -> SyncResponse:
    """
    Sync conversation to another surface.
    
    Enables cross-surface continuity:
    - User starts on web
    - Switches to extension
    - Conversation history is available
    """
    result = bridge.sync_to_surface(
        conversation_id=request.conversation_id,
        target_surface=request.target_surface
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Sync failed")
        )
    
    return SyncResponse(**result)


@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "service": "maestra-conversation-hub-api",
        "version": "1.0.0"
    }


# ============================================================================
# CORS and Middleware
# ============================================================================

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for multi-surface
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8826)
