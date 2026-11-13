# -*- coding: utf-8 -*-
"""Rotas da tabela de cores. A conta é a cor da dezena de cada modalidade."""
from __future__ import annotations

import os

from flask import Blueprint, jsonify, render_template, request, send_from_directory

from analise_cores.service import analisar_modalidade

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
_STATIC_DIR = os.path.join(_PKG_DIR, "static")


def register_tabela_cores(analise_bp: Blueprint, modality_key: str) -> None:
    key = (modality_key or "").strip().lower()
    try:
        from configuracoes.regras_modalidade import get_regras
        nome = get_regras(key)["nome"]
    except Exception:
        nome = key

    @analise_bp.route("/tabela-cores/")
    def tabela_cores_page():
        return render_template(
            "tabela_cores.html",
            page_title="Tabela de Cores",
            page_subtitle="Quantidade por concurso, frequência, repetição e intervalo",
            modality_nome=nome,
            api_base="/analise/api/tabela-cores",
        )

    @analise_bp.route("/tabela-cores/static/<path:filename>")
    def tabela_cores_static(filename):
        return send_from_directory(_STATIC_DIR, filename)

    @analise_bp.route("/api/tabela-cores")
    def api_tabela_cores():
        try:
            de = request.args.get("de", type=int)
            ate = request.args.get("ate", type=int)
            out = analisar_modalidade(key, de=de, ate=ate)
            return jsonify(out), (200 if out.get("sucesso") else 400)
        except Exception as exc:
            return jsonify({"sucesso": False, "erro": str(exc)}), 500
