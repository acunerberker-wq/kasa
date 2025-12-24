# -*- coding: utf-8 -*-
"""Banka 'makro' fonksiyonları.

Bu modül, Excel/VBA tarafında kullanılan iki temel ihtiyacı uygulama içine taşır:

1) Açıklamaya göre esnek gruplama (benzer açıklamaları yakalayıp etiket önerme)
2) Banka hareketleri için özet/aylık/günlük/grup-günlük analiz tabloları üretme

Uygulama içinde bu fonksiyonlar genellikle 'toblo / tablo' pencerelerinde
(örn. BankaWorkspaceWindow) bir "eklenti" gibi çalıştırılır.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import re
from typing import Callable, Dict, List, Optional, Sequence, Tuple


# ==========================================================
# 1) Açıklama bazlı gruplama
# ==========================================================

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


def tr_normalize(s: str) -> str:
    """Türkçe karakterleri sadeleştirir + lower."""
    return (s or "").translate(_TR_MAP).lower()


_RX_MULTI_SPACE = re.compile(r"\s+")
_RX_NON_ALNUM = re.compile(r"[^a-z0-9\s]")
_RX_SN = re.compile(r"\bsn\s*: ?\s*\d+\b", re.IGNORECASE)
_RX_REF_NUM = re.compile(
    r"\b(gonbanka|gonbanka\s*no|gonsube|gonsube\s*no|eftref|eftrefno|ref|sube|banka)\s*: ?\s*\d+\b",
    re.IGNORECASE,
)
_RX_BIG_NUM = re.compile(r"\b\d{3,}\b")


_STOPWORDS = {
    # Banka / transfer kelimeleri
    "eft",
    "havale",
    "fast",
    "swift",
    "pos",
    "atm",
    "islem",
    "islemi",
    "odeme",
    "odemes",
    "odemesi",
    "tahsilat",
    "tahsil",
    "banka",
    "sube",
    "no",
    "ref",
    "sn",
    "gelen",
    "giden",
    "giris",
    "cikis",
    "borc",
    "alacak",
    "ucret",
    "komisyon",
    "faiz",
    "bsmv",
    "kkdf",
    "masraf",
    "transfer",
    "tutar",
    "tl",
    "try",
    "usd",
    "eur",
    # Çok genel
    "ve",
    "ile",
    "icin",
    "da",
    "de",
    "a",
    "an",
    "the",
    "to",
    "from",
}

# Ek stopword/temizlik kelimeleri (doğruluk için geniş tutulur)
_STOPWORDS.update({
    # Şirket ekleri / çok sık geçen gürültü
    'ltd', 'ltdsti', 'sti', 'as', 'a', 's', 'anonim', 'sirket', 'sirketi', 'limited', 'tic', 'san', 'ticaret', 'sanayi',
    'ins', 'insaat', 'nak', 'nakliyat', 'turizm', 'gida', 'tekstil', 'otomotiv', 'petrol',
    # Banka uygulama gürültüleri
    'turkiye', 'cumhuriyeti', 't', 'c', 'tc', 'bankasi', 'mobil', 'internet', 'sube', 'subesi', 'genel',
    # Genel bağlaçlar/kelimeler
    'veya', 'ile', 'icin', 'kadar', 'tutar', 'tutari', 'aciklama', 'aciklamasi', 'odeme', 'odemesi', 'tahsilat', 'tahsil',
    'islemler', 'islem', 'islemi', 'islemno', 'islem_no', 'islemno', 'islemnr',
})



# ------------------
# Etiket kuralları (kural tabanlı ilk katman)
# ------------------

DEFAULT_TAG_RULES: List[Dict[str, object]] = [
    # Öncelik küçük olan önce uygulanır
    {'priority': 10, 'tag': 'Market', 'pattern': r"\b(BIM|A101|SOK|MIGROS|CARREFOUR|FILE|KIPA)\b"},
    {'priority': 20, 'tag': 'Akaryakıt', 'pattern': r"\b(OPET|SHELL|BP|PO|PETROL\s*OFISI|TOTAL|AYGAZ)\b"},
    {'priority': 30, 'tag': 'Yemek', 'pattern': r"\b(YEMEKSEPETI|GETIR|TRENDYOL\s*GO|MIGROS\s*YEMEK|SETCARD|MULTINET)\b"},
    {'priority': 40, 'tag': 'E-Ticaret', 'pattern': r"\b(TRENDYOL|HEPSIBURADA|AMAZON|N11)\b"},
    {'priority': 50, 'tag': 'Fatura', 'pattern': r"\b(AYEDA\s*S|BEDAS|TEIAS|TEDAS|DOGALGAZ|IGDAS|SU\s*FATURA|INTERNET\s*FATURA)\b"},
    {'priority': 60, 'tag': 'Kira', 'pattern': r"\b(KIRA|KIRASI)\b"},
    {'priority': 70, 'tag': 'Maaş', 'pattern': r"\b(MAAS|UCRET|PERSONEL)\b"},
    {'priority': 80, 'tag': 'Vergi', 'pattern': r"\b(VD\.?|VERGI\s*DAIRESI|GIB|KDV|STOPAJ|MUHTASAR)\b"},
    {'priority': 90, 'tag': 'Banka Ücreti', 'pattern': r"\b(KOMISYON|MASRAF|UCRET|BSMV|KKDF|FAIZ)\b"},
]

def _strip_sign_suffix(tag: str) -> str:
    return re.sub(r"\s*\([+-]\)\s*$", "", (tag or "").strip())

def _as_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except Exception:
            return default
    return default

def _as_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except Exception:
            return default
    return default

def compile_tag_rules(rules: Sequence[Dict[str, object]]) -> List[Tuple[int, str, re.Pattern]]:
    compiled: List[Tuple[int, str, re.Pattern]] = []
    for r in (rules or []):
        try:
            tag = str(r.get('tag') or '').strip()
            pat = str(r.get('pattern') or '').strip()
            pr = _as_int(r.get('priority'), 100)
            if not tag or not pat:
                continue
            rx = re.compile(pat, re.IGNORECASE)
            compiled.append((pr, tag, rx))
        except Exception:
            continue
    compiled.sort(key=lambda x: x[0])
    return compiled

def _match_rule(desc_norm: str, compiled: Sequence[Tuple[int, str, re.Pattern]]) -> str:
    for _, tag, rx in compiled:
        try:
            if rx.search(desc_norm):
                return tag
        except Exception:
            continue
    return ''

def build_tag_suggestions(
    rows: Sequence[Dict[str, object]],
    *,
    rules: Optional[Sequence[Dict[str, object]]] = None,
    target_only_empty: bool = False,
    split_plus_minus: bool = True,
    progress_cb: Optional[Callable[[str, int, int], None]] = None,
    should_cancel: Optional[Callable[[], bool]] = None,
) -> Tuple[Dict[int, str], int]:
    """Satır id -> etiket önerisi üretir (kural + öğrenen eşleştirme + fuzzy).

    - rules: regex tabanlı kural listesi
    - target_only_empty: True ise sadece ETİKET boş satırlara öneri üretir; mevcut etiketler öğrenme için kullanılır.
    - split_plus_minus: (+)/(-) ayrımı ekler.
    """
    compiled = compile_tag_rules(rules or DEFAULT_TAG_RULES)

    # 1) Öğrenen eşleştirme: mevcut etiketli satırlardan (normalize_desc -> tag) sözlüğü
    learned: Dict[str, str] = {}
    for r in rows:
        t = str(r.get('etiket') or '').strip()
        if not t:
            continue
        key = normalize_for_grouping(str(r.get('aciklama') or ''))
        base = _strip_sign_suffix(t)
        if key and base and key not in learned:
            learned[key] = base

    # 2) Hedef satırları seç
    targets: List[Dict[str, object]] = []
    for r in rows:
        if target_only_empty and str(r.get('etiket') or '').strip():
            continue
        targets.append(r)

    total = len(targets) if targets else 0
    out: Dict[int, str] = {}

    def signed(tag_base: str, tip: str) -> str:
        tag_base = (tag_base or '').strip()
        if not tag_base:
            return ''
        if not split_plus_minus:
            return tag_base
        if re.search(r"\([+-]\)\s*$", tag_base):
            return tag_base
        is_plus = (str(tip or '').strip() == 'Giriş')
        return f"{tag_base} (+)" if is_plus else f"{tag_base} (-)"

    # 3) Kuralları ve öğreneni uygula
    remaining: List[Dict[str, object]] = []
    for i, r in enumerate(targets):
        if should_cancel and should_cancel():
            raise RuntimeError('İşlem iptal edildi.')
        if progress_cb and (i % 50 == 0 or i == total - 1):
            progress_cb('Kurallar/Öğrenen', i + 1, total)

        rid = _as_int(r.get('id'), 0)
        if rid == 0:
            continue
        tip = str(r.get('tip') or '')
        desc_norm = tr_normalize(str(r.get('aciklama') or ''))

        # kural
        base = _match_rule(desc_norm, compiled)
        if base:
            out[rid] = signed(base, tip)
            continue

        # öğrenen (exact normalize match)
        k = normalize_for_grouping(str(r.get('aciklama') or ''))
        base2 = learned.get(k, '')
        if base2:
            out[rid] = signed(base2, tip)
            continue

        remaining.append(r)

    # 4) Kalanlar için fuzzy gruplama
    group_count = 0
    if remaining:
        groups = group_rows_by_description(
            remaining,
            progress_cb=(lambda c, t: progress_cb('Fuzzy Gruplama', c, t) if progress_cb else None),
            should_cancel=should_cancel,
        )
        group_count = len(groups)
        tag_map = suggest_tags_from_groups(groups, split_plus_minus=split_plus_minus)
        out.update(tag_map)

    return out, group_count


def _filter_meaningful_tokens(text: str) -> List[str]:
    toks: List[str] = []
    for t in (text or "").split():
        t = t.strip()
        if not t:
            continue
        if any(ch.isdigit() for ch in t):
            continue
        if len(t) < 3:
            continue
        if t in _STOPWORDS:
            continue
        toks.append(t)
    return toks


def normalize_for_grouping(raw_desc: str) -> str:
    """Açıklamayı benzerlik hesapları için normalize eder."""
    t = tr_normalize(raw_desc or "")
    t = t.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    t = _RX_SN.sub(" ", t)
    t = _RX_REF_NUM.sub(" ", t)
    t = _RX_BIG_NUM.sub(" ", t)
    t = _RX_NON_ALNUM.sub(" ", t)
    t = _RX_MULTI_SPACE.sub(" ", t).strip()

    toks = _filter_meaningful_tokens(t)
    if not toks:
        # Tamamen boş kalmasın; en azından kısa bir parça bırak.
        fallback = tr_normalize(raw_desc or "")
        fallback = _RX_NON_ALNUM.sub(" ", fallback)
        fallback = _RX_MULTI_SPACE.sub(" ", fallback).strip()
        return fallback[:30].strip()
    return " ".join(toks)


def _bucket_key(norm_desc: str) -> str:
    toks = (norm_desc or "").split()
    if not toks:
        return ""
    if len(toks) == 1:
        return toks[0]
    return f"{toks[0]} {toks[1]}"


def _token_weight(tok: str) -> float:
    L = len(tok)
    if L >= 10:
        return 3.0
    if L >= 6:
        return 2.0
    return 1.0


def weighted_jaccard_sim(a: str, b: str) -> float:
    a = (a or "").strip()
    b = (b or "").strip()
    if not a or not b:
        return 0.0

    da: Dict[str, float] = {}
    db: Dict[str, float] = {}
    for tok in a.split():
        w = _token_weight(tok)
        if tok in da:
            if w > da[tok]:
                da[tok] = w
        else:
            da[tok] = w
    for tok in b.split():
        w = _token_weight(tok)
        if tok in db:
            if w > db[tok]:
                db[tok] = w
        else:
            db[tok] = w

    inter_w = 0.0
    union_w = 0.0
    for k, wa in da.items():
        if k in db:
            wb = db[k]
            inter_w += wa if wa < wb else wb
            union_w += wa if wa > wb else wb
        else:
            union_w += wa
    for k, wb in db.items():
        if k not in da:
            union_w += wb

    return 0.0 if union_w <= 0 else float(inter_w / union_w)


def _levenshtein_distance_limited(s: str, t: str, max_dist: int) -> int:
    """Levenshtein mesafesi (limitli). Limit aşılırsa -1."""
    if s == t:
        return 0
    n = len(s)
    m = len(t)
    if n == 0:
        return m if m <= max_dist else -1
    if m == 0:
        return n if n <= max_dist else -1

    # DP için iki satır
    prev = list(range(m + 1))
    cur = [0] * (m + 1)

    for i in range(1, n + 1):
        cur[0] = i
        # erken çıkış için satır min
        row_min = cur[0]
        sc = s[i - 1]
        for j in range(1, m + 1):
            cost = 0 if sc == t[j - 1] else 1
            cur[j] = min(
                prev[j] + 1,      # sil
                cur[j - 1] + 1,   # ekle
                prev[j - 1] + cost,
            )
            if cur[j] < row_min:
                row_min = cur[j]
        if row_min > max_dist:
            return -1
        prev, cur = cur, prev
    return prev[m] if prev[m] <= max_dist else -1


def similarity_levenshtein_limited(s1: str, s2: str, threshold: float) -> float:
    s1 = s1 or ""
    s2 = s2 or ""
    l1 = len(s1)
    l2 = len(s2)
    if l1 == 0 and l2 == 0:
        return 1.0
    max_len = l1 if l1 >= l2 else l2
    max_dist = int(((1.0 - threshold) * max_len) + 0.999999)
    dist = _levenshtein_distance_limited(s1, s2, max_dist)
    if dist < 0:
        return 0.0
    return 1.0 - (dist / max_len)


def clean_short_title(s: str, max_len: int = 30) -> str:
    t = (s or "").replace("\r", " ").replace("\n", " ").replace("\t", " ")
    t = _RX_MULTI_SPACE.sub(" ", t).strip()
    if not t:
        t = "(boş açıklama)"
    if len(t) > max_len:
        return t[: max(1, max_len - 1)] + "…"
    return t


@dataclass
class GroupResult:
    title: str
    members_plus: List[int]
    members_minus: List[int]

    @property
    def size(self) -> int:
        return len(self.members_plus) + len(self.members_minus)


def group_rows_by_description(
    rows: Sequence[Dict[str, object]],
    *,
    strong_threshold: float = 0.72,
    weak_threshold: float = 0.60,
    progress_cb: Optional[Callable[[int, int], None]] = None,
    should_cancel: Optional[Callable[[], bool]] = None,
) -> List[GroupResult]:
    """Benzer açıklamalara göre satırları gruplar.

    rows: her eleman en az şu anahtarları taşımalı:
      - id (int)
      - aciklama (str)
      - tip (str)  -> 'Giriş' / 'Çıkış' (plus/minus ayrımı için)

    Çıktı: grup listesi (büyükten küçüğe).
    """

    # Hazırlık
    norm: List[str] = []
    bucket: List[str] = []
    for r in rows:
        nd = normalize_for_grouping(str(r.get("aciklama") or ""))
        norm.append(nd)
        bucket.append(_bucket_key(nd))

    # Gruplar
    rep_norm: List[str] = []
    rep_title: List[str] = []
    members_plus: List[List[int]] = []
    members_minus: List[List[int]] = []
    bucket_to_gids: Dict[str, List[int]] = {}

    for idx, r in enumerate(rows):
        if should_cancel and should_cancel():
            raise RuntimeError('İşlem iptal edildi.')
        if progress_cb and (idx % 50 == 0 or idx == len(rows) - 1):
            progress_cb(idx + 1, len(rows))

        rid = _as_int(r.get("id"), 0)
        if rid == 0:
            continue
        tip = str(r.get("tip") or "")
        is_plus = (tip == "Giriş")
        nd = norm[idx]
        bkey = bucket[idx]

        candidates = bucket_to_gids.get(bkey, [])

        best_gid: Optional[int] = None
        best_sim: float = 0.0
        for gid in candidates:
            # hızlı filtre: wj düşükse boşuna lev hesaplama
            wj = weighted_jaccard_sim(nd, rep_norm[gid])
            if wj < 0.42:
                continue
            lev = similarity_levenshtein_limited(nd, rep_norm[gid], threshold=0.65)
            sim = wj if wj > lev else lev

            gsize = len(members_plus[gid]) + len(members_minus[gid])
            thr = strong_threshold if gsize > 1 else weak_threshold
            if sim >= thr and sim > best_sim:
                best_sim = sim
                best_gid = gid

        if best_gid is None:
            # yeni grup
            gid = len(rep_norm)
            rep_norm.append(nd)
            rep_title.append(clean_short_title(str(r.get("aciklama") or ""), max_len=30))
            members_plus.append([])
            members_minus.append([])
            bucket_to_gids.setdefault(bkey, []).append(gid)
            best_gid = gid

        if is_plus:
            members_plus[best_gid].append(rid)
        else:
            members_minus[best_gid].append(rid)

    groups: List[GroupResult] = []
    for gid in range(len(rep_norm)):
        groups.append(GroupResult(title=rep_title[gid], members_plus=members_plus[gid], members_minus=members_minus[gid]))
    groups.sort(key=lambda g: (-g.size, g.title.lower()))
    return groups


def suggest_tags_from_groups(
    groups: Sequence[GroupResult],
    *,
    split_plus_minus: bool = True,
) -> Dict[int, str]:
    """Gruplardan satır-id -> etiket önerisi üretir."""
    out: Dict[int, str] = {}
    for g in groups:
        title = g.title or "(boş açıklama)"
        has_plus = bool(g.members_plus)
        has_minus = bool(g.members_minus)

        if split_plus_minus and (has_plus or has_minus):
            # VBA'daki gibi (+) ve (-) grupları ardışık tutulabilsin diye işaretliyoruz.
            if has_plus:
                t_plus = f"{title} (+)" if (has_plus and has_minus) else f"{title} (+)"
                for rid in g.members_plus:
                    out[int(rid)] = t_plus
            if has_minus:
                t_minus = f"{title} (-)" if (has_plus and has_minus) else f"{title} (-)"
                for rid in g.members_minus:
                    out[int(rid)] = t_minus
        else:
            for rid in g.members_plus:
                out[int(rid)] = title
            for rid in g.members_minus:
                out[int(rid)] = title
    return out


# ==========================================================
# 2) Analiz (özet/aylık/günlük/grup-günlük)
# ==========================================================


@dataclass
class SummaryRow:
    key: str
    pos: float
    neg: float
    net: float
    count: int
    avg: float = 0.0
    max_pos: float = 0.0
    min_neg: float = 0.0


def _parse_iso_date(s: str) -> Optional[datetime]:
    s = (s or '').strip()
    if not s:
        return None

    # Excel seri tarihi (örn. 45687) -> tarih
    try:
        if re.fullmatch(r"\d+(?:\.\d+)?", s):
            n = float(s)
            if 1000 <= n <= 90000:
                base = datetime(1899, 12, 30)
                return base + timedelta(days=int(n))
    except Exception:
        pass

    # KasaPro içinde tarih genelde YYYY-MM-DD
    try:
        return datetime.fromisoformat(s)
    except Exception:
        # Türkçe format dd.mm.yyyy olabilir
        for fmt in ('%d.%m.%Y', '%d/%m/%Y', '%Y-%m-%d'):
            try:
                return datetime.strptime(s, fmt)
            except Exception:
                pass
    return None


def compute_bank_analysis(
    rows: Sequence[Dict[str, object]],
    *,
    group_field: str = "etiket",
    type_field: str = "banka",
) -> Dict[str, List[SummaryRow]]:
    """Bankaya ait analiz tablolarını üretir.

    group_field: grup bazlı özetin hangi alandan yapılacağı (etiket/banka/hesap/belge/...)
    type_field : 'İşlem Tipi Analizi' tablosu için hangi alanın kullanılacağı
    """

    by_group: Dict[str, SummaryRow] = {}
    by_type: Dict[str, SummaryRow] = {}
    by_month: Dict[str, SummaryRow] = {}
    by_day: Dict[str, SummaryRow] = {}
    by_group_day: Dict[str, SummaryRow] = {}

    for r in rows:
        try:
            rid = _as_int(r.get("id"), 0)
            if rid <= 0:
                continue
        except Exception:
            continue

        tip = str(r.get("tip") or "")
        # tutar DB'de +, yön tip'te. UI'de formatlı gelebilir; float parse eden taraf çağırmalı.
        raw_amt = r.get("tutar")
        if isinstance(raw_amt, str):
            try:
                amt = float(raw_amt)
            except Exception:
                try:
                    amt = float(raw_amt.replace(".", "").replace(",", "."))
                except Exception:
                    amt = 0.0
        else:
            amt = _as_float(raw_amt, 0.0)
        amt = abs(amt)
        signed = amt if tip == "Giriş" else -amt
        pos = amt if signed > 0 else 0.0
        neg = signed if signed < 0 else 0.0

        gkey = str(r.get(group_field) or "").strip() or "(Grupsuz)"
        tkey = str(r.get(type_field) or "").strip() or "(Boş)"

        dt = _parse_iso_date(str(r.get("tarih") or ""))
        if not dt:
            continue
        mkey = dt.strftime("%Y-%m")
        dkey = dt.strftime("%Y-%m-%d")
        gdkey = f"{gkey}|{dt.strftime('%Y%m%d')}"

        def upd(d: Dict[str, SummaryRow], key: str):
            if key not in d:
                d[key] = SummaryRow(key=key, pos=0.0, neg=0.0, net=0.0, count=0, max_pos=0.0, min_neg=0.0)
            s = d[key]
            s.pos += pos
            s.neg += neg
            s.net += signed
            s.count += 1
            if pos > 0 and pos > s.max_pos:
                s.max_pos = pos
            if neg < 0 and (s.min_neg == 0.0 or neg < s.min_neg):
                s.min_neg = neg

        upd(by_group, gkey)
        upd(by_type, tkey)
        upd(by_month, mkey)
        upd(by_day, dkey)
        upd(by_group_day, gdkey)

    # Ortalama
    for d in (by_group, by_type, by_month, by_day, by_group_day):
        for s in d.values():
            s.avg = (s.net / s.count) if s.count else 0.0

    out = {
        "groups": sorted(by_group.values(), key=lambda s: (-s.count, s.key.lower())),
        "types": sorted(by_type.values(), key=lambda s: (-abs(s.net), s.key.lower())),
        "months": sorted(by_month.values(), key=lambda s: s.key),
        "days": sorted(by_day.values(), key=lambda s: s.key),
        "group_days": sorted(by_group_day.values(), key=lambda s: (s.key.split("|", 1)[0].lower(), s.key.split("|", 1)[1])),
    }
    return out
