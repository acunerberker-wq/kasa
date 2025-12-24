# -*- coding: utf-8 -*-
"""UI Plugin: Sistem Testleri / Sağlık Kontrolü.

Bu ekran; uygulamanın temel altyapısını ve kritik fonksiyon çağrılarını
çalıştırarak hızlı bir sağlık kontrolü sağlar.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import os
import time
from typing import Callable, List, Optional, Tuple, TYPE_CHECKING

import tkinter as tk
from tkinter import ttk, messagebox

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

if TYPE_CHECKING:
    from ...app import App

PLUGIN_META = {
    "key": "diagnostics",
    "nav_text": "🧪 Sistem Testleri",
    "page_title": "Sistem Testleri",
    "order": 95,
}


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


class DiagnosticsFrame(ttk.Frame):
    def __init__(self, master, app: "App"):
        super().__init__(master)
        self.app = app
        self.status_var = tk.StringVar(value="Hazır")
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
                "Bu ekran temel veritabanı bağlantısı, dizin erişimi ve kritik repo çağrılarını kontrol eder."
            ),
            foreground="#555",
        )
        note.pack(fill=tk.X, padx=10)

        actions = ttk.Frame(self)
        actions.pack(fill=tk.X, padx=10, pady=6)
        ttk.Button(actions, text="Testleri Çalıştır", command=self.run_checks).pack(side=tk.LEFT)
        ttk.Button(actions, text="Temizle", command=self.clear_results).pack(side=tk.LEFT, padx=6)
        ttk.Button(actions, text="Raporu Kopyala", command=self.copy_report).pack(side=tk.LEFT)

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
        self.clear_results()
        self.status_var.set("Testler çalıştırılıyor...")
        self.update_idletasks()

        start = time.time()
        results: List[CheckResult] = []
        for name, fn in self._checks():
            results.append(self._run_check(name, fn))

        total = len(results)
        ok_count = sum(1 for r in results if r.ok)
        fail_count = total - ok_count
        elapsed = time.time() - start

        for res in results:
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
            ok = False
            detail = f"Beklenmeyen hata: {exc}"
        return CheckResult(name=name, ok=ok, detail=detail)

    def _checks(self) -> List[Tuple[str, Callable[[], Tuple[bool, str]]]]:
        return [
            ("Uygulama dizinleri", self._check_directories),
            ("Log dizini yazılabilir mi", self._check_log_dir),
            ("Kullanıcı DB bağlantısı", self._check_users_db),
            ("Şirket DB bağlantısı", self._check_company_db),
            ("Zorunlu tablolar", self._check_required_tables),
            ("Varsayılan ayarlar", self._check_settings),
            ("Repo okuma fonksiyonları", self._check_repo_calls),
            ("Opsiyonel bağımlılıklar", self._check_optional_dependencies),
        ]

    def _check_directories(self) -> Tuple[bool, str]:
        base_dir = APP_BASE_DIR
        data_dir = os.path.join(base_dir, DATA_DIRNAME)
        shared_dir = os.path.join(base_dir, SHARED_STORAGE_DIRNAME)
        missing = [p for p in (base_dir, data_dir, shared_dir) if not os.path.isdir(p)]
        if missing:
            return False, f"Eksik dizinler: {', '.join(missing)}"
        return True, f"Base: {base_dir}"  # temel dizinleri döndür

    def _check_log_dir(self) -> Tuple[bool, str]:
        log_dir = os.path.join(APP_BASE_DIR, LOG_DIRNAME)
        if not os.path.isdir(log_dir):
            return False, f"Log dizini bulunamadı: {log_dir}"
        writable = os.access(log_dir, os.W_OK)
        if not writable:
            return False, f"Log dizinine yazılamıyor: {log_dir}"
        return True, f"Log dizini hazır: {log_dir}"

    def _check_users_db(self) -> Tuple[bool, str]:
        self.app.usersdb.conn.execute("SELECT 1")
        users = self.app.usersdb.list_users()
        return True, f"Kullanıcı sayısı: {len(users)}"

    def _check_company_db(self) -> Tuple[bool, str]:
        self.app.db.conn.execute("SELECT 1")
        return True, f"DB: {self.app.db.path}"

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

    def _check_optional_dependencies(self) -> Tuple[bool, str]:
        parts = [
            f"openpyxl: {'var' if HAS_OPENPYXL else 'yok'}",
            f"reportlab: {'var' if HAS_REPORTLAB else 'yok'}",
            f"tksheet: {'var' if HAS_TKSHEET else 'yok'}",
        ]
        return True, ", ".join(parts)


def build(master, app: "App") -> ttk.Frame:
    return DiagnosticsFrame(master, app)
