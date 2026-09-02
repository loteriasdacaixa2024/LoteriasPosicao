"""
modelos_service.py  (Mega Sena)
================================
6 Modelos Estratégicos — Mega-Sena: 60 dezenas (01-60), escolher 6.
14 apostas por modelo.

MODELOS:
  M1 — Conservador       : top-freq + top-atraso balanceados (pool ∪)
  M2 — Atraso Forte      : top-6 mais atrasadas (com variação)
  M3 — Frequência Pura   : top-6 mais frequentes (com variação)
  M4 — Misto Inteligente : freq nas baixas (1-30) / atraso nas altas (31-60)
  M5 — Decades           : 1 dezena por faixa de 10 (6 faixas, 01-60)
  M6 — Aleatório Ponderado: peso histórico + aleatoriedade
"""
import random
from models.shared import db
from models.sorteio_megasena import SorteioMegaSena
from sqlalchemy import desc

TOTAL_DEZENAS = 60
NUM_ESCOLHA   = 6
NUM_APOSTAS   = 14

MODELOS = {
    1: {"nome":"Conservador",         "emoji":"🔹","subtitulo":"Top-freq + Top-atraso equilibrados","cor":"#1a6e3c","estrutura":"Top12-FREQ ∪ Top12-ATR → 6"},
    2: {"nome":"Atraso Controlado",        "emoji":"🔸","subtitulo":"As dezenas mais atrasadas do histórico","cor":"#c47a1e","estrutura":"Top12-ATR → 6"},
    3: {"nome":"Núcleo Forte",     "emoji":"🔥","subtitulo":"As dezenas mais frequentes do histórico","cor":"#8b1a1a","estrutura":"Top12-FREQ → 6"},
    4: {"nome":"Rotação Inteligente",   "emoji":"🔄","subtitulo":"Freq 01-30 · Atraso 31-60","cor":"#1a3a8b","estrutura":"FREQ(baixas)+ATR(altas)→6"},
    5: {"nome":"Frequência Dominante",             "emoji":"📈","subtitulo":"1 dezena por faixa de 10 (6 faixas)","cor":"#5a1a8b","estrutura":"1/faixa × 6 faixas"},
    6: {"nome":"Ciclo Anterior", "emoji":"♻️","subtitulo":"Peso histórico + aleatoriedade controlada","cor":"#1a5c6e","estrutura":"Prob(freq) × 6"},
}


class ModelosMegaSenaService:

    @staticmethod
    def _build_stats():
        sorteios = db.session.query(SorteioMegaSena).order_by(desc(SorteioMegaSena.concurso)).all()
        if not sorteios:
            return None, None, None, None
        total  = len(sorteios)
        ultimo = sorteios[0].concurso
        freq   = {d: 0 for d in range(1, TOTAL_DEZENAS + 1)}
        visto  = {d: 0 for d in range(1, TOTAL_DEZENAS + 1)}
        for s in sorteios:
            for d in s.dezenas():
                freq[d] += 1
                if visto[d] == 0:
                    visto[d] = s.concurso
        atraso = {d: (ultimo - visto[d]) if visto[d] > 0 else total for d in range(1, TOTAL_DEZENAS + 1)}
        return freq, atraso, ultimo, total

    @staticmethod
    def _gerar_aposta(modelo_id, freq, atraso, rng, offset=0):
        todos = list(range(1, TOTAL_DEZENAS + 1))

        if modelo_id == 1:  # Conservador
            top_freq = sorted(todos, key=lambda d: -freq[d])[:12]
            top_atr  = sorted(todos, key=lambda d: -atraso[d])[:12]
            pool = list(set(top_freq) | set(top_atr))
            return sorted(rng.sample(pool, min(NUM_ESCOLHA, len(pool))))

        elif modelo_id == 2:  # Atraso Forte
            pool = sorted(todos, key=lambda d: -atraso[d])[:18]
            return sorted(rng.sample(pool, NUM_ESCOLHA))

        elif modelo_id == 3:  # Frequência Pura
            pool = sorted(todos, key=lambda d: -freq[d])[:18]
            return sorted(rng.sample(pool, NUM_ESCOLHA))

        elif modelo_id == 4:  # Misto
            baixas = [d for d in todos if d <= 30]
            altas  = [d for d in todos if d > 30]
            top_b  = sorted(baixas, key=lambda d: -freq[d])[:10]
            top_a  = sorted(altas,  key=lambda d: -atraso[d])[:10]
            pool   = list(set(top_b) | set(top_a))
            return sorted(rng.sample(pool, min(NUM_ESCOLHA, len(pool))))

        elif modelo_id == 5:  # Décadas — 1 dezena por faixa de 10
            faixas = [(1,10),(11,20),(21,30),(31,40),(41,50),(51,60)]
            result = []
            for ini, fim in faixas:
                faixa_dez = list(range(ini, fim + 1))
                # Pega a mais frequente da faixa com jitter por offset
                top = sorted(faixa_dez, key=lambda d: -freq[d])
                idx = offset % max(1, len(top))
                result.append(top[idx % len(top)])
            return sorted(result)

        elif modelo_id == 6:  # Ponderado
            total_f = sum(freq.values()) or 1
            pesos = [freq[d] / total_f for d in todos]
            escolhidos = set()
            t = 0
            while len(escolhidos) < NUM_ESCOLHA and t < 200:
                d = rng.choices(todos, weights=pesos, k=1)[0]
                escolhidos.add(d)
                t += 1
            restantes = [d for d in todos if d not in escolhidos]
            while len(escolhidos) < NUM_ESCOLHA:
                escolhidos.add(restantes.pop(0))
            return sorted(escolhidos)

        return sorted(rng.sample(todos, NUM_ESCOLHA))

    @staticmethod
    def gerar_apostas_modelo(modelo_id: int):
        freq, atraso, ultimo_concurso, total = ModelosMegaSenaService._build_stats()
        if freq is None:
            return {"error": "Sem dados no banco."}

        cfg = MODELOS[modelo_id]
        apostas, vistos, tentativas = [], set(), 0

        while len(apostas) < NUM_APOSTAS and tentativas < NUM_APOSTAS * 50:
            rng = random.Random(tentativas + modelo_id * 1000)
            dezenas = ModelosMegaSenaService._gerar_aposta(modelo_id, freq, atraso, rng, offset=tentativas)
            chave = tuple(dezenas)
            if chave not in vistos:
                vistos.add(chave)
                apostas.append({
                    "aposta_num": len(apostas) + 1,
                    "dezenas": dezenas,
                    "formatado": " - ".join(f"{d:02d}" for d in dezenas),
                })
            tentativas += 1

        top6_freq = sorted(range(1, TOTAL_DEZENAS + 1), key=lambda d: -freq[d])[:6]
        top6_atr  = sorted(range(1, TOTAL_DEZENAS + 1), key=lambda d: -atraso[d])[:6]

        return {
            "modelo_id":       modelo_id,
            "modelo_nome":     cfg["nome"],
            "modelo_emoji":    cfg["emoji"],
            "estrutura":       cfg["estrutura"],
            "ultimo_concurso": ultimo_concurso,
            "total_geradas":   len(apostas),
            "apostas":         apostas,
            "pool_info": {
                "top6_freq": [f"{d:02d}" for d in top6_freq],
                "top6_atr":  [f"{d:02d}" for d in top6_atr],
            },
        }

    @staticmethod
    def backtesting_modelos():
        freq, atraso, ultimo_concurso, total_sorteios = ModelosMegaSenaService._build_stats()
        if freq is None:
            return {"error": "Sem dados no banco."}

        sorteios = db.session.query(SorteioMegaSena).all()
        ranking  = []

        for modelo_id in range(1, 7):
            cfg = MODELOS[modelo_id]
            apostas, vistos, tentativas = [], set(), 0
            while len(apostas) < NUM_APOSTAS and tentativas < NUM_APOSTAS * 50:
                rng = random.Random(tentativas + modelo_id * 1000)
                dezenas = ModelosMegaSenaService._gerar_aposta(modelo_id, freq, atraso, rng, offset=tentativas)
                chave = tuple(dezenas)
                if chave not in vistos:
                    vistos.add(chave)
                    apostas.append(set(dezenas))
                tentativas += 1

            hits = {6:0, 5:0, 4:0}
            total_premios = 0
            melhor_acerto = 0
            melhor_concurso = None

            for s in sorteios:
                sorteadas = s.dezenas()
                for aposta in apostas:
                    ac = len(aposta & sorteadas)
                    if ac >= 4:
                        hits[min(ac, 6)] = hits.get(min(ac, 6), 0) + 1
                        total_premios += 1
                    if ac > melhor_acerto:
                        melhor_acerto   = ac
                        melhor_concurso = s.concurso

            score = hits[6]*100000 + hits[5]*2000 + hits[4]*50

            ranking.append({
                "modelo_id":       modelo_id,
                "modelo_nome":     cfg["nome"],
                "modelo_emoji":    cfg["emoji"],
                "estrutura":       cfg["estrutura"],
                "cor":             cfg["cor"],
                "total_premios":   total_premios,
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
            "ultimo_concurso": ultimo_concurso,
            "total_sorteios":  total_sorteios,
            "ranking":         ranking,
        }

    @staticmethod
    def listar_modelos():
        return [
            {"id":mid,"nome":cfg["nome"],"emoji":cfg["emoji"],
             "subtitulo":cfg["subtitulo"],"cor":cfg["cor"],"estrutura":cfg["estrutura"]}
            for mid, cfg in MODELOS.items()
        ]
