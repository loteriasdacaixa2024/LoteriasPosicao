from datetime import datetime

from flask import Blueprint, jsonify, render_template, request

from services.ciclo_service import CicloMaisMilionariaService
from services.desdobramento_service import DesdobramentoMaisMilionariaService

desdobramento_bp = Blueprint('desdobramento', __name__)
MAX_DEZENA = 50


@desdobramento_bp.route('/')
def desdobramento_index():
    try:
        ciclo_info = CicloMaisMilionariaService.obter_ciclo_atual()
    except Exception as e:
        print(f"Erro ao obter ciclo: {e}")
        ciclo_info = {
            "ciclo_num": 1,
            "dezenas_sorteadas": [],
            "dezenas_faltantes": list(range(1, MAX_DEZENA + 1)),
            "total_sorteadas": 0,
            "total_faltantes": MAX_DEZENA,
            "concursos_no_ciclo": 0,
        }
    return render_template(
        'desdobramento.html',
        ciclo=ciclo_info,
        modalidade='+Milionária',
        max_dezena=MAX_DEZENA,
        suporta_trevo=True,
    )


@desdobramento_bp.route('/api/ciclo', methods=['GET'])
def api_ciclo():
    try:
        return jsonify({"status": "success", **CicloMaisMilionariaService.obter_ciclo_atual()})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@desdobramento_bp.route('/api/sugestoes-colunas', methods=['GET'])
def api_sugestoes_colunas():
    try:
        return jsonify({"status": "success", "sugestoes": DesdobramentoMaisMilionariaService.obter_sugestoes_colunas()})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


def _validar_colunas(numeros):
    colunas = {}
    for n in numeros:
        col = 10 if n % 10 == 0 else n % 10
        colunas.setdefault(col, []).append(n)
    if len(colunas) != 4:
        return "Deve selecionar dezenas de exatamente 4 colunas."
    for col, dezenas in colunas.items():
        if len(dezenas) != 4:
            return f"A coluna {col} deve conter exatamente 4 dezenas."
    return None


@desdobramento_bp.route('/api/desdobrar', methods=['POST'])
def api_desdobrar():
    try:
        data = request.get_json() or {}
        numeros = data.get('numeros', [])
        nome = data.get('nome', f"Desdobramento {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        modo = data.get('modo', 'bronze').lower()
        if len(numeros) != 16:
            return jsonify({"status": "error", "message": "Deve fornecer exatamente 16 números."}), 400
        for num in numeros:
            if num < 1 or num > MAX_DEZENA:
                return jsonify({"status": "error", "message": f"Os números devem estar entre 01 e {MAX_DEZENA:02d}."}), 400
        err = _validar_colunas(numeros)
        if err:
            return jsonify({"status": "error", "message": err}), 400
        id_salvo = DesdobramentoMaisMilionariaService.salvar_desdobramento(nome, numeros, modo)
        detalhes = DesdobramentoMaisMilionariaService.buscar_por_id(id_salvo)
        if not detalhes:
            return jsonify({"status": "error", "message": "Erro ao recuperar desdobramento salvo."}), 500
        return jsonify({"status": "success", "sucesso": True, **detalhes})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@desdobramento_bp.route('/api/desdobrar-trevos', methods=['POST'])
def api_desdobrar_trevos():
    try:
        data = request.get_json() or {}
        trevos = data.get('trevos', [])
        nome = data.get('nome', f"Trevos {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        if len(trevos) != 4:
            return jsonify({"status": "error", "message": "Selecione exatamente 4 trevos (1 a 6)."}), 400
        for t in trevos:
            if t < 1 or t > 6:
                return jsonify({"status": "error", "message": "Trevos devem estar entre 1 e 6."}), 400
        if len(set(trevos)) != 4:
            return jsonify({"status": "error", "message": "Os 4 trevos devem ser distintos."}), 400
        id_salvo = DesdobramentoMaisMilionariaService.salvar_desdobramento_trevos(nome, trevos)
        detalhes = DesdobramentoMaisMilionariaService.buscar_por_id(id_salvo)
        if not detalhes:
            return jsonify({"status": "error", "message": "Erro ao recuperar fechamento."}), 500
        return jsonify({"status": "success", "sucesso": True, **detalhes})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@desdobramento_bp.route('/api/desdobramentos', methods=['GET'])
def api_listar_desdobramentos():
    try:
        tipo = request.args.get('tipo')
        return jsonify({"status": "success", "desdobramentos": DesdobramentoMaisMilionariaService.listar_todos(tipo)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@desdobramento_bp.route('/api/desdobramento/<int:id>', methods=['GET'])
def api_buscar_desdobramento(id):
    try:
        detalhes = DesdobramentoMaisMilionariaService.buscar_por_id(id)
        if not detalhes:
            return jsonify({"status": "error", "message": "Desdobramento não encontrado."}), 404
        return jsonify({"status": "success", "desdobramento": detalhes})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@desdobramento_bp.route('/api/desdobramento/<int:id>', methods=['DELETE'])
def api_deletar_desdobramento(id):
    try:
        if not DesdobramentoMaisMilionariaService.deletar_por_id(id):
            return jsonify({"status": "error", "message": "Desdobramento não encontrado."}), 404
        return jsonify({"status": "success", "sucesso": True})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
