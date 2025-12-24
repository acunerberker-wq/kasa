# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timedelta

from kasapro.db.main_db import DB
from kasapro.db.users_db import UsersDB
from kasapro.modules.notes_reminders.service import NotesRemindersService, RecurrenceRule


class NotesRemindersTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.base_dir = self.tmpdir.name
        self.db_path = os.path.join(self.base_dir, "company.db")
        self.db = DB(self.db_path)
        self.usersdb = UsersDB(self.base_dir)
        self.service = NotesRemindersService(self.db, self.usersdb)
        self.company_id = 1
        self.user_id = 1
        self.db.user_add("user2", "pass", "user")
        self.user2_id = 2

    def tearDown(self) -> None:
        self.db.close()
        self.usersdb.close()
        self.tmpdir.cleanup()

    def test_note_create_edit_archive_pin(self) -> None:
        note_id = self.service.create_note(
            self.company_id,
            self.user_id,
            "Test Not",
            "İçerik",
            "Genel",
            "normal",
            False,
            "personal",
            ["tag1"],
        )
        self.service.set_note_pinned(note_id, self.company_id, self.user_id, True)
        self.service.update_note(
            note_id,
            self.company_id,
            self.user_id,
            "Test Not Güncel",
            "Yeni içerik",
            "Genel",
            "high",
            True,
            "personal",
            "active",
            ["tag1", "tag2"],
        )
        self.service.archive_note(note_id, self.company_id, self.user_id, True)
        notes = self.service.list_notes(self.company_id, self.user_id, include_archived=True)
        self.assertTrue(any(int(n["id"]) == note_id and n["status"] == "archived" for n in notes))

    def test_note_search_and_tag_filter(self) -> None:
        self.service.create_note(
            self.company_id,
            self.user_id,
            "Toplantı Notu",
            "İçerik",
            "Toplantı",
            "normal",
            False,
            "team",
            ["ops", "todo"],
        )
        notes = self.service.list_notes(self.company_id, self.user_id, q="Toplantı", tag="ops")
        self.assertTrue(any("Toplantı" in str(n["title"]) for n in notes))

    def test_reminder_due_triggers_notification(self) -> None:
        due_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rid = self.service.create_reminder(
            self.company_id,
            self.user_id,
            "Hatırlatma",
            "Body",
            due_at,
            "normal",
        )
        due, count = self.service.check_due_reminders(self.company_id, self.user_id)
        self.assertTrue(any(int(d["id"]) == rid for d in due))
        self.assertGreaterEqual(count, 1)

    def test_snooze_updates_due(self) -> None:
        due_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rid = self.service.create_reminder(
            self.company_id,
            self.user_id,
            "Snooze",
            "Body",
            due_at,
            "normal",
        )
        self.service.snooze_reminder(rid, 5, self.company_id, self.user_id)
        row = self.db.notes_reminders.get_reminder(rid)
        self.assertIsNotNone(row)
        new_due = datetime.strptime(str(row["due_at"]), "%Y-%m-%d %H:%M:%S")
        self.assertGreaterEqual(new_due, datetime.now())

    def test_overdue_dashboard_lists(self) -> None:
        due_at = (datetime.now() - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")
        self.service.create_reminder(
            self.company_id,
            self.user_id,
            "Overdue",
            "Body",
            due_at,
            "normal",
        )
        self.service.check_due_reminders(self.company_id, self.user_id)
        overdue = self.service.list_overdue(self.company_id, self.user_id)
        self.assertTrue(overdue)

    def test_recurring_daily_and_weekly(self) -> None:
        base = datetime(2024, 1, 1, 9, 0, 0)
        rid = self.service.create_reminder(
            self.company_id,
            self.user_id,
            "Daily",
            "Body",
            base.strftime("%Y-%m-%d %H:%M:%S"),
            "normal",
            recurrence=RecurrenceRule("daily", interval=1),
        )
        self.service.mark_reminder_done(rid, self.company_id, self.user_id, close_series=False)
        rows = self.db.notes_reminders.list_reminders(self.company_id, self.user_id, q="Daily")
        self.assertGreaterEqual(len(rows), 2)

        weekly_base = datetime(2024, 1, 1, 10, 0, 0)
        rid2 = self.service.create_reminder(
            self.company_id,
            self.user_id,
            "Weekly",
            "Body",
            weekly_base.strftime("%Y-%m-%d %H:%M:%S"),
            "normal",
            recurrence=RecurrenceRule("weekly", interval=1, byweekday=[0]),
        )
        self.service.mark_reminder_done(rid2, self.company_id, self.user_id, close_series=False)
        rows2 = [r for r in self.db.notes_reminders.list_reminders(self.company_id, self.user_id, q="Weekly")]
        self.assertGreaterEqual(len(rows2), 2)

    def test_reminder_done_close_series(self) -> None:
        base = datetime(2024, 1, 1, 9, 0, 0)
        rid = self.service.create_reminder(
            self.company_id,
            self.user_id,
            "Series",
            "Body",
            base.strftime("%Y-%m-%d %H:%M:%S"),
            "normal",
            recurrence=RecurrenceRule("daily", interval=1),
        )
        self.service.mark_reminder_done(rid, self.company_id, self.user_id, close_series=True)
        rows = [r for r in self.db.notes_reminders.list_reminders(self.company_id, self.user_id, q="Series")]
        self.assertEqual(len(rows), 1)

    def test_attachment_add_and_read(self) -> None:
        note_id = self.service.create_note(
            self.company_id,
            self.user_id,
            "Ekli",
            "İçerik",
            "Genel",
            "normal",
            False,
            "personal",
            [],
        )
        temp_file = os.path.join(self.base_dir, "sample.txt")
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write("data")
        self.service.add_note_attachment(note_id, self.company_id, self.user_id, temp_file)
        attachments = self.service.list_note_attachments(note_id)
        self.assertTrue(attachments)
        path = self.service.get_note_attachment_path(str(attachments[0]["stored_name"]))
        self.assertTrue(os.path.exists(path))

    def test_scope_personal_visible_only_to_owner(self) -> None:
        self.service.create_note(
            self.company_id,
            self.user_id,
            "Özel",
            "Body",
            "Genel",
            "normal",
            False,
            "personal",
            [],
        )
        notes_user2 = self.service.list_notes(self.company_id, self.user2_id)
        self.assertFalse(any(str(n["title"]) == "Özel" for n in notes_user2))

    def test_audit_log_written(self) -> None:
        note_id = self.service.create_note(
            self.company_id,
            self.user_id,
            "Audit",
            "Body",
            "Genel",
            "normal",
            False,
            "personal",
            [],
        )
        self.service.create_reminder(
            self.company_id,
            self.user_id,
            "Audit Reminder",
            "Body",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "normal",
        )
        rows = list(self.db.conn.execute("SELECT * FROM audit_log WHERE entity_id=?", (note_id,)))
        self.assertTrue(rows)
