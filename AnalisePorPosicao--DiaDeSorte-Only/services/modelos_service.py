"""
modelos_service.py  (Dia de Sorte)
==================================
6 Modelos: 7 dezenas (01-31) + 1 Mês (1-12)
14 apostas por modelo.

Tabela de prêmios (scoring para backtesting):
- 7 dezenas  = 500.000 pts
- 6 dezenas  =   5.000 pts
- 5 dezenas  =      50 pts
- 4 dezenas  =       5 pts
- Mês        =       2 pts
Nota: No Dia de Sorte o prêmio do mês acumula (soma) com o das dezenas.
"""
import random
from models.shared import db
from models.sorteio_diadesorte import SorteioDiaDeSorte, MESES_DO_ANO, mes_abrev_de
from sqlalchemy import desc

TOTAL_DEZ   = 31
TOTAL_MESES = 12
NUM_DEZ     = 7
NUM_APOSTAS = 14

MODELOS = {
    1: {"nome":"Conservador",      "emoji":"🔹","subtitulo":"Top-freq dezenas + mês mais freq",        "cor":"#1a6e3c","estrutura":"Top12-FREQ + MÊS-FREQ"},
    2: {"nome":"Atraso Controlado",     "emoji":"🔸","subtitulo":"Mais atrasadas + mês mais atrasado",      "cor":"#c47a1e","estrutura":"Top12-ATR + MÊS-ATR"},
    3: {"nome":"Núcleo Forte",  "emoji":"🔥","subtitulo":"Top-12 freq dezenas + mês campeão",       "cor":"#8b1a1a","estrutura":"Top12-FREQ + MÊS-TOP"},
    4: {"nome":"Rotação Inteligente",            "emoji":"🔄","subtitulo":"Mistura Freq e Atraso (Dez e Mês)",       "cor":"#1a3a8b","estrutura":"FREQ+ATR + MÊS-FREQ"},
    5: {"nome":"Frequência Dominante",        "emoji":"📈","subtitulo":"Distribui entre 1-15 e 16-31 + Mês Freq","cor":"#5a1a8b","estrutura":"Baixas+Altas + MÊS-FREQ"},
    6: {"nome":"Ciclo Anterior",  "emoji":"♻️","subtitulo":"Pesos históricos de freq (Dezenas+Mês)",  "cor":"#1a5c6e","estrutura":"Prob(freq)"},
}

SCORE_DEZ = {7: 500000, 6: 5000, 5: 50, 4: 5}
SCORE_MES = 2


class ModelosDiaDeSorteService:

    @staticmethod
    def _build_stats():
        sorteios = db.session.query(SorteioDiaDeSorte).order_by(
            desc(SorteioDiaDeSorte.concurso)
        ).all()
        if not sorteios:
            return None, None, None, None, None, None

        total  = len(sorteios)
        ultimo = sorteios[0].concurso

        freq_d = {d: 0 for d in range(1, TOTAL_DEZ + 1)}
        vist_d = {d: 0 for d in range(1, TOTAL_DEZ + 1)}
        freq_m = {m: 0 for m in range(1, TOTAL_MESES + 1)}
        vist_m = {m: 0 for m in range(1, TOTAL_MESES + 1)}

        for s in sorteios:
            for d in s.dezenas():
                freq_d[d] += 1
                if vist_d[d] == 0: vist_d[d] = s.concurso
            if s.mes_num and 1 <= s.mes_num <= TOTAL_MESES:
                freq_m[s.mes_num] += 1
                if vist_m[s.mes_num] == 0: vist_m[s.mes_num] = s.concurso

        atr_d = {d: (ultimo - vist_d[d]) if vist_d[d] > 0 else total for d in range(1, TOTAL_DEZ + 1)}
        atr_m = {m: (ultimo - vist_m[m]) if vist_m[m] > 0 else total for m in range(1, TOTAL_MESES + 1)}

        return freq_d, atr_d, freq_m, atr_m, ultimo, total

    @staticmethod
    def _escolher_mes(estrategia, freq_m, atr_m, rng):
        todos = list(range(1, TOTAL_MESES + 1))
        if estrategia == 'freq':
            pool = sorted(todos, key=lambda m: -freq_m[m])[:3]
        elif estrategia == 'atr':
            pool = sorted(todos, key=lambda m: -atr_m[m])[:3]
        elif estrategia == 'prob':
            total_f = sum(freq_m.values()) or 1
            pesos   = [freq_m[m] / total_f for m in todos]
            return rng.choices(todos, weights=pesos, k=1)[0]
        else:
            pool = todos
        return rng.choice(pool)

    @staticmethod
    def _gerar_dezenas(modelo_id, freq_d, atr_d, rng, offset=0):
        todos = list(range(1, TOTAL_DEZ + 1))

        if modelo_id == 1:
            pool = sorted(todos, key=lambda d: -freq_d[d])[:12]
            return sorted(rng.sample(pool, NUM_DEZ))

        elif modelo_id == 2:
            pool = sorted(todos, key=lambda d: -atr_d[d])[:12]
            return sorted(rng.sample(pool, NUM_DEZ))

        elif modelo_id == 3:
            pool = sorted(todos, key=lambda d: -freq_d[d])[:10]
            return sorted(rng.sample(pool, NUM_DEZ))

        elif modelo_id == 4:
            tf = sorted(todos, key=lambda d: -freq_d[d])[:8]
            ta = sorted(todos, key=lambda d: -atr_d[d])[:8]
            pool = list(set(tf) | set(ta))
            return sorted(rng.sample(pool, min(NUM_DEZ, len(pool))))

        elif modelo_id == 5:
            baixas = [d for d in todos if d <= 15]
            altas  = [d for d in todos if d > 15]
            top_b  = sorted(baixas, key=lambda d: -freq_d[d])[:8]
            top_a  = sorted(altas,  key=lambda d: -freq_d[d])[:8]
            pool   = top_b + top_a
            return sorted(rng.sample(pool, NUM_DEZ))

        elif modelo_id == 6:
            total_f = sum(freq_d.values()) or 1
            pesos   = [freq_d[d] / total_f for d in todos]
            escolhidos = set()
            t = 0
            while len(escolhidos) < NUM_DEZ and t < 200:
                d = rng.choices(todos, weights=pesos, k=1)[0]
                escolhidos.add(d); t += 1
            restantes = [d for d in todos if d not in escolhidos]
            while len(escolhidos) < NUM_DEZ:
                escolhidos.add(restantes.pop(0))
            return sorted(escolhidos)

        return sorted(rng.sample(todos, NUM_DEZ))

    @staticmethod
    def gerar_apostas_modelo(modelo_id: int):
        freq_d, atr_d, freq_m, atr_m, ultimo, total = ModelosDiaDeSorteService._build_stats()
        if freq_d is None: return {"error": "Sem dados."}
        
        cfg = MODELOS[modelo_id]
        est_mes = 'atr' if modelo_id == 2 else 'prob' if modelo_id == 6 else 'freq'

        apostas, vistos, tentativas = [], set(), 0
        while len(apostas) < NUM_APOSTAS and tentativas < 1000:
            rng  = random.Random(tentativas + modelo_id * 3000)
            dez  = ModelosDiaDeSorteService._gerar_dezenas(modelo_id, freq_d, atr_d, rng, tentativas)
            mes  = ModelosDiaDeSorteService._escolher_mes(est_mes, freq_m, atr_m, rng)
            chave = (tuple(dez), mes)
            if chave not in vistos:
                vistos.add(chave)
                apostas.append({
                    "aposta_num": len(apostas) + 1,
                    "dezenas": dez,
                    "mes_num": mes,
                    "mes_nome": MESES_DO_ANO.get(mes, str(mes)),
                    "mes_abrev": mes_abrev_de(mes, MESES_DO_ANO.get(mes)),
                    "formatado": " - ".join(f"{d:02d}" for d in dez) + f"  🗓️ {mes_abrev_de(mes, MESES_DO_ANO.get(mes))}",
                })
            tentativas += 1

        top7_freq = sorted(range(1, TOTAL_DEZ + 1), key=lambda d: -freq_d[d])[:7]
        top7_atr  = sorted(range(1, TOTAL_DEZ + 1), key=lambda d: -atr_d[d])[:7]
        top_m     = sorted(range(1, TOTAL_MESES + 1), key=lambda m: -freq_m[m])[:3]

        return {
            "modelo_id": modelo_id,
            "modelo_nome": cfg["nome"],
            "modelo_emoji": cfg["emoji"],
            "estrutura": cfg["estrutura"],
            "ultimo_concurso": ultimo,
            "total_geradas": len(apostas),
            "apostas": apostas,
            "pool_info": {
                "top7_freq": [f"{d:02d}" for d in top7_freq],
                "top7_atr":  [f"{d:02d}" for d in top7_atr],
                "top_meses": [{"num": m, "nome": MESES_DO_ANO.get(m)} for m in top_m],
            },
        }

    @staticmethod
    def backtesting_modelos():
        freq_d, atr_d, freq_m, atr_m, ultimo, total_sorteios = ModelosDiaDeSorteService._build_stats()
        if freq_d is None: return {"error": "Sem dados."}

        sorteios = db.session.query(SorteioDiaDeSorte).all()
        ranking  = []

        for modelo_id in range(1, 7):
            cfg = MODELOS[modelo_id]
            est_mes = 'atr' if modelo_id == 2 else 'prob' if modelo_id == 6 else 'freq'
            apostas, vistos, tentativas = [], set(), 0
            while len(apostas) < NUM_APOSTAS and tentativas < 1000:
                rng  = random.Random(tentativas + modelo_id * 3000)
                dez  = ModelosDiaDeSorteService._gerar_dezenas(modelo_id, freq_d, atr_d, rng, tentativas)
                mes  = ModelosDiaDeSorteService._escolher_mes(est_mes, freq_m, atr_m, rng)
                chave = (tuple(dez), mes)
                if chave not in vistos:
                    vistos.add(chave)
                    apostas.append((set(dez), mes))
                tentativas += 1

            hits_d = {7:0, 6:0, 5:0, 4:0}
            hits_m = 0
            score = 0; total_premios = 0
            melhor_ac = 0; melhor_conc = None

            for s in sorteios:
                sd, sm = s.dezenas(), s.mes_num
                for apost_dez, apost_mes in apostas:
                    ac = len(apost_dez & sd)
                    acm = (apost_mes == sm)
                    ganhou = False

                    if ac >= 4:
                        pts = SCORE_DEZ.get(ac, 0)
                        score += pts
                        hits_d[ac] += 1
                        ganhou = True
                        if ac > melhor_ac:
                            melhor_ac = ac; melhor_conc = s.concurso

                    if acm:
                        score += SCORE_MES
                        hits_m += 1
                        ganhou = True

                    if ganhou:
                        total_premios += 1

            ranking.append({
                "modelo_id": modelo_id,
                "modelo_nome": cfg["nome"],
                "modelo_emoji": cfg["emoji"],
                "estrutura": cfg["estrutura"],
                "cor": cfg["cor"],
                "total_premios": total_premios,
                "hits_7": hits_d[7],
                "hits_6": hits_d[6],
                "hits_5": hits_d[5],
                "hits_4": hits_d[4],
                "hits_0": hits_m,
                "melhor_acerto": melhor_ac,
                "melhor_concurso": melhor_conc,
                "score": score,
            })

        ranking.sort(key=lambda x: -x["score"])
        for i, m in enumerate(ranking):
            m["posicao"] = i + 1

        return {
            "ultimo_concurso": ultimo,
            "total_sorteios": total_sorteios,
            "ranking": ranking,
        }

    @staticmethod
    def listar_modelos():
        return [{"id":mid,"nome":cfg["nome"],"emoji":cfg["emoji"],
                 "subtitulo":cfg["subtitulo"],"cor":cfg["cor"],"estrutura":cfg["estrutura"]}
                for mid, cfg in MODELOS.items()]
