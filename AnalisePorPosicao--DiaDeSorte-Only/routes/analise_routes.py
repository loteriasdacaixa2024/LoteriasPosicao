# -*- coding: utf-8 -*-
"""Rotas de análise — Dia de Sorte."""
import os
import sys

from flask import Blueprint, jsonify, render_template, request

_SHARED = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from geradores_elite.inteligente import get_comportamento_service, tem_gerador_comportamento
from geradores_elite.comportamento.specs import COMPORTAMENTO_TITLES

from services.analise_diadesorte_service import AnaliseDiaDeSorteService

analise_bp = Blueprint("analise", __name__)

_MODALITY = "diadesorte"


def _comportamento_svc():
    if not tem_gerador_comportamento(_MODALITY):
        return None
    return get_comportamento_service(_MODALITY)


@analise_bp.route("/")
def analise_index():
    return render_template("analise.html")


@analise_bp.route("/comportamento/")
def analise_comportamento_page():
    svc = _comportamento_svc()
    if not svc:
        return "Análise comportamental indisponível.", 404
    sp_title = COMPORTAMENTO_TITLES.get(_MODALITY, "Comportamento")
    ui = svc.ui_config()
    meses_cores = {}
    try:
        from services.cores_meses_service import CoresMesesService
        meses_cores = CoresMesesService.obter_cores() or {}
    except Exception:
        meses_cores = {}
    return render_template(
        "analise_comportamento.html",
        page_title=f"Análise {sp_title}",
        page_subtitle="PA · IM · PR · RT · MO · SQ · M3 · FB · MS — Geral, Vencedores e Acumulados",
        modality_nome="Dia de Sorte",
        comportamento_ui=ui,
        api_base="/analise/api/comportamento",
        meses_cores=meses_cores,
    )




@analise_bp.route("/api/dados", methods=["GET"])
def api_dados():
    try:
        dados = AnaliseDiaDeSorteService.analise_geral()
        if not dados:
            return jsonify({"status": "error", "message": "Sem dados no banco."}), 404
        return jsonify({"status": "success", **dados})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@analise_bp.route("/api/ultimos", methods=["GET"])
def api_ultimos():
    try:
        return jsonify({
            "status": "success",
            "sorteios": AnaliseDiaDeSorteService.ultimos_sorteios(),
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@analise_bp.route("/api/comportamento")
def api_analise_comportamento():
    svc = _comportamento_svc()
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
    svc = _comportamento_svc()
    if not svc:
        return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
    try:
        janela = int(request.args.get("janela", svc.ui_config().get("janela_default", 10)))
        return jsonify(svc.analise_comparativo_bases(janela=janela))
    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 500


@analise_bp.route("/api/meses-indicados")
def api_meses_indicados():
    try:
        janela = int(request.args.get("janela", 10))
        dados = AnaliseDiaDeSorteService.meses_indicados(janela=janela)
        if not dados.get("sucesso"):
            return jsonify(dados), 404
        return jsonify(dados)
    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 500


@analise_bp.route("/api/comportamento/panorama-indicadores")
def api_panorama_indicadores():
    svc = _comportamento_svc()
    if not svc:
        return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
    try:
        base = request.args.get("base", "geral")
        return jsonify(svc.panorama_indicadores_api(base_estatistica=base))
    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 500

# POSICAO_ANALISE_WIRED
from posicao_analise.app_integration import wire_posicao_analise
wire_posicao_analise(analise_bp, "diadesorte")

# CONCENTRACAO_ACERTOS_WIRED
from concentracao_acertos.app_integration import wire_concentracao_analise
wire_concentracao_analise(analise_bp, "diadesorte")

# ANALISE_ESTUDOS_WIRED
from analise_estudos.app_integration import wire_analise_estudos
wire_analise_estudos(analise_bp, "diadesorte")

from linhas_universo.app_integration import wire_camadas_linhas_dd_du
wire_camadas_linhas_dd_du(analise_bp, "diadesorte")

# RESUMO_GERAL_MODALIDADE
from resumo_modalidade.app_integration import wire_resumo_modalidade
wire_resumo_modalidade(analise_bp, "diadesorte")

# ANALISE_SOMAS_DIGITOS_WIRED
from analise_somas_digitos.app_integration import wire_analise_somas_digitos
wire_analise_somas_digitos(analise_bp, "diadesorte")

# ANALISE_INTELIGENTES_WIRED
from analise_inteligentes_diadesorte.app_integration import wire_analise_inteligentes
wire_analise_inteligentes(analise_bp, "diadesorte")

# ANALISE_ESCOLHA_VISUAL_WIRED
from analise_escolha_visual.app_integration import wire_analise_escolha_visual
wire_analise_escolha_visual(analise_bp, "diadesorte")

# ANALISE_TUBULAR_INTELIGENTE_WIRED
from analise_tubular_inteligente.app_integration import wire_analise_tubular_inteligente
wire_analise_tubular_inteligente(analise_bp, "diadesorte")
