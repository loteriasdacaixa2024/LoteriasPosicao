from flask import Blueprint, render_template, jsonify
from services.analise_supersete_service import AnaliseSuperSeteService
from services.api_supersete_service import ApiSuperSeteService

index_bp = Blueprint('index', __name__)

@index_bp.route('/')
def index():
    stats = AnaliseSuperSeteService.get_stats_banco()
    return render_template('index.html', stats=stats)

@index_bp.route('/api/status-banco', methods=['GET'])
def api_status_banco():
    try:
        return jsonify({"status": "success", **ApiSuperSeteService.status_banco()})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@index_bp.route('/api/sincronizar', methods=['POST'])
def api_sincronizar():
    resultado = ApiSuperSeteService.sincronizar_banco()
    return jsonify(resultado)
