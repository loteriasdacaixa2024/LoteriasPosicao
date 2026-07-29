# -*- coding: utf-8 -*-
"""Integração Flask — Concentração de Acertos."""
from __future__ import annotations

import os
import sys

from jinja2 import ChoiceLoader, FileSystemLoader

_SHARED = os.path.dirname(os.path.abspath(__file__))
if os.path.dirname(_SHARED) not in sys.path:
    sys.path.insert(0, os.path.dirname(_SHARED))


def extend_concentracao_app(app, modality_key: str) -> None:
    """Adiciona templates compartilhados (prioridade sobre locais)."""
    tpl = os.path.join(_SHARED, "templates")
    loaders = [FileSystemLoader(tpl)]
    existing = app.jinja_loader
    if isinstance(existing, ChoiceLoader):
        loaders.extend(existing.loaders)
    elif existing is not None:
        loaders.append(existing)
    app.jinja_loader = ChoiceLoader(loaders)


def wire_concentracao_analise(analise_bp, modality_key: str) -> None:
    from concentracao_acertos.routes_factory import register_concentracao_analise

    register_concentracao_analise(analise_bp, modality_key)
