# -*- coding: utf-8 -*-
from __future__ import annotations

import queue
import threading
import time
from typing import Optional


class IntegrationWorker:
    def __init__(self, service, poll_interval: float = 2.0):
        self.service = service
        self.poll_interval = poll_interval
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._ui_queue: "queue.Queue[str]" = queue.Queue()

    def start(self, root=None):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        if root is not None:
            try:
                root.after(500, lambda: self._drain_ui_queue(root))
            except Exception:
                pass

    def stop(self):
        self._stop.set()

    def _run(self):
        while not self._stop.is_set():
            try:
                handled = self.service.run_next_job()
                if handled:
                    self._ui_queue.put("job_processed")
            except Exception:
                pass
            time.sleep(self.poll_interval)

    def _drain_ui_queue(self, root):
        try:
            while True:
                _ = self._ui_queue.get_nowait()
        except queue.Empty:
            pass
        if not self._stop.is_set():
            try:
                root.after(500, lambda: self._drain_ui_queue(root))
            except Exception:
                pass
