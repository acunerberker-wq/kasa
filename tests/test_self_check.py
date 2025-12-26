# -*- coding: utf-8 -*-

from __future__ import annotations

from kasapro.self_check import run_checks


def test_self_check_runs() -> None:
    results = run_checks(check_ui=False)
    assert results, "Self-check sonuç üretmedi"
    assert any(r.name == "logging" for r in results)
    assert any(r.name == "db" for r in results)
