# DEV CHECKLIST (KasaPro)

## Çalıştırma
- `python run.py`
- Alternatif: `python -m kasapro`

## Opsiyonel Bağımlılıklar
- Excel import/export: `pip install .[excel]`
- PDF export: `pip install .[pdf]`
- UI tabloları (opsiyonel): `pip install .[ui]`

## Hızlı Kontrol
- `python -m kasapro.self_check`
- UI kontrolü için: `python -m kasapro.self_check --ui`

## Smoke Test
- `python -m pytest tests/test_smoke.py`
- `python -m tests.smoke_test`

## Profiling / Benchmark
- Startup + ekran açılış süreleri: `python tools/bench_startup.py`
- Startup profil (ilk 5 fonksiyon): `python tools/profile_startup.py`

## Repo Audit
- `python tools/repo_audit.py`
