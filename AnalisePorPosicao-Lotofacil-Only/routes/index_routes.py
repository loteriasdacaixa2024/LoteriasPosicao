from flask import Blueprint, render_template, jsonify, request
from models.sorteio_lotofacil import SorteioLotofacil
from services.api_lotofacil_service import ApiLotofacilService
from models.shared import db
from sqlalchemy import desc

index_bp = Blueprint('index', __name__)

@index_bp.route('/')
def index():
    return render_template('index.html')

@index_bp.route('/api/status-banco', methods=['GET'])
def api_status_banco():
    try:
        return jsonify({"status": "success", **ApiLotofacilService.status_banco()})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@index_bp.route('/api/sincronizar', methods=['POST'])
def sincronizar_api():
    try:
        data = request.get_json(silent=True) or {}
        modo = data.get("modo", "completo")
        limite = int(data.get("limite", 60))
        teto = data.get("teto_concurso")
        teto = int(teto) if teto else None
        resultado = ApiLotofacilService.sincronizar_banco(
            modo=modo, limite=limite, teto_concurso=teto,
        )
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"status": "error", "message": f"Erro fatal ao sincronizar: {str(e)}"})

@index_bp.route('/api/ultimos-sorteios')
def ultimos_sorteios():
    from sqlalchemy import desc
    sorteios = db.session.query(SorteioLotofacil).order_by(desc(SorteioLotofacil.concurso)).all()
    dados = []
    for s in sorteios:
        dados.append({
            "concurso": s.concurso,
            "data": s.data,
            "dezenas": s.dezenas_lista(),
            "dezenas_ordem": s.dezenas_ordem_lista(),
        })
    return jsonify({"sorteios": dados})
