# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from kasapro.utils import now_iso
from kasapro.db.main_db import DB

from .api import ApiAuthService, WebhookService
from .bank import BankStatementService, BankTransactionRow
from .connectors import GenericCSVConnector
from .notifications import NotificationService
from .repo import IntegrationRepo
from .security import SettingsEncryptor


class IntegrationService:
    def __init__(self, db: DB, context_provider):
        self.db = db
        self.repo = IntegrationRepo(db.conn)
        self._context_provider = context_provider
        self.logger = logging.getLogger("kasapro.integrations")
        self.notifications = NotificationService(self.repo)
        self.bank = BankStatementService(self.repo)
        self.api_auth = ApiAuthService(self.repo)
        self.webhooks = WebhookService(self.repo)
        self.csv = GenericCSVConnector(self.repo)
        self.max_attempts = 3

    def _ctx(self):
        return self._context_provider()

    def _company_id(self) -> int:
        ctx = self._ctx()
        return int(getattr(ctx, "company_id", 1) or 1)

    def _actor(self) -> str:
        ctx = self._ctx()
        return str(getattr(ctx, "actor_username", "system"))

    def encryptor(self) -> SettingsEncryptor:
        master_key = self.db.get_setting("integration_master_key")
        if not master_key:
            encryptor = SettingsEncryptor()
            self.db.set_setting("integration_master_key", encryptor.master_key)
            return encryptor
        return SettingsEncryptor(master_key)

    def set_secure_setting(self, key: str, value: str) -> None:
        encryptor = self.encryptor()
        encrypted = encryptor.encrypt(value)
        self.db.conn.execute(
            """
            INSERT INTO integration_settings(company_id, setting_key, value_encrypted, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(company_id, setting_key)
            DO UPDATE SET value_encrypted = excluded.value_encrypted, updated_at = CURRENT_TIMESTAMP
            """,
            (self._company_id(), key, encrypted),
        )
        self.db.conn.commit()

    def get_secure_setting(self, key: str) -> str:
        row = self.db.conn.execute(
            "SELECT value_encrypted FROM integration_settings WHERE company_id = ? AND setting_key = ?",
            (self._company_id(), key),
        ).fetchone()
        if not row:
            return ""
        encryptor = self.encryptor()
        return encryptor.decrypt(row["value_encrypted"])

    # -----------------
    # Outbox / Jobs
    # -----------------
    def emit_event(self, event_type: str, payload: Dict[str, Any], idempotency_key: Optional[str] = None) -> int:
        company_id = self._company_id()
        event_id = self.repo.outbox_add(company_id, event_type, json.dumps(payload, ensure_ascii=False), idempotency_key)
        self.repo.audit_log(company_id, self._actor(), "emit_event", "event", event_id, event_type)
        return event_id

    def process_outbox(self) -> int:
        company_id = self._company_id()
        pending = self.repo.outbox_list_pending(company_id)
        created_jobs = 0
        for event in pending:
            payload = json.loads(event["payload_json"] or "{}")
            event_type = event["event_type"]
            idempotency_key = event["idempotency_key"] or f"event:{event['event_id']}"
            job_payload = {
                "event_type": event_type,
                "payload": payload,
            }
            job_id = self.enqueue_job("notification_dispatch", job_payload, idempotency_key)
            if job_id:
                created_jobs += 1
            webhook_job_id = self.enqueue_job("webhook_delivery", job_payload, f"webhook:{idempotency_key}")
            if webhook_job_id:
                created_jobs += 1
            self.repo.outbox_mark_processed(int(event["event_id"]))
        return created_jobs

    def enqueue_job(self, job_type: str, payload: Dict[str, Any], idempotency_key: Optional[str] = None) -> int:
        company_id = self._company_id()
        return self.repo.job_enqueue(company_id, job_type, json.dumps(payload, ensure_ascii=False), idempotency_key)

    def run_next_job(self) -> bool:
        company_id = self._company_id()
        job = self.repo.job_next_due(company_id)
        if not job:
            return False
        self.repo.job_mark_running(int(job["job_id"]))
        try:
            ok = self._handle_job(job)
        except Exception as exc:  # pragma: no cover
            ok = False
            err = str(exc)
        else:
            err = ""
        if ok:
            self.repo.job_mark_done(int(job["job_id"]))
            return True
        attempts = int(job["attempts"]) + 1
        next_retry = (datetime.now() + timedelta(seconds=2 * attempts)).strftime("%Y-%m-%d %H:%M:%S")
        self.repo.job_mark_failed(int(job["job_id"]), attempts, next_retry, err or "Job failed")
        job = self.repo.job_get(int(job["job_id"]))
        if job and int(job["attempts"]) >= self.max_attempts:
            self.repo.job_move_dead_letter(job)
        return True

    def _handle_job(self, job) -> bool:
        job_type = job["job_type"]
        payload = json.loads(job["payload_json"] or "{}")
        if job_type == "notification_dispatch":
            return self._handle_notification_job(payload)
        if job_type == "webhook_delivery":
            return self._handle_webhook_job(payload)
        return True

    # -----------------
    # Notifications
    # -----------------
    def _handle_notification_job(self, payload: Dict[str, Any]) -> bool:
        company_id = self._company_id()
        event_type = payload.get("event_type", "")
        rules = self.repo.notification_rules_list(company_id, event_type)
        if not rules:
            return True
        ok_all = True
        for rule in rules:
            template = self.repo.notification_template_get(int(rule["template_id"]))
            if not template:
                continue
            subject = (template["subject"] or "").format_map(payload.get("payload", {}))
            body = (template["body"] or "").format_map(payload.get("payload", {}))
            outbox_id = self.repo.notification_outbox_add(
                company_id,
                rule["channel"],
                rule["recipient"],
                subject,
                body,
                rule["id"],
            )
            result = self.notifications.send_notification(
                company_id,
                rule["channel"],
                rule["recipient"],
                subject,
                body,
                notification_id=outbox_id,
            )
            status = "sent" if result.status == "sent" else result.status
            self.repo.notification_outbox_update(outbox_id, status)
            if result.status not in ("sent", "blocked", "throttled"):
                ok_all = False
        return ok_all

    # -----------------
    # Webhooks
    # -----------------
    def _handle_webhook_job(self, payload: Dict[str, Any]) -> bool:
        company_id = self._company_id()
        event_type = payload.get("event_type", "")
        subs = self.repo.webhook_subscriptions_list(company_id, event_type)
        if not subs:
            return True
        ok_all = True
        payload_json = json.dumps(payload, ensure_ascii=False)
        for sub in subs:
            signature = self.webhooks.sign_payload(sub["secret"], payload_json)
            attempts = 1
            status = "sent"
            last_error = ""
            if "fail" in (sub["url"] or ""):
                status = "failed"
                last_error = "Webhook simülasyon hatası"
                ok_all = False
            self.repo.webhook_delivery_add(
                company_id,
                int(sub["id"]),
                event_type,
                payload_json,
                status,
                attempts,
                None if status == "sent" else now_iso(),
                last_error or signature,
            )
        return ok_all

    # -----------------
    # External Systems
    # -----------------
    def export_csv(self, output_dir: Path) -> List[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        paths = [
            self.csv.export_cariler(self.db.conn, output_dir),
            self.csv.export_faturalar(self.db.conn, output_dir),
            self.csv.export_tahsilatlar(self.db.conn, output_dir),
        ]
        return paths

    def import_csv(self, entity_type: str, csv_path: Path) -> Tuple[int, int]:
        company_id = self._company_id()
        job_id = self.repo.import_job_add(company_id, f"import:{entity_type}")
        return self.csv.import_csv(job_id, entity_type, csv_path)

    # -----------------
    # Bank
    # -----------------
    def import_bank_csv(self, source_name: str, period_start: str, period_end: str, csv_path: Path):
        transactions = self.bank.parse_csv(csv_path)
        return self.bank.import_statement(self._company_id(), source_name, period_start, period_end, transactions)

    def auto_reconcile(self) -> int:
        return self.bank.auto_reconcile(self._company_id(), self.db.conn)

    def manual_reconcile(self, tx_id: int, reference: str) -> None:
        self.bank.manual_reconcile(tx_id, reference)

    # -----------------
    # API
    # -----------------
    def create_api_token(self, name: str, scopes: List[str]) -> Tuple[str, int]:
        company_id = self._company_id()
        token, token_id = self.api_auth.create_token(company_id, name, scopes)
        self.repo.audit_log(company_id, self._actor(), "create_token", "api_token", token_id, name)
        return token, token_id

    def validate_api_token(self, token: str, scope: Optional[str] = None):
        return self.api_auth.validate_token(token, scope=scope)

    def record_idempotency(self, key: str, payload: Dict[str, Any]) -> bool:
        company_id = self._company_id()
        request_hash = json.dumps(payload, sort_keys=True)
        return self.api_auth.check_idempotency(company_id, key, request_hash)
