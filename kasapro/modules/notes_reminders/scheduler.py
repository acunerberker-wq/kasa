# -*- coding: utf-8 -*-
"""Hatırlatma scheduler (thread-safe)."""

from __future__ import annotations

import queue
import threading
import time
from typing import Any, Dict, Optional

from .service import NotesRemindersService


class ReminderScheduler:
    def __init__(self, app, service: NotesRemindersService, interval_seconds: int = 45):
        self.app = app
        self.service = service
        self.interval_seconds = max(30, min(int(interval_seconds), 60))
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._queue: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        self._notified_ids: set[int] = set()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        try:
            self.app.root.after(800, self._poll_queue)
        except Exception:
            pass

    def stop(self) -> None:
        self._stop.set()

    def reset_context(self) -> None:
        self._notified_ids.clear()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                uid = self.app.get_active_user_id() if hasattr(self.app, "get_active_user_id") else None
                cid = getattr(self.app, "active_company_id", None)
                if uid:
                    due, overdue_count = self.service.check_due_reminders(cid, uid)
                    if due:
                        for item in due:
                            rid = int(item.get("id") or 0)
                            if rid and rid not in self._notified_ids:
                                self._queue.put({"type": "notify", "payload": item})
                                self._notified_ids.add(rid)
                    self._queue.put({"type": "badge", "payload": overdue_count})
            except Exception:
                self._queue.put({"type": "error", "payload": "scheduler"})
            time.sleep(self.interval_seconds)

    def _poll_queue(self) -> None:
        try:
            while True:
                msg = self._queue.get_nowait()
                self._handle_message(msg)
        except queue.Empty:
            pass
        if not self._stop.is_set():
            try:
                self.app.root.after(1000, self._poll_queue)
            except Exception:
                pass

    def _handle_message(self, msg: Dict[str, Any]) -> None:
        mtype = msg.get("type")
        if mtype == "notify":
            payload = msg.get("payload") or {}
            title = str(payload.get("title") or "Hatırlatma")
            due_at = str(payload.get("due_at") or "")
            try:
                self.app.show_toast(f"Hatırlatma: {title}\n{due_at}")
            except Exception:
                pass
        if mtype == "badge":
            count = int(msg.get("payload") or 0)
            try:
                if hasattr(self.app, "update_notes_reminders_badge"):
                    self.app.update_notes_reminders_badge(count)
            except Exception:
                pass
            try:
                if hasattr(self.app, "update_overdue_dashboard"):
                    self.app.update_overdue_dashboard(count)
            except Exception:
                pass
            try:
                frame = getattr(self.app, "frames", {}).get("rapor_araclar")
                if frame and hasattr(frame, "refresh_notes_reminders_badge"):
                    frame.refresh_notes_reminders_badge(count)
            except Exception:
                pass
        if mtype == "error":
            return
