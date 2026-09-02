# -*- coding: utf-8 -*-
"""Rotas Flask — Análise de Somas e Dígitos."""
from __future__ import annotations

import os

from flask import Blueprint, jsonify, render_template, request, send_from_directory

from analise_estudos.service_factory import make_estudos_base
from analise_estudos.specs import get_estudos_config, tem_analise_estudos
from analise_somas_digitos.service import AnaliseSomasDigitosService

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
_STATIC_DIR = os.path.join(_PKG_DIR, "static")


def _page_context(modality_key: str) -> dict:
    cfg = get_estudos_config(modality_key)
    Base = make_estudos_base(modality_key)
    construtor_habilitado = False
    try:
        from geradores_elite.construtor import tem_construtor
        construtor_habilitado = tem_construtor(modality_key)
    except Exception:
        pass
    return {
        "modality_key": modality_key,
        "modality_nome": cfg["nome"],
        "estudos_ui": Base.ui_config(),
        "api_base": "/analise/api/somas-digitos",
        "page_title": "Análise de Somas e Dígitos",
        "page_subtitle": "Soma das dezenas · dígitos distintos · tabelas de frequência",
        "construtor_habilitado": construtor_habilitado,
        "construtor_url": "/geradores-elite/construtor-construcoes/",
        "gerador_elite_url": "/geradores-elite/",
    }


def register_analise_somas_digitos(analise_bp: Blueprint, modality_key: str) -> None:
    if not tem_analise_estudos(modality_key):
        return

    @analise_bp.route("/somas-digitos/")
    def somas_digitos_page():
        return render_template("analise_somas_digitos.html", **_page_context(modality_key))

    @analise_bp.route("/somas-digitos/static/<path:filename>")
    def somas_digitos_static(filename):
        return send_from_directory(_STATIC_DIR, filename)

    @analise_bp.route("/api/somas-digitos/meta")
    def api_somas_digitos_meta():
        try:
            return jsonify({"sucesso": True, **_page_context(modality_key)})
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @analise_bp.route("/api/somas-digitos/somas")
    def api_somas():
        try:
            janela = request.args.get("janela", type=int)
            if janela is None:
                janela = make_estudos_base(modality_key).ui_config()["janela_default"]
            base = request.args.get("base", "geral")
            out = AnaliseSomasDigitosService.analisar_somas(
                modality_key, janela=janela, base_estatistica=base,
            )
            return jsonify(out), (200 if out.get("sucesso") else 400)
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @analise_bp.route("/api/somas-digitos/digitos")
    def api_digitos():
        try:
            janela = request.args.get("janela", type=int)
            if janela is None:
                janela = make_estudos_base(modality_key).ui_config()["janela_default"]
            base = request.args.get("base", "geral")
            out = AnaliseSomasDigitosService.analisar_digitos(
                modality_key, janela=janela, base_estatistica=base,
            )
            return jsonify(out), (200 if out.get("sucesso") else 400)
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @analise_bp.route("/api/somas-digitos/conjunto", methods=["GET", "POST"])
    def api_conjunto():
        try:
            if request.method == "POST":
                data = request.get_json(silent=True) or {}
                janela = int(data.get("janela", 0))
                base = data.get("base", "geral")
                pool = data.get("conjunto_base") or []
            else:
                janela = request.args.get("janela", 0, type=int)
                base = request.args.get("base", "geral")
                raw = request.args.get("dezenas", "")
                pool = [int(x) for x in raw.replace(";", ",").split(",") if x.strip().isdigit()]
            out = AnaliseSomasDigitosService.estatisticas_conjunto(
                modality_key, conjunto_base=pool or None, janela=janela, base_estatistica=base,
            )
            return jsonify(out), (200 if out.get("sucesso") else 400)
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @analise_bp.route("/api/somas-digitos/validar", methods=["POST"])
    def api_validar():
        try:
            data = request.get_json(silent=True) or {}
            out = AnaliseSomasDigitosService.validar_conjunto_base(
                modality_key,
                data.get("conjunto_base") or [],
                soma_min=data.get("soma_min"),
                soma_max=data.get("soma_max"),
                digitos_exigidos=data.get("digitos_exigidos"),
                exigir_digitos=bool(data.get("exigir_digitos")),
            )
            return jsonify(out), (200 if out.get("valido") else 400)
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500
