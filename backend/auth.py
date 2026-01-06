"""
Memory-Native Auth Module

Handles authentication via K-entry anchors without passwords or tokens.
Enforces mode transitions and device-based access control.
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)

# In-memory session store (replace with Redis in production)
_sessions: Dict[str, Dict] = {}

class AuthSession:
    """Represents an authenticated session"""
    
    def __init__(self, user_id: str, device_type: str, capabilities: List[str]):
        self.user_id = user_id
        self.device_type = device_type
        self.capabilities = capabilities
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.session_id = hashlib.sha256(
            f"{user_id}{device_type}{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:32]
    
    def is_valid(self) -> bool:
        """Check if session is still valid (24h expiry)"""
        return (datetime.utcnow() - self.created_at) < timedelta(hours=24)
    
    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "device_type": self.device_type,
            "capabilities": self.capabilities,
            "created_at": self.created_at.isoformat(),
            "valid": self.is_valid()
        }


async def authenticate_handshake(
    device_fingerprint: str,
    requested_capabilities: List[str]
) -> Optional[Dict]:
    """
    Perform Memory-Native Auth handshake
    
    In production, this would:
    1. Verify device fingerprint against known devices
    2. Check for auth anchor K-entry
    3. Validate capability permissions
    4. Return scoped JWT
    
    For now, returns mock session for development
    """
    
    # Mock implementation - in production, verify against K-entries
    # and device registry
    
    # Registered users who get full capabilities
    registered_users = {
        "justin_harmon": ["read-library", "write-capture", "context-query", "personalization"],
        "becky": ["read-library", "write-capture", "context-query", "personalization"],
    }
    
    # For demo: treat device fingerprint as user_id
    user_id = device_fingerprint.split("_")[0] if "_" in device_fingerprint else "guest"
    device_type = "web"
    
    # Determine granted capabilities
    if user_id in registered_users:
        granted_capabilities = registered_users[user_id]
        logger.info(f"Authenticated registered user: {user_id}")
    else:
        # Guest mode - limited capabilities
        granted_capabilities = ["context-query"]  # Read-only
        logger.info(f"Guest mode for device: {device_fingerprint}")
    
    # Filter to requested capabilities
    granted = [cap for cap in requested_capabilities if cap in granted_capabilities]
    
    # Create session
    session = AuthSession(user_id, device_type, granted)
    _sessions[session.session_id] = session.to_dict()
    
    return {
        "success": True,
        "session_id": session.session_id,
        "user_id": user_id,
        "device_type": device_type,
        "granted_capabilities": granted,
        "mode": "quad-core" if user_id in registered_users else "guest",
        "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
    }


async def validate_session(session_id: str) -> bool:
    """Validate if a session is still active and valid"""
    if session_id not in _sessions:
        return False
    
    session = _sessions[session_id]
    # Check expiry
    created = datetime.fromisoformat(session["created_at"])
    return (datetime.utcnow() - created) < timedelta(hours=24)


async def get_session_capabilities(session_id: str) -> List[str]:
    """Get capabilities granted to a session"""
    if session_id not in _sessions:
        return []
    
    return _sessions[session_id].get("capabilities", [])


async def enforce_mode_transition(
    session_id: str,
    target_mode: str
) -> bool:
    """
    Enforce mode transitions with auth checks
    
    Registered users cannot fall back to Cloud-Only mode
    Guest users can only use Cloud-Only mode
    """
    if session_id not in _sessions:
        return False
    
    session = _sessions[session_id]
    user_id = session.get("user_id", "")
    
    # Registered users: block Cloud-Only
    if user_id in ["justin_harmon", "becky"]:
        if target_mode == "cloud-only":
            logger.warning(f"Blocked Cloud-Only mode for registered user: {user_id}")
            return False
    
    # Guest users: only allow Cloud-Only
    if user_id == "guest":
        if target_mode != "cloud-only":
            logger.warning(f"Blocked non-Cloud-Only mode for guest user")
            return False
    
    return True
