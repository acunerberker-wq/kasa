# -*- coding: utf-8 -*-
"""KasaPro v3 - Ortak UI widget'ları"""

from __future__ import annotations

from typing import Any, List

import re
import tkinter as tk
from tkinter import ttk

from ..utils import safe_float, fmt_amount, parse_number_smart

class SimpleField:
    """Basit get/set alanı (LabeledEntry yerine)"""
    def __init__(self, value: str = ""):
        self._v = "" if value is None else str(value)
    def get(self) -> str:
        return self._v
    def set(self, v: str):
        self._v = "" if v is None else str(v)

class LabeledEntry(ttk.Frame):
    def __init__(self, master, label: str, width: int = 18):
        super().__init__(master)
        ttk.Label(self, text=label).pack(side=tk.LEFT, padx=(0,6))
        self.ent = ttk.Entry(self, width=width)
        self.ent.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def get(self) -> str:
        return self.ent.get()

    def set(self, v: str):
        self.ent.delete(0, tk.END)
        self.ent.insert(0, v)

class LabeledCombo(ttk.Frame):
    def __init__(self, master, label: str, values: List[str], width: int = 18, state: str="readonly"):
        super().__init__(master)
        ttk.Label(self, text=label).pack(side=tk.LEFT, padx=(0,6))
        self.var = tk.StringVar()
        self.cmb = ttk.Combobox(self, textvariable=self.var, values=values, width=width, state=state)
        self.cmb.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def get(self) -> str:
        return self.var.get()

    def set(self, v: str):
        self.var.set(v)

class MoneyEntry(ttk.Frame):
    """Para/tutar girişi için Entry (TR).
    - Yazarken maskeleme: 1111111 -> 1.111.111,00
    - ',' veya '.' basınca imleç küsurat kısmına geçer (virgülden sonraki 2 hane).
    - FocusOut / Enter'da kesin TR formatına çevirir (fmt_amount).
    """
    _IGNORE_KEYS = {
        "Left","Right","Up","Down","Home","End","Tab",
        "Shift_L","Shift_R","Control_L","Control_R","Alt_L","Alt_R",
        "Caps_Lock","Escape","Prior","Next"
    }

    def __init__(self, master, label: str, width: int = 12):
        super().__init__(master)
        ttk.Label(self, text=label).pack(side=tk.LEFT, padx=(0,6))
        self.var = tk.StringVar()
        self.ent = ttk.Entry(self, width=width, textvariable=self.var)
        self.ent.pack(side=tk.LEFT)

        self._formatting = False

        # Canlı maskeleme + çıkınca/enter'da kesin format
        self.ent.bind("<KeyRelease>", self._on_key_release)
        self.ent.bind("<FocusOut>", lambda _e: self.format_now())
        self.ent.bind("<Return>", self._on_return)

    @staticmethod
    def _group_tr(digits: str) -> str:
        # "1234567" -> "1.234.567"
        if not digits:
            return "0"
        rev = digits[::-1]
        parts = [rev[i:i+3] for i in range(0, len(rev), 3)]
        return ".".join(p[::-1] for p in parts[::-1])

    def _mask_tr(self, s: str) -> tuple[str, int]:
        """Girilen metni TR para biçimine maskele.
        Dönüş: (formatted, typed_dec_len)
        typed_dec_len: kullanıcının küsurat kısmında yazdığı hane sayısı (0-2).
        """
        s = (s or "").strip()
        if not s:
            return ("", 0)

        # işaret
        sign = ""
        if s.startswith("-"):
            sign = "-"
            s = s[1:].lstrip()

        # yalnızca rakam + ayırıcılar
        s = re.sub(r"[^\d,\.]", "", s)

        # Ondalık ayracı belirle:
        # - Virgül varsa onu kullan
        # - Virgül yoksa ve tek nokta + en fazla 2 hane ile bitiyorsa onu ondalık say
        dec_sep = None
        if "," in s:
            dec_sep = ","
        elif "." in s and s.count(".") == 1 and re.fullmatch(r"\d+\.\d{0,2}", s):
            dec_sep = "."

        if dec_sep:
            ip, dp = s.split(dec_sep, 1)
            ip_digits = re.sub(r"\D", "", ip)
            dp_digits = re.sub(r"\D", "", dp)[:2]
            typed_dec_len = len(dp_digits)
        else:
            ip_digits = re.sub(r"\D", "", s)
            dp_digits = ""
            typed_dec_len = 0

        if ip_digits == "" and dp_digits == "":
            return ("", 0)

        ip_digits = ip_digits.lstrip("0") or "0"
        grouped = self._group_tr(ip_digits)
        dp_show = (dp_digits or "").ljust(2, "0")[:2] if (dp_digits or "") else "00"
        return (f"{sign}{grouped},{dp_show}", typed_dec_len)

    def _on_return(self, _e):
        self.format_now()
        return "break"

    def _on_key_release(self, e: tk.Event):
        if self._formatting:
            return
        if getattr(e, "keysym", "") in self._IGNORE_KEYS:
            return
        # Enter zaten ayrı handler
        if getattr(e, "keysym", "") in ("Return", "KP_Enter"):
            return

        raw = self.var.get()
        # imleç konumu: küsurata mı yazıyor?
        try:
            cur = int(self.ent.index(tk.INSERT))
        except Exception:
            cur = len(raw)

        comma_pos_raw = raw.find(",")
        dot_pos_raw = raw.rfind(".")
        in_dec = False
        if comma_pos_raw != -1 and cur > comma_pos_raw:
            in_dec = True
        elif comma_pos_raw == -1 and dot_pos_raw != -1 and re.fullmatch(r".*\.\d{0,2}", raw):
            if cur > dot_pos_raw:
                in_dec = True

        # ',' veya '.' tuşu basıldıysa küsurata geç
        if getattr(e, "char", "") in (",", "."):
            in_dec = True

        formatted, typed_dec_len = self._mask_tr(raw)

        # tamamen boşsa boş bırak
        if formatted == "":
            return

        # Yeniden yaz
        self._formatting = True
        try:
            if formatted != raw:
                self.var.set(formatted)
        finally:
            self._formatting = False

        # imleci ayarla
        comma_pos = formatted.find(",")
        try:
            if in_dec:
                if getattr(e, "char", "") in (",", "."):
                    # küsurat kısmını seç ki direkt yazılabilsin
                    self.ent.icursor(comma_pos + 1)
                    self.ent.selection_range(comma_pos + 1, tk.END)
                else:
                    newpos = min(len(formatted), comma_pos + 1 + min(typed_dec_len, 2))
                    self.ent.icursor(newpos)
            else:
                # sürekli rakam girerken virgülden önce kalsın
                self.ent.icursor(comma_pos)
        except Exception:
            pass

    def format_now(self):
        s = (self.var.get() or "").strip()
        if not s:
            return
        val = parse_number_smart(s)
        self._formatting = True
        try:
            self.var.set(fmt_amount(val))
        finally:
            self._formatting = False

    def get_float(self) -> float:
        return safe_float(self.var.get())

    def set(self, v: Any):
        self._formatting = True
        try:
            self.var.set("" if (v is None or v == "") else fmt_amount(parse_number_smart(v)))
        finally:
            self._formatting = False
