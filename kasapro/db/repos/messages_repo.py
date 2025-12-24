# -*- coding: utf-8 -*-
"""Şirket içi mesajlaşma veritabanı erişim katmanı."""

from __future__ import annotations

import sqlite3
from typing import Iterable, List, Optional, Tuple

from ...utils import now_iso


class MessagesRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create_message(
        self,
        sender_id: int,
        sender_username: str,
        subject: str,
        body: str,
        is_draft: int = 0,
    ) -> int:
        ts = now_iso()
        cur = self.conn.execute(
            """
            INSERT INTO messages(sender_id, sender_username, subject, body, is_draft, created_at, updated_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            (int(sender_id), str(sender_username), subject, body, int(is_draft), ts, ts),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def update_message(self, message_id: int, subject: str, body: str, is_draft: int) -> None:
        self.conn.execute(
            """
            UPDATE messages
            SET subject=?, body=?, is_draft=?, updated_at=?
            WHERE id=?
            """,
            (subject, body, int(is_draft), now_iso(), int(message_id)),
        )
        self.conn.commit()

    def delete_message(self, message_id: int) -> None:
        self.conn.execute("DELETE FROM messages WHERE id=?", (int(message_id),))
        self.conn.commit()

    def clear_recipients(self, message_id: int) -> None:
        self.conn.execute("DELETE FROM message_recipients WHERE message_id=?", (int(message_id),))
        self.conn.commit()

    def add_recipients(self, message_id: int, recipients: Iterable[Tuple[int, str]]) -> None:
        ts = now_iso()
        rows = [(int(message_id), int(uid), str(uname), ts) for uid, uname in recipients]
        if not rows:
            return
        self.conn.executemany(
            """
            INSERT INTO message_recipients(message_id, recipient_id, recipient_username, created_at)
            VALUES(?,?,?,?)
            """,
            rows,
        )
        self.conn.commit()

    def list_inbox(
        self,
        recipient_id: int,
        q: str = "",
        only_unread: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[sqlite3.Row]:
        params: List[object] = [int(recipient_id)]
        where = ["mr.recipient_id=?","m.is_draft=0"]
        if only_unread:
            where.append("mr.is_read=0")
        if q:
            like = f"%{q}%"
            where.append(
                "(m.subject LIKE ? OR m.body LIKE ? OR m.sender_username LIKE ?)"
            )
            params.extend([like, like, like])
        params.extend([int(limit), int(offset)])
        sql = f"""
            SELECT m.id AS message_id,
                   m.subject,
                   m.body,
                   m.sender_username,
                   m.created_at,
                   mr.is_read,
                   mr.read_at
            FROM messages m
            JOIN message_recipients mr ON mr.message_id = m.id
            WHERE {' AND '.join(where)}
            ORDER BY m.created_at DESC
            LIMIT ? OFFSET ?
        """
        return list(self.conn.execute(sql, params))

    def list_sent(
        self,
        sender_id: int,
        q: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> List[sqlite3.Row]:
        params: List[object] = [int(sender_id)]
        where = ["m.sender_id=?","m.is_draft=0"]
        if q:
            like = f"%{q}%"
            where.append(
                "(m.subject LIKE ? OR m.body LIKE ? OR EXISTS ("
                "SELECT 1 FROM message_recipients mr2 WHERE mr2.message_id=m.id AND mr2.recipient_username LIKE ?))"
            )
            params.extend([like, like, like])
        params.extend([int(limit), int(offset)])
        sql = f"""
            SELECT m.id AS message_id,
                   m.subject,
                   m.body,
                   m.created_at,
                   (
                     SELECT GROUP_CONCAT(recipient_username, ', ')
                     FROM message_recipients
                     WHERE message_id = m.id
                   ) AS recipients
            FROM messages m
            WHERE {' AND '.join(where)}
            ORDER BY m.created_at DESC
            LIMIT ? OFFSET ?
        """
        return list(self.conn.execute(sql, params))

    def list_drafts(
        self,
        sender_id: int,
        q: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> List[sqlite3.Row]:
        params: List[object] = [int(sender_id)]
        where = ["m.sender_id=?","m.is_draft=1"]
        if q:
            like = f"%{q}%"
            where.append("(m.subject LIKE ? OR m.body LIKE ?)")
            params.extend([like, like])
        params.extend([int(limit), int(offset)])
        sql = f"""
            SELECT m.id AS message_id,
                   m.subject,
                   m.body,
                   m.created_at,
                   (
                     SELECT GROUP_CONCAT(recipient_username, ', ')
                     FROM message_recipients
                     WHERE message_id = m.id
                   ) AS recipients
            FROM messages m
            WHERE {' AND '.join(where)}
            ORDER BY m.updated_at DESC
            LIMIT ? OFFSET ?
        """
        return list(self.conn.execute(sql, params))

    def get_message_for_recipient(self, message_id: int, recipient_id: int) -> Optional[sqlite3.Row]:
        return self.conn.execute(
            """
            SELECT m.*, mr.is_read, mr.read_at
            FROM messages m
            JOIN message_recipients mr ON mr.message_id = m.id
            WHERE m.id=? AND mr.recipient_id=? AND m.is_draft=0
            """,
            (int(message_id), int(recipient_id)),
        ).fetchone()

    def get_message_for_sender(self, message_id: int, sender_id: int) -> Optional[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM messages WHERE id=? AND sender_id=?",
            (int(message_id), int(sender_id)),
        ).fetchone()

    def list_recipients(self, message_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT recipient_id, recipient_username, is_read, read_at FROM message_recipients WHERE message_id=?",
                (int(message_id),),
            )
        )

    def mark_read(self, message_id: int, recipient_id: int) -> None:
        self.conn.execute(
            """
            UPDATE message_recipients
            SET is_read=1, read_at=?
            WHERE message_id=? AND recipient_id=?
            """,
            (now_iso(), int(message_id), int(recipient_id)),
        )
        self.conn.commit()

    def get_unread_count(self, recipient_id: int) -> int:
        row = self.conn.execute(
            """
            SELECT COUNT(*) AS n
            FROM message_recipients mr
            JOIN messages m ON m.id = mr.message_id
            WHERE mr.recipient_id=? AND mr.is_read=0 AND m.is_draft=0
            """,
            (int(recipient_id),),
        ).fetchone()
        return int(row["n"]) if row else 0

    def add_attachment(self, message_id: int, filename: str, stored_name: str, size_bytes: int) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO message_attachments(message_id, filename, stored_name, size_bytes, created_at)
            VALUES(?,?,?,?,?)
            """,
            (int(message_id), filename, stored_name, int(size_bytes), now_iso()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list_attachments(self, message_id: int) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM message_attachments WHERE message_id=? ORDER BY id",
                (int(message_id),),
            )
        )
