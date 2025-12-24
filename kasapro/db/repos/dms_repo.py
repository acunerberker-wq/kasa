# -*- coding: utf-8 -*-
from __future__ import annotations

import sqlite3
from typing import List, Optional, Sequence, Tuple


class DmsRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create_document(self, company_id: int, title: str, doc_type: str, status: str, tags: Sequence[str]) -> int:
        self.conn.execute(
            "INSERT INTO documents(company_id,title,doc_type,status) VALUES(?,?,?,?)",
            (int(company_id), title.strip(), doc_type.strip(), status.strip()),
        )
        doc_id = int(self.conn.execute("SELECT last_insert_rowid() id").fetchone()[0])
        self._set_tags(company_id, doc_id, tags)
        self.conn.commit()
        return doc_id

    def update_document(
        self, company_id: int, document_id: int, title: str, doc_type: str, status: str, tags: Sequence[str]
    ) -> None:
        self.conn.execute(
            "UPDATE documents SET title=?, doc_type=?, status=?, updated_at=CURRENT_TIMESTAMP "
            "WHERE id=? AND company_id=?",
            (title.strip(), doc_type.strip(), status.strip(), int(document_id), int(company_id)),
        )
        self._set_tags(company_id, document_id, tags)
        self.conn.commit()

    def archive_document(self, company_id: int, document_id: int) -> None:
        self.conn.execute(
            "UPDATE documents SET status='ARCHIVED', updated_at=CURRENT_TIMESTAMP WHERE id=? AND company_id=?",
            (int(document_id), int(company_id)),
        )
        self.conn.commit()

    def list_documents(
        self,
        company_id: int,
        q: str = "",
        status: str = "",
        doc_type: str = "",
        tag: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> List[sqlite3.Row]:
        clauses = ["d.company_id=?"]
        params: List[object] = [int(company_id)]
        if q:
            clauses.append("d.title LIKE ?")
            params.append(f"%{q.strip()}%")
        if status:
            clauses.append("d.status=?")
            params.append(status.strip())
        if doc_type:
            clauses.append("d.doc_type=?")
            params.append(doc_type.strip())
        if tag:
            clauses.append("dt.tag=?")
            params.append(tag.strip())
        where = " AND ".join(clauses)
        return list(
            self.conn.execute(
                "SELECT DISTINCT d.* FROM documents d "
                "LEFT JOIN document_tags dt ON dt.document_id=d.id AND dt.company_id=d.company_id "
                f"WHERE {where} ORDER BY d.updated_at DESC LIMIT ? OFFSET ?",
                tuple(params + [int(limit), int(offset)]),
            )
        )

    def get_document(self, company_id: int, document_id: int) -> Optional[sqlite3.Row]:
        cur = self.conn.execute(
            "SELECT * FROM documents WHERE id=? AND company_id=?",
            (int(document_id), int(company_id)),
        )
        return cur.fetchone()

    def list_tags(self, company_id: int, document_id: int) -> List[str]:
        cur = self.conn.execute(
            "SELECT tag FROM document_tags WHERE document_id=? AND company_id=? ORDER BY tag",
            (int(document_id), int(company_id)),
        )
        return [str(r[0]) for r in cur.fetchall()]

    def add_document_link(self, company_id: int, document_id: int, entity_type: str, entity_id: str) -> int:
        self.conn.execute(
            "INSERT INTO document_links(company_id,document_id,entity_type,entity_id) VALUES(?,?,?,?)",
            (int(company_id), int(document_id), entity_type.strip(), str(entity_id).strip()),
        )
        self.conn.commit()
        return int(self.conn.execute("SELECT last_insert_rowid() id").fetchone()[0])

    def list_document_links(self, company_id: int, document_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM document_links WHERE document_id=? AND company_id=? ORDER BY created_at DESC",
                (int(document_id), int(company_id)),
            )
        )

    def next_version_no(self, company_id: int, document_id: int) -> int:
        cur = self.conn.execute(
            "SELECT COALESCE(MAX(version_no),0) FROM document_versions WHERE document_id=? AND company_id=?",
            (int(document_id), int(company_id)),
        )
        return int(cur.fetchone()[0]) + 1

    def add_version(
        self,
        company_id: int,
        document_id: int,
        version_no: int,
        file_path: str,
        original_name: str,
        mime: str,
        size: int,
        sha256: str,
        change_note: str,
    ) -> int:
        self.conn.execute(
            "INSERT INTO document_versions("
            "company_id,document_id,version_no,file_path,original_name,mime,size,sha256,change_note,status"
            ") VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                int(company_id),
                int(document_id),
                int(version_no),
                file_path,
                original_name,
                mime,
                int(size),
                sha256,
                change_note.strip(),
                "DRAFT",
            ),
        )
        version_id = int(self.conn.execute("SELECT last_insert_rowid() id").fetchone()[0])
        self.conn.execute(
            "UPDATE documents SET current_version_id=?, updated_at=CURRENT_TIMESTAMP "
            "WHERE id=? AND company_id=?",
            (version_id, int(document_id), int(company_id)),
        )
        self.conn.commit()
        return version_id

    def list_versions(self, company_id: int, document_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM document_versions WHERE document_id=? AND company_id=? ORDER BY version_no DESC",
                (int(document_id), int(company_id)),
            )
        )

    def set_version_status(self, company_id: int, version_id: int, status: str) -> None:
        self.conn.execute(
            "UPDATE document_versions SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND company_id=?",
            (status.strip(), int(version_id), int(company_id)),
        )
        self.conn.commit()

    def create_workflow_template(self, company_id: int, name: str, entity_type: str) -> int:
        self.conn.execute(
            "INSERT INTO workflow_templates(company_id,name,entity_type) VALUES(?,?,?)",
            (int(company_id), name.strip(), entity_type.strip()),
        )
        self.conn.commit()
        return int(self.conn.execute("SELECT last_insert_rowid() id").fetchone()[0])

    def add_workflow_step(
        self,
        company_id: int,
        template_id: int,
        step_no: int,
        name: str,
        approver_role: str,
        approver_user_id: Optional[int],
    ) -> int:
        self.conn.execute(
            "INSERT INTO workflow_steps(company_id,template_id,step_no,name,approver_role,approver_user_id) "
            "VALUES(?,?,?,?,?,?)",
            (
                int(company_id),
                int(template_id),
                int(step_no),
                name.strip(),
                approver_role.strip(),
                int(approver_user_id) if approver_user_id else None,
            ),
        )
        self.conn.commit()
        return int(self.conn.execute("SELECT last_insert_rowid() id").fetchone()[0])

    def list_workflow_templates(self, company_id: int, entity_type: str) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM workflow_templates WHERE company_id=? AND entity_type=? AND is_active=1 ORDER BY name",
                (int(company_id), entity_type.strip()),
            )
        )

    def list_workflow_steps(self, company_id: int, template_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM workflow_steps WHERE company_id=? AND template_id=? ORDER BY step_no",
                (int(company_id), int(template_id)),
            )
        )

    def start_workflow(self, company_id: int, template_id: int, document_id: int, actor_id: Optional[int]) -> int:
        steps = self.list_workflow_steps(company_id, template_id)
        if not steps:
            raise ValueError("Workflow adımı bulunamadı.")
        first_step = int(steps[0]["step_no"])
        self.conn.execute(
            "INSERT INTO workflow_instances(company_id,template_id,document_id,status,current_step_no,started_by) "
            "VALUES(?,?,?,?,?,?)",
            (int(company_id), int(template_id), int(document_id), "IN_REVIEW", first_step, actor_id),
        )
        instance_id = int(self.conn.execute("SELECT last_insert_rowid() id").fetchone()[0])
        self.conn.commit()
        return instance_id

    def list_pending_approvals(self, company_id: int, user_id: int, role: str) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT wi.*, wt.name template_name, d.title doc_title FROM workflow_instances wi "
                "JOIN workflow_templates wt ON wt.id=wi.template_id "
                "JOIN documents d ON d.id=wi.document_id "
                "JOIN workflow_steps ws ON ws.template_id=wi.template_id AND ws.step_no=wi.current_step_no "
                "WHERE wi.company_id=? AND wi.status='IN_REVIEW' AND "
                "(ws.approver_user_id=? OR ws.approver_role=?) ORDER BY wi.updated_at DESC",
                (int(company_id), int(user_id), role.strip()),
            )
        )

    def act_workflow(
        self,
        company_id: int,
        instance_id: int,
        action: str,
        actor_id: Optional[int],
        comment: str,
    ) -> None:
        instance = self.conn.execute(
            "SELECT * FROM workflow_instances WHERE id=? AND company_id=?",
            (int(instance_id), int(company_id)),
        ).fetchone()
        if not instance:
            raise ValueError("Workflow bulunamadı.")

        step_no = int(instance["current_step_no"] or 0)
        self.conn.execute(
            "INSERT INTO workflow_actions(company_id,instance_id,step_no,action,comment,actor_id) "
            "VALUES(?,?,?,?,?,?)",
            (int(company_id), int(instance_id), step_no, action, comment.strip(), actor_id),
        )

        if action == "approve":
            steps = self.list_workflow_steps(company_id, int(instance["template_id"]))
            next_step = None
            for step in steps:
                if int(step["step_no"]) > step_no:
                    next_step = int(step["step_no"])
                    break
            if next_step:
                self.conn.execute(
                    "UPDATE workflow_instances SET current_step_no=?, updated_at=CURRENT_TIMESTAMP "
                    "WHERE id=? AND company_id=?",
                    (next_step, int(instance_id), int(company_id)),
                )
            else:
                self.conn.execute(
                    "UPDATE workflow_instances SET status='COMPLETED', updated_at=CURRENT_TIMESTAMP "
                    "WHERE id=? AND company_id=?",
                    (int(instance_id), int(company_id)),
                )
                self.conn.execute(
                    "UPDATE documents SET status='APPROVED', updated_at=CURRENT_TIMESTAMP "
                    "WHERE id=? AND company_id=?",
                    (int(instance["document_id"]), int(company_id)),
                )
        elif action == "reject":
            self.conn.execute(
                "UPDATE workflow_instances SET status='REJECTED', updated_at=CURRENT_TIMESTAMP "
                "WHERE id=? AND company_id=?",
                (int(instance_id), int(company_id)),
            )
            self.conn.execute(
                "UPDATE documents SET status='REJECTED', updated_at=CURRENT_TIMESTAMP "
                "WHERE id=? AND company_id=?",
                (int(instance["document_id"]), int(company_id)),
            )
        elif action == "revise":
            self.conn.execute(
                "UPDATE workflow_instances SET status='REVISION_REQUESTED', updated_at=CURRENT_TIMESTAMP "
                "WHERE id=? AND company_id=?",
                (int(instance_id), int(company_id)),
            )
            self.conn.execute(
                "UPDATE documents SET status='REVISION_REQUESTED', updated_at=CURRENT_TIMESTAMP "
                "WHERE id=? AND company_id=?",
                (int(instance["document_id"]), int(company_id)),
            )
        self.conn.commit()

    def list_workflow_actions(self, company_id: int, instance_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM workflow_actions WHERE company_id=? AND instance_id=? ORDER BY acted_at DESC",
                (int(company_id), int(instance_id)),
            )
        )

    def list_workflows_for_document(self, company_id: int, document_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT wi.*, wt.name template_name FROM workflow_instances wi "
                "JOIN workflow_templates wt ON wt.id=wi.template_id "
                "WHERE wi.company_id=? AND wi.document_id=? ORDER BY wi.updated_at DESC",
                (int(company_id), int(document_id)),
            )
        )

    def create_task(self, company_id: int, document_id: int, title: str, assignee_id: int, due_at: str) -> int:
        self.conn.execute(
            "INSERT INTO tasks(company_id,document_id,title,assignee_id,due_at,status) VALUES(?,?,?,?,?,?)",
            (int(company_id), int(document_id), title.strip(), int(assignee_id), due_at, "OPEN"),
        )
        self.conn.commit()
        return int(self.conn.execute("SELECT last_insert_rowid() id").fetchone()[0])

    def update_task_status(self, company_id: int, task_id: int, status: str) -> None:
        self.conn.execute(
            "UPDATE tasks SET status=?, completed_at=CASE WHEN ?='DONE' THEN CURRENT_TIMESTAMP ELSE completed_at END "
            "WHERE id=? AND company_id=?",
            (status.strip(), status.strip(), int(task_id), int(company_id)),
        )
        self.conn.commit()

    def list_tasks_by_assignee(self, company_id: int, assignee_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT t.*, d.title doc_title FROM tasks t "
                "LEFT JOIN documents d ON d.id=t.document_id "
                "WHERE t.company_id=? AND t.assignee_id=? ORDER BY t.due_at",
                (int(company_id), int(assignee_id)),
            )
        )

    def list_tasks_for_document(self, company_id: int, document_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT t.* FROM tasks t WHERE t.company_id=? AND t.document_id=? ORDER BY t.due_at",
                (int(company_id), int(document_id)),
            )
        )

    def create_reminder(self, company_id: int, document_id: int, remind_at: str) -> int:
        self.conn.execute(
            "INSERT INTO reminders(company_id,document_id,remind_at,status) VALUES(?,?,?,?)",
            (int(company_id), int(document_id), remind_at, "PENDING"),
        )
        self.conn.commit()
        return int(self.conn.execute("SELECT last_insert_rowid() id").fetchone()[0])

    def list_due_reminders(self, company_id: int, now_iso: str) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT r.*, d.title doc_title FROM reminders r "
                "LEFT JOIN documents d ON d.id=r.document_id "
                "WHERE r.company_id=? AND r.status='PENDING' AND r.remind_at<=? ORDER BY r.remind_at",
                (int(company_id), now_iso),
            )
        )

    def mark_reminder_snoozed(self, company_id: int, reminder_id: int, snooze_until: str) -> None:
        self.conn.execute(
            "UPDATE reminders SET status='SNOOZED', snooze_until=? WHERE id=? AND company_id=?",
            (snooze_until, int(reminder_id), int(company_id)),
        )
        self.conn.commit()

    def log_audit(
        self,
        company_id: int,
        entity_type: str,
        entity_id: int,
        action: str,
        actor_id: Optional[int],
        details: str,
    ) -> None:
        self.conn.execute(
            "INSERT INTO audit_log(company_id,entity_type,entity_id,action,actor_id,details) VALUES(?,?,?,?,?,?)",
            (int(company_id), entity_type, int(entity_id), action, actor_id, details),
        )
        self.conn.commit()

    def list_audit(self, company_id: int, entity_type: str, entity_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM audit_log WHERE company_id=? AND entity_type=? AND entity_id=? ORDER BY created_at DESC",
                (int(company_id), entity_type, int(entity_id)),
            )
        )

    def _set_tags(self, company_id: int, document_id: int, tags: Sequence[str]) -> None:
        self.conn.execute(
            "DELETE FROM document_tags WHERE company_id=? AND document_id=?",
            (int(company_id), int(document_id)),
        )
        clean_tags = sorted({t.strip() for t in tags if t and t.strip()})
        for tag in clean_tags:
            self.conn.execute(
                "INSERT INTO document_tags(company_id,document_id,tag) VALUES(?,?,?)",
                (int(company_id), int(document_id), tag),
            )

    def list_documents_for_link(self, company_id: int, entity_type: str, entity_id: str) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT d.* FROM document_links dl "
                "JOIN documents d ON d.id=dl.document_id "
                "WHERE dl.company_id=? AND dl.entity_type=? AND dl.entity_id=?",
                (int(company_id), entity_type.strip(), str(entity_id).strip()),
            )
        )

    def list_reminders(self, company_id: int, status: str = "") -> List[sqlite3.Row]:
        clauses = ["company_id=?"]
        params: List[object] = [int(company_id)]
        if status:
            clauses.append("status=?")
            params.append(status.strip())
        where = " AND ".join(clauses)
        return list(
            self.conn.execute(
                f"SELECT * FROM reminders WHERE {where} ORDER BY remind_at",
                tuple(params),
            )
        )

    def get_task(self, company_id: int, task_id: int) -> Optional[sqlite3.Row]:
        cur = self.conn.execute(
            "SELECT * FROM tasks WHERE company_id=? AND id=?",
            (int(company_id), int(task_id)),
        )
        return cur.fetchone()

    def get_workflow_instance(self, company_id: int, instance_id: int) -> Optional[sqlite3.Row]:
        cur = self.conn.execute(
            "SELECT * FROM workflow_instances WHERE company_id=? AND id=?",
            (int(company_id), int(instance_id)),
        )
        return cur.fetchone()

    def get_document_versions_for_current(self, company_id: int, document_id: int) -> Optional[sqlite3.Row]:
        cur = self.conn.execute(
            "SELECT dv.* FROM document_versions dv "
            "JOIN documents d ON d.current_version_id=dv.id "
            "WHERE d.company_id=? AND d.id=?",
            (int(company_id), int(document_id)),
        )
        return cur.fetchone()

    def list_document_summary(self, company_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT d.*, dv.version_no current_version_no FROM documents d "
                "LEFT JOIN document_versions dv ON dv.id=d.current_version_id "
                "WHERE d.company_id=? ORDER BY d.updated_at DESC",
                (int(company_id),),
            )
        )

    def list_tasks_dashboard(self, company_id: int, assignee_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT t.*, d.title doc_title FROM tasks t "
                "LEFT JOIN documents d ON d.id=t.document_id "
                "WHERE t.company_id=? AND t.assignee_id=? AND t.status!='DONE' ORDER BY t.due_at",
                (int(company_id), int(assignee_id)),
            )
        )

    def list_overdue_tasks(self, company_id: int, assignee_id: int, now_iso: str) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT t.*, d.title doc_title FROM tasks t "
                "LEFT JOIN documents d ON d.id=t.document_id "
                "WHERE t.company_id=? AND t.assignee_id=? AND t.status!='DONE' AND t.due_at<=? "
                "ORDER BY t.due_at",
                (int(company_id), int(assignee_id), now_iso),
            )
        )

    def list_audit_all(self, company_id: int, limit: int = 200) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM audit_log WHERE company_id=? ORDER BY created_at DESC LIMIT ?",
                (int(company_id), int(limit)),
            )
        )
