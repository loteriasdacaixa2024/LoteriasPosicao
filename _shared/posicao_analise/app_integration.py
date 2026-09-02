# -*- coding: utf-8 -*-
"""Integração Flask — templates e rotas de análise por posição."""
from __future__ import annotations

import os
import sys

from jinja2 import ChoiceLoader, FileSystemLoader

_SHARED = os.path.dirname(os.path.abspath(__file__))
if os.path.dirname(_SHARED) not in sys.path:
    sys.path.insert(0, os.path.dirname(_SHARED))


def _merge_template_dirs(app, tpl_dirs: list) -> None:
    loaders = []
    existing = app.jinja_loader
    if isinstance(existing, ChoiceLoader):
        loaders.extend(existing.loaders)
    elif existing is not None:
        loaders.append(existing)
    known = set()
    for loader in loaders:
        if hasattr(loader, "searchpath"):
            known.update(loader.searchpath)
    for tpl_dir in tpl_dirs:
        if os.path.isdir(tpl_dir) and tpl_dir not in known:
            loaders.append(FileSystemLoader(tpl_dir))
            known.add(tpl_dir)
    app.jinja_loader = ChoiceLoader(loaders)


def extend_posicao_app(app, modality_key: str) -> None:
    """Adiciona templates compartilhados de posição (prioridade sobre locais)."""
    tpl = os.path.join(_SHARED, "templates")
    loaders = [FileSystemLoader(tpl)]
    existing = app.jinja_loader
    if isinstance(existing, ChoiceLoader):
        loaders.extend(existing.loaders)
    elif existing is not None:
        loaders.append(existing)
    app.jinja_loader = ChoiceLoader(loaders)


def wire_posicao_analise(analise_bp, modality_key: str) -> None:
    from posicao_analise.routes_factory import register_posicao_routes

    register_posicao_routes(analise_bp, modality_key)
