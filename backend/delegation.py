"""
Delegation Token Management for Brain Router.

Handles token validation, TTL enforcement, and session binding.
"""

import logging
from datetime import datetime
from typing import Dict, Optional, Any
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
import json

logger = logging.getLogger(__name__)


class DelegationTokenManager:
    """Manages delegation tokens and their lifecycle."""
    
    def __init__(self, public_key_pem: str):
        """
        Initialize token manager with public key from authority service.
        
        Args:
            public_key_pem: PEM-encoded public key from local sidecar
        """
        self.public_key = serialization.load_pem_public_key(public_key_pem.encode())
        self.revoked_tokens = set()  # token_id -> revocation timestamp
    
    def verify_token(self, token: Dict[str, Any]) -> bool:
        """
        Verify token signature and validity.
        
        Args:
            token: Token dict with signature and other fields
        
        Returns:
            True if token is valid, False otherwise
        """
        try:
            # Check if token is revoked
            if token.get("token_id") in self.revoked_tokens:
                logger.warning(f"Token {token.get('token_id')} is revoked")
                return False
            
            # Check TTL
            expires_at = datetime.fromisoformat(token.get("expires_at", ""))
            if datetime.utcnow() > expires_at:
                logger.warning(f"Token {token.get('token_id')} expired")
                return False
            
            # Verify signature
            signature_hex = token.get("signature", "")
            signature_bytes = bytes.fromhex(signature_hex)
            
            # Reconstruct token body for verification
            token_body = json.dumps({
                "token_id": token.get("token_id"),
                "manifest_id": token.get("manifest_id"),
                "capability_id": token.get("capability_id"),
                "session_id": token.get("session_id"),
                "subject": token.get("subject"),
                "issued_at": token.get("issued_at"),
                "expires_at": token.get("expires_at"),
                "policy": token.get("policy"),
                "nonce": token.get("nonce")
            }, sort_keys=True)
            
            self.public_key.verify(signature_bytes, token_body.encode())
            logger.info(f"Token {token.get('token_id')} verified successfully")
            return True
        
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return False
    
    def check_session_binding(self, token: Dict[str, Any], session_id: str) -> bool:
        """
        Check if token is bound to the correct session.
        
        Args:
            token: Token dict
            session_id: Current session ID
        
        Returns:
            True if token is bound to this session, False otherwise
        """
        token_session = token.get("session_id")
        if token_session != session_id:
            logger.warning(
                f"Session binding mismatch: token={token_session}, current={session_id}"
            )
            return False
        return True
    
    def check_replay(self, token: Dict[str, Any], nonce_cache: set) -> bool:
        """
        Check if token has been used before (replay detection).
        
        Args:
            token: Token dict
            nonce_cache: Set of previously seen nonces
        
        Returns:
            True if token is new, False if replay detected
        """
        nonce = token.get("nonce")
        if nonce in nonce_cache:
            logger.warning(f"Token replay detected: nonce={nonce}")
            return False
        return True
    
    def revoke_token(self, token_id: str):
        """Revoke a token."""
        self.revoked_tokens.add(token_id)
        logger.info(f"Token {token_id} revoked")
    
    def is_revoked(self, token_id: str) -> bool:
        """Check if token is revoked."""
        return token_id in self.revoked_tokens


class Tier2GrantManager:
    """Manages Tier 2 ephemeral data grants."""
    
    def __init__(self):
        self.active_grants = {}  # grant_id -> grant_data
        self.byte_budgets = {}  # grant_id -> bytes_used
    
    def create_grant(
        self,
        grant_id: str,
        token_id: str,
        session_id: str,
        byte_budget: int,
        expires_at: str
    ) -> Dict[str, Any]:
        """Create a new Tier 2 grant."""
        grant = {
            "grant_id": grant_id,
            "token_id": token_id,
            "session_id": session_id,
            "byte_budget": byte_budget,
            "bytes_used": 0,
            "expires_at": expires_at,
            "created_at": datetime.utcnow().isoformat()
        }
        self.active_grants[grant_id] = grant
        self.byte_budgets[grant_id] = 0
        logger.info(f"Created Tier 2 grant {grant_id}")
        return grant
    
    def check_byte_budget(self, grant_id: str, bytes_to_add: int) -> bool:
        """
        Check if adding bytes would exceed budget.
        
        Args:
            grant_id: Grant ID
            bytes_to_add: Bytes to add
        
        Returns:
            True if within budget, False otherwise
        """
        grant = self.active_grants.get(grant_id)
        if not grant:
            logger.warning(f"Grant {grant_id} not found")
            return False
        
        current_usage = self.byte_budgets.get(grant_id, 0)
        if current_usage + bytes_to_add > grant["byte_budget"]:
            logger.warning(
                f"Byte budget exceeded for grant {grant_id}: "
                f"{current_usage} + {bytes_to_add} > {grant['byte_budget']}"
            )
            return False
        
        return True
    
    def record_bytes(self, grant_id: str, bytes_used: int):
        """Record bytes used against grant."""
        if grant_id in self.byte_budgets:
            self.byte_budgets[grant_id] += bytes_used
            logger.info(f"Recorded {bytes_used} bytes for grant {grant_id}")
    
    def check_expiration(self, grant_id: str) -> bool:
        """
        Check if grant has expired.
        
        Args:
            grant_id: Grant ID
        
        Returns:
            True if expired, False otherwise
        """
        grant = self.active_grants.get(grant_id)
        if not grant:
            return True
        
        expires_at = datetime.fromisoformat(grant["expires_at"])
        if datetime.utcnow() > expires_at:
            logger.warning(f"Grant {grant_id} expired")
            self._destroy_grant(grant_id)
            return True
        
        return False
    
    def _destroy_grant(self, grant_id: str):
        """Destroy grant and wipe data."""
        if grant_id in self.active_grants:
            del self.active_grants[grant_id]
        if grant_id in self.byte_budgets:
            del self.byte_budgets[grant_id]
        logger.info(f"Destroyed grant {grant_id}")
    
    def get_grant(self, grant_id: str) -> Optional[Dict[str, Any]]:
        """Get grant data."""
        return self.active_grants.get(grant_id)
    
    def get_byte_usage(self, grant_id: str) -> int:
        """Get current byte usage for grant."""
        return self.byte_budgets.get(grant_id, 0)
