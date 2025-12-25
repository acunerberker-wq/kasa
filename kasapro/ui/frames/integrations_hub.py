# -*- coding: utf-8 -*-
from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class IntegrationsHubFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tab_notifications = ttk.Frame(self.nb)
        self.tab_external = ttk.Frame(self.nb)
        self.tab_bank = ttk.Frame(self.nb)
        self.tab_api = ttk.Frame(self.nb)

        self.nb.add(self.tab_notifications, text="📣 Bildirimler")
        self.nb.add(self.tab_external, text="🔁 Dış Sistem")
        self.nb.add(self.tab_bank, text="🏦 Banka")
        self.nb.add(self.tab_api, text="🔌 API/Webhook")

        self._build_notifications()
        self._build_external()
        self._build_bank()
        self._build_api()

    def _build_section(self, parent, title: str, items: list[str]):
        frame = ttk.LabelFrame(parent, text=title)
        frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=10)
        for item in items:
            ttk.Label(frame, text=f"• {item}").pack(anchor="w", padx=10, pady=2)

    def _build_notifications(self):
        self._build_section(
            self.tab_notifications,
            "Bildirim Kanalları",
            [
                "Email/SMS/WhatsApp şablonları",
                "Event → Channel → Recipient kuralları",
                "KVKK opt-in ve rate limit",
                "Uygulama içi bildirimler ve delivery log",
            ],
        )

    def _build_external(self):
        self._build_section(
            self.tab_external,
            "Dış Sistem Aktarımı",
            [
                "Generic CSV Connector (Cari/Fatura/Tahsilat)",
                "API Connector altyapısı",
                "Staging ve import/export job takibi",
                "Mapping ve entegrasyon ayarları",
            ],
        )

    def _build_bank(self):
        self._build_section(
            self.tab_bank,
            "Banka İçe Aktarım",
            [
                "CSV/Excel format parser",
                "Mükerrer engelleme (unique hash)",
                "Otomatik + manuel mutabakat",
                "POS komisyonu / masraf işaretleme",
            ],
        )

    def _build_api(self):
        self._build_section(
            self.tab_api,
            "API / Webhook",
            [
                "API token + scope kontrolü",
                "Webhook abonelikleri ve HMAC imza",
                "Idempotency key desteği",
                "Rate limit ve audit log",
            ],
        )

    def select_tab(self, tab_key: str):
        mapping = {
            "bildirimler": self.tab_notifications,
            "dis_sistem": self.tab_external,
            "banka": self.tab_bank,
            "api": self.tab_api,
        }
        target = mapping.get((tab_key or "").lower())
        if target is None:
            target = self.tab_notifications
        try:
            self.nb.select(target)
        except Exception:
            pass

    def refresh(self):
        return
