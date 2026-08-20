# -*- coding: utf-8 -*-
"""Integra rotas de Análise — Ciclo de Cobertura (fonte oficial)."""
from __future__ import annotations

import os
import traceback

from flask import Blueprint, jsonify, render_template


def _page_ctx(modality_key: str, active_tab: str) -> dict:
    from ciclo_cobertura.specs import get_ciclo_spec, tem_ciclo_cobertura

    enabled = tem_ciclo_cobertura(modality_key)
    nome = get_ciclo_spec(modality_key).nome if enabled else modality_key
    return {
        "modality_key": modality_key,
        "modality_nome": nome,
        "enabled": enabled,
        "active_tab": active_tab,
        "api_base": "/analise/api/ciclo-cobertura",
        "elite_href": "/geradores-elite/ciclo-apostas/?modo=estrategia",
    }


def extend_ciclo_cobertura_app(app, modality_key: str = "diadesorte") -> None:
    from menu.app_integration import _merge_template_dirs

    pkg = os.path.dirname(os.path.abspath(__file__))
    _merge_template_dirs(app, [os.path.join(pkg, "templates")])

    bp = Blueprint(
        "ciclo_cobertura_analise",
        __name__,
        url_prefix="/analise",
    )

    @bp.route("/ciclo-cobertura/")
    def ciclo_cobertura_page():
        return render_template(
            "ciclo_cobertura_analise.html",
            **_page_ctx(modality_key, "ciclo-atual"),
        )

    @bp.route("/ciclo-cobertura/metricas/")
    def ciclo_metricas_page():
        return render_template(
            "ciclo_cobertura_metricas.html",
            **_page_ctx(modality_key, "metricas"),
        )

    @bp.route("/ciclo-cobertura/inteligencia-operacional/")
    def ciclo_inteligencia_page():
        return render_template(
            "ciclo_cobertura_inteligencia.html",
            **_page_ctx(modality_key, "inteligencia"),
        )

    @bp.route("/api/ciclo-cobertura/ciclo-atual")
    def api_ciclo_atual():
        try:
            from ciclo_cobertura.analise_service import AnaliseCicloCoberturaService

            payload = AnaliseCicloCoberturaService.payload_oficial(modality_key)
            status = 200 if payload.get("sucesso") else 404
            return jsonify(payload), status
        except Exception as e:
            traceback.print_exc()
            return jsonify({"sucesso": False, "erro": str(e), "mensagem": str(e)}), 500

    @bp.route("/api/ciclo-cobertura/metricas-historicas")
    def api_metricas():
        try:
            from ciclo_cobertura.analise_service import AnaliseCicloCoberturaService

            payload = AnaliseCicloCoberturaService.payload_metricas(modality_key)
            status = 200 if payload.get("sucesso") else 404
            return jsonify(payload), status
        except Exception as e:
            traceback.print_exc()
            return jsonify({"sucesso": False, "erro": str(e), "mensagem": str(e)}), 500

    @bp.route("/api/ciclo-cobertura/inteligencia-operacional")
    def api_inteligencia():
        try:
            from ciclo_cobertura.inteligencia_service import CicloInteligenciaService

            dados = CicloInteligenciaService.obter_inteligencia_operacional(modality_key)
            if not dados:
                return jsonify({
                    "sucesso": False,
                    "mensagem": "Não foi possível montar a inteligência operacional.",
                }), 404
            return jsonify({"sucesso": True, "dados": dados})
        except Exception as e:
            traceback.print_exc()
            return jsonify({"sucesso": False, "erro": str(e), "mensagem": str(e)}), 500

    @bp.route("/api/ciclo-cobertura/contexto")
    def api_contexto():
        from ciclo_cobertura.service import contexto_dois_ultimos, metricas_padrao_2n1r

        ctx = contexto_dois_ultimos(modality_key)
        met = metricas_padrao_2n1r(modality_key)
        return jsonify({"ok": bool(ctx.get("ok")), "contexto": ctx, "metricas": met})

    app.register_blueprint(bp)
