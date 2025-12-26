# -*- coding: utf-8 -*-
"""Notlar & Hatırlatmalar veritabanı erişim katmanı."""

from __future__ import annotations

import sqlite3
from typing import Iterable, List, Optional, Sequence, Tuple

from ...utils import now_iso


class NotesRemindersRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # -----------------
    # Audit
    # -----------------
    def add_audit_log(
        self,
        company_id: int,
        user_id: int,
        action: str,
        entity: str,
        entity_id: int,
        detail: str = "",
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO audit_log(company_id, entity_type, entity_id, action, actor_id, details, created_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            (
                int(company_id),
                str(entity),
                int(entity_id),
                str(action),
                int(user_id),
                str(detail),
                now_iso(),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    # -----------------
    # Notes
    # -----------------
    def create_note(
        self,
        company_id: int,
        owner_user_id: int,
        title: str,
        body: str,
        category: str,
        priority: str,
        pinned: int,
        scope: str,
        status: str,
    ) -> int:
        ts = now_iso()
        cur = self.conn.execute(
            """
            INSERT INTO notes(company_id, owner_user_id, title, body, category, priority, pinned, scope, status, created_at, updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                int(company_id),
                int(owner_user_id),
                str(title),
                str(body),
                str(category),
                str(priority),
                int(pinned),
                str(scope),
                str(status),
                ts,
                ts,
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def update_note(
        self,
        note_id: int,
        title: str,
        body: str,
        category: str,
        priority: str,
        pinned: int,
        scope: str,
        status: str,
    ) -> None:
        self.conn.execute(
            """
            UPDATE notes
            SET title=?, body=?, category=?, priority=?, pinned=?, scope=?, status=?, updated_at=?
            WHERE id=?
            """,
            (
                str(title),
                str(body),
                str(category),
                str(priority),
                int(pinned),
                str(scope),
                str(status),
                now_iso(),
                int(note_id),
            ),
        )
        self.conn.commit()

    def set_note_status(self, note_id: int, status: str) -> None:
        self.conn.execute(
            "UPDATE notes SET status=?, updated_at=? WHERE id=?",
            (str(status), now_iso(), int(note_id)),
        )
        self.conn.commit()

    def set_note_pinned(self, note_id: int, pinned: int) -> None:
        self.conn.execute(
            "UPDATE notes SET pinned=?, updated_at=? WHERE id=?",
            (int(pinned), now_iso(), int(note_id)),
        )
        self.conn.commit()

    def get_note(self, note_id: int) -> Optional[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM notes WHERE id=?", (int(note_id),)).fetchone()

    def list_notes(
        self,
        company_id: int,
        owner_user_id: int,
        q: str = "",
        category: str = "",
        tag: str = "",
        pinned: Optional[int] = None,
        scope: str = "",
        include_archived: bool = False,
        created_from: str = "",
        created_to: str = "",
    ) -> List[sqlite3.Row]:
        params: List[object] = [int(company_id), int(owner_user_id)]
        where: List[str] = [
            "n.company_id=?",
            "(n.scope != 'personal' OR n.owner_user_id=?)",
        ]
        if not include_archived:
            where.append("n.status != 'archived'")
        if q:
            like = f"%{q}%"
            where.append("(n.title LIKE ? OR n.body LIKE ? OR n.category LIKE ?)")
            params.extend([like, like, like])
        if category:
            where.append("n.category=?")
            params.append(str(category))
        if scope:
            where.append("n.scope=?")
            params.append(str(scope))
        if pinned is not None:
            where.append("n.pinned=?")
            params.append(int(pinned))
        if created_from:
            where.append("n.created_at >= ?")
            params.append(str(created_from))
        if created_to:
            where.append("n.created_at <= ?")
            params.append(str(created_to))
        if tag:
            where.append("EXISTS (SELECT 1 FROM note_tags nt WHERE nt.note_id = n.id AND nt.tag = ?)")
            params.append(str(tag))

        sql = f"""
            SELECT n.*,
                   (SELECT GROUP_CONCAT(tag, ',') FROM note_tags nt WHERE nt.note_id = n.id) AS tags
            FROM notes n
            WHERE {' AND '.join(where)}
            ORDER BY n.pinned DESC, n.updated_at DESC
        """
        return list(self.conn.execute(sql, params))

    def clear_note_tags(self, note_id: int) -> None:
        self.conn.execute("DELETE FROM note_tags WHERE note_id=?", (int(note_id),))
        self.conn.commit()

    def add_note_tags(self, note_id: int, tags: Iterable[str]) -> None:
        ts = now_iso()
        rows = [(int(note_id), str(tag), ts) for tag in tags if tag]
        if not rows:
            return
        self.conn.executemany(
            """
            INSERT INTO note_tags(note_id, tag, created_at)
            VALUES(?,?,?)
            """,
            rows,
        )
        self.conn.commit()

    def add_note_attachment(
        self,
        note_id: int,
        filename: str,
        stored_name: str,
        size_bytes: int,
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO note_attachments(note_id, filename, stored_name, size_bytes, created_at)
            VALUES(?,?,?,?,?)
            """,
            (int(note_id), str(filename), str(stored_name), int(size_bytes), now_iso()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list_note_attachments(self, note_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT id, filename, stored_name, size_bytes, created_at FROM note_attachments WHERE note_id=? ORDER BY created_at DESC",
                (int(note_id),),
            )
        )

    # -----------------
    # Reminders
    # -----------------
    def create_reminder(
        self,
        company_id: int,
        owner_user_id: int,
        title: str,
        body: str,
        due_at: str,
        priority: str,
        status: str,
        assignee_user_id: Optional[int] = None,
        series_id: Optional[int] = None,
    ) -> int:
        ts = now_iso()
        cur = self.conn.execute(
            """
            INSERT INTO reminders(
                company_id, owner_user_id, assignee_user_id, title, body, due_at,
                priority, status, series_id, created_at, updated_at
            )
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                int(company_id),
                int(owner_user_id),
                int(assignee_user_id) if assignee_user_id is not None else None,
                str(title),
                str(body),
                str(due_at),
                str(priority),
                str(status),
                int(series_id) if series_id is not None else None,
                ts,
                ts,
            ),
        )
        self.conn.commit()
        rid = int(cur.lastrowid)
        if series_id is None:
            self.conn.execute("UPDATE reminders SET series_id=? WHERE id=?", (rid, rid))
            self.conn.commit()
        return rid

    def update_reminder(
        self,
        reminder_id: int,
        title: str,
        body: str,
        due_at: str,
        priority: str,
        status: str,
        assignee_user_id: Optional[int],
    ) -> None:
        self.conn.execute(
            """
            UPDATE reminders
            SET title=?, body=?, due_at=?, priority=?, status=?, assignee_user_id=?, updated_at=?
            WHERE id=?
            """,
            (
                str(title),
                str(body),
                str(due_at),
                str(priority),
                str(status),
                int(assignee_user_id) if assignee_user_id is not None else None,
                now_iso(),
                int(reminder_id),
            ),
        )
        self.conn.commit()

    def set_reminder_status(self, reminder_id: int, status: str) -> None:
        self.conn.execute(
            "UPDATE reminders SET status=?, updated_at=? WHERE id=?",
            (str(status), now_iso(), int(reminder_id)),
        )
        self.conn.commit()

    def update_reminder_due(self, reminder_id: int, due_at: str) -> None:
        self.conn.execute(
            "UPDATE reminders SET due_at=?, updated_at=? WHERE id=?",
            (str(due_at), now_iso(), int(reminder_id)),
        )
        self.conn.commit()

    def get_reminder(self, reminder_id: int) -> Optional[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM reminders WHERE id=?", (int(reminder_id),)).fetchone()

    def list_reminders(
        self,
        company_id: int,
        owner_user_id: int,
        q: str = "",
        status: str = "",
        due_from: str = "",
        due_to: str = "",
        include_archived: bool = False,
        only_assigned: bool = False,
    ) -> List[sqlite3.Row]:
        params: List[object] = [int(company_id)]
        where: List[str] = ["company_id=?"]
        if not include_archived:
            where.append("status != 'archived'")
        if only_assigned:
            where.append("assignee_user_id = ?")
            params.append(int(owner_user_id))
        else:
            where.append("(owner_user_id = ? OR assignee_user_id = ?)")
            params.extend([int(owner_user_id), int(owner_user_id)])
        if q:
            like = f"%{q}%"
            where.append("(title LIKE ? OR body LIKE ?)")
            params.extend([like, like])
        if status:
            where.append("status = ?")
            params.append(str(status))
        if due_from:
            where.append("due_at >= ?")
            params.append(str(due_from))
        if due_to:
            where.append("due_at <= ?")
            params.append(str(due_to))
        sql = f"""
            SELECT * FROM reminders
            WHERE {' AND '.join(where)}
            ORDER BY due_at ASC
        """
        return list(self.conn.execute(sql, params))

    def list_due_reminders(
        self,
        company_id: int,
        owner_user_id: int,
        status: str,
        due_before: str,
    ) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                """
                SELECT * FROM reminders
                WHERE company_id=? AND status=? AND due_at <= ?
                  AND (owner_user_id=? OR assignee_user_id=?)
                ORDER BY due_at ASC
                """,
                (int(company_id), str(status), str(due_before), int(owner_user_id), int(owner_user_id)),
            )
        )

    def list_overdue(self, company_id: int, owner_user_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                """
                SELECT * FROM reminders
                WHERE company_id=? AND status='overdue' AND (owner_user_id=? OR assignee_user_id=?)
                ORDER BY due_at ASC
                """,
                (int(company_id), int(owner_user_id), int(owner_user_id)),
            )
        )

    # -----------------
    # Recurrence
    # -----------------
    def upsert_recurrence(
        self,
        reminder_id: int,
        frequency: str,
        interval: int,
        until: str,
        byweekday: str,
        bymonthday: str,
        active: int,
    ) -> None:
        ts = now_iso()
        self.conn.execute(
            """
            INSERT INTO reminder_recurrence(
                reminder_id, frequency, interval, until, byweekday, bymonthday, active, created_at, updated_at
            )
            VALUES(?,?,?,?,?,?,?,?,?)
            ON CONFLICT(reminder_id) DO UPDATE SET
                frequency=excluded.frequency,
                interval=excluded.interval,
                until=excluded.until,
                byweekday=excluded.byweekday,
                bymonthday=excluded.bymonthday,
                active=excluded.active,
                updated_at=excluded.updated_at
            """,
            (
                int(reminder_id),
                str(frequency),
                int(interval),
                str(until),
                str(byweekday),
                str(bymonthday),
                int(active),
                ts,
                ts,
            ),
        )
        self.conn.commit()

    def get_recurrence(self, reminder_id: int) -> Optional[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM reminder_recurrence WHERE reminder_id=?",
            (int(reminder_id),),
        ).fetchone()

    def set_recurrence_active(self, reminder_id: int, active: int) -> None:
        self.conn.execute(
            "UPDATE reminder_recurrence SET active=?, updated_at=? WHERE reminder_id=?",
            (int(active), now_iso(), int(reminder_id)),
        )
        self.conn.commit()

    # -----------------
    # Links
    # -----------------
    def add_reminder_link(self, reminder_id: int, linked_type: str, linked_id: str) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO reminder_links(reminder_id, linked_type, linked_id, created_at)
            VALUES(?,?,?,?)
            """,
            (int(reminder_id), str(linked_type), str(linked_id), now_iso()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list_reminder_links(self, reminder_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT linked_type, linked_id, created_at FROM reminder_links WHERE reminder_id=?",
                (int(reminder_id),),
            )
        )

    # -----------------
    # Reports
    # -----------------
    def report_completed_by_user(self, company_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                """
                SELECT owner_user_id, COUNT(*) AS completed_count
                FROM reminders
                WHERE company_id=? AND status='done'
                GROUP BY owner_user_id
                ORDER BY completed_count DESC
                """,
                (int(company_id),),
            )
        )

    def report_missed_by_user(self, company_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                """
                SELECT owner_user_id, COUNT(*) AS missed_count
                FROM reminders
                WHERE company_id=? AND status='overdue'
                GROUP BY owner_user_id
                ORDER BY missed_count DESC
                """,
                (int(company_id),),
            )
        )

    def report_notes_by_category(self, company_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                """
                SELECT category, COUNT(*) AS note_count
                FROM notes
                WHERE company_id=? AND status != 'archived'
                GROUP BY category
                ORDER BY note_count DESC
                """,
                (int(company_id),),
            )
        )

    def report_notes_by_tag(self, company_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                """
                SELECT tag, COUNT(*) AS note_count
                FROM note_tags nt
                JOIN notes n ON n.id = nt.note_id
                WHERE n.company_id=? AND n.status != 'archived'
                GROUP BY tag
                ORDER BY note_count DESC
                """,
                (int(company_id),),
            )
        )
