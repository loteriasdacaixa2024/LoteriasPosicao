"""
analise_lotomania_service.py
============================
Análise estatística das dezenas da Lotomania.

Lotomania: 100 dezenas (00-99), sorteiam 20, jogador marca 50.
Análise: frequência e atraso de cada dezena nos sorteios históricos.
"""

from models.shared import db
from models.sorteio_lotomania import SorteioLotomania
from sqlalchemy import desc

TOTAL_DEZENAS = 100   # 00 a 99
NUM_SORTEADAS = 20    # sorteadas por concurso


class AnaliseLotomaniaService:

    @staticmethod
    def analise_geral():
        """
        Para cada dezena (00-99) calcula:
          - freq:   quantas vezes apareceu no histórico
          - atraso: concursos desde a última aparição
          - pct:    % de sorteios em que apareceu
        Retorna lista ordenada por dezena (00, 01, ..., 99).
        """
        sorteios = db.session.query(SorteioLotomania).order_by(
            desc(SorteioLotomania.concurso)
        ).all()

        if not sorteios:
            return None

        total = len(sorteios)
        ultimo = sorteios[0].concurso

        freq  = {d: 0 for d in range(TOTAL_DEZENAS)}
        visto = {d: 0 for d in range(TOTAL_DEZENAS)}  # último concurso em que apareceu

        for s in sorteios:
            for d in s.dezenas():
                freq[d] += 1
                if visto[d] == 0:
                    visto[d] = s.concurso

        resultado = []
        for d in range(TOTAL_DEZENAS):
            atraso = (ultimo - visto[d]) if visto[d] > 0 else total
            pct = round(freq[d] / total * 100, 1) if total > 0 else 0
            resultado.append({
                "dezena":  d,
                "dezena_fmt": f"{d:02d}",
                "freq":    freq[d],
                "atraso":  atraso,
                "pct":     pct,
            })

        return {
            "dados":          resultado,
            "total_sorteios": total,
            "ultimo_concurso": ultimo,
            "esperado_pct":   round(NUM_SORTEADAS / TOTAL_DEZENAS * 100, 1),  # 20%
        }

    @staticmethod
    def ultimos_sorteios():
        """Retorna os últimos `limit` sorteios para exibição."""
        sorteios = db.session.query(SorteioLotomania).order_by(
            desc(SorteioLotomania.concurso)
        ).all()

        return [
            {
                "concurso": s.concurso,
                "data":     s.data,
                "dezenas":  s.dezenas_lista(),
                "dezenas_ordem": s.dezenas_ordem_lista(),
            }
            for s in sorteios
        ]
