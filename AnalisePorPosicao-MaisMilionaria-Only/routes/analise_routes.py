import os
import sys

_SHARED = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from flask import Blueprint, render_template, jsonify
from services.analise_maismilionaria_service import AnaliseMaisMilionariaService

analise_bp = Blueprint('analise', __name__)

@analise_bp.route('/')
def analise_index():
    return render_template('analise.html')

@analise_bp.route('/api/dados', methods=['GET'])
def api_dados():
    try:
        dados = AnaliseMaisMilionariaService.analise_geral()
        if not dados:
            return jsonify({"status":"error","message":"Sem dados no banco."}), 404
        return jsonify({"status":"success",**dados})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500

@analise_bp.route('/api/ultimos', methods=['GET'])
def api_ultimos():
    try:
        return jsonify({"status":"success","sorteios":AnaliseMaisMilionariaService.ultimos_sorteios()})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500

# POSICAO_ANALISE_WIRED
from posicao_analise.app_integration import wire_posicao_analise
wire_posicao_analise(analise_bp, "maismilionaria")
