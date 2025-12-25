# -*- coding: utf-8 -*-
from __future__ import annotations

import sqlite3
from typing import Any, Iterable, Optional


class IntegrationRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row

    # -----------------
    # Outbox & Jobs
    # -----------------
    def outbox_add(self, company_id: int, event_type: str, payload_json: str, idempotency_key: Optional[str]) -> int:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO event_outbox(company_id, event_type, payload_json, idempotency_key, created_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (company_id, event_type, payload_json, idempotency_key),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def outbox_list_pending(self, company_id: int, limit: int = 50):
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT * FROM event_outbox
            WHERE company_id = ? AND processed_at IS NULL
            ORDER BY event_id ASC
            LIMIT ?
            """,
            (company_id, limit),
        )
        return cur.fetchall()

    def outbox_mark_processed(self, event_id: int) -> None:
        self.conn.execute(
            "UPDATE event_outbox SET processed_at = CURRENT_TIMESTAMP WHERE event_id = ?",
            (event_id,),
        )
        self.conn.commit()

    def job_enqueue(
        self,
        company_id: int,
        job_type: str,
        payload_json: str,
        idempotency_key: Optional[str],
        status: str = "pending",
        next_retry_at: Optional[str] = None,
    ) -> int:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT OR IGNORE INTO jobs(company_id, job_type, payload_json, status, attempts, next_retry_at, idempotency_key, created_at)
            VALUES (?, ?, ?, ?, 0, ?, ?, CURRENT_TIMESTAMP)
            """,
            (company_id, job_type, payload_json, status, next_retry_at, idempotency_key),
        )
        if cur.lastrowid:
            job_id = int(cur.lastrowid)
        else:
            row = self.job_get_by_idempotency(company_id, idempotency_key)
            job_id = int(row["job_id"]) if row else 0
        self.conn.commit()
        return job_id

    def job_get_by_idempotency(self, company_id: int, idempotency_key: Optional[str]):
        if not idempotency_key:
            return None
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM jobs WHERE company_id = ? AND idempotency_key = ?",
            (company_id, idempotency_key),
        )
        return cur.fetchone()

    def job_get(self, job_id: int):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
        return cur.fetchone()

    def job_next_due(self, company_id: int):
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT * FROM jobs
            WHERE company_id = ?
              AND status = 'pending'
              AND (next_retry_at IS NULL OR next_retry_at <= CURRENT_TIMESTAMP)
            ORDER BY job_id ASC
            LIMIT 1
            """,
            (company_id,),
        )
        return cur.fetchone()

    def job_mark_running(self, job_id: int) -> None:
        self.conn.execute(
            "UPDATE jobs SET status = 'running', updated_at = CURRENT_TIMESTAMP WHERE job_id = ?",
            (job_id,),
        )
        self.conn.commit()

    def job_mark_done(self, job_id: int) -> None:
        self.conn.execute(
            "UPDATE jobs SET status = 'done', updated_at = CURRENT_TIMESTAMP WHERE job_id = ?",
            (job_id,),
        )
        self.conn.commit()

    def job_mark_failed(self, job_id: int, attempts: int, next_retry_at: Optional[str], last_error: str) -> None:
        self.conn.execute(
            """
            UPDATE jobs
            SET status = 'pending', attempts = ?, next_retry_at = ?, last_error = ?, updated_at = CURRENT_TIMESTAMP
            WHERE job_id = ?
            """,
            (attempts, next_retry_at, last_error, job_id),
        )
        self.conn.commit()

    def job_move_dead_letter(self, job_row: sqlite3.Row) -> None:
        self.conn.execute(
            """
            INSERT INTO dead_letter_jobs(company_id, job_type, payload_json, attempts, last_error, idempotency_key, failed_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                job_row["company_id"],
                job_row["job_type"],
                job_row["payload_json"],
                job_row["attempts"],
                job_row["last_error"],
                job_row["idempotency_key"],
            ),
        )
        self.conn.execute(
            "UPDATE jobs SET status = 'dead', updated_at = CURRENT_TIMESTAMP WHERE job_id = ?",
            (job_row["job_id"],),
        )
        self.conn.commit()

    # -----------------
    # Audit
    # -----------------
    def audit_log(self, company_id: int, actor: str, action: str, entity_type: str, entity_id: Optional[int], detail: str) -> None:
        detail_text = f"actor={actor} {detail}".strip()
        self.conn.execute(
            """
            INSERT INTO audit_log(company_id, entity_type, entity_id, action, details, created_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (company_id, entity_type, entity_id or 0, action, detail_text),
        )
        self.conn.commit()

    def audit_list(self, company_id: int, limit: int = 200):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM audit_log WHERE company_id = ? ORDER BY id DESC LIMIT ?",
            (company_id, limit),
        )
        return cur.fetchall()

    # -----------------
    # Notifications
    # -----------------
    def notification_template_add(self, company_id: int, name: str, channel: str, subject: str, body: str, variables_json: str):
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO notification_templates(company_id, name, channel, subject, body, variables_json, active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (company_id, name, channel, subject, body, variables_json),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def notification_template_get(self, template_id: int):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM notification_templates WHERE id = ?", (template_id,))
        return cur.fetchone()

    def notification_rules_list(self, company_id: int, event_type: str):
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT * FROM notification_rules
            WHERE company_id = ? AND event_type = ? AND active = 1
            """,
            (company_id, event_type),
        )
        return cur.fetchall()

    def notification_rule_add(self, company_id: int, event_type: str, channel: str, recipient: str, template_id: int):
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO notification_rules(company_id, event_type, channel, recipient, template_id, active)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (company_id, event_type, channel, recipient, template_id),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def notification_outbox_add(
        self,
        company_id: int,
        channel: str,
        recipient: str,
        subject: str,
        body: str,
        idempotency_key: Optional[str],
    ) -> int:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO notification_outbox(company_id, channel, recipient, subject, body, status, attempts, idempotency_key, created_at)
            VALUES (?, ?, ?, ?, ?, 'pending', 0, ?, CURRENT_TIMESTAMP)
            """,
            (company_id, channel, recipient, subject, body, idempotency_key),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def notification_outbox_update(self, outbox_id: int, status: str) -> None:
        self.conn.execute(
            "UPDATE notification_outbox SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, outbox_id),
        )
        self.conn.commit()

    def delivery_log_add(self, notification_id: int, provider: str, status: str, detail: str) -> int:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO delivery_log(notification_id, provider, status, detail, created_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (notification_id, provider, status, detail),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def consent_set(self, company_id: int, contact: str, channel: str, opt_in: int) -> None:
        self.conn.execute(
            """
            INSERT INTO contact_consents(company_id, contact, channel, opt_in, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(company_id, contact, channel)
            DO UPDATE SET opt_in = excluded.opt_in, updated_at = CURRENT_TIMESTAMP
            """,
            (company_id, contact, channel, opt_in),
        )
        self.conn.commit()

    def consent_get(self, company_id: int, contact: str, channel: str) -> Optional[int]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT opt_in FROM contact_consents WHERE company_id = ? AND contact = ? AND channel = ?",
            (company_id, contact, channel),
        )
        row = cur.fetchone()
        if row:
            return int(row["opt_in"])
        return None

    # -----------------
    # External systems
    # -----------------
    def external_mapping_upsert(self, company_id: int, system: str, entity_type: str, internal_id: int, external_id: str) -> None:
        self.conn.execute(
            """
            INSERT INTO external_mappings(company_id, system, entity_type, internal_id, external_id, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(company_id, system, entity_type, internal_id)
            DO UPDATE SET external_id = excluded.external_id, updated_at = CURRENT_TIMESTAMP
            """,
            (company_id, system, entity_type, internal_id, external_id),
        )
        self.conn.commit()

    def export_job_add(self, company_id: int, job_type: str, status: str = "pending") -> int:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO export_jobs(company_id, job_type, status, created_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (company_id, job_type, status),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def export_item_add(self, job_id: int, entity_type: str, payload_json: str, status: str = "pending") -> int:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO export_items(job_id, entity_type, payload_json, status)
            VALUES (?, ?, ?, ?)
            """,
            (job_id, entity_type, payload_json, status),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def import_job_add(self, company_id: int, job_type: str, status: str = "pending") -> int:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO import_jobs(company_id, job_type, status, created_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (company_id, job_type, status),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def import_item_add(self, job_id: int, entity_type: str, payload_json: str, status: str = "pending", error: str = "") -> int:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO import_items(job_id, entity_type, payload_json, status, error)
            VALUES (?, ?, ?, ?, ?)
            """,
            (job_id, entity_type, payload_json, status, error),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    # -----------------
    # Bank
    # -----------------
    def bank_statement_add(self, company_id: int, source_name: str, period_start: str, period_end: str) -> int:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO bank_statements(company_id, source_name, period_start, period_end, imported_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (company_id, source_name, period_start, period_end),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def bank_transaction_add(
        self,
        company_id: int,
        statement_id: int,
        transaction_date: str,
        amount: float,
        description: str,
        unique_hash: str,
    ) -> bool:
        try:
            self.conn.execute(
                """
                INSERT INTO bank_transactions(company_id, statement_id, transaction_date, amount, description, unique_hash, matched)
                VALUES (?, ?, ?, ?, ?, ?, 0)
                """,
                (company_id, statement_id, transaction_date, amount, description, unique_hash),
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def bank_transactions_list(self, company_id: int, matched: Optional[int] = None):
        cur = self.conn.cursor()
        if matched is None:
            cur.execute(
                "SELECT * FROM bank_transactions WHERE company_id = ? ORDER BY transaction_date",
                (company_id,),
            )
        else:
            cur.execute(
                "SELECT * FROM bank_transactions WHERE company_id = ? AND matched = ? ORDER BY transaction_date",
                (company_id, matched),
            )
        return cur.fetchall()

    def bank_transaction_mark_matched(self, tx_id: int, matched_ref: str) -> None:
        self.conn.execute(
            """
            UPDATE bank_transactions
            SET matched = 1, matched_ref = ?, matched_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (matched_ref, tx_id),
        )
        self.conn.commit()

    # -----------------
    # API & Webhook
    # -----------------
    def api_token_add(self, company_id: int, name: str, token_hash: str, scopes_json: str) -> int:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO api_tokens(company_id, name, token_hash, scopes_json, active, created_at)
            VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
            """,
            (company_id, name, token_hash, scopes_json),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def api_token_get(self, token_hash: str):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM api_tokens WHERE token_hash = ? AND active = 1",
            (token_hash,),
        )
        return cur.fetchone()

    def api_token_touch(self, token_id: int) -> None:
        self.conn.execute(
            "UPDATE api_tokens SET last_used_at = CURRENT_TIMESTAMP WHERE id = ?",
            (token_id,),
        )
        self.conn.commit()

    def webhook_subscription_add(self, company_id: int, url: str, secret: str, events_json: str) -> int:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO webhook_subscriptions(company_id, url, secret, events_json, active, created_at)
            VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
            """,
            (company_id, url, secret, events_json),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def webhook_subscriptions_list(self, company_id: int, event_type: str):
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT * FROM webhook_subscriptions
            WHERE company_id = ? AND active = 1
              AND (events_json LIKE ? OR events_json LIKE '%"*"%')
            """,
            (company_id, f"%{event_type}%"),
        )
        return cur.fetchall()

    def webhook_delivery_add(
        self,
        company_id: int,
        subscription_id: int,
        event_type: str,
        payload_json: str,
        status: str,
        attempts: int,
        next_retry_at: Optional[str],
        last_error: str,
    ) -> int:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO webhook_deliveries(company_id, subscription_id, event_type, payload_json, status, attempts, next_retry_at, last_error, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (company_id, subscription_id, event_type, payload_json, status, attempts, next_retry_at, last_error),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def webhook_delivery_update(self, delivery_id: int, status: str, attempts: int, next_retry_at: Optional[str], last_error: str) -> None:
        self.conn.execute(
            """
            UPDATE webhook_deliveries
            SET status = ?, attempts = ?, next_retry_at = ?, last_error = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, attempts, next_retry_at, last_error, delivery_id),
        )
        self.conn.commit()

    def idempotency_key_store(self, company_id: int, key: str, request_hash: str) -> bool:
        try:
            self.conn.execute(
                """
                INSERT INTO idempotency_keys(company_id, idempotency_key, request_hash, created_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (company_id, key, request_hash),
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def idempotency_key_get(self, company_id: int, key: str):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM idempotency_keys WHERE company_id = ? AND idempotency_key = ?",
            (company_id, key),
        )
        return cur.fetchone()

    # -----------------
    # Helpers
    # -----------------
    def query(self, sql: str, params: Iterable[Any] = ()):  # pragma: no cover - dev helper
        cur = self.conn.cursor()
        cur.execute(sql, params)
        return cur.fetchall()
