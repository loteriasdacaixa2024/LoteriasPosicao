from flask import Blueprint, render_template, jsonify
from models.shared import db
from models.sorteio_maismilionaria import SorteioMaisMilionaria
from services.analise_maismilionaria_service import AnaliseMaisMilionariaService
from sqlalchemy import desc

conferencia_bp = Blueprint('conferencia', __name__)

@conferencia_bp.route('/')
def conferencia_index():
    return render_template('conferencia.html')

@conferencia_bp.route('/api/conferir', methods=['POST'])
def api_conferir():
    """Confere os últimos 200 concursos contra aposta Sniper:
       Top-6 dezenas mais frequentes + top-2 trevos mais frequentes.
    """
    try:
        analise = AnaliseMaisMilionariaService.analise_geral()
        if not analise:
            return jsonify({"status":"error","message":"Sem dados no banco."}), 404

        sniper_dez = sorted(
            [d["dezena"] for d in sorted(analise["dados"], key=lambda x:-x["freq"])[:6]]
        )
        sniper_trv = sorted(
            [t["trevo"] for t in sorted(analise["dados_trevos"], key=lambda x:-x["freq"])[:2]]
        )
        sniper_dez_set = set(sniper_dez)
        sniper_trv_set = set(sniper_trv)

        sorteios = db.session.query(SorteioMaisMilionaria).order_by(
            desc(SorteioMaisMilionaria.concurso)
        ).all()

        resultados = []
        for s in sorteios:
            ac_dez = len(sniper_dez_set & s.dezenas())
            ac_trv = len(sniper_trv_set & s.trevos())
            resultados.append({
                "concurso":   s.concurso,
                "data":       s.data,
                "dezenas":    s.dezenas_lista(),
                "trevos":     s.trevos_lista(),
                "sniper_dez": sniper_dez,
                "sniper_trv": sniper_trv,
                "acertos_dez": ac_dez,
                "acertos_trv": ac_trv,
            })

        return jsonify({"status":"success","resultados":resultados})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500
