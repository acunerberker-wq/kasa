# KasaPro - Copilot Yönergeleri

## Proje Özeti
KasaPro, Türk işletmeleri için Tkinter + SQLite tabanlı modüler bir muhasebe/kasa uygulamasıdır. Çok şirketli mimari, kullanıcı yönetimi ve mesajlaşma sistemini destekler.

## Mimari

### Katmanlı Yapı
```
kasapro/
├── db/repos/         # Repository katmanı (SQLite CRUD)
├── db/main_db.py     # DB façade - UI'nın tek erişim noktası
├── services/         # İş mantığı (repo'ları kullanır)
├── ui/frames/        # Sekme içerikleri (her ekran ayrı dosya)
├── modules/          # Bağımsız modüller (hakedis, dms, invoice...)
└── config.py         # Tüm yapılandırma + kasapro.ini override
```

### Veri Akışı
1. **UI Frame** → `app.services.X` çağırır
2. **Service** → `DB` façade veya doğrudan `Repo` kullanır
3. **Repo** → SQLite bağlantısı ile CRUD işlemleri

### Kritik Dosyalar
- [kasapro/app.py](kasapro/app.py) - Ana uygulama, login, şirket seçimi
- [kasapro/services/context.py](kasapro/services/context.py) - `Services.build()` ile tüm servisler oluşturulur
- [kasapro/db/schema.py](kasapro/db/schema.py) - Tablo tanımları + migrasyon + seed

## Geliştirici Komutları

```bash
# Uygulamayı başlat
python run.py

# Hızlı doğrulama
python -m kasapro.self_check
python -m kasapro.self_check --ui  # Tkinter kontrolü dahil

# Testler
python -m pytest tests/test_smoke.py
python -m tests.smoke_test

# Profiling
python tools/bench_startup.py
python tools/profile_startup.py
```

## Kodlama Kuralları

### Repository Pattern
Yeni veri erişimi eklerken:
1. `kasapro/db/repos/` altına `xxx_repo.py` oluştur
2. `__init__.py`'ye ekle
3. `main_db.py`'de repo'yu başlat ve façade metodları ekle

```python
# Örnek: kasapro/db/repos/cariler_repo.py
class CarilerRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
    
    def list(self, q: str = "", *, only_active: bool = False) -> List[sqlite3.Row]:
        ...
    def upsert(self, ad: str, ...) -> int:
        ...
```

### UI Frame Pattern
Yeni ekran eklerken `kasapro/ui/frames/` altına dosya oluştur:

```python
from ..base import BaseView

class MyFrame(BaseView):
    def __init__(self, parent, controller, **kw):
        super().__init__(parent, controller, **kw)
        self.build_ui()
    
    def build_ui(self) -> None:
        ...
    
    def refresh(self, data=None) -> None:
        ...
```

### Servis Pattern
İş mantığı için `kasapro/services/` veya `kasapro/modules/X/service.py`:

```python
class MyService:
    def __init__(self, db: DB, exporter: ExportService = None):
        self.db = db
        self.exporter = exporter
```

## Proje Spesifik Kurallar

### TR Formatları
- Tarih: `gg.mm.yyyy` (ISO dahili: `yyyy-mm-dd`)
- Para: `1.234.567,89` (nokta binlik, virgül ondalık)
- `kasapro/utils.py` içindeki `fmt_amount()`, `parse_number_smart()`, `parse_date_smart()` kullan

### Widget'lar
Para girişi için özel `MoneyEntry` widget'ı kullan (`kasapro/ui/widgets.py`). Otomatik TR formatlaması yapar.

### Çok Şirketli Yapı
- Her şirketin ayrı SQLite DB'si var
- `UsersDB`: kullanıcı/şirket yönetimi (kasa_users.db)
- `DB`: aktif şirket verisi (şirket_adi.db)

### Opsiyonel Bağımlılıklar
```python
from kasapro.config import HAS_OPENPYXL, HAS_REPORTLAB
if HAS_OPENPYXL:
    # Excel import/export
if HAS_REPORTLAB:
    # PDF export
```

### Logging
UI olayları için `log_ui_event()` kullan:
```python
from kasapro.ui.ui_logging import log_ui_event
log_ui_event("button_click", view="KasaFrame", action="save")
```

## Test Yazma

```python
# tests/test_*.py
class TestMyFeature(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db = DB(os.path.join(self.tmpdir.name, "test.db"))
    
    def tearDown(self):
        self.db.close()
        self.tmpdir.cleanup()
```

## Modül Ekleme
Yeni bağımsız modül için `kasapro/modules/mymodule/`:
- `repo.py` - Veritabanı işlemleri
- `service.py` - İş mantığı
- `ui.py` - Tkinter bileşenleri (opsiyonel)

Sonra `Services` dataclass'ına ekle (`kasapro/services/context.py`).
