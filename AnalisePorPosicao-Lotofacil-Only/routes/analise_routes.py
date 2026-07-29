import os
import sys

_SHARED = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from flask import Blueprint, render_template, jsonify, request, send_file
from models.shared import db
from services.analise_lotofacil_service import AnaliseLotofacilService
import os

analise_bp = Blueprint('analise', __name__)

@analise_bp.route('/')
def analise_index():
    return render_template('sniper.html')

@analise_bp.route('/api/gerar-sniper', methods=['POST', 'GET'])
def gerar_sniper():
    try:
        resultado = AnaliseLotofacilService.gerar_matriz_sniper_vertical()
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"error": f"Erro interno ao gerar matriz Sniper: {str(e)}"})

@analise_bp.route('/atrasos')
def atrasos_posicao():
    return render_template('atrasos.html')

@analise_bp.route('/api/atrasos')
def api_atrasos():
    try:
        resultado = AnaliseLotofacilService.calcular_atrasos_absolutos()
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"error": str(e)})

@analise_bp.route('/api/aposta-sniper-atraso')
def api_aposta_sniper_atraso():
    try:
        resultado = AnaliseLotofacilService.gerar_aposta_por_maior_atraso()
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"error": str(e)})

@analise_bp.route('/api/download-24-apostas', methods=['POST'])
def api_download_24_apostas():
    """Gera 24 apostas sniper, salva em docs/ e retorna para download."""
    try:
        resultado = AnaliseLotofacilService.gerar_e_salvar_24_apostas()
        if "error" in resultado:
            return jsonify({"error": resultado["error"]})
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"error": str(e)})

@analise_bp.route('/api/download-arquivo-txt')
def api_download_arquivo_txt():
    """Serve o arquivo TXT para download direto pelo browser."""
    caminho = request.args.get('caminho', '')
    if not caminho or not os.path.exists(caminho):
        return jsonify({"error": "Arquivo não encontrado"}), 404
    return send_file(caminho, as_attachment=True, mimetype='text/plain')

# POSICAO_ANALISE_WIRED
from posicao_analise.app_integration import wire_posicao_analise
wire_posicao_analise(analise_bp, "lotofacil")
from concentracao_acertos.app_integration import wire_concentracao_analise
wire_concentracao_analise(analise_bp, "lotofacil")
from analise_estudos.app_integration import wire_analise_estudos
wire_analise_estudos(analise_bp, "lotofacil")
from analise_inteligentes_diadesorte.app_integration import wire_analise_inteligentes
wire_analise_inteligentes(analise_bp, "lotofacil")
from geradores_elite.comportamento_analise_integration import wire_analise_comportamento
wire_analise_comportamento(analise_bp, "lotofacil")
from analise_somas_digitos.app_integration import wire_analise_somas_digitos
wire_analise_somas_digitos(analise_bp, "lotofacil")
