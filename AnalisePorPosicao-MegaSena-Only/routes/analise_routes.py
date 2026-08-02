import os
import sys

_POS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_SHARED = os.path.join(_POS_ROOT, "_shared")
for _p in (_SHARED, _POS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from flask import Blueprint, render_template, jsonify
from services.analise_megasena_service import AnaliseMegaSenaService
from services.geometria_volante_service import GeometriaVolanteService
from services.repeticao_consecutiva_service import RepeticaoConsecutivaService
from models.sorteio_megasena import SorteioMegaSena
from _shared.coluna_final_vivo.app_integration import register_coluna_final_vivo

analise_bp = Blueprint('analise', __name__)
register_coluna_final_vivo(analise_bp, 'megasena', SorteioMegaSena)

@analise_bp.route('/')
def analise_index():
    return render_template('analise.html')

@analise_bp.route('/api/dados', methods=['GET'])
def api_dados():
    try:
        dados = AnaliseMegaSenaService.analise_geral()
        if not dados:
            return jsonify({"status":"error","message":"Sem dados no banco."}), 404
        return jsonify({"status":"success",**dados})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500

@analise_bp.route('/api/ultimos', methods=['GET'])
def api_ultimos():
    try:
        return jsonify({"status":"success","sorteios":AnaliseMegaSenaService.ultimos_sorteios()})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500

@analise_bp.route('/api/avancada', methods=['GET'])
def api_avancada():
    try:
        dados = AnaliseMegaSenaService.analise_avancada()
        if not dados:
            return jsonify({"status":"error","message":"Sem dados no banco."}), 404
        return jsonify({"status":"success",**dados})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500

@analise_bp.route('/api/geometria-estrutural', methods=['GET'])
def api_geometria_estrutural():
    try:
        dados = GeometriaVolanteService.analise_completa()
        if not dados:
            return jsonify({"status": "error", "message": "Sem dados no banco."}), 404
        return jsonify({"status": "success", **dados})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@analise_bp.route('/api/repeticao-consecutiva', methods=['GET'])
def api_repeticao_consecutiva():
    try:
        dados = RepeticaoConsecutivaService.analise_completa()
        if not dados:
            return jsonify({"status": "error", "message": "Dados insuficientes."}), 404
        return jsonify({"status": "success", **dados})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# POSICAO_ANALISE_WIRED
from posicao_analise.app_integration import wire_posicao_analise
wire_posicao_analise(analise_bp, "megasena")
from concentracao_acertos.app_integration import wire_concentracao_analise
wire_concentracao_analise(analise_bp, "megasena")
from analise_estudos.app_integration import wire_analise_estudos
wire_analise_estudos(analise_bp, "megasena")
from analise_inteligentes_diadesorte.app_integration import wire_analise_inteligentes
wire_analise_inteligentes(analise_bp, "megasena")
from geradores_elite.comportamento_analise_integration import wire_analise_comportamento
wire_analise_comportamento(analise_bp, "megasena")
from analise_somas_digitos.app_integration import wire_analise_somas_digitos
wire_analise_somas_digitos(analise_bp, "megasena")

from analise_escolha_visual.app_integration import wire_analise_escolha_visual
wire_analise_escolha_visual(analise_bp, "megasena")
from analise_tubular_inteligente.app_integration import wire_analise_tubular_inteligente
wire_analise_tubular_inteligente(analise_bp, "megasena")
