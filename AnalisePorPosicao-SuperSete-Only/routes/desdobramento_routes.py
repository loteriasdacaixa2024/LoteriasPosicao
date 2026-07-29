from flask import Blueprint, jsonify, render_template, request
from itertools import product

desdobramento_bp = Blueprint('desdobramento', __name__)


@desdobramento_bp.route('/')
def desdobramento_index():
    return render_template('desdobramento.html', modalidade='Super Sete')


@desdobramento_bp.route('/api/gerar', methods=['POST'])
def api_gerar():
    data = request.get_json() or {}
    colunas = data.get('colunas', [])
    if len(colunas) != 7:
        return jsonify({"status": "error", "message": "Informe 7 colunas."}), 400
    listas = []
    for i, c in enumerate(colunas, 1):
        vals = sorted({int(v) for v in c if str(v).isdigit() and 0 <= int(v) <= 9})
        if not vals:
            return jsonify({"status": "error", "message": f"Coluna {i} sem dígitos válidos (0-9)."}), 400
        if len(vals) > 3:
            return jsonify({"status": "error", "message": f"Coluna {i} excedeu 3 dígitos (limite oficial Caixa)."}), 400
        listas.append(vals)
    apostas = [list(p) for p in product(*listas)]
    if len(apostas) > 2187:
        return jsonify({"status": "error", "message": "Combinações acima do limite (2187 = 3^7). Reduza os dígitos por coluna."}), 400
    return jsonify({"status": "success", "total": len(apostas), "apostas": apostas})
