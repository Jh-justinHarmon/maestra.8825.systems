"""Backend Identity System - Cryptographic identity for local/hosted backends"""

import hashlib
import uuid
import platform
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


class BackendIdentity:
    """Cryptographic identity for backend instances"""
    
    def __init__(self, backend_type: str = "local"):
        """
        Initialize backend identity
        
        Args:
            backend_type: "local" or "hosted"
        """
        self.backend_type = backend_type
        self.backend_id = self._generate_backend_id()
        self.public_key, self.private_key = self._load_or_generate_keypair()
        self.capabilities = self._detect_capabilities()
        self.created_at = datetime.utcnow()
        self.version = "1.0"
    
    def _generate_backend_id(self) -> str:
        """
        Generate unique backend_id from machine/deployment identifier
        
        For local: SHA256 of machine UUID
        For hosted: SHA256 of deployment ID (e.g., "fly_io_maestra_backend")
        """
        if self.backend_type == "local":
            # Use machine UUID for local backends
            machine_id = str(uuid.getnode())  # MAC address as int
            hostname = platform.node()
            identifier = f"{machine_id}_{hostname}"
        else:
            # Use deployment identifier for hosted backends
            identifier = "fly_io_maestra_backend_8825"
        
        # SHA256 hash
        hash_obj = hashlib.sha256(identifier.encode())
        return f"{self.backend_type}_sha256_{hash_obj.hexdigest()[:16]}"
    
    def _load_or_generate_keypair(self) -> tuple[str, str]:
        """
        Load existing keypair from keychain or generate new RSA-2048 keypair
        
        For local backends: Uses OS keychain
        For hosted backends: Uses environment variable BACKEND_PRIVATE_KEY
        
        Returns:
            (public_key_pem, private_key_pem)
        """
        existing_private_key = None
        
        # Hosted backends use environment variable (no keychain in containers)
        if self.backend_type == "hosted":
            existing_private_key = os.getenv("BACKEND_PRIVATE_KEY")
        else:
            # Local backends use OS keychain
            try:
                from keychain import KeychainManager
                keychain = KeychainManager()
                existing_private_key = keychain.load_private_key(self.backend_id)
            except Exception:
                # Keychain not available, will generate new key
                pass
        
        if existing_private_key:
            # Load existing keypair
            private_key_obj = serialization.load_pem_private_key(
                existing_private_key.encode(),
                password=None,
                backend=default_backend()
            )
            public_key_obj = private_key_obj.public_key()
        else:
            # Generate new RSA-2048 keypair
            private_key_obj = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            public_key_obj = private_key_obj.public_key()
            
            # Store private key (only for local backends with keychain)
            private_key_pem = private_key_obj.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode()
            
            if self.backend_type == "local":
                try:
                    from keychain import KeychainManager
                    keychain = KeychainManager()
                    keychain.store_private_key(self.backend_id, private_key_pem)
                except Exception:
                    # Keychain storage failed, key will be regenerated on restart
                    pass
        
        # Serialize keys to PEM format
        public_key_pem = public_key_obj.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        
        private_key_pem = private_key_obj.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode()
        
        return public_key_pem, private_key_pem
    
    def _detect_capabilities(self) -> list[str]:
        """
        Detect backend capabilities based on environment
        
        Returns:
            List of capability strings
        """
        capabilities = []
        
        if self.backend_type == "local":
            capabilities.extend([
                "offline",
                "fast_context",
                "local_capture",
                "conversation_storage"
            ])
        else:
            capabilities.extend([
                "scale",
                "persistence",
                "global_telemetry",
                "cross_user_analytics"
            ])
        
        return capabilities
    
    def sign(self, data: dict) -> str:
        """
        Sign data with private key using RSA-PSS
        
        Args:
            data: Dictionary to sign
            
        Returns:
            Base64-encoded signature
        """
        import json
        import base64
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        
        # Serialize data deterministically
        message = json.dumps(data, sort_keys=True).encode()
        
        # Load private key
        private_key_obj = serialization.load_pem_private_key(
            self.private_key.encode(),
            password=None,
            backend=default_backend()
        )
        
        # Sign with RSA-PSS
        signature = private_key_obj.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        return base64.b64encode(signature).decode()
    
    def verify(self, data: dict, signature: str, peer_public_key: str) -> bool:
        """
        Verify signature from peer using their public key
        
        Args:
            data: Dictionary that was signed
            signature: Base64-encoded signature
            peer_public_key: Peer's public key in PEM format
            
        Returns:
            True if signature is valid
        """
        import json
        import base64
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        
        try:
            # Serialize data deterministically
            message = json.dumps(data, sort_keys=True).encode()
            
            # Load peer's public key
            public_key_obj = serialization.load_pem_public_key(
                peer_public_key.encode(),
                backend=default_backend()
            )
            
            # Decode signature
            signature_bytes = base64.b64decode(signature)
            
            # Verify with RSA-PSS
            public_key_obj.verify(
                signature_bytes,
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            return True
        except Exception:
            return False
    
    def to_dict(self) -> Dict:
        """
        Export identity as dictionary (public info only)
        
        Returns:
            Dictionary with public identity information
        """
        return {
            "backend_id": self.backend_id,
            "backend_type": self.backend_type,
            "public_key": self.public_key,
            "capabilities": self.capabilities,
            "version": self.version,
            "created_at": self.created_at.isoformat()
        }


# Global identity instance (initialized on import)
_identity: Optional[BackendIdentity] = None


def get_identity(backend_type: str = "local") -> BackendIdentity:
    """
    Get or create global backend identity
    
    Args:
        backend_type: "local" or "hosted"
        
    Returns:
        BackendIdentity instance
    """
    global _identity
    if _identity is None:
        _identity = BackendIdentity(backend_type=backend_type)
    return _identity
