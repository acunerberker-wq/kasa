# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional

from .repo import IntegrationRepo


class NotificationProvider:
    name = "generic"

    def send(self, recipient: str, subject: str, body: str) -> bool:
        raise NotImplementedError


class EmailProvider(NotificationProvider):
    name = "smtp"

    def send(self, recipient: str, subject: str, body: str) -> bool:
        raise NotImplementedError


class MockEmailProvider(EmailProvider):
    name = "mock_email"

    def send(self, recipient: str, subject: str, body: str) -> bool:
        if "FAIL" in subject.upper():
            return False
        return True


class SmsProvider(NotificationProvider):
    name = "sms_generic"


class MockSmsProvider(SmsProvider):
    name = "mock_sms"

    def send(self, recipient: str, subject: str, body: str) -> bool:
        if "FAIL" in body.upper():
            return False
        return True


class WhatsAppProvider(NotificationProvider):
    name = "whatsapp_generic"


class MockWhatsAppProvider(WhatsAppProvider):
    name = "mock_whatsapp"

    def send(self, recipient: str, subject: str, body: str) -> bool:
        if "FAIL" in body.upper():
            return False
        return True


@dataclass
class NotificationResult:
    status: str
    provider: str
    detail: str


class NotificationService:
    def __init__(self, repo: IntegrationRepo):
        self.repo = repo
        self.logger = logging.getLogger("kasapro.integrations.notifications")
        self.providers: Dict[str, NotificationProvider] = {
            "email": MockEmailProvider(),
            "sms": MockSmsProvider(),
            "whatsapp": MockWhatsAppProvider(),
            "in_app": MockEmailProvider(),
        }
        self._rate_buckets: Dict[str, deque] = defaultdict(deque)
        self.rate_limit_per_minute = 30

    def _rate_key(self, company_id: int, channel: str) -> str:
        return f"{company_id}:{channel}"

    def _check_rate_limit(self, company_id: int, channel: str) -> bool:
        key = self._rate_key(company_id, channel)
        bucket = self._rate_buckets[key]
        now = datetime.now()
        window_start = now - timedelta(minutes=1)
        while bucket and bucket[0] < window_start:
            bucket.popleft()
        if len(bucket) >= self.rate_limit_per_minute:
            return False
        bucket.append(now)
        return True

    def set_provider(self, channel: str, provider: NotificationProvider) -> None:
        self.providers[channel] = provider

    def send_notification(
        self,
        company_id: int,
        channel: str,
        recipient: str,
        subject: str,
        body: str,
        notification_id: Optional[int] = None,
    ) -> NotificationResult:
        channel = channel.lower()
        consent = self.repo.consent_get(company_id, recipient, channel)
        if consent is not None and consent == 0:
            detail = "KVKK opt-in yok"
            if notification_id:
                self.repo.delivery_log_add(notification_id, "policy", "blocked", detail)
            return NotificationResult("blocked", "policy", detail)

        if not self._check_rate_limit(company_id, channel):
            detail = "Rate limit"
            if notification_id:
                self.repo.delivery_log_add(notification_id, "rate_limit", "throttled", detail)
            return NotificationResult("throttled", "rate_limit", detail)

        provider = self.providers.get(channel)
        if not provider:
            detail = "Provider bulunamadı"
            if notification_id:
                self.repo.delivery_log_add(notification_id, "missing", "failed", detail)
            return NotificationResult("failed", "missing", detail)

        ok = False
        try:
            ok = provider.send(recipient, subject, body)
        except Exception as exc:  # pragma: no cover - extra safety
            detail = f"Provider hata: {exc}"
            self.repo.delivery_log_add(notification_id or 0, provider.name, "failed", detail)
            return NotificationResult("failed", provider.name, detail)

        status = "sent" if ok else "failed"
        detail = "OK" if ok else "Provider failure"
        if notification_id:
            self.repo.delivery_log_add(notification_id, provider.name, status, detail)
        return NotificationResult(status, provider.name, detail)
