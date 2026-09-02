# -*- coding: utf-8 -*-
"""Integração Flask — Análise de Somas e Dígitos."""
from __future__ import annotations

import os
import sys

from jinja2 import ChoiceLoader, FileSystemLoader

_PKG = os.path.dirname(os.path.abspath(__file__))
if os.path.dirname(_PKG) not in sys.path:
    sys.path.insert(0, os.path.dirname(_PKG))


def extend_analise_somas_digitos_app(app) -> None:
    tpl = os.path.join(_PKG, "templates")
    loaders = [FileSystemLoader(tpl)]
    existing = app.jinja_loader
    if isinstance(existing, ChoiceLoader):
        loaders.extend(existing.loaders)
    elif existing is not None:
        loaders.append(existing)
    app.jinja_loader = ChoiceLoader(loaders)


def wire_analise_somas_digitos(analise_bp, modality_key: str) -> None:
    from analise_somas_digitos.routes_factory import register_analise_somas_digitos

    register_analise_somas_digitos(analise_bp, modality_key)
