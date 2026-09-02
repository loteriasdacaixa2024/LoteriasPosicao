from flask import Blueprint, render_template, jsonify
from models.shared import db
from models.sorteio_quina import SorteioQuina
from services.analise_quina_service import AnaliseQuinaService
from sqlalchemy import desc

conferencia_bp = Blueprint('conferencia', __name__)

@conferencia_bp.route('/')
def conferencia_index():
    return render_template('conferencia.html')

@conferencia_bp.route('/api/conferir', methods=['POST'])
def api_conferir():
    """Confere últimos 200 concursos contra aposta Sniper (top-5 mais frequentes)."""
    try:
        analise = AnaliseQuinaService.analise_geral()
        if not analise:
            return jsonify({"status": "error", "message": "Sem dados no banco."}), 404

        aposta_sniper = sorted(
            [d["dezena"] for d in sorted(analise["dados"], key=lambda x: -x["freq"])[:5]]
        )
        aposta_sniper_set = set(aposta_sniper)

        sorteios = db.session.query(SorteioQuina).order_by(
            desc(SorteioQuina.concurso)
        ).all()

        resultados = []
        for s in sorteios:
            sorteadas = s.dezenas_lista()
            acertos = len(aposta_sniper_set & set(sorteadas))
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
