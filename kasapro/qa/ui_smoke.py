# -*- coding: utf-8 -*-
"""UI smoke test runner for KasaPro (Tkinter)."""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import tkinter as tk
from tkinter import ttk

from ..app import App

try:
    from tests.report import write_report
except Exception:  # pragma: no cover - runner still works without report module
    write_report = None  # type: ignore


SAFE_BUTTON_KEYWORDS = [
    "Yeni",
    "Ekle",
    "Oluştur",
    "Fatura",
    "Yapılandır",
    "Ekstre",
    "Otomatik",
    "Gelir",
    "Gider",
    "Kaydet",
]

UNSAFE_BUTTON_KEYWORDS = [
    "Sil",
    "Kapat",
    "Çıkış",
    "İçe Aktar",
    "Export",
    "Excel",
    "Yedek",
    "Geri",
    "Reset",
    "Temizle",
]


@dataclass
class StepResult:
    name: str
    key: str
    status: str = "PASS"
    duration_s: float = 0.0
    screenshot: Optional[str] = None
    heading: Optional[str] = None
    table_headers: List[str] = field(default_factory=list)
    table_rows: Optional[int] = None
    tabs: List[Dict[str, Any]] = field(default_factory=list)
    buttons: List[Dict[str, Any]] = field(default_factory=list)
    disabled_widgets: List[str] = field(default_factory=list)
    empty_state: bool = False
    notes: List[str] = field(default_factory=list)
    error: Optional[str] = None


class UISmokeRunner:
    def __init__(self, app: App, artifacts_dir: Path, timeout_s: float = 12.0):
        self.app = app
        self.root = app.root
        self.timeout_s = timeout_s
        self.artifacts_dir = artifacts_dir
        self.screenshots_dir = artifacts_dir / "screenshots"
        self.logs_dir = artifacts_dir / "logs"
        self.results_path = artifacts_dir / "results.json"
        self.report_path = artifacts_dir / "report.md"
        self.report_html_path = artifacts_dir / "report.html"
        self.steps: List[StepResult] = []
        self.errors: List[str] = []
        self._start_time = time.monotonic()
        self._logger = logging.getLogger("kasapro.ui_smoke")
        self._setup_dirs()
        self._setup_logging()
        self._hook_exceptions()

    def _setup_dirs(self) -> None:
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def _setup_logging(self) -> None:
        log_path = self.logs_dir / "ui_smoke.log"
        handler = logging.FileHandler(log_path, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        handler.setFormatter(formatter)
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(handler)

    def _hook_exceptions(self) -> None:
        def handle_exception(exc_type, exc, tb):
            msg = "".join(traceback.format_exception(exc_type, exc, tb))
            self.errors.append(msg)
            self._logger.exception("Unhandled exception captured", exc_info=(exc_type, exc, tb))

        def handle_tk_exception(exc, val, tb):
            msg = "".join(traceback.format_exception(exc, val, tb))
            self.errors.append(msg)
            self._logger.exception("Tkinter callback exception", exc_info=(exc, val, tb))

        sys.excepthook = handle_exception
        self.root.report_callback_exception = handle_tk_exception

    def _wait_for(self, predicate: Callable[[], bool], timeout_s: float) -> bool:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            try:
                self.root.update()
            except tk.TclError:
                return False
            if predicate():
                return True
            time.sleep(0.02)
        return False

    def _resolve_target_key(self, key: str) -> str:
        if key in self.app.frames:
            return key
        routes = getattr(self.app, "_nav_routes", {}) or {}
        route = routes.get(key)
        if isinstance(route, dict):
            target = route.get("target")
            if isinstance(target, str):
                return target
        return key

    def _iter_widgets(self, widget: tk.Widget) -> Iterable[tk.Widget]:
        stack = [widget]
        while stack:
            current = stack.pop()
            yield current
            try:
                stack.extend(current.winfo_children())
            except Exception:
                continue

    def _collect_tabs(self, frame: tk.Widget) -> Tuple[List[Dict[str, Any]], List[str]]:
        tabs: List[Dict[str, Any]] = []
        disabled: List[str] = []
        for widget in self._iter_widgets(frame):
            if isinstance(widget, ttk.Notebook):
                for tab_id in widget.tabs():
                    text = widget.tab(tab_id, "text") or ""
                    state = widget.tab(tab_id, "state") or "normal"
                    tab_info = {"text": text, "state": state}
                    if state == "disabled":
                        disabled.append(text or tab_id)
                    else:
                        try:
                            widget.select(tab_id)
                            self.root.update()
                        except Exception:
                            tab_info["error"] = "select_failed"
                    try:
                        tab_widget = widget.nametowidget(tab_id)
                        tab_info["has_content"] = bool(tab_widget.winfo_children())
                    except Exception:
                        tab_info["has_content"] = False
                    tabs.append(tab_info)
        return tabs, disabled

    def _collect_table_headers(self, frame: tk.Widget) -> Tuple[List[str], Optional[int]]:
        for widget in self._iter_widgets(frame):
            if isinstance(widget, ttk.Treeview):
                headers: List[str] = []
                for col in widget["columns"]:
                    header_text = widget.heading(col).get("text", "")
                    headers.append(str(header_text))
                try:
                    rows = len(widget.get_children())
                except Exception:
                    rows = None
                return headers, rows
        return [], None

    def _collect_buttons(self, frame: tk.Widget) -> Tuple[List[Dict[str, Any]], List[str]]:
        buttons: List[Dict[str, Any]] = []
        disabled: List[str] = []
        for widget in self._iter_widgets(frame):
            if isinstance(widget, ttk.Button):
                try:
                    text = widget.cget("text")
                except Exception:
                    text = ""
                try:
                    state = widget.state()
                    is_disabled = "disabled" in state
                except Exception:
                    is_disabled = False
                button_info = {"text": text, "disabled": is_disabled}
                if is_disabled:
                    disabled.append(text or "<button>")
                buttons.append(button_info)
        return buttons, disabled

    def _should_click_button(self, text: str) -> bool:
        if not text:
            return False
        for keyword in UNSAFE_BUTTON_KEYWORDS:
            if keyword.lower() in text.lower():
                return False
        for keyword in SAFE_BUTTON_KEYWORDS:
            if keyword.lower() in text.lower():
                return True
        return False

    def _click_buttons(self, frame: tk.Widget, limit: int = 3) -> List[Dict[str, Any]]:
        clicked: List[Dict[str, Any]] = []
        for widget in self._iter_widgets(frame):
            if not isinstance(widget, ttk.Button):
                continue
            text = str(widget.cget("text") or "")
            if not self._should_click_button(text):
                continue
            if "disabled" in widget.state():
                clicked.append({"text": text, "status": "disabled"})
                continue
            before_children = set(self.root.winfo_children())
            try:
                widget.invoke()
                self.root.update()
                clicked.append({"text": text, "status": "clicked"})
            except Exception as exc:
                clicked.append({"text": text, "status": f"error: {exc}"})
            self._close_new_toplevels(before_children)
            if len(clicked) >= limit:
                break
        return clicked

    def _close_new_toplevels(self, before_children: set[tk.Widget]) -> None:
        try:
            after_children = set(self.root.winfo_children())
        except Exception:
            return
        new_windows = [w for w in after_children if w not in before_children and isinstance(w, tk.Toplevel)]
        for win in new_windows:
            try:
                win.destroy()
            except Exception:
                continue

    def _take_screenshot(self, index: int, name: str) -> Optional[str]:
        filename = f"{index:03d}_{name}.png"
        path = self.screenshots_dir / filename
        try:
            from PIL import ImageGrab
        except Exception as exc:
            self.errors.append(f"Screenshot dependency missing: {exc}")
            return None
        try:
            self.root.update_idletasks()
            x = self.root.winfo_rootx()
            y = self.root.winfo_rooty()
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            bbox = (x, y, x + w, y + h)
            img = ImageGrab.grab(bbox=bbox)
            img.save(path)
            return str(path)
        except Exception as exc:
            self.errors.append(f"Screenshot failed: {exc}")
            return None

    def _wait_for_screen(self, key: str) -> bool:
        target_key = self._resolve_target_key(key)

        def predicate() -> bool:
            frame = self.app.frames.get(target_key)
            if frame is None:
                return False
            try:
                return bool(frame.winfo_ismapped())
            except Exception:
                return False

        return self._wait_for(predicate, self.timeout_s)

    def _record_step(self, step: StepResult) -> None:
        self.steps.append(step)
        self._logger.info("Step %s status=%s duration=%.2fs", step.name, step.status, step.duration_s)

    def _screen_step(self, name: str, key: str) -> None:
        start = time.monotonic()
        step = StepResult(name=name, key=key)
        try:
            self.app.show(key)
            if not self._wait_for_screen(key):
                raise TimeoutError(f"Screen {key} did not render within {self.timeout_s}s")
            target_key = self._resolve_target_key(key)
            frame = self.app.frames.get(target_key)
            step.heading = str(self.app.lbl_page_title.cget("text")) if hasattr(self.app, "lbl_page_title") else None
            if frame is not None:
                step.table_headers, step.table_rows = self._collect_table_headers(frame)
                if step.table_rows == 0:
                    step.empty_state = True
                tabs, disabled_tabs = self._collect_tabs(frame)
                step.tabs = tabs
                buttons, disabled_buttons = self._collect_buttons(frame)
                step.buttons = buttons
                step.disabled_widgets.extend(disabled_tabs)
                step.disabled_widgets.extend(disabled_buttons)
                step.buttons.extend(self._click_buttons(frame))
            step.screenshot = self._take_screenshot(len(self.steps) + 1, key)
        except Exception as exc:
            step.status = "FAIL"
            step.error = str(exc)
            step.screenshot = self._take_screenshot(len(self.steps) + 1, f"{key}_error")
        finally:
            step.duration_s = time.monotonic() - start
            self._record_step(step)

    def _import_step(self) -> None:
        start = time.monotonic()
        step = StepResult(name="Import", key="import")
        try:
            btn = getattr(self.app, "btn_import_excel", None)
            if btn is None:
                raise RuntimeError("Import button not found")
            step.heading = "Excel İçe Aktar"
            state = "disabled" if "disabled" in btn.state() else "normal"
            step.buttons.append({"text": btn.cget("text"), "state": state, "clicked": False})
            if state == "disabled":
                step.notes.append("Import button disabled (openpyxl missing)")
            step.screenshot = self._take_screenshot(len(self.steps) + 1, "import")
        except Exception as exc:
            step.status = "FAIL"
            step.error = str(exc)
            step.screenshot = self._take_screenshot(len(self.steps) + 1, "import_error")
        finally:
            step.duration_s = time.monotonic() - start
            self._record_step(step)

    def _settings_step(self) -> None:
        start = time.monotonic()
        step = StepResult(name="Ayarlar", key="settings")
        try:
            before_children = set(self.root.winfo_children())
            self.app.open_settings()
            self.root.update()
            self._close_new_toplevels(before_children)
            step.screenshot = self._take_screenshot(len(self.steps) + 1, "settings")
        except Exception as exc:
            step.status = "FAIL"
            step.error = str(exc)
            step.screenshot = self._take_screenshot(len(self.steps) + 1, "settings_error")
        finally:
            step.duration_s = time.monotonic() - start
            self._record_step(step)

    def run(self) -> int:
        try:
            try:
                self.root.deiconify()
            except Exception:
                pass
            self.root.update()
            self._wait_for(lambda: self.root.winfo_viewable(), self.timeout_s)

            screens = [
                ("Dashboard", "kasa"),
                ("Kasa", "kasa"),
                ("Cariler", "cariler"),
                ("Cari Hareket/Ekstre", "cari_hareketler"),
                ("Fatura", "fatura"),
                ("Banka", "banka_hareketleri"),
                ("Maaş", "maas_takibi"),
                ("Raporlar", "raporlar"),
            ]
            for name, key in screens:
                self._screen_step(name, key)

            self._import_step()
            self._settings_step()
        finally:
            self._finalize()
        return 0 if self._summary_status() == "PASS" else 1

    def _summary_status(self) -> str:
        if self.errors:
            return "FAIL"
        if any(step.status == "FAIL" for step in self.steps):
            return "FAIL"
        return "PASS"

    def _finalize(self) -> None:
        results = {
            "status": self._summary_status(),
            "duration_s": time.monotonic() - self._start_time,
            "errors": self.errors,
            "steps": [step.__dict__ for step in self.steps],
        }
        try:
            self.results_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            self._logger.exception("Failed to write results.json")
        if write_report is not None:
            try:
                write_report(results, self.artifacts_dir, self.report_path, self.report_html_path)
            except Exception:
                self._logger.exception("Failed to write report")
        try:
            self.app.on_close()
        except Exception:
            pass


def main() -> int:
    artifacts_env = os.environ.get("KASAPRO_TEST_ARTIFACTS")
    artifacts_dir = Path(artifacts_env) if artifacts_env else Path.cwd() / "test_artifacts"
    app = App(test_mode=True)
    runner = UISmokeRunner(app, artifacts_dir)
    exit_code = 1

    def _run_and_quit() -> None:
        nonlocal exit_code
        exit_code = runner.run()
        try:
            app.root.quit()
        except Exception:
            pass

    app.root.after(200, _run_and_quit)
    app.run()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
