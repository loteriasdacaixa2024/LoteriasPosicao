# -*- coding: utf-8 -*-
import os
import sys

from flask import Blueprint
from jinja2 import ChoiceLoader, FileSystemLoader

_SHARED = os.path.dirname(os.path.abspath(__file__))
if _SHARED not in sys.path:
    sys.path.insert(0, os.path.dirname(_SHARED))

from central_conferencias.config import get_conf


def extend_app(app, modality_key: str) -> None:
    """Templates compartilhados + blueprint de assets estáticos."""
    tpl_dir = os.path.join(_SHARED, "templates")
    app.jinja_loader = ChoiceLoader([app.jinja_loader, FileSystemLoader(tpl_dir)])
    app.config["CC_MODALITY_KEY"] = modality_key
    app.config["CC_CFG"] = get_conf(modality_key)

    @app.context_processor
    def _inject_cc():
        return {"cc_cfg": get_conf(modality_key)}

    static_bp = Blueprint(
        "cc_static",
        __name__,
        static_folder=os.path.join(_SHARED, "static"),
        static_url_path="/static/cc",
    )
    if "cc_static" not in app.blueprints:
        app.register_blueprint(static_bp)


def register_conferencia_extras(conferencia_bp, modality_key: str) -> None:
    from central_conferencias.routes_extra import register_central_conferencias_extras

    register_central_conferencias_extras(conferencia_bp, modality_key)
