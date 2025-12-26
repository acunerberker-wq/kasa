# -*- coding: utf-8 -*-
"""UI Plugin: Banka Hareketleri.

İstekler:
- Banka hareketlerini uygulama içinde inceleyebilme
- Excel ile içe aktarma (mapping/eşleştirme destekli)
- İçe aktarımlar özet görünüm (tek satır) + çift tık/"Aç" ile detay tablosuna geçiş
- İçe aktarılan veriyi Excel benzeri çalışma alanında açıp düzenleyebilme

Notlar:
- Banka hareketleri DB'de `banka_hareket` tablosunda tutulur.
- `import_grup` alanı, her içe aktarmayı gruplamak için kullanılır.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional, List, TYPE_CHECKING

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from ...config import APP_TITLE, HAS_OPENPYXL
from ...utils import fmt_tr_date, fmt_amount
from ..base import BaseView
from ..widgets import LabeledEntry, LabeledCombo
from ..windows import ImportWizard, BankaWorkspaceWindow

if TYPE_CHECKING:
    from ...app import App

PLUGIN_META = {
    "key": "banka_hareketleri",
    "nav_text": "🏦 Banka",
    "page_title": "Banka Hareketleri",
    "order": 22,
}


class BankaHareketleriFrame(BaseView):
    def __init__(self, master, app: "App"):
        self.app = app
        super().__init__(master, app)
        self.build_ui()

    def build_ui(self) -> None:
        self._build()

    # -----------------
    # UI
    # -----------------
    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=10, pady=(10, 6))

        ttk.Button(top, text="📥 Excel İçe Aktar", command=self.import_excel).pack(side=tk.LEFT)
        ttk.Button(top, text="🧾 Tabloyu Aç (Çalış)", command=self.open_selected_import_as_table).pack(side=tk.LEFT, padx=8)
        ttk.Button(top, text="📦 Son Import", command=self.open_last_import).pack(side=tk.LEFT, padx=8)
        ttk.Button(top, text="Yenile", command=self.refresh).pack(side=tk.LEFT, padx=8)

        self.lbl_sum = ttk.Label(top, text="")
        self.lbl_sum.pack(side=tk.LEFT, padx=(12, 0))

        # Filtre
        box = ttk.LabelFrame(self, text="Filtre")
        box.pack(fill=tk.X, padx=10, pady=(0, 8))

        row = ttk.Frame(box)
        row.pack(fill=tk.X, pady=6)

        self.f_q = LabeledEntry(row, "Ara:", 22)
        self.f_q.pack(side=tk.LEFT, padx=6)

        self.f_tip = LabeledCombo(row, "Tip:", ["(Tümü)", "Giriş", "Çıkış"], 10)
        self.f_tip.pack(side=tk.LEFT, padx=6)
        self.f_tip.set("(Tümü)")

        self.f_banka = LabeledCombo(row, "Banka:", ["(Tümü)"], 14)
        self.f_banka.pack(side=tk.LEFT, padx=6)
        self.f_banka.set("(Tümü)")
        try:
            self.f_banka.cmb.bind("<<ComboboxSelected>>", lambda _e: self._reload_hesap_combo())
        except Exception:
            pass

        self.f_hesap = LabeledCombo(row, "Hesap:", ["(Tümü)"], 18)
        self.f_hesap.pack(side=tk.LEFT, padx=6)
        self.f_hesap.set("(Tümü)")

        self.f_import = LabeledCombo(row, "Import:", ["(Tümü)"], 26)
        self.f_import.pack(side=tk.LEFT, padx=6)
        self.f_import.set("(Tümü)")

        self.f_from = LabeledEntry(row, "Başlangıç:", 12)
        self.f_from.pack(side=tk.LEFT, padx=6)
        self.f_to = LabeledEntry(row, "Bitiş:", 12)
        self.f_to.pack(side=tk.LEFT, padx=6)

        ttk.Button(row, text="Bu Ay", command=self.this_month).pack(side=tk.LEFT, padx=6)
        ttk.Button(row, text="Son 30 gün", command=self.last30).pack(side=tk.LEFT, padx=6)

        # Sekmeler
        mid = ttk.LabelFrame(self, text="Banka")
        mid.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.nb = ttk.Notebook(mid)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # Detay sekmesi
        self.tab_detail = ttk.Frame(self.nb)
        self.nb.add(self.tab_detail, text="Detay (Hareketler)")

        cols = (
            "id",
            "tarih",
            "banka",
            "hesap",
            "tip",
            "tutar",
            "para",
            "aciklama",
            "referans",
            "belge",
            "etiket",
            "bakiye",
        )
        self.tree = ttk.Treeview(self.tab_detail, columns=cols, show="headings", height=16, selectmode="browse")
        for c in cols:
            self.tree.heading(c, text=c.upper())

        self.tree.column("id", width=55, anchor="center")
        self.tree.column("tarih", width=95)
        self.tree.column("banka", width=130)
        self.tree.column("hesap", width=160)
        self.tree.column("tip", width=70, anchor="center")
        self.tree.column("tutar", width=110, anchor="e")
        self.tree.column("para", width=55, anchor="center")
        self.tree.column("aciklama", width=360)
        self.tree.column("referans", width=120)
        self.tree.column("belge", width=90)
        self.tree.column("etiket", width=90)
        self.tree.column("bakiye", width=110, anchor="e")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=(6, 0))

        btm = ttk.Frame(self.tab_detail)
        btm.pack(fill=tk.X, pady=(6, 6))
        ttk.Button(btm, text="Seçili Import'u Aç", command=self.open_selected_import_as_table).pack(side=tk.LEFT, padx=6)
        self.btn_del = ttk.Button(btm, text="Seçili Kaydı Sil", command=self.delete_selected)
        self.btn_del.pack(side=tk.LEFT, padx=6)

        # Import özet sekmesi
        self.tab_imp = ttk.Frame(self.nb)
        self.nb.add(self.tab_imp, text="İçe Aktarımlar (Özet)")

        imp_cols = ("import_grup", "min_tarih", "max_tarih", "adet", "giris", "cikis", "net")
        self.tree_imp = ttk.Treeview(self.tab_imp, columns=imp_cols, show="headings", height=16, selectmode="browse")
        for c in imp_cols:
            self.tree_imp.heading(c, text=c.upper())
        self.tree_imp.column("import_grup", width=360)
        self.tree_imp.column("min_tarih", width=95)
        self.tree_imp.column("max_tarih", width=95)
        self.tree_imp.column("adet", width=70, anchor="center")
        self.tree_imp.column("giris", width=120, anchor="e")
        self.tree_imp.column("cikis", width=120, anchor="e")
        self.tree_imp.column("net", width=120, anchor="e")
        self.tree_imp.pack(fill=tk.BOTH, expand=True, padx=6, pady=(6, 0))
        self.tree_imp.bind("<Double-1>", lambda _e: self._open_group_in_detail(from_summary=True))

        btm2 = ttk.Frame(self.tab_imp)
        btm2.pack(fill=tk.X, pady=(6, 6))
        ttk.Button(btm2, text="Detay Sekmesinde Göster", command=lambda: self._open_group_in_detail(from_summary=True)).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(btm2, text="🧾 Tabloyu Aç (Çalış)", command=self.open_selected_import_as_table).pack(side=tk.LEFT, padx=6)

        self._apply_permissions()
        self.last30()
        self.refresh()

    def _apply_permissions(self):
        state = ("normal" if self.app.is_admin else "disabled")
        try:
            self.btn_del.config(state=state)
        except Exception:
            pass

    def reload_settings(self):
        pass

    # -----------------
    # Combo loaders
    # -----------------
    def _reload_banka_combo(self):
        try:
            banks = ["(Tümü)"] + (self.app.db.banka_distinct_banks() or [])
            cur = self.f_banka.get() or "(Tümü)"
            self.f_banka.cmb.configure(values=banks)
            if cur not in banks:
                cur = "(Tümü)"
            self.f_banka.set(cur)
        except Exception:
            pass

    def _reload_hesap_combo(self):
        try:
            b = self.f_banka.get()
            banka = "" if b in ("(Tümü)", "", None) else b
            accs = ["(Tümü)"] + (self.app.db.banka_distinct_accounts(banka=banka) or [])
            cur = self.f_hesap.get() or "(Tümü)"
            self.f_hesap.cmb.configure(values=accs)
            if cur not in accs:
                cur = "(Tümü)"
            self.f_hesap.set(cur)
        except Exception:
            pass

    def _reload_import_combo(self):
        try:
            groups = ["(Tümü)"] + (self.app.db.banka_import_groups(limit=80) or [])
            cur = self.f_import.get() or "(Tümü)"
            self.f_import.cmb.configure(values=groups)
            if cur not in groups:
                cur = "(Tümü)"
            self.f_import.set(cur)
        except Exception:
            pass

    # -----------------
    # Date shortcuts
    # -----------------
    def this_month(self):
        today = date.today()
        start = today.replace(day=1)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end = start.replace(month=start.month + 1, day=1) - timedelta(days=1)
        self.f_from.set(fmt_tr_date(start.isoformat()))
        self.f_to.set(fmt_tr_date(end.isoformat()))
        self.refresh()

    def last30(self):
        today = date.today()
        start = today - timedelta(days=30)
        self.f_from.set(fmt_tr_date(start.isoformat()))
        self.f_to.set(fmt_tr_date(today.isoformat()))
        self.refresh()

    # -----------------
    # Refresh
    # -----------------
    def refresh(self, data=None):
        self._reload_banka_combo()
        self._reload_hesap_combo()
        self._reload_import_combo()
        self._refresh_import_summary(select_group=(self.f_import.get() if self.f_import.get() != "(Tümü)" else ""))

        q = (self.f_q.get() or "").strip()
        tip = (self.f_tip.get() or "").strip()
        tip = "" if tip == "(Tümü)" else tip
        banka = (self.f_banka.get() or "").strip()
        banka = "" if banka == "(Tümü)" else banka
        hesap = (self.f_hesap.get() or "").strip()
        hesap = "" if hesap == "(Tümü)" else hesap
        imp = (self.f_import.get() or "").strip()
        import_grup = "" if imp in ("(Tümü)", "", None) else imp
        date_from = (self.f_from.get() or "").strip()
        date_to = (self.f_to.get() or "").strip()

        # Detay liste
        try:
            for i in self.tree.get_children():
                self.tree.delete(i)
        except Exception:
            pass

        rows = self.app.db.banka_list(
            q=q,
            date_from=date_from,
            date_to=date_to,
            tip=tip,
            banka=banka,
            hesap=hesap,
            import_grup=import_grup,
            limit=4000,
        )
        for r in rows:
            self.tree.insert(
                "",
                tk.END,
                values=(
                    r["id"],
                    r["tarih"],
                    r["banka"],
                    r["hesap"],
                    r["tip"],
                    fmt_amount(r["tutar"]),
                    r["para"],
                    (r["aciklama"] or ""),
                    (r["referans"] or ""),
                    (r["belge"] or ""),
                    (r["etiket"] or ""),
                    ("" if r["bakiye"] is None else fmt_amount(r["bakiye"])),
                ),
            )

        # Toplam
        if import_grup:
            giris = 0.0
            cikis = 0.0
            for r in rows:
                try:
                    if str(r["tip"]) == "Giriş":
                        giris += float(r["tutar"])
                    else:
                        cikis += float(r["tutar"])
                except Exception:
                    pass
            net = giris - cikis
            self.lbl_sum.config(text=f"Toplam: Giriş {fmt_amount(giris)}  •  Çıkış {fmt_amount(cikis)}  •  Net {fmt_amount(net)}")
        else:
            totals = self.app.db.banka_toplam(date_from=date_from, date_to=date_to, banka=banka, hesap=hesap)
            self.lbl_sum.config(
                text=f"Toplam: Giriş {fmt_amount(totals['giris'])}  •  Çıkış {fmt_amount(totals['cikis'])}  •  Net {fmt_amount(totals['net'])}"
            )

    # -----------------
    # Import summary helpers
    # -----------------
    def _refresh_import_summary(self, select_group: str = ""):
        """Özet sekmesindeki import gruplarını yeniler."""
        try:
            for iid in list(self.tree_imp.get_children()):
                self.tree_imp.delete(iid)
        except Exception:
            return

        try:
            rows = self.app.db.banka_import_group_summaries(limit=300) or []
        except Exception:
            rows = []

        to_select = None
        for r in rows:
            try:
                grp = str(r["import_grup"])
                min_t = str(r["min_tarih"] or "")
                max_t = str(r["max_tarih"] or "")
                adet = int(r["adet"] or 0)
                giris = float(r["giris"] or 0)
                cikis = float(r["cikis"] or 0)
                net = float(r["net"] or 0)
            except Exception:
                # tuple/list fallback
                try:
                    grp = str(r[0])
                    min_t = str(r[1])
                    max_t = str(r[2])
                    adet = int(r[3])
                    giris = float(r[4] or 0)
                    cikis = float(r[5] or 0)
                    net = float(r[6] or 0)
                except Exception:
                    continue
            if not grp:
                continue

            try:
                self.tree_imp.insert(
                    "",
                    tk.END,
                    iid=grp,
                    values=(grp, min_t, max_t, adet, fmt_amount(giris), fmt_amount(cikis), fmt_amount(net)),
                )
            except Exception:
                self.tree_imp.insert(
                    "",
                    tk.END,
                    values=(grp, min_t, max_t, adet, fmt_amount(giris), fmt_amount(cikis), fmt_amount(net)),
                )

            if select_group and grp == select_group:
                to_select = grp

        if to_select:
            try:
                self.tree_imp.selection_set(to_select)
                self.tree_imp.focus(to_select)
                self.tree_imp.see(to_select)
            except Exception:
                pass

    def _selected_id(self) -> Optional[int]:
        sel = self.tree.selection()
        if not sel:
            return None
        vals = self.tree.item(sel[0], "values")
        try:
            return int(vals[0])
        except Exception:
            return None

    def _get_selected_import_group(self) -> str:
        """Seçili import grubunu bulur.

        Öncelik:
          1) Filtre combobox
          2) Özet sekmesi seçimi
          3) Detay sekmesinde seçili satırın import_grup'u (DB'den)
        """
        try:
            imp = self.f_import.get()
            if imp and imp != "(Tümü)":
                return str(imp)
        except Exception:
            pass

        try:
            sel = self.tree_imp.selection()
            if sel:
                vals = self.tree_imp.item(sel[0], "values")
                if vals and vals[0]:
                    return str(vals[0])
        except Exception:
            pass

        hid = self._selected_id()
        if hid:
            try:
                r = self.app.db.banka_get(int(hid))
                return str(r["import_grup"] or "") if r else ""
            except Exception:
                return ""
        return ""

    def _open_group_in_detail(self, *, from_summary: bool = False):
        """Özet sekmesinde seçili grubu Detay sekmesinde göster."""
        grp = ""
        if from_summary:
            try:
                sel = self.tree_imp.selection()
                if sel:
                    vals = self.tree_imp.item(sel[0], "values")
                    grp = str(vals[0]) if vals and vals[0] else ""
            except Exception:
                grp = ""

        if not grp:
            grp = self._get_selected_import_group()
        if not grp:
            messagebox.showinfo(APP_TITLE, "Bir import grubu seçmelisin.")
            return

        try:
            self._reload_import_combo()
            self.f_import.set(grp)
        except Exception:
            pass
        self.refresh()
        try:
            self.nb.select(self.tab_detail)
        except Exception:
            pass

    # -----------------
    # Actions
    # -----------------
    def open_workspace(self, ids: Optional[List[int]] = None):
        """Mevcut filtreye göre (veya verilen id listesiyle) Excel benzeri tablo ekranını açar."""
        try:
            q = (self.f_q.get() or "").strip()
            tip = (self.f_tip.get() or "").strip()
            tip = "" if tip == "(Tümü)" else tip
            banka = (self.f_banka.get() or "").strip()
            banka = "" if banka == "(Tümü)" else banka
            hesap = (self.f_hesap.get() or "").strip()
            hesap = "" if hesap == "(Tümü)" else hesap
            date_from = (self.f_from.get() or "").strip()
            date_to = (self.f_to.get() or "").strip()
            imp = (self.f_import.get() or "").strip()
            import_grup = "" if imp in ("(Tümü)", "", None) else imp
        except Exception:
            q = tip = banka = hesap = date_from = date_to = import_grup = ""

        flt = {
            "q": q,
            "tip": (tip or "(Tümü)"),
            "banka": banka,
            "hesap": hesap,
            "import_grup": import_grup,
            "date_from": date_from,
            "date_to": date_to,
        }
        title_suffix = "Filtreli Görünüm" if not ids else "İçe Aktarılan Kayıtlar"
        BankaWorkspaceWindow(self.app, ids=ids, initial_filters=flt, title_suffix=title_suffix)

    def open_selected_import_as_table(self):
        grp = self._get_selected_import_group()
        if grp:
            try:
                ids = self.app.db.banka_ids_by_import_group(grp)
            except Exception:
                ids = []
            if not ids:
                messagebox.showinfo(APP_TITLE, "Bu import grubunda kayıt bulunamadı.")
                return
            # Detay sekmesinde de göster
            try:
                self.f_import.set(grp)
            except Exception:
                pass
            self.refresh()
            try:
                self.nb.select(self.tab_detail)
            except Exception:
                pass
            self.open_workspace(ids=ids)
            return

        # Grup yoksa mevcut filtreyle aç
        self.open_workspace(ids=None)

    def open_last_import(self):
        grp = ""
        try:
            grp = self.app.db.banka_last_import_group()
        except Exception:
            grp = ""
        if not grp:
            messagebox.showinfo(APP_TITLE, "Henüz bir banka excel içe aktarma yapılmamış.")
            return
        try:
            ids = self.app.db.banka_ids_by_import_group(grp)
        except Exception:
            ids = []
        if not ids:
            messagebox.showinfo(APP_TITLE, "Son import grubunda kayıt bulunamadı.")
            return
        try:
            self.f_import.set(grp)
        except Exception:
            pass
        self.refresh()
        try:
            self.nb.select(self.tab_detail)
        except Exception:
            pass
        self.open_workspace(ids=ids)

    def delete_selected(self):
        hid = self._selected_id()
        if not hid:
            return
        if not self.app.is_admin:
            messagebox.showerror(APP_TITLE, "Bu işlem için admin yetkisi gerekiyor.")
            return
        if not messagebox.askyesno(APP_TITLE, "Seçili banka hareketi silinsin mi?"):
            return
        try:
            self.app.db.banka_delete(hid)
            self.app.db.log("Banka", f"Silindi id={hid}")
        except Exception as e:
            messagebox.showerror(APP_TITLE, str(e))
            return
        self.refresh()

    def import_excel(self):
        if not HAS_OPENPYXL:
            messagebox.showerror(APP_TITLE, "openpyxl kurulu değil. Kur: pip install openpyxl")
            return
        p = filedialog.askopenfilename(title="Excel Seç", filetypes=[("Excel", "*.xlsx *.xlsm"), ("All", "*.*")])
        if not p:
            return

        w = ImportWizard(self.app, p, mode="bank")
        self.app.root.wait_window(w)

        if getattr(w, "result_counts", None):
            grp = str(getattr(w, "last_import_bank_group", "") or "")
            ids = getattr(w, "last_import_bank_ids", None)
            if grp:
                try:
                    self.f_import.set(grp)
                except Exception:
                    pass
            self.refresh()
            try:
                self.nb.select(self.tab_detail)
            except Exception:
                pass
            if ids:
                self.open_workspace(ids=list(ids))

    def _load_table(self) -> None:
        """Banka hareketlerini yükle."""
        try:
            rows = self.app.banka_repo.list_all(limit=500, offset=0)
            self.table.clear()
            
            if not rows:
                # Boş durum için bilgilendirme
                self.table.insert_row(
                    values=["Kayıt bulunamadı", "", "", "", ""],
                    tags=("empty",)
                )
                return
            
            for row in rows:
                self.table.insert_row(
                    values=[
                        row.id,
                        fmt_tr_date(row.tarih),
                        row.banka,
                        row.hesap,
                        row.tip,
                        fmt_amount(row.tutar),
                        row.para,
                        row.aciklama,
                        row.referans,
                        row.belge,
                        row.etiket,
                        fmt_amount(row.bakiye),
                    ]
                )
        except Exception as e:
            messagebox.showerror(
                "Hata",
                f"Banka hareketleri yüklenemedi:\n{e}"
            )
            import logging
            logging.exception("Banka tablosu yükleme hatası")


def build(master, app: "App") -> ttk.Frame:
    return BankaHareketleriFrame(master, app)
