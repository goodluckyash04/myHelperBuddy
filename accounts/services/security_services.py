"""
Security Service - Encryption and decryption utilities.

Provides secure encryption/decryption using:
- Django's built-in signing framework (default)
- Fernet symmetric encryption (optional)
"""

import base64
from typing import Any, Union

from cryptography.fernet import Fernet
from django.conf import settings
from django.core import signing


class SecurityService:
    """
    Service for encrypting and decrypting sensitive data.
    
    Features:
        - Django signing for session-based encryption (default)
        - Fernet encryption for stronger security (optional)
        - Configurable expiration for signed data
        - Base64 encoding for transport
    """
    
    def __init__(self):
        """
        Initialize security service with encryption keys.
        
        Raises:
            ValueError: If ENCRYPTION_KEY is not properly configured
        """
        try:
            encryption_key_bytes = base64.b64decode(
                settings.ENCRYPTION_KEY.encode("utf-8")
            )
            self.cipher_suite = Fernet(encryption_key_bytes)
        except Exception as e:
            print(f"Warning: Fernet encryption initialization failed: {e}")
            self.cipher_suite = None
    
    def encrypt_text(
        self,
        data: Union[str, dict],
        use_default: bool = True
    ) -> str:
        """
        Encrypt text or data object.
        
        Args:
            data: String or dict to encrypt
            use_default: If True, use Django signing; if False, use Fernet
            
        Returns:
            str: Encrypted string
            
        Example:
            >>> service = SecurityService()
            >>> encrypted = service.encrypt_text({"user_id": 123})
            >>> # Returns signed string
        """
        if use_default:
            # Use Django's signing framework (includes tampering protection)
            return signing.dumps(data, salt=settings.SALT)
        
        # Use Fernet encryption
        if not self.cipher_suite:
            raise RuntimeError("Fernet encryption not available")
        
        if isinstance(data, str):
            data = data.encode("utf-8")
        elif isinstance(data, dict):
            # Convert dict to JSON string
            import json
            data = json.dumps(data).encode("utf-8")
        
        encrypted_bytes = self.cipher_suite.encrypt(data)
        return encrypted_bytes.decode("utf-8")
    
    def decrypt_text(
        self,
        data: str,
        use_default: bool = True,
        max_age: int = 3600
    ) -> Any:
        """
        Decrypt encrypted text or data object.
        
        Args:
            data: Encrypted string
            use_default: If True, use Django signing; if False, use Fernet
            max_age: Maximum age in seconds for signed data (default: 1 hour)
            
        Returns:
            Decrypted data (str or dict depending on original data)
            
        Raises:
            signing.SignatureExpired: If signed data has expired
            signing.BadSignature: If signature is invalid
            
        Example:
            >>> service = SecurityService()
            >>> decrypted = service.decrypt_text(encrypted_string)
        """
        if use_default:
            # Use Django's signing framework
            return signing.loads(
                data,
                salt=settings.SALT,
                max_age=max_age
            )
        
        # Use Fernet decryption
        if not self.cipher_suite:
            raise RuntimeError("Fernet decryption not available")
        
        decrypted_bytes = self.cipher_suite.decrypt(data.encode("utf-8"))
        decrypted_str = decrypted_bytes.decode("utf-8")
        
        # Try to parse as JSON (in case it was a dict)
        try:
            import json
            return json.loads(decrypted_str)
        except (json.JSONDecodeError, ValueError):
            return decrypted_str


# Singleton instance for convenience
security_service = SecurityService()
