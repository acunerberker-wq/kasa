# -*- coding: utf-8 -*-
"""KasaPro UI - Frame'ler (sekme içerikleri)."""

from .kasa import KasaFrame as KasaFrame
from .cariler import CarilerFrame as CarilerFrame
from .raporlar import RaporlarFrame as RaporlarFrame
from .global_search import GlobalSearchFrame as GlobalSearchFrame
from .logs import LogsFrame as LogsFrame
from .sirketler import SirketlerFrame as SirketlerFrame
from .kullanicilar import KullanicilarFrame as KullanicilarFrame
from .tanimlar_hub import TanimlarHubFrame as TanimlarHubFrame
from .rapor_araclar_hub import RaporAraclarHubFrame as RaporAraclarHubFrame
from .messages import MessagesFrame as MessagesFrame

__all__ = [
    "KasaFrame",
    "CarilerFrame",
    "RaporlarFrame",
    "GlobalSearchFrame",
    "LogsFrame",
    "SirketlerFrame",
    "KullanicilarFrame",
    "TanimlarHubFrame",
    "RaporAraclarHubFrame",
    "MessagesFrame",
]
