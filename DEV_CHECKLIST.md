# DEV_CHECKLIST

## Çalıştırma
- `python run.py`

## Hızlı smoke test
- `python -m pytest tests/test_smoke.py`

## UI smoke (isteğe bağlı, görsel çıktı üretir)
- `pip install -r requirements-dev.txt`
- `python -m tests.run_ui_smoke`

## Opsiyonel bağımlılıklar
- Excel import/export: `pip install openpyxl`
- PDF export: `pip install reportlab`
- Gelişmiş tablo (opsiyonel): `pip install tksheet`
