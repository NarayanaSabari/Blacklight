"""Token encryption utility for secure OAuth token storage."""

from cryptography.fernet import Fernet, InvalidToken
from config.settings import settings
import base64
import hashlib


class TokenEncryption:
    """
    Utility for encrypting/decrypting OAuth tokens at rest.
    Uses Fernet symmetric encryption (AES-128-CBC).
    """
    
    def __init__(self):
        self._fernet = None
    
    @property
    def fernet(self):
        """Lazy initialization of Fernet instance."""
        if self._fernet is None:
            key = settings.token_encryption_key
            if not key:
                raise ValueError(
                    "TOKEN_ENCRYPTION_KEY environment variable is required. "
                    "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
                )
            
            # Validate key format
            try:
                self._fernet = Fernet(key.encode() if isinstance(key, str) else key)
            except Exception as e:
                raise ValueError(f"Invalid TOKEN_ENCRYPTION_KEY format: {e}")
        
        return self._fernet
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a string and return base64-encoded ciphertext.
        
        Args:
            plaintext: The string to encrypt (e.g., OAuth token)
        
        Returns:
            Base64-encoded encrypted string
        """
        if not plaintext:
            return ""
        
        encrypted = self.fernet.encrypt(plaintext.encode('utf-8'))
        return encrypted.decode('utf-8')
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt base64-encoded ciphertext and return plaintext.
        
        Args:
            ciphertext: The encrypted string to decrypt
        
        Returns:
            Decrypted plaintext string
        
        Raises:
            InvalidToken: If decryption fails (wrong key or corrupted data)
        """
        if not ciphertext:
            return ""
        
        try:
            decrypted = self.fernet.decrypt(ciphertext.encode('utf-8'))
            return decrypted.decode('utf-8')
        except InvalidToken:
            raise ValueError("Failed to decrypt token. Key may have changed or data is corrupted.")
    
    def is_valid(self) -> bool:
        """
        Check if encryption is properly configured.
        
        Returns:
            True if encryption key is valid and can encrypt/decrypt
        """
        try:
            test_data = "test_token_validation"
            encrypted = self.encrypt(test_data)
            decrypted = self.decrypt(encrypted)
            return decrypted == test_data
        except Exception:
            return False


# Singleton instance for import
token_encryption = TokenEncryption()


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.
    Use this to generate a value for TOKEN_ENCRYPTION_KEY.
    
    Returns:
        A valid Fernet key as a string
    """
    return Fernet.generate_key().decode('utf-8')


def derive_key_from_secret(secret: str) -> str:
    """
    Derive a Fernet-compatible key from an arbitrary secret string.
    Useful if you want to use a human-readable secret.
    
    Args:
        secret: Any string to derive the key from
    
    Returns:
        A valid Fernet key as a string
    """
    # Hash the secret to get 32 bytes
    key_bytes = hashlib.sha256(secret.encode()).digest()
    # Base64 encode for Fernet compatibility
    return base64.urlsafe_b64encode(key_bytes).decode('utf-8')
