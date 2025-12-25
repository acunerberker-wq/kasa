# -*- coding: utf-8 -*-
from __future__ import annotations

import base64
import hashlib
import secrets
from typing import Optional


class SettingsEncryptor:
    def __init__(self, master_key: Optional[str] = None):
        self._master_key = master_key or self._generate_key()

    @property
    def master_key(self) -> str:
        return self._master_key

    def _generate_key(self) -> str:
        return secrets.token_hex(16)

    def _derive_bytes(self) -> bytes:
        digest = hashlib.sha256(self._master_key.encode("utf-8")).digest()
        return digest

    def encrypt(self, value: str) -> str:
        value = value or ""
        key = self._derive_bytes()
        data = value.encode("utf-8")
        xored = bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])
        return base64.urlsafe_b64encode(xored).decode("utf-8")

    def decrypt(self, value: str) -> str:
        if not value:
            return ""
        key = self._derive_bytes()
        raw = base64.urlsafe_b64decode(value.encode("utf-8"))
        data = bytes([b ^ key[i % len(key)] for i, b in enumerate(raw)])
        return data.decode("utf-8")
