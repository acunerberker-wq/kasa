# KasaPro v3 (Pro Modüler)

Bu paket; tek dosyadan çıkarılıp **modül/repository** mantığıyla bölünmüş, sonradan geliştirmesi daha kolay bir iskelet sunar.

## Çalıştırma

Bu klasörde:

- `python run.py` (önerilen)
- veya `python -m kasapro`

## Config

Aynı klasördeki `kasapro.ini` ile data/log konumlarını ve log seviyesini değiştirebilirsin.

- `KASAPRO_HOME` environment variable set edersen, data/log dosyaları oraya yazılır.

## Loglama

`logs/kasapro.log` dosyasına döner (RotatingFile: 5MB x 3). Log dizini `kasapro.ini` ile değiştirilebilir.

## Opsiyonel bağımlılıklar

- Excel import/export: `pip install openpyxl`
- PDF export: `pip install reportlab`

## Excel Çalışma Alanı (Banka)

Banka ekranındaki tablo kısmında:

- **📤 Excel'e Aktar**: Görüntülenen satırları `.xlsx` olarak kaydeder
- **🟩 Excel'de Aç**: Dışarı `.xlsx` çıkarıp Excel'de açar
- **🔄 Excel'den Güncelle**: Excel'de yaptığın değişiklikleri **ID bazlı** geri alır (sonra **💾 Değişiklikleri Kaydet** ile DB'ye yazılır)

Notlar:
- Excel'de ilk satır **başlık** olmalı ve `id` kolonu bulunmalı.
- Excel'de yeni satır eklediysen uygulama otomatik oluşturmaz; mevcut `id`'leri günceller.

## Proje Yapısı

- `kasapro/core/`
  - `version.py`: sürüm
  - `logging.py`: log altyapısı
- `kasapro/config.py`: varsayılanlar + `kasapro.ini` override
- `kasapro/utils.py`: tarih/para/format yardımcıları
- `kasapro/db/`
  - `connection.py`: sqlite bağlantısı
  - `schema.py`: şema + migrasyon + seed
  - `repos/`: repository katmanı (`cariler_repo.py`, `kasa_repo.py`, ...)
  - `main_db.py`: UI’nın kullandığı DB façade (repo’lara delegasyon)
  - `users_db.py`: giriş/kullanıcı/şirket yönetimi DB’si
- `kasapro/ui/`
  - `style.py`, `widgets.py`, `dialogs.py`, `windows.py`
  - `frames/`: her sekme **ayrı dosya** (`kasa.py`, `cariler.py`, ...)
- `kasapro/app.py`: App sınıfı ve main()
