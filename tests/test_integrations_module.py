# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import json
from pathlib import Path

from kasapro.db.main_db import DB
from kasapro.modules.integrations.service import IntegrationService
from kasapro.modules.integrations.repo import IntegrationRepo
from kasapro.modules.integrations.notifications import MockEmailProvider


class DummyContext:
    def __init__(self, company_id: int = 1, actor_username: str = "tester"):
        self.company_id = company_id
        self.actor_username = actor_username
        self.actor_role = "admin"


def make_service(tmp_path: Path) -> IntegrationService:
    db_path = tmp_path / "test.db"
    db = DB(str(db_path))
    ctx = DummyContext()
    return IntegrationService(db, lambda: ctx)


def seed_invoice_data(db: DB):
    conn = db.conn
    conn.execute("INSERT INTO cariler(ad, tur, telefon) VALUES (?, ?, ?)", ("Acme", "musteri", "555"))
    cari_id = conn.execute("SELECT id FROM cariler WHERE ad = ?", ("Acme",)).fetchone()[0]
    conn.execute(
        """
        INSERT INTO fatura(tarih, fatura_no, cari_id, cari_ad, genel_toplam)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("2024-01-10", "FTR-0001", cari_id, "Acme", 100.0),
    )
    fatura_id = conn.execute("SELECT id FROM fatura WHERE fatura_no = ?", ("FTR-0001",)).fetchone()[0]
    conn.execute(
        "INSERT INTO fatura_odeme(fatura_id, tarih, tutar) VALUES (?, ?, ?)",
        (fatura_id, "2024-01-11", 100.0),
    )
    conn.commit()


def test_event_outbox_creates_job(tmp_path: Path):
    service = make_service(tmp_path)
    service.emit_event("invoice.created", {"id": 1})
    created = service.process_outbox()
    count = service.db.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    assert created >= 1
    assert count >= 1


def test_job_retry_and_dead_letter(tmp_path: Path):
    service = make_service(tmp_path)
    repo = IntegrationRepo(service.db.conn)
    tpl_id = repo.notification_template_add(1, "fail_tpl", "email", "FAIL {name}", "Body", "{}")
    repo.notification_rule_add(1, "invoice.failed", "email", "user@example.com", tpl_id)
    repo.consent_set(1, "user@example.com", "email", 1)

    service.enqueue_job("notification_dispatch", {"event_type": "invoice.failed", "payload": {"name": "ACME"}}, "dup-1")

    for _ in range(service.max_attempts + 1):
        service.run_next_job()
        service.db.conn.execute("UPDATE jobs SET next_retry_at = CURRENT_TIMESTAMP")
        service.db.conn.commit()

    dead_count = service.db.conn.execute("SELECT COUNT(*) FROM dead_letter_jobs").fetchone()[0]
    assert dead_count == 1


def test_idempotency_prevents_duplicate_jobs(tmp_path: Path):
    service = make_service(tmp_path)
    service.enqueue_job("notification_dispatch", {"event_type": "x", "payload": {}}, "idem-1")
    service.enqueue_job("notification_dispatch", {"event_type": "x", "payload": {}}, "idem-1")
    count = service.db.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    assert count == 1


def test_email_provider_mock_logs_success_fail(tmp_path: Path):
    service = make_service(tmp_path)
    repo = IntegrationRepo(service.db.conn)
    repo.consent_set(1, "mail@example.com", "email", 1)

    ok_id = repo.notification_outbox_add(1, "email", "mail@example.com", "OK", "body", "ok")
    fail_id = repo.notification_outbox_add(1, "email", "mail@example.com", "FAIL", "body", "fail")

    service.notifications.send_notification(1, "email", "mail@example.com", "OK", "body", ok_id)
    service.notifications.send_notification(1, "email", "mail@example.com", "FAIL", "body", fail_id)

    rows = service.db.conn.execute("SELECT status FROM delivery_log ORDER BY id").fetchall()
    statuses = [r[0] for r in rows]
    assert "sent" in statuses
    assert "failed" in statuses


def test_sms_whatsapp_mock(tmp_path: Path):
    service = make_service(tmp_path)
    repo = IntegrationRepo(service.db.conn)
    repo.consent_set(1, "90555", "sms", 1)
    repo.consent_set(1, "90555", "whatsapp", 1)

    sms_id = repo.notification_outbox_add(1, "sms", "90555", "", "hello", "sms")
    wa_id = repo.notification_outbox_add(1, "whatsapp", "90555", "", "hello", "wa")

    sms_result = service.notifications.send_notification(1, "sms", "90555", "", "hello", sms_id)
    wa_result = service.notifications.send_notification(1, "whatsapp", "90555", "", "hello", wa_id)

    assert sms_result.status == "sent"
    assert wa_result.status == "sent"


def test_kvkk_opt_in_blocks(tmp_path: Path):
    service = make_service(tmp_path)
    repo = IntegrationRepo(service.db.conn)
    repo.consent_set(1, "90555", "sms", 0)

    outbox_id = repo.notification_outbox_add(1, "sms", "90555", "", "hello", "sms")
    result = service.notifications.send_notification(1, "sms", "90555", "", "hello", outbox_id)

    row = service.db.conn.execute("SELECT status FROM delivery_log WHERE notification_id = ?", (outbox_id,)).fetchone()
    assert result.status == "blocked"
    assert row[0] == "blocked"


def test_csv_export(tmp_path: Path):
    service = make_service(tmp_path)
    seed_invoice_data(service.db)

    output_dir = tmp_path / "exports"
    paths = service.export_csv(output_dir)

    assert all(p.exists() for p in paths)
    assert any(p.stat().st_size > 0 for p in paths)


def test_csv_import_staging_with_errors(tmp_path: Path):
    service = make_service(tmp_path)
    csv_path = tmp_path / "import.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "ad"])
        writer.writerow(["", ""])  # empty row -> error
        writer.writerow(["1", "Test"])

    ok, failed = service.import_csv("cariler", csv_path)
    rows = service.db.conn.execute("SELECT status FROM import_items ORDER BY id").fetchall()

    assert ok == 1
    assert failed == 1
    assert rows[0][0] == "failed"
    assert rows[1][0] == "staged"


def test_bank_statement_unique_hash(tmp_path: Path):
    service = make_service(tmp_path)
    csv_path = tmp_path / "bank.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["tarih", "tutar", "aciklama"])
        writer.writerow(["2024-01-10", "100", "Payment"])
        writer.writerow(["2024-01-10", "100", "Payment"])

    service.import_bank_csv("TestBank", "2024-01-01", "2024-01-31", csv_path)
    count = service.db.conn.execute("SELECT COUNT(*) FROM bank_transactions").fetchone()[0]
    assert count == 1


def test_auto_reconcile(tmp_path: Path):
    service = make_service(tmp_path)
    seed_invoice_data(service.db)

    csv_path = tmp_path / "bank.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["tarih", "tutar", "aciklama"])
        writer.writerow(["2024-01-12", "100", "FTR-0001"])

    service.import_bank_csv("TestBank", "2024-01-01", "2024-01-31", csv_path)
    matched = service.auto_reconcile()
    row = service.db.conn.execute("SELECT matched FROM bank_transactions").fetchone()

    assert matched == 1
    assert row[0] == 1


def test_manual_reconcile(tmp_path: Path):
    service = make_service(tmp_path)
    csv_path = tmp_path / "bank.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["tarih", "tutar", "aciklama"])
        writer.writerow(["2024-01-12", "50", "Manual"])

    service.import_bank_csv("TestBank", "2024-01-01", "2024-01-31", csv_path)
    tx_id = service.db.conn.execute("SELECT id FROM bank_transactions").fetchone()[0]
    service.manual_reconcile(tx_id, "manual:1")
    row = service.db.conn.execute("SELECT matched, matched_ref FROM bank_transactions WHERE id = ?", (tx_id,)).fetchone()
    assert row[0] == 1
    assert row[1] == "manual:1"


def test_api_token_validation_and_scope(tmp_path: Path):
    service = make_service(tmp_path)
    token, _token_id = service.create_api_token("default", ["customers"])

    assert service.validate_api_token(token, scope="customers") is not None
    assert service.validate_api_token(token, scope="invoices") is None


def test_webhook_delivery_signature_and_retry(tmp_path: Path):
    service = make_service(tmp_path)
    repo = IntegrationRepo(service.db.conn)
    ok_id = repo.webhook_subscription_add(1, "https://ok.example", "secret", json.dumps(["*"]))
    fail_id = repo.webhook_subscription_add(1, "https://fail.example", "secret", json.dumps(["*"]))

    service.enqueue_job("webhook_delivery", {"event_type": "invoice.created", "payload": {"id": 1}}, "wh-1")
    service.run_next_job()

    rows = service.db.conn.execute("SELECT status, last_error, subscription_id FROM webhook_deliveries").fetchall()
    statuses = {r[2]: r[0] for r in rows}
    assert statuses.get(ok_id) == "sent"
    assert statuses.get(fail_id) == "failed"

    payload_json = json.dumps({"event_type": "invoice.created", "payload": {"id": 1}}, ensure_ascii=False)
    signature = service.webhooks.sign_payload("secret", payload_json)
    ok_row = next(r for r in rows if r[2] == ok_id)
    assert ok_row[1] == signature


def test_audit_log_entries(tmp_path: Path):
    service = make_service(tmp_path)
    service.emit_event("invoice.created", {"id": 1})
    service.create_api_token("default", ["customers"])
    rows = service.db.conn.execute("SELECT action FROM audit_log ORDER BY id DESC").fetchall()
    actions = {r[0] for r in rows}
    assert "emit_event" in actions
    assert "create_token" in actions
