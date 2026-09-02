"""
analise_maismilionaria_service.py
==================================
Análise estatística da +Milionária:
  - 50 dezenas (01-50)  → frequência e atraso por dezena
  - 6 trevos  (01-06)  → frequência e atraso por trevo
"""
from models.shared import db
from models.sorteio_maismilionaria import SorteioMaisMilionaria
from sqlalchemy import desc

TOTAL_DEZENAS = 50
TOTAL_TREVOS  = 6
NUM_SORT_DEZ  = 6
NUM_SORT_TRV  = 2


class AnaliseMaisMilionariaService:

    @staticmethod
    def analise_geral():
        sorteios = db.session.query(SorteioMaisMilionaria).order_by(
            desc(SorteioMaisMilionaria.concurso)
        ).all()

        if not sorteios:
            return None

        total  = len(sorteios)
        ultimo = sorteios[0].concurso

        # Dezenas
        freq_dez  = {d: 0 for d in range(1, TOTAL_DEZENAS + 1)}
        visto_dez = {d: 0 for d in range(1, TOTAL_DEZENAS + 1)}

        # Trevos
        freq_trv  = {t: 0 for t in range(1, TOTAL_TREVOS + 1)}
        visto_trv = {t: 0 for t in range(1, TOTAL_TREVOS + 1)}

        for s in sorteios:
            for d in s.dezenas():
                freq_dez[d] += 1
                if visto_dez[d] == 0:
                    visto_dez[d] = s.concurso
            for t in s.trevos():
                freq_trv[t] += 1
                if visto_trv[t] == 0:
                    visto_trv[t] = s.concurso

        dados_dez = []
        for d in range(1, TOTAL_DEZENAS + 1):
            atraso = (ultimo - visto_dez[d]) if visto_dez[d] > 0 else total
            pct    = round(freq_dez[d] / total * 100, 1) if total > 0 else 0
            dados_dez.append({
                "dezena": d, "dezena_fmt": f"{d:02d}",
                "freq": freq_dez[d], "atraso": atraso, "pct": pct
            })

        dados_trv = []
        for t in range(1, TOTAL_TREVOS + 1):
            atraso = (ultimo - visto_trv[t]) if visto_trv[t] > 0 else total
            pct    = round(freq_trv[t] / total * 100, 1) if total > 0 else 0
            dados_trv.append({
                "trevo": t, "trevo_fmt": f"{t:02d}",
                "freq": freq_trv[t], "atraso": atraso, "pct": pct
            })

        return {
            "dados":           dados_dez,
            "dados_trevos":    dados_trv,
            "total_sorteios":  total,
            "ultimo_concurso": ultimo,
            "esperado_pct_dez": round(NUM_SORT_DEZ / TOTAL_DEZENAS * 100, 1),  # 12%
            "esperado_pct_trv": round(NUM_SORT_TRV / TOTAL_TREVOS  * 100, 1),  # 33.3%
        }

    @staticmethod
    def ultimos_sorteios():
        sorteios = db.session.query(SorteioMaisMilionaria).order_by(
            desc(SorteioMaisMilionaria.concurso)
        ).all()
        return [
            {
                "concurso": s.concurso,
                "data":     s.data,
                "dezenas":  s.dezenas_lista(),
                "dezenas_ordem": s.dezenas_ordem_lista(),
                "trevos":   s.trevos_lista(),
                "trevos_ordem": s.trevos_ordem_lista(),
            }
            for s in sorteios
        ]
