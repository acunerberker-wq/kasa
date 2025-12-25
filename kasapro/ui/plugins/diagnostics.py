# -*- coding: utf-8 -*-
"""UI Plugin: Sistem Testleri / Sağlık Kontrolü.

Bu ekran; uygulamanın temel altyapısını ve kritik fonksiyon çağrılarını
çalıştırarak hızlı bir sağlık kontrolü sağlar.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
import os
import shutil
import time
import threading
from queue import Queue, Empty
from typing import Callable, Dict, List, Tuple, TYPE_CHECKING

import tkinter as tk
from tkinter import ttk, messagebox

from ..base import BaseView
from ..ui_logging import wrap_callback

import logging
from ...config import (
    APP_BASE_DIR,
    APP_TITLE,
    DATA_DIRNAME,
    LOG_DIRNAME,
    SHARED_STORAGE_DIRNAME,
    HAS_OPENPYXL,
    HAS_REPORTLAB,
    HAS_TKSHEET,
)
from ...core.version import __version__ as APP_VERSION

if TYPE_CHECKING:
    from ...app import App

PLUGIN_META = {
    "key": "diagnostics",
    "name": "Sistem Testleri",
    "version": "1.1.0",
    "enabled": True,
    "nav_text": "🧪 Sistem Testleri",
    "page_title": "Sistem Testleri",
    "order": 95,
}


logger = logging.getLogger("kasapro.plugins.diagnostics")

CONFIG_KEY = "diagnostics.config"
DEFAULT_CONFIG = {
    "auto_run": False,
    "min_free_mb": 100,
}


def _ensure_logger() -> None:
    if any(isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", "").endswith("app.log") for h in logger.handlers):
        return
    log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "..", "logs", "app.log")
    log_path = os.path.abspath(log_path)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    handler = logging.FileHandler(log_path)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def _validate_config(config: Dict[str, object]) -> Dict[str, object]:
    auto_run = bool(config.get("auto_run", DEFAULT_CONFIG["auto_run"]))
    min_free_mb = config.get("min_free_mb", DEFAULT_CONFIG["min_free_mb"])
    try:
        min_free_mb = int(min_free_mb)
    except Exception:
        min_free_mb = DEFAULT_CONFIG["min_free_mb"]
    if min_free_mb < 10:
        min_free_mb = DEFAULT_CONFIG["min_free_mb"]
    return {"auto_run": auto_run, "min_free_mb": min_free_mb}


def load_config(db) -> Dict[str, object]:
    raw = None
    try:
        raw = db.get_setting(CONFIG_KEY)
    except Exception:
        raw = None
    if not raw:
        return DEFAULT_CONFIG.copy()
    try:
        payload = json.loads(raw)
        if isinstance(payload, dict):
            return _validate_config(payload)
    except Exception:
        pass
    return DEFAULT_CONFIG.copy()


def save_config(db, config: Dict[str, object]) -> None:
    validated = _validate_config(config)
    db.set_setting(CONFIG_KEY, json.dumps(validated))


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


class DiagnosticsFrame(BaseView):
    def __init__(self, master, app: "App"):
        self.app = app
        super().__init__(master, app)
        self.status_var = tk.StringVar(value="Hazır")
        self._queue: "Queue[List[CheckResult]]" = Queue()
        self._worker: threading.Thread | None = None
        self._config = load_config(self.app.db)
        self.build_ui()
        if self._config.get("auto_run"):
            self.after(200, self.run_checks)

    def build_ui(self) -> None:
        self._build()

    def _build(self):
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=10, pady=(10, 6))

        title = ttk.Label(header, text="Sistem Sağlık Kontrolü", font=("Segoe UI", 12, "bold"))
        title.pack(side=tk.LEFT)

        status = ttk.Label(header, textvariable=self.status_var)
        status.pack(side=tk.RIGHT)

        note = ttk.Label(
            self,
            text=(
                "Bu ekran veritabanı bağlantısı, dizin erişimi, temel okuma akışları ve yapılandırma kontrollerini çalıştırır."
            ),
            foreground="#555",
        )
        note.pack(fill=tk.X, padx=10)

        actions = ttk.Frame(self)
        actions.pack(fill=tk.X, padx=10, pady=6)
        self.btn_run = ttk.Button(actions, text="Testleri Çalıştır", command=wrap_callback("diagnostics_run", self.run_checks))
        self.btn_run.pack(side=tk.LEFT)
        ttk.Button(actions, text="Temizle", command=wrap_callback("diagnostics_clear", self.clear_results)).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(actions, text="Raporu Kopyala", command=wrap_callback("diagnostics_copy", self.copy_report)).pack(
            side=tk.LEFT
        )

        settings = ttk.LabelFrame(self, text="Ayarlar")
        settings.pack(fill=tk.X, padx=10, pady=(0, 6))
        self.auto_run_var = tk.BooleanVar(value=bool(self._config.get("auto_run")))
        ttk.Checkbutton(settings, text="Açılışta otomatik çalıştır", variable=self.auto_run_var).pack(side=tk.LEFT, padx=6)
        ttk.Label(settings, text="Minimum boş alan (MB):").pack(side=tk.LEFT, padx=(12, 4))
        self.min_free_var = tk.StringVar(value=str(self._config.get("min_free_mb", 100)))
        ttk.Entry(settings, textvariable=self.min_free_var, width=8).pack(side=tk.LEFT)
        ttk.Button(settings, text="Kaydet", command=wrap_callback("diagnostics_save_cfg", self._save_config)).pack(side=tk.LEFT, padx=8)

        if not getattr(self.app, "is_admin", True):
            ttk.Label(self, text="Bu ekran yalnızca yöneticiler için kullanılabilir.", foreground="#b00020").pack(
                anchor="w",
                padx=10,
                pady=(0, 6),
            )
            self.btn_run.config(state="disabled")

        table_wrap = ttk.Frame(self)
        table_wrap.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        columns = ("test", "status", "detail")
        self.tree = ttk.Treeview(table_wrap, columns=columns, show="headings", height=16)
        self.tree.heading("test", text="Test")
        self.tree.heading("status", text="Durum")
        self.tree.heading("detail", text="Detay")
        self.tree.column("test", width=240)
        self.tree.column("status", width=120, anchor="center")
        self.tree.column("detail", width=700)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(table_wrap, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

    def clear_results(self):
        for row_id in self.tree.get_children():
            self.tree.delete(row_id)
        self.status_var.set("Hazır")

    def run_checks(self):
        if self._worker and self._worker.is_alive():
            return
        if not getattr(self.app, "is_admin", True):
            messagebox.showwarning(APP_TITLE, "Bu ekran yalnızca yöneticiler için kullanılabilir.")
            return
        self.clear_results()
        self.status_var.set("Testler çalıştırılıyor...")
        self.btn_run.config(state="disabled")
        self.update_idletasks()
        _ensure_logger()
        logger.info("Diagnostics run started")

        def worker():
            start = time.time()
            results: List[CheckResult] = []
            for name, fn in self._checks():
                results.append(self._run_check(name, fn))
            elapsed = time.time() - start
            self._queue.put(results + [CheckResult(name="__elapsed__", ok=True, detail=f"{elapsed:.2f}")])

        self._worker = threading.Thread(target=worker, daemon=True)
        self._worker.start()
        self.after(100, self._poll_results)

    def copy_report(self):
        report = self._build_report_text()
        if not report:
            messagebox.showinfo(APP_TITLE, "Kopyalanacak rapor bulunamadı.")
            return
        try:
            self.clipboard_clear()
            self.clipboard_append(report)
            messagebox.showinfo(APP_TITLE, "Rapor panoya kopyalandı.")
        except Exception:
            messagebox.showwarning(APP_TITLE, "Rapor kopyalanırken bir hata oluştu.")

    def _build_report_text(self) -> str:
        rows = self.tree.get_children()
        if not rows:
            return ""
        lines = ["KasaPro Sistem Testleri"]
        for row_id in rows:
            test, status, detail = self.tree.item(row_id, "values")
            lines.append(f"- {status} {test}: {detail}")
        return "\n".join(lines)

    def _run_check(self, name: str, fn: Callable[[], Tuple[bool, str]]) -> CheckResult:
        try:
            ok, detail = fn()
        except Exception as exc:
            _ensure_logger()
            logger.exception("Diagnostics check failed: %s", name)
            ok = False
            detail = f"Beklenmeyen hata: {exc}"
        return CheckResult(name=name, ok=ok, detail=detail)

    def _poll_results(self) -> None:
        try:
            payload = self._queue.get_nowait()
        except Empty:
            self.after(100, self._poll_results)
            return
        elapsed = 0.0
        if payload and payload[-1].name == "__elapsed__":
            try:
                elapsed = float(payload[-1].detail)
            except Exception:
                elapsed = 0.0
            payload = payload[:-1]

        total = len(payload)
        ok_count = sum(1 for r in payload if r.ok)
        fail_count = total - ok_count

        for res in payload:
            self.tree.insert(
                "",
                tk.END,
                values=(
                    res.name,
                    "✅ Başarılı" if res.ok else "❌ Hata",
                    res.detail,
                ),
            )
        self.status_var.set(f"{total} test: {ok_count} başarılı, {fail_count} hata ({elapsed:.2f} sn)")
        self.btn_run.config(state="normal")
        _ensure_logger()
        logger.info("Diagnostics run finished: total=%s ok=%s fail=%s", total, ok_count, fail_count)

    def _save_config(self) -> None:
        config = {
            "auto_run": bool(self.auto_run_var.get()),
            "min_free_mb": self.min_free_var.get(),
        }
        config = _validate_config(config)
        save_config(self.app.db, config)
        self._config = config
        messagebox.showinfo(APP_TITLE, "Ayarlar kaydedildi.")

    def _checks(self) -> List[Tuple[str, Callable[[], Tuple[bool, str]]]]:
        return [
            ("Sürüm bilgisi", self._check_version),
            ("Uygulama dizinleri", self._check_directories),
            ("Disk alanı", self._check_disk_space),
            ("Veri dizini yazılabilir mi", self._check_data_dir),
            ("Log dizini yazılabilir mi", self._check_log_dir),
            ("Kullanıcı DB bağlantısı", self._check_users_db),
            ("Şirket DB bağlantısı", self._check_company_db),
            ("Kullanıcı şirket kayıtları", self._check_user_companies),
            ("Zorunlu tablolar", self._check_required_tables),
            ("DB bütünlük kontrolü", self._check_integrity),
            ("Foreign key ayarı", self._check_foreign_keys),
            ("Varsayılan ayarlar", self._check_settings),
            ("Repo okuma fonksiyonları", self._check_repo_calls),
            ("Tablo sayımları", self._check_table_counts),
            ("Opsiyonel bağımlılıklar", self._check_optional_dependencies),
        ]

    def _check_version(self) -> Tuple[bool, str]:
        return True, f"Sürüm: {APP_VERSION}"

    def _check_directories(self) -> Tuple[bool, str]:
        base_dir = APP_BASE_DIR
        data_dir = os.path.join(base_dir, DATA_DIRNAME)
        shared_dir = os.path.join(base_dir, SHARED_STORAGE_DIRNAME)
        
        # Eksik dizinleri oluşturmayı dene
        created = []
        for p in (data_dir, shared_dir):
            if not os.path.isdir(p):
                try:
                    os.makedirs(p, exist_ok=True)
                    created.append(os.path.basename(p))
                except Exception:
                    pass
        
        missing = [p for p in (base_dir, data_dir, shared_dir) if not os.path.isdir(p)]
        if missing:
            return False, f"Eksik dizinler: {', '.join(missing)}"
        
        if created:
            return True, f"Base: {base_dir} (Oluşturuldu: {', '.join(created)})"
        return True, f"Base: {base_dir}"

    def _check_disk_space(self) -> Tuple[bool, str]:
        try:
            total, used, free = shutil.disk_usage(APP_BASE_DIR)
        except Exception as exc:
            return False, f"Disk bilgisi okunamadı: {exc}"
        free_mb = free / (1024 * 1024)
        threshold = int(self._config.get("min_free_mb", 100))
        if free_mb < threshold:
            return False, f"Düşük disk alanı: {free_mb:.1f} MB"
        return True, f"Boş alan: {free_mb:.1f} MB"

    def _check_data_dir(self) -> Tuple[bool, str]:
        data_dir = os.path.join(APP_BASE_DIR, DATA_DIRNAME)
        if not os.path.isdir(data_dir):
            return False, f"Data dizini yok: {data_dir}"
        test_path = os.path.join(data_dir, ".diag_write_test")
        try:
            with open(test_path, "w", encoding="utf-8") as f:
                f.write("ok")
            os.remove(test_path)
        except Exception as exc:
            return False, f"Data dizinine yazılamıyor: {exc}"
        return True, f"Data dizini yazılabilir: {data_dir}"

    def _check_log_dir(self) -> Tuple[bool, str]:
        log_dir = os.path.join(APP_BASE_DIR, LOG_DIRNAME)
        if not os.path.isdir(log_dir):
            return False, f"Log dizini bulunamadı: {log_dir}"
        test_path = os.path.join(log_dir, ".diag_log_test")
        try:
            with open(test_path, "w", encoding="utf-8") as f:
                f.write("ok")
            os.remove(test_path)
        except Exception as exc:
            return False, f"Log dizinine yazılamıyor: {exc}"
        return True, f"Log dizini hazır: {log_dir}"

    def _check_users_db(self) -> Tuple[bool, str]:
        self.app.usersdb.conn.execute("SELECT 1")
        users = self.app.usersdb.list_users()
        return True, f"Kullanıcı sayısı: {len(users)} ({self.app.usersdb.users_db_path})"

    def _check_company_db(self) -> Tuple[bool, str]:
        self.app.db.conn.execute("SELECT 1")
        if not os.path.exists(self.app.db.path):
            return False, f"DB dosyası bulunamadı: {self.app.db.path}"
        return True, f"DB: {self.app.db.path}"

    def _check_user_companies(self) -> Tuple[bool, str]:
        user_id = getattr(self.app, "data_owner_user_id", None)
        if not user_id:
            return False, "Aktif kullanıcı ID bulunamadı"
        companies = self.app.usersdb.list_companies(int(user_id))
        if not companies:
            return False, "Kullanıcıya bağlı şirket bulunamadı"
        missing = []
        for c in companies:
            try:
                path = self.app.usersdb.get_company_db_path(c)
            except Exception:
                path = ""
            if path and not os.path.exists(path):
                missing.append(path)
        if missing:
            return False, f"Eksik şirket DB: {', '.join(missing)}"
        return True, f"Şirket sayısı: {len(companies)}"

    def _check_required_tables(self) -> Tuple[bool, str]:
        expected = {
            "users",
            "settings",
            "cariler",
            "cari_hareket",
            "kasa_hareket",
            "banka_hareket",
            "fatura",
            "fatura_kalem",
            "fatura_odeme",
            "fatura_seri",
            "logs",
            "stok_urun",
            "stok_lokasyon",
            "stok_parti",
            "stok_hareket",
            "maas_meslek",
            "maas_calisan",
            "maas_odeme",
            "maas_hesap_hareket",
            "nakliye_firma",
            "nakliye_arac",
            "nakliye_rota",
            "nakliye_is",
            "nakliye_islem",
        }
        cur = self.app.db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing = {row[0] for row in cur.fetchall()}
        missing = sorted(expected - existing)
        if missing:
            return False, f"Eksik tablolar: {', '.join(missing)}"
        return True, f"Toplam tablo: {len(existing)}"

    def _check_integrity(self) -> Tuple[bool, str]:
        checks = []
        for name, conn in (("users_db", self.app.usersdb.conn), ("company_db", self.app.db.conn)):
            row = conn.execute("PRAGMA integrity_check").fetchone()
            result = str(row[0]) if row else "unknown"
            checks.append(f"{name}: {result}")
        if any("ok" != c.split(": ", 1)[1] for c in checks):
            return False, " / ".join(checks)
        return True, " / ".join(checks)

    def _check_foreign_keys(self) -> Tuple[bool, str]:
        u_fk = self.app.usersdb.conn.execute("PRAGMA foreign_keys").fetchone()
        c_fk = self.app.db.conn.execute("PRAGMA foreign_keys").fetchone()
        u_val = int(u_fk[0]) if u_fk else 0
        c_val = int(c_fk[0]) if c_fk else 0
        if u_val != 1 or c_val != 1:
            return False, f"users_db={u_val}, company_db={c_val}"
        return True, f"users_db={u_val}, company_db={c_val}"

    def _check_settings(self) -> Tuple[bool, str]:
        currencies = self.app.db.list_currencies()
        payments = self.app.db.list_payments()
        categories = self.app.db.list_categories()
        stock_units = self.app.db.list_stock_units()
        stock_categories = self.app.db.list_stock_categories()

        if not currencies or not payments or not categories:
            return False, "Varsayılan listeler boş"
        detail = (
            f"Para birimi: {len(currencies)}, Ödeme: {len(payments)}, "
            f"Kategori: {len(categories)}, Stok birim: {len(stock_units)}, "
            f"Stok kategori: {len(stock_categories)}"
        )
        return True, detail

    def _check_repo_calls(self) -> Tuple[bool, str]:
        today = date.today().isoformat()
        self.app.db.cari_list(only_active=True)
        self.app.db.cari_hareket_list()
        self.app.db.kasa_list()
        self.app.db.kasa_toplam()
        self.app.db.kasa_aylik_ozet(limit=1)
        self.app.db.kasa_gunluk(today, today)
        self.app.db.kasa_kategori_ozet(today, today, tip="Gider")
        self.app.db.banka.list(limit=5)
        self.app.db.fatura_list()
        self.app.db.search.global_search("test", limit=5)
        return True, "Kritik repo çağrıları çalıştı"

    def _check_table_counts(self) -> Tuple[bool, str]:
        tables = [
            "cariler",
            "cari_hareket",
            "kasa_hareket",
            "banka_hareket",
            "fatura",
            "stok_urun",
            "stok_hareket",
        ]
        counts = []
        for tname in tables:
            row = self.app.db.conn.execute(f"SELECT COUNT(*) FROM {tname}").fetchone()
            count = int(row[0]) if row else 0
            counts.append(f"{tname}:{count}")
        return True, ", ".join(counts)

    def _check_optional_dependencies(self) -> Tuple[bool, str]:
        parts = [
            f"openpyxl: {'var' if HAS_OPENPYXL else 'yok'}",
            f"reportlab: {'var' if HAS_REPORTLAB else 'yok'}",
            f"tksheet: {'var' if HAS_TKSHEET else 'yok'}",
        ]
        return True, ", ".join(parts)


def build(master, app: "App") -> ttk.Frame:
    return DiagnosticsFrame(master, app)
