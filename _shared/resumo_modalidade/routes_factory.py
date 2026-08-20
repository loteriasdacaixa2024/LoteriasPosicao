# -*- coding: utf-8 -*-
"""Rotas Flask — Resumo geral / DNA da modalidade."""
from __future__ import annotations

from flask import Blueprint, jsonify, render_template

from resumo_modalidade.service import ResumoModalidadeService
from resumo_modalidade.specs import get_resumo_spec, tem_resumo_modalidade


def _page_context(modality_key: str) -> dict:
    spec = get_resumo_spec(modality_key)
    return {
        "modality_key": modality_key,
        "modality_nome": spec.nome,
        "page_title": "Resumo Geral da Modalidade",
        "page_subtitle": "DNA estatístico para montar apostas — histórico real, sem previsão",
        "api_base": "/analise/api/resumo-geral",
    }


def register_resumo_modalidade(analise_bp: Blueprint, modality_key: str) -> None:
    if not tem_resumo_modalidade(modality_key):
        return

    @analise_bp.route("/resumo-geral/")
    def resumo_geral_page():
        payload = ResumoModalidadeService.calcular(modality_key)
        ctx = _page_context(modality_key)
        return render_template("resumo_modalidade.html", data=payload, **ctx)

    @analise_bp.route("/api/resumo-geral")
    def api_resumo_geral():
        payload = ResumoModalidadeService.calcular(modality_key)
        status = 200 if payload.get("sucesso") else 404
        return jsonify(payload), status
