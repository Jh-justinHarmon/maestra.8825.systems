"""Session Binding Token (SBT) - Cryptographically links local and hosted backends"""

import hmac
import hashlib
import json
import base64
from datetime import datetime, timedelta
from typing import Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class SessionBindingToken:
    """
    Session Binding Token (SBT) - Cryptographically links local and hosted backends
    
    The SBT is created by the UI when both backends are detected and serves as
    proof that the user has authorized the connection between them.
    """
    
    # Token metadata
    sbt_id: str  # Unique token ID
    user_id: str  # User identifier (e.g., email, user_id)
    session_id: str  # UI session ID
    
    # Backend identities
    local_backend_id: str
    hosted_backend_id: str
    
    # Timestamps
    created_at: str  # ISO 8601
    expires_at: str  # ISO 8601
    
    # Cryptographic proof
    signature: str  # HMAC-SHA256 signature
    
    @classmethod
    def create(
        cls,
        user_id: str,
        session_id: str,
        local_backend_id: str,
        hosted_backend_id: str,
        local_private_key: str,
        expiration_hours: int = 8
    ) -> "SessionBindingToken":
        """
        Create a new Session Binding Token
        
        Args:
            user_id: User identifier
            session_id: UI session ID
            local_backend_id: Local backend's backend_id
            hosted_backend_id: Hosted backend's backend_id
            local_private_key: Local backend's private key (for signing)
            expiration_hours: Token expiration in hours (default: 8)
            
        Returns:
            SessionBindingToken instance
        """
        import uuid
        
        sbt_id = f"sbt_{uuid.uuid4().hex[:16]}"
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(hours=expiration_hours)
        
        # Create payload to sign
        payload = {
            "sbt_id": sbt_id,
            "user_id": user_id,
            "session_id": session_id,
            "local_backend_id": local_backend_id,
            "hosted_backend_id": hosted_backend_id,
            "created_at": created_at.isoformat(),
            "expires_at": expires_at.isoformat()
        }
        
        # Sign with HMAC-SHA256 using local backend's private key
        signature = cls._sign_payload(payload, local_private_key)
        
        return cls(
            sbt_id=sbt_id,
            user_id=user_id,
            session_id=session_id,
            local_backend_id=local_backend_id,
            hosted_backend_id=hosted_backend_id,
            created_at=created_at.isoformat(),
            expires_at=expires_at.isoformat(),
            signature=signature
        )
    
    @staticmethod
    def _sign_payload(payload: Dict, private_key: str) -> str:
        """
        Sign payload with HMAC-SHA256
        
        Args:
            payload: Dictionary to sign
            private_key: Private key to use as HMAC secret
            
        Returns:
            Base64-encoded signature
        """
        # Serialize payload deterministically
        message = json.dumps(payload, sort_keys=True).encode()
        
        # Use first 64 bytes of private key as HMAC secret
        secret = private_key.encode()[:64]
        
        # Create HMAC-SHA256 signature
        signature = hmac.new(secret, message, hashlib.sha256).digest()
        
        return base64.b64encode(signature).decode()
    
    def verify(self, private_key: str) -> bool:
        """
        Verify SBT signature
        
        Args:
            private_key: Private key to verify against
            
        Returns:
            True if signature is valid
        """
        payload = {
            "sbt_id": self.sbt_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "local_backend_id": self.local_backend_id,
            "hosted_backend_id": self.hosted_backend_id,
            "created_at": self.created_at,
            "expires_at": self.expires_at
        }
        
        expected_signature = self._sign_payload(payload, private_key)
        return hmac.compare_digest(self.signature, expected_signature)
    
    def is_expired(self) -> bool:
        """
        Check if token is expired
        
        Returns:
            True if token is expired
        """
        expires_at = datetime.fromisoformat(self.expires_at)
        return datetime.utcnow() > expires_at
    
    def is_valid(self, private_key: str) -> bool:
        """
        Check if token is valid (not expired and signature matches)
        
        Args:
            private_key: Private key to verify against
            
        Returns:
            True if token is valid
        """
        return not self.is_expired() and self.verify(private_key)
    
    def to_dict(self) -> Dict:
        """
        Export SBT as dictionary
        
        Returns:
            Dictionary representation
        """
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "SessionBindingToken":
        """
        Create SBT from dictionary
        
        Args:
            data: Dictionary representation
            
        Returns:
            SessionBindingToken instance
        """
        return cls(**data)
    
    def to_jwt_like_string(self) -> str:
        """
        Export SBT as JWT-like string (for HTTP headers)
        
        Format: base64(header).base64(payload).signature
        
        Returns:
            JWT-like string
        """
        header = {"typ": "SBT", "alg": "HS256"}
        payload = self.to_dict()
        
        header_b64 = base64.urlsafe_b64encode(
            json.dumps(header).encode()
        ).decode().rstrip("=")
        
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).decode().rstrip("=")
        
        return f"{header_b64}.{payload_b64}.{self.signature}"
    
    @classmethod
    def from_jwt_like_string(cls, token_string: str) -> "SessionBindingToken":
        """
        Parse SBT from JWT-like string
        
        Args:
            token_string: JWT-like string
            
        Returns:
            SessionBindingToken instance
        """
        parts = token_string.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid SBT format")
        
        # Decode payload (middle part)
        payload_b64 = parts[1]
        # Add padding if needed
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        
        return cls.from_dict(payload)


class PeerRegistry:
    """
    Registry of registered peer backends
    
    Stores SBTs and peer information for active connections
    """
    
    def __init__(self):
        self._peers: Dict[str, Dict] = {}  # peer_id -> peer_info
    
    def register_peer(
        self,
        sbt: SessionBindingToken,
        peer_backend_id: str,
        peer_public_key: str,
        peer_capabilities: list
    ):
        """
        Register a peer backend
        
        Args:
            sbt: Session Binding Token
            peer_backend_id: Peer's backend_id
            peer_public_key: Peer's public key
            peer_capabilities: Peer's capabilities
        """
        self._peers[peer_backend_id] = {
            "sbt": sbt.to_dict(),
            "backend_id": peer_backend_id,
            "public_key": peer_public_key,
            "capabilities": peer_capabilities,
            "registered_at": datetime.utcnow().isoformat()
        }
    
    def get_peer(self, peer_backend_id: str) -> Optional[Dict]:
        """
        Get peer information
        
        Args:
            peer_backend_id: Peer's backend_id
            
        Returns:
            Peer information or None
        """
        return self._peers.get(peer_backend_id)
    
    def is_peer_registered(self, peer_backend_id: str) -> bool:
        """
        Check if peer is registered
        
        Args:
            peer_backend_id: Peer's backend_id
            
        Returns:
            True if peer is registered
        """
        return peer_backend_id in self._peers
    
    def list_peers(self) -> list:
        """
        List all registered peers
        
        Returns:
            List of peer information
        """
        return list(self._peers.values())
    
    def remove_peer(self, peer_backend_id: str):
        """
        Remove a peer
        
        Args:
            peer_backend_id: Peer's backend_id
        """
        if peer_backend_id in self._peers:
            del self._peers[peer_backend_id]


# Global peer registry
_peer_registry: Optional[PeerRegistry] = None


def get_peer_registry() -> PeerRegistry:
    """
    Get or create global peer registry
    
    Returns:
        PeerRegistry instance
    """
    global _peer_registry
    if _peer_registry is None:
        _peer_registry = PeerRegistry()
    return _peer_registry
