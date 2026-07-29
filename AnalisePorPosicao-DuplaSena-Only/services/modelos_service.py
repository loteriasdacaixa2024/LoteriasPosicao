"""
modelos_service.py  (Dupla Sena)
=================================
6 Modelos Estratégicos — Dupla Sena: 50 dezenas (01-50), escolher 6.
14 apostas por modelo.

⚠️ MECÂNICA: cada aposta concorre a 2 sorteios.
O backtesting avalia acertos contra AMBOS os sorteios de cada concurso.
Scoring:
  Sena  (6 acertos) em qualquer sorteio = 60.000 pts
  Quina (5 acertos)                      =  2.000 pts
  Quadra(4 acertos)                      =     50 pts
  Score é multiplicado quando ganha nos DOIS sorteios.

MODELOS:
  M1 — Conservador       : pool de top-freq + top-atraso combinados
  M2 — Atraso Forte      : mais atrasadas em ambos os sorteios
  M3 — Frequência Dupla  : top-freq no 1º e 2º sorteio combinados
  M4 — Misto 1ºS+2ºS     : mais freq no 1º sorteio + mais at. no 2º sortio
  M5 — Décadas           : 1 dezena de cada faixa de 10 (5 faixas → 5 + 1 extra)
  M6 — Aleatório Ponderado: pesos combinados de freq nos dois sorteios
"""
import random
from models.shared import db
from models.sorteio_duplasena import SorteiosDuplaSena
from sqlalchemy import desc

TOTAL_DEZENAS = 50
NUM_ESCOLHA   = 6
NUM_APOSTAS   = 14

MODELOS = {
    1: {"nome":"Conservador",         "emoji":"🔹","subtitulo":"Top-freq + top-atraso (ambos sorteios)","cor":"#1a6e3c","estrutura":"Top12-FREQ ∪ Top12-ATR → 6"},
    2: {"nome":"Atraso Controlado",        "emoji":"🔸","subtitulo":"Dezenas mais atrasadas em qualquer sorteio","cor":"#c47a1e","estrutura":"Top15-ATR → 6"},
    3: {"nome":"Núcleo Forte",    "emoji":"🔥","subtitulo":"Top-freq combinando 1º e 2º sorteios","cor":"#8b1a1a","estrutura":"Top15-FREQ(1+2) → 6"},
    4: {"nome":"Rotação Inteligente", "emoji":"🔄","subtitulo":"Top-freq 1º sorteio + top-atraso 2º sorteio","cor":"#1a3a8b","estrutura":"FREQ(S1)+ATR(S2)→6"},
    5: {"nome":"Frequência Dominante",             "emoji":"📈","subtitulo":"1 dezena por faixa de 10 + 1 extra freq","cor":"#5a1a8b","estrutura":"1/faixa×5 + 1-FREQ"},
    6: {"nome":"Ciclo Anterior", "emoji":"♻️","subtitulo":"Peso histórico combinado (1º+2º sorteio)","cor":"#1a5c6e","estrutura":"Prob(freq1+freq2)×6"},
}


class ModelosDuplaSenaService:

    @staticmethod
    def _build_stats():
        sorteios = db.session.query(SorteiosDuplaSena).order_by(
            desc(SorteiosDuplaSena.concurso)
        ).all()

        if not sorteios:
            return None, None, None, None, None, None

        total  = len(sorteios)
        ultimo = sorteios[0].concurso

        freq     = {d: 0 for d in range(1, TOTAL_DEZENAS + 1)}
        freq1    = {d: 0 for d in range(1, TOTAL_DEZENAS + 1)}
        freq2    = {d: 0 for d in range(1, TOTAL_DEZENAS + 1)}
        visto    = {d: 0 for d in range(1, TOTAL_DEZENAS + 1)}

        for s in sorteios:
            for d in s.sorteio1():
                freq[d] += 1; freq1[d] += 1
                if visto[d] == 0: visto[d] = s.concurso
            for d in s.sorteio2():
                freq[d] += 1; freq2[d] += 1
                if visto[d] == 0: visto[d] = s.concurso

        atraso = {d: (ultimo - visto[d]) if visto[d] > 0 else total
                  for d in range(1, TOTAL_DEZENAS + 1)}

        return freq, freq1, freq2, atraso, ultimo, total

    @staticmethod
    def _gerar_aposta(modelo_id, freq, freq1, freq2, atraso, rng, offset=0):
        todos = list(range(1, TOTAL_DEZENAS + 1))

        if modelo_id == 1:
            top_f = sorted(todos, key=lambda d: -freq[d])[:12]
            top_a = sorted(todos, key=lambda d: -atraso[d])[:12]
            pool  = list(set(top_f) | set(top_a))
            return sorted(rng.sample(pool, min(NUM_ESCOLHA, len(pool))))

        elif modelo_id == 2:
            pool = sorted(todos, key=lambda d: -atraso[d])[:15]
            return sorted(rng.sample(pool, NUM_ESCOLHA))

        elif modelo_id == 3:
            pool = sorted(todos, key=lambda d: -freq[d])[:15]
            return sorted(rng.sample(pool, NUM_ESCOLHA))

        elif modelo_id == 4:
            top_s1 = sorted(todos, key=lambda d: -freq1[d])[:10]
            top_s2 = sorted(todos, key=lambda d: -atraso[d])[:10]
            pool   = list(set(top_s1) | set(top_s2))
            return sorted(rng.sample(pool, min(NUM_ESCOLHA, len(pool))))

        elif modelo_id == 5:
            faixas = [(1,10),(11,20),(21,30),(31,40),(41,50)]
            dez = []
            for ini, fim in faixas:
                faixa = list(range(ini, fim + 1))
                top   = sorted(faixa, key=lambda d: -freq[d])
                dez.append(top[(offset // 3) % len(top)])
            dez = list(dict.fromkeys(dez))
            if len(dez) < NUM_ESCOLHA:
                extra = sorted(todos, key=lambda d: -freq[d])
                for e in extra:
                    if e not in dez: dez.append(e)
                    if len(dez) == NUM_ESCOLHA: break
            return sorted(dez[:NUM_ESCOLHA])

        elif modelo_id == 6:
            total_f = sum(freq.values()) or 1
            pesos   = [freq[d] / total_f for d in todos]
            escolhidos = set()
            t = 0
            while len(escolhidos) < NUM_ESCOLHA and t < 200:
                d = rng.choices(todos, weights=pesos, k=1)[0]
                escolhidos.add(d); t += 1
            restantes = [d for d in todos if d not in escolhidos]
            while len(escolhidos) < NUM_ESCOLHA:
                escolhidos.add(restantes.pop(0))
            return sorted(escolhidos)

        return sorted(rng.sample(todos, NUM_ESCOLHA))

    @staticmethod
    def gerar_apostas_modelo(modelo_id: int):
        freq, freq1, freq2, atraso, ultimo, total = ModelosDuplaSenaService._build_stats()
        if freq is None:
            return {"error": "Sem dados no banco."}

        cfg = MODELOS[modelo_id]
        apostas, vistos, tentativas = [], set(), 0

        while len(apostas) < NUM_APOSTAS and tentativas < NUM_APOSTAS * 60:
            rng     = random.Random(tentativas + modelo_id * 1000)
            dezenas = ModelosDuplaSenaService._gerar_aposta(
                modelo_id, freq, freq1, freq2, atraso, rng, offset=tentativas
            )
            chave = tuple(dezenas)
            if chave not in vistos:
                vistos.add(chave)
                apostas.append({
                    "aposta_num": len(apostas) + 1,
                    "dezenas":    dezenas,
                    "formatado":  " - ".join(f"{d:02d}" for d in dezenas),
                })
            tentativas += 1

        top6_freq = sorted(range(1, TOTAL_DEZENAS + 1), key=lambda d: -freq[d])[:6]
        top6_atr  = sorted(range(1, TOTAL_DEZENAS + 1), key=lambda d: -atraso[d])[:6]

        return {
            "modelo_id":       modelo_id,
            "modelo_nome":     cfg["nome"],
            "modelo_emoji":    cfg["emoji"],
            "estrutura":       cfg["estrutura"],
            "ultimo_concurso": ultimo,
            "total_geradas":   len(apostas),
            "apostas":         apostas,
            "pool_info": {
                "top6_freq": [f"{d:02d}" for d in top6_freq],
                "top6_atr":  [f"{d:02d}" for d in top6_atr],
            },
        }

    @staticmethod
    def backtesting_modelos():
        freq, freq1, freq2, atraso, ultimo, total_sorteios = ModelosDuplaSenaService._build_stats()
        if freq is None:
            return {"error": "Sem dados no banco."}

        sorteios = db.session.query(SorteiosDuplaSena).all()
        ranking  = []

        for modelo_id in range(1, 7):
            cfg = MODELOS[modelo_id]
            apostas, vistos, tentativas = [], set(), 0
            while len(apostas) < NUM_APOSTAS and tentativas < NUM_APOSTAS * 60:
                rng     = random.Random(tentativas + modelo_id * 1000)
                dezenas = ModelosDuplaSenaService._gerar_aposta(
                    modelo_id, freq, freq1, freq2, atraso, rng, offset=tentativas
                )
                chave = tuple(dezenas)
                if chave not in vistos:
                    vistos.add(chave)
                    apostas.append(set(dezenas))
                tentativas += 1

            # Avalia cada aposta contra AMBOS os sorteios
            hits   = {6: 0, 5: 0, 4: 0}  # por sorteio (cada concurso = 2 oportunidades)
            score  = 0
            total_premios   = 0
            melhor_acerto   = 0
            melhor_concurso = None
            duplo_premio    = 0  # ganhou nos 2 sorteios do mesmo concurso

            for s in sorteios:
                s1, s2 = s.sorteio1(), s.sorteio2()
                for aposta in apostas:
                    ac1 = len(aposta & s1)
                    ac2 = len(aposta & s2)
                    ganhou1 = ac1 >= 4
                    ganhou2 = ac2 >= 4
                    if ganhou1:
                        hits[min(ac1, 6)] = hits.get(min(ac1, 6), 0) + 1
                        pts = 60000 if ac1 >= 6 else 2000 if ac1 == 5 else 50
                        score += pts; total_premios += 1
                    if ganhou2:
                        hits[min(ac2, 6)] = hits.get(min(ac2, 6), 0) + 1
                        pts = 60000 if ac2 >= 6 else 2000 if ac2 == 5 else 50
                        score += pts; total_premios += 1
                    if ganhou1 and ganhou2:
                        duplo_premio += 1   # ganhou nos dois sorteios do mesmo concurso!
                    max_ac = max(ac1, ac2)
                    if max_ac > melhor_acerto:
                        melhor_acerto   = max_ac
                        melhor_concurso = s.concurso

            ranking.append({
                "modelo_id":       modelo_id,
                "modelo_nome":     cfg["nome"],
                "modelo_emoji":    cfg["emoji"],
                "estrutura":       cfg["estrutura"],
                "cor":             cfg["cor"],
                "total_premios":   total_premios,
                "duplo_premio":    duplo_premio,
                "hits_6":          hits[6],
                "hits_5":          hits[5],
                "hits_4":          hits[4],
                "melhor_acerto":   melhor_acerto,
                "melhor_concurso": melhor_concurso,
                "score":           score,
            })

        ranking.sort(key=lambda x: -x["score"])
        for i, m in enumerate(ranking):
            m["posicao"] = i + 1

        return {
            "ultimo_concurso": ultimo,
            "total_sorteios":  total_sorteios,
            "total_draws":     total_sorteios * 2,
            "ranking":         ranking,
        }

    @staticmethod
    def listar_modelos():
        return [
            {"id":mid,"nome":cfg["nome"],"emoji":cfg["emoji"],
             "subtitulo":cfg["subtitulo"],"cor":cfg["cor"],"estrutura":cfg["estrutura"]}
            for mid, cfg in MODELOS.items()
        ]
