# -*- coding: utf-8 -*-
import os
from typing import Type

from flask import Blueprint
from jinja2 import ChoiceLoader, FileSystemLoader

from _shared.coluna_final_vivo.service_factory import build_coluna_final_vivo_service


def extend_coluna_final_vivo_templates(app):
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


def register_coluna_final_vivo(
    blueprint: Blueprint,
    slug: str,
    sorteio_model: Type,
):
    svc = build_coluna_final_vivo_service(sorteio_model, slug)

    @blueprint.route("/api/coluna-final-vivo", methods=["GET"])
    def api_coluna_final_vivo():
        from flask import jsonify

        try:
            return jsonify({"status": "success", **svc.obter_payload()})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    return svc
