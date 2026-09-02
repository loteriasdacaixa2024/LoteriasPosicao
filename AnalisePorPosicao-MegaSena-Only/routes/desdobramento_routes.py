from flask import Blueprint, render_template, jsonify, request
from services.desdobramento_service import DesdobramentoMegaSenaService
from services.ciclo_service import CicloMegaSenaService
from datetime import datetime

desdobramento_bp = Blueprint('desdobramento', __name__)

@desdobramento_bp.route('/')
def desdobramento_index():
    """Renderiza a interface do Desdobramento Inteligente"""
    try:
        ciclo_info = CicloMegaSenaService.obter_ciclo_atual()
    except Exception as e:
        print(f"Erro ao obter ciclo Mega-Sena: {e}")
        ciclo_info = {
            "ciclo_num": 1,
            "dezenas_sorteadas": [],
            "dezenas_faltantes": list(range(1, 61)),
            "total_sorteadas": 0,
            "total_faltantes": 60,
            "concursos_no_ciclo": 0
        }
    return render_template('desdobramento.html', ciclo=ciclo_info)

@desdobramento_bp.route('/api/ciclo', methods=['GET'])
def api_ciclo():
    """Retorna o ciclo ativo atual da Mega-Sena"""
    try:
        ciclo_info = CicloMegaSenaService.obter_ciclo_atual()
        return jsonify({"status": "success", **ciclo_info})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@desdobramento_bp.route('/api/sugestoes-colunas', methods=['GET'])
def api_sugestoes_colunas():
    """Retorna sugestões de colunas quentes, atrasadas e balanceadas"""
    try:
        sugestoes = DesdobramentoMegaSenaService.obter_sugestoes_colunas()
        return jsonify({"status": "success", "sugestoes": sugestoes})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@desdobramento_bp.route('/api/desdobrar', methods=['POST'])
def api_desdobrar():
    """Cria, valida e salva um desdobramento"""
    try:
        data = request.get_json() or {}
        numeros = data.get('numeros', [])
        nome = data.get('nome', f"Desdobramento {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        modo = data.get('modo', 'bronze').lower()

        if len(numeros) != 16:
            return jsonify({"status": "error", "message": "Deve fornecer exatamente 16 números."}), 400

        for num in numeros:
            if num < 1 or num > 60:
                return jsonify({"status": "error", "message": "Os números devem estar entre 01 e 60."}), 400

        # Enforce exactly 4 columns with exactly 4 numbers each
        colunas = {}
        for n in numeros:
            col = 10 if n % 10 == 0 else n % 10
            if col not in colunas:
                colunas[col] = []
            colunas[col].append(n)
        
        if len(colunas) != 4:
            return jsonify({"status": "error", "message": "Deve selecionar dezenas de exatamente 4 colunas."}), 400
            
        for col, dezenas in colunas.items():
            if len(dezenas) != 4:
                return jsonify({"status": "error", "message": f"A coluna {col} deve conter exatamente 4 dezenas."}), 400

        # Persistir no banco usando o serviço
        id_salvo = DesdobramentoMegaSenaService.salvar_desdobramento(nome, numeros, modo)
        
        # Buscar completo para retornar os detalhes calculados e salvos
        detalhes = DesdobramentoMegaSenaService.buscar_por_id(id_salvo)
        
        if not detalhes:
            return jsonify({"status": "error", "message": "Erro ao recuperar desdobramento salvo."}), 500

        return jsonify({
            "status": "success",
            "sucesso": True,
            "id": detalhes["id"],
            "nome": detalhes["nome"],
            "data_criacao": detalhes["data_criacao"],
            "numeros": detalhes["numeros"],
            "modo": detalhes["modo"],
            "total_apostas": detalhes["total_apostas"],
            "grupos": detalhes["grupos"],
            "pares": detalhes["pares"],
            "apostas": detalhes["apostas"]
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@desdobramento_bp.route('/api/desdobramentos', methods=['GET'])
def api_listar_desdobramentos():
    """Retorna todos os desdobramentos salvos"""
    try:
        lista = DesdobramentoMegaSenaService.listar_todos()
        return jsonify({"status": "success", "desdobramentos": lista})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@desdobramento_bp.route('/api/desdobramento/<int:id>', methods=['GET'])
def api_buscar_desdobramento(id):
    """Busca um desdobramento completo pelo ID"""
    try:
        detalhes = DesdobramentoMegaSenaService.buscar_por_id(id)
        if not detalhes:
            return jsonify({"status": "error", "message": "Desdobramento não encontrado."}), 404
        return jsonify({"status": "success", "desdobramento": detalhes})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@desdobramento_bp.route('/api/desdobramento/<int:id>', methods=['DELETE'])
def api_deletar_desdobramento(id):
    """Deleta um desdobramento pelo ID"""
    try:
        sucesso = DesdobramentoMegaSenaService.deletar_por_id(id)
        if not sucesso:
            return jsonify({"status": "error", "message": "Desdobramento não encontrado."}), 404
        return jsonify({"status": "success", "sucesso": True})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
