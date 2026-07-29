import os
import sys

_SHARED = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from flask import Blueprint, render_template, jsonify
from services.analise_timemania_service import AnaliseTimemaniaSService

analise_bp = Blueprint('analise', __name__)

@analise_bp.route('/')
def analise_index():
    return render_template('analise.html')

@analise_bp.route('/api/dados', methods=['GET'])
def api_dados():
    try:
        dados = AnaliseTimemaniaSService.analise_geral()
        if not dados:
            return jsonify({"status":"error","message":"Sem dados no banco."}), 404
        return jsonify({"status":"success",**dados})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500

@analise_bp.route('/api/ultimos', methods=['GET'])
def api_ultimos():
    try:
        return jsonify({"status":"success","sorteios":AnaliseTimemaniaSService.ultimos_sorteios()})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500

# POSICAO_ANALISE_WIRED
from posicao_analise.app_integration import wire_posicao_analise
wire_posicao_analise(analise_bp, "timemania")
from concentracao_acertos.app_integration import wire_concentracao_analise
wire_concentracao_analise(analise_bp, "timemania")
from analise_estudos.app_integration import wire_analise_estudos
wire_analise_estudos(analise_bp, "timemania")
from analise_inteligentes_diadesorte.app_integration import wire_analise_inteligentes
wire_analise_inteligentes(analise_bp, "timemania")
from geradores_elite.comportamento_analise_integration import wire_analise_comportamento
wire_analise_comportamento(analise_bp, "timemania")
from analise_somas_digitos.app_integration import wire_analise_somas_digitos
wire_analise_somas_digitos(analise_bp, "timemania")
