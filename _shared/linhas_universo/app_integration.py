# -*- coding: utf-8 -*-
"""Integração Flask — camadas Linhas + DD×DU (página + API)."""
from __future__ import annotations

import os
import sys

from jinja2 import ChoiceLoader, FileSystemLoader

_PKG = os.path.dirname(os.path.abspath(__file__))
_SHARED = os.path.dirname(_PKG)
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)


def extend_camadas_linhas_dd_du_app(app) -> None:
    tpl = os.path.join(_PKG, "templates")
    loaders = [FileSystemLoader(tpl)]
    existing = app.jinja_loader
    if isinstance(existing, ChoiceLoader):
        loaders.extend(existing.loaders)
    elif existing is not None:
        loaders.append(existing)
    app.jinja_loader = ChoiceLoader(loaders)


def wire_camadas_linhas_dd_du(analise_bp, modality_key: str) -> None:
    from linhas_universo.routes_factory import register_camadas_linhas_dd_du

    register_camadas_linhas_dd_du(analise_bp, modality_key)
