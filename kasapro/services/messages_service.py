# -*- coding: utf-8 -*-
"""Şirket içi mesajlaşma iş kuralları ve dosya işlemleri."""

from __future__ import annotations

import os
import re
import shutil
import uuid
from typing import Iterable, List, Optional, Sequence, Tuple

from ..config import MESSAGE_ATTACHMENTS_DIRNAME, MESSAGE_ATTACHMENT_MAX_BYTES
from ..db.main_db import DB
from ..db.users_db import UsersDB


class MessagesService:
    def __init__(self, db: DB, usersdb: UsersDB):
        self.db = db
        self.usersdb = usersdb

    def list_users(self) -> List[Tuple[int, str]]:
        users = []
        for r in self.usersdb.list_users():
            try:
                users.append((int(r["id"]), str(r["username"])))
            except Exception:
                continue
        return users

    def _attachments_root(self) -> str:
        data_dir = os.path.dirname(self.db.path)
        base = os.path.splitext(os.path.basename(self.db.path))[0] or "company"
        root = os.path.join(data_dir, MESSAGE_ATTACHMENTS_DIRNAME, base)
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

    def save_attachment(self, source_path: str) -> Tuple[str, str, int]:
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
        return original, stored_name, size

    def get_attachment_path(self, stored_name: str) -> str:
        root = self._attachments_root()
        safe = self._safe_filename(stored_name)
        return self._ensure_path_inside(root, os.path.join(root, safe))

    def send_message(
        self,
        sender_id: int,
        sender_username: str,
        recipients: Sequence[Tuple[int, str]],
        subject: str,
        body: str,
        attachments: Optional[Sequence[str]] = None,
    ) -> int:
        msg_id = self.db.message_create(sender_id, sender_username, subject, body, is_draft=0)
        self.db.message_recipients_set(msg_id, recipients)
        self._save_attachments(msg_id, attachments or [])
        try:
            self.db.log("Mesaj", f"Gönderildi (id={msg_id}) {sender_username} -> {len(recipients)} kişi")
        except Exception:
            pass
        return msg_id

    def save_draft(
        self,
        sender_id: int,
        sender_username: str,
        recipients: Sequence[Tuple[int, str]],
        subject: str,
        body: str,
        attachments: Optional[Sequence[str]] = None,
    ) -> int:
        msg_id = self.db.message_create(sender_id, sender_username, subject, body, is_draft=1)
        if recipients:
            self.db.message_recipients_set(msg_id, recipients)
        self._save_attachments(msg_id, attachments or [])
        try:
            self.db.log("Mesaj", f"Taslak kaydedildi (id={msg_id})")
        except Exception:
            pass
        return msg_id

    def update_draft_and_send(
        self,
        message_id: int,
        sender_id: int,
        sender_username: str,
        recipients: Sequence[Tuple[int, str]],
        subject: str,
        body: str,
        attachments: Optional[Sequence[str]] = None,
    ) -> None:
        row = self.db.message_get_for_sender(message_id, sender_id)
        if not row or int(row["is_draft"]) != 1:
            raise ValueError("Taslak bulunamadı.")
        self.db.message_update(message_id, subject, body, is_draft=0)
        self.db.message_recipients_set(message_id, recipients)
        self._save_attachments(message_id, attachments or [])
        try:
            self.db.log("Mesaj", f"Taslak gönderildi (id={message_id})")
        except Exception:
            pass

    def update_draft(
        self,
        message_id: int,
        sender_id: int,
        recipients: Sequence[Tuple[int, str]],
        subject: str,
        body: str,
        attachments: Optional[Sequence[str]] = None,
    ) -> None:
        row = self.db.message_get_for_sender(message_id, sender_id)
        if not row or int(row["is_draft"]) != 1:
            raise ValueError("Taslak bulunamadı.")
        self.db.message_update(message_id, subject, body, is_draft=1)
        self.db.message_recipients_set(message_id, recipients)
        self._save_attachments(message_id, attachments or [])
        try:
            self.db.log("Mesaj", f"Taslak güncellendi (id={message_id})")
        except Exception:
            pass

    def _save_attachments(self, message_id: int, attachments: Iterable[str]) -> None:
        for path in attachments:
            original, stored_name, size = self.save_attachment(path)
            self.db.message_attachment_add(message_id, original, stored_name, size)

    def mark_read(self, message_id: int, recipient_id: int) -> None:
        self.db.message_mark_read(message_id, recipient_id)
        try:
            self.db.log("Mesaj", f"Okundu (id={message_id})")
        except Exception:
            pass
