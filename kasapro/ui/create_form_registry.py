# -*- coding: utf-8 -*-
"""Create Center form registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, List, Sequence

from tkinter import ttk

from .create_forms import BaseCreateForm


FormFactory = Callable[[ttk.Frame, Any], BaseCreateForm]


@dataclass(frozen=True)
class FormSpec:
    form_id: str
    label: str
    category: str
    roles_allowed: Sequence[str]
    factory: FormFactory


CATEGORY_ORDER = [
    "Satış",
    "Satınalma",
    "Finans",
    "Stok",
    "Proje/Şantiye",
    "İK",
    "Doküman",
]


def get_form_registry() -> List[FormSpec]:
    def _cari_factory(parent: ttk.Frame, app: Any) -> BaseCreateForm:
        from .create_forms.cari import CariCreateForm

        return CariCreateForm(parent, app)

    def _urun_factory(parent: ttk.Frame, app: Any) -> BaseCreateForm:
        from .create_forms.urun import UrunCreateForm

        return UrunCreateForm(parent, app)

    def _satis_fatura_factory(parent: ttk.Frame, app: Any) -> BaseCreateForm:
        from .create_forms.satis_fatura import SatisFaturaCreateForm

        return SatisFaturaCreateForm(parent, app)

    def _siparis_factory(parent: ttk.Frame, app: Any) -> BaseCreateForm:
        from .create_forms.siparis import SiparisCreateForm

        return SiparisCreateForm(parent, app)

    def _tahsilat_factory(parent: ttk.Frame, app: Any) -> BaseCreateForm:
        from .create_forms.tahsilat import TahsilatCreateForm

        return TahsilatCreateForm(parent, app)

    return [
        FormSpec(
            form_id="cari",
            label="Cari Kartı",
            category="Satış",
            roles_allowed=["admin", "muhasebe", "satis", "satinlama"],
            factory=_cari_factory,
        ),
        FormSpec(
            form_id="urun",
            label="Ürün Kartı",
            category="Stok",
            roles_allowed=["admin", "muhasebe", "depo"],
            factory=_urun_factory,
        ),
        FormSpec(
            form_id="satis_fatura",
            label="Satış Faturası",
            category="Satış",
            roles_allowed=["admin", "muhasebe", "satis"],
            factory=_satis_fatura_factory,
        ),
        FormSpec(
            form_id="siparis",
            label="Sipariş",
            category="Satış",
            roles_allowed=["admin", "muhasebe", "satis", "satinlama"],
            factory=_siparis_factory,
        ),
        FormSpec(
            form_id="tahsilat",
            label="Tahsilat",
            category="Finans",
            roles_allowed=["admin", "muhasebe", "satis"],
            factory=_tahsilat_factory,
        ),
    ]
