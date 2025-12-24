# -*- coding: utf-8 -*-
"""Şirket içi kullanıcı yönetimi (company DB)."""

from __future__ import annotations


from ..db.main_db import DB


class CompanyUsersService:
    def __init__(self, db: DB):
        self.db = db

    def list(self):
        return self.db.users_list()

    def add(self, username: str, password: str, role: str = "user"):
        if not username.strip():
            raise ValueError("username boş olamaz")
        if not password:
            raise ValueError("password boş olamaz")
        if role not in ("admin", "user"):
            role = "user"
        self.db.user_add(username.strip(), password, role)

    def set_password(self, user_id: int, new_password: str):
        if not new_password:
            raise ValueError("new_password boş olamaz")
        self.db.user_set_password(int(user_id), new_password)

    def set_role(self, user_id: int, role: str):
        if role not in ("admin", "user"):
            raise ValueError("role geçersiz")
        self.db.user_set_role(int(user_id), role)

    def delete(self, user_id: int):
        self.db.user_delete(int(user_id))
