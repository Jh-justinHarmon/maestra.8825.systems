"""Keychain Manager - Secure storage for private keys using OS keychain"""

import keyring
from typing import Optional


class KeychainManager:
    """Secure storage for backend private keys using OS keychain"""
    
    SERVICE_NAME = "com.8825.maestra.backend"
    
    def store_private_key(self, backend_id: str, key_pem: str):
        """
        Store private key in OS keychain
        
        Uses:
        - macOS: Keychain Access
        - Windows: Credential Manager
        - Linux: Secret Service API (GNOME Keyring, KWallet)
        
        Args:
            backend_id: Unique backend identifier
            key_pem: Private key in PEM format
        """
        keyring.set_password(
            self.SERVICE_NAME,
            f"{backend_id}_private_key",
            key_pem
        )
    
    def load_private_key(self, backend_id: str) -> Optional[str]:
        """
        Load private key from OS keychain
        
        Args:
            backend_id: Unique backend identifier
            
        Returns:
            Private key in PEM format, or None if not found
        """
        return keyring.get_password(
            self.SERVICE_NAME,
            f"{backend_id}_private_key"
        )
    
    def delete_private_key(self, backend_id: str):
        """
        Delete private key from OS keychain (revocation)
        
        Args:
            backend_id: Unique backend identifier
        """
        try:
            keyring.delete_password(
                self.SERVICE_NAME,
                f"{backend_id}_private_key"
            )
        except keyring.errors.PasswordDeleteError:
            # Key doesn't exist, ignore
            pass
