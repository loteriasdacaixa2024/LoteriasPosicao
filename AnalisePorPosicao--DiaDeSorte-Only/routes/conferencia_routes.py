from flask import Blueprint, render_template, jsonify
from models.shared import db
from models.sorteio_diadesorte import SorteioDiaDeSorte, mes_abrev_de
from services.analise_diadesorte_service import AnaliseDiaDeSorteService
from services.cores_meses_service import CoresMesesService
from sqlalchemy import desc

conferencia_bp = Blueprint('conferencia', __name__)

@conferencia_bp.route('/')
def conferencia_index():
    return render_template('conferencia.html', meses_cores=CoresMesesService.obter_cores())

@conferencia_bp.route('/api/conferir', methods=['POST'])
def api_conferir():
    try:
        analise = AnaliseDiaDeSorteService.analise_geral()
        if not analise:
            return jsonify({"status":"error","message":"Sem dados no banco."}), 404

        sniper_dez = sorted(
            [d["dezena"] for d in sorted(analise["dados"], key=lambda x:-x["freq"])[:7]]
        )
        top_mes = sorted(analise["dados_meses"], key=lambda x:-x["freq"])[0]
        sniper_mes_num  = top_mes["mes_num"]
        sniper_mes_nome = top_mes["mes_nome"]
        sniper_mes_abrev = top_mes.get("mes_abrev") or mes_abrev_de(sniper_mes_num, sniper_mes_nome)
        sniper_set = set(sniper_dez)

        sorteios = db.session.query(SorteioDiaDeSorte).order_by(
            desc(SorteioDiaDeSorte.concurso)
        ).all()

        resultados = []
        for s in sorteios:
            ac_dez = len(sniper_set & s.dezenas())
            ac_mes = (s.mes_num == sniper_mes_num) if s.mes_num else False
            resultados.append({
                "concurso":         s.concurso,
                "data":             s.data,
                "dezenas":          s.dezenas_lista(),
                "dezenas_ordem":    s.dezenas_ordem_lista(),
                "mes_num":          s.mes_num,
                "mes_nome":         s.mes_nome,
                "mes_abrev":        s.mes_abrev(),
                "sniper_dez":       sniper_dez,
                "sniper_mes_num":   sniper_mes_num,
                "sniper_mes_nome":  sniper_mes_nome,
                "sniper_mes_abrev": sniper_mes_abrev,
                "acertos_dez":      ac_dez,
                "acerto_mes":       ac_mes,
            })

        return jsonify({"status":"success","resultados":resultados})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500
