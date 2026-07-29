"""
analise_timemania_service.py
==============================
80 dezenas (01-80)  → freq/atraso por dezena
80 times do coração → freq/atraso por time
"""
from models.shared import db
from models.sorteio_timemania import SorteioTimemania, TIMES_DO_CORACAO
from sqlalchemy import desc

TOTAL_DEZ    = 80
NUM_SORT_DEZ = 7   # sorteadas por concurso (jogador marca 10)
TOTAL_TIMES  = 80


class AnaliseTimemaniaSService:

    @staticmethod
    def analise_geral():
        sorteios = db.session.query(SorteioTimemania).order_by(
            desc(SorteioTimemania.concurso)
        ).all()

        if not sorteios:
            return None

        total  = len(sorteios)
        ultimo = sorteios[0].concurso

        freq_dez  = {d: 0 for d in range(1, TOTAL_DEZ + 1)}
        visto_dez = {d: 0 for d in range(1, TOTAL_DEZ + 1)}
        freq_time = {t: 0 for t in range(1, TOTAL_TIMES + 1)}
        visto_time= {t: 0 for t in range(1, TOTAL_TIMES + 1)}

        for s in sorteios:
            for d in s.dezenas():
                freq_dez[d] += 1
                if visto_dez[d] == 0: visto_dez[d] = s.concurso
            if s.time_num and 1 <= s.time_num <= TOTAL_TIMES:
                freq_time[s.time_num] += 1
                if visto_time[s.time_num] == 0: visto_time[s.time_num] = s.concurso

        dados_dez = []
        for d in range(1, TOTAL_DEZ + 1):
            atraso = (ultimo - visto_dez[d]) if visto_dez[d] > 0 else total
            pct    = round(freq_dez[d] / total * 100, 1) if total > 0 else 0
            dados_dez.append({
                "dezena": d, "dezena_fmt": f"{d:02d}",
                "freq": freq_dez[d], "atraso": atraso, "pct": pct
            })

        dados_time = []
        for t in range(1, TOTAL_TIMES + 1):
            atraso = (ultimo - visto_time[t]) if visto_time[t] > 0 else total
            pct    = round(freq_time[t] / total * 100, 1) if total > 0 else 0
            dados_time.append({
                "time_num":  t,
                "time_nome": TIMES_DO_CORACAO.get(t, f"Time {t}"),
                "freq":  freq_time[t],
                "atraso": atraso,
                "pct":   pct,
            })

        return {
            "dados":            dados_dez,
            "dados_times":      dados_time,
            "total_sorteios":   total,
            "ultimo_concurso":  ultimo,
            "esperado_pct_dez": round(NUM_SORT_DEZ / TOTAL_DEZ  * 100, 1),  # 12.5%
            "esperado_pct_time":round(1             / TOTAL_TIMES * 100, 1), # 1.25%
        }

    @staticmethod
    def ultimos_sorteios():
        sorteios = db.session.query(SorteioTimemania).order_by(
            desc(SorteioTimemania.concurso)
        ).all()
        return [
            {
                "concurso":  s.concurso,
                "data":      s.data,
                "dezenas":   s.dezenas_lista(),
                "dezenas_ordem": s.dezenas_ordem_lista(),
                "time_num":  s.time_num,
                "time_nome": s.time_nome,
            }
            for s in sorteios
        ]
