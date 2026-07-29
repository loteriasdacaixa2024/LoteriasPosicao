"""
analise_quina_service.py
========================
Análise estatística da Quina: 80 dezenas (01-80), sorteiam 5.
"""

from models.shared import db
from models.sorteio_quina import SorteioQuina
from sqlalchemy import desc

TOTAL_DEZENAS = 80   # 01 a 80
NUM_SORTEADAS = 5


class AnaliseQuinaService:

    @staticmethod
    def analise_geral():
        sorteios = db.session.query(SorteioQuina).order_by(
            desc(SorteioQuina.concurso)
        ).all()

        if not sorteios:
            return None

        total  = len(sorteios)
        ultimo = sorteios[0].concurso

        freq  = {d: 0 for d in range(1, TOTAL_DEZENAS + 1)}
        visto = {d: 0 for d in range(1, TOTAL_DEZENAS + 1)}

        for s in sorteios:
            for d in s.dezenas():
                freq[d] += 1
                if visto[d] == 0:
                    visto[d] = s.concurso

        resultado = []
        for d in range(1, TOTAL_DEZENAS + 1):
            atraso = (ultimo - visto[d]) if visto[d] > 0 else total
            pct    = round(freq[d] / total * 100, 1) if total > 0 else 0
            resultado.append({
                "dezena":     d,
                "dezena_fmt": f"{d:02d}",
                "freq":       freq[d],
                "atraso":     atraso,
                "pct":        pct,
            })

        return {
            "dados":           resultado,
            "total_sorteios":  total,
            "ultimo_concurso": ultimo,
            "esperado_pct":    round(NUM_SORTEADAS / TOTAL_DEZENAS * 100, 1),  # 6.25%
        }

    @staticmethod
    def ultimos_sorteios():
        sorteios = db.session.query(SorteioQuina).order_by(
            desc(SorteioQuina.concurso)
        ).all()
        return [
            {"concurso": s.concurso, "data": s.data, "dezenas": s.dezenas_lista(), "dezenas_ordem": s.dezenas_ordem_lista()}
            for s in sorteios
        ]
