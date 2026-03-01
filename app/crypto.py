from __future__ import annotations

from typing import Optional

from cryptography.fernet import Fernet, InvalidToken


class Crypto:
    def __init__(self, key: Optional[str]) -> None:
        self._fernet = Fernet(key) if key else None

    def encrypt(self, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if not self._fernet:
            return value
        return self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt(self, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if not self._fernet:
            return value
        try:
            return self._fernet.decrypt(value.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            return None

    @staticmethod
    def generate_key() -> str:
        return Fernet.generate_key().decode("utf-8")
