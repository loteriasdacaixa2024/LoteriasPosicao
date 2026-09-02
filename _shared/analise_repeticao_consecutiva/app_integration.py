# -*- coding: utf-8 -*-
import os
import sys

from flask import send_from_directory
from jinja2 import ChoiceLoader, FileSystemLoader

_PKG = os.path.dirname(os.path.abspath(__file__))
_SHARED = os.path.dirname(_PKG)
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)


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


def extend_repconsec_app(app) -> None:
    """Templates + rota estática do JS compartilhado."""
    tpl = os.path.join(_PKG, "templates")
    _merge_template_dirs(app, [tpl])

    if app.config.get("REPCONSEC_STATIC_REGISTERED"):
        return

    static_dir = os.path.join(_PKG, "static")

    @app.route("/static/js/analise-repeticao-consecutiva.js")
    def _serve_repconsec_js():
        return send_from_directory(static_dir, "analise-repeticao-consecutiva.js")

    app.config["REPCONSEC_STATIC_REGISTERED"] = True


def register_repconsec_api(analise_bp, modality_key: str) -> None:
    from flask import jsonify

    from .repeticao_consecutiva_service import RepeticaoConsecutivaService

    svc = RepeticaoConsecutivaService(modality_key)

    @analise_bp.route("/api/repeticao-consecutiva", methods=["GET"])
    def api_repeticao_consecutiva():
        try:
            dados = svc.analise_completa()
            if not dados:
                return jsonify({"status": "error", "message": "Dados insuficientes."}), 404
            return jsonify({"status": "success", **dados})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
