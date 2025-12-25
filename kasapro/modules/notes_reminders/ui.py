# -*- coding: utf-8 -*-
"""Notlar & Hatırlatmalar UI."""

from __future__ import annotations

import os
import queue
import threading
from datetime import datetime
from typing import Any, Dict, Optional, Sequence

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from ...config import APP_TITLE
from ...ui.widgets import LabeledEntry, LabeledCombo
from ...utils import today_iso
from .service import NotesRemindersService, RecurrenceRule


class NotesRemindersFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.service: NotesRemindersService = app.services.notes_reminders
        self._queue: "queue.Queue[tuple]" = queue.Queue()
        self._notes_cache: Dict[int, Dict[str, Any]] = {}
        self._reminders_cache: Dict[int, Dict[str, Any]] = {}
        self._build()
        self.after(200, self._poll_queue)
        self.refresh()

    def _build(self):
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tab_notes = ttk.Frame(self.nb)
        self.tab_reminders = ttk.Frame(self.nb)
        self.tab_reports = ttk.Frame(self.nb)

        self.nb.add(self.tab_notes, text="📝 Notlar")
        self.nb.add(self.tab_reminders, text="⏰ Hatırlatmalar")
        self.nb.add(self.tab_reports, text="📊 Raporlar")

        self._build_notes_tab(self.tab_notes)
        self._build_reminders_tab(self.tab_reminders)
        self._build_reports_tab(self.tab_reports)

    # -----------------
    # Notes tab
    # -----------------
    def _build_notes_tab(self, parent: ttk.Frame) -> None:
        filters = ttk.LabelFrame(parent, text="Not Filtreleri")
        filters.pack(fill=tk.X, padx=6, pady=6)

        row1 = ttk.Frame(filters)
        row1.pack(fill=tk.X, pady=4)
        self.note_q = LabeledEntry(row1, "Ara:", 20)
        self.note_q.pack(side=tk.LEFT, padx=6)
        self.note_cat = LabeledEntry(row1, "Kategori:", 14)
        self.note_cat.pack(side=tk.LEFT, padx=6)
        self.note_tag = LabeledEntry(row1, "Tag:", 14)
        self.note_tag.pack(side=tk.LEFT, padx=6)
        self.note_scope = LabeledCombo(row1, "Scope:", ["(Tümü)", "personal", "team", "company"], 12)
        self.note_scope.pack(side=tk.LEFT, padx=6)
        self.note_scope.set("(Tümü)")

        row2 = ttk.Frame(filters)
        row2.pack(fill=tk.X, pady=4)
        self.note_pinned = LabeledCombo(row2, "Pinned:", ["(Tümü)", "Evet", "Hayır"], 12)
        self.note_pinned.pack(side=tk.LEFT, padx=6)
        self.note_pinned.set("(Tümü)")
        self.note_archived_var = tk.IntVar(value=0)
        ttk.Checkbutton(row2, text="Arşiv dahil", variable=self.note_archived_var).pack(side=tk.LEFT, padx=6)
        ttk.Button(row2, text="Yenile", command=self.refresh_notes).pack(side=tk.LEFT, padx=6)

        table = ttk.LabelFrame(parent, text="Notlar")
        table.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        cols = ("id", "title", "category", "priority", "pinned", "scope", "tags", "updated_at", "status")
        self.notes_tree = ttk.Treeview(table, columns=cols, show="headings", height=12)
        for c in cols:
            self.notes_tree.heading(c, text=c.upper())
        self.notes_tree.column("id", width=60, anchor="center")
        self.notes_tree.column("title", width=220)
        self.notes_tree.column("category", width=120)
        self.notes_tree.column("priority", width=90, anchor="center")
        self.notes_tree.column("pinned", width=70, anchor="center")
        self.notes_tree.column("scope", width=90, anchor="center")
        self.notes_tree.column("tags", width=160)
        self.notes_tree.column("updated_at", width=140)
        self.notes_tree.column("status", width=90, anchor="center")
        self.notes_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.notes_tree.bind("<Double-1>", lambda _e: self._edit_note())

        actions = ttk.Frame(table)
        actions.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(actions, text="➕ Yeni", command=self._new_note).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="✏️ Düzenle", command=self._edit_note).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="📌 Pin", command=lambda: self._toggle_note_pin(True)).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="📍 Unpin", command=lambda: self._toggle_note_pin(False)).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="🗂️ Arşiv", command=lambda: self._toggle_note_archive(True)).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="↩️ Geri Al", command=lambda: self._toggle_note_archive(False)).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="📎 Ek", command=self._attach_note).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="📂 Ekler", command=self._view_note_attachments).pack(side=tk.LEFT, padx=4)

    def _selected_note_id(self) -> Optional[int]:
        sel = self.notes_tree.selection()
        if not sel:
            return None
        try:
            return int(self.notes_tree.item(sel[0], "values")[0])
        except Exception:
            return None

    def _new_note(self) -> None:
        editor = NoteEditor(self, title="Yeni Not")
        data = editor.result
        if not data:
            return
        try:
            self.service.create_note(
                self._company_id(),
                self._user_id(),
                data["title"],
                data["body"],
                data["category"],
                data["priority"],
                data["pinned"],
                data["scope"],
                data["tags"],
            )
            self.refresh_notes()
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Not eklenemedi: {exc}")

    def _edit_note(self) -> None:
        note_id = self._selected_note_id()
        if not note_id:
            return
        note = self._notes_cache.get(note_id)
        if not note:
            return
        editor = NoteEditor(self, title="Not Düzenle", data=note)
        data = editor.result
        if not data:
            return
        try:
            self.service.update_note(
                note_id,
                self._company_id(),
                self._user_id(),
                data["title"],
                data["body"],
                data["category"],
                data["priority"],
                data["pinned"],
                data["scope"],
                data["status"],
                data["tags"],
            )
            self.refresh_notes()
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Not güncellenemedi: {exc}")

    def _toggle_note_pin(self, pinned: bool) -> None:
        note_id = self._selected_note_id()
        if not note_id:
            return
        try:
            self.service.set_note_pinned(note_id, self._company_id(), self._user_id(), pinned)
            self.refresh_notes()
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Pin güncellenemedi: {exc}")

    def _toggle_note_archive(self, archived: bool) -> None:
        note_id = self._selected_note_id()
        if not note_id:
            return
        try:
            self.service.archive_note(note_id, self._company_id(), self._user_id(), archived)
            self.refresh_notes()
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Arşiv işlemi başarısız: {exc}")

    def _attach_note(self) -> None:
        note_id = self._selected_note_id()
        if not note_id:
            return
        path = filedialog.askopenfilename(title="Ek Dosya Seç")
        if not path:
            return
        try:
            self.service.add_note_attachment(note_id, self._company_id(), self._user_id(), path)
            messagebox.showinfo(APP_TITLE, "Ek dosya kaydedildi.")
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Ek dosya eklenemedi: {exc}")

    def _view_note_attachments(self) -> None:
        note_id = self._selected_note_id()
        if not note_id:
            return
        win = AttachmentsWindow(self, self.service, note_id)
        win.wait_window()

    # -----------------
    # Reminders tab
    # -----------------
    def _build_reminders_tab(self, parent: ttk.Frame) -> None:
        filters = ttk.LabelFrame(parent, text="Hatırlatma Filtreleri")
        filters.pack(fill=tk.X, padx=6, pady=6)

        row1 = ttk.Frame(filters)
        row1.pack(fill=tk.X, pady=4)
        self.reminder_q = LabeledEntry(row1, "Ara:", 20)
        self.reminder_q.pack(side=tk.LEFT, padx=6)
        self.reminder_status = LabeledCombo(
            row1,
            "Durum:",
            ["(Tümü)", "scheduled", "overdue", "done", "canceled", "archived", "deleted"],
            12,
        )
        self.reminder_status.pack(side=tk.LEFT, padx=6)
        self.reminder_status.set("(Tümü)")
        self.reminder_due_from = LabeledEntry(row1, "Başlangıç:", 12)
        self.reminder_due_from.pack(side=tk.LEFT, padx=6)
        self.reminder_due_to = LabeledEntry(row1, "Bitiş:", 12)
        self.reminder_due_to.pack(side=tk.LEFT, padx=6)

        row2 = ttk.Frame(filters)
        row2.pack(fill=tk.X, pady=4)
        self.reminder_assigned_var = tk.IntVar(value=0)
        ttk.Checkbutton(row2, text="Sadece bana atanan", variable=self.reminder_assigned_var).pack(side=tk.LEFT, padx=6)
        self.reminder_archived_var = tk.IntVar(value=0)
        ttk.Checkbutton(row2, text="Arşiv dahil", variable=self.reminder_archived_var).pack(side=tk.LEFT, padx=6)
        ttk.Button(row2, text="Yenile", command=self.refresh_reminders).pack(side=tk.LEFT, padx=6)

        table = ttk.LabelFrame(parent, text="Hatırlatmalar")
        table.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        cols = ("id", "title", "due_at", "status", "priority", "assignee", "series_id")
        self.reminders_tree = ttk.Treeview(table, columns=cols, show="headings", height=12)
        for c in cols:
            self.reminders_tree.heading(c, text=c.upper())
        self.reminders_tree.column("id", width=60, anchor="center")
        self.reminders_tree.column("title", width=240)
        self.reminders_tree.column("due_at", width=150)
        self.reminders_tree.column("status", width=100, anchor="center")
        self.reminders_tree.column("priority", width=90, anchor="center")
        self.reminders_tree.column("assignee", width=120)
        self.reminders_tree.column("series_id", width=80, anchor="center")
        self.reminders_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.reminders_tree.bind("<Double-1>", lambda _e: self._edit_reminder())

        actions = ttk.Frame(table)
        actions.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(actions, text="➕ Yeni", command=self._new_reminder).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="✏️ Düzenle", command=self._edit_reminder).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="✅ Tamamlandı", command=self._done_reminder).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="⏸️ Snooze 5dk", command=lambda: self._snooze_reminder(5)).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="⏸️ Snooze 15dk", command=lambda: self._snooze_reminder(15)).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="⏸️ Snooze 1s", command=lambda: self._snooze_reminder(60)).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="⏸️ Snooze 1g", command=lambda: self._snooze_reminder(60 * 24)).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="🚫 İptal", command=self._cancel_reminder).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="🗂️ Arşiv", command=lambda: self._toggle_reminder_archive(True)).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="↩️ Geri Al", command=lambda: self._toggle_reminder_archive(False)).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="🔗 Bağla", command=self._link_reminder).pack(side=tk.LEFT, padx=4)

    def _selected_reminder_id(self) -> Optional[int]:
        sel = self.reminders_tree.selection()
        if not sel:
            return None
        try:
            return int(self.reminders_tree.item(sel[0], "values")[0])
        except Exception:
            return None

    def _new_reminder(self) -> None:
        editor = ReminderEditor(self, title="Yeni Hatırlatma", users=self.service.list_company_users())
        data = editor.result
        if not data:
            return
        try:
            recurrence = data.get("recurrence")
            self.service.create_reminder(
                self._company_id(),
                self._user_id(),
                data["title"],
                data["body"],
                data["due_at"],
                data["priority"],
                assignee_user_id=data.get("assignee"),
                recurrence=recurrence,
            )
            self.refresh_reminders()
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Hatırlatma eklenemedi: {exc}")

    def _edit_reminder(self) -> None:
        rid = self._selected_reminder_id()
        if not rid:
            return
        reminder = self._reminders_cache.get(rid)
        if not reminder:
            return
        series_id = int(reminder.get("series_id") or rid)
        reminder["recurrence"] = self.service.get_recurrence_data(series_id) or {}
        editor = ReminderEditor(
            self,
            title="Hatırlatma Düzenle",
            data=reminder,
            users=self.service.list_company_users(),
        )
        data = editor.result
        if not data:
            return
        try:
            self.service.update_reminder(
                rid,
                self._company_id(),
                self._user_id(),
                data["title"],
                data["body"],
                data["due_at"],
                data["priority"],
                data["status"],
                data.get("assignee"),
                data.get("recurrence"),
            )
            self.refresh_reminders()
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Hatırlatma güncellenemedi: {exc}")

    def _done_reminder(self) -> None:
        rid = self._selected_reminder_id()
        if not rid:
            return
        close_series = messagebox.askyesno(APP_TITLE, "Seriyi de kapatmak ister misiniz?")
        try:
            self.service.mark_reminder_done(rid, self._company_id(), self._user_id(), close_series=close_series)
            self.refresh_reminders()
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Hatırlatma tamamlanamadı: {exc}")

    def _snooze_reminder(self, minutes: int) -> None:
        rid = self._selected_reminder_id()
        if not rid:
            return
        try:
            self.service.snooze_reminder(rid, minutes, self._company_id(), self._user_id())
            self.refresh_reminders()
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Snooze başarısız: {exc}")

    def _cancel_reminder(self) -> None:
        rid = self._selected_reminder_id()
        if not rid:
            return
        try:
            self.service.cancel_reminder(rid, self._company_id(), self._user_id())
            self.refresh_reminders()
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"İptal edilemedi: {exc}")

    def _toggle_reminder_archive(self, archived: bool) -> None:
        rid = self._selected_reminder_id()
        if not rid:
            return
        try:
            self.service.archive_reminder(rid, self._company_id(), self._user_id(), archived)
            self.refresh_reminders()
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Arşiv işlemi başarısız: {exc}")

    def _link_reminder(self) -> None:
        rid = self._selected_reminder_id()
        if not rid:
            return
        win = LinkWindow(self)
        data = win.result
        if not data:
            return
        try:
            self.service.add_reminder_link(rid, self._company_id(), self._user_id(), data["type"], data["id"])
            messagebox.showinfo(APP_TITLE, "Bağlantı kaydedildi.")
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Bağlantı eklenemedi: {exc}")

    # -----------------
    # Reports
    # -----------------
    def _build_reports_tab(self, parent: ttk.Frame) -> None:
        top = ttk.Frame(parent)
        top.pack(fill=tk.X, padx=6, pady=6)
        ttk.Button(top, text="Yenile", command=self.refresh_reports).pack(side=tk.LEFT, padx=6)

        self.report_overdue = ttk.LabelFrame(parent, text="Geciken Hatırlatmalar")
        self.report_overdue.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.overdue_tree = ttk.Treeview(self.report_overdue, columns=("id", "title", "due_at", "status"), show="headings", height=6)
        for c in ("id", "title", "due_at", "status"):
            self.overdue_tree.heading(c, text=c.upper())
        self.overdue_tree.column("id", width=60, anchor="center")
        self.overdue_tree.column("title", width=240)
        self.overdue_tree.column("due_at", width=150)
        self.overdue_tree.column("status", width=100, anchor="center")
        self.overdue_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        stats = ttk.Frame(parent)
        stats.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self.report_users = ttk.LabelFrame(stats, text="Kullanıcı Bazlı Tamamlanan / Kaçırılan")
        self.report_users.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        self.users_tree = ttk.Treeview(self.report_users, columns=("user_id", "completed", "missed"), show="headings", height=6)
        for c in ("user_id", "completed", "missed"):
            self.users_tree.heading(c, text=c.upper())
        self.users_tree.column("user_id", width=80, anchor="center")
        self.users_tree.column("completed", width=120, anchor="center")
        self.users_tree.column("missed", width=120, anchor="center")
        self.users_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self.report_tags = ttk.LabelFrame(stats, text="Tag/Kategori Dağılımı")
        self.report_tags.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tags_tree = ttk.Treeview(self.report_tags, columns=("type", "value", "count"), show="headings", height=6)
        for c in ("type", "value", "count"):
            self.tags_tree.heading(c, text=c.upper())
        self.tags_tree.column("type", width=80, anchor="center")
        self.tags_tree.column("value", width=160)
        self.tags_tree.column("count", width=80, anchor="center")
        self.tags_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

    # -----------------
    # Refresh
    # -----------------
    def refresh(self) -> None:
        self.refresh_notes()
        self.refresh_reminders()
        self.refresh_reports()

    def refresh_notes(self) -> None:
        threading.Thread(target=self._load_notes, daemon=True).start()

    def refresh_reminders(self) -> None:
        threading.Thread(target=self._load_reminders, daemon=True).start()

    def refresh_reports(self) -> None:
        threading.Thread(target=self._load_reports, daemon=True).start()

    def _load_notes(self) -> None:
        try:
            q = self.note_q.get().strip()
            category = self.note_cat.get().strip()
            tag = self.note_tag.get().strip()
            scope = self.note_scope.get()
            if scope == "(Tümü)":
                scope = ""
            pinned_val = self.note_pinned.get()
            pinned = None
            if pinned_val == "Evet":
                pinned = True
            elif pinned_val == "Hayır":
                pinned = False
            rows = self.service.list_notes(
                self._company_id(),
                self._user_id(),
                q=q,
                category=category,
                tag=tag,
                pinned=pinned,
                scope=scope,
                include_archived=bool(self.note_archived_var.get()),
            )
            self._queue.put(("notes", rows))
        except Exception as exc:
            self._queue.put(("error", str(exc)))

    def _load_reminders(self) -> None:
        try:
            q = self.reminder_q.get().strip()
            status = self.reminder_status.get()
            if status == "(Tümü)":
                status = ""
            due_from = self.reminder_due_from.get().strip()
            due_to = self.reminder_due_to.get().strip()
            rows = self.service.list_reminders(
                self._company_id(),
                self._user_id(),
                q=q,
                status=status,
                due_from=due_from,
                due_to=due_to,
                include_archived=bool(self.reminder_archived_var.get()),
                only_assigned=bool(self.reminder_assigned_var.get()),
            )
            self._queue.put(("reminders", rows))
        except Exception as exc:
            self._queue.put(("error", str(exc)))

    def _load_reports(self) -> None:
        try:
            overdue = self.service.report_overdue(self._company_id(), self._user_id())
            completed, missed = self.service.report_user_completion(self._company_id())
            categories, tags = self.service.report_notes_distribution(self._company_id())
            self._queue.put(("reports", overdue, completed, missed, categories, tags))
        except Exception as exc:
            self._queue.put(("error", str(exc)))

    def _poll_queue(self) -> None:
        try:
            while True:
                msg = self._queue.get_nowait()
                self._handle_queue(msg)
        except queue.Empty:
            pass
        self.after(150, self._poll_queue)

    def _handle_queue(self, msg: tuple) -> None:
        if not msg:
            return
        if msg[0] == "notes":
            rows = msg[1]
            self._notes_cache.clear()
            self.notes_tree.delete(*self.notes_tree.get_children())
            for r in rows:
                rid = int(r["id"])
                tags = str(r["tags"] or "")
                self._notes_cache[rid] = dict(r)
                self.notes_tree.insert(
                    "",
                    tk.END,
                    values=(
                        rid,
                        r["title"],
                        r["category"],
                        r["priority"],
                        "✅" if int(r["pinned"]) else "",
                        r["scope"],
                        tags,
                        r["updated_at"],
                        r["status"],
                    ),
                )
        elif msg[0] == "reminders":
            rows = msg[1]
            self._reminders_cache.clear()
            self.reminders_tree.delete(*self.reminders_tree.get_children())
            for r in rows:
                rid = int(r["id"])
                self._reminders_cache[rid] = dict(r)
                assignee = str(r["assignee_user_id"] or "")
                self.reminders_tree.insert(
                    "",
                    tk.END,
                    values=(
                        rid,
                        r["title"],
                        r["due_at"],
                        r["status"],
                        r["priority"],
                        assignee,
                        r["series_id"],
                    ),
                )
        elif msg[0] == "reports":
            overdue, completed, missed, categories, tags = msg[1:]
            self.overdue_tree.delete(*self.overdue_tree.get_children())
            for r in overdue:
                self.overdue_tree.insert("", tk.END, values=(r["id"], r["title"], r["due_at"], r["status"]))
            self.users_tree.delete(*self.users_tree.get_children())
            missed_map = {int(r["owner_user_id"]): int(r["missed_count"]) for r in missed}
            for r in completed:
                uid = int(r["owner_user_id"])
                self.users_tree.insert("", tk.END, values=(uid, r["completed_count"], missed_map.get(uid, 0)))
            self.tags_tree.delete(*self.tags_tree.get_children())
            for r in categories:
                self.tags_tree.insert("", tk.END, values=("Kategori", r["category"], r["note_count"]))
            for r in tags:
                self.tags_tree.insert("", tk.END, values=("Tag", r["tag"], r["note_count"]))
        elif msg[0] == "error":
            return

    def _company_id(self) -> int:
        return int(getattr(self.app, "active_company_id", None) or 1)

    def _user_id(self) -> int:
        return int(self.app.get_active_user_id() or 1)


class NoteEditor(tk.Toplevel):
    def __init__(self, parent, title: str, data: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.title(title)
        self.geometry("520x420")
        self.resizable(False, False)
        self.result: Optional[Dict[str, Any]] = None
        self._build(data or {})
        self.grab_set()
        self.wait_window()

    def _build(self, data: Dict[str, Any]) -> None:
        frm = ttk.Frame(self)
        frm.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        self.in_title = LabeledEntry(frm, "Başlık:", 32)
        self.in_title.pack(fill=tk.X, pady=4)
        self.in_title.set(data.get("title", ""))

        self.in_category = LabeledEntry(frm, "Kategori:", 20)
        self.in_category.pack(fill=tk.X, pady=4)
        self.in_category.set(data.get("category", ""))

        self.in_priority = LabeledCombo(frm, "Öncelik:", ["low", "normal", "high"], 12)
        self.in_priority.pack(fill=tk.X, pady=4)
        self.in_priority.set(data.get("priority", "normal"))

        self.in_scope = LabeledCombo(frm, "Scope:", ["personal", "team", "company"], 12)
        self.in_scope.pack(fill=tk.X, pady=4)
        self.in_scope.set(data.get("scope", "personal"))

        self.var_pinned = tk.IntVar(value=1 if int(data.get("pinned", 0) or 0) else 0)
        ttk.Checkbutton(frm, text="Pinned", variable=self.var_pinned).pack(anchor="w", pady=4)

        ttk.Label(frm, text="Tagler (virgülle):").pack(anchor="w")
        self.in_tags = ttk.Entry(frm, width=40)
        self.in_tags.pack(fill=tk.X, pady=4)
        self.in_tags.insert(0, data.get("tags", ""))

        ttk.Label(frm, text="İçerik:").pack(anchor="w")
        self.txt_body = tk.Text(frm, height=8)
        self.txt_body.pack(fill=tk.BOTH, expand=True, pady=4)
        self.txt_body.insert("1.0", data.get("body", ""))

        self.in_status = LabeledCombo(frm, "Durum:", ["active", "archived", "deleted"], 12)
        self.in_status.pack(fill=tk.X, pady=4)
        self.in_status.set(data.get("status", "active"))

        btns = ttk.Frame(frm)
        btns.pack(fill=tk.X, pady=10)
        ttk.Button(btns, text="Kaydet", command=self._save).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="İptal", command=self.destroy).pack(side=tk.RIGHT, padx=6)

    def _save(self) -> None:
        title = self.in_title.get().strip()
        if not title:
            messagebox.showerror(APP_TITLE, "Başlık zorunlu.")
            return
        tags = [t.strip() for t in self.in_tags.get().split(",") if t.strip()]
        self.result = {
            "title": title,
            "category": self.in_category.get().strip(),
            "priority": self.in_priority.get().strip() or "normal",
            "scope": self.in_scope.get().strip() or "personal",
            "pinned": bool(self.var_pinned.get()),
            "tags": tags,
            "body": self.txt_body.get("1.0", tk.END).strip(),
            "status": self.in_status.get().strip() or "active",
        }
        self.destroy()


class ReminderEditor(tk.Toplevel):
    def __init__(
        self,
        parent,
        title: str,
        data: Optional[Dict[str, Any]] = None,
        users: Sequence[tuple[int, str]] = (),
    ):
        super().__init__(parent)
        self.title(title)
        self.geometry("560x520")
        self.resizable(False, False)
        self.result: Optional[Dict[str, Any]] = None
        self.users = list(users)
        self._build(data or {})
        self.grab_set()
        self.wait_window()

    def _build(self, data: Dict[str, Any]) -> None:
        frm = ttk.Frame(self)
        frm.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        self.in_title = LabeledEntry(frm, "Başlık:", 32)
        self.in_title.pack(fill=tk.X, pady=4)
        self.in_title.set(data.get("title", ""))

        ttk.Label(frm, text="İçerik:").pack(anchor="w")
        self.txt_body = tk.Text(frm, height=6)
        self.txt_body.pack(fill=tk.BOTH, expand=True, pady=4)
        self.txt_body.insert("1.0", data.get("body", ""))

        due = str(data.get("due_at", ""))
        due_date, due_time = self._split_due(due)
        row_due = ttk.Frame(frm)
        row_due.pack(fill=tk.X, pady=4)
        self.in_due_date = LabeledEntry(row_due, "Tarih (YYYY-MM-DD):", 14)
        self.in_due_date.pack(side=tk.LEFT, padx=6)
        self.in_due_date.set(due_date or today_iso())
        self.in_due_time = LabeledEntry(row_due, "Saat (HH:MM):", 8)
        self.in_due_time.pack(side=tk.LEFT, padx=6)
        self.in_due_time.set(due_time or "09:00")

        row_meta = ttk.Frame(frm)
        row_meta.pack(fill=tk.X, pady=4)
        self.in_priority = LabeledCombo(frm, "Öncelik:", ["low", "normal", "high"], 12)
        self.in_priority.pack(fill=tk.X, pady=4)
        self.in_priority.set(data.get("priority", "normal"))

        status_val = str(data.get("status", "scheduled"))
        self.in_status = LabeledCombo(
            frm,
            "Durum:",
            ["scheduled", "overdue", "done", "canceled", "archived", "deleted"],
            12,
        )
        self.in_status.pack(fill=tk.X, pady=4)
        self.in_status.set(status_val)

        user_map = {str(uid): name for uid, name in self.users}
        user_values = ["(Yok)"] + [f"{uid}:{name}" for uid, name in self.users]
        self.in_assignee = LabeledCombo(frm, "Atanan:", user_values, 16)
        self.in_assignee.pack(fill=tk.X, pady=4)
        assignee_id = data.get("assignee_user_id")
        if assignee_id:
            uname = user_map.get(str(assignee_id), "")
            self.in_assignee.set(f"{assignee_id}:{uname}")
        else:
            self.in_assignee.set("(Yok)")

        rec_box = ttk.LabelFrame(frm, text="Tekrarlama")
        rec_box.pack(fill=tk.X, pady=6)
        self.rec_frequency = LabeledCombo(rec_box, "Frekans:", ["(Yok)", "daily", "weekly", "monthly", "yearly"], 12)
        self.rec_frequency.pack(side=tk.LEFT, padx=6, pady=4)
        self.rec_interval = LabeledEntry(rec_box, "Aralık:", 6)
        self.rec_interval.pack(side=tk.LEFT, padx=6)
        self.rec_until = LabeledEntry(rec_box, "Until (YYYY-MM-DD HH:MM:SS):", 20)
        self.rec_until.pack(side=tk.LEFT, padx=6)

        rec_row2 = ttk.Frame(rec_box)
        rec_row2.pack(fill=tk.X, pady=4)
        self.rec_byweekday = LabeledEntry(rec_row2, "Byweekday (0-6):", 12)
        self.rec_byweekday.pack(side=tk.LEFT, padx=6)
        self.rec_bymonthday = LabeledEntry(rec_row2, "Bymonthday:", 10)
        self.rec_bymonthday.pack(side=tk.LEFT, padx=6)

        rec = data.get("recurrence") or {}
        if rec:
            self.rec_frequency.set(rec.get("frequency", "(Yok)"))
            self.rec_interval.set(str(rec.get("interval", "1")))
            self.rec_until.set(rec.get("until", ""))
            self.rec_byweekday.set(rec.get("byweekday", ""))
            self.rec_bymonthday.set(rec.get("bymonthday", ""))
        else:
            self.rec_frequency.set("(Yok)")
            self.rec_interval.set("1")

        btns = ttk.Frame(frm)
        btns.pack(fill=tk.X, pady=10)
        ttk.Button(btns, text="Kaydet", command=self._save).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="İptal", command=self.destroy).pack(side=tk.RIGHT, padx=6)

    def _save(self) -> None:
        title = self.in_title.get().strip()
        if not title:
            messagebox.showerror(APP_TITLE, "Başlık zorunlu.")
            return
        due_at = self._combine_due()
        if not due_at:
            messagebox.showerror(APP_TITLE, "Tarih/saat formatı hatalı.")
            return
        assignee = self._parse_assignee(self.in_assignee.get())
        recurrence = self._build_recurrence()
        self.result = {
            "title": title,
            "body": self.txt_body.get("1.0", tk.END).strip(),
            "due_at": due_at,
            "priority": self.in_priority.get().strip() or "normal",
            "status": self.in_status.get().strip() or "scheduled",
            "assignee": assignee,
            "recurrence": recurrence,
        }
        self.destroy()

    def _split_due(self, due: str) -> tuple[str, str]:
        if not due:
            return "", ""
        try:
            dt = datetime.strptime(due, "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")
        except Exception:
            return "", ""

    def _combine_due(self) -> str:
        date_val = self.in_due_date.get().strip()
        time_val = self.in_due_time.get().strip()
        if not date_val or not time_val:
            return ""
        if len(time_val) == 5:
            time_val = f"{time_val}:00"
        try:
            dt = datetime.strptime(f"{date_val} {time_val}", "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return ""

    def _parse_assignee(self, value: str) -> Optional[int]:
        if value.startswith("(Yok)"):
            return None
        if ":" in value:
            try:
                return int(value.split(":", 1)[0])
            except Exception:
                return None
        return None

    def _build_recurrence(self) -> Optional[RecurrenceRule]:
        freq = self.rec_frequency.get().strip()
        if freq == "(Yok)" or not freq:
            return None
        try:
            interval = int(self.rec_interval.get().strip() or "1")
        except Exception:
            interval = 1
        until = self.rec_until.get().strip()
        byweekday_raw = self.rec_byweekday.get().strip()
        byweekday = []
        if byweekday_raw:
            try:
                byweekday = [int(x.strip()) for x in byweekday_raw.split(",") if x.strip()]
            except Exception:
                byweekday = []
        bymonthday = self.rec_bymonthday.get().strip()
        return RecurrenceRule(
            frequency=freq,
            interval=interval,
            until=until,
            byweekday=byweekday,
            bymonthday=bymonthday,
        )


class AttachmentsWindow(tk.Toplevel):
    def __init__(self, parent, service: NotesRemindersService, note_id: int):
        super().__init__(parent)
        self.service = service
        self.note_id = note_id
        self.title("Ekler")
        self.geometry("420x280")
        self.resizable(False, False)
        self._build()
        self.grab_set()

    def _build(self) -> None:
        frm = ttk.Frame(self)
        frm.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        cols = ("id", "filename", "size")
        self.tree = ttk.Treeview(frm, columns=cols, show="headings", height=8)
        for c in cols:
            self.tree.heading(c, text=c.upper())
        self.tree.column("id", width=60, anchor="center")
        self.tree.column("filename", width=220)
        self.tree.column("size", width=80, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True, pady=6)
        self.tree.bind("<Double-1>", lambda _e: self._open_selected())

        btns = ttk.Frame(frm)
        btns.pack(fill=tk.X, pady=4)
        ttk.Button(btns, text="Aç", command=self._open_selected).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Kapat", command=self.destroy).pack(side=tk.RIGHT, padx=6)

        self._load()

    def _load(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for r in self.service.list_note_attachments(self.note_id):
            self.tree.insert("", tk.END, values=(r["id"], r["filename"], r["size_bytes"]))

    def _open_selected(self) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        stored = None
        for r in self.service.list_note_attachments(self.note_id):
            if int(r["id"]) == int(self.tree.item(sel[0], "values")[0]):
                stored = r["stored_name"]
                break
        if not stored:
            return
        try:
            path = self.service.get_note_attachment_path(str(stored))
            if os.name == "nt":
                os.startfile(path)
            else:
                import webbrowser

                webbrowser.open(path)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Dosya açılamadı: {exc}")


class LinkWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Bağlantı Ekle")
        self.geometry("320x180")
        self.resizable(False, False)
        self.result: Optional[Dict[str, str]] = None
        self._build()
        self.grab_set()
        self.wait_window()

    def _build(self) -> None:
        frm = ttk.Frame(self)
        frm.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        self.in_type = LabeledCombo(frm, "Tür:", ["customer", "invoice", "order", "employee", "project"], 14)
        self.in_type.pack(fill=tk.X, pady=4)
        self.in_type.set("customer")
        self.in_id = LabeledEntry(frm, "Kayıt ID:", 12)
        self.in_id.pack(fill=tk.X, pady=4)

        btns = ttk.Frame(frm)
        btns.pack(fill=tk.X, pady=8)
        ttk.Button(btns, text="Kaydet", command=self._save).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="İptal", command=self.destroy).pack(side=tk.RIGHT, padx=6)

    def _save(self) -> None:
        link_type = self.in_type.get().strip()
        link_id = self.in_id.get().strip()
        if not link_type or not link_id:
            messagebox.showerror(APP_TITLE, "Tür ve kayıt ID zorunlu.")
            return
        self.result = {"type": link_type, "id": link_id}
        self.destroy()
