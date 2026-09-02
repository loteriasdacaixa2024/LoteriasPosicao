from flask import Blueprint, render_template, jsonify
from models.shared import db
from models.sorteio_timemania import SorteioTimemania
from services.analise_timemania_service import AnaliseTimemaniaSService
from sqlalchemy import desc

conferencia_bp = Blueprint('conferencia', __name__)

@conferencia_bp.route('/')
def conferencia_index():
    return render_template('conferencia.html')

@conferencia_bp.route('/api/conferir', methods=['POST'])
def api_conferir():
    try:
        analise = AnaliseTimemaniaSService.analise_geral()
        if not analise:
            return jsonify({"status":"error","message":"Sem dados no banco."}), 404

        sniper_dez = sorted(
            [d["dezena"] for d in sorted(analise["dados"], key=lambda x:-x["freq"])[:10]]
        )
        top_time   = sorted(analise["dados_times"], key=lambda x:-x["freq"])[0]
        sniper_time_num  = top_time["time_num"]
        sniper_time_nome = top_time["time_nome"]
        sniper_set = set(sniper_dez)

        sorteios = db.session.query(SorteioTimemania).order_by(
            desc(SorteioTimemania.concurso)
        ).all()

        resultados = []
        for s in sorteios:
            ac_dez  = len(sniper_set & s.dezenas())
            ac_time = (s.time_num == sniper_time_num) if s.time_num else False
            resultados.append({
                "concurso":         s.concurso,
                "data":             s.data,
                "dezenas":          s.dezenas_lista(),
                "time_num":         s.time_num,
                "time_nome":        s.time_nome,
                "sniper_dez":       sniper_dez,
                "sniper_time_num":  sniper_time_num,
                "sniper_time_nome": sniper_time_nome,
                "acertos_dez":      ac_dez,
                "acerto_time":      ac_time,
            })

        return jsonify({"status":"success","resultados":resultados})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500
