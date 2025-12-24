# -*- coding: utf-8 -*-
"""Banka Makro Analiz Penceresi.

Bu pencere, toblo/tablo (Treeview) üzerinden alınan banka hareketlerini
Excel'deki "Detaylı Grup Analizi" makrosuna benzer şekilde raporlar.

Veri kaynağı olarak DB'ye tekrar gitmez; kendisine verilen satır listesiyle
çalışır. Böylece tablo üzerinde henüz kaydedilmemiş (dirty) değişiklikler de
analize yansır.
"""

from __future__ import annotations

from typing import Dict, List, Sequence

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from ...config import APP_TITLE, HAS_OPENPYXL
from ...utils import fmt_amount, center_window
from ...core.banka_macros import SummaryRow, compute_bank_analysis


class BankaAnalizWindow(tk.Toplevel):
    def __init__(self, app: "App", rows: Sequence[Dict[str, object]], *, title_suffix: str = ""):
        super().__init__(app.root)
        self.app = app
        self.rows = list(rows or [])

        self.title(f"{APP_TITLE} - Banka Analiz{(' - ' + title_suffix) if title_suffix else ''}")
        self.geometry("1180x760")

        self.var_group_field = tk.StringVar(value="etiket")
        self.var_type_field = tk.StringVar(value="banka")

        self._build()
        self.refresh()
        center_window(self, self.app.root)

    # -----------------
    # UI
    # -----------------
    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=10, pady=(10, 6))

        ttk.Label(top, text="Grup alanı:").pack(side=tk.LEFT)
        self.cmb_group = ttk.Combobox(
            top,
            textvariable=self.var_group_field,
            values=["etiket", "banka", "hesap", "belge", "referans", "para"],
            width=14,
            state="readonly",
        )
        self.cmb_group.pack(side=tk.LEFT, padx=6)

        ttk.Label(top, text="Tip alanı:").pack(side=tk.LEFT, padx=(12, 0))
        self.cmb_type = ttk.Combobox(
            top,
            textvariable=self.var_type_field,
            values=["banka", "hesap", "etiket", "belge", "referans", "para"],
            width=14,
            state="readonly",
        )
        self.cmb_type.pack(side=tk.LEFT, padx=6)

        ttk.Button(top, text="Yenile", command=self.refresh).pack(side=tk.LEFT, padx=8)
        ttk.Button(top, text="📤 Excel'e Aktar", command=self.export_excel).pack(side=tk.LEFT)

        self.lbl_info = ttk.Label(top, text="")
        self.lbl_info.pack(side=tk.RIGHT)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.tab_groups = ttk.Frame(self.nb)
        self.tab_types = ttk.Frame(self.nb)
        self.tab_months = ttk.Frame(self.nb)
        self.tab_days = ttk.Frame(self.nb)
        self.tab_group_days = ttk.Frame(self.nb)

        self.nb.add(self.tab_groups, text="Gruplar Özeti")
        self.nb.add(self.tab_types, text="İşlem Tipi Analizi")
        self.nb.add(self.tab_months, text="Aylık Analiz")
        self.nb.add(self.tab_days, text="Günlük Analiz")
        self.nb.add(self.tab_group_days, text="Grup Günlük Analiz")

        self.tree_groups = self._make_tree(
            self.tab_groups,
            cols=("grup", "pos", "neg", "net", "avg", "max_pos", "min_neg", "count"),
            widths={"grup": 320, "count": 80},
        )
        self.tree_types = self._make_tree(
            self.tab_types,
            cols=("tip", "pos", "neg", "net", "count"),
            widths={"tip": 320, "count": 80},
        )
        self.tree_months = self._make_tree(
            self.tab_months,
            cols=("ay", "pos", "neg", "net", "count"),
            widths={"ay": 90, "count": 80},
        )
        self.tree_days = self._make_tree(
            self.tab_days,
            cols=("gun", "pos", "neg", "net", "count"),
            widths={"gun": 110, "count": 80},
        )
        self.tree_group_days = self._make_tree(
            self.tab_group_days,
            cols=("grup", "gun", "pos", "neg", "net", "count"),
            widths={"grup": 300, "gun": 110, "count": 80},
        )

    def _make_tree(self, parent: ttk.Frame, *, cols, widths=None) -> ttk.Treeview:
        widths = widths or {}
        box = ttk.Frame(parent)
        box.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        tree = ttk.Treeview(box, columns=cols, show="headings", selectmode="browse")
        vsb = ttk.Scrollbar(box, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(box, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        box.columnconfigure(0, weight=1)
        box.rowconfigure(0, weight=1)

        for c in cols:
            tree.heading(c, text=str(c).upper())
            w = int(widths.get(c, 140))
            anchor = "e" if c in ("pos", "neg", "net", "avg", "max_pos", "min_neg") else "w"
            if c in ("count",):
                anchor = "center"
            tree.column(c, width=w, anchor=anchor)
        return tree

    # -----------------
    # Data
    # -----------------
    def refresh(self):
        group_field = (self.var_group_field.get() or "etiket").strip()
        type_field = (self.var_type_field.get() or "banka").strip()
        data = compute_bank_analysis(self.rows, group_field=group_field, type_field=type_field)

        self._fill_groups(self.tree_groups, data.get("groups", []))
        self._fill_types(self.tree_types, data.get("types", []))
        self._fill_months(self.tree_months, data.get("months", []))
        self._fill_days(self.tree_days, data.get("days", []))
        self._fill_group_days(self.tree_group_days, data.get("group_days", []))

        self.lbl_info.config(text=f"Satır: {len(self.rows)}  •  Grup: {len(data.get('groups', []))}")

    def _clear(self, tree: ttk.Treeview):
        try:
            for iid in list(tree.get_children()):
                tree.delete(iid)
        except Exception:
            pass

    def _fill_groups(self, tree: ttk.Treeview, rows: List[SummaryRow]):
        self._clear(tree)
        for s in rows:
            tree.insert(
                "",
                tk.END,
                values=(
                    s.key,
                    fmt_amount(s.pos),
                    fmt_amount(s.neg),
                    fmt_amount(s.net),
                    fmt_amount(s.avg),
                    fmt_amount(s.max_pos),
                    fmt_amount(s.min_neg),
                    int(s.count),
                ),
            )

    def _fill_types(self, tree: ttk.Treeview, rows: List[SummaryRow]):
        self._clear(tree)
        for s in rows:
            tree.insert("", tk.END, values=(s.key, fmt_amount(s.pos), fmt_amount(s.neg), fmt_amount(s.net), int(s.count)))

    def _fill_months(self, tree: ttk.Treeview, rows: List[SummaryRow]):
        self._clear(tree)
        for s in rows:
            tree.insert("", tk.END, values=(s.key, fmt_amount(s.pos), fmt_amount(s.neg), fmt_amount(s.net), int(s.count)))

    def _fill_days(self, tree: ttk.Treeview, rows: List[SummaryRow]):
        self._clear(tree)
        for s in rows:
            tree.insert("", tk.END, values=(s.key, fmt_amount(s.pos), fmt_amount(s.neg), fmt_amount(s.net), int(s.count)))

    def _fill_group_days(self, tree: ttk.Treeview, rows: List[SummaryRow]):
        self._clear(tree)
        for s in rows:
            # key: group|yyyymmdd
            try:
                g, ymd = s.key.split("|", 1)
                gun = f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:8]}"
            except Exception:
                g, gun = s.key, ""
            tree.insert(
                "",
                tk.END,
                values=(g, gun, fmt_amount(s.pos), fmt_amount(s.neg), fmt_amount(s.net), int(s.count)),
            )

    # -----------------
    # Export
    # -----------------
    def export_excel(self):
        if not HAS_OPENPYXL:
            messagebox.showerror(APP_TITLE, "openpyxl kurulu değil. Kur: pip install openpyxl")
            return

        p = filedialog.asksaveasfilename(
            title="Excel Kaydet",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx"), ("All", "*.*")],
        )
        if not p:
            return

        try:
            import openpyxl
        except Exception:
            messagebox.showerror(APP_TITLE, "openpyxl import edilemedi. Kur: pip install openpyxl")
            return

        group_field = (self.var_group_field.get() or "etiket").strip()
        type_field = (self.var_type_field.get() or "banka").strip()
        data = compute_bank_analysis(self.rows, group_field=group_field, type_field=type_field)

        try:
            wb = openpyxl.Workbook()
            wb.remove(wb.active)

            def add_sheet(name: str, header: List[str], rows2: List[List[object]]):
                ws = wb.create_sheet(title=name)
                ws.append(header)
                for rr in rows2:
                    ws.append(rr)

            add_sheet(
                "Gruplar Ozeti",
                ["Grup", "Pozitif (+)", "Negatif (-)", "Net", "Ortalama", "Max (+)", "Min (-)", "Islem Sayisi"],
                [
                    [s.key, s.pos, s.neg, s.net, s.avg, s.max_pos, s.min_neg, int(s.count)]
                    for s in (data.get("groups") or [])
                ],
            )
            add_sheet(
                "Islem Tipi",
                ["Tip", "Pozitif (+)", "Negatif (-)", "Net", "Islem Sayisi"],
                [[s.key, s.pos, s.neg, s.net, int(s.count)] for s in (data.get("types") or [])],
            )
            add_sheet(
                "Aylik",
                ["Ay", "Pozitif (+)", "Negatif (-)", "Net", "Islem Sayisi"],
                [[s.key, s.pos, s.neg, s.net, int(s.count)] for s in (data.get("months") or [])],
            )
            add_sheet(
                "Gunluk",
                ["Gun", "Pozitif (+)", "Negatif (-)", "Net", "Islem Sayisi"],
                [[s.key, s.pos, s.neg, s.net, int(s.count)] for s in (data.get("days") or [])],
            )
            add_sheet(
                "GrupGunluk",
                ["Grup", "Gun", "Pozitif (+)", "Negatif (-)", "Net", "Islem Sayisi"],
                [
                    [
                        (s.key.split("|", 1)[0] if "|" in s.key else s.key),
                        (s.key.split("|", 1)[1] if "|" in s.key else ""),
                        s.pos,
                        s.neg,
                        s.net,
                        int(s.count),
                    ]
                    for s in (data.get("group_days") or [])
                ],
            )

            # Basit kolon genişlikleri
            for ws in wb.worksheets:
                for col in ws.columns:
                    max_len = 0
                    col_letter = col[0].column_letter
                    for cell in col:
                        try:
                            v = cell.value
                            if v is None:
                                continue
                            s = str(v)
                            if len(s) > max_len:
                                max_len = len(s)
                        except Exception:
                            pass
                    ws.column_dimensions[col_letter].width = min(55, max(10, max_len + 2))

            wb.save(p)
        except Exception as e:
            messagebox.showerror(APP_TITLE, str(e))
            return

        messagebox.showinfo(APP_TITLE, "Excel raporu oluşturuldu.")
