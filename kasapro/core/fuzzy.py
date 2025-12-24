# -*- coding: utf-8 -*-
"""Basit (ek bağımlılıksız) fuzzy metin eşleştirme yardımcıları.

Bu modül özellikle:
- Türkçe karakter normalize
- İsim/ünvan benzerliği (büyük/küçük, 1 harf farkı vb.)
- Açıklama içinde kişi adı arama

Amaç: Banka hareketleri içindeki kişi adlarını (maaş alanlar vb.)
yakalamak ve eşleştirme/renklendirme için skor üretmek.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from typing import Sequence


_TR_MAP = str.maketrans(
    {
        "İ": "i",
        "I": "i",
        "ı": "i",
        "Ş": "s",
        "ş": "s",
        "Ğ": "g",
        "ğ": "g",
        "Ü": "u",
        "ü": "u",
        "Ö": "o",
        "ö": "o",
        "Ç": "c",
        "ç": "c",
    }
)

_RX_NON_ALNUM = re.compile(r"[^a-z0-9\s]")
_RX_MULTI_SPACE = re.compile(r"\s+")


def tr_normalize(s: str) -> str:
    """Türkçe karakterleri sadeleştirir + lower."""
    return (s or "").translate(_TR_MAP).lower()


def normalize_text(s: str) -> str:
    """Karşılaştırma için metni normalize eder."""
    t = tr_normalize(s)
    t = _RX_NON_ALNUM.sub(" ", t)
    t = _RX_MULTI_SPACE.sub(" ", t).strip()
    return t


def similarity(a: str, b: str) -> float:
    """0..1 arası benzerlik (SequenceMatcher)."""
    a = (a or "").strip()
    b = (b or "").strip()
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return float(difflib.SequenceMatcher(None, a, b).ratio())


def best_substring_similarity(needle: str, haystack: str) -> float:
    """needle ifadesinin haystack içinde en iyi eşleşme skorunu döndürür.

    - Kelime bazlı kaydırmalı pencere kullanır.
    - 1 harf farkı / büyük-küçük farklarını iyi tolere eder.
    """
    n = normalize_text(needle)
    h = normalize_text(haystack)
    if not n or not h:
        return 0.0
    if n in h:
        return 1.0

    n_tokens = n.split()
    h_tokens = h.split()
    if not n_tokens or not h_tokens:
        return similarity(n, h)

    # Token overlap (hafif bir skor)
    try:
        overlap = len(set(n_tokens) & set(h_tokens)) / max(1, len(set(n_tokens)))
    except Exception:
        overlap = 0.0

    # Kaydırmalı pencere: n-1, n, n+1
    lens = sorted({max(1, len(n_tokens) - 1), len(n_tokens), len(n_tokens) + 1})
    best = 0.0
    for L in lens:
        if L <= 0:
            continue
        if len(h_tokens) < L:
            best = max(best, similarity(n, h))
            continue
        for i in range(0, len(h_tokens) - L + 1):
            chunk = " ".join(h_tokens[i : i + L])
            best = max(best, similarity(n, chunk))
            if best >= 0.995:
                return 1.0

    return float(max(best, overlap))


def amount_score(amount: float, expected: float, *, abs_tol: float = 2.0, pct_tol: float = 0.03) -> float:
    """Tutar benzerliği skoru (0..1).

    - abs_tol: mutlak tolerans
    - pct_tol: yüzde tolerans (örn %3)
    """
    try:
        a = abs(float(amount))
        e = abs(float(expected))
    except Exception:
        return 0.0
    if e <= 0:
        return 0.0
    diff = abs(a - e)
    tol = max(abs_tol, e * pct_tol)
    if diff <= tol:
        # tolerans içinde lineer skor
        return float(max(0.0, 1.0 - (diff / tol)))
    return 0.0


@dataclass
class BestMatch:
    key: str
    score: float


def best_key_match(keys: Sequence[str], text: str) -> BestMatch:
    best = BestMatch(key="", score=0.0)
    for k in keys or []:
        s = best_substring_similarity(k, text)
        if s > best.score:
            best = BestMatch(key=str(k), score=float(s))
    return best


def combine_scores(name_score: float, amt_score: float, *, w_name: float = 0.7, w_amt: float = 0.3) -> float:
    """İsim + tutar skorlarını tek bir skora indirger."""
    name_score = float(max(0.0, min(1.0, name_score)))
    amt_score = float(max(0.0, min(1.0, amt_score)))
    w_name = float(max(0.0, min(1.0, w_name)))
    w_amt = float(max(0.0, min(1.0, w_amt)))
    if (w_name + w_amt) <= 0:
        return name_score
    return (name_score * w_name + amt_score * w_amt) / (w_name + w_amt)


def combine3_scores(a: float, b: float, c: float, *, w_a: float = 0.5, w_b: float = 0.3, w_c: float = 0.2) -> float:
    """Üç skoru (0..1) ağırlıklı ortalama ile tek bir skora indirger."""

    def _clamp(x: float) -> float:
        return float(max(0.0, min(1.0, x)))

    a = _clamp(a)
    b = _clamp(b)
    c = _clamp(c)
    w_a = float(max(0.0, min(1.0, w_a)))
    w_b = float(max(0.0, min(1.0, w_b)))
    w_c = float(max(0.0, min(1.0, w_c)))
    tot = (w_a + w_b + w_c)
    if tot <= 0:
        return a
    return (a * w_a + b * w_b + c * w_c) / tot
