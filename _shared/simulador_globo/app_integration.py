# -*- coding: utf-8 -*-
"""Integração Flask — uma instância por modalidade, no SQLite dela."""
from __future__ import annotations

import os
import sys

from jinja2 import ChoiceLoader, FileSystemLoader

_PKG = os.path.dirname(os.path.abspath(__file__))
_SHARED = os.path.dirname(_PKG)
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)


def extend_simulador_globo_app(app, modality_key: str) -> None:
    from menu.app_integration import _merge_template_dirs
    from simulador_globo.historico_service import caminho_sqlite, ensure_schema
    from simulador_globo.routes_factory import register_simulador_globo

    _merge_template_dirs(app, [os.path.join(_PKG, "templates")])
    register_simulador_globo(app, modality_key)
    uri = app.config.get("SQLALCHEMY_DATABASE_URI") or ""
    if str(uri).startswith("sqlite:"):
        ensure_schema(caminho_sqlite(uri))
