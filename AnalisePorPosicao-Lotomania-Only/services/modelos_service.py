"""
modelos_service.py  (Lotomania)
================================
Geração de apostas pelos 6 Modelos Estratégicos para Lotomania.

Lotomania: 100 dezenas (00-99), jogador escolhe 50, sorteiam 20.
Gerar 50 dezenas por aposta — 14 apostas por modelo (2 × 7 faixas de dezenas).

MODELOS:
  M1 — Conservador       : 25 quentes (top-freq) + 25 atrasadas
  M2 — Atraso Forte      : top-50 dezenas mais atrasadas
  M3 — Frequência        : top-50 dezenas mais frequentes
  M4 — Misto Inteligente : faixas intercaladas (freq pares, atraso ímpares por dezena)
  M5 — Espelho           : usa a dezena espelho (99 - d) das top-freq
  M6 — Aleatório Ponderado: seleção ponderada por frequência histórica
"""

import random
from models.shared import db
from models.sorteio_lotomania import SorteioLotomania
from sqlalchemy import desc

TOTAL_DEZENAS = 100
NUM_ESCOLHA   = 50    # jogador marca 50
NUM_APOSTAS   = 14    # 14 apostas por modelo

MODELOS = {
    1: {"nome": "Conservador",         "emoji": "🔹", "subtitulo": "25 quentes + 25 atrasadas",            "cor": "#1a6e3c", "estrutura": "Top25-FREQ + Top25-ATR"},
    2: {"nome": "Atraso Controlado",        "emoji": "🔸", "subtitulo": "Top-50 mais atrasadas",                "cor": "#c47a1e", "estrutura": "Top50-ATR"},
    3: {"nome": "Núcleo Forte",          "emoji": "🔥", "subtitulo": "Top-50 mais frequentes",               "cor": "#8b1a1a", "estrutura": "Top50-FREQ"},
    4: {"nome": "Rotação Inteligente",   "emoji": "🔄", "subtitulo": "Freq nas pares · Atraso nas ímpares",  "cor": "#1a3a8b", "estrutura": "FREQ(par) + ATR(ímpar)"},
    5: {"nome": "Frequência Dominante",             "emoji": "📈", "subtitulo": "Dezenas espelho (99-n) das top-freq",  "cor": "#5a1a8b", "estrutura": "Espelho(Top50-FREQ)"},
    6: {"nome": "Ciclo Anterior", "emoji": "♻️", "subtitulo": "Peso histórico + aleatoriedade",       "cor": "#1a5c6e", "estrutura": "Prob(freq) × 50"},
}


class ModelosLotomaniaService:

    @staticmethod
    def _build_stats():
        """
        Para cada dezena (00-99) calcula freq e atraso.
        Retorna (freq, atraso, ultimo_concurso, total).
        """
        sorteios = db.session.query(SorteioLotomania).order_by(
            desc(SorteioLotomania.concurso)
        ).all()

        if not sorteios:
            return None, None, None, None

        total = len(sorteios)
        ultimo = sorteios[0].concurso

        freq  = {d: 0 for d in range(TOTAL_DEZENAS)}
        visto = {d: 0 for d in range(TOTAL_DEZENAS)}

        for s in sorteios:
            for d in s.dezenas():
                freq[d] += 1
                if visto[d] == 0:
                    visto[d] = s.concurso

        atraso = {}
        for d in range(TOTAL_DEZENAS):
            atraso[d] = (ultimo - visto[d]) if visto[d] > 0 else total

        return freq, atraso, ultimo, total

    @staticmethod
    def _gerar_aposta(modelo_id, freq, atraso, rng):
        """Gera 50 dezenas conforme a estratégia do modelo."""
        todos = list(range(TOTAL_DEZENAS))

        if modelo_id == 1:  # Conservador: 25 freq + 25 atraso
            top_freq = sorted(todos, key=lambda d: -freq[d])[:25]
            top_atr  = sorted(todos, key=lambda d: -atraso[d])[:25]
            pool = list(set(top_freq) | set(top_atr))
            # Completa até 50 se precisar
            restantes = [d for d in todos if d not in pool]
            pool += restantes[:max(0, NUM_ESCOLHA - len(pool))]
            return sorted(rng.sample(pool, min(NUM_ESCOLHA, len(pool))))

        elif modelo_id == 2:  # Atraso Forte: top-50 atrasadas
            pool = sorted(todos, key=lambda d: -atraso[d])[:NUM_ESCOLHA]
            return sorted(pool)

        elif modelo_id == 3:  # Frequência: top-50 mais frequentes
            pool = sorted(todos, key=lambda d: -freq[d])[:NUM_ESCOLHA]
            return sorted(pool)

        elif modelo_id == 4:  # Misto: pares=freq, ímpares=atraso
            pares   = [d for d in todos if d % 2 == 0]
            impares = [d for d in todos if d % 2 != 0]
            top_pares   = sorted(pares,   key=lambda d: -freq[d])[:25]
            top_impares = sorted(impares, key=lambda d: -atraso[d])[:25]
            pool = list(set(top_pares) | set(top_impares))
            restantes = [d for d in todos if d not in pool]
            pool += restantes[:max(0, NUM_ESCOLHA - len(pool))]
            return sorted(rng.sample(pool, min(NUM_ESCOLHA, len(pool))))

        elif modelo_id == 5:  # Espelho: 99 - dezena das top-freq
            top_freq = sorted(todos, key=lambda d: -freq[d])[:NUM_ESCOLHA]
            pool = list(set([(99 - d) for d in top_freq]))
            restantes = [d for d in todos if d not in pool]
            pool += restantes[:max(0, NUM_ESCOLHA - len(pool))]
            return sorted(pool[:NUM_ESCOLHA])

        elif modelo_id == 6:  # Ponderado por frequência
            total_f = sum(freq.values()) or 1
            pesos = [freq[d] / total_f for d in todos]
            escolhidos = set()
            tentativas = 0
            while len(escolhidos) < NUM_ESCOLHA and tentativas < 500:
                d = rng.choices(todos, weights=pesos, k=1)[0]
                escolhidos.add(d)
                tentativas += 1
            # Completa se necessário
            if len(escolhidos) < NUM_ESCOLHA:
                restantes = [d for d in todos if d not in escolhidos]
                escolhidos.update(restantes[:NUM_ESCOLHA - len(escolhidos)])
            return sorted(escolhidos)

        return sorted(rng.sample(todos, NUM_ESCOLHA))

    @staticmethod
    def gerar_apostas_modelo(modelo_id: int):
        freq, atraso, ultimo_concurso, total = ModelosLotomaniaService._build_stats()
        if freq is None:
            return {"error": "Sem dados no banco de dados."}

        cfg = MODELOS[modelo_id]
        apostas = []
        vistos  = set()
        tentativas = 0

        while len(apostas) < NUM_APOSTAS and tentativas < NUM_APOSTAS * 30:
            rng = random.Random(tentativas + modelo_id * 1000)
            dezenas = ModelosLotomaniaService._gerar_aposta(modelo_id, freq, atraso, rng)
            chave = tuple(dezenas)
            if chave not in vistos:
                vistos.add(chave)
                apostas.append({
                    "aposta_num": len(apostas) + 1,
                    "dezenas":    dezenas,
                    "formatado":  " - ".join(f"{d:02d}" for d in dezenas),
                })
            tentativas += 1

        # Estatísticas de pool para exibição
        top10_freq = sorted(range(TOTAL_DEZENAS), key=lambda d: -freq[d])[:10]
        top10_atr  = sorted(range(TOTAL_DEZENAS), key=lambda d: -atraso[d])[:10]

        return {
            "modelo_id":       modelo_id,
            "modelo_nome":     cfg["nome"],
            "modelo_emoji":    cfg["emoji"],
            "estrutura":       cfg["estrutura"],
            "ultimo_concurso": ultimo_concurso,
            "total_geradas":   len(apostas),
            "apostas":         apostas,
            "pool_info": {
                "top10_freq": [f"{d:02d}" for d in top10_freq],
                "top10_atr":  [f"{d:02d}" for d in top10_atr],
            },
        }

    @staticmethod
    def backtesting_modelos():
        """
        Para cada modelo gera 14 apostas e confere contra o histórico.
        Conta acertos: 20, 19..15 = prêmio; 0 = prêmio especial.
        """
        freq, atraso, ultimo_concurso, total_sorteios = ModelosLotomaniaService._build_stats()
        if freq is None:
            return {"error": "Sem dados no banco de dados."}

        sorteios = db.session.query(SorteioLotomania).all()

        ranking = []
        for modelo_id in range(1, 7):
            cfg = MODELOS[modelo_id]

            apostas = []
            vistos  = set()
            tentativas = 0
            while len(apostas) < NUM_APOSTAS and tentativas < NUM_APOSTAS * 30:
                rng = random.Random(tentativas + modelo_id * 1000)
                dezenas = ModelosLotomaniaService._gerar_aposta(modelo_id, freq, atraso, rng)
                chave = tuple(dezenas)
                if chave not in vistos:
                    vistos.add(chave)
                    apostas.append(set(dezenas))
                tentativas += 1

            hits = {20:0, 19:0, 18:0, 17:0, 16:0, 15:0, 0:0}
            total_premios  = 0
            melhor_acerto  = 0
            melhor_concurso = None

            for s in sorteios:
                sorteadas = s.dezenas()
                for aposta in apostas:
                    acertos = len(aposta & sorteadas)
                    if acertos >= 15:
                        hits[min(acertos, 20)] = hits.get(min(acertos, 20), 0) + 1
                        total_premios += 1
                    elif acertos == 0:
                        hits[0] += 1
                        total_premios += 1
                    if acertos > melhor_acerto:
                        melhor_acerto   = acertos
                        melhor_concurso = s.concurso

            score = (hits.get(20,0)*10000 + hits.get(19,0)*1000 +
                     hits.get(18,0)*200  + hits.get(17,0)*50  +
                     hits.get(16,0)*10   + hits.get(15,0)*3   +
                     hits.get(0,0)*5)

            ranking.append({
                "modelo_id":       modelo_id,
                "modelo_nome":     cfg["nome"],
                "modelo_emoji":    cfg["emoji"],
                "estrutura":       cfg["estrutura"],
                "cor":             cfg["cor"],
                "total_premios":   total_premios,
                "hits_20":         hits.get(20, 0),
                "hits_19":         hits.get(19, 0),
                "hits_18":         hits.get(18, 0),
                "hits_17":         hits.get(17, 0),
                "hits_16":         hits.get(16, 0),
                "hits_15":         hits.get(15, 0),
                "hits_0":          hits.get(0, 0),
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
            {
                "id":        mid,
                "nome":      cfg["nome"],
                "emoji":     cfg["emoji"],
                "subtitulo": cfg["subtitulo"],
                "cor":       cfg["cor"],
                "estrutura": cfg["estrutura"],
            }
            for mid, cfg in MODELOS.items()
        ]
