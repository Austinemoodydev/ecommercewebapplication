import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

from allauth.mfa.adapter import DefaultMFAAdapter


class EncryptedMFAAdapter(DefaultMFAAdapter):
    """Encrypt TOTP and recovery-code seeds before database storage."""

    def _fernet(self):
        source = settings.MFA_ENCRYPTION_KEY.encode("utf-8")
        key = base64.urlsafe_b64encode(hashlib.sha256(source).digest())
        return Fernet(key)

    def encrypt(self, text):
        return self._fernet().encrypt(text.encode("utf-8")).decode("ascii")

    def decrypt(self, encrypted_text):
        try:
            return self._fernet().decrypt(encrypted_text.encode("ascii")).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError(
                "The MFA encryption key is incorrect or the stored secret is damaged."
            ) from exc
