# -*- coding: utf-8 -*-
"""UI Plugin: Maaş Eklentileri (ek modül)

Bu eklenti; mevcut "Maaş Takibi" ve "Banka" modüllerindeki bazı özellikleri
tek ekranda toplar:

1) Maaş Excel içe aktarma + Banka hareketleriyle eşleştirme
2) Banka çalışma alanını açıp (isteğe bağlı) "Maaşları Bul" taraması

Not: Bu eklenti, mevcut DB fonksiyonlarını kullanır.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from ...utils import safe_float, fmt_amount
from ...core.fuzzy import best_substring_similarity, amount_score, combine_scores, combine3_scores, normalize_text
from ..base import BaseView
from ..widgets import LabeledEntry, LabeledCombo
from ..windows import ImportWizard, BankaWorkspaceWindow
from ...config import APP_TITLE, HAS_OPENPYXL

if TYPE_CHECKING:
    from ...app import App

PLUGIN_META = {
    "key": "maas_eklentileri",
    "nav_text": "🧩 Maaş Eklentileri",
    "page_title": "Maaş Eklentileri",
    "order": 36,
}


def _current_period() -> str:
    return date.today().strftime("%Y-%m")


class MaasEklentileriFrame(BaseView):
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
        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        tab_match = ttk.Frame(nb)
        tab_scan = ttk.Frame(nb)
        tab_hist = ttk.Frame(nb)

        nb.add(tab_match, text="🧩 Excel & Eşleştirme")
        nb.add(tab_scan, text="💼 Bankada Maaş Bul")
        nb.add(tab_hist, text="🧾 Maaş Geçmişi / Hesap Hareketleri")

        self._build_match(tab_match)
        self._build_scan(tab_scan)
        self._build_history(tab_hist)

    # -----------------
    # Helpers
    # -----------------
    def _period_candidates(self) -> list[str]:
        out: list[str] = []
        today = date.today()
        y, m = today.year, today.month
        for i in range(0, 36):
            yy = y
            mm = m - i
            while mm <= 0:
                mm += 12
                yy -= 1
            out.append(f"{yy:04d}-{mm:02d}")

        # DB'den ek dönemler
        try:
            existing = self.app.db.maas_donem_list(limit=60)  # type: ignore
            for p in existing:
                if p and p not in out:
                    out.append(p)
        except Exception:
            pass
        return out

    @staticmethod
    def _period_to_range(period: str) -> Tuple[str, str]:
        """YYYY-MM -> (start_iso, end_iso)"""
        try:
            y, m = [int(x) for x in (period or "").split("-")[:2]]
            start = date(y, m, 1)
        except Exception:
            start = date.today().replace(day=1)

        if start.month == 12:
            nxt = date(start.year + 1, 1, 1)
        else:
            nxt = date(start.year, start.month + 1, 1)
        end = nxt - timedelta(days=1)
        return (start.isoformat(), end.isoformat())

    @staticmethod
    def _to_date(v: Any) -> Optional[date]:
        if v is None:
            return None
        if isinstance(v, date) and not isinstance(v, datetime):
            return v
        if isinstance(v, datetime):
            return v.date()
        try:
            s = str(v).strip()[:10]
            if not s:
                return None
            return date.fromisoformat(s)
        except Exception:
            return None

    @classmethod
    def _date_score(cls, bank_date: Any, pay_date: Any) -> float:
        bd = cls._to_date(bank_date)
        pd = cls._to_date(pay_date)
        if not bd or not pd:
            return 0.0
        diff = abs((bd - pd).days)
        if diff == 0:
            return 1.0
        if diff == 1:
            return 0.92
        if diff == 2:
            return 0.85
        if diff == 3:
            return 0.75
        if diff <= 7:
            return 0.55
        if diff <= 14:
            return 0.35
        return 0.0

    # -----------------
    # Tab 1: Excel & Eşleştirme
    # -----------------
    def _build_match(self, parent: ttk.Frame):
        box = ttk.LabelFrame(parent, text="Maaş Excel İçe Aktarma ve Banka Eşleştirme")
        box.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        top = ttk.Frame(box)
        top.pack(fill=tk.X, padx=6, pady=6)

        self.m_period = LabeledCombo(top, "Dönem:", ["(Seç)"] + self._period_candidates(), 10)
        self.m_period.pack(side=tk.LEFT, padx=6)
        self.m_period.set(_current_period())
        try:
            self.m_period.cmb.bind("<<ComboboxSelected>>", lambda _e: self._sync_match_date_range())
        except Exception:
            pass

        self.btn_maas_excel = ttk.Button(top, text="📥 Maaş Exceli İçe Aktar", command=self.import_maas_excel)
        self.btn_maas_excel.pack(side=tk.LEFT, padx=6)
        if not HAS_OPENPYXL:
            self.btn_maas_excel.config(state="disabled")

        ttk.Separator(top, orient="vertical").pack(side=tk.LEFT, fill=tk.Y, padx=10)

        self.m_from = LabeledEntry(top, "Banka Başlangıç:", 12)
        self.m_from.pack(side=tk.LEFT, padx=6)
        self.m_to = LabeledEntry(top, "Banka Bitiş:", 12)
        self.m_to.pack(side=tk.LEFT, padx=6)

        self.var_m_only_unpaid = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text="Sadece ödenmemiş", variable=self.var_m_only_unpaid).pack(side=tk.LEFT, padx=6)

        self.m_min_score = LabeledEntry(top, "Skor eşiği:", 6)
        self.m_min_score.pack(side=tk.LEFT, padx=6)
        self.m_min_score.set("0.78")

        self.m_abs_tol = LabeledEntry(top, "± TL:", 6)
        self.m_abs_tol.pack(side=tk.LEFT, padx=6)
        self.m_abs_tol.set("2")

        ttk.Button(top, text="🔎 Öner", command=self.suggest_salary_matches).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="✅ Seçili Uygula", command=self.apply_selected_matches).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="🧹 Bağı Temizle", command=self.clear_selected_links).pack(side=tk.LEFT, padx=6)

        cols = (
            "pid",
            "calisan",
            "tutar",
            "para",
            "odendi",
            "banka_id",
            "banka_tarih",
            "banka_tutar",
            "banka_aciklama",
            "score",
        )
        self.m_tree = ttk.Treeview(box, columns=cols, show="headings", height=18, selectmode="extended")
        for c in cols:
            self.m_tree.heading(c, text=c.upper())
        self.m_tree.column("pid", width=55, anchor="center")
        self.m_tree.column("calisan", width=200)
        self.m_tree.column("tutar", width=110, anchor="e")
        self.m_tree.column("para", width=55, anchor="center")
        self.m_tree.column("odendi", width=70, anchor="center")
        self.m_tree.column("banka_id", width=70, anchor="center")
        self.m_tree.column("banka_tarih", width=100)
        self.m_tree.column("banka_tutar", width=110, anchor="e")
        self.m_tree.column("banka_aciklama", width=420)
        self.m_tree.column("score", width=70, anchor="center")
        self.m_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        try:
            self.m_tree.tag_configure("ok", background="#D1FAE5")
            self.m_tree.tag_configure("warn", background="#FEF3C7")
            self.m_tree.tag_configure("no", background="#FEE2E2")
        except Exception:
            pass

        self._sync_match_date_range()

    def _sync_match_date_range(self):
        try:
            per = (self.m_period.get() or "").strip()
        except Exception:
            per = ""
        if not per or per == "(Seç)":
            per = _current_period()
        start, end = self._period_to_range(per)
        try:
            self.m_from.set(start)
            self.m_to.set(end)
        except Exception:
            pass

    def import_maas_excel(self):
        if not HAS_OPENPYXL:
            messagebox.showerror(APP_TITLE, "Excel içe aktarma için 'openpyxl' kurulu değil.\n\nKomut: pip install openpyxl")
            return

        period = (self.m_period.get() or "").strip()
        if not period or period == "(Seç)":
            period = _current_period()
        try:
            self.app.db.maas_ensure_donem(period)  # type: ignore
        except Exception:
            pass

        p = filedialog.askopenfilename(
            title="Maaş Exceli Seç",
            filetypes=[("Excel", "*.xlsx *.xlsm *.xltx *.xltm"), ("Tüm Dosyalar", "*.*")],
        )
        if not p:
            return

        w = ImportWizard(self.app, p, mode="maas", context={"donem": period})
        self.app.root.wait_window(w)

        # Ad-soyad ile banka hareketlerinde otomatik tarama + geçmiş kaydı
        try:
            self._auto_record_name_matches(period)
        except Exception:
            pass

        # İçe aktardıktan sonra direkt öneri üret
        self.suggest_salary_matches()
        try:
            self.refresh_history_tab()
        except Exception:
            pass


    def _auto_record_name_matches(self, period: str, *, date_from: str = "", date_to: str = "", name_min: float = 0.78) -> tuple[int, int]:
        """İçe aktarımdan sonra, çalışan ad-soyad + (varsa) aynı gün/aynı tutar yakınlığı ile
        banka hareketlerini tarar ve 'maas_hesap_hareket' tablosuna geçmiş kaydı açar.

        Dönüş: (eklenen_kayıt_sayısı, otomatik_link_sayısı)
        """
        period = (period or "").strip() or _current_period()
        if not date_from or not date_to:
            date_from, date_to = self._period_to_range(period)

        try:
            pay_rows = self.app.db.maas_odeme_list(donem=period, odendi=None, include_inactive=True)  # type: ignore
        except Exception:
            pay_rows = []
        if not pay_rows:
            return (0, 0)

        try:
            bank_rows = self.app.db.banka_list(date_from=date_from, date_to=date_to, tip="Çıkış", limit=15000)
        except Exception:
            bank_rows = []
        bank_rows = list(bank_rows or [])
        if not bank_rows:
            return (0, 0)

        def _get(r: Any, k: str, d: Any = "") -> Any:
            if isinstance(r, dict):
                return r.get(k, d)
            try:
                return r[k]
            except Exception:
                return d

        token_index: dict[str, list[int]] = {}
        bank_by_id: dict[int, tuple[Any, str, str, float, Any]] = {}  # id -> (row, norm_desc, para, abs_tutar, tarih)
        amount_buckets: dict[int, list[int]] = {}

        for b in bank_rows:
            try:
                bid = int(_get(b, "id", 0) or 0)
            except Exception:
                continue
            if bid <= 0:
                continue
            desc = str(_get(b, "aciklama", "") or "")
            nd = normalize_text(desc)
            para = str(_get(b, "para", "") or "")
            try:
                btutar = abs(float(_get(b, "tutar", 0.0) or 0.0))
            except Exception:
                btutar = 0.0
            btarih = _get(b, "tarih", "")
            bank_by_id[bid] = (b, nd, para, btutar, btarih)
            for tok in set(nd.split()):
                if len(tok) >= 3:
                    token_index.setdefault(tok, []).append(bid)
            try:
                buck = int(round(btutar))
            except Exception:
                buck = 0
            if buck > 0:
                amount_buckets.setdefault(buck, []).append(bid)

        used_bank_ids: set[int] = set()
        for pr in pay_rows:
            try:
                ub = int(_get(pr, "banka_hareket_id", 0) or 0)
            except Exception:
                ub = 0
            if ub:
                used_bank_ids.add(int(ub))

        added = 0
        auto_linked = 0

        for pr in pay_rows:
            try:
                oid = int(_get(pr, "id"))
                cid = int(_get(pr, "calisan_id"))
                emp_name = str(_get(pr, "calisan_ad", "") or "")
                expected = abs(float(_get(pr, "tutar", 0.0) or 0.0))
                epara = str(_get(pr, "para", "TL") or "TL")
                existing_link = int(_get(pr, "banka_hareket_id", 0) or 0)
                pay_date = _get(pr, "odeme_tarihi", "")
            except Exception:
                continue

            nname = normalize_text(emp_name)
            tokens = [t for t in nname.split() if len(t) >= 3]
            anchor = max(tokens, key=len) if tokens else ""
            name_cand_ids = token_index.get(anchor, []) if anchor else []

            # aynı gün/aynı tutar için aday seti (tarih yoksa pas)
            amtdate_cand: set[int] = set()
            if self._to_date(pay_date) is not None and expected > 0:
                tol_amt = max(2.0, expected * 0.03)
                lo = int(round(max(0.0, expected - tol_amt)))
                hi = int(round(expected + tol_amt))
                for buck in range(lo, hi + 1):
                    for bid in amount_buckets.get(buck, []) or []:
                        amtdate_cand.add(int(bid))

            best_link: tuple[float, Optional[int], float, float, float, str] = (0.0, None, 0.0, 0.0, 0.0, "")
            second_link = 0.0

            def _score_and_store(bid: int, *, mode: str, do_store: bool = True) -> Optional[tuple[float, float, float, float]]:
                nonlocal added, best_link, second_link
                if bid not in bank_by_id:
                    return None
                brow, _nd, bpara, btutar, btarih = bank_by_id[bid]
                desc = str(_get(brow, "aciklama", "") or "")
                name_sc = float(best_substring_similarity(emp_name, desc))
                thr = float(name_min + (0.08 if len(nname.split()) < 2 else 0.0))
                if mode == "name" and name_sc < thr:
                    return None
                try:
                    if epara and bpara and str(epara).strip().upper() != str(bpara).strip().upper():
                        return None
                except Exception:
                    pass

                amt_sc = float(amount_score(btutar, expected, abs_tol=2.0, pct_tol=0.03)) if expected > 0 else 0.0
                date_sc = float(self._date_score(btarih, pay_date)) if self._to_date(pay_date) is not None else 0.0

                if self._to_date(pay_date) is not None:
                    if name_sc >= 0.78:
                        score = float(combine3_scores(name_sc, amt_sc, date_sc, w_a=0.55, w_b=0.25, w_c=0.20))
                    elif date_sc >= 0.85:
                        score = float(combine3_scores(name_sc, amt_sc, date_sc, w_a=0.15, w_b=0.55, w_c=0.30))
                    else:
                        score = float(combine3_scores(name_sc, amt_sc, date_sc, w_a=0.25, w_b=0.65, w_c=0.10))
                else:
                    score = float(combine_scores(name_sc, amt_sc, w_name=0.85 if mode == "name" else 0.55, w_amt=0.15 if mode == "name" else 0.45))

                if do_store:
                    try:
                        rid = int(
                            self.app.db.maas_hesap_hareket_add(
                                donem=period,
                                calisan_id=cid,
                                banka_hareket_id=int(bid),
                                odeme_id=oid,
                                match_score=float(score),
                                match_type=("auto_name_scan" if mode == "name" else "auto_amt_date_scan"),
                            )
                            or 0
                        )  # type: ignore
                        if rid:
                            added += 1
                    except Exception:
                        pass

                if bid not in used_bank_ids and existing_link == 0:
                    if score > best_link[0]:
                        second_link = best_link[0]
                        best_link = (score, bid, name_sc, amt_sc, date_sc, mode)
                    elif score > second_link:
                        second_link = score

                return (score, name_sc, amt_sc, date_sc)

            for bid in name_cand_ids[:300]:
                _score_and_store(int(bid), mode="name")

            if amtdate_cand:
                tmp: list[tuple[float, int]] = []
                for bid in list(amtdate_cand)[:1200]:
                    res = _score_and_store(int(bid), mode="amtdate", do_store=False)
                    if res is None:
                        continue
                    sc, _ns, _as, ds = res
                    if sc >= 0.70 and ds >= 0.35:
                        tmp.append((sc, int(bid)))
                tmp.sort(key=lambda x: x[0], reverse=True)
                for _sc, bid in tmp[:6]:
                    _score_and_store(int(bid), mode="amtdate", do_store=True)

            if existing_link or best_link[1] is None:
                continue

            score, bid_opt, name_sc, amt_sc, date_sc, mode = best_link
            if bid_opt is None:
                continue
            bid = int(bid_opt)
            strong_by_name = (name_sc >= 0.90)
            strong_by_date_amt = (amt_sc >= 0.92 and date_sc >= 0.92)
            if score >= 0.92 and (score - second_link) >= 0.07 and (strong_by_name or strong_by_date_amt):
                try:
                    note = "auto_name_scan" if mode == "name" else "auto_amt_date"
                    self.app.db.maas_odeme_link_bank(oid, bid, score=float(score), note=note)  # type: ignore
                    used_bank_ids.add(bid)
                    auto_linked += 1
                except Exception:
                    pass

        return (added, auto_linked)

    def suggest_salary_matches(self):
        period = (self.m_period.get() or "").strip()
        if not period or period == "(Seç)":
            period = _current_period()

        date_from = (self.m_from.get() or "").strip()
        date_to = (self.m_to.get() or "").strip()
        if not date_from or not date_to:
            date_from, date_to = self._period_to_range(period)

        min_score = float(safe_float(self.m_min_score.get()))
        abs_tol = float(safe_float(self.m_abs_tol.get()))
        only_unpaid = bool(self.var_m_only_unpaid.get())

        for i in self.m_tree.get_children():
            self.m_tree.delete(i)

        try:
            pay_rows = self.app.db.maas_odeme_list(donem=period, odendi=(0 if only_unpaid else None))  # type: ignore
        except Exception:
            pay_rows = []

        try:
            bank_rows = self.app.db.banka_list(date_from=date_from, date_to=date_to, tip="Çıkış", limit=8000)
        except Exception:
            bank_rows = []

        bank_rows = list(bank_rows or [])

        def _get(r: Any, k: str, d: Any = "") -> Any:
            if isinstance(r, dict):
                return r.get(k, d)
            try:
                return r[k]
            except Exception:
                return d

        bank_by_id: Dict[int, Any] = {}
        bank_meta: Dict[int, Tuple[str, float, Any, str]] = {}  # id -> (para, abs_tutar, tarih, aciklama)
        amount_buckets: Dict[int, list[int]] = {}

        for br in bank_rows:
            try:
                bid = int(_get(br, "id", 0) or 0)
            except Exception:
                continue
            if bid <= 0:
                continue
            bank_by_id[bid] = br
            bpara = str(_get(br, "para", "") or "")
            try:
                btutar = abs(float(_get(br, "tutar", 0.0) or 0.0))
            except Exception:
                btutar = 0.0
            btarih = _get(br, "tarih", "")
            baciklama = str(_get(br, "aciklama", "") or "")
            bank_meta[bid] = (bpara, btutar, btarih, baciklama)
            try:
                buck = int(round(btutar))
            except Exception:
                buck = 0
            if buck > 0:
                amount_buckets.setdefault(buck, []).append(bid)

        unused_bank_ids = set(bank_by_id.keys())

        # DB'de linkli olanları önce göster
        for pr in pay_rows:
            try:
                existing_bank_id = int(pr.get("banka_hareket_id") or 0)
            except Exception:
                existing_bank_id = 0
            if existing_bank_id:
                try:
                    b = self.app.db.banka_get(existing_bank_id)
                except Exception:
                    b = None
                if b is not None:
                    unused_bank_ids.discard(existing_bank_id)
                    try:
                        score = float(pr.get("banka_match_score") or 1.0)
                    except Exception:
                        score = 1.0
                    self._insert_match_row(pr, b, score, force_tag="ok")

        # Linkli olmayanlara öneri üret (tutar + (varsa) tarih yakınlığı ile aday havuzu)
        pending: List[Tuple[int, float, Any, Any, str]] = []  # (rank, score, pr, br, tag)

        for pr in pay_rows:
            try:
                existing_bank_id = int(_get(pr, "banka_hareket_id", 0) or 0)
            except Exception:
                existing_bank_id = 0
            if existing_bank_id:
                continue

            try:
                emp_name = str(_get(pr, "calisan_ad", "") or "")
                expected = abs(float(_get(pr, "tutar", 0.0) or 0.0))
                para = str(_get(pr, "para", "TL") or "TL")
                pay_date = _get(pr, "odeme_tarihi", "")
            except Exception:
                continue

            has_pay_date = self._to_date(pay_date) is not None

            # adayları tutar bucket'larından topla
            cand_set: set[int] = set()
            tol_amt = max(float(abs_tol), float(expected) * 0.03, 0.01)
            lo = int(round(max(0.0, expected - tol_amt)))
            hi = int(round(expected + tol_amt))
            for buck in range(lo, hi + 1):
                for bid in amount_buckets.get(buck, []) or []:
                    if bid in unused_bank_ids:
                        cand_set.add(int(bid))

            if not cand_set:
                # fallback: ilk birkaçını tara (performans)
                cand_set = set(list(unused_bank_ids)[:2500])

            best_score = 0.0
            best_id: Optional[int] = None
            for bid in cand_set:
                if bid not in unused_bank_ids:
                    continue
                meta = bank_meta.get(int(bid))
                if not meta:
                    continue
                bpara, btutar, btarih, baciklama = meta
                try:
                    if para and bpara and str(para).strip().upper() != str(bpara).strip().upper():
                        continue
                except Exception:
                    pass

                amt_sc = float(amount_score(float(btutar), expected, abs_tol=max(float(abs_tol), 0.01), pct_tol=0.03))
                if amt_sc <= 0:
                    continue

                name_sc = float(best_substring_similarity(emp_name, str(baciklama or "")))
                date_sc = float(self._date_score(btarih, pay_date)) if has_pay_date else 0.0

                if has_pay_date:
                    if name_sc >= 0.78:
                        score = float(combine3_scores(name_sc, amt_sc, date_sc, w_a=0.55, w_b=0.25, w_c=0.20))
                    elif date_sc >= 0.85:
                        score = float(combine3_scores(name_sc, amt_sc, date_sc, w_a=0.15, w_b=0.55, w_c=0.30))
                    else:
                        score = float(combine3_scores(name_sc, amt_sc, date_sc, w_a=0.25, w_b=0.65, w_c=0.10))
                else:
                    score = float(combine_scores(name_sc, amt_sc, w_name=0.75, w_amt=0.25))

                if score > best_score:
                    best_score = score
                    best_id = int(bid)

            if best_id is not None and best_score >= float(min_score):
                br = bank_by_id.get(int(best_id))
                if br is not None:
                    unused_bank_ids.discard(int(best_id))
                    tag = "ok" if best_score >= 0.87 else "warn"
                    rank = 2 if tag == "ok" else 1
                    pending.append((rank, best_score, pr, br, tag))
                else:
                    pending.append((0, 0.0, pr, None, "no"))
            else:
                pending.append((0, 0.0, pr, None, "no"))

        pending.sort(key=lambda x: (x[0], x[1]), reverse=True)
        for _rank, sc, pr, br, tag in pending:
            self._insert_match_row(pr, br, sc, force_tag=tag)

    def _insert_match_row(self, pr: Any, br: Any, score: float, force_tag: str = ""):
        try:
            pid = int(pr["id"])
            emp = str(pr["calisan_ad"])
            tutar = float(pr["tutar"] or 0)
            para = str(pr.get("para") or "TL")
            odendi_val = int(pr.get("odendi") or 0)
            odendi = "Ödendi" if odendi_val == 1 else "Ödenmedi"
        except Exception:
            return

        if br is not None:
            try:
                bid = int(br.get("id") or 0)
                btarih = str(br.get("tarih") or "")
                btutar = float(br.get("tutar") or 0)
                baciklama = str(br.get("aciklama") or "")
            except Exception:
                bid, btarih, btutar, baciklama = 0, "", 0.0, ""
        else:
            bid, btarih, btutar, baciklama = 0, "", 0.0, ""

        values = (
            pid,
            emp,
            fmt_amount(tutar),
            para,
            odendi,
            ("" if bid == 0 else bid),
            btarih,
            fmt_amount(btutar),
            baciklama,
            ("" if score <= 0 else f"{score:.2f}"),
        )
        tag = force_tag or ("ok" if score >= 0.87 else ("warn" if score >= 0.78 else "no"))
        self.m_tree.insert("", "end", values=values, tags=(tag,))

    def apply_selected_matches(self):
        sel = self.m_tree.selection()
        if not sel:
            messagebox.showinfo(APP_TITLE, "Uygulamak için en az bir satır seç.")
            return

        ok = 0
        for iid in sel:
            vals = self.m_tree.item(iid, "values")
            if not vals or len(vals) < 10:
                continue
            try:
                pid = int(vals[0])
                bank_id = int(vals[5])
            except Exception:
                continue
            if bank_id <= 0:
                continue

            bank_date = str(vals[6] or "")
            try:
                score = float(str(vals[9] or "0").replace(",", "."))
            except Exception:
                score = 0.0

            try:
                self.app.db.maas_odeme_set_paid(pid, 1, odeme_tarihi=bank_date)  # type: ignore
                self.app.db.maas_odeme_link_bank(pid, bank_id, score=score)  # type: ignore
                # geçmişe de yaz
                try:
                    meta = self.app.db.maas_odeme_get(pid)  # type: ignore
                    if meta is not None:
                        self.app.db.maas_hesap_hareket_add(
                            donem=str(meta["donem"] or ""),
                            calisan_id=int(meta["calisan_id"]),
                            banka_hareket_id=int(bank_id),
                            odeme_id=int(pid),
                            match_score=float(score or 0.0),
                            match_type="manual_apply",
                        )  # type: ignore
                except Exception:
                    pass
                ok += 1
            except Exception:
                continue

        messagebox.showinfo(APP_TITLE, f"Uygulandı: {ok} satır")
        self.suggest_salary_matches()
        try:
            self.refresh_history_tab()
        except Exception:
            pass

    def clear_selected_links(self):
        sel = self.m_tree.selection()
        if not sel:
            messagebox.showinfo(APP_TITLE, "Temizlemek için en az bir satır seç.")
            return

        ok = 0
        for iid in sel:
            vals = self.m_tree.item(iid, "values")
            if not vals:
                continue
            try:
                pid = int(vals[0])
            except Exception:
                continue
            try:
                self.app.db.maas_odeme_clear_bank_link(pid)  # type: ignore
                ok += 1
            except Exception:
                continue

        messagebox.showinfo(APP_TITLE, f"Temizlendi: {ok} satır")
        self.suggest_salary_matches()
        try:
            self.refresh_history_tab()
        except Exception:
            pass

    # -----------------
    # Tab 2: Bankada Maaş Bul
    # -----------------


    def _build_history(self, parent: ttk.Frame):
        box = ttk.LabelFrame(parent, text="Maaş Geçmişi / Hesap Hareketleri")
        box.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        top = ttk.Frame(box)
        top.pack(fill=tk.X, padx=6, pady=6)

        self.h_period = LabeledCombo(top, "Dönem:", ["(Seç)"] + self._period_candidates(), 10)
        self.h_period.pack(side=tk.LEFT, padx=6)
        self.h_period.set(_current_period())

        self.h_from = LabeledEntry(top, "Tarih Başlangıç:", 12)
        self.h_from.pack(side=tk.LEFT, padx=6)
        self.h_to = LabeledEntry(top, "Tarih Bitiş:", 12)
        self.h_to.pack(side=tk.LEFT, padx=6)

        self.h_q = LabeledEntry(top, "Ara:", 18)
        self.h_q.pack(side=tk.LEFT, padx=6)

        ttk.Button(top, text="Yenile", command=self.refresh_history_tab).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="Temizle (Dönem)", command=self.clear_history_tab).pack(side=tk.LEFT, padx=6)

        try:
            s, e = self._period_to_range(_current_period())
            self.h_from.set(s)
            self.h_to.set(e)
        except Exception:
            pass

        cols = (
            "id",
            "created_at",
            "calisan",
            "donem",
            "banka_id",
            "banka_tarih",
            "banka_tutar",
            "banka_aciklama",
            "skor",
            "eslesme",
            "odeme_id",
            "odendi",
        )
        self.h_tree = ttk.Treeview(box, columns=cols, show="headings", height=14, selectmode="browse")
        for c in cols:
            self.h_tree.heading(c, text=c.upper())
        self.h_tree.column("id", width=55, anchor="center")
        self.h_tree.column("created_at", width=130)
        self.h_tree.column("calisan", width=200)
        self.h_tree.column("donem", width=90, anchor="center")
        self.h_tree.column("banka_id", width=75, anchor="center")
        self.h_tree.column("banka_tarih", width=110)
        self.h_tree.column("banka_tutar", width=110, anchor="e")
        self.h_tree.column("banka_aciklama", width=520)
        self.h_tree.column("skor", width=60, anchor="center")
        self.h_tree.column("eslesme", width=120)
        self.h_tree.column("odeme_id", width=75, anchor="center")
        self.h_tree.column("odendi", width=90, anchor="center")
        self.h_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.h_tree.bind("<Double-1>", lambda _e: self._show_history_detail())

    def _show_history_detail(self):
        sel = self.h_tree.selection()
        if not sel:
            return
        vals = self.h_tree.item(sel[0], "values")
        if not vals:
            return
        try:
            msg = (
                f"Çalışan: {vals[2]}\n"
                f"Dönem: {vals[3]}\n"
                f"Banka ID: {vals[4]}\n"
                f"Tarih: {vals[5]}\n"
                f"Tutar: {vals[6]}\n"
                f"Açıklama: {vals[7]}\n"
                f"Skor: {vals[8]} ({vals[9]})"
            )
        except Exception:
            msg = str(vals)
        messagebox.showinfo(APP_TITLE, msg)

    def refresh_history_tab(self):
        try:
            for i in self.h_tree.get_children():
                self.h_tree.delete(i)
        except Exception:
            return

        per = (self.h_period.get() or "").strip()
        if not per or per == "(Seç)":
            per = _current_period()

        date_from = (self.h_from.get() or "").strip()
        date_to = (self.h_to.get() or "").strip()
        if not date_from or not date_to:
            date_from, date_to = self._period_to_range(per)

        q = (self.h_q.get() or "").strip()

        try:
            rows = self.app.db.maas_hesap_hareket_list(donem=per, q=q, date_from=date_from, date_to=date_to, limit=8000, include_inactive=True)  # type: ignore
        except Exception:
            rows = []

        for r in rows or []:
            try:
                rid = int(r["id"])
                created_at = str(r["created_at"] or "")
                calisan = str(r["calisan_ad"] or "")
                donem = str(r["donem"] or "")
                bank_id = int(r["banka_hareket_id"])
                btarih = str(r["banka_tarih"] or "")
                btutar = fmt_amount(float(r["banka_tutar"] or 0))
                baciklama = str(r["banka_aciklama"] or "")
                skor = float(r["match_score"] or 0)
                eslesme = str(r["match_type"] or "")
                oid = r["odeme_id"]
                odeme_id = ("" if oid is None else int(oid))
                odendi = "Ödendi" if int(r["maas_odendi"] or 0) == 1 else "Ödenmedi"
            except Exception:
                continue

            self.h_tree.insert(
                "",
                "end",
                values=(rid, created_at, calisan, donem, bank_id, btarih, btutar, baciklama, ("" if skor <= 0 else f"{skor:.2f}"), eslesme, odeme_id, odendi),
            )

    def clear_history_tab(self):
        per = (self.h_period.get() or "").strip()
        if not per or per == "(Seç)":
            per = _current_period()
        if not messagebox.askyesno(APP_TITLE, f"{per} dönemi hesap hareketi geçmişi silinsin mi?"):
            return
        try:
            n = int(self.app.db.maas_hesap_hareket_clear_donem(per) or 0)  # type: ignore
        except Exception:
            n = 0
        messagebox.showinfo(APP_TITLE, f"Silindi: {n} kayıt")
        self.refresh_history_tab()
    def _build_scan(self, parent: ttk.Frame):
        box = ttk.LabelFrame(parent, text="Banka Çalışma Alanı - Maaş Tarama")
        box.pack(fill=tk.X, padx=6, pady=6)

        row = ttk.Frame(box)
        row.pack(fill=tk.X, padx=6, pady=8)

        self.s_from = LabeledEntry(row, "Başlangıç:", 12)
        self.s_from.pack(side=tk.LEFT, padx=6)
        self.s_to = LabeledEntry(row, "Bitiş:", 12)
        self.s_to.pack(side=tk.LEFT, padx=6)

        ttk.Button(row, text="Bu Ay", command=self._scan_this_month).pack(side=tk.LEFT, padx=6)
        ttk.Button(row, text="Son 30 gün", command=self._scan_last30).pack(side=tk.LEFT, padx=6)

        ttk.Separator(row, orient="vertical").pack(side=tk.LEFT, fill=tk.Y, padx=10)

        ttk.Button(row, text="🧾 Çalışma Alanını Aç", command=lambda: self._open_bank_workspace(auto_run=False)).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(row, text="💼 Aç + Maaşları Bul", command=lambda: self._open_bank_workspace(auto_run=True)).pack(
            side=tk.LEFT, padx=6
        )

        info = ttk.Label(
            parent,
            text=(
                "Not: 'Maaşları Bul' taraması banka açıklamalarında çalışan isimlerini (fuzzy) arar.\n"
                "Büyük/küçük harf, Türkçe karakter ve küçük yazım hatalarına toleranslıdır."
            ),
        )
        info.pack(anchor="w", padx=12, pady=(6, 0))

        self._scan_this_month()

    def _scan_this_month(self):
        today = date.today()
        start = today.replace(day=1)
        if start.month == 12:
            end = date(start.year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(start.year, start.month + 1, 1) - timedelta(days=1)
        self.s_from.set(start.isoformat())
        self.s_to.set(end.isoformat())

    def _scan_last30(self):
        today = date.today()
        start = today - timedelta(days=30)
        self.s_from.set(start.isoformat())
        self.s_to.set(today.isoformat())

    def _open_bank_workspace(self, *, auto_run: bool):
        date_from = (self.s_from.get() or "").strip()
        date_to = (self.s_to.get() or "").strip()

        flt = {
            "q": "",
            "tip": "Çıkış",
            "banka": "",
            "hesap": "",
            "import_grup": "(Tümü)",
            "date_from": date_from,
            "date_to": date_to,
        }

        w = BankaWorkspaceWindow(self.app, ids=None, initial_filters=flt, title_suffix="Maaş Tarama")
        if auto_run:
            try:
                w.after(250, w.macro_find_salary)
            except Exception:
                pass


def build(master, app: "App") -> ttk.Frame:
    frame = MaasEklentileriFrame(master, app)
    return frame
