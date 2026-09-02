from flask import Blueprint, render_template, jsonify
from services.modelos_service import ModelosDuplaSenaService

modelos_bp = Blueprint('modelos', __name__)

@modelos_bp.route('/')
def modelos_index():
    return render_template('modelos.html', modelos=ModelosDuplaSenaService.listar_modelos())

@modelos_bp.route('/api/gerar/<int:modelo_id>', methods=['POST'])
def api_gerar_modelo(modelo_id):
    if modelo_id not in range(1, 7):
        return jsonify({"error":"Modelo inválido. Use 1-6."}), 400
    try:
        return jsonify(ModelosDuplaSenaService.gerar_apostas_modelo(modelo_id))
    except Exception as e:
        return jsonify({"error":str(e)}), 500

@modelos_bp.route('/api/backtesting', methods=['POST'])
def api_backtesting():
    try:
        resultado = ModelosDuplaSenaService.backtesting_modelos()
        res = jsonify(resultado)
        import gc
        gc.collect()
        return res
    except Exception as e:
        return jsonify({"error":str(e)}), 500
