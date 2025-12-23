# -*- coding: utf-8 -*-

from __future__ import annotations

import secrets
import sqlite3
from typing import List, Optional

from ...utils import make_salt, hash_password, now_iso


class UsersRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def auth(self, username: str, password: str) -> Optional[sqlite3.Row]:
        cur = self.conn.execute("SELECT * FROM users WHERE username=?", (username.strip(),))
        u = cur.fetchone()
        if not u:
            return None
        if secrets.compare_digest(hash_password(password, u["salt"]), u["pass_hash"]):
            return u
        return None

    def list(self) -> List[sqlite3.Row]:
        return list(self.conn.execute("SELECT id,username,role,created_at FROM users ORDER BY username"))

    def add(self, username: str, password: str, role: str):
        salt = make_salt()
        self.conn.execute(
            "INSERT INTO users(username,salt,pass_hash,role,created_at) VALUES(?,?,?,?,?)",
            (username.strip(), salt, hash_password(password, salt), role, now_iso()),
        )
        self.conn.commit()

    def set_password(self, user_id: int, new_password: str):
        salt = make_salt()
        self.conn.execute(
            "UPDATE users SET salt=?, pass_hash=? WHERE id=?",
            (salt, hash_password(new_password, salt), int(user_id)),
        )
        self.conn.commit()

    def set_role(self, user_id: int, role: str):
        self.conn.execute("UPDATE users SET role=? WHERE id=?", (role, int(user_id)))
        self.conn.commit()

    def delete(self, user_id: int):
        self.conn.execute("DELETE FROM users WHERE id=?", (int(user_id),))
        self.conn.commit()
