import os
import sys

_SHARED = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from flask import Blueprint, render_template, jsonify
from services.analise_lotomania_service import AnaliseLotomaniaService
from analise_repeticao_consecutiva.app_integration import register_repconsec_api

analise_bp = Blueprint('analise', __name__)
register_repconsec_api(analise_bp, 'lotomania')

@analise_bp.route('/')
def analise_index():
    return render_template('analise.html')

@analise_bp.route('/api/dados', methods=['GET'])
def api_dados():
    try:
        dados = AnaliseLotomaniaService.analise_geral()
        if not dados:
            return jsonify({"status": "error", "message": "Sem dados no banco."}), 404
        return jsonify({"status": "success", **dados})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@analise_bp.route('/api/ultimos', methods=['GET'])
def api_ultimos():
    try:
        sorteios = AnaliseLotomaniaService.ultimos_sorteios()
        return jsonify({"status": "success", "sorteios": sorteios})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# POSICAO_ANALISE_WIRED
from posicao_analise.app_integration import wire_posicao_analise
wire_posicao_analise(analise_bp, "lotomania")
from concentracao_acertos.app_integration import wire_concentracao_analise
wire_concentracao_analise(analise_bp, "lotomania")
from analise_estudos.app_integration import wire_analise_estudos
wire_analise_estudos(analise_bp, "lotomania")

from linhas_universo.app_integration import wire_camadas_linhas_dd_du
wire_camadas_linhas_dd_du(analise_bp, "lotomania")
from analise_inteligentes_diadesorte.app_integration import wire_analise_inteligentes
wire_analise_inteligentes(analise_bp, "lotomania")
from geradores_elite.comportamento_analise_integration import wire_analise_comportamento
wire_analise_comportamento(analise_bp, "lotomania")
from analise_somas_digitos.app_integration import wire_analise_somas_digitos
wire_analise_somas_digitos(analise_bp, "lotomania")

from analise_gaps_ciclo.app_integration import wire_analise_gaps_ciclo
wire_analise_gaps_ciclo(analise_bp, "lotomania")

from analise_escolha_visual.app_integration import wire_analise_escolha_visual
wire_analise_escolha_visual(analise_bp, "lotomania")
from analise_tubular_inteligente.app_integration import wire_analise_tubular_inteligente
wire_analise_tubular_inteligente(analise_bp, "lotomania")

from resumo_modalidade.app_integration import wire_resumo_modalidade
wire_resumo_modalidade(analise_bp, "lotomania")
