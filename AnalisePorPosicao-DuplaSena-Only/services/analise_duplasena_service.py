"""
analise_duplasena_service.py
=============================
Análise estatística da Dupla Sena.
50 dezenas (01–50). CADA concurso tem DOIS sorteios de 6 dezenas.
A frequência e o atraso são calculados combinando os dois sorteios.
"""
from models.shared import db
from models.sorteio_duplasena import SorteiosDuplaSena
from sqlalchemy import desc

TOTAL_DEZENAS   = 50
NUM_SORT_DEZ    = 6


class AnaliseDuplaSenaService:

    @staticmethod
    def analise_geral():
        sorteios = db.session.query(SorteiosDuplaSena).order_by(
            desc(SorteiosDuplaSena.concurso)
        ).all()

        if not sorteios:
            return None

        total  = len(sorteios)
        ultimo = sorteios[0].concurso

        freq  = {d: 0 for d in range(1, TOTAL_DEZENAS + 1)}
        freq1 = {d: 0 for d in range(1, TOTAL_DEZENAS + 1)}  # somente 1º sorteio
        freq2 = {d: 0 for d in range(1, TOTAL_DEZENAS + 1)}  # somente 2º sorteio
        visto = {d: 0 for d in range(1, TOTAL_DEZENAS + 1)}  # última vez (qualquer sorteio)

        for s in sorteios:
            for d in s.sorteio1():
                freq[d]  += 1
                freq1[d] += 1
                if visto[d] == 0:
                    visto[d] = s.concurso
            for d in s.sorteio2():
                freq[d]  += 1
                freq2[d] += 1
                if visto[d] == 0:
                    visto[d] = s.concurso

        resultado = []
        for d in range(1, TOTAL_DEZENAS + 1):
            atraso = (ultimo - visto[d]) if visto[d] > 0 else total
            pct    = round(freq[d] / (total * 2) * 100, 1) if total > 0 else 0  # /2 draws
            resultado.append({
                "dezena":     d,
                "dezena_fmt": f"{d:02d}",
                "freq":       freq[d],     # frequência total (ambos sorteios)
                "freq1":      freq1[d],    # somente 1º sorteio
                "freq2":      freq2[d],    # somente 2º sorteio
                "atraso":     atraso,
                "pct":        pct,
            })

        return {
            "dados":           resultado,
            "total_sorteios":  total,
            "total_draws":     total * 2,   # 2 sorteios por concurso
            "ultimo_concurso": ultimo,
            "esperado_pct":    round(NUM_SORT_DEZ / TOTAL_DEZENAS * 100, 1),  # 12%
        }

    @staticmethod
    def ultimos_sorteios():
        sorteios = db.session.query(SorteiosDuplaSena).order_by(
            desc(SorteiosDuplaSena.concurso)
        ).all()
        return [
            {
                "concurso": s.concurso,
                "data":     s.data,
                "sorteio1": s.sorteio1_lista(),
                "sorteio1_ordem": s.sorteio1_ordem_lista(),
                "sorteio2": s.sorteio2_lista(),
                "sorteio2_ordem": s.sorteio2_ordem_lista(),
            }
            for s in sorteios
        ]
