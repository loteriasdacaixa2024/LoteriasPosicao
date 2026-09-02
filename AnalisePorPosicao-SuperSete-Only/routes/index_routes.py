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


import os as _os
import sys as _sys
from models.shared import db
from models.sorteio_supersete import SorteioSuperSete
_SHARED = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..", "_shared"))
if _SHARED not in _sys.path:
    _sys.path.insert(0, _SHARED)
from caixa_excel.routes_factory import register_premiacao_caixa
register_premiacao_caixa(index_bp, modality_key="supersete", sorteio_model=SorteioSuperSete, db=db)
