# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .storage import store_attachment
from .constants import TASK_STATUSES


@dataclass
class DmsService:
    db: object
    storage_base_dir: Optional[str] = None

    def _company_id(self, company_id: Optional[int]) -> int:
        return int(company_id or 1)

    def create_document(
        self,
        company_id: Optional[int],
        title: str,
        doc_type: str,
        status: str,
        tags: List[str],
        actor_id: Optional[int],
    ) -> int:
        cid = self._company_id(company_id)
        doc_id = self.db.dms.create_document(cid, title, doc_type, status, tags)
        self.db.dms.log_audit(cid, "document", doc_id, "create_doc", actor_id, f"{title}")
        return doc_id

    def update_document(
        self,
        company_id: Optional[int],
        document_id: int,
        title: str,
        doc_type: str,
        status: str,
        tags: List[str],
        actor_id: Optional[int],
    ) -> None:
        cid = self._company_id(company_id)
        self.db.dms.update_document(cid, document_id, title, doc_type, status, tags)
        self.db.dms.log_audit(cid, "document", document_id, "update_doc", actor_id, f"{title}")

    def archive_document(self, company_id: Optional[int], document_id: int, actor_id: Optional[int]) -> None:
        cid = self._company_id(company_id)
        self.db.dms.archive_document(cid, document_id)
        self.db.dms.log_audit(cid, "document", document_id, "archive", actor_id, "")

    def add_document_link(
        self,
        company_id: Optional[int],
        document_id: int,
        entity_type: str,
        entity_id: str,
        actor_id: Optional[int],
    ) -> int:
        cid = self._company_id(company_id)
        link_id = self.db.dms.add_document_link(cid, document_id, entity_type, entity_id)
        self.db.dms.log_audit(cid, "document", document_id, "link_entity", actor_id, f"{entity_type}:{entity_id}")
        return link_id

    def upload_version(
        self,
        company_id: Optional[int],
        document_id: int,
        source_path: str,
        original_name: str,
        change_note: str,
        actor_id: Optional[int],
    ) -> int:
        cid = self._company_id(company_id)
        next_version = self.db.dms.next_version_no(cid, document_id)
        stored = store_attachment(
            company_id=cid,
            document_id=document_id,
            version_no=next_version,
            source_path=source_path,
            original_name=original_name,
            base_dir=self.storage_base_dir,
        )
        version_id = self.db.dms.add_version(
            cid,
            document_id,
            next_version,
            stored.file_path,
            stored.original_name,
            stored.mime,
            stored.size,
            stored.sha256,
            change_note,
        )
        self.db.dms.log_audit(cid, "document", document_id, "upload_version", actor_id, f"v{next_version}")
        return version_id

    def start_workflow(
        self,
        company_id: Optional[int],
        document_id: int,
        template_id: int,
        actor_id: Optional[int],
    ) -> int:
        cid = self._company_id(company_id)
        instance_id = self.db.dms.start_workflow(cid, template_id, document_id, actor_id)
        self.db.dms.log_audit(cid, "workflow", instance_id, "start_workflow", actor_id, f"doc:{document_id}")
        return instance_id

    def workflow_approve(self, company_id: Optional[int], instance_id: int, actor_id: Optional[int], comment: str) -> None:
        cid = self._company_id(company_id)
        self.db.dms.act_workflow(cid, instance_id, "approve", actor_id, comment)
        self.db.dms.log_audit(cid, "workflow", instance_id, "approve", actor_id, comment)

    def workflow_reject(self, company_id: Optional[int], instance_id: int, actor_id: Optional[int], comment: str) -> None:
        cid = self._company_id(company_id)
        self.db.dms.act_workflow(cid, instance_id, "reject", actor_id, comment)
        self.db.dms.log_audit(cid, "workflow", instance_id, "reject", actor_id, comment)

    def workflow_request_revision(
        self, company_id: Optional[int], instance_id: int, actor_id: Optional[int], comment: str
    ) -> None:
        cid = self._company_id(company_id)
        self.db.dms.act_workflow(cid, instance_id, "revise", actor_id, comment)
        self.db.dms.log_audit(cid, "workflow", instance_id, "request_revision", actor_id, comment)

    def create_task(
        self,
        company_id: Optional[int],
        document_id: int,
        title: str,
        assignee_id: int,
        due_at: str,
        actor_id: Optional[int],
    ) -> int:
        cid = self._company_id(company_id)
        task_id = self.db.dms.create_task(cid, document_id, title, assignee_id, due_at)
        self.db.dms.log_audit(cid, "task", task_id, "assign_task", actor_id, f"doc:{document_id}")
        return task_id

    def complete_task(self, company_id: Optional[int], task_id: int, actor_id: Optional[int]) -> None:
        cid = self._company_id(company_id)
        self.db.dms.update_task_status(cid, task_id, TASK_STATUSES[-1])
        self.db.dms.log_audit(cid, "task", task_id, "complete_task", actor_id, "")

    def create_reminder(
        self,
        company_id: Optional[int],
        document_id: int,
        remind_at: str,
        actor_id: Optional[int],
    ) -> int:
        cid = self._company_id(company_id)
        reminder_id = self.db.dms.create_reminder(cid, document_id, remind_at)
        self.db.dms.log_audit(cid, "reminder", reminder_id, "create_reminder", actor_id, "")
        return reminder_id
