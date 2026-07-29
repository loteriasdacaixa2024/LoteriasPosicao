from flask import Blueprint, render_template, jsonify
from models.shared import db
from models.sorteio_lotomania import SorteioLotomania
from services.analise_lotomania_service import AnaliseLotomaniaService
from sqlalchemy import desc

conferencia_bp = Blueprint('conferencia', __name__)

@conferencia_bp.route('/')
def conferencia_index():
    return render_template('conferencia.html')

@conferencia_bp.route('/api/conferir', methods=['POST'])
def api_conferir():
    """
    Confere os últimos 200 concursos contra a aposta Sniper
    (top-20 dezenas mais frequentes).
    """
    try:
        analise = AnaliseLotomaniaService.analise_geral()
        if not analise:
            return jsonify({"status": "error", "message": "Sem dados no banco."}), 404

        # Top-20 dezenas como aposta sniper
        dados = analise["dados"]
        aposta_sniper = sorted(
            [d["dezena"] for d in sorted(dados, key=lambda x: -x["freq"])[:20]]
        )
        aposta_sniper_set = set(aposta_sniper)

        sorteios = db.session.query(SorteioLotomania).order_by(
            desc(SorteioLotomania.concurso)
        ).all()

        resultados = []
        for s in sorteios:
            sorteadas = s.dezenas_lista()
            sorteadas_set = set(sorteadas)
            acertos = len(aposta_sniper_set & sorteadas_set)
            resultados.append({
                "concurso":      s.concurso,
                "data":          s.data,
                "dezenas":       sorteadas,
                "aposta_sniper": aposta_sniper,
                "acertos":       acertos,
            })

        return jsonify({"status": "success", "resultados": resultados})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
