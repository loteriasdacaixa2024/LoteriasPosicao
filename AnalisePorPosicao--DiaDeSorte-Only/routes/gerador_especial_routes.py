from flask import Blueprint, render_template, jsonify
from services.ciclo_service import CicloDiaDeSorteService
from services.cores_meses_service import CoresMesesService

gerador_especial_bp = Blueprint('gerador_especial', __name__)

@gerador_especial_bp.route('/')
def gerador_especial_index():
    try:
        ciclo_info = CicloDiaDeSorteService.obter_ciclo_atual()
    except Exception as e:
        print(f"Erro ao obter ciclo para index: {e}")
        ciclo_info = {
            "ciclo_num": 1,
            "dezenas_sorteadas": [],
            "dezenas_faltantes": list(range(1, 32)),
            "total_sorteadas": 0,
            "total_faltantes": 31,
            "concursos_no_ciclo": 0
        }
    
    cores_meses = CoresMesesService.obter_cores()
    
    return render_template(
        'gerador_especial.html', 
        ciclo=ciclo_info,
        cores_meses=cores_meses
    )

@gerador_especial_bp.route('/api/ciclo', methods=['GET'])
def api_ciclo():
    try:
        ciclo_info = CicloDiaDeSorteService.obter_ciclo_atual()
        return jsonify({"status": "success", **ciclo_info})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
