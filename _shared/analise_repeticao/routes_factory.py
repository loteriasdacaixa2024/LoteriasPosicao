# -*- coding: utf-8 -*-
"""Blueprint factory — Repetição entre concursos."""
from __future__ import annotations

import os

from flask import Blueprint, jsonify, render_template, request

from analise_comparar.routes_factory import _ensure_template_path

from .repeticao_config import get_repeticao_config, get_repeticao_ui_context
from .repeticao_service import RepeticaoConcursosService


def build_repeticao_blueprint(modality_key: str) -> Blueprint:
    cfg = get_repeticao_config(modality_key)
    pkg_dir = os.path.dirname(os.path.abspath(__file__))

    bp = Blueprint(
        "analise_repeticao",
        __name__,
        template_folder=os.path.join(pkg_dir, "templates"),
        url_prefix="/analise/repeticao-concursos",
    )
    svc = RepeticaoConcursosService(modality_key)

    @bp.route("/")
    def pagina():
        ui_ctx = get_repeticao_ui_context(modality_key)
        tem_sniper_apostas = False
        try:
            from geradores_elite.inteligente import tem_gerador_inteligente

            tem_sniper_apostas = tem_gerador_inteligente(modality_key)
        except ImportError:
            pass
        return render_template(
            "analise_repeticao_concursos.html",
            modality_key=modality_key,
            cfg=cfg,
            meses_cores=ui_ctx.get("meses_cores", {}),
            tem_sniper_apostas=tem_sniper_apostas,
        )

    @bp.route("/api/analise")
    def api_analise():
        modo = request.args.get("modo", (cfg.get("modos") or ["volante"])[0])
        return jsonify(svc.analisar_completo(modo))

    @bp.route("/api/concursos")
    def api_concursos():
        limite = request.args.get("limit", 150)
        return jsonify({"sucesso": True, "concursos": svc.listar_concursos(limite)})

    @bp.route("/api/concurso/<int:concurso>")
    def api_concurso(concurso):
        row = svc.obter_concurso(concurso)
        if not row:
            return jsonify({"sucesso": False, "erro": "Concurso não encontrado"}), 404
        return jsonify({"sucesso": True, **row})

    @bp.route("/api/gerar", methods=["POST"])
    def api_gerar():
        data = request.get_json(silent=True) or {}
        modo = data.get("modo", (cfg.get("modos") or ["volante"])[0])
        analise = svc.analisar_completo(modo)
        if not analise.get("sucesso"):
            return jsonify(analise), 400
        resultado = svc.gerar_apostas(
            quantidade=int(data.get("quantidade", 10)),
            dezenas_por_jogo=int(data.get("dezenas_por_jogo", cfg["dezenas_default"])),
            modo=modo,
            perfil=data.get("perfil", "equilibrado"),
            usar_ultimo_par=bool(data.get("usar_ultimo_par", True)),
            so_permanencia=bool(data.get("so_permanencia", False)),
            respeitar_par_impar=bool(data.get("respeitar_par_impar", True)),
            analise=analise,
        )
        resultado["analise_resumo"] = {
            "ultimo": analise["ultimo_concurso"],
            "penultimo": analise["penultimo_concurso"],
            "repetidas": analise["resumo_ultimo_par"]["volante"]["dezenas"],
        }
        return jsonify(resultado)

    return bp


def register_repeticao(app, modality_key: str) -> None:
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    tpl = os.path.join(pkg_dir, "templates")
    _ensure_template_path(app, tpl)
    app.register_blueprint(build_repeticao_blueprint(modality_key))
