from flask import Blueprint, render_template, jsonify, request
from services.api_diadesorte_service import ApiDiaDeSorteService
from services.caixa_excel_service import atualizar_diadesorte, listar_premiacao_diadesorte

index_bp = Blueprint('index', __name__)

@index_bp.route('/')
def index():
    return render_template('index.html')

@index_bp.route('/api/status-banco', methods=['GET'])
def api_status_banco():
    try:
        return jsonify({"status": "success", **ApiDiaDeSorteService.status_banco()})
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
        resultado = ApiDiaDeSorteService.sincronizar_banco(
            modo=modo, limite=limite, teto_concurso=teto,
        )
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@index_bp.route("/api/premiacao-caixa", methods=["GET"])
def api_premiacao_caixa():
    try:
        page = int(request.args.get("page", 1))
        size = int(request.args.get("size", 50))
        return jsonify(listar_premiacao_diadesorte(page=page, size=size, paginar=True))
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@index_bp.route("/api/premiacao-caixa/atualizar", methods=["POST"])
def api_premiacao_caixa_atualizar():
    try:
        data = request.get_json(silent=True) or {}
        fonte = (data.get("fonte") or "api").strip().lower()
        baixar = data.get("baixar", fonte == "excel")
        if isinstance(baixar, str):
            baixar = baixar.strip().lower() not in ("0", "false", "nao", "não")
        limite = int(data.get("limite", 80))
        if fonte == "excel":
            return jsonify(atualizar_diadesorte(baixar=bool(baixar), fonte="excel"))
        from services.caixa_excel_service import backfill_premiacao_api
        return jsonify(backfill_premiacao_api(limite=limite, apenas_faltantes=True))
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@index_bp.route("/api/ranking-uf-pagamentos", methods=["GET"])
def api_ranking_uf_pagamentos():
    try:
        from services.caixa_excel_service import ranking_uf_pagamentos
        return jsonify(ranking_uf_pagamentos())
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
