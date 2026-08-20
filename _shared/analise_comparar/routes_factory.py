# -*- coding: utf-8 -*-
"""Blueprint factory — Comparar concursos (padrão Lotofácil)."""
from __future__ import annotations

import os

from flask import Blueprint, jsonify, render_template, request
from jinja2 import ChoiceLoader, FileSystemLoader

from .compare_config import get_compare_config
from .compare_service import CompararConcursosService


def _ensure_template_path(app, tpl: str) -> None:
    """Inclui pasta de templates compartilhados (nav includes) no loader do app."""
    loader = app.jinja_loader
    if isinstance(loader, ChoiceLoader):
        for sub in loader.loaders:
            if isinstance(sub, FileSystemLoader) and tpl in sub.searchpath:
                return
        loader.loaders.insert(0, FileSystemLoader(tpl))
        return
    if isinstance(loader, FileSystemLoader):
        if tpl not in loader.searchpath:
            loader.searchpath.insert(0, tpl)
        return
    app.jinja_loader = ChoiceLoader([FileSystemLoader(tpl), loader])


def build_comparar_blueprint(modality_key: str) -> Blueprint:
    cfg = get_compare_config(modality_key)
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    bp = Blueprint(
        "analise_comparar",
        __name__,
        template_folder=os.path.join(pkg_dir, "templates"),
        url_prefix="/analise/comparar-concursos",
    )
    svc = CompararConcursosService(modality_key)

    @bp.route("/")
    def pagina():
        return render_template(
            "analise_comparar_concursos.html",
            modality_key=modality_key,
            cfg=cfg,
        )

    @bp.route("/api/comparar")
    def api_comparar():
        modo = request.args.get("modo", cfg.get("modos", ["volante"])[0])
        ca = request.args.get("concurso_a", type=int)
        cb = request.args.get("concurso_b", type=int)
        sa = request.args.get("sorteio_a", 1, type=int)
        sb = request.args.get("sorteio_b", 1, type=int)
        return jsonify(svc.comparar(ca, cb, modo, sa, sb))

    @bp.route("/api/concursos")
    def api_concursos():
        limite = request.args.get("limit", 150)
        return jsonify({"sucesso": True, "concursos": svc.listar_concursos(limite)})

    @bp.route("/api/indicacao-padrao")
    def api_indicacao_padrao():
        return jsonify(svc.indicacao_padrao())

    @bp.route("/api/historico-indicados")
    def api_historico_indicados():
        limite = request.args.get("limit", 15, type=int)
        offset = request.args.get("offset", 0, type=int)
        return jsonify(svc.historico_indicados(limit=limite, offset=offset))

    @bp.route("/api/historico-visual")
    def api_historico_visual():
        limite = request.args.get("limit", 10, type=int)
        antes_de = request.args.get("antes_de", type=int)
        concursos = request.args.get("concursos", "") or ""
        return jsonify(svc.historico_visual(limit=limite, antes_de=antes_de, concursos=concursos))

    @bp.route("/api/combinacoes-auto", methods=["POST"])
    def api_combinacoes_auto():
        from .auto_combinacoes import gerar_e_testar
        body = request.get_json(silent=True) or {}
        hist = svc.historico_indicados(limit=0)
        if not hist.get("sucesso"):
            return jsonify({"sucesso": False, "erro": "Falha ao ler o histórico."}), 400
        return jsonify(gerar_e_testar(
            concursos=hist.get("concursos") or [],
            dmin=int(cfg["dezena_min"]),
            dmax=int(cfg["dezena_max"]),
            modality_key=modality_key,
            dezenas_manual=body.get("dezenas_manual") or [],
        ))

    return bp


def register_comparar(app, modality_key: str) -> None:
    """Registra blueprint + pasta de templates compartilhados no app."""
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    tpl = os.path.join(pkg_dir, "templates")
    _ensure_template_path(app, tpl)
    app.register_blueprint(build_comparar_blueprint(modality_key))