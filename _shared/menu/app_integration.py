# -*- coding: utf-8 -*-
import os
import sys

from jinja2 import ChoiceLoader, FileSystemLoader

_SHARED = os.path.dirname(os.path.abspath(__file__))
if os.path.dirname(_SHARED) not in sys.path:
    sys.path.insert(0, os.path.dirname(_SHARED))

from menu.nav_config import get_nav_config


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


def extend_nav_app(app, modality_key: str) -> None:
    """Injeta nav_cfg e adiciona templates compartilhados de menu."""
    shared_root = os.path.dirname(_SHARED)
    tpl_dirs = [
        os.path.join(_SHARED, "templates"),
        os.path.join(shared_root, "analise_comparar", "templates"),
        os.path.join(shared_root, "analise_repeticao", "templates"),
    ]
    _merge_template_dirs(app, tpl_dirs)

    cfg = get_nav_config(modality_key)
    app.config["NAV_MODALITY_KEY"] = modality_key

    @app.context_processor
    def _inject_nav():
        return {"nav_cfg": get_nav_config(modality_key)}
