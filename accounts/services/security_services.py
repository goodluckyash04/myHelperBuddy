import base64
from cryptography.fernet import Fernet

from django.conf import settings
from django.core import signing


class SecurityService:
    def __init__(self):
        self.encryption_key = base64.b64decode(settings.ENCRYPTION_KEY.encode("utf-8"))
        self.cipher_suite = Fernet(self.encryption_key)

    
    def encrypt_text(self, data, use_default = True):
        if use_default:
            return signing.dumps(data, salt=settings.SALT)
        
        if isinstance(data, str):
            data = data.encode("utf-8")

        return self.cipher_suite.encrypt(data).decode("utf-8")
    
    def decrypt_text(self, data, use_default=True):
        if use_default:
            return signing.loads(data, salt=settings.SALT, max_age=3600)

        return self.cipher_suite.decrypt(data.encode("utf-8")).decode("utf-8")
    

security_service = SecurityService()
