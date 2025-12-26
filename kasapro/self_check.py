# -*- coding: utf-8 -*-
"""KasaPro hızlı doğrulama (self-check) komutu."""

from __future__ import annotations

import argparse
import logging
import tempfile
from dataclasses import dataclass
from typing import List

import tkinter as tk

from .config import APP_BASE_DIR, LOG_DIRNAME
from .core.logging import setup_logging
from .db.main_db import DB


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str = ""


def _can_start_tk() -> bool:
    try:
        root = tk.Tk()
        root.withdraw()
        root.update_idletasks()
        root.destroy()
        return True
    except tk.TclError:
        return False


def run_checks(check_ui: bool = False) -> List[CheckResult]:
    results: List[CheckResult] = []
    logger = logging.getLogger(__name__)

    try:
        log_path = setup_logging(APP_BASE_DIR, log_dirname=LOG_DIRNAME)
        results.append(CheckResult("logging", True, log_path))
    except Exception as exc:
        results.append(CheckResult("logging", False, str(exc)))

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = DB(f"{tmpdir}/self_check.db")
            row = db.conn.execute("SELECT 1").fetchone()
            db.close()
            ok = bool(row and row[0] == 1)
            results.append(CheckResult("db", ok, "sqlite ok" if ok else "query failed"))
    except Exception as exc:
        logger.exception("DB self-check failed")
        results.append(CheckResult("db", False, str(exc)))

    if check_ui:
        if _can_start_tk():
            results.append(CheckResult("ui", True, "Tkinter ok"))
        else:
            results.append(CheckResult("ui", False, "Tkinter başlatılamadı (headless?)"))

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="KasaPro hızlı doğrulama komutu")
    parser.add_argument("--ui", action="store_true", help="Tkinter başlatma kontrolünü de yap")
    args = parser.parse_args()

    results = run_checks(check_ui=args.ui)
    failed = [r for r in results if not r.ok]
    for res in results:
        status = "OK" if res.ok else "FAIL"
        detail = f" - {res.detail}" if res.detail else ""
        print(f"[{status}] {res.name}{detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
