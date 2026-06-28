from cryptography.fernet import Fernet
from typing import Optional
from engines.integration.identity.secret_store import SecretStore

class TokenManager:
    """Manages encryption and decryption of tokens using Fernet."""
    
    def __init__(self):
        self.fernet = Fernet(SecretStore.get_master_key())

    def encrypt(self, data: str) -> str:
        """Encrypt a plain text token."""
        if not data:
            return data
        return self.fernet.encrypt(data.encode('utf-8')).decode('utf-8')

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt an encrypted token."""
        if not encrypted_data:
            return encrypted_data
        return self.fernet.decrypt(encrypted_data.encode('utf-8')).decode('utf-8')

# Singleton instance
token_manager = TokenManager()
