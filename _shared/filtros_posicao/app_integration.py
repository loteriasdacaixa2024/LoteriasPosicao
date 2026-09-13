# -*- coding: utf-8 -*-
from __future__ import annotations

import os

from jinja2 import ChoiceLoader, FileSystemLoader


def _ensure_template_path(app, tpl: str) -> None:
    loader = app.jinja_loader
    if isinstance(loader, ChoiceLoader):
        for sub in loader.loaders:
            if isinstance(sub, FileSystemLoader) and tpl in getattr(sub, "searchpath", []):
                return
        loader.loaders.insert(0, FileSystemLoader(tpl))
        return
    if isinstance(loader, FileSystemLoader):
        if tpl not in loader.searchpath:
            loader.searchpath.insert(0, tpl)
        return
    app.jinja_loader = ChoiceLoader([FileSystemLoader(tpl), loader])


def register_filtros_posicao(app, modality_key: str) -> None:
    from .routes_factory import build_filtros_posicao_blueprint

    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    _ensure_template_path(app, os.path.join(pkg_dir, "templates"))
    app.register_blueprint(build_filtros_posicao_blueprint(modality_key))
