# -*- coding: utf-8 -*-
"""Blueprint — Filtros por posição (menu DADOS)."""
from __future__ import annotations

import os

from flask import Blueprint, jsonify, render_template, request

from .service import analisar, get_posicao_spec


def build_filtros_posicao_blueprint(modality_key: str) -> Blueprint:
    spec = get_posicao_spec(modality_key)
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    bp = Blueprint(
        "filtros_posicao",
        __name__,
        template_folder=os.path.join(pkg_dir, "templates"),
        url_prefix="/dados/filtros-posicao",
    )

    @bp.route("/")
    def pagina():
        return render_template(
            "filtros_posicao.html",
            modality_key=modality_key,
            modality_nome=spec.nome,
            pos_cfg=spec.to_ui(),
        )

    @bp.route("/api")
    def api():
        modo = request.args.get("modo", "crescente")
        sorteio = request.args.get("sorteio", 1, type=int) or 1
        return jsonify(analisar(modality_key, modo=modo, sorteio=sorteio))

    return bp
