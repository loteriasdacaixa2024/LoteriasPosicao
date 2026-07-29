from flask import Blueprint, render_template, jsonify, request
from services.api_maismilionaria_service import ApiMaisMilionariaService

index_bp = Blueprint('index', __name__)

@index_bp.route('/')
def index():
    return render_template('index.html')

@index_bp.route('/api/status-banco', methods=['GET'])
def api_status_banco():
    try:
        return jsonify({"status": "success", **ApiMaisMilionariaService.status_banco()})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@index_bp.route('/api/sincronizar', methods=['POST'])
def api_sincronizar():
    try:
        data = request.get_json(silent=True) or {}
        modo = data.get("modo", "completo")
        limite = int(data.get("limite", 60))
        teto = data.get("teto_concurso")
        teto = int(teto) if teto else None
        resultado = ApiMaisMilionariaService.sincronizar_banco(
            modo=modo, limite=limite, teto_concurso=teto,
        )
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
