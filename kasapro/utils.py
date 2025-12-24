# -*- coding: utf-8 -*-
"""KasaPro v3 - Ortak yardımcı fonksiyonlar

Not: Bu dosya özellikle UI/DB katmanları tarafından yoğun kullanılır.
"""

from __future__ import annotations

import os
import re
import hashlib
import secrets
from datetime import datetime, date, timedelta
from typing import Any, Optional, List, Dict, Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    import tkinter as tk

def today_iso() -> str:
    return date.today().isoformat()

def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def fmt_tr_date(iso: str) -> str:
    try:
        d = datetime.strptime(iso, "%Y-%m-%d").date()
        return d.strftime("%d.%m.%Y")
    except Exception:
        return iso

def norm_header(s: str) -> str:
    s = (s or "").strip().lower()
    tr_map = str.maketrans("çğıöşü", "cgiosu")
    s = s.translate(tr_map)
    s = re.sub(r"\s+", " ", s)
    return s

def parse_date_smart(v: Any) -> str:
    """
    Kabul:
    - datetime/date
    - 'gg.aa.yyyy', 'gg/aa/yyyy', 'gg-aa-yyyy'
    - 'yyyy-mm-dd'
    - Excel seri tarihi: 30000..90000 arası (örn 45687) + 45687.0
    """
    if v is None:
        return today_iso()

    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()

    s = str(v).strip()
    if not s:
        return today_iso()

    # 1) yyyy-mm-dd
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        try:
            datetime.strptime(s, "%Y-%m-%d")
            return s
        except Exception:
            return today_iso()

    # 2) gg.aa.yyyy / gg/aa/yyyy / gg-aa-yyyy
    m = re.fullmatch(r"(\d{1,2})[./-](\d{1,2})[./-](\d{4})", s)
    if m:
        dd, mm, yyyy = m.groups()
        try:
            return date(int(yyyy), int(mm), int(dd)).isoformat()
        except Exception:
            return today_iso()

    # 3) Excel serial (string or numeric-like string: 45687 / 45687.0 / 45687,0)
    m = re.fullmatch(r"(\d+)(?:[.,]\d+)?", s)
    if m:
        try:
            serial = int(float(s.replace(",", ".")))
            if 30000 <= serial <= 90000:
                base = date(1899, 12, 30)
                return (base + timedelta(days=serial)).isoformat()
        except Exception:
            pass

    # 4) numeric directly
    if isinstance(v, (int, float)):
        try:
            serial = int(float(v))
            if 30000 <= serial <= 90000:
                base = date(1899, 12, 30)
                return (base + timedelta(days=serial)).isoformat()
        except Exception:
            pass

    return today_iso()

def parse_number_smart(v: Any) -> float:
    """Sayı/para değeri ayrıştırır (TR/EN noktalama + birim ekleri).

    Desteklenen örnekler:
    - 1234,56 / 1234.56
    - 1.234,56 / 1,234.56 / 1 234,56
    - (1.234,56)  -> negatif
    - 125kr / 125 kuruş  -> 1.25 (kuruş => /100)
    - 18% / yüzde 18     -> 0.18
    - 18‰ / binde 18     -> 0.018
    - 10 ppm / milyonda 10 -> 0.00001

    Not: Tek başına "1.234" ifadesi belirsiz olabilir; bu fonksiyon bunu ondalık (1.234) olarak kabul eder.
    """
    try:
        if v is None:
            return 0.0
        if isinstance(v, (int, float)):
            return float(v)

        s = str(v).strip()
        if not s:
            return 0.0

        # Negatif parantez (muhasebe formatı): (1.234,56)
        neg = False
        if s.startswith("(") and s.endswith(")"):
            neg = True
            s = s[1:-1].strip()

        mult = 1.0
        sl = s.lower()

        # Para birimleri / semboller (yoksay)
        s = re.sub(r"(?i)\b(tl|try|usd|eur)\b", "", s)
        s = s.replace("₺", "").replace("$", "").replace("€", "")

        # Kuruş / kr
        if re.search(r"(?i)(\bkr\b|\bkuruş\b|\bkurus\b|kr\s*$)", s):
            mult *= 0.01
            s = re.sub(r"(?i)\b(kuruş|kurus|kr)\b", "", s).strip()
            s = re.sub(r"(?i)kr\s*$", "", s).strip()

        # Yüzde
        if "%" in s or re.search(r"(?i)\b(yuzde|yüzde)\b", s):
            mult *= 0.01
            s = s.replace("%", "")
            s = re.sub(r"(?i)\b(yuzde|yüzde)\b", "", s)

        # Binde
        if "‰" in s or re.search(r"(?i)\b(binde)\b", s):
            mult *= 0.001
            s = s.replace("‰", "")
            s = re.sub(r"(?i)\b(binde)\b", "", s)

        # Onbinde (‱) / on binde
        if "‱" in s or re.search(r"(?i)\b(on\s*binde|onbinde)\b", s):
            mult *= 0.0001
            s = s.replace("‱", "")
            s = re.sub(r"(?i)\b(on\s*binde|onbinde)\b", "", s)


        # Milyonda (ppm)
        if re.search(r"(?i)\b(ppm|milyonda)\b", s):
            mult *= 1e-6
            s = re.sub(r"(?i)\b(ppm|milyonda)\b", "", s)

        s = s.strip().replace("\u00A0", "")

        # İçinden sayı yakala
        m = re.search(r"[-+]?\d[\d\s.,'_]*", s)
        if not m:
            return 0.0
        num = m.group(0)
        num = num.replace(" ", "").replace("_", "").replace("'", "")

        # Hem . hem , varsa: sağdaki ondalık kabul edilir, diğeri binlik ayırıcı sayılır
        if "." in num and "," in num:
            if num.rfind(".") > num.rfind(","):
                dec = "."
                thou = ","
            else:
                dec = ","
                thou = "."
            num = num.replace(thou, "")
            num = num.replace(dec, ".")
        elif "," in num:
            # Çoklu virgülde: son virgül ondalık, diğerleri binlik
            if num.count(",") > 1:
                parts = num.split(",")
                num = "".join(parts[:-1]) + "." + parts[-1]
            else:
                num = num.replace(",", ".")
            # Nokta sayısı >1 olduysa (garip veri), yine son nokta ondalık kalsın
            if num.count(".") > 1:
                parts = num.split(".")
                num = "".join(parts[:-1]) + "." + parts[-1]
        elif "." in num:
            # Sadece nokta var (TR'de binlik ayırıcı da olabilir).
            # Eğer sayı "1.234.567" gibi binlik gruplamaya benziyorsa noktaları kaldır.
            if re.fullmatch(r"[-+]?\d{1,3}(?:\.\d{3})+", num) and not re.match(r"[-+]?0\.", num):
                num = num.replace(".", "")
            else:
                # Çoklu noktada: son nokta ondalık, diğerleri binlik
                if num.count(".") > 1:
                    parts = num.split(".")
                    num = "".join(parts[:-1]) + "." + parts[-1]
                # Tek nokta -> ondalık olarak bırakılır (1.234 => 1.234)

        val = float(num) * mult
        if neg:
            val = -val
        return val
    except Exception:
        return 0.0

def safe_float(v: Any) -> float:
    # Geriye dönük uyumluluk
    return parse_number_smart(v)

def fmt_amount(v: Any, min_dec: int = 2, max_dec: int = 6) -> str:
    """Tutarı TR formatında gösterir: binlik '.' ve ondalık ','.
    En az min_dec, gerekirse 3-6 ondalık. Örn: 1234567.89 -> 1.234.567,89
    """
    try:
        # float( "1.234,56" ) çalışmaz; bu yüzden akıllı parser kullan
        x = parse_number_smart(v)
    except Exception:
        try:
            x = float(v)
        except Exception:
            return str(v)

    neg = x < 0
    ax = abs(x)

    # Önce EN formatında (1,234,567.890000) üret, sonra TR'ye çevir
    s = f"{ax:,.{max_dec}f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")

    # En az min_dec basamak göster
    if min_dec > 0:
        if "." not in s:
            s = f"{ax:,.{min_dec}f}"
        else:
            dec_len = len(s.split(".", 1)[1])
            if dec_len < min_dec:
                s = s + ("0" * (min_dec - dec_len))

    # TR ayırıcılarına dönüştür: 1,234,567.89 -> 1.234.567,89
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")

    if neg and ax != 0:
        s = "-" + s
    return s


def make_salt() -> str:
    return secrets.token_hex(16)

def hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()

def center_window(win: Any, parent: Optional[Any] = None):
    """Pencereyi ekrana (veya parent'a) ortalar.

    Not: Tk'te henüz ekrana 'map' olmamış pencerelerde winfo_width/height çoğu zaman 1 döner.
    Bu yüzden <=1 ise reqwidth/reqheight'e düşeriz (aksi halde pencere 1x1 olup görünmeyebilir).
    """
    try:
        win.update_idletasks()

        w = win.winfo_width()
        h = win.winfo_height()
        if w <= 1:
            w = win.winfo_reqwidth()
        if h <= 1:
            h = win.winfo_reqheight()

        # Parent görünmüyorsa (withdraw/minimize vb.), ekran ortalamasına dön.
        try:
            if parent is not None and hasattr(parent, "winfo_viewable"):
                if not bool(parent.winfo_viewable()):
                    parent = None
        except Exception:
            parent = None

        if parent is not None:
            parent.update_idletasks()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            if pw <= 1:
                pw = parent.winfo_reqwidth()
            if ph <= 1:
                ph = parent.winfo_reqheight()
            x = px + (pw - w) // 2
            y = py + (ph - h) // 2
        else:
            sw = win.winfo_screenwidth()
            sh = win.winfo_screenheight()
            x = (sw - w) // 2
            y = (sh - h) // 2

        win.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")
    except Exception:
        pass

# =========================
# DB
# =========================


# ==========================================================
# PDF FONT (TÜRKÇE KARAKTERLER İÇİN)
# ==========================================================
def ensure_pdf_fonts():
    """
    ReportLab standart fontları (Helvetica/Times) bazı sistemlerde Türkçe karakterleri
    (ı, İ, ş, Ş, ğ, Ğ, ö, Ö, ü, Ü, ç, Ç) eksik gösterir. PDF içine Unicode TTF font
    gömerek sorunu çözer.

    Dönüş: (regular_font_name, bold_font_name)
    """
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except Exception:
        return ("Helvetica", "Helvetica-Bold")

    cached = getattr(ensure_pdf_fonts, "_cached", None)
    if cached:
        return cached

    import os

    def _try_register(font_base, regular_path, bold_path=None):
        try:
            if font_base not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(font_base, regular_path))
            bold_name = font_base
            if bold_path and os.path.exists(bold_path):
                bold_name = font_base + "-Bold"
                if bold_name not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont(bold_name, bold_path))
            ensure_pdf_fonts._cached = (font_base, bold_name)
            return ensure_pdf_fonts._cached
        except Exception:
            return None

    # Aranacak dizinler
    search_dirs = []
    try:
        search_dirs.append(os.path.dirname(__file__))
    except Exception:
        pass
    search_dirs.extend([os.getcwd()])

    # Windows font dizini
    win_fonts = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")
    if os.path.isdir(win_fonts):
        search_dirs.append(win_fonts)

    # Linux/Mac olası dizinler
    for d in [
        "/usr/share/fonts", "/usr/local/share/fonts",
        "/usr/share/fonts/truetype", "/usr/share/fonts/truetype/dejavu",
        "/Library/Fonts", os.path.expanduser("~/Library/Fonts")
    ]:
        if os.path.isdir(d):
            search_dirs.append(d)

    def find_font_file(filenames):
        for d in search_dirs:
            for fn in filenames:
                p = os.path.join(d, fn)
                if os.path.exists(p):
                    return p
        return None

    # Öncelik: DejaVu → Arial → Liberation/Noto
    candidates = [
        ("DejaVuSans",
         ["DejaVuSans.ttf", "dejavusans.ttf"],
         ["DejaVuSans-Bold.ttf", "dejavusans-bold.ttf", "DejaVuSansBold.ttf"]),
        ("Arial",
         ["arial.ttf", "Arial.ttf"],
         ["arialbd.ttf", "Arial Bold.ttf", "Arialbd.ttf"]),
        ("LiberationSans",
         ["LiberationSans-Regular.ttf", "LiberationSans.ttf"],
         ["LiberationSans-Bold.ttf"]),
        ("NotoSans",
         ["NotoSans-Regular.ttf", "NotoSans.ttf"],
         ["NotoSans-Bold.ttf"]),
    ]

    for base, reg_list, bold_list in candidates:
        reg = find_font_file(reg_list)
        if not reg:
            continue
        bold = find_font_file(bold_list)
        out = _try_register(base, reg, bold)
        if out:
            return out

    ensure_pdf_fonts._cached = ("Helvetica", "Helvetica-Bold")
    return ensure_pdf_fonts._cached

def _safe_slug(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_\-]", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "user"
