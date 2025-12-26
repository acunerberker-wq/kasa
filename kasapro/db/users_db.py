# -*- coding: utf-8 -*-
"""KasaPro v3 - Kullanıcı/Şirket yetkilendirme DB'si (kasa_users.db)

Multi-company/multi-user routing burada yönetilir.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import secrets
from typing import Optional, List

from ..config import USERS_DB_FILENAME, DATA_DIRNAME, DB_FILENAME
from ..utils import make_salt, hash_password, _safe_slug, now_iso
from .main_db import DB

def _ensure_dir(p: str):
    try:
        os.makedirs(p, exist_ok=True)
    except Exception:
        pass

class UsersDB:
    """Uygulama kullanıcıları (kimlik doğrulama) için ayrı veritabanı.

    - Kullanıcıların verileri ayrı olsun diye, her kullanıcı için ayrı SQLite dosyası (DATA_DIRNAME altında) tutulur.
    - Bu sınıf sadece login + kullanıcı yönetimi içindir.
    """
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.users_db_path = os.path.join(base_dir, USERS_DB_FILENAME)
        self.data_dir = os.path.join(base_dir, DATA_DIRNAME)
        _ensure_dir(self.data_dir)

        # Allow using this connection from worker threads if needed.
        self.conn = sqlite3.connect(self.users_db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        try:
            self.conn.execute("PRAGMA foreign_keys = ON;")
        except Exception:
            pass
        self._init_schema()
        self._migrate_schema()
        self._ensure_default_admin_and_migrate()
        self._migrate_schema()

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass

    def _init_schema(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                salt TEXT NOT NULL,
                pass_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                db_file TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_login TEXT
            );
        """)
        self.conn.commit()

    def _user_exists(self, username: str) -> bool:
        r = self.conn.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone()
        return bool(r)

    def _ensure_default_admin_and_migrate(self):
        # 1) Eğer hiç kullanıcı yoksa default admin oluştur.
        row = self.conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()
        n = int(row["n"]) if row else 0
        if n == 0:
            self.add_user("admin", "admin", role="admin", create_db=True)

        # 2) Eski tek DB varsa (kasa_pro.db), admin'in DB'sine taşı.
        legacy = os.path.join(self.base_dir, DB_FILENAME)
        admin = self.get_user_by_username("admin")
        if not admin:
            return

        admin_db_path = self.get_user_db_path(admin)
        if os.path.exists(legacy) and not os.path.exists(admin_db_path):
            # Eski veriyi kaybetmemek için taşıyoruz (move).
            try:
                shutil.move(legacy, admin_db_path)
            except Exception:
                # move olmazsa kopyala
                try:
                    shutil.copy2(legacy, admin_db_path)
                except Exception:
                    pass

    def list_users(self) -> List[sqlite3.Row]:
        return list(self.conn.execute("SELECT * FROM users ORDER BY username COLLATE NOCASE"))

    def list_usernames(self) -> List[str]:
        return [str(r["username"]) for r in self.conn.execute("SELECT username FROM users ORDER BY username COLLATE NOCASE")]

    def get_user_by_username(self, username: str) -> Optional[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()

    def get_user_db_path(self, user_row: sqlite3.Row) -> str:
        return os.path.join(self.data_dir, str(user_row["db_file"]))

    def auth(self, username: str, password: str) -> Optional[sqlite3.Row]:
        u = self.get_user_by_username(username)
        if not u:
            return None
        salt = str(u["salt"])
        expected = str(u["pass_hash"])
        got = hash_password(password, salt)
        if not secrets.compare_digest(got, expected):
            return None
        # last_login güncelle
        try:
            self.conn.execute("UPDATE users SET last_login=? WHERE id=?", (now_iso(), int(u["id"])))
            self.conn.commit()
        except Exception:
            pass
        return self.get_user_by_username(username)

    def _next_db_filename(self, username: str) -> str:
        base = _safe_slug(username)
        fname = f"{base}.db"
        i = 2
        while os.path.exists(os.path.join(self.data_dir, fname)):
            fname = f"{base}_{i}.db"
            i += 1
        return fname

    def add_user(self, username: str, password: str, role: str = "user", create_db: bool = True) -> int:
        username = username.strip()
        if not username:
            raise ValueError("Kullanıcı adı boş olamaz.")
        if role not in ("admin", "user"):
            role = "user"
        if self._user_exists(username):
            raise ValueError("Bu kullanıcı zaten var.")
        salt = make_salt()
        pwh = hash_password(password, salt)
        db_file = self._next_db_filename(username)
        self.conn.execute(
            "INSERT INTO users(username,salt,pass_hash,role,db_file,created_at) VALUES(?,?,?,?,?,?)",
            (username, salt, pwh, role, db_file, now_iso())
        )
        self.conn.commit()
        uid = int(self.conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()["id"])
        if create_db:
            # Kullanıcı DB'sini oluştur
            db_path = os.path.join(self.data_dir, db_file)
            try:
                _ = DB(db_path)
                _.close()
            except Exception:
                pass
        try:
            # İlk şirket kaydını oluştur (kullanıcı DB'si = 1. şirket)
            if not self.list_companies(uid):
                self._create_default_company_for_user(uid, username, db_file)
        except Exception:
            pass
        return uid

    def set_password(self, username: str, new_password: str):
        u = self.get_user_by_username(username)
        if not u:
            raise ValueError("Kullanıcı bulunamadı.")
        salt = make_salt()
        pwh = hash_password(new_password, salt)
        self.conn.execute("UPDATE users SET salt=?, pass_hash=? WHERE username=?", (salt, pwh, username))
        self.conn.commit()

    def set_role(self, user_id: int, role: str):
        """Login kullanıcı rolünü değiştir.

        Not: Rol değişikliği, kullanıcı yeniden giriş yapınca etkili olur.
        """
        if role not in ("admin", "user"):
            role = "user"
        self.conn.execute("UPDATE users SET role=? WHERE id=?", (role, int(user_id)))
        self.conn.commit()

    
    def delete_user(self, username: str, delete_db_file: bool = False):
        u = self.get_user_by_username(username)
        if not u:
            return
        if str(u["username"]) == "admin":
            raise ValueError("admin kullanıcısı silinemez.")

        # Kullanıcının tüm şirket DB dosyalarını topla
        company_files = []
        try:
            uid = int(u["id"])
            for c in self.list_companies(uid):
                try:
                    company_files.append(str(c["db_file"]))
                except Exception:
                    pass
        except Exception:
            company_files = [str(u["db_file"])]

        self.conn.execute("DELETE FROM users WHERE username=?", (username,))
        self.conn.commit()

        if delete_db_file:
            for db_file in set(company_files):
                try:
                    db_path = os.path.join(self.data_dir, db_file)
                    if os.path.exists(db_path):
                        os.remove(db_path)
                except Exception:
                    pass


    # =========================
    # Şirket (Firma) Yönetimi
    # =========================

    def _table_columns(self, table: str) -> set:
        try:
            rows = list(self.conn.execute(f"PRAGMA table_info({table})"))
            cols = set()
            for r in rows:
                try:
                    cols.add(str(r["name"]))
                except Exception:
                    try:
                        cols.add(str(r[1]))
                    except Exception:
                        pass
            return cols
        except Exception:
            return set()

    def _ensure_company_db_exists(self, db_file: str):
        """Şirket DB dosyası yoksa oluştur."""
        try:
            db_path = os.path.join(self.data_dir, db_file)
            if not os.path.exists(db_path):
                _ = DB(db_path)
                _.close()
        except Exception:
            pass

    def _next_company_db_filename(self, username: str, company_name: str) -> str:
        base_u = _safe_slug(username) or "user"
        base_c = _safe_slug(company_name) or "company"
        base = f"{base_u}__{base_c}"
        fname = f"{base}.db"
        i = 2
        while os.path.exists(os.path.join(self.data_dir, fname)):
            fname = f"{base}_{i}.db"
            i += 1
        return fname

    def _create_default_company_for_user(self, user_id: int, username: str, db_file: str) -> Optional[int]:
        """Eski (tek DB) düzeninden gelen kullanıcılar için varsayılan şirket oluşturur."""
        name = "1. Şirket"
        # Aynı isim varsa alternatif dene
        existing = self.conn.execute("SELECT 1 FROM companies WHERE user_id=? AND name=?", (user_id, name)).fetchone()
        if existing:
            name = "Ana Şirket"
        try:
            self.conn.execute(
                "INSERT INTO companies(user_id,name,db_file,created_at) VALUES(?,?,?,?)",
                (user_id, name, db_file, now_iso())
            )
            self.conn.commit()
            cid = int(self.conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"])
        except Exception:
            return None

        self._ensure_company_db_exists(db_file)

        # last_company_id kolonunu set etmeye çalış
        try:
            cols = self._table_columns("users")
            if "last_company_id" in cols:
                self.conn.execute("UPDATE users SET last_company_id=? WHERE id=?", (cid, user_id))
                self.conn.commit()
        except Exception:
            pass
        return cid

    def _migrate_schema(self):
        """UsersDB şemasını güncelle: şirket tablosu + kullanıcı last_company_id."""
        try:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS companies(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    db_file TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(user_id, name),
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );
            """)
        except sqlite3.OperationalError:
            pass  # Tablo zaten var

        # users tablosuna last_company_id ekle (yoksa)
        try:
            cols = self._table_columns("users")
            if "last_company_id" not in cols:
                try:
                    self.conn.execute("ALTER TABLE users ADD COLUMN last_company_id INTEGER;")
                except sqlite3.OperationalError:
                    pass  # Kolon zaten var
        except Exception:
            pass

        try:
            self.conn.commit()
        except Exception:
            pass

        # Her kullanıcı için en az 1 şirket olsun
        try:
            cols = self._table_columns("users")
            if "last_company_id" in cols:
                users = list(self.conn.execute("SELECT id, username, db_file, last_company_id FROM users"))
            else:
                users = list(self.conn.execute("SELECT id, username, db_file FROM users"))
        except Exception:
            users = []

        for u in users:
            try:
                uid = int(u["id"])
                uname = str(u["username"])
                db_file = str(u["db_file"])
                last_cid = None
                try:
                    last_cid = u["last_company_id"]
                except Exception:
                    last_cid = None

                comps = list(self.conn.execute("SELECT id, name, db_file FROM companies WHERE user_id=? ORDER BY id", (uid,)))
                if not comps:
                    self._create_default_company_for_user(uid, uname, db_file)
                    comps = list(self.conn.execute("SELECT id, name, db_file FROM companies WHERE user_id=? ORDER BY id", (uid,)))
                    if not comps:
                        continue
                # last_company_id geçerli mi?
                try:
                    cols2 = self._table_columns("users")
                    if "last_company_id" in cols2:
                        valid_ids = {int(c["id"]) for c in comps}
                        if last_cid is None or int(last_cid) not in valid_ids:
                            new_id = int(comps[0]["id"])
                            self.conn.execute("UPDATE users SET last_company_id=? WHERE id=?", (new_id, uid))
                            self.conn.commit()
                except Exception:
                    pass

                # DB dosyaları mevcut mu?
                for c in comps:
                    try:
                        self._ensure_company_db_exists(str(c["db_file"]))
                    except Exception:
                        pass
            except Exception:
                continue

    def list_companies(self, user_id: int):
        try:
            return list(self.conn.execute(
                "SELECT * FROM companies WHERE user_id=? ORDER BY id",
                (int(user_id),)
            ))
        except Exception:
            return []

    def get_company_by_id(self, company_id: int):
        try:
            return self.conn.execute("SELECT * FROM companies WHERE id=?", (int(company_id),)).fetchone()
        except Exception:
            return None

    def get_company_db_path(self, company_row: sqlite3.Row) -> str:
        return os.path.join(self.data_dir, str(company_row["db_file"]))

    def get_active_company_for_user(self, user_row: sqlite3.Row) -> Optional[sqlite3.Row]:
        """Kullanıcının son kullandığı (yoksa ilk) şirketini döndürür."""
        try:
            uid = int(user_row["id"])
        except Exception:
            return None

        comps = self.list_companies(uid)
        if not comps:
            # migrasyon eksik kaldıysa güvenlik
            try:
                self._migrate_schema()
            except Exception:
                pass
            comps = self.list_companies(uid)
            if not comps:
                return None

        last_id = None
        try:
            last_id = user_row["last_company_id"]
        except Exception:
            last_id = None
        if last_id:
            c = self.get_company_by_id(int(last_id))
            if c and int(c["user_id"]) == uid:
                return c
        return comps[0]

    def set_last_company_id(self, user_id: int, company_id: int):
        try:
            cols = self._table_columns("users")
            if "last_company_id" not in cols:
                return
            self.conn.execute("UPDATE users SET last_company_id=? WHERE id=?", (int(company_id), int(user_id)))
            self.conn.commit()
        except Exception:
            pass

    def add_company(self, user_id: int, company_name: str) -> int:
        company_name = (company_name or "").strip()
        if not company_name:
            raise ValueError("Şirket adı boş olamaz.")
        # kullanıcıyı bul
        u = self.conn.execute("SELECT id, username FROM users WHERE id=?", (int(user_id),)).fetchone()
        if not u:
            raise ValueError("Kullanıcı bulunamadı.")
        uname = str(u["username"])
        db_file = self._next_company_db_filename(uname, company_name)
        # DB oluştur
        self._ensure_company_db_exists(db_file)
        # kaydet
        self.conn.execute(
            "INSERT INTO companies(user_id,name,db_file,created_at) VALUES(?,?,?,?)",
            (int(user_id), company_name, db_file, now_iso())
        )
        self.conn.commit()
        cid = int(self.conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"])
        self.set_last_company_id(int(user_id), cid)
        return cid

    def rename_company(self, company_id: int, new_name: str):
        new_name = (new_name or "").strip()
        if not new_name:
            raise ValueError("Şirket adı boş olamaz.")
        c = self.get_company_by_id(company_id)
        if not c:
            raise ValueError("Şirket bulunamadı.")
        uid = int(c["user_id"])
        # Aynı isim var mı?
        ex = self.conn.execute(
            "SELECT 1 FROM companies WHERE user_id=? AND name=? AND id<>?",
            (uid, new_name, int(company_id))
        ).fetchone()
        if ex:
            raise ValueError("Bu isimde bir şirket zaten var.")
        self.conn.execute("UPDATE companies SET name=? WHERE id=?", (new_name, int(company_id)))
        self.conn.commit()

    def delete_company(self, company_id: int, delete_db_file: bool = True):
        c = self.get_company_by_id(company_id)
        if not c:
            return
        uid = int(c["user_id"])
        db_file = str(c["db_file"])
        # En az 1 şirket kalsın
        comps = self.list_companies(uid)
        if len(comps) <= 1:
            raise ValueError("En az 1 şirket kalmalıdır.")
        self.conn.execute("DELETE FROM companies WHERE id=?", (int(company_id),))
        self.conn.commit()
        if delete_db_file:
            try:
                db_path = os.path.join(self.data_dir, db_file)
                if os.path.exists(db_path):
                    os.remove(db_path)
            except Exception:
                pass
        # Eğer silinen son şirket ise başka birini seç
        try:
            cols = self._table_columns("users")
            if "last_company_id" in cols:
                u = self.conn.execute("SELECT last_company_id FROM users WHERE id=?", (uid,)).fetchone()
                last = u["last_company_id"] if u else None
                if last and int(last) == int(company_id):
                    new_first = self.conn.execute(
                        "SELECT id FROM companies WHERE user_id=? ORDER BY id LIMIT 1",
                        (uid,)
                    ).fetchone()
                    if new_first:
                        self.set_last_company_id(uid, int(new_first["id"]))
        except Exception:
            pass
