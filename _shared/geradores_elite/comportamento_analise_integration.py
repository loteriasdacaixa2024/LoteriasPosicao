# -*- coding: utf-8 -*-
"""Integração — página Análise Comportamental (/analise/comportamento/)."""
from __future__ import annotations

import os

from flask import Blueprint, jsonify, render_template, request
from jinja2 import ChoiceLoader, FileSystemLoader

from geradores_elite.comportamento.specs import COMPORTAMENTO_TITLES, SPECS
from geradores_elite.inteligente import get_comportamento_service, tem_gerador_comportamento
from geradores_elite.modality_config import MODALITIES

_PKG = os.path.dirname(os.path.abspath(__file__))


def extend_comportamento_analise_app(app) -> None:
    """Garante templates de comportamento no loader da app."""
    tpl = os.path.join(_PKG, "templates")
    loaders = [FileSystemLoader(tpl)]
    existing = app.jinja_loader
    if isinstance(existing, ChoiceLoader):
        loaders.extend(existing.loaders)
    elif existing is not None:
        loaders.append(existing)
    app.jinja_loader = ChoiceLoader(loaders)


def wire_analise_comportamento(analise_bp: Blueprint, modality_key: str) -> None:
    if not tem_gerador_comportamento(modality_key):
        return

    def _svc():
        return get_comportamento_service(modality_key)

    @analise_bp.route("/comportamento/")
    def analise_comportamento_page():
        svc = _svc()
        if not svc:
            return "Análise comportamental indisponível.", 404
        sp_title = COMPORTAMENTO_TITLES.get(modality_key, "Comportamento")
        ui = svc.ui_config()
        nome = (MODALITIES.get(modality_key) or {}).get("nome") or modality_key
        spec = SPECS.get(modality_key)
        extras = ""
        if spec and getattr(spec, "has_mes", False):
            extras = " · MS"
        elif spec and getattr(spec, "has_time", False):
            extras = " · TM"
        return render_template(
            "analise_comportamento.html",
            page_title=f"Análise {sp_title}",
            page_subtitle=(
                "PA · IM · PR · RT · MO · SQ · M3 · FB"
                f"{extras} — janelas e bases estatísticas"
            ),
            modality_nome=nome,
            comportamento_ui=ui,
            api_base="/analise/api/comportamento",
            meses_cores={},
        )

    @analise_bp.route("/api/comportamento")
    def api_analise_comportamento():
        svc = _svc()
        if not svc:
            return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
        try:
            ui = svc.ui_config()
            janela = int(request.args.get("janela", ui.get("janela_default", 10)))
            base = request.args.get("base", "geral")
            filtros = {}
            for cod in ui.get("indicadores") or []:
                v = request.args.get(cod)
                if v is not None and v != "":
                    filtros[cod] = int(v)
            return jsonify(svc.analise_completa_api(
                janela=janela, filtros=filtros or None, base_estatistica=base,
            ))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @analise_bp.route("/api/comportamento/comparativo")
    def api_analise_comportamento_comparativo():
        svc = _svc()
        if not svc:
            return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
        try:
            janela = int(request.args.get("janela", svc.ui_config().get("janela_default", 10)))
            return jsonify(svc.analise_comparativo_bases(janela=janela))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @analise_bp.route("/api/comportamento/panorama-indicadores")
    def api_panorama_indicadores():
        svc = _svc()
        if not svc:
            return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
        try:
            base = request.args.get("base", "geral")
            return jsonify(svc.panorama_indicadores_api(base_estatistica=base))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500
