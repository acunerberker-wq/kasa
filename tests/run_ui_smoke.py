# -*- coding: utf-8 -*-
"""Launches the UI smoke test runner in a subprocess."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    artifacts_dir = root / "test_artifacts"
    env = os.environ.copy()
    env["KASAPRO_TEST_ARTIFACTS"] = str(artifacts_dir)
    cmd = [sys.executable, "-m", "kasapro.qa.ui_smoke"]
    result = subprocess.run(cmd, cwd=str(root), env=env)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
