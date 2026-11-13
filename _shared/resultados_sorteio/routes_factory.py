# -*- coding: utf-8 -*-
"""Rotas — Resultados (últimos cartões e dezenas deslocadas)."""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, render_template

from geradores_elite.modality_config import MODALITIES
from resultados_sorteio.service import garantir_estimativas, listar_resultados


def register_resultados_sorteio(analise_bp: Blueprint, modality_key: str) -> None:
    mod = MODALITIES.get(modality_key) or {}
    nome = mod.get("nome") or modality_key

    @analise_bp.route("/resultados/")
    def resultados_sorteio_page():
        return render_template(
            "resultados_sorteio.html",
            page_title=f"Resultados — {nome}",
            modality_nome=nome,
            api_url="/analise/api/resultados-sorteio/",
        )

    @analise_bp.route("/api/resultados-sorteio/")
    def resultados_sorteio_api():
        try:
            garantir_estimativas(current_app._get_current_object(), modality_key, imediato=24)
            return jsonify(listar_resultados(modality_key))
        except Exception as exc:
            return jsonify({"sucesso": False, "mensagem": str(exc)}), 500
