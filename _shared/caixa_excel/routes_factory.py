# -*- coding: utf-8 -*-
"""Rotas /api/premiacao-caixa — padrão Dia de Sorte, sem gravar em sorteio_*."""
from __future__ import annotations

import os

from flask import jsonify, request, send_from_directory

_STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
_TEMPLATES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")


def register_premiacao_caixa(bp, *, modality_key: str, sorteio_model, db) -> None:
    from caixa_excel.complemento import (
        importar_excel_complemento,
        listar_complemento,
        ranking_uf_complemento,
    )
    from caixa_excel.ui_config import PREMIACAO_UI

    ui = PREMIACAO_UI.get(modality_key) or {
        "nome": modality_key,
        "nBolas": 6,
        "pad": 2,
        "labelBola": "P",
        "extra": None,
        "ordenar": True,
        "fonte": "excel",
        "faixas": [],
    }

    @bp.record_once
    def _on_register(state):
        from menu.app_integration import _merge_template_dirs
        _merge_template_dirs(state.app, [_TEMPLATES])

        @state.app.context_processor
        def _inject_premiacao_ui():
            return {"premiacao_ui": ui}

    @bp.route("/caixa-excel/premiacao.js")
    def caixa_excel_premiacao_js():
        return send_from_directory(_STATIC, "premiacao.js", mimetype="text/javascript")

    @bp.route("/caixa-excel/premiacao.css")
    def caixa_excel_premiacao_css():
        return send_from_directory(_STATIC, "premiacao.css", mimetype="text/css")

    @bp.route("/api/premiacao-caixa", methods=["GET"])
    def api_premiacao_caixa():
        try:
            all_flag = str(request.args.get("all", "")).strip().lower() in ("1", "true", "sim", "yes")
            if all_flag:
                return jsonify(listar_complemento(
                    db, sorteio_model, modality_key=modality_key, paginar=False,
                ))
            page = int(request.args.get("page", 1))
            size = int(request.args.get("size", 50))
            return jsonify(listar_complemento(
                db, sorteio_model, modality_key=modality_key, page=page, size=size, paginar=True,
            ))
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    @bp.route("/api/premiacao-caixa/atualizar", methods=["POST"])
    def api_premiacao_caixa_atualizar():
        try:
            data = request.get_json(silent=True) or {}
            fonte = (data.get("fonte") or "excel").strip().lower()
            baixar = data.get("baixar", fonte == "excel")
            if isinstance(baixar, str):
                baixar = baixar.strip().lower() not in ("0", "false", "nao", "não")
            if fonte != "excel":
                return jsonify({
                    "status": "success",
                    "fonte": fonte,
                    "message": "Premiação complementar desta modalidade usa só o Excel (sorteios continuam na API).",
                    "inseridos": 0,
                })
            out = importar_excel_complemento(
                db,
                modality_key=modality_key,
                sorteio_model=sorteio_model,
                baixar=bool(baixar),
            )
            return jsonify(out)
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    @bp.route("/api/ranking-uf-pagamentos", methods=["GET"])
    def api_ranking_uf_pagamentos():
        try:
            return jsonify(ranking_uf_complemento(db))
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
