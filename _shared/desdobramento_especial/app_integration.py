# -*- coding: utf-8 -*-
import os
from typing import Optional, Type

from jinja2 import ChoiceLoader, FileSystemLoader

from _shared.desdobramento_especial.routes_factory import create_desdobramento_especial_blueprint
from _shared.desdobramento_especial.service_factory import build_desdobramento_especial_service


def register_desdobramento_especial(
    app,
    slug: str,
    ciclo_service_class: Type,
    desdobramento_service_class: Type,
    analise_service_class: Optional[Type] = None,
    url_prefix: str = "/desdobramento-especial",
):
    tpl_dir = os.path.join(os.path.dirname(__file__), "templates")
    loaders = [app.jinja_loader]
    if isinstance(app.jinja_loader, ChoiceLoader):
        loaders = list(app.jinja_loader.loaders)
    known = set()
    for loader in loaders:
        if hasattr(loader, "searchpath"):
            known.update(loader.searchpath)
    if tpl_dir not in known:
        loaders.insert(0, FileSystemLoader(tpl_dir))
        app.jinja_loader = ChoiceLoader(loaders)

    svc = build_desdobramento_especial_service(
        slug,
        ciclo_service_class,
        desdobramento_service_class,
        analise_service_class=analise_service_class,
    )
    bp = create_desdobramento_especial_blueprint(svc)
    app.register_blueprint(bp, url_prefix=url_prefix)
    app.config[f"DESDOBRAMENTO_ESPECIAL_{slug.upper()}"] = svc
    return svc
