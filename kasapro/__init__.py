# -*- coding: utf-8 -*-

from .core.version import __version__

# Not: Bazı ortamlarda (minimal Python kurulumları, test konteynerleri) tkinter
# bulunmayabilir. Bu durumda paketin sadece DB/servis katmanını import etmek
# isteyenler için import-time crash olmasın.
try:
    from .app import main, App  # type: ignore
except Exception:  # pragma: no cover
    main = None  # type: ignore
    App = None  # type: ignore

__all__ = ["App", "main", "__version__"]
