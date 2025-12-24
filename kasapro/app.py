# -*- coding: utf-8 -*-
"""KasaPro v3 - Uygulama giriş noktası (App)

Bu modül; kullanıcı girişi, şirket seçimi ve ana UI'ı başlatır.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
from datetime import datetime
from typing import Any, Optional, List, Dict, Tuple

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from .config import APP_TITLE, HAS_OPENPYXL, APP_BASE_DIR, DB_FILENAME
from .utils import _safe_slug
from .db.main_db import DB
from .db.users_db import UsersDB
from .services import Services
from .ui.style import apply_modern_style
from .ui.windows import LoginWindow, SettingsWindow, HelpWindow, ImportWizard
from .ui.frames import (
    KasaFrame,
    TanimlarHubFrame,
    RaporAraclarHubFrame,
    KullanicilarFrame,
    MessagesFrame,
)
from .ui.plugins.loader import discover_ui_plugins

class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.geometry("1320x780")
        self.root.minsize(1120, 650)

        # Tema/Fontları login penceresinde de uygula
        try:
            apply_modern_style(self.root)
        except Exception:
            pass

        # Giriş penceresi görünürken ana pencereyi gizle (bazı sistemlerde
        # login penceresi arka planda kalabiliyor).
        try:
            self.root.withdraw()
        except Exception:
            pass

        self.base_dir = APP_BASE_DIR
        self.usersdb = UsersDB(self.base_dir)

        self.user = self._login()
        if not self.user:
            try:
                self.usersdb.close()
            except Exception:
                pass
            self.root.destroy()
            raise SystemExit(0)

        # Aktif veri sahibi (kullanıcı) + aktif şirket (her şirketin kendi DB'si vardır)
        self.is_admin = (self.user["role"] == "admin")
        self.data_owner_username = str(self.user["username"])
        try:
            self.data_owner_user_id = int(self.user["id"])
        except Exception:
            self.data_owner_user_id = None

        # Şirket: son kullanılan (yoksa ilk)
        self.active_company = None
        try:
            self.active_company = self.usersdb.get_active_company_for_user(self.user)
        except Exception:
            self.active_company = None

        if self.active_company:
            db_path = self.usersdb.get_company_db_path(self.active_company)
            try:
                self.active_company_id = int(self.active_company["id"])
            except Exception:
                self.active_company_id = None
            try:
                self.active_company_name = str(self.active_company["name"])
            except Exception:
                self.active_company_name = ""
            try:
                if self.data_owner_user_id and self.active_company_id:
                    self.usersdb.set_last_company_id(int(self.data_owner_user_id), int(self.active_company_id))
            except Exception:
                pass
        else:
            # Güvenlik: çok eski kurulumlarda şirket kaydı yoksa user DB'si ile devam et
            db_path = self.usersdb.get_user_db_path(self.user)
            self.active_company_id = None
            self.active_company_name = "1. Şirket"

        self.db = DB(db_path)
        # Servis katmanı (UI -> services -> DB)
        self.services = Services.build(self.db, self.usersdb)
        try:
            cname = getattr(self, "active_company_name", "")
            if cname:
                self.db.log("Login", f"{self.user['username']} ({self.user['role']}) / {cname}")
            else:
                self.db.log("Login", f"{self.user['username']} ({self.user['role']})")
        except Exception:
            pass

        self.frames: Dict[str, ttk.Frame] = {}
        self._build_ui()
        self._start_message_polling()

        # Login başarılı -> ana pencereyi göster
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.after(80, self.root.lift)
        except Exception:
            pass

    def _login(self) -> Optional[sqlite3.Row]:
        # LoginWindow kullanıcı seçimi + şifre doğrulama yapar
        w = LoginWindow(self.root, self.usersdb)

        # ⚠️ Önemli:
        # Login penceresi kapanmadan user bilgisi set edilmez.
        # Bu yüzden burada beklemek gerekiyor; aksi halde uygulama hemen kapanır
        # ve "pencere hiç gelmiyor" gibi görünür.
        try:
            self.root.wait_window(w)
        except Exception:
            # Çok nadir: wait_window sorun çıkarırsa güvenli bir manuel döngü
            try:
                while True:
                    if not w.winfo_exists():
                        break
                    self.root.update()
            except Exception:
                pass

        return w.user


    def reload_settings(self):
        """Para birimi / ödeme / kategori gibi ayar listelerini tüm ekranlarda yeniler."""
        try:
            for fr in (getattr(self, "frames", {}) or {}).values():
                if fr is not None and hasattr(fr, "reload_settings"):
                    try:
                        fr.reload_settings()  # type: ignore
                    except Exception:
                        pass
        except Exception:
            pass

    
    def _update_company_label(self):
        try:
            if hasattr(self, "lbl_company"):
                name = getattr(self, "active_company_name", "") or ""
                self.lbl_company.config(text=f"Şirket: {name}")
        except Exception:
            pass

    def update_messages_badge(self, count: int):
        try:
            btn = (getattr(self, "nav_buttons", {}) or {}).get("mesajlar")
            if not btn:
                return
            base = getattr(self, "_messages_nav_base_text", "📨 Mesajlar")
            text = f"{base} ({count})" if count and count > 0 else base
            btn.config(text=text)
        except Exception:
            pass

    def show_toast(self, text: str, duration_ms: int = 3500):
        try:
            toast = tk.Toplevel(self.root)
            toast.overrideredirect(True)
            toast.configure(bg="#333333")
            label = tk.Label(toast, text=text, bg="#333333", fg="#ffffff", padx=12, pady=6)
            label.pack()
            toast.update_idletasks()
            x = self.root.winfo_x() + self.root.winfo_width() - toast.winfo_width() - 24
            y = self.root.winfo_y() + 60
            toast.geometry(f"+{x}+{y}")
            toast.after(duration_ms, toast.destroy)
        except Exception:
            pass

    def _start_message_polling(self):
        self._last_unread_count = None
        self._message_polling_active = True
        try:
            self._poll_messages()
        except Exception:
            pass

    def _refresh_message_badge(self):
        uid = self.get_active_user_id()
        if not uid:
            return
        try:
            count = self.db.message_unread_count(uid)
            self.update_messages_badge(count)
            self._last_unread_count = count
        except Exception:
            pass

    def _poll_messages(self):
        uid = self.get_active_user_id()
        if uid:
            try:
                count = self.db.message_unread_count(uid)
                self.update_messages_badge(count)
                if self._last_unread_count is not None and count > self._last_unread_count:
                    self.show_toast("Yeni mesajınız var.")
                self._last_unread_count = count
            except Exception:
                pass
        try:
            if getattr(self, "_message_polling_active", False):
                self.root.after(15000, self._poll_messages)
        except Exception:
            pass

    def get_active_user_row(self) -> Optional[sqlite3.Row]:
        """Admin için seçili veri sahibi, diğerleri için giriş yapan kullanıcı."""
        try:
            if self.is_admin and getattr(self, "data_owner_username", None):
                u = self.usersdb.get_user_by_username(str(self.data_owner_username))
                if u:
                    return u
        except Exception:
            pass
        return self.user

    def get_active_user_id(self) -> Optional[int]:
        u = self.get_active_user_row()
        try:
            return int(u["id"]) if u else None
        except Exception:
            return None

    def switch_company(self, company_id: int):
        """Aktif şirketi değiştirir (DB dosyası değişir)."""
        u = self.get_active_user_row()
        if not u:
            return
        c = self.usersdb.get_company_by_id(int(company_id))
        if (not c) or (int(c["user_id"]) != int(u["id"])):
            messagebox.showerror(APP_TITLE, "Şirket bulunamadı veya yetkiniz yok.")
            return

        new_path = self.usersdb.get_company_db_path(c)

        try:
            self.db.close()
        except Exception:
            pass
        self.db = DB(new_path)
        self.services = Services.build(self.db, self.usersdb)

        self.active_company = c
        try:
            self.active_company_id = int(c["id"])
        except Exception:
            self.active_company_id = None
        try:
            self.active_company_name = str(c["name"])
        except Exception:
            self.active_company_name = ""

        try:
            self.usersdb.set_last_company_id(int(u["id"]), int(self.active_company_id or 0))
        except Exception:
            pass

        self.reload_settings()

        try:
            self._update_company_label()
        except Exception:
            pass

        # Ekranları yenile (varsa)
        try:
            if "tanimlar" in self.frames and hasattr(self.frames["tanimlar"], "refresh"):
                self.frames["tanimlar"].refresh()  # type: ignore
        except Exception:
            pass
        try:
            if "kasa" in self.frames and hasattr(self.frames["kasa"], "refresh"):
                self.frames["kasa"].refresh()  # type: ignore
        except Exception:
            pass
        try:
            for key in ("cari_hareket_ekle", "cari_hareketler"):
                if key in self.frames:
                    fr = self.frames[key]
                    try:
                        if hasattr(fr, "reload_cari"):
                            fr.reload_cari()  # type: ignore
                    except Exception:
                        pass
                    try:
                        if hasattr(fr, "refresh"):
                            fr.refresh()  # type: ignore
                    except Exception:
                        pass
        except Exception:
            pass
        try:
            if "rapor_araclar" in self.frames and hasattr(self.frames["rapor_araclar"], "refresh"):
                self.frames["rapor_araclar"].refresh()  # type: ignore
        except Exception:
            pass
        try:
            if "sirketler" in self.frames and hasattr(self.frames["sirketler"], "refresh"):
                self.frames["sirketler"].refresh()  # type: ignore
        except Exception:
            pass

        try:
            self.db.log("Şirket", f"Aktif şirket: {self.active_company_name}")
        except Exception:
            pass

        try:
            self._last_unread_count = None
            self._refresh_message_badge()
        except Exception:
            pass

    def get_active_username(self) -> str:
        """Aktif veri sahibi kullanıcı adı (admin için seçili kullanıcı, diğerleri için kendi)."""
        try:
            if self.is_admin and getattr(self, "data_owner_username", None):
                return str(self.data_owner_username)
        except Exception:
            pass
        try:
            return str(self.user["username"])
        except Exception:
            return "user"

    def on_users_changed(self):
        """Kullanıcı listesi değiştiyse (admin combobox) güncelle."""
        if not getattr(self, "is_admin", False):
            return
        if not hasattr(self, "cmb_data_owner"):
            return
        try:
            vals = self.usersdb.list_usernames()
        except Exception:
            vals = [self.get_active_username()]
        try:
            self.cmb_data_owner["values"] = vals
        except Exception:
            pass
        if self.get_active_username() not in vals:
            try:
                self.data_owner_username = str(self.user["username"])
            except Exception:
                self.data_owner_username = "admin"
            try:
                self.cmb_data_owner.set(self.data_owner_username)
            except Exception:
                pass
            try:
                self.switch_data_owner(self.data_owner_username)
            except Exception:
                pass

    def _on_data_owner_change(self):
        if not self.is_admin:
            return
        try:
            new_u = str(self.cmb_data_owner.get()).strip()
        except Exception:
            return
        if not new_u or new_u == self.get_active_username():
            return
        self.switch_data_owner(new_u)

    def switch_data_owner(self, username: str):
        """Admin için aktif veri sahibini değiştir (başka kullanıcının DB'sini görüntüle/düzenle)."""
        if not self.is_admin:
            return
        try:
            urow = self.usersdb.get_user_by_username(username)
        except Exception:
            urow = None
        if not urow:
            messagebox.showerror(APP_TITLE, f"Kullanıcı bulunamadı: {username}")
            return

        # Aktif veri sahibi değişince aktif şirketi de o kullanıcıya göre seç
        try:
            self.data_owner_user_id = int(urow["id"])
        except Exception:
            self.data_owner_user_id = None

        crow = None
        try:
            crow = self.usersdb.get_active_company_for_user(urow)
        except Exception:
            crow = None

        if crow:
            new_path = self.usersdb.get_company_db_path(crow)
            self.active_company = crow
            try:
                self.active_company_id = int(crow["id"])
            except Exception:
                self.active_company_id = None
            try:
                self.active_company_name = str(crow["name"])
            except Exception:
                self.active_company_name = ""
            try:
                if self.data_owner_user_id and self.active_company_id:
                    self.usersdb.set_last_company_id(int(self.data_owner_user_id), int(self.active_company_id))
            except Exception:
                pass

        try:
            self._last_unread_count = None
            self._refresh_message_badge()
        except Exception:
            pass
        else:
            # güvenlik
            new_path = self.usersdb.get_user_db_path(urow)
            self.active_company = None
            self.active_company_id = None
            self.active_company_name = "1. Şirket"

        try:
            self.db.close()
        except Exception:
            pass
        self.db = DB(new_path)
        self.services = Services.build(self.db, self.usersdb)
        self.data_owner_username = str(username)

        self.reload_settings()
        try:
            self._update_company_label()
        except Exception:
            pass
        try:
            if "sirketler" in self.frames and hasattr(self.frames["sirketler"], "refresh"):
                self.frames["sirketler"].refresh()  # type: ignore
        except Exception:
            pass

        # Ekranları yenile (varsa)
        try:
            if "tanimlar" in self.frames and hasattr(self.frames["tanimlar"], "refresh"):
                self.frames["tanimlar"].refresh()  # type: ignore
        except Exception:
            pass
        try:
            if "kasa" in self.frames and hasattr(self.frames["kasa"], "refresh"):
                self.frames["kasa"].refresh()  # type: ignore
        except Exception:
            pass
        try:
            for key in ("cari_hareket_ekle", "cari_hareketler"):
                if key in self.frames:
                    fr = self.frames[key]
                    try:
                        if hasattr(fr, "reload_cari"):
                            fr.reload_cari()  # type: ignore
                    except Exception:
                        pass
                    try:
                        if hasattr(fr, "refresh"):
                            fr.refresh()  # type: ignore
                    except Exception:
                        pass
        except Exception:
            pass
        try:
            if "rapor_araclar" in self.frames and hasattr(self.frames["rapor_araclar"], "refresh"):
                self.frames["rapor_araclar"].refresh()  # type: ignore
        except Exception:
            pass

    def _build_ui(self):
        # Modern tema + okunabilir fontlar
        try:
            self._ui_colors = apply_modern_style(self.root)
        except Exception:
            self._ui_colors = {}

        container = ttk.Frame(self.root, style="TFrame")
        container.pack(fill=tk.BOTH, expand=True)

        # Sol menü
        nav = ttk.Frame(container, style="Sidebar.TFrame", width=270)
        nav.pack(side=tk.LEFT, fill=tk.Y)
        try:
            nav.pack_propagate(False)
        except Exception:
            pass

        # Sağ içerik
        content = ttk.Frame(container, style="TFrame")
        content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Üst bar (sayfa başlığı + hızlı aksiyon)
        topbar = ttk.Frame(content, style="Topbar.TFrame")
        topbar.pack(fill=tk.X, padx=12, pady=(12, 8))

        self.lbl_page_title = ttk.Label(topbar, text="Kasa", style="TopTitle.TLabel")
        self.lbl_page_title.pack(side=tk.LEFT, padx=(10, 10), pady=8)

        self.lbl_page_sub = ttk.Label(topbar, text="", style="TopSub.TLabel")
        self.lbl_page_sub.pack(side=tk.LEFT, pady=10)

        # Hızlı butonlar
        ttk.Button(topbar, text="❓", width=3, command=self.open_help).pack(side=tk.RIGHT, padx=(6, 10), pady=8)
        ttk.Button(topbar, text="⚙️", width=3, command=self.open_settings).pack(side=tk.RIGHT, padx=6, pady=8)

        # İçerik gövdesi (ekranlar buraya gelecek)
        body = ttk.Frame(content, style="TFrame")
        body.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        # Status bar
        self.status_var = tk.StringVar(value="F1: Yardım  •  Ctrl+F: Global Arama  •  Çift tık: Düzenle")
        self.status = ttk.Label(content, textvariable=self.status_var, style="Status.TLabel")
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

        # Sol menü üst bilgi
        hdr = ttk.Frame(nav, style="Sidebar.TFrame")
        hdr.pack(fill=tk.X, padx=14, pady=(14, 10))

        ttk.Label(hdr, text="KasaPro", style="SidebarTitle.TLabel").pack(anchor="w")
        ttk.Label(hdr, text=f"Kullanıcı: {self.user['username']} ({self.user['role']})", style="SidebarSub.TLabel").pack(anchor="w", pady=(2, 0))
        self.lbl_company = ttk.Label(hdr, text=f"Şirket: {getattr(self,'active_company_name','')}", style="SidebarSub.TLabel")
        self.lbl_company.pack(anchor="w")

        if self.is_admin:
            try:
                vals = self.usersdb.list_usernames()
            except Exception:
                vals = [str(self.user["username"])]

            rowu = ttk.Frame(hdr, style="Sidebar.TFrame")
            rowu.pack(fill=tk.X, pady=(8, 0))

            ttk.Label(rowu, text="Veri Sahibi:", style="SidebarSub.TLabel").pack(side=tk.LEFT)
            self.cmb_data_owner = ttk.Combobox(rowu, state="readonly", width=16, values=vals)
            self.cmb_data_owner.pack(side=tk.LEFT, padx=(8, 0))

            try:
                self.cmb_data_owner.set(self.data_owner_username)
            except Exception:
                pass
            try:
                self.cmb_data_owner.bind("<<ComboboxSelected>>", lambda _e: self._on_data_owner_change())
            except Exception:
                pass

        ttk.Separator(nav, orient="horizontal").pack(fill=tk.X, padx=12, pady=(6, 10))

        # Menü butonları
        self.nav_buttons: Dict[str, ttk.Button] = {}

        menu = ttk.Frame(nav, style="Sidebar.TFrame")
        menu.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        def nav_btn(text, key):
            b = ttk.Button(menu, text=text, style="Sidebar.TButton", command=lambda k=key: self.show(k))
            b.pack(fill=tk.X, padx=4, pady=2)
            self.nav_buttons[key] = b
            return b

        def nav_section(title: str):
            """Sol menüde bölüm başlığı (Tanımlar/İşlemler/Rapor)."""
            try:
                ttk.Label(menu, text=title, style="SidebarSection.TLabel").pack(fill=tk.X, padx=4, pady=(10, 2))
                ttk.Separator(menu, orient="horizontal").pack(fill=tk.X, padx=10, pady=(0, 6))
            except Exception:
                ttk.Label(menu, text=title, style="SidebarSub.TLabel").pack(fill=tk.X, padx=8, pady=(10, 4))

        # UI eklentileri (ör: cari hareketler + cari hareket ekle)
        # Not: Maaş Eklentileri artık Maaş Takibi içine taşındığı için menü/ekran olarak yüklenmez.
        self.ui_plugins = [p for p in discover_ui_plugins() if p.key != "maas_eklentileri"]
        self._plugin_titles = {p.key: p.page_title for p in self.ui_plugins}

        # "Çalışanlar" gibi bazı ekranları, var olan bir plugin ekranının sekmesine yönlendirebiliriz.
        if not hasattr(self, "_nav_routes") or not isinstance(getattr(self, "_nav_routes", None), dict):
            self._nav_routes = {}
        # Tanımlar ekranı içinde alt sekme yönlendirmeleri
        self._nav_routes["cariler"] = {"target": "tanimlar", "after": "hub_tab", "tab": "cariler"}
        self._nav_routes["calisanlar"] = {"target": "tanimlar", "after": "hub_tab", "tab": "calisanlar"}
        self._nav_routes["maas_meslekler"] = {"target": "tanimlar", "after": "hub_tab", "tab": "meslekler"}

        # Rapor & Araçlar hub iç sekme yönlendirmeleri (eski kısayollar uyumlu kalsın)
        self._nav_routes["raporlar"] = {"target": "rapor_araclar", "after": "hub_tab", "tab": "raporlar"}
        self._nav_routes["search"] = {"target": "rapor_araclar", "after": "hub_tab", "tab": "search"}
        self._nav_routes["loglar"] = {"target": "rapor_araclar", "after": "hub_tab", "tab": "loglar"}

        # Eski kısayol uyumluluğu: Maaş Eklentileri -> Maaş Takibi / Bankada Maaş Bul
        self._nav_routes["maas_eklentileri"] = {"target": "maas_takibi", "after": "plugin_tab", "tab": "scan"}

        # ----------------
        # Menü bölümleri
        # ----------------
        nav_section("📚 TANIMLAR")
        nav_btn("📚 Tanımlar", "tanimlar")

        # Şirket yönetimi sol menüden kaldırıldı; ⚙️ Ayarlar > Şirketler sekmesinde.

        nav_section("💳 İŞLEMLER")
        nav_btn("🏦 Kasa", "kasa")
        self._messages_nav_base_text = "📨 Mesajlar"
        nav_btn(self._messages_nav_base_text, "mesajlar")
        for p in self.ui_plugins:
            # Meslekler Tanımlar altında gösteriliyor
            if p.key == "maas_meslekler":
                continue
            # Maaş Eklentileri artık Maaş Takibi içine taşındı
            if p.key == "maas_eklentileri":
                continue
            nav_btn(p.nav_text, p.key)

        nav_section("📈 RAPOR & ARAÇLAR")
        nav_btn("📈 Rapor & Araçlar", "rapor_araclar")

        # Kullanıcı yönetimi Ayarlar (⚙️) içine taşındı.
        # Sol menüde ayrı bir "Kullanıcılar" sayfası göstermiyoruz.

        # Alt aksiyonlar
        actions = ttk.Frame(nav, style="Sidebar.TFrame")
        actions.pack(fill=tk.X, padx=8, pady=(0, 12), side=tk.BOTTOM)

        ttk.Separator(actions, orient="horizontal").pack(fill=tk.X, padx=4, pady=(4, 8))

        self.btn_import_excel = ttk.Button(actions, text="📥 Excel İçe Aktar", command=self.import_excel)
        self.btn_import_excel.pack(fill=tk.X, padx=4, pady=2)

        self.btn_export_excel = ttk.Button(actions, text="📤 Excel Export", command=self.export_excel)
        self.btn_export_excel.pack(fill=tk.X, padx=4, pady=2)

        # openpyxl yoksa Excel import/export devre dışı
        if not HAS_OPENPYXL:
            try:
                self.btn_import_excel.config(state="disabled")
                self.btn_export_excel.config(state="disabled")
            except Exception:
                pass

        # DB yedek/geri yükle işlemleri artık ⚙️ Ayarlar > DB sekmelerine taşındı.

        ttk.Button(actions, text="🚪 Çıkış", command=self.on_close).pack(fill=tk.X, padx=4, pady=(8, 2))

        # Ekranlar
        self.frames["kasa"] = KasaFrame(body, self)
        self.frames["mesajlar"] = MessagesFrame(body, self)
        self.frames["tanimlar"] = TanimlarHubFrame(body, self)
        self.frames["rapor_araclar"] = RaporAraclarHubFrame(body, self)

        # Plugin ekranları
        for p in getattr(self, "ui_plugins", []) or []:
            try:
                self.frames[p.key] = p.build(body, self)
            except Exception:
                # hatalı eklenti uygulamayı düşürmesin
                pass

        if self.is_admin:
            self.frames["kullanicilar"] = KullanicilarFrame(body, self)

        # İlk yüklemeler
        try:
            if "tanimlar" in self.frames and hasattr(self.frames["tanimlar"], "refresh"):
                self.frames["tanimlar"].refresh()  # type: ignore
        except Exception:
            pass
        try:
            for key in ("cari_hareket_ekle", "cari_hareketler"):
                if key in self.frames and hasattr(self.frames[key], "reload_cari"):
                    self.frames[key].reload_cari()  # type: ignore
        except Exception:
            pass
        try:
            self.frames["kasa"].reload_cari_combo()  # type: ignore
            self.frames["kasa"].refresh()  # type: ignore
        except Exception:
            pass

        for f in self.frames.values():
            f.pack_forget()

        # Kısayollar
        try:
            self.root.bind("<F1>", lambda _e: self.open_help())
        except Exception:
            pass
        try:
            self.root.bind("<Control-f>", lambda _e: self.show("search"))
        except Exception:
            pass

        # Başlangıç ekranı
        self.show("kasa")

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _ui_on_show(self, key: str, active_nav_key: Optional[str] = None):
        """Ekran değişince sol menü + başlık gibi UI parçalarını günceller."""
        title_map = {
            "kasa": "Kasa",
            "tanimlar": "Tanımlar",
            "cariler": "Tanımlar",
            "rapor_araclar": "Rapor & Araçlar",
            "raporlar": "Raporlar",
            "search": "Global Arama",
            "loglar": "Log",
            "kullanicilar": "Kullanıcılar",
            "mesajlar": "Mesajlar",
        }

        # Plugin başlıkları
        try:
            title_map.update(getattr(self, "_plugin_titles", {}) or {})
        except Exception:
            pass

        # Aktif menü vurgusu
        active_key = active_nav_key or key
        btns = getattr(self, "nav_buttons", {}) or {}
        for k, b in btns.items():
            try:
                b.configure(style=("SidebarActive.TButton" if k == active_key else "Sidebar.TButton"))
            except Exception:
                pass

        # Üst başlık
        try:
            t = title_map.get(key, key)
            self.lbl_page_title.config(text=t)
        except Exception:
            pass

        # Alt bilgi (şirket + kullanıcı)
        try:
            cname = getattr(self, "active_company_name", "") or ""
            uname = self.get_active_username() if hasattr(self, "get_active_username") else (str(self.user["username"]) if self.user else "")
            sub = " • ".join([x for x in (cname, uname) if x])
            self.lbl_page_sub.config(text=sub)
        except Exception:
            pass


    def show(self, key: str):
        # Bazı menü tuşları, var olan bir ekranın belirli sekmesine yönlenebilir (örn: Çalışanlar -> Maaş Takibi/Çalışanlar sekmesi)
        route = None
        try:
            route = (getattr(self, "_nav_routes", {}) or {}).get(key)
        except Exception:
            route = None

        target_key = key
        if isinstance(route, dict):
            try:
                target_key = str(route.get("target") or key)
            except Exception:
                target_key = key

        for k, f in self.frames.items():
            if k == target_key:
                f.pack(fill=tk.BOTH, expand=True)
            else:
                f.pack_forget()

        # Route sonrası aksiyonlar
        if isinstance(route, dict):
            after = str(route.get("after") or "")

            # Eski kısayol: Çalışanlar -> Maaş Takibi/Çalışanlar
            if after == "employees":
                try:
                    fr = self.frames.get(target_key)
                    if fr is not None and hasattr(fr, "select_employees_tab"):
                        fr.select_employees_tab()  # type: ignore
                except Exception:
                    pass

            # Yeni: Tanımlar hub iç sekme yönlendirmesi
            if after == "hub_tab":
                try:
                    fr = self.frames.get(target_key)
                    tab = str(route.get("tab") or "")
                    if fr is not None and hasattr(fr, "select_tab"):
                        fr.select_tab(tab)  # type: ignore
                except Exception:
                    pass

            # Plugin iç sekme yönlendirmesi (örn: Maaş Takibi gibi Notebook kullanan pluginler)
            if after == "plugin_tab":
                try:
                    fr = self.frames.get(target_key)
                    tab = str(route.get("tab") or "")
                    if fr is not None and hasattr(fr, "select_tab"):
                        fr.select_tab(tab)  # type: ignore
                except Exception:
                    pass

        try:
            # Sol menüde tek tuş altında toplanan ekranlar için (örn: Rapor & Araçlar),
            # başlık key'e göre, menü vurgusu ise target_key'e göre olsun.
            self._ui_on_show(key, active_nav_key=(target_key if hasattr(self, 'nav_buttons') and target_key in getattr(self, 'nav_buttons', {}) else None))
        except Exception:
            pass

        if key in ("tanimlar", "cariler", "cari_hareket_ekle", "cari_hareketler", "rapor_araclar", "raporlar", "search", "loglar", "kasa", "mesajlar"):
            try:
                for k2 in ("cari_hareket_ekle", "cari_hareketler"):
                    if k2 in self.frames and hasattr(self.frames[k2], "reload_cari"):
                        self.frames[k2].reload_cari()  # type: ignore
            except Exception:
                pass
            try:
                self.frames["kasa"].reload_cari_combo()  # type: ignore
            except Exception:
                pass
            if key in ("rapor_araclar", "raporlar", "search", "loglar"):
                try:
                    if "rapor_araclar" in self.frames and hasattr(self.frames["rapor_araclar"], "refresh"):
                        self.frames["rapor_araclar"].refresh()  # type: ignore
                except Exception:
                    pass
            if key == "mesajlar":
                try:
                    if "mesajlar" in self.frames and hasattr(self.frames["mesajlar"], "refresh"):
                        self.frames["mesajlar"].refresh()  # type: ignore
                except Exception:
                    pass



        if key == "kullanicilar":
            try:
                self.frames["kullanicilar"].refresh()  # type: ignore
            except Exception:
                pass
    def open_settings(self):
        SettingsWindow(self)


    def open_help(self):
        HelpWindow(self)

    def backup_db(self):
        base = self.base_dir if hasattr(self, 'base_dir') else APP_BASE_DIR
        src = getattr(self.db, 'path', None) or os.path.join(base, DB_FILENAME)
        if not src or not os.path.exists(src):
            raise FileNotFoundError('DB bulunamadı.')
        uname = self.get_active_username() if hasattr(self, 'get_active_username') else (str(self.user['username']) if self.user else 'user')
        cname = _safe_slug(getattr(self, "active_company_name", "") or "sirket")
        dst = os.path.join(base, f"kasa_backup_{uname}_{cname}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        shutil.copy2(src, dst)
        try:
            self.db.log('Yedek', dst)
        except Exception:
            pass
        messagebox.showinfo(APP_TITLE, f"Yedek alındı:\n{dst}")

    def restore_db(self):
        p = filedialog.askopenfilename(title='DB Yedek Seç', filetypes=[('DB', '*.db'), ('All', '*.*')])
        if not p:
            return
        uname = self.get_active_username() if hasattr(self, 'get_active_username') else (str(self.user['username']) if self.user else 'user')
        if not messagebox.askyesno(APP_TITLE, f"Geri yükleme '{uname}' verisinin DB'sinin üzerine yazar. Devam?"):
            return
        dst = getattr(self.db, 'path', None)
        if not dst:
            messagebox.showerror(APP_TITLE, 'Hedef DB yolu bulunamadı.')
            return
        try:
            self.db.close()
        except Exception:
            pass
        try:
            shutil.copy2(p, dst)
        except Exception as e:
            messagebox.showerror(APP_TITLE, f'Geri yükleme başarısız: {e}')
            # DB'yi tekrar açmayı deneyelim
            try:
                self.db = DB(dst)
            except Exception:
                pass
            return
        self.db = DB(dst)
        try:
            self.db.log('Restore', os.path.basename(p))
        except Exception:
            pass
        messagebox.showinfo(APP_TITLE, 'Geri yüklendi. Uygulamayı yeniden başlatman önerilir.')

    def import_excel(self):
        p = filedialog.askopenfilename(title="Excel Seç", filetypes=[("Excel", "*.xlsx *.xlsm"), ("All", "*.*")])
        if not p:
            return
        w = ImportWizard(self, p)
        self.root.wait_window(w)
        if w.result_counts:
            try:
                if "tanimlar" in self.frames and hasattr(self.frames["tanimlar"], "refresh"):
                    self.frames["tanimlar"].refresh()  # type: ignore
            except Exception:
                pass
            try:
                self.frames["kasa"].refresh()  # type: ignore
            except Exception:
                pass
            try:
                if "cari_hareketler" in self.frames and hasattr(self.frames["cari_hareketler"], "refresh"):
                    self.frames["cari_hareketler"].refresh()  # type: ignore
            except Exception:
                pass
            try:
                if "banka_hareketleri" in self.frames and hasattr(self.frames["banka_hareketleri"], "refresh"):
                    self.frames["banka_hareketleri"].refresh()  # type: ignore
            except Exception:
                pass

    def export_excel(self):
        try:
            from openpyxl import Workbook
            from openpyxl.utils import get_column_letter
        except Exception:
            messagebox.showerror(APP_TITLE, "openpyxl kurulu değil. Kur: pip install openpyxl")
            return

        wb = Workbook()
        wb.remove(wb.active)

        def add_sheet(name: str, headers: List[str], rows: List[Tuple[Any, ...]]):
            ws = wb.create_sheet(title=name)
            ws.append(headers)
            for r in rows:
                ws.append(list(r))
            for i, h in enumerate(headers, start=1):
                ws.column_dimensions[get_column_letter(i)].width = min(45, max(12, len(str(h))+2))
            ws.freeze_panes = "A2"

        caris = self.db.cari_list()
        add_sheet("Cariler", ["id","ad","tur","telefon","notlar","acilis_bakiye","aktif"],
                  [(r["id"], r["ad"], r["tur"], r["telefon"], r["notlar"], r["acilis_bakiye"], r.get("aktif", 1) if hasattr(r, "get") else r["aktif"]) for r in caris])

        ch = self.db.cari_hareket_list()
        add_sheet("Cari_Hareket", ["id","tarih","cari","tip","tutar","para","aciklama","odeme","belge","etiket"],
                  [(r["id"], r["tarih"], r["cari_ad"], r["tip"], r["tutar"], r["para"], r["aciklama"], r["odeme"], r["belge"], r["etiket"]) for r in ch])

        kh = self.db.kasa_list()
        add_sheet("Kasa_Hareket", ["id","tarih","tip","tutar","para","odeme","kategori","cari","aciklama","belge","etiket"],
                  [(r["id"], r["tarih"], r["tip"], r["tutar"], r["para"], r["odeme"], r["kategori"], r["cari_ad"], r["aciklama"], r["belge"], r["etiket"]) for r in kh])

        # Banka
        try:
            bh = self.db.banka_list(limit=200000)
            add_sheet("Banka_Hareket", ["id","tarih","banka","hesap","tip","tutar","para","aciklama","referans","belge","etiket","bakiye"],
                      [(r["id"], r["tarih"], r["banka"], r["hesap"], r["tip"], r["tutar"], r["para"], r["aciklama"], r["referans"], r["belge"], r["etiket"], r["bakiye"]) for r in bh])
        except Exception:
            pass

        # Stok
        try:
            urunler = self.db.stok_urun_list()
            add_sheet(
                "Stok_Urun",
                ["id","kod","ad","kategori","birim","min_stok","kritik_stok","max_stok","raf","tedarikci_id","barkod","aktif","aciklama"],
                [
                    (
                        r["id"],
                        r["kod"],
                        r["ad"],
                        r["kategori"],
                        r["birim"],
                        r["min_stok"],
                        r["kritik_stok"],
                        r["max_stok"],
                        r["raf"],
                        r["tedarikci_id"],
                        r["barkod"],
                        r["aktif"],
                        r["aciklama"],
                    )
                    for r in urunler
                ],
            )
            loks = self.db.stok_lokasyon_list(only_active=False)
            add_sheet("Stok_Lokasyon", ["id","ad","aciklama","aktif"],
                      [(r["id"], r["ad"], r["aciklama"], r["aktif"]) for r in loks])
            partiler = self.db.stok_parti_list()
            add_sheet("Stok_Parti", ["id","urun_id","parti_no","skt","uretim_tarih","aciklama"],
                      [(r["id"], r["urun_id"], r["parti_no"], r["skt"], r["uretim_tarih"], r["aciklama"]) for r in partiler])
            hareketler = self.db.stok_hareket_list(limit=200000)
            add_sheet(
                "Stok_Hareket",
                ["id","tarih","urun_id","tip","miktar","birim","kaynak_lokasyon_id","hedef_lokasyon_id","parti_id","referans_tipi","referans_id","maliyet","aciklama"],
                [
                    (
                        r["id"],
                        r["tarih"],
                        r["urun_id"],
                        r["tip"],
                        r["miktar"],
                        r["birim"],
                        r["kaynak_lokasyon_id"],
                        r["hedef_lokasyon_id"],
                        r["parti_id"],
                        r["referans_tipi"],
                        r["referans_id"],
                        r["maliyet"],
                        r["aciklama"],
                    )
                    for r in hareketler
                ],
            )
        except Exception:
            pass

        ws = wb.create_sheet("Ozet")
        totals = self.db.kasa_toplam()
        ws["A1"] = "Kasa Özet"
        ws["A3"] = "Gelir"
        ws["B3"] = totals["gelir"]
        ws["A4"] = "Gider"
        ws["B4"] = totals["gider"]
        ws["A5"] = "Net"
        ws["B5"] = totals["net"]

        base = APP_BASE_DIR
        out = os.path.join(base, f"kasa_pro_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        wb.save(out)
        self.db.log("Excel Export", out)
        messagebox.showinfo(APP_TITLE, f"Excel export:\n{out}")

    def on_close(self):
        try:
            self.db.log("Uygulama", "Kapandı")
        except Exception:
            pass
        try:
            self.db.close()
        except Exception:
            pass
        try:
            self.usersdb.close()
        except Exception:
            pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    try:
        App().run()
    except SystemExit:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            messagebox.showerror(APP_TITLE, f"Hata:\n{e}")
        except Exception:
            pass

if __name__ == "__main__":
    main()
