from flask import Blueprint, render_template, jsonify, request, Response
from datetime import datetime
from services.des2_service import Des2MegaSenaService
from services.des2_engine import validar_entrada

des2_bp = Blueprint('des2', __name__)


@des2_bp.route('/')
def des2_index():
    return render_template('des2.html')


@des2_bp.route('/api/config', methods=['GET'])
def api_config():
    try:
        return jsonify({"status": "success", **Des2MegaSenaService.obter_config()})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@des2_bp.route('/api/sugestoes', methods=['GET'])
def api_sugestoes():
    try:
        qtd = int(request.args.get('dezenas', 8))
        data = Des2MegaSenaService.obter_sugestoes(qtd)
        return jsonify({"status": "success", **data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@des2_bp.route('/api/desdobrar-colunas', methods=['POST'])
def api_desdobrar_colunas():
    """Retorna o desdobramento (15 pares) de cada coluna selecionada."""
    try:
        data = request.get_json() or {}
        colunas = [int(c) for c in data.get('colunas', [])]
        if not colunas:
            return jsonify({"status": "error", "message": "Selecione ao menos uma coluna."}), 400
        preview = Des2MegaSenaService.preview_desdobramento_colunas(colunas)
        qtd = int(data.get('qtd_dezenas', 0))
        if qtd:
            nec = qtd // 2
            preview["colunas_necessarias"] = nec
            preview["dezenas_por_jogo"] = nec * 2
            preview["formula"] = f"{nec} × 2 = {nec * 2} dezenas por jogo"
        return jsonify({"status": "success", **preview})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@des2_bp.route('/api/gerar', methods=['POST'])
def api_gerar():
    try:
        data = request.get_json() or {}
        colunas = data.get('colunas', [])
        qtd_dezenas = int(data.get('qtd_dezenas', 8))
        colunas = [int(c) for c in colunas]

        erro = validar_entrada(colunas, qtd_dezenas)
        if erro:
            return jsonify({"status": "error", "message": erro}), 400

        resultado = Des2MegaSenaService.gerar(colunas, qtd_dezenas)
        return jsonify({"status": "success", **resultado})
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@des2_bp.route('/api/conferir', methods=['POST'])
def api_conferir():
    try:
        data = request.get_json() or {}
        jogos = data.get('jogos', [])
        if not jogos:
            colunas = data.get('colunas', [])
            qtd = int(data.get('qtd_dezenas', 8))
            if colunas:
                res = Des2MegaSenaService.gerar([int(c) for c in colunas], qtd)
                jogos = res["jogos"]
            else:
                return jsonify({"status": "error", "message": "Informe jogos ou colunas para conferir."}), 400

        conferencia = Des2MegaSenaService.conferir_historico(jogos)
        if "erro" in conferencia:
            return jsonify({"status": "error", "message": conferencia["erro"]}), 404

        return jsonify({"status": "success", "conferencia": conferencia})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@des2_bp.route('/api/salvar', methods=['POST'])
def api_salvar():
    try:
        data = request.get_json() or {}
        nome = data.get('nome') or f"Des2 {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        colunas = [int(c) for c in data.get('colunas', [])]
        qtd = int(data.get('qtd_dezenas', 8))
        resultado = data.get('resultado')
        if not resultado:
            resultado = Des2MegaSenaService.gerar(colunas, qtd)
        id_ = Des2MegaSenaService.salvar_estrategia(nome, colunas, qtd, resultado)
        return jsonify({"status": "success", "id": id_, "nome": nome})
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@des2_bp.route('/api/estrategias', methods=['GET'])
def api_listar_estrategias():
    try:
        lista = Des2MegaSenaService.listar_estrategias()
        return jsonify({"status": "success", "estrategias": lista})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@des2_bp.route('/api/estrategia/<int:id_>', methods=['GET'])
def api_buscar_estrategia(id_):
    try:
        item = Des2MegaSenaService.buscar_estrategia(id_)
        if not item:
            return jsonify({"status": "error", "message": "Estratégia não encontrada."}), 404
        return jsonify({"status": "success", "estrategia": item})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@des2_bp.route('/api/estrategia/<int:id_>', methods=['DELETE'])
def api_deletar_estrategia(id_):
    try:
        if not Des2MegaSenaService.deletar_estrategia(id_):
            return jsonify({"status": "error", "message": "Estratégia não encontrada."}), 404
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@des2_bp.route('/api/exportar/txt', methods=['POST'])
def api_exportar_txt():
    try:
        data = request.get_json() or {}
        resultado = data.get("resultado")
        nome = data.get("nome", "Des2")
        if not resultado:
            return jsonify({"status": "error", "message": "Gere os jogos antes de exportar."}), 400
        texto = Des2MegaSenaService.exportar_txt(resultado, nome)
        return Response(
            texto,
            mimetype="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{nome}.txt"'},
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@des2_bp.route('/api/exportar/csv', methods=['POST'])
def api_exportar_csv():
    try:
        data = request.get_json() or {}
        resultado = data.get("resultado")
        nome = data.get("nome", "Des2")
        if not resultado:
            return jsonify({"status": "error", "message": "Gere os jogos antes de exportar."}), 400
        csv_content = Des2MegaSenaService.exportar_csv(resultado)
        return Response(
            "\ufeff" + csv_content,
            mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{nome}.csv"'},
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
