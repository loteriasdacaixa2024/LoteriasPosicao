import os
import sys

_SHARED = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from flask import Blueprint, render_template, jsonify
from services.analise_duplasena_service import AnaliseDuplaSenaService

analise_bp = Blueprint('analise', __name__)

@analise_bp.route('/')
def analise_index():
    return render_template('analise.html')

@analise_bp.route('/api/dados', methods=['GET'])
def api_dados():
    try:
        dados = AnaliseDuplaSenaService.analise_geral()
        if not dados:
            return jsonify({"status":"error","message":"Sem dados no banco."}), 404
        return jsonify({"status":"success",**dados})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500

@analise_bp.route('/api/ultimos', methods=['GET'])
def api_ultimos():
    try:
        return jsonify({"status":"success","sorteios":AnaliseDuplaSenaService.ultimos_sorteios()})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500

# POSICAO_ANALISE_WIRED
from posicao_analise.app_integration import wire_posicao_analise
wire_posicao_analise(analise_bp, "duplasena")

from analise_estudos.app_integration import wire_analise_estudos
wire_analise_estudos(analise_bp, "duplasena")

from analise_gaps_ciclo.app_integration import wire_analise_gaps_ciclo
wire_analise_gaps_ciclo(analise_bp, "duplasena")

from linhas_universo.app_integration import wire_camadas_linhas_dd_du
wire_camadas_linhas_dd_du(analise_bp, "duplasena")
from analise_escolha_visual.app_integration import wire_analise_escolha_visual
wire_analise_escolha_visual(analise_bp, "duplasena")
from analise_tubular_inteligente.app_integration import wire_analise_tubular_inteligente
wire_analise_tubular_inteligente(analise_bp, "duplasena")
from analise_inteligentes_diadesorte.app_integration import wire_analise_inteligentes
wire_analise_inteligentes(analise_bp, "duplasena")

from resumo_modalidade.app_integration import wire_resumo_modalidade
wire_resumo_modalidade(analise_bp, "duplasena")
