# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from kasapro.db.main_db import DB
from kasapro.modules.dms.service import DmsService


def _create_db(tmp_path: Path) -> DB:
    db_path = tmp_path / "dms_test.db"
    return DB(str(db_path))


def _create_service(db: DB, tmp_path: Path) -> DmsService:
    return DmsService(db=db, storage_base_dir=str(tmp_path))


def _create_pdf(tmp_path: Path, name: str = "sample.pdf") -> Path:
    path = tmp_path / name
    path.write_bytes(b"%PDF-1.4 sample content")
    return path


def _create_template(db: DB, company_id: int, steps: int = 2) -> int:
    template_id = db.dms.create_workflow_template(company_id, "Test Onay", "document")
    for step in range(1, steps + 1):
        db.dms.add_workflow_step(company_id, template_id, step, f"Adim {step}", "admin", None)
    return template_id


def test_document_create_tag_and_link(tmp_path: Path) -> None:
    db = _create_db(tmp_path)
    service = _create_service(db, tmp_path)
    doc_id = service.create_document(1, "Sözleşme A", "Sözleşme", "ACTIVE", ["kritik", "2024"], 1)
    service.add_document_link(1, doc_id, "contract", "C-1", 1)

    doc = db.dms.get_document(1, doc_id)
    assert doc is not None
    assert doc["title"] == "Sözleşme A"
    assert set(db.dms.list_tags(1, doc_id)) == {"kritik", "2024"}
    links = db.dms.list_document_links(1, doc_id)
    assert len(links) == 1
    assert links[0]["entity_type"] == "contract"


def test_upload_version_v1_sets_current(tmp_path: Path) -> None:
    db = _create_db(tmp_path)
    service = _create_service(db, tmp_path)
    doc_id = service.create_document(1, "Teklif", "Teklif", "ACTIVE", [], 1)
    file_path = _create_pdf(tmp_path)

    version_id = service.upload_version(1, doc_id, str(file_path), "sample.pdf", "v1", 1)
    doc = db.dms.get_document(1, doc_id)
    assert doc["current_version_id"] == version_id


def test_upload_version_v2_updates_current(tmp_path: Path) -> None:
    db = _create_db(tmp_path)
    service = _create_service(db, tmp_path)
    doc_id = service.create_document(1, "Teklif", "Teklif", "ACTIVE", [], 1)
    file_path = _create_pdf(tmp_path, "v1.pdf")
    service.upload_version(1, doc_id, str(file_path), "v1.pdf", "v1", 1)

    file_path2 = _create_pdf(tmp_path, "v2.pdf")
    version_id = service.upload_version(1, doc_id, str(file_path2), "v2.pdf", "v2", 1)
    doc = db.dms.get_document(1, doc_id)
    assert doc["current_version_id"] == version_id


def test_start_workflow_shows_pending(tmp_path: Path) -> None:
    db = _create_db(tmp_path)
    service = _create_service(db, tmp_path)
    doc_id = service.create_document(1, "Tutanak", "Tutanak", "ACTIVE", [], 1)
    template_id = _create_template(db, 1, steps=1)

    service.start_workflow(1, doc_id, template_id, 1)
    pending = db.dms.list_pending_approvals(1, 1, "admin")
    assert len(pending) == 1


def test_approve_moves_to_next_step(tmp_path: Path) -> None:
    db = _create_db(tmp_path)
    service = _create_service(db, tmp_path)
    doc_id = service.create_document(1, "Tutanak", "Tutanak", "ACTIVE", [], 1)
    template_id = _create_template(db, 1, steps=2)
    instance_id = service.start_workflow(1, doc_id, template_id, 1)

    service.workflow_approve(1, instance_id, 1, "onay")
    instance = db.dms.get_workflow_instance(1, instance_id)
    assert instance["current_step_no"] == 2


def test_revision_requested_sets_status(tmp_path: Path) -> None:
    db = _create_db(tmp_path)
    service = _create_service(db, tmp_path)
    doc_id = service.create_document(1, "Tutanak", "Tutanak", "ACTIVE", [], 1)
    template_id = _create_template(db, 1, steps=1)
    instance_id = service.start_workflow(1, doc_id, template_id, 1)

    service.workflow_request_revision(1, instance_id, 1, "revize")
    instance = db.dms.get_workflow_instance(1, instance_id)
    assert instance["status"] == "REVISION_REQUESTED"


def test_reject_sets_status(tmp_path: Path) -> None:
    db = _create_db(tmp_path)
    service = _create_service(db, tmp_path)
    doc_id = service.create_document(1, "Tutanak", "Tutanak", "ACTIVE", [], 1)
    template_id = _create_template(db, 1, steps=1)
    instance_id = service.start_workflow(1, doc_id, template_id, 1)

    service.workflow_reject(1, instance_id, 1, "red")
    instance = db.dms.get_workflow_instance(1, instance_id)
    assert instance["status"] == "REJECTED"


def test_task_assignment_visible_to_assignee(tmp_path: Path) -> None:
    db = _create_db(tmp_path)
    service = _create_service(db, tmp_path)
    doc_id = service.create_document(1, "Hakediş", "Hakediş", "ACTIVE", [], 1)
    task_id = service.create_task(1, doc_id, "İncele", 2, "2024-01-01", 1)

    tasks = db.dms.list_tasks_by_assignee(1, 2)
    assert any(task["id"] == task_id for task in tasks)


def test_task_complete_sets_done(tmp_path: Path) -> None:
    db = _create_db(tmp_path)
    service = _create_service(db, tmp_path)
    doc_id = service.create_document(1, "Hakediş", "Hakediş", "ACTIVE", [], 1)
    task_id = service.create_task(1, doc_id, "İncele", 2, "2024-01-01", 1)

    service.complete_task(1, task_id, 1)
    task = db.dms.get_task(1, task_id)
    assert task["status"] == "DONE"


def test_reminder_due_list(tmp_path: Path) -> None:
    db = _create_db(tmp_path)
    service = _create_service(db, tmp_path)
    doc_id = service.create_document(1, "Genel", "Genel", "ACTIVE", [], 1)
    remind_at = (datetime.now() - timedelta(days=1)).isoformat()
    service.create_reminder(1, doc_id, remind_at, 1)

    due = db.dms.list_due_reminders(1, datetime.now().isoformat())
    assert len(due) == 1


def test_path_traversal_is_blocked(tmp_path: Path) -> None:
    db = _create_db(tmp_path)
    service = _create_service(db, tmp_path)
    doc_id = service.create_document(1, "Teklif", "Teklif", "ACTIVE", [], 1)
    file_path = _create_pdf(tmp_path)

    with pytest.raises(ValueError):
        service.upload_version(1, doc_id, str(file_path), "../evil.pdf", "", 1)


def test_audit_log_records_actions(tmp_path: Path) -> None:
    db = _create_db(tmp_path)
    service = _create_service(db, tmp_path)
    doc_id = service.create_document(1, "Sözleşme", "Sözleşme", "ACTIVE", [], 1)
    file_path = _create_pdf(tmp_path)
    service.upload_version(1, doc_id, str(file_path), "sample.pdf", "v1", 1)
    template_id = _create_template(db, 1, steps=1)
    instance_id = service.start_workflow(1, doc_id, template_id, 1)
    service.workflow_approve(1, instance_id, 1, "ok")
    task_id = service.create_task(1, doc_id, "Kontrol", 2, "2024-01-01", 1)
    service.complete_task(1, task_id, 1)
    service.archive_document(1, doc_id, 1)

    audit = db.dms.list_audit_all(1)
    actions = {row["action"] for row in audit}
    assert {"create_doc", "upload_version", "start_workflow", "approve", "assign_task", "complete_task", "archive"}.issubset(actions)
