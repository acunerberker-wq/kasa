# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from typing import List, Optional, Tuple

from .repo import IntegrationRepo


class ApiAuthService:
    def __init__(self, repo: IntegrationRepo):
        self.repo = repo

    def create_token(self, company_id: int, name: str, scopes: List[str]) -> Tuple[str, int]:
        token = secrets.token_urlsafe(24)
        token_hash = self._hash_token(token)
        scopes_json = json.dumps(scopes, ensure_ascii=False)
        token_id = self.repo.api_token_add(company_id, name, token_hash, scopes_json)
        return token, token_id

    def validate_token(self, token: str, scope: Optional[str] = None):
        token_hash = self._hash_token(token)
        row = self.repo.api_token_get(token_hash)
        if not row:
            return None
        if scope:
            scopes = json.loads(row["scopes_json"] or "[]")
            if scope not in scopes:
                return None
        self.repo.api_token_touch(int(row["id"]))
        return row

    def check_idempotency(self, company_id: int, key: str, request_hash: str) -> bool:
        return self.repo.idempotency_key_store(company_id, key, request_hash)

    def _hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()


class WebhookService:
    def __init__(self, repo: IntegrationRepo):
        self.repo = repo

    def sign_payload(self, secret: str, payload: str) -> str:
        digest = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return digest

    def add_subscription(self, company_id: int, url: str, secret: str, events: List[str]) -> int:
        return self.repo.webhook_subscription_add(company_id, url, secret, json.dumps(events, ensure_ascii=False))
