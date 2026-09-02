# -*- coding: utf-8 -*-
"""Rotas — página + API Linhas do Universo e DD×DU."""
from __future__ import annotations

import os

from flask import Blueprint, jsonify, render_template, request, send_from_directory

from analise_estudos.service_factory import make_estudos_base
from analise_estudos.specs import get_estudos_config, tem_analise_estudos

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
_STATIC_DIR = os.path.join(_PKG_DIR, "static")


def _page_context(modality_key: str) -> dict:
    cfg = get_estudos_config(modality_key)
    Base = make_estudos_base(modality_key)
    return {
        "modality_key": modality_key,
        "modality_nome": cfg["nome"],
        "estudos_ui": Base.ui_config(),
        "page_title": "Linhas & DD × DU",
        "page_subtitle": "Padronização L1–L10 · Dígito da Dezena × Dígito da Unidade",
    }


def register_camadas_linhas_dd_du(analise_bp: Blueprint, modality_key: str) -> None:
    if not tem_analise_estudos(modality_key):
        return

    @analise_bp.route("/linhas-dd-du/")
    def linhas_dd_du_page():
        return render_template("linhas_dd_du.html", **_page_context(modality_key))

    @analise_bp.route("/linhas-dd-du/static/<path:filename>")
    def linhas_dd_du_static(filename):
        return send_from_directory(_STATIC_DIR, filename)

    @analise_bp.route("/api/linhas-universo/meta")
    def api_linhas_universo_meta():
        try:
            from linhas_universo.service import LinhasUniversoService

            return jsonify(LinhasUniversoService.meta(modality_key))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @analise_bp.route("/api/linhas-universo/analise")
    def api_linhas_universo_analise():
        try:
            from linhas_universo.service import LinhasUniversoService

            janela = request.args.get("janela", type=int)
            if janela is None:
                janela = make_estudos_base(modality_key).ui_config()["janela_default"]
            base = request.args.get("base", "geral")
            out = LinhasUniversoService.analisar(
                modality_key, janela=janela, base_estatistica=base,
            )
            return jsonify(out), (200 if out.get("sucesso") else 400)
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @analise_bp.route("/api/dd-du/analise")
    def api_dd_du_analise():
        try:
            from dd_du.service import DdDuService

            janela = request.args.get("janela", type=int)
            if janela is None:
                janela = make_estudos_base(modality_key).ui_config()["janela_default"]
            base = request.args.get("base", "geral")
            out = DdDuService.analisar(
                modality_key, janela=janela, base_estatistica=base,
            )
            return jsonify(out), (200 if out.get("sucesso") else 400)
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @analise_bp.route("/api/dd-du/decompor")
    def api_dd_du_decompor():
        try:
            from dd_du.core import decompor_lista

            cfg = get_estudos_config(modality_key)
            pad = int(cfg.get("pad_width") or 2)
            raw = (request.args.get("dezenas") or "").strip()
            if not raw:
                return jsonify({"sucesso": False, "erro": "Informe dezenas="}), 400
            parts = [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]
            dezenas = [int(p) for p in parts]
            return jsonify({
                "sucesso": True,
                "modality_key": modality_key,
                "pad_width": pad,
                **decompor_lista(dezenas, pad),
            })
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500
