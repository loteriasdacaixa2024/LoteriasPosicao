"""
modelos_service.py  (+Milionária)
==================================
6 Modelos Estratégicos.
Cada aposta: 6 dezenas (01-50) + 2 trevos (01-06).
14 apostas por modelo.

Tabela de prêmios (scoring):
  6dez+2trv → 500.000 pts (Principal)
  6dez+1trv →  50.000 pts
  6dez+0trv →   5.000 pts
  5dez+2trv →   1.000 pts
  5dez+1trv →     300 pts
  4dez+2trv →     100 pts
  4dez+0trv →      10 pts

MODELOS:
  M1 — Conservador       : top-freq dez + top-freq trevo
  M2 — Atraso Forte      : top-atraso dez + top-atraso trevo
  M3 — Frequência Pura   : top-freq dez + par de trevos mais frequentes
  M4 — Misto Inteligente : freq nas baixas (1-25) / atraso nas altas (26-50)
  M5 — Décadas+Trevo     : 1 dezena por faixa de 10 + trevos equilibrados
  M6 — Aleatório Ponderado: pesos históricos para dez e trevos
"""
import random
from models.shared import db
from models.sorteio_maismilionaria import SorteioMaisMilionaria
from sqlalchemy import desc

TOTAL_DEZENAS = 50
TOTAL_TREVOS  = 6
NUM_DEZ       = 6
NUM_TRV       = 2
NUM_APOSTAS   = 14

MODELOS = {
    1: {"nome":"Conservador",         "emoji":"🔹","subtitulo":"Top-freq dezenas + top-freq trevos",       "cor":"#1a6e3c","estrutura":"Top12-FREQ(dez) + Top2-FREQ(trv)"},
    2: {"nome":"Atraso Controlado",        "emoji":"🔸","subtitulo":"Dezenas e trevos mais atrasados",           "cor":"#c47a1e","estrutura":"Top12-ATR(dez) + Top2-ATR(trv)"},
    3: {"nome":"Núcleo Forte",     "emoji":"🔥","subtitulo":"Top dezenas + par de trevos campeões",      "cor":"#8b1a1a","estrutura":"Top12-FREQ(dez) + 2-FREQ(trv)"},
    4: {"nome":"Rotação Inteligente",   "emoji":"🔄","subtitulo":"Freq 1-25 · Atraso 26-50 + trevos balanceados","cor":"#1a3a8b","estrutura":"FREQ(baixas)+ATR(altas)+TRV-BAL"},
    5: {"nome":"Frequência Dominante",     "emoji":"📈","subtitulo":"1 dezena/faixa × 5 faixas + trevos opostos","cor":"#5a1a8b","estrutura":"1/faixa×5 + TRV-opostos"},
    6: {"nome":"Ciclo Anterior", "emoji":"♻️","subtitulo":"Pesos históricos para dezenas e trevos",    "cor":"#1a5c6e","estrutura":"Prob(freq-dez) + Prob(freq-trv)"},
}


class ModelosMaisMilionariaService:

    @staticmethod
    def _build_stats():
        sorteios = db.session.query(SorteioMaisMilionaria).order_by(
            desc(SorteioMaisMilionaria.concurso)
        ).all()

        if not sorteios:
            return None, None, None, None, None, None

        total  = len(sorteios)
        ultimo = sorteios[0].concurso

        freq_dez  = {d: 0 for d in range(1, TOTAL_DEZENAS + 1)}
        visto_dez = {d: 0 for d in range(1, TOTAL_DEZENAS + 1)}
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

        atr_dez = {d: (ultimo - visto_dez[d]) if visto_dez[d] > 0 else total
                   for d in range(1, TOTAL_DEZENAS + 1)}
        atr_trv = {t: (ultimo - visto_trv[t]) if visto_trv[t] > 0 else total
                   for t in range(1, TOTAL_TREVOS + 1)}

        return freq_dez, atr_dez, freq_trv, atr_trv, ultimo, total

    @staticmethod
    def _gerar_trevos(estrategia, freq_trv, atr_trv, rng):
        """Gera 2 trevos conforme estratégia."""
        todos = list(range(1, TOTAL_TREVOS + 1))
        if estrategia == 'freq':
            pool = sorted(todos, key=lambda t: -freq_trv[t])[:4]
        elif estrategia == 'atr':
            pool = sorted(todos, key=lambda t: -atr_trv[t])[:4]
        elif estrategia == 'bal':
            # Balancear: 1 mais frequente + 1 mais atrasado
            top_f = sorted(todos, key=lambda t: -freq_trv[t])[0]
            top_a = sorted(todos, key=lambda t: -atr_trv[t])[0]
            pool  = list({top_f, top_a})
            if len(pool) < NUM_TRV:
                pool += [t for t in todos if t not in pool]
        elif estrategia == 'oposto':
            top2  = sorted(todos, key=lambda t: -freq_trv[t])[:2]
            opost = [(TOTAL_TREVOS + 1 - t) for t in top2]
            pool  = list(set(opost))
            if len(pool) < NUM_TRV:
                pool += [t for t in todos if t not in pool]
        else:
            pool = todos
        return sorted(rng.sample(pool, min(NUM_TRV, len(pool))))

    @staticmethod
    def _gerar_aposta(modelo_id, freq_dez, atr_dez, freq_trv, atr_trv, rng, offset=0):
        todos = list(range(1, TOTAL_DEZENAS + 1))

        if modelo_id == 1:
            pool = list(set(sorted(todos, key=lambda d: -freq_dez[d])[:12]) |
                        set(sorted(todos, key=lambda d: -atr_dez[d])[:12]))
            dez  = sorted(rng.sample(pool, min(NUM_DEZ, len(pool))))
            trv  = ModelosMaisMilionariaService._gerar_trevos('freq', freq_trv, atr_trv, rng)

        elif modelo_id == 2:
            pool = sorted(todos, key=lambda d: -atr_dez[d])[:18]
            dez  = sorted(rng.sample(pool, NUM_DEZ))
            trv  = ModelosMaisMilionariaService._gerar_trevos('atr', freq_trv, atr_trv, rng)

        elif modelo_id == 3:
            pool = sorted(todos, key=lambda d: -freq_dez[d])[:18]
            dez  = sorted(rng.sample(pool, NUM_DEZ))
            trv  = ModelosMaisMilionariaService._gerar_trevos('freq', freq_trv, atr_trv, rng)

        elif modelo_id == 4:
            baixas = sorted([d for d in todos if d <= 25], key=lambda d: -freq_dez[d])[:10]
            altas  = sorted([d for d in todos if d > 25],  key=lambda d: -atr_dez[d])[:10]
            pool   = list(set(baixas) | set(altas))
            dez    = sorted(rng.sample(pool, min(NUM_DEZ, len(pool))))
            trv    = ModelosMaisMilionariaService._gerar_trevos('bal', freq_trv, atr_trv, rng)

        elif modelo_id == 5:
            # 5 faixas de 10, mais 1 dezena extra do topo-freq
            faixas = [(1,10),(11,20),(21,30),(31,40),(41,50)]
            dez = []
            for ini, fim in faixas:
                faixa = list(range(ini, fim + 1))
                top   = sorted(faixa, key=lambda d: -freq_dez[d])
                dez.append(top[(offset // 3) % len(top)])
            # Remove duplicatas e completa
            dez = list(dict.fromkeys(dez))
            if len(dez) < NUM_DEZ:
                extra = sorted(todos, key=lambda d: -freq_dez[d])
                for e in extra:
                    if e not in dez:
                        dez.append(e)
                    if len(dez) == NUM_DEZ:
                        break
            dez = sorted(dez[:NUM_DEZ])
            trv = ModelosMaisMilionariaService._gerar_trevos('oposto', freq_trv, atr_trv, rng)

        elif modelo_id == 6:
            total_f = sum(freq_dez.values()) or 1
            pesos   = [freq_dez[d] / total_f for d in todos]
            escolhidos = set()
            t = 0
            while len(escolhidos) < NUM_DEZ and t < 200:
                d = rng.choices(todos, weights=pesos, k=1)[0]
                escolhidos.add(d)
                t += 1
            restantes = [d for d in todos if d not in escolhidos]
            while len(escolhidos) < NUM_DEZ:
                escolhidos.add(restantes.pop(0))
            dez = sorted(escolhidos)

            total_t = sum(freq_trv.values()) or 1
            ptrevos = [freq_trv[t] / total_t for t in range(1, TOTAL_TREVOS + 1)]
            t_set   = set()
            tt = 0
            while len(t_set) < NUM_TRV and tt < 50:
                v = rng.choices(list(range(1, TOTAL_TREVOS + 1)), weights=ptrevos, k=1)[0]
                t_set.add(v)
                tt += 1
            if len(t_set) < NUM_TRV:
                for extra in range(1, TOTAL_TREVOS + 1):
                    if extra not in t_set:
                        t_set.add(extra)
                    if len(t_set) == NUM_TRV:
                        break
            trv = sorted(t_set)

        else:
            dez = sorted(rng.sample(todos, NUM_DEZ))
            trv = sorted(rng.sample(list(range(1, TOTAL_TREVOS + 1)), NUM_TRV))

        return dez, trv

    @staticmethod
    def gerar_apostas_modelo(modelo_id: int):
        freq_dez, atr_dez, freq_trv, atr_trv, ultimo, total = ModelosMaisMilionariaService._build_stats()
        if freq_dez is None:
            return {"error": "Sem dados no banco."}

        cfg = MODELOS[modelo_id]
        apostas, vistos, tentativas = [], set(), 0

        while len(apostas) < NUM_APOSTAS and tentativas < NUM_APOSTAS * 60:
            rng    = random.Random(tentativas + modelo_id * 1000)
            dez, trv = ModelosMaisMilionariaService._gerar_aposta(
                modelo_id, freq_dez, atr_dez, freq_trv, atr_trv, rng, offset=tentativas
            )
            chave = (tuple(dez), tuple(trv))
            if chave not in vistos:
                vistos.add(chave)
                apostas.append({
                    "aposta_num": len(apostas) + 1,
                    "dezenas":    dez,
                    "trevos":     trv,
                    "formatado":  " - ".join(f"{d:02d}" for d in dez) + f"  🍀 {' - '.join(f'{t:02d}' for t in trv)}",
                })
            tentativas += 1

        top6_freq_dez = sorted(range(1, TOTAL_DEZENAS + 1), key=lambda d: -freq_dez[d])[:6]
        top6_atr_dez  = sorted(range(1, TOTAL_DEZENAS + 1), key=lambda d: -atr_dez[d])[:6]
        top_freq_trv  = sorted(range(1, TOTAL_TREVOS + 1),  key=lambda t: -freq_trv[t])
        top_atr_trv   = sorted(range(1, TOTAL_TREVOS + 1),  key=lambda t: -atr_trv[t])

        return {
            "modelo_id":       modelo_id,
            "modelo_nome":     cfg["nome"],
            "modelo_emoji":    cfg["emoji"],
            "estrutura":       cfg["estrutura"],
            "ultimo_concurso": ultimo,
            "total_geradas":   len(apostas),
            "apostas":         apostas,
            "pool_info": {
                "top6_freq_dez": [f"{d:02d}" for d in top6_freq_dez],
                "top6_atr_dez":  [f"{d:02d}" for d in top6_atr_dez],
                "freq_trevos":   [f"{t:02d}" for t in top_freq_trv],
                "atr_trevos":    [f"{t:02d}" for t in top_atr_trv],
            },
        }

    @staticmethod
    def backtesting_modelos():
        freq_dez, atr_dez, freq_trv, atr_trv, ultimo, total_sorteios = ModelosMaisMilionariaService._build_stats()
        if freq_dez is None:
            return {"error": "Sem dados no banco."}

        sorteios = db.session.query(SorteioMaisMilionaria).all()
        ranking  = []

        SCORE_TABLE = {
            (6,2): 500_000, (6,1): 50_000, (6,0): 5_000,
            (5,2): 1_000,   (5,1): 300,    (4,2): 100,
            (4,0): 10,
        }

        for modelo_id in range(1, 7):
            cfg = MODELOS[modelo_id]
            apostas, vistos, tentativas = [], set(), 0
            while len(apostas) < NUM_APOSTAS and tentativas < NUM_APOSTAS * 60:
                rng = random.Random(tentativas + modelo_id * 1000)
                dez, trv = ModelosMaisMilionariaService._gerar_aposta(
                    modelo_id, freq_dez, atr_dez, freq_trv, atr_trv, rng, offset=tentativas
                )
                chave = (tuple(dez), tuple(trv))
                if chave not in vistos:
                    vistos.add(chave)
                    apostas.append((set(dez), set(trv)))
                tentativas += 1

            hits   = {k: 0 for k in SCORE_TABLE}
            score  = 0
            total_premios   = 0
            melhor_score    = 0
            melhor_concurso = None

            for s in sorteios:
                sd, st = s.dezenas(), s.trevos()
                for aposta_dez, aposta_trv in apostas:
                    ad = len(aposta_dez & sd)
                    at = len(aposta_trv & st)
                    key = (min(ad, 6), at) if (min(ad, 6), at) in SCORE_TABLE else None
                    # Premia 4dez+0trv separado
                    if key is None and ad == 4 and at == 0:
                        key = (4, 0)
                    if key is not None:
                        hits[key] = hits.get(key, 0) + 1
                        pts = SCORE_TABLE[key]
                        score += pts
                        total_premios += 1
                        if pts > melhor_score:
                            melhor_score    = pts
                            melhor_concurso = s.concurso

            ranking.append({
                "modelo_id":       modelo_id,
                "modelo_nome":     cfg["nome"],
                "modelo_emoji":    cfg["emoji"],
                "estrutura":       cfg["estrutura"],
                "cor":             cfg["cor"],
                "total_premios":   total_premios,
                "hits_6_2":        hits.get((6,2), 0),
                "hits_6_1":        hits.get((6,1), 0),
                "hits_6_0":        hits.get((6,0), 0),
                "hits_5_2":        hits.get((5,2), 0),
                "hits_5_1":        hits.get((5,1), 0),
                "hits_4_2":        hits.get((4,2), 0),
                "hits_4_0":        hits.get((4,0), 0),
                "melhor_concurso": melhor_concurso,
                "score":           score,
            })

        ranking.sort(key=lambda x: -x["score"])
        for i, m in enumerate(ranking):
            m["posicao"] = i + 1

        return {
            "ultimo_concurso": ultimo,
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
