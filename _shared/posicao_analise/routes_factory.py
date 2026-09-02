# -*- coding: utf-8 -*-
"""Rotas Flask — Análise por Posição (registrar no analise_bp existente)."""
from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request

from .specs import get_posicao_spec, tem_posicao_analise


def _page_extras(modality_key: str) -> dict:
    spec = get_posicao_spec(modality_key)
    meses_cores = {}
    if spec.extra_mes:
        try:
            from services.cores_meses_service import CoresMesesService

            meses_cores = CoresMesesService.obter_cores() or {}
        except Exception:
            try:
                from _shared.diadesorte.meses_cores import obter_meses_cores

                meses_cores = obter_meses_cores() or {}
            except Exception:
                meses_cores = {}
    return {
        "modality_key": modality_key,
        "modality_nome": spec.nome,
        "pos_cfg": spec.to_ui(),
        "meses_cores": meses_cores,
    }


def register_posicao_routes(analise_bp: Blueprint, modality_key: str) -> None:
    if not tem_posicao_analise(modality_key):
        return

    from posicao_analise.service_factory import make_service

    Svc = make_service(modality_key)
    extras = _page_extras(modality_key)

    @analise_bp.route("/por-posicao/")
    def analise_por_posicao_page():
        return render_template("analise_por_posicao.html", **extras)

    @analise_bp.route("/api/por-posicao/concursos", methods=["GET"])
    def api_por_posicao_concursos():
        try:
            limit = request.args.get("limit", type=int)
            sorteio = int(request.args.get("sorteio", 1))
            return jsonify({
                "status": "success",
                "concursos": Svc.listar_concursos(limit=limit, sorteio=sorteio),
                "pos_cfg": extras["pos_cfg"],
            })
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    @analise_bp.route("/api/por-posicao/<int:concurso>", methods=["GET"])
    def api_por_posicao_concurso(concurso):
        try:
            sorteio = int(request.args.get("sorteio", 1))
            dados = Svc.analisar_concurso(concurso, sorteio=sorteio)
            if not dados:
                return jsonify({
                    "status": "error",
                    "message": f"Concurso {concurso} não encontrado ou ordem incompleta.",
                }), 404
            return jsonify({"status": "success", **dados})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
