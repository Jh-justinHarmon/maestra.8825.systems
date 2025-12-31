"""
Maestra Backend - Session Manager

Handles session lifecycle and JWT verification for handshake protocol.
Tracks authenticated sessions with local companion capabilities.
"""

import os
import sys
import logging
import time
import jwt
from typing import Optional, List, Dict
from datetime import datetime
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# JWT configuration
JWT_SECRET = os.getenv("COMPANION_JWT_SECRET", "dev-secret-change-in-prod")
JWT_ALGORITHM = "HS256"

# In-memory session store (in production, use Redis or database)
_sessions: Dict[str, Dict] = {}

class SessionCapabilities(BaseModel):
    session_id: str
    library_id: str
    jwt: str
    capabilities: List[str]

class SessionInfo(BaseModel):
    session_id: str
    status: str
    library_id: Optional[str]
    capabilities_enabled: List[str]
    authenticated_at: Optional[str]
    expires_at: Optional[str]

def verify_jwt(token: str) -> Optional[Dict]:
    """
    Verify JWT from local companion.
    
    Returns decoded payload if valid, None if invalid/expired.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        logger.info(f"JWT verified for library: {payload.get('library_id')}")
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT: {e}")
        return None
    except Exception as e:
        logger.error(f"JWT verification error: {e}")
        return None

def register_session(session_id: str, library_id: str, jwt_token: str, capabilities: List[str]) -> SessionInfo:
    """
    Register an authenticated session.
    
    Verifies JWT and stores session info.
    """
    # Verify JWT
    payload = verify_jwt(jwt_token)
    if not payload:
        logger.warning(f"Failed to register session {session_id}: invalid JWT")
        return SessionInfo(
            session_id=session_id,
            status="rejected",
            library_id=None,
            capabilities_enabled=[],
            authenticated_at=None,
            expires_at=None
        )
    
    # Verify library_id matches
    if payload.get("library_id") != library_id:
        logger.warning(f"Library ID mismatch for session {session_id}")
        return SessionInfo(
            session_id=session_id,
            status="rejected",
            library_id=None,
            capabilities_enabled=[],
            authenticated_at=None,
            expires_at=None
        )
    
    # Store session
    _sessions[session_id] = {
        "library_id": library_id,
        "jwt": jwt_token,
        "capabilities": capabilities,
        "authenticated_at": datetime.utcnow().isoformat(),
        "expires_at": payload.get("exp"),
        "status": "authenticated"
    }
    
    logger.info(f"Session {session_id} authenticated with capabilities: {capabilities}")
    
    return SessionInfo(
        session_id=session_id,
        status="authenticated",
        library_id=library_id,
        capabilities_enabled=capabilities,
        authenticated_at=datetime.utcnow().isoformat(),
        expires_at=payload.get("exp")
    )

def get_session(session_id: str) -> Optional[SessionInfo]:
    """Get session info."""
    if session_id not in _sessions:
        return SessionInfo(
            session_id=session_id,
            status="anonymous",
            library_id=None,
            capabilities_enabled=[],
            authenticated_at=None,
            expires_at=None
        )
    
    session = _sessions[session_id]
    return SessionInfo(
        session_id=session_id,
        status=session.get("status", "anonymous"),
        library_id=session.get("library_id"),
        capabilities_enabled=session.get("capabilities", []),
        authenticated_at=session.get("authenticated_at"),
        expires_at=session.get("expires_at")
    )

def has_capability(session_id: str, capability: str) -> bool:
    """Check if session has a specific capability."""
    if session_id not in _sessions:
        return False
    
    session = _sessions[session_id]
    return capability in session.get("capabilities", [])

def get_library_id(session_id: str) -> Optional[str]:
    """Get library ID for authenticated session."""
    if session_id not in _sessions:
        return None
    
    return _sessions[session_id].get("library_id")

def cleanup_expired_sessions():
    """Remove expired sessions (called periodically)."""
    now = datetime.utcnow().timestamp()
    expired = [
        sid for sid, session in _sessions.items()
        if session.get("expires_at") and session["expires_at"] < now
    ]
    
    for sid in expired:
        del _sessions[sid]
        logger.info(f"Cleaned up expired session: {sid}")
    
    return len(expired)
