"""
Session Handler
Manages session creation, retrieval, and updates
"""
import uuid
from datetime import datetime
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)

# In-memory session storage (temporary - will be replaced with database)
_sessions: Dict[str, dict] = {}
_device_to_session: Dict[str, str] = {}


def get_or_create_session(device_id: str, surface: str, user_id: str = "anonymous") -> dict:
    """
    Get existing session for device or create new one
    
    Args:
        device_id: Stable device identifier
        surface: Surface name (web_app, browser_extension, figma_v2)
        user_id: User identifier
    
    Returns:
        Session dictionary with all required fields
    """
    now = datetime.utcnow().isoformat() + "Z"
    
    # Check if device has an active session
    if device_id in _device_to_session:
        session_id = _device_to_session[device_id]
        session = _sessions.get(session_id)
        
        if session:
            # Update existing session
            if surface not in session["surfaces"]:
                session["surfaces"].append(surface)
            session["last_active_surface"] = surface
            session["last_active_on"] = now
            
            logger.info(f"[SESSION] Resumed session {session_id} for device {device_id} on {surface}")
            
            return {
                **session,
                "is_new_session": False
            }
    
    # Create new session
    session_id = str(uuid.uuid4())
    session = {
        "session_id": session_id,
        "device_id": device_id,
        "user_id": user_id,
        "surfaces": [surface],
        "last_active_surface": surface,
        "started_on": now,
        "last_active_on": now
    }
    
    # Store session
    _sessions[session_id] = session
    _device_to_session[device_id] = session_id
    
    logger.info(f"[SESSION] Created new session {session_id} for device {device_id} on {surface}")
    
    return {
        **session,
        "is_new_session": True
    }


def update_session_activity(session_id: str, surface: str) -> None:
    """
    Update session last activity timestamp
    
    Args:
        session_id: Session identifier
        surface: Surface making the request
    """
    session = _sessions.get(session_id)
    if session:
        now = datetime.utcnow().isoformat() + "Z"
        session["last_active_on"] = now
        session["last_active_surface"] = surface
        
        if surface not in session["surfaces"]:
            session["surfaces"].append(surface)


def get_session(session_id: str) -> Optional[dict]:
    """
    Get session by ID
    
    Args:
        session_id: Session identifier
    
    Returns:
        Session dictionary or None if not found
    """
    return _sessions.get(session_id)
