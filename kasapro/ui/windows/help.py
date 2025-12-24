# -*- coding: utf-8 -*-
"""KasaPro v3 - Yardım penceresi."""

from __future__ import annotations

from typing import List, Tuple

import tkinter as tk
from tkinter import ttk

from ...utils import center_window

def _tr_norm(s: str) -> str:
    """Arama için TR-dostu normalizasyon (I/İ davranışı dahil)."""
    s = "" if s is None else str(s)
    s = s.replace("I", "ı").replace("İ", "i")
    return s.lower()

HELP_TOPICS: List[Tuple[str, str]] = [
    ("Genel Bakış",
"""KasaPro; Kasa hareketleri, Cariler ve Cari Hareketleri tek bir veritabanında tutar.
Sol menüden ekranlar arasında geçiş yapabilirsin.

Roller:
- admin: silme/düzenleme, DB geri yükleme, kullanıcı yönetimi gibi yetkiler.
- user: kayıt ekleme/görüntüleme (bazı kritik işlemler kapalı olabilir).

Kısayollar:
- F1: Yardım penceresini açar.
"""),

    ("Navigasyon ve Genel Mantık",
"""Sol menüdeki ana ekranlar:
- 📚 Tanımlar: Cariler / Çalışanlar / Meslekler gibi tanım verileri
- 🏦 Kasa: gelir/gider kayıtları + geçmiş + cari hareketleri
- 📈 Rapor & Araçlar: Raporlar + Global Arama + Log

⚙️ Ayarlar içinde:
- Şirketler: şirket oluştur/seç (aktif şirketi buradan değiştirebilirsin)
- Kullanıcılar: (admin) kullanıcı yönetimi

Her ekranda:
- Üst bölüm: kayıt ekleme / düzenleme formu
- Alt bölüm: kayıt listesi (filtre/arama + tablo)
"""),

    ("Tutar Girişi (TR Para Formatı)",
"""Programdaki tüm tutar girişleri TR formatını kullanır.

Örnek gösterim:
- 1111111  -> 1.111.111,00
- 100,32   -> 100,32
- 1.234,50 -> 1.234,50

Nasıl yazılır?
- Tam kısmı yaz: 1250 => 1.250,00
- Kuruş yazmak için ',' (veya '.') tuşla: 1250,75
- Yazarken otomatik nokta/virgül maskelemesi yapılır.
- Enter veya alandan çıkınca (focus out) format kesinleşir.

İpucu:
- Binlik ayıracı olarak '.' kullanılır.
- Ondalık ayıracı olarak ',' kullanılır.
"""),

    ("Kasa Ekranı",
"""Kasa; gelir ve gider kayıtlarının tutulduğu ana ekrandır.

İşlem ekleme:
- Tarih / Tip (Gelir-Gider) / Tutar / Para / Ödeme / Kategori / Cari (opsiyonel)
- Belge No ve Etiket alanlarıyla kayıtlarını sınıflandırabilirsin.
- Açıklama alanı bir butondur: 'Açıklama yaz…' → sekmeli pencerede yaz.

Kayıt listesi:
- Gelir/Gider kayıtlarının tamamı listelenir.
- Çift tık: Seçili kaydı düzenle (admin)
- Seçili Kaydı Düzenle / Sil (admin)

Kaydet sonrası:
- Yeni kayıt için form temizlenir (açıklama dahil).
"""),

    ("Şirket Diğer Giderler",
"""Bu ekran; cari ile ilişkilendirmeden (cari seçmeden) gider girmek içindir.

- Tip otomatik olarak "Gider" kabul edilir.
- Kayıtlar kasa_hareket tablosunda tutulur fakat sadece cari_id boş olanlar gösterilir.
- "Gider Hesabı" alanı kategori listesini kullanır.
"""),

    ("Cari Hareket Ekranı",
"""Cari Hareket Ekle:
- Tarih / Cari / Tip (Borç-Alacak) / Tutar / Para / Ödeme / Belge / Etiket
- Açıklama: butona basarak sekmeli pencereden girilir.

Çoklu seçim:
- 'Çoklu Seçim: Açık' iken satırlara tek tek tıklayarak çoklu seçebilirsin.
- 'Seçili Kaydı Sil' çoklu seçimde hepsini siler (admin).

Düzenleme:
- Düzenleme için tek kayıt seçili olmalıdır (admin).
- Çift tık: seçili kaydı düzenle (admin).
"""),

    ("Cariler Ekranı",
"""Cari kartı:
- Cari Adı (zorunlu), Tür, Telefon, Notlar
- Açılış Bakiyesi: TR para formatındadır.

İşlemler:
- Kaydet: yeni cari ekler / seçili cari üzerinde günceller
- Sil: admin yetkisiyle çalışır

Not:
- Bir cariyi silmek için ilişkili hareketler varsa önce hareketleri temizlemek gerekebilir.
"""),

    ("Açıklama Sekmesi (Buton)",
"""Kasa ve Cari Hareket ekranlarında Açıklama alanı butondur.

Kullanım:
- 'Açıklama yaz…' butonuna bas → sekmeli pencere açılır.
- Metni yaz → 'Uygula' veya 'Uygula & Kapat' ile forma aktarılır.
- Kaydet dedikten sonra yeni kayıt için açıklama otomatik temizlenir.
- Pencere ekranın ortasında açılır.
"""),

    ("Excel İçe Aktar / Export",
"""Excel İçe Aktar:
- openpyxl kurulu olmalı: pip install openpyxl
- Dosya seçilir → Eşleştirme Sihirbazı açılır
- Her tablo için sheet ve kolon eşleştirmesi yapılır
- 'Cari yoksa otomatik oluştur' seçeneği ile eksik cariler otomatik eklenebilir.

Excel Export:
- Veriler yeni bir Excel dosyasına aktarılır.
"""),

    ("PDF Dışa Aktarım (Türkçe Karakter)",
"""PDF'te Türkçe karakterler bozuluyorsa:
- PDF çıktısı için Unicode font gömme kullanılır (DejaVuSans/Arial vb.).
- Eğer sistemde uygun font bulunamazsa metinde kare/bozuk karakter görülebilir.

Çözüm:
- Windows'ta genelde Arial bulunduğundan otomatik düzelir.
- Gerekirse DejaVuSans.ttf dosyasını programın yanına koyabilirsin.
"""),

    ("DB Yedek / Geri Yükle",
"""DB Yedek:
- '💾 DB Yedek' butonu mevcut giriş yapılan kullanıcının veritabanını kopyalar.

DB Geri Yükle:
- Mevcut giriş yapılan kullanıcının DB'sinin üstüne yazar (geri dönüşü zordur). Önce yedek önerilir.
"""),

    ("Kullanıcılar (Çoklu Kullanıcı)",
"""- Giriş ekranında kullanıcı seçip şifreyle giriş yaparsın.
- Her kullanıcının verileri ayrı tutulur: kasa_data/ klasöründe kullanıcıya özel .db dosyası.
- Sadece admin: Sol menüde "👤 Kullanıcılar" bölümünden kullanıcı ekle/sil ve şifre sıfırla.
- "💾 DB Yedek" / "♻️ DB Geri Yükle" işlemleri mevcut giriş yapılan kullanıcının verisini etkiler.
"""),

    ("Sık Sorulanlar",
"""S: Tutar yazarken neden otomatik değişiyor?
C: Para girişleri TR formatında maskelenir; bu yanlış girişi azaltır.

S: Silme/Düzenleme butonları pasif.
C: Admin hesabıyla giriş yapmalısın.

S: Excel import görünmüyor.
C: openpyxl kurulu değilse import/export devre dışı kalır.

S: PDF'te Türkçe karakter bozuk.
C: Unicode font gömme ayarı gerekir (programda otomatik denenir).
"""),
]

class HelpWindow(tk.Toplevel):
    def __init__(self, app: "App"):
        super().__init__(app.root)
        self.app = app
        self.title("Yardım")
        self.geometry("980x640")
        self.minsize(820, 520)
        try:
            self.transient(app.root)
        except Exception:
            pass

        self._all_topics = HELP_TOPICS[:]
        self._topics_view: List[Tuple[str, str]] = self._all_topics[:]
        self._current_topic_index: int = 0
        self._last_find_index: str = "1.0"

        self._build()
        center_window(self, app.root)

    def _build(self):
        top = ttk.Frame(self); top.pack(fill=tk.X, padx=12, pady=10)

        ttk.Label(top, text="Yardım", font=("Calibri", 14, "bold")).pack(side=tk.LEFT)
        ttk.Label(top, text=f"  (Kullanıcı: {self.app.user['username']} / {self.app.user['role']})", foreground="#666").pack(side=tk.LEFT)

        self.var_q = tk.StringVar()
        ent = ttk.Entry(top, textvariable=self.var_q, width=42)
        ent.pack(side=tk.RIGHT, padx=(6, 0))
        ent.bind("<Return>", lambda _e: self.search())
        ttk.Button(top, text="Ara", command=self.search).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(top, text="Temizle", command=self.clear_search).pack(side=tk.RIGHT, padx=(6, 12))

        self.lbl_status = ttk.Label(self, text="", foreground="#666")
        self.lbl_status.pack(fill=tk.X, padx=12, pady=(0, 6))

        pw = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        pw.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        left = ttk.Frame(pw); right = ttk.Frame(pw)
        pw.add(left, weight=1)
        pw.add(right, weight=3)

        # Sol: konu listesi
        ttk.Label(left, text="Konular").pack(anchor="w", padx=6, pady=(6, 2))
        self.lb = tk.Listbox(left, height=18)
        sb = ttk.Scrollbar(left, orient="vertical", command=self.lb.yview)
        self.lb.configure(yscrollcommand=sb.set)
        self.lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6,0), pady=6)
        sb.pack(side=tk.RIGHT, fill=tk.Y, pady=6)

        self.lb.bind("<<ListboxSelect>>", self._on_select_topic)

        # Sağ: içerik + arama içinde gezinme
        nav = ttk.Frame(right); nav.pack(fill=tk.X, padx=6, pady=(6, 0))
        ttk.Button(nav, text="Önceki", command=lambda: self.find_next(backwards=True)).pack(side=tk.LEFT)
        ttk.Button(nav, text="Sonraki", command=lambda: self.find_next(backwards=False)).pack(side=tk.LEFT, padx=6)
        ttk.Button(nav, text="Kopyala", command=self.copy_current).pack(side=tk.RIGHT)

        self.txt = tk.Text(right, wrap="word")
        ysb = ttk.Scrollbar(right, orient="vertical", command=self.txt.yview)
        self.txt.configure(yscrollcommand=ysb.set)
        self.txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6,0), pady=6)
        ysb.pack(side=tk.RIGHT, fill=tk.Y, pady=6)

        self.txt.tag_configure("h", font=("Calibri", 13, "bold"))
        self.txt.tag_configure("hl", background="#ffe08a")

        self._reload_list()
        self._show_topic(0)

        # kısayol
        try:
            self.bind("<Escape>", lambda _e: self.destroy())
        except Exception:
            pass

    def _reload_list(self):
        self.lb.delete(0, tk.END)
        for title, _body in self._topics_view:
            self.lb.insert(tk.END, title)
        if self._topics_view:
            self.lb.selection_clear(0, tk.END)
            self.lb.selection_set(0)
            self.lb.activate(0)

    def _on_select_topic(self, _e=None):
        sel = self.lb.curselection()
        if not sel:
            return
        self._show_topic(int(sel[0]))

    def _show_topic(self, idx: int):
        if not self._topics_view:
            return
        idx = max(0, min(idx, len(self._topics_view)-1))
        self._current_topic_index = idx
        title, body = self._topics_view[idx]

        self.txt.configure(state="normal")
        self.txt.delete("1.0", tk.END)
        self.txt.insert("1.0", title + "\n", ("h",))
        self.txt.insert("end", "\n" + body.strip() + "\n")
        self.txt.configure(state="disabled")

        self._last_find_index = "1.0"
        self._apply_highlight()

        # status
        q = self.var_q.get().strip()
        if q:
            self.lbl_status.config(text=f"Arama: '{q}'  |  Konu: {title}")
        else:
            self.lbl_status.config(text=f"Konu: {title}")

    def _apply_highlight(self):
        q = self.var_q.get().strip()
        self.txt.configure(state="normal")
        self.txt.tag_remove("hl", "1.0", tk.END)
        if q:
            start = "1.0"
            while True:
                pos = self.txt.search(q, start, stopindex=tk.END, nocase=True)
                if not pos:
                    break
                end = f"{pos}+{len(q)}c"
                self.txt.tag_add("hl", pos, end)
                start = end
        self.txt.configure(state="disabled")

    def search(self):
        q = self.var_q.get().strip()
        if not q:
            self.clear_search()
            return

        nq = _tr_norm(q)
        filtered = []
        for title, body in self._all_topics:
            if nq in _tr_norm(title) or nq in _tr_norm(body):
                filtered.append((title, body))

        self._topics_view = filtered if filtered else []
        self._reload_list()

        if not self._topics_view:
            self.lbl_status.config(text=f"'{q}' için sonuç bulunamadı.")
            self.txt.configure(state="normal")
            self.txt.delete("1.0", tk.END)
            self.txt.insert("1.0", "Sonuç bulunamadı. Aramayı değiştir veya 'Temizle'ye bas.")
            self.txt.configure(state="disabled")
            return

        self.lbl_status.config(text=f"'{q}' için {len(self._topics_view)} konu bulundu.")
        self._show_topic(0)

    def clear_search(self):
        self.var_q.set("")
        self._topics_view = self._all_topics[:]
        self._reload_list()
        self.lbl_status.config(text="")
        self._show_topic(0)

    def find_next(self, backwards: bool = False):
        q = self.var_q.get().strip()
        if not q:
            return

        self.txt.configure(state="normal")
        try:
            if backwards:
                pos = self.txt.search(q, self._last_find_index, stopindex="1.0", nocase=True, backwards=True)
            else:
                pos = self.txt.search(q, self._last_find_index, stopindex=tk.END, nocase=True)
            if not pos:
                # sar
                pos = self.txt.search(q, tk.END if backwards else "1.0", stopindex="1.0" if backwards else tk.END, nocase=True, backwards=backwards)
            if pos:
                end = f"{pos}+{len(q)}c"
                self.txt.tag_remove("sel", "1.0", tk.END)
                self.txt.tag_add("sel", pos, end)
                self.txt.mark_set(tk.INSERT, end)
                self.txt.see(pos)
                self._last_find_index = pos
        finally:
            self.txt.configure(state="disabled")

    def copy_current(self):
        try:
            sel = self.lb.curselection()
            idx = int(sel[0]) if sel else 0
            title, body = self._topics_view[idx]
            txt = f"{title}\n\n{body}"
            self.clipboard_clear()
            self.clipboard_append(txt)
            self.update_idletasks()
            self.lbl_status.config(text="Kopyalandı.")
        except Exception:
            pass

# =========================
