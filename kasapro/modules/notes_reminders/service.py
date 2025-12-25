# -*- coding: utf-8 -*-
"""Notlar & Hatırlatmalar iş kuralları."""

from __future__ import annotations

import logging
import os
import re
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from ...config import MESSAGE_ATTACHMENTS_DIRNAME, MESSAGE_ATTACHMENT_MAX_BYTES
from ...db.main_db import DB
from ...db.users_db import UsersDB
from ...utils import now_iso

logger = logging.getLogger(__name__)


@dataclass
class RecurrenceRule:
    frequency: str
    interval: int = 1
    until: str = ""
    byweekday: Sequence[int] = ()
    bymonthday: str = ""


class NotesRemindersService:
    def __init__(self, db: DB, usersdb: UsersDB):
        self.db = db
        self.usersdb = usersdb

    # -----------------
    # Helpers
    # -----------------
    def _company_id(self, company_id: Optional[int]) -> int:
        return int(company_id or 1)

    def _attachments_root(self) -> str:
        data_dir = os.path.dirname(self.db.path)
        base = os.path.splitext(os.path.basename(self.db.path))[0] or "company"
        root = os.path.join(data_dir, MESSAGE_ATTACHMENTS_DIRNAME, "notes_reminders", base)
        os.makedirs(root, exist_ok=True)
        return root

    def _safe_filename(self, name: str) -> str:
        base = os.path.basename(name or "")
        base = re.sub(r"[^\w.\-]", "_", base)
        base = re.sub(r"_+", "_", base).strip("_")
        return base or "attachment"

    def _ensure_path_inside(self, root: str, path: str) -> str:
        root_abs = os.path.abspath(root)
        path_abs = os.path.abspath(path)
        if os.path.commonpath([root_abs, path_abs]) != root_abs:
            raise ValueError("Dosya yolu geçersiz.")
        return path_abs

    def _audit(self, company_id: int, user_id: int, action: str, entity: str, entity_id: int, detail: str = "") -> None:
        try:
            self.db.notes_reminders.add_audit_log(company_id, user_id, action, entity, entity_id, detail)
        except Exception:
            logger.exception("Audit log yazılamadı")

    def list_company_users(self) -> List[Tuple[int, str]]:
        out: List[Tuple[int, str]] = []
        try:
            for u in self.db.users_list():
                try:
                    out.append((int(u["id"]), str(u["username"])))
                except Exception:
                    continue
        except Exception:
            pass
        return out

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
        pinned: bool,
        scope: str,
        tags: Sequence[str],
    ) -> int:
        cid = self._company_id(company_id)
        note_id = self.db.notes_reminders.create_note(
            cid,
            owner_user_id,
            title,
            body,
            category,
            priority,
            int(pinned),
            scope,
            "active",
        )
        self._replace_note_tags(note_id, tags)
        self._audit(cid, owner_user_id, "create", "note", note_id, title)
        return note_id

    def update_note(
        self,
        note_id: int,
        company_id: int,
        owner_user_id: int,
        title: str,
        body: str,
        category: str,
        priority: str,
        pinned: bool,
        scope: str,
        status: str,
        tags: Sequence[str],
    ) -> None:
        cid = self._company_id(company_id)
        self.db.notes_reminders.update_note(
            note_id,
            title,
            body,
            category,
            priority,
            int(pinned),
            scope,
            status,
        )
        self._replace_note_tags(note_id, tags)
        self._audit(cid, owner_user_id, "update", "note", note_id, title)

    def archive_note(self, note_id: int, company_id: int, owner_user_id: int, archived: bool) -> None:
        cid = self._company_id(company_id)
        status = "archived" if archived else "active"
        self.db.notes_reminders.set_note_status(note_id, status)
        self._audit(cid, owner_user_id, "archive" if archived else "restore", "note", note_id, status)

    def set_note_pinned(self, note_id: int, company_id: int, owner_user_id: int, pinned: bool) -> None:
        cid = self._company_id(company_id)
        self.db.notes_reminders.set_note_pinned(note_id, int(pinned))
        self._audit(cid, owner_user_id, "pin" if pinned else "unpin", "note", note_id, "")

    def list_notes(
        self,
        company_id: int,
        owner_user_id: int,
        q: str = "",
        category: str = "",
        tag: str = "",
        pinned: Optional[bool] = None,
        scope: str = "",
        include_archived: bool = False,
    ):
        return self.db.notes_reminders.list_notes(
            self._company_id(company_id),
            owner_user_id,
            q=q,
            category=category,
            tag=tag,
            pinned=(int(pinned) if pinned is not None else None),
            scope=scope,
            include_archived=include_archived,
        )

    def add_note_attachment(self, note_id: int, company_id: int, owner_user_id: int, source_path: str) -> int:
        if not source_path or not os.path.exists(source_path):
            raise ValueError("Dosya bulunamadı.")
        size = int(os.path.getsize(source_path))
        if size > MESSAGE_ATTACHMENT_MAX_BYTES:
            max_mb = MESSAGE_ATTACHMENT_MAX_BYTES / (1024 * 1024)
            raise ValueError(f"Ek dosya boyutu limiti aşıldı ({max_mb:.0f}MB).")
        original = self._safe_filename(os.path.basename(source_path))
        root = self._attachments_root()
        ext = os.path.splitext(original)[1]
        stored_name = f"{uuid.uuid4().hex}{ext}"
        dest = self._ensure_path_inside(root, os.path.join(root, stored_name))
        shutil.copy2(source_path, dest)
        cid = self._company_id(company_id)
        att_id = self.db.notes_reminders.add_note_attachment(note_id, original, stored_name, size)
        self._audit(cid, owner_user_id, "attach", "note", note_id, original)
        return att_id

    def get_note_attachment_path(self, stored_name: str) -> str:
        root = self._attachments_root()
        safe = self._safe_filename(stored_name)
        return self._ensure_path_inside(root, os.path.join(root, safe))

    def list_note_attachments(self, note_id: int):
        return self.db.notes_reminders.list_note_attachments(note_id)

    def _replace_note_tags(self, note_id: int, tags: Sequence[str]) -> None:
        clean = [t.strip() for t in tags if t and t.strip()]
        self.db.notes_reminders.clear_note_tags(note_id)
        if clean:
            self.db.notes_reminders.add_note_tags(note_id, clean)

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
        status: str = "scheduled",
        assignee_user_id: Optional[int] = None,
        recurrence: Optional[RecurrenceRule] = None,
    ) -> int:
        cid = self._company_id(company_id)
        rid = self.db.notes_reminders.create_reminder(
            cid,
            owner_user_id,
            title,
            body,
            due_at,
            priority,
            status,
            assignee_user_id=assignee_user_id,
            series_id=None,
        )
        if recurrence:
            self.db.notes_reminders.upsert_recurrence(
                rid,
                recurrence.frequency,
                recurrence.interval,
                recurrence.until,
                ",".join(str(x) for x in recurrence.byweekday),
                str(recurrence.bymonthday or ""),
                1,
            )
        self._audit(cid, owner_user_id, "create", "reminder", rid, title)
        return rid

    def update_reminder(
        self,
        reminder_id: int,
        company_id: int,
        owner_user_id: int,
        title: str,
        body: str,
        due_at: str,
        priority: str,
        status: str,
        assignee_user_id: Optional[int],
        recurrence: Optional[RecurrenceRule],
    ) -> None:
        cid = self._company_id(company_id)
        self.db.notes_reminders.update_reminder(
            reminder_id,
            title,
            body,
            due_at,
            priority,
            status,
            assignee_user_id,
        )
        if recurrence:
            self.db.notes_reminders.upsert_recurrence(
                reminder_id,
                recurrence.frequency,
                recurrence.interval,
                recurrence.until,
                ",".join(str(x) for x in recurrence.byweekday),
                str(recurrence.bymonthday or ""),
                1,
            )
        self._audit(cid, owner_user_id, "update", "reminder", reminder_id, title)

    def snooze_reminder(self, reminder_id: int, minutes: int, company_id: int, owner_user_id: int) -> None:
        row = self.db.notes_reminders.get_reminder(reminder_id)
        if not row:
            raise ValueError("Hatırlatma bulunamadı.")
        due = self._parse_dt(str(row["due_at"])) + timedelta(minutes=int(minutes))
        self.db.notes_reminders.update_reminder_due(reminder_id, due.strftime("%Y-%m-%d %H:%M:%S"))
        self.db.notes_reminders.set_reminder_status(reminder_id, "scheduled")
        self._audit(self._company_id(company_id), owner_user_id, "snooze", "reminder", reminder_id, f"{minutes} dk")

    def mark_reminder_done(self, reminder_id: int, company_id: int, owner_user_id: int, close_series: bool = False) -> None:
        row = self.db.notes_reminders.get_reminder(reminder_id)
        if not row:
            raise ValueError("Hatırlatma bulunamadı.")
        self.db.notes_reminders.set_reminder_status(reminder_id, "done")
        series_id = int(row["series_id"] or row["id"])
        if close_series:
            self.db.notes_reminders.set_recurrence_active(series_id, 0)
        else:
            self._create_next_occurrence(row)
        self._audit(self._company_id(company_id), owner_user_id, "done", "reminder", reminder_id, "")

    def cancel_reminder(self, reminder_id: int, company_id: int, owner_user_id: int) -> None:
        self.db.notes_reminders.set_reminder_status(reminder_id, "canceled")
        self._audit(self._company_id(company_id), owner_user_id, "cancel", "reminder", reminder_id, "")

    def archive_reminder(self, reminder_id: int, company_id: int, owner_user_id: int, archived: bool) -> None:
        status = "archived" if archived else "scheduled"
        self.db.notes_reminders.set_reminder_status(reminder_id, status)
        self._audit(self._company_id(company_id), owner_user_id, "archive" if archived else "restore", "reminder", reminder_id, status)

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
    ):
        return self.db.notes_reminders.list_reminders(
            self._company_id(company_id),
            owner_user_id,
            q=q,
            status=status,
            due_from=due_from,
            due_to=due_to,
            include_archived=include_archived,
            only_assigned=only_assigned,
        )

    def check_due_reminders(self, company_id: int, owner_user_id: int) -> Tuple[List[Dict[str, str]], int]:
        cid = self._company_id(company_id)
        now = now_iso()
        due = self.db.notes_reminders.list_due_reminders(cid, owner_user_id, "scheduled", now)
        notified = []
        for r in due:
            self.db.notes_reminders.set_reminder_status(int(r["id"]), "overdue")
            notified.append({"id": str(r["id"]), "title": str(r["title"]), "due_at": str(r["due_at"])})
        overdue = self.db.notes_reminders.list_overdue(cid, owner_user_id)
        return notified, len(overdue)

    def list_overdue(self, company_id: int, owner_user_id: int):
        return self.db.notes_reminders.list_overdue(self._company_id(company_id), owner_user_id)

    def add_reminder_link(
        self,
        reminder_id: int,
        company_id: int,
        owner_user_id: int,
        linked_type: str,
        linked_id: str,
    ) -> int:
        rid = self.db.notes_reminders.add_reminder_link(reminder_id, linked_type, linked_id)
        self._audit(self._company_id(company_id), owner_user_id, "link", "reminder", reminder_id, f"{linked_type}:{linked_id}")
        return rid

    def list_reminder_links(self, reminder_id: int):
        return self.db.notes_reminders.list_reminder_links(reminder_id)

    def get_recurrence_data(self, reminder_id: int) -> Optional[Dict[str, str]]:
        row = self.db.notes_reminders.get_recurrence(reminder_id)
        if not row or int(row["active"]) != 1:
            return None
        return {
            "frequency": str(row["frequency"]),
            "interval": str(row["interval"]),
            "until": str(row["until"] or ""),
            "byweekday": str(row["byweekday"] or ""),
            "bymonthday": str(row["bymonthday"] or ""),
        }

    # -----------------
    # Reports
    # -----------------
    def report_overdue(self, company_id: int, owner_user_id: int):
        return self.list_overdue(company_id, owner_user_id)

    def report_user_completion(self, company_id: int):
        completed = self.db.notes_reminders.report_completed_by_user(self._company_id(company_id))
        missed = self.db.notes_reminders.report_missed_by_user(self._company_id(company_id))
        return completed, missed

    def report_notes_distribution(self, company_id: int):
        categories = self.db.notes_reminders.report_notes_by_category(self._company_id(company_id))
        tags = self.db.notes_reminders.report_notes_by_tag(self._company_id(company_id))
        return categories, tags

    # -----------------
    # Recurrence helpers
    # -----------------
    def _parse_dt(self, iso: str) -> datetime:
        return datetime.strptime(iso, "%Y-%m-%d %H:%M:%S")

    def _get_recurrence(self, series_id: int) -> Optional[RecurrenceRule]:
        row = self.db.notes_reminders.get_recurrence(series_id)
        if not row or int(row["active"]) != 1:
            return None
        weekdays: List[int] = []
        if str(row["byweekday"] or "").strip():
            try:
                weekdays = [int(x) for x in str(row["byweekday"]).split(",") if str(x).strip()]
            except Exception:
                weekdays = []
        return RecurrenceRule(
            frequency=str(row["frequency"]),
            interval=int(row["interval"] or 1),
            until=str(row["until"] or ""),
            byweekday=weekdays,
            bymonthday=str(row["bymonthday"] or ""),
        )

    def _create_next_occurrence(self, reminder_row) -> None:
        series_id = int(reminder_row["series_id"] or reminder_row["id"])
        rule = self._get_recurrence(series_id)
        if not rule:
            return
        due = self._parse_dt(str(reminder_row["due_at"]))
        next_due = self._next_due(due, rule)
        if not next_due:
            return
        self.db.notes_reminders.create_reminder(
            int(reminder_row["company_id"]),
            int(reminder_row["owner_user_id"]),
            str(reminder_row["title"]),
            str(reminder_row["body"]),
            next_due.strftime("%Y-%m-%d %H:%M:%S"),
            str(reminder_row["priority"]),
            "scheduled",
            assignee_user_id=int(reminder_row["assignee_user_id"]) if reminder_row["assignee_user_id"] is not None else None,
            series_id=series_id,
        )

    def _next_due(self, base: datetime, rule: RecurrenceRule) -> Optional[datetime]:
        freq = rule.frequency.lower()
        interval = max(int(rule.interval or 1), 1)
        if freq == "daily":
            candidate = base + timedelta(days=interval)
        elif freq == "weekly":
            weekdays = list(rule.byweekday) or [base.weekday()]
            candidate = self._next_weekday(base, weekdays, interval)
        elif freq == "monthly":
            candidate = self._add_months(base, interval, rule.bymonthday)
        elif freq == "yearly":
            candidate = self._add_years(base, interval)
        else:
            return None
        if rule.until:
            try:
                until_dt = self._parse_dt(rule.until)
                if candidate > until_dt:
                    return None
            except Exception:
                pass
        return candidate

    def _next_weekday(self, base: datetime, weekdays: Sequence[int], interval: int) -> datetime:
        weekdays = sorted({int(w) for w in weekdays if 0 <= int(w) <= 6})
        if not weekdays:
            return base + timedelta(weeks=interval)
        for offset in range(1, 7 * interval + 1):
            candidate = base + timedelta(days=offset)
            if candidate.weekday() in weekdays:
                return candidate
        return base + timedelta(weeks=interval)

    def _add_months(self, base: datetime, months: int, bymonthday: str) -> datetime:
        month = base.month - 1 + months
        year = base.year + month // 12
        month = month % 12 + 1
        day = base.day
        if bymonthday:
            try:
                day = int(bymonthday)
            except Exception:
                day = base.day
        last_day = self._last_day_of_month(year, month)
        day = min(day, last_day)
        return base.replace(year=year, month=month, day=day)

    def _add_years(self, base: datetime, years: int) -> datetime:
        year = base.year + years
        day = min(base.day, self._last_day_of_month(year, base.month))
        return base.replace(year=year, day=day)

    def _last_day_of_month(self, year: int, month: int) -> int:
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        return (next_month - timedelta(days=1)).day
