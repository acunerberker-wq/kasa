# -*- coding: utf-8 -*-
"""Repo audit: structure, imports, config, and UI entrypoints.

Writes REPORT.md at repo root.
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path
from typing import Dict, List


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = REPO_ROOT / "REPORT.md"


def _check_paths() -> Dict[str, bool]:
    required = {
        "run.py": (REPO_ROOT / "run.py").exists(),
        "kasapro/app.py": (REPO_ROOT / "kasapro" / "app.py").exists(),
        "kasapro/ui": (REPO_ROOT / "kasapro" / "ui").is_dir(),
        "tests": (REPO_ROOT / "tests").is_dir(),
        "logs": (REPO_ROOT / "logs").is_dir(),
        "config (kasapro.ini)": (REPO_ROOT / "kasapro.ini").exists(),
    }
    return required


def _check_imports() -> Dict[str, str]:
    results: Dict[str, str] = {}
    for mod in ("kasapro", "kasapro.app", "kasapro.ui", "kasapro.db"):
        try:
            importlib.import_module(mod)
            results[mod] = "ok"
        except Exception as exc:
            results[mod] = f"fail: {exc}"
    return results


def _check_ui_routes() -> Dict[str, str]:
    results: Dict[str, str] = {}
    try:
        app_mod = importlib.import_module("kasapro.app")
        App = getattr(app_mod, "App", None)
        if App is None:
            results["App"] = "missing"
            return results
        app = App(test_mode=True)
        for key in ("kasa", "tanimlar", "rapor_araclar", "satis_raporlari", "entegrasyonlar"):
            results[key] = "ok" if key in getattr(app, "frames", {}) else "missing"
        try:
            app.on_close()
        except Exception:
            pass
    except Exception as exc:
        results["App"] = f"fail: {exc}"
    return results


def main() -> None:
    structure = _check_paths()
    imports = _check_imports()
    ui_routes = _check_ui_routes()

    lines: List[str] = []
    lines.append("# REPORT")
    lines.append("")
    lines.append("## Structure")
    for key, ok in structure.items():
        lines.append(f"- {key}: {'OK' if ok else 'MISSING'}")
    lines.append("")
    lines.append("## Imports")
    for key, status in imports.items():
        lines.append(f"- {key}: {status}")
    lines.append("")
    lines.append("## UI Routes")
    for key, status in ui_routes.items():
        lines.append(f"- {key}: {status}")
    lines.append("")
    lines.append("## Fixes Applied")
    lines.append("- None (audit only).")

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
