# -*- coding: utf-8 -*-
"""Rotas — Gerador Elite Estatísticas e Ciclo."""
from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request

from .service import (
    contexto_estatisticas_ciclo,
    gerar_apostas_estatisticas_ciclo,
    tem_gerador_estatisticas_ciclo,
)


def register_gerador_estatisticas_ciclo(bp: Blueprint, modality_key: str, modality_nome: str) -> None:
    if not tem_gerador_estatisticas_ciclo(modality_key):
        return

    @bp.route("/estatisticas-ciclo/")
    def estatisticas_ciclo_page():
        ctx = contexto_estatisticas_ciclo(modality_key)
        meses_cores = {}
        try:
            from services.cores_meses_service import CoresMesesService
            meses_cores = CoresMesesService.obter_cores() or {}
        except Exception:
            meses_cores = {}
        return render_template(
            "gerador_estatisticas_ciclo.html",
            modality_key=modality_key,
            modality_nome=modality_nome,
            page_title="Estatísticas e Ciclo",
            page_subtitle="Estatísticas Básicas · dezenas pendentes do ciclo",
            api_base="/geradores-elite/api/estatisticas-ciclo",
            ctx=ctx if ctx.get("sucesso") else {},
            meses_cores=meses_cores,
            escolha_url="/analise/escolha-visual/",
            ciclo_url="/analise/ciclo-cobertura/",
            padroes_url="/analise/analises-inteligentes/?aba=padroes-ii",
            panorama_url="/analise/analises-inteligentes/?aba=panorama",
            extra_mes=True,
        )

    @bp.route("/api/estatisticas-ciclo/contexto")
    def api_estatisticas_ciclo_contexto():
        out = contexto_estatisticas_ciclo(modality_key)
        return jsonify(out), (200 if out.get("sucesso") else 400)

    @bp.route("/api/estatisticas-ciclo/gerar", methods=["POST"])
    def api_estatisticas_ciclo_gerar():
        data = request.get_json(silent=True) or {}
        try:
            out = gerar_apostas_estatisticas_ciclo(
                modality_key,
                quantidade=int(data.get("quantidade") or 10),
                mes_valor=data.get("mes_num") if data.get("mes_num") not in (None, "", 0, "0") else None,
            )
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

        if out.get("sucesso"):
            try:
                from geradores_elite.validacao.pipeline import pipeline_from_request
                out = pipeline_from_request(
                    out,
                    modality_key=modality_key,
                    origem="estatisticas_ciclo",
                    data=data,
                )
            except Exception:
                pass
        return jsonify(out), (200 if out.get("sucesso") else 400)

    @bp.route("/api/estatisticas-ciclo/export-txt", methods=["POST"])
    def api_estatisticas_ciclo_export():
        data = request.get_json(silent=True) or {}
        apostas = data.get("apostas") or []
        if not apostas:
            return jsonify({"sucesso": False, "erro": "Nenhuma aposta para exportar."}), 400
        try:
            from geradores_elite.engine_final_core import formatar_export_txt
            txt = formatar_export_txt(modality_key, apostas, {})
            return jsonify({"sucesso": True, "txt": txt, "filename": "apostas_estatisticas_ciclo.txt"})
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500
