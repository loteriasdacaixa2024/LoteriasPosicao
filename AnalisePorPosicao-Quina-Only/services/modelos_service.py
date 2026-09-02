"""
modelos_service.py  (Quina)
===========================
6 Modelos Estratégicos — Quina: 80 dezenas (01-80), escolher 5.
14 apostas por modelo (2 × 7 — alinhado à semana de sorteios).

MODELOS:
  M1 — Conservador       : top-freq + top-atraso balanceados
  M2 — Atraso Forte      : top-5 mais atrasadas
  M3 — Frequência        : top-5 mais frequentes
  M4 — Misto Inteligente : freq nas dezenas baixas (1-40) / atraso nas altas (41-80)
  M5 — Sequencial        : janelas de 16 dezenas rotativas por atraso
  M6 — Aleatório Ponderado: seleção ponderada por frequência histórica
"""

import random
from models.shared import db
from models.sorteio_quina import SorteioQuina
from sqlalchemy import desc

TOTAL_DEZENAS = 80
NUM_ESCOLHA   = 5
NUM_APOSTAS   = 14

MODELOS = {
    1: {"nome": "Conservador",         "emoji": "🔹", "subtitulo": "Top-freq + Top-atraso equilibrados",       "cor": "#1a6e3c", "estrutura": "Top10-FREQ ∪ Top10-ATR → 5"},
    2: {"nome": "Atraso Controlado",        "emoji": "🔸", "subtitulo": "Aposta nas 5 mais atrasadas",              "cor": "#c47a1e", "estrutura": "Top5-ATR"},
    3: {"nome": "Núcleo Forte",     "emoji": "🔥", "subtitulo": "As 5 dezenas mais frequentes no histórico","cor": "#8b1a1a", "estrutura": "Top5-FREQ"},
    4: {"nome": "Rotação Inteligente",   "emoji": "🔄", "subtitulo": "Freq 1-40 · Atraso 41-80",                "cor": "#1a3a8b", "estrutura": "FREQ(baixas) + ATR(altas)"},
    5: {"nome": "Frequência Dominante",   "emoji": "📈", "subtitulo": "Janelas de 16 dezenas por atraso",         "cor": "#5a1a8b", "estrutura": "Janela-ATR × 5 dezenas"},
    6: {"nome": "Ciclo Anterior", "emoji": "♻️", "subtitulo": "Peso histórico + aleatoriedade controlada","cor": "#1a5c6e", "estrutura": "Prob(freq) × 5"},
}


class ModelosQuinaService:

    @staticmethod
    def _build_stats():
        sorteios = db.session.query(SorteioQuina).order_by(
            desc(SorteioQuina.concurso)
        ).all()

        if not sorteios:
            return None, None, None, None

        total  = len(sorteios)
        ultimo = sorteios[0].concurso

        freq  = {d: 0 for d in range(1, TOTAL_DEZENAS + 1)}
        visto = {d: 0 for d in range(1, TOTAL_DEZENAS + 1)}

        for s in sorteios:
            for d in s.dezenas():
                freq[d] += 1
                if visto[d] == 0:
                    visto[d] = s.concurso

        atraso = {d: (ultimo - visto[d]) if visto[d] > 0 else total
                  for d in range(1, TOTAL_DEZENAS + 1)}

        return freq, atraso, ultimo, total

    @staticmethod
    def _gerar_aposta(modelo_id, freq, atraso, rng, offset=0):
        todos = list(range(1, TOTAL_DEZENAS + 1))

        if modelo_id == 1:  # Conservador: pool = top10-freq ∪ top10-atr
            top_freq = sorted(todos, key=lambda d: -freq[d])[:10]
            top_atr  = sorted(todos, key=lambda d: -atraso[d])[:10]
            pool = list(set(top_freq) | set(top_atr))
            return sorted(rng.sample(pool, min(NUM_ESCOLHA, len(pool))))

        elif modelo_id == 2:  # Atraso Forte
            pool = sorted(todos, key=lambda d: -atraso[d])[:15]
            return sorted(rng.sample(pool, NUM_ESCOLHA))

        elif modelo_id == 3:  # Frequência pura
            pool = sorted(todos, key=lambda d: -freq[d])[:15]
            return sorted(rng.sample(pool, NUM_ESCOLHA))

        elif modelo_id == 4:  # Misto: baixas=freq, altas=atraso
            baixas = [d for d in todos if d <= 40]
            altas  = [d for d in todos if d > 40]
            top_b  = sorted(baixas, key=lambda d: -freq[d])[:10]
            top_a  = sorted(altas,  key=lambda d: -atraso[d])[:10]
            pool = list(set(top_b) | set(top_a))
            return sorted(rng.sample(pool, min(NUM_ESCOLHA, len(pool))))

        elif modelo_id == 5:  # Janela Sequencial (16 janelas de 5)
            # Divide as 80 dezenas em 16 janelas, escolhe a mais atrasada
            janela_idx = offset % 16
            inicio = janela_idx * 5 + 1  # 1,6,11,...,76
            janela = list(range(inicio, min(inicio + 5, 81)))
            if len(janela) < NUM_ESCOLHA:
                janela += list(range(1, NUM_ESCOLHA - len(janela) + 1))
            return sorted(janela[:NUM_ESCOLHA])

        elif modelo_id == 6:  # Ponderado por frequência
            total_f = sum(freq.values()) or 1
            pesos = [freq[d] / total_f for d in todos]
            escolhidos = set()
            tentativas = 0
            while len(escolhidos) < NUM_ESCOLHA and tentativas < 200:
                d = rng.choices(todos, weights=pesos, k=1)[0]
                escolhidos.add(d)
                tentativas += 1
            restantes = [d for d in todos if d not in escolhidos]
            while len(escolhidos) < NUM_ESCOLHA:
                escolhidos.add(restantes.pop(0))
            return sorted(escolhidos)

        return sorted(rng.sample(todos, NUM_ESCOLHA))

    @staticmethod
    def gerar_apostas_modelo(modelo_id: int):
        freq, atraso, ultimo_concurso, total = ModelosQuinaService._build_stats()
        if freq is None:
            return {"error": "Sem dados no banco."}

        cfg = MODELOS[modelo_id]
        apostas = []
        vistos  = set()
        tentativas = 0

        while len(apostas) < NUM_APOSTAS and tentativas < NUM_APOSTAS * 50:
            rng = random.Random(tentativas + modelo_id * 1000)
            dezenas = ModelosQuinaService._gerar_aposta(modelo_id, freq, atraso, rng, offset=tentativas)
            chave = tuple(dezenas)
            if chave not in vistos:
                vistos.add(chave)
                apostas.append({
                    "aposta_num": len(apostas) + 1,
                    "dezenas":    dezenas,
                    "formatado":  " - ".join(f"{d:02d}" for d in dezenas),
                })
            tentativas += 1

        # Top-5 freq e atraso para pool info
        top5_freq = sorted(range(1, TOTAL_DEZENAS + 1), key=lambda d: -freq[d])[:5]
        top5_atr  = sorted(range(1, TOTAL_DEZENAS + 1), key=lambda d: -atraso[d])[:5]

        return {
            "modelo_id":       modelo_id,
            "modelo_nome":     cfg["nome"],
            "modelo_emoji":    cfg["emoji"],
            "estrutura":       cfg["estrutura"],
            "ultimo_concurso": ultimo_concurso,
            "total_geradas":   len(apostas),
            "apostas":         apostas,
            "pool_info": {
                "top5_freq": [f"{d:02d}" for d in top5_freq],
                "top5_atr":  [f"{d:02d}" for d in top5_atr],
            },
        }

    @staticmethod
    def backtesting_modelos():
        freq, atraso, ultimo_concurso, total_sorteios = ModelosQuinaService._build_stats()
        if freq is None:
            return {"error": "Sem dados no banco."}

        sorteios = db.session.query(SorteioQuina).all()
        ranking  = []

        for modelo_id in range(1, 7):
            cfg = MODELOS[modelo_id]

            apostas = []
            vistos  = set()
            tentativas = 0
            while len(apostas) < NUM_APOSTAS and tentativas < NUM_APOSTAS * 50:
                rng = random.Random(tentativas + modelo_id * 1000)
                dezenas = ModelosQuinaService._gerar_aposta(modelo_id, freq, atraso, rng, offset=tentativas)
                chave = tuple(dezenas)
                if chave not in vistos:
                    vistos.add(chave)
                    apostas.append(set(dezenas))
                tentativas += 1

            hits = {5: 0, 4: 0, 3: 0, 2: 0}
            total_premios   = 0
            melhor_acerto   = 0
            melhor_concurso = None

            for s in sorteios:
                sorteadas = s.dezenas()
                for aposta in apostas:
                    ac = len(aposta & sorteadas)
                    if ac >= 2:
                        hits[min(ac, 5)] = hits.get(min(ac, 5), 0) + 1
                        if ac >= 2:
                            total_premios += 1
                    if ac > melhor_acerto:
                        melhor_acerto   = ac
                        melhor_concurso = s.concurso

            score = hits[5]*5000 + hits[4]*200 + hits[3]*10 + hits[2]

            ranking.append({
                "modelo_id":       modelo_id,
                "modelo_nome":     cfg["nome"],
                "modelo_emoji":    cfg["emoji"],
                "estrutura":       cfg["estrutura"],
                "cor":             cfg["cor"],
                "total_premios":   total_premios,
                "hits_5":          hits[5],
                "hits_4":          hits[4],
                "hits_3":          hits[3],
                "hits_2":          hits[2],
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
            {"id": mid, "nome": cfg["nome"], "emoji": cfg["emoji"],
             "subtitulo": cfg["subtitulo"], "cor": cfg["cor"], "estrutura": cfg["estrutura"]}
            for mid, cfg in MODELOS.items()
        ]
