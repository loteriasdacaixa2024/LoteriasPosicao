from flask import Blueprint, render_template, jsonify
from models.shared import db
from models.sorteio_duplasena import SorteiosDuplaSena
from services.analise_duplasena_service import AnaliseDuplaSenaService
from sqlalchemy import desc

conferencia_bp = Blueprint('conferencia', __name__)

@conferencia_bp.route('/')
def conferencia_index():
    return render_template('conferencia.html')

@conferencia_bp.route('/api/conferir', methods=['POST'])
def api_conferir():
    """
    Confere últimos 200 concursos contra aposta Sniper (top-6 freq combinadas).
    Avalia acertos em AMBOS os sorteios de cada concurso.
    """
    try:
        analise = AnaliseDuplaSenaService.analise_geral()
        if not analise:
            return jsonify({"status":"error","message":"Sem dados no banco."}), 404

        sniper = sorted(
            [d["dezena"] for d in sorted(analise["dados"], key=lambda x:-x["freq"])[:6]]
        )
        sniper_set = set(sniper)

        sorteios = db.session.query(SorteiosDuplaSena).order_by(
            desc(SorteiosDuplaSena.concurso)
        ).all()

        resultados = []
        for s in sorteios:
            ac1 = len(sniper_set & s.sorteio1())
            ac2 = len(sniper_set & s.sorteio2())
            resultados.append({
                "concurso":     s.concurso,
                "data":         s.data,
                "sorteio1":     s.sorteio1_lista(),
                "sorteio2":     s.sorteio2_lista(),
                "sniper":       sniper,
                "acertos_s1":   ac1,
                "acertos_s2":   ac2,
                "melhor":       max(ac1, ac2),
                "duplo":        ac1 >= 4 and ac2 >= 4,  # ganhou nos dois?
            })

        return jsonify({"status":"success","resultados":resultados})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500
