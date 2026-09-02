"""
modelos_service.py  (Timemania)
================================
6 Modelos: 10 dezenas (01-80) + 1 Time do Coração (1-80)
14 apostas por modelo.

Tabela de prêmios (scoring para backtesting):
  10 dez + Time  → 5.000.000 pts
  10 dez          → 500.000 pts
   9 dez + Time  →  50.000 pts
   9 dez          →   5.000 pts
   8 dez + Time  →   1.000 pts
   8 dez          →     100 pts
   7 dez          →      10 pts
   Time (só)      →       1 pt

MODELOS:
  M1 — Conservador      : top-freq dez + time mais frequente
  M2 — Atraso Forte     : top-atraso dez + time mais atrasado
  M3 — Frequência Pura  : top-18 freq dez + top-freq time
  M4 — Misto Sniper     : top-freq (baixas 1-40) + top-atraso (altas 41-80) + top-freq time
  M5 — Oitavas          : 1-10 de cada oito faixas de 10, melhor por freq + top-freq time
  M6 — Aleatório Pond.  : pesos históricos dez + time
"""
import random
from models.shared import db
from models.sorteio_timemania import SorteioTimemania, TIMES_DO_CORACAO
from sqlalchemy import desc

TOTAL_DEZ   = 80
TOTAL_TIMES = 80
NUM_DEZ     = 10
NUM_APOSTAS = 14

MODELOS = {
    1: {"nome":"Conservador",       "emoji":"🔹","subtitulo":"Top-freq dezenas + time mais frequente",            "cor":"#1a6e3c","estrutura":"Top18-FREQ(dez) + TIME-FREQ"},
    2: {"nome":"Atraso Controlado",      "emoji":"🔸","subtitulo":"Mais atrasadas + time mais atrasado",               "cor":"#c47a1e","estrutura":"Top18-ATR + TIME-ATR"},
    3: {"nome":"Núcleo Forte",   "emoji":"🔥","subtitulo":"Top-18 freq + time campeão",                        "cor":"#8b1a1a","estrutura":"Top18-FREQ + TIME-TOP"},
    4: {"nome":"Rotação Inteligente",      "emoji":"🔄","subtitulo":"Freq nas baixas (1-40) + atraso nas altas (41-80)", "cor":"#1a3a8b","estrutura":"FREQ(1-40)+ATR(41-80)+TIME-FREQ"},
    5: {"nome":"Frequência Dominante",           "emoji":"📈","subtitulo":"1 dezena por faixa de 10 (8 faixas) + 2 extras",   "cor":"#5a1a8b","estrutura":"1/faixa×8 + 2-FREQ + TIME-FREQ"},
    6: {"nome":"Ciclo Anterior",   "emoji":"♻️","subtitulo":"Pesos históricos de freq para dez + time",          "cor":"#1a5c6e","estrutura":"Prob(freq-dez) + Prob(freq-time)"},
}

SCORE_TABLE = {
    (7, True):  5_000_000,
    (7, False):   500_000,
    (6, True):     50_000,
    (6, False):     5_000,
    (5, True):      1_000,
    (5, False):       100,
    (4, True):         20,
    (4, False):        10,
    (3, True):          8,
    (3, False):         5,
    (0, True):          1,
}


class ModelosTimemaniaService:

    @staticmethod
    def _build_stats():
        sorteios = db.session.query(SorteioTimemania).order_by(
            desc(SorteioTimemania.concurso)
        ).all()
        if not sorteios:
            return None, None, None, None, None, None

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

        atr_dez  = {d: (ultimo - visto_dez[d])  if visto_dez[d]  > 0 else total for d in range(1, TOTAL_DEZ + 1)}
        atr_time = {t: (ultimo - visto_time[t]) if visto_time[t] > 0 else total for t in range(1, TOTAL_TIMES + 1)}

        return freq_dez, atr_dez, freq_time, atr_time, ultimo, total

    @staticmethod
    def _escolher_time(estrategia, freq_time, atr_time, rng):
        todos = list(range(1, TOTAL_TIMES + 1))
        if estrategia == 'freq':
            pool = sorted(todos, key=lambda t: -freq_time[t])[:5]
        elif estrategia == 'atr':
            pool = sorted(todos, key=lambda t: -atr_time[t])[:5]
        elif estrategia == 'prob':
            total_f = sum(freq_time.values()) or 1
            pesos   = [freq_time[t] / total_f for t in todos]
            return rng.choices(todos, weights=pesos, k=1)[0]
        else:
            pool = todos
        return rng.choice(pool)

    @staticmethod
    def _gerar_dezenas(modelo_id, freq_dez, atr_dez, rng, offset=0):
        todos = list(range(1, TOTAL_DEZ + 1))

        if modelo_id == 1:
            pool = sorted(todos, key=lambda d: -freq_dez[d])[:20]
            return sorted(rng.sample(pool, NUM_DEZ))

        elif modelo_id == 2:
            pool = sorted(todos, key=lambda d: -atr_dez[d])[:20]
            return sorted(rng.sample(pool, NUM_DEZ))

        elif modelo_id == 3:
            pool = sorted(todos, key=lambda d: -freq_dez[d])[:18]
            return sorted(rng.sample(pool, NUM_DEZ))

        elif modelo_id == 4:
            baixas = sorted([d for d in todos if d <= 40], key=lambda d: -freq_dez[d])[:14]
            altas  = sorted([d for d in todos if d > 40],  key=lambda d: -atr_dez[d])[:14]
            pool   = list(set(baixas) | set(altas))
            return sorted(rng.sample(pool, min(NUM_DEZ, len(pool))))

        elif modelo_id == 5:
            # 8 faixas de 10, 1 por faixa + 2 extras de freq
            faixas = [(1,10),(11,20),(21,30),(31,40),(41,50),(51,60),(61,70),(71,80)]
            dez = []
            for ini, fim in faixas:
                faixa = list(range(ini, fim + 1))
                top   = sorted(faixa, key=lambda d: -freq_dez[d])
                dez.append(top[(offset // 3) % len(top)])
            dez = list(dict.fromkeys(dez))
            if len(dez) < NUM_DEZ:
                extra = sorted(todos, key=lambda d: -freq_dez[d])
                for e in extra:
                    if e not in dez: dez.append(e)
                    if len(dez) == NUM_DEZ: break
            return sorted(dez[:NUM_DEZ])

        elif modelo_id == 6:
            total_f = sum(freq_dez.values()) or 1
            pesos   = [freq_dez[d] / total_f for d in todos]
            escolhidos = set()
            t = 0
            while len(escolhidos) < NUM_DEZ and t < 400:
                d = rng.choices(todos, weights=pesos, k=1)[0]
                escolhidos.add(d); t += 1
            restantes = [d for d in todos if d not in escolhidos]
            while len(escolhidos) < NUM_DEZ:
                escolhidos.add(restantes.pop(0))
            return sorted(escolhidos)

        return sorted(rng.sample(todos, NUM_DEZ))

    @staticmethod
    def gerar_apostas_modelo(modelo_id: int):
        freq_dez, atr_dez, freq_time, atr_time, ultimo, total = ModelosTimemaniaService._build_stats()
        if freq_dez is None:
            return {"error": "Sem dados no banco."}
        cfg = MODELOS[modelo_id]
        estrategia_time = 'atr' if modelo_id == 2 else 'prob' if modelo_id == 6 else 'freq'

        apostas, vistos, tentativas = [], set(), 0
        while len(apostas) < NUM_APOSTAS and tentativas < NUM_APOSTAS * 80:
            rng  = random.Random(tentativas + modelo_id * 2000)
            dez  = ModelosTimemaniaService._gerar_dezenas(modelo_id, freq_dez, atr_dez, rng, tentativas)
            time = ModelosTimemaniaService._escolher_time(estrategia_time, freq_time, atr_time, rng)
            chave = (tuple(dez), time)
            if chave not in vistos:
                vistos.add(chave)
                apostas.append({
                    "aposta_num": len(apostas) + 1,
                    "dezenas":    dez,
                    "time_num":   time,
                    "time_nome":  TIMES_DO_CORACAO.get(time, f"Time {time}"),
                    "formatado":  " - ".join(f"{d:02d}" for d in dez) +
                                  f"  ⚽ {TIMES_DO_CORACAO.get(time, str(time))}",
                })
            tentativas += 1

        top10_freq = sorted(range(1, TOTAL_DEZ + 1),   key=lambda d: -freq_dez[d])[:6]
        top10_atr  = sorted(range(1, TOTAL_DEZ + 1),   key=lambda d: -atr_dez[d])[:6]
        top_times  = sorted(range(1, TOTAL_TIMES + 1), key=lambda t: -freq_time[t])[:5]

        return {
            "modelo_id":       modelo_id,
            "modelo_nome":     cfg["nome"],
            "modelo_emoji":    cfg["emoji"],
            "estrutura":       cfg["estrutura"],
            "ultimo_concurso": ultimo,
            "total_geradas":   len(apostas),
            "apostas":         apostas,
            "pool_info": {
                "top6_freq": [f"{d:02d}" for d in top10_freq],
                "top6_atr":  [f"{d:02d}" for d in top10_atr],
                "top_times": [{"num": t, "nome": TIMES_DO_CORACAO.get(t)} for t in top_times],
            },
        }

    @staticmethod
    def backtesting_modelos():
        freq_dez, atr_dez, freq_time, atr_time, ultimo, total_sorteios = ModelosTimemaniaService._build_stats()
        if freq_dez is None:
            return {"error": "Sem dados no banco."}

        sorteios = db.session.query(SorteioTimemania).all()
        ranking  = []

        for modelo_id in range(1, 7):
            cfg = MODELOS[modelo_id]
            estrategia_time = 'atr' if modelo_id == 2 else 'prob' if modelo_id == 6 else 'freq'
            apostas, vistos, tentativas = [], set(), 0
            while len(apostas) < NUM_APOSTAS and tentativas < NUM_APOSTAS * 80:
                rng  = random.Random(tentativas + modelo_id * 2000)
                dez  = ModelosTimemaniaService._gerar_dezenas(modelo_id, freq_dez, atr_dez, rng, tentativas)
                time = ModelosTimemaniaService._escolher_time(estrategia_time, freq_time, atr_time, rng)
                chave = (tuple(dez), time)
                if chave not in vistos:
                    vistos.add(chave)
                    apostas.append((set(dez), time))
                tentativas += 1

            hits  = {k: 0 for k in SCORE_TABLE}
            score = 0; total_premios = 0
            melhor_ac = 0; melhor_conc = None

            for s in sorteios:
                sd, st = s.dezenas(), s.time_num
                for aposta_dez, aposta_time in apostas:
                    ac     = len(aposta_dez & sd)
                    actime = (aposta_time == st) if st else False
                    key    = (ac, actime) if (ac, actime) in SCORE_TABLE else \
                             (ac, False)  if (ac, False)  in SCORE_TABLE else \
                             (0,  True)   if actime        else None
                    if key:
                        hits[key] = hits.get(key, 0) + 1
                        score += SCORE_TABLE[key]
                        total_premios += 1
                    if ac > melhor_ac:
                        melhor_ac = ac; melhor_conc = s.concurso

            ranking.append({
                "modelo_id":       modelo_id,
                "modelo_nome":     cfg["nome"],
                "modelo_emoji":    cfg["emoji"],
                "estrutura":       cfg["estrutura"],
                "cor":             cfg["cor"],
                "total_premios":   total_premios,
                "hits_7":          hits.get((7,False),0) + hits.get((7,True),0),
                "hits_6":          hits.get((6,False),0) + hits.get((6,True),0),
                "hits_5":          hits.get((5,False),0) + hits.get((5,True),0),
                "hits_4":          hits.get((4,False),0) + hits.get((4,True),0),
                "hits_3":          hits.get((3,False),0) + hits.get((3,True),0),
                "hits_0":          sum(v for k,v in hits.items() if k[1] == True),
                "melhor_acerto":   melhor_ac,
                "melhor_concurso": melhor_conc,
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
