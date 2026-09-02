# -*- coding: utf-8 -*-
"""Rotas Flask — Análise Tubular Inteligente."""
from __future__ import annotations

import os

from flask import Blueprint, jsonify, render_template, request, send_from_directory

from analise_estudos.service_factory import make_estudos_base
from analise_estudos.specs import get_estudos_config, tem_analise_estudos
from analise_tubular_inteligente.service import AnaliseTubularInteligenteService

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
_STATIC_DIR = os.path.join(_PKG_DIR, "static")


def _page_context(modality_key: str) -> dict:
    cfg = get_estudos_config(modality_key)
    Base = make_estudos_base(modality_key)
    return {
        "modality_key": modality_key,
        "modality_nome": cfg["nome"],
        "page_title": "Análise Tubular",
        "page_subtitle": "Monitoramento estatístico dos padrões da Visualização Tubular",
        "api_base": "/analise/api/analise-tubular",
        "estudos_ui": Base.ui_config(),
        "extra_mes": bool(cfg.get("extra_mes")),
        "gerador_elite_url": "/geradores-elite/",
        "gerador_escolha_url": "/geradores-elite/escolha-tubular-apostas/",
        "escolha_url": "/analise/escolha-visual/",
        "inteligentes_url": "/analise/analises-inteligentes/",
    }


def register_analise_tubular_inteligente(analise_bp: Blueprint, modality_key: str) -> None:
    if not tem_analise_estudos(modality_key):
        return

    @analise_bp.route("/analise-tubular/")
    def analise_tubular_page():
        return render_template("analise_tubular_inteligente.html", **_page_context(modality_key))

    @analise_bp.route("/analise-tubular/static/<path:filename>")
    def analise_tubular_static(filename):
        return send_from_directory(_STATIC_DIR, filename)

    @analise_bp.route("/api/analise-tubular/meta")
    def api_analise_tubular_meta():
        try:
            return jsonify({"sucesso": True, **_page_context(modality_key)})
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @analise_bp.route("/api/analise-tubular/dados")
    def api_analise_tubular_dados():
        try:
            janela = request.args.get("janela", type=int)
            if janela is None:
                janela = 0
            base = request.args.get("base", "geral")
            out = AnaliseTubularInteligenteService.analisar(
                modality_key, base_estatistica=base, janela=janela,
            )
            return jsonify(out), (200 if out.get("sucesso") else 400)
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500
