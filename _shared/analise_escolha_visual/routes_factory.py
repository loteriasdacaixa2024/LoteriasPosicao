# -*- coding: utf-8 -*-
"""Rotas Flask — Escolha Visual."""
from __future__ import annotations

import os

from flask import Blueprint, jsonify, render_template, request, send_from_directory

from analise_escolha_visual.service import AnaliseEscolhaVisualService
from analise_estudos.specs import get_estudos_config, tem_analise_estudos

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
_STATIC_DIR = os.path.join(_PKG_DIR, "static")


def _page_context(modality_key: str) -> dict:
    cfg = get_estudos_config(modality_key)
    ui = AnaliseEscolhaVisualService.ui_meta(modality_key)
    return {
        "modality_key": modality_key,
        "modality_nome": cfg["nome"],
        "page_title": "Escolha Visual",
        "page_subtitle": "Destaques no volante — pares, ímpares, repetidos, sequências e finais",
        "api_base": "/analise/api/escolha-visual",
        "escolha_ui": ui,
        "gerador_elite_url": "/geradores-elite/",
        "gerador_escolha_url": "/geradores-elite/escolha-tubular-apostas/",
        "tubular_url": "/analise/analise-tubular/",
    }


def register_analise_escolha_visual(analise_bp: Blueprint, modality_key: str) -> None:
    if not tem_analise_estudos(modality_key):
        return

    @analise_bp.route("/escolha-visual/")
    def escolha_visual_page():
        return render_template("analise_escolha_visual.html", **_page_context(modality_key))

    @analise_bp.route("/escolha-visual/static/<path:filename>")
    def escolha_visual_static(filename):
        return send_from_directory(_STATIC_DIR, filename)

    @analise_bp.route("/api/escolha-visual/meta")
    def api_escolha_visual_meta():
        try:
            return jsonify({"sucesso": True, **_page_context(modality_key)})
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @analise_bp.route("/api/escolha-visual/sorteios")
    def api_escolha_visual_sorteios():
        try:
            ordem = request.args.get("ordem", "desc")
            limite = request.args.get("limite", 0, type=int) or 0
            base = request.args.get("base", "geral")
            out = AnaliseEscolhaVisualService.listar_sorteios(
                modality_key, ordem=ordem, limite=limite, base_estatistica=base,
            )
            return jsonify(out), (200 if out.get("sucesso") else 400)
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500
