"""
modelos_service.py  (Super Sete)
=================================
Geração de apostas pelos 6 Modelos Estratégicos para Super Sete.

Super Sete: 7 colunas, cada uma com dígito 0-9.
Uma aposta mínima = 1 dígito por coluna = 7 dígitos.

MODELOS:
  M1 — Conservador   : col quente + col atrasada equilibrado
  M2 — Atraso Forte  : força os dígitos mais atrasados em cada coluna
  M3 — Frequência    : prioriza os dígitos mais frequentes por coluna
  M4 — Misto         : combina atrasado e frequente por coluna
  M5 — Ciclo Anterior: usa o dígito atual de cada coluna como âncora ±1
  M6 — Aleatório Ponderado: peso histórico + aleatoriedade controlada
"""

import random
from models.shared import db
from models.sorteio_supersete import SorteioSuperSete
from sqlalchemy import desc

NUM_COLUNAS  = 7
DIGITOS      = list(range(10))   # 0-9
NUM_APOSTAS  = 14   # 2 apostas × 7 colunas Super Sete

# Cores dos modelos (verde-lima Super Sete palette)
MODELOS = {
    1: {"nome": "Conservador",         "emoji": "🔹", "subtitulo": "Equilíbrio — quente + atrasado",       "cor": "#1a6e3c", "estrutura": "1QNT + 1ATR por coluna"},
    2: {"nome": "Atraso Controlado",        "emoji": "🔸", "subtitulo": "Aposta nos dígitos mais atrasados",    "cor": "#c47a1e", "estrutura": "Top-ATR por coluna"},
    3: {"nome": "Núcleo Forte",          "emoji": "🔥", "subtitulo": "Dígitos mais frequentes no comando",   "cor": "#8b1a1a", "estrutura": "Top-FREQ por coluna"},
    4: {"nome": "Rotação Inteligente",   "emoji": "🔄", "subtitulo": "Mistura freq + atraso dinamicamente",  "cor": "#1a3a8b", "estrutura": "FREQ c1+c3+c5+c7 / ATR c2+c4+c6"},
    5: {"nome": "Frequência Dominante",      "emoji": "📈", "subtitulo": "Âncora no dígito do último sorteio",  "cor": "#5a1a8b", "estrutura": "ANT ±1 por coluna"},
    6: {"nome": "Ciclo Anterior", "emoji": "♻️", "subtitulo": "Peso histórico + variação controlada", "cor": "#1a5c6e", "estrutura": "Prob(freq) por coluna"},
}


class ModelosSuperSeteService:

    # -------------------------------------------------------------------
    # DADOS BASE
    # -------------------------------------------------------------------
    @staticmethod
    def _build_rankings():
        """
        Para cada coluna, constrói:
          - freq[col][digito]  → contagem histórica
          - atraso[col][digito] → concursos desde última aparição
          - atual[col]         → dígito do último sorteio
        """
        sorteios = db.session.query(SorteioSuperSete).order_by(
            desc(SorteioSuperSete.concurso)
        ).all()

        if not sorteios:
            return None, None, None, None, None

        total = len(sorteios)
        ultimo_concurso = sorteios[0].concurso

        freq   = {c: {d: 0 for d in DIGITOS} for c in range(1, NUM_COLUNAS + 1)}
        visto  = {c: {d: 0 for d in DIGITOS} for c in range(1, NUM_COLUNAS + 1)}

        for s in sorteios:
            for col in range(1, NUM_COLUNAS + 1):
                d = getattr(s, f'coluna_{col}')
                freq[col][d] += 1
                if visto[col][d] == 0:
                    visto[col][d] = s.concurso

        atraso = {}
        for col in range(1, NUM_COLUNAS + 1):
            atraso[col] = {}
            for d in DIGITOS:
                if visto[col][d] == 0:
                    atraso[col][d] = total
                else:
                    atraso[col][d] = ultimo_concurso - visto[col][d]

        # Dígito atual por coluna
        atual = {col: getattr(sorteios[0], f'coluna_{col}') for col in range(1, NUM_COLUNAS + 1)}

        return freq, atraso, atual, ultimo_concurso, total

    # -------------------------------------------------------------------
    # GERAÇÃO DE UMA APOSTA
    # Retorna lista de 7 dígitos [d1, d2, ..., d7] — um por coluna
    # -------------------------------------------------------------------
    @staticmethod
    def _escolher_digito(col, freq, atraso, atual, modelo_id, rng):
        """Escolhe 1 dígito para a coluna `col` conforme a estratégia do modelo."""
        digitos = DIGITOS[:]

        if modelo_id == 1:  # Conservador: 50% quente, 50% atrasado
            top_freq  = sorted(digitos, key=lambda d: -freq[col][d])[:5]
            top_atr   = sorted(digitos, key=lambda d: -atraso[col][d])[:5]
            pool = list(set(top_freq) | set(top_atr))
            return rng.choice(pool)

        elif modelo_id == 2:  # Atraso Forte: top-3 atrasados
            top = sorted(digitos, key=lambda d: -atraso[col][d])[:3]
            return rng.choice(top)

        elif modelo_id == 3:  # Frequência: top-3 mais frequentes
            top = sorted(digitos, key=lambda d: -freq[col][d])[:3]
            return rng.choice(top)

        elif modelo_id == 4:  # Misto: colunas ímpares=freq, pares=atraso
            if col % 2 == 1:
                top = sorted(digitos, key=lambda d: -freq[col][d])[:3]
            else:
                top = sorted(digitos, key=lambda d: -atraso[col][d])[:3]
            return rng.choice(top)

        elif modelo_id == 5:  # Ciclo Anterior: atual ±1
            candidatos = [(atual[col] + delta) % 10 for delta in [-1, 0, 1]]
            return rng.choice(candidatos)

        elif modelo_id == 6:  # Aleatório Ponderado: prob ∝ freq
            total_f = sum(freq[col].values()) or 1
            pesos = [freq[col][d] / total_f for d in digitos]
            return rng.choices(digitos, weights=pesos, k=1)[0]

        return rng.choice(digitos)

    @staticmethod
    def _gerar_uma_aposta(modelo_id, freq, atraso, atual, seed_offset):
        rng = random.Random(seed_offset)
        return [
            ModelosSuperSeteService._escolher_digito(col, freq, atraso, atual, modelo_id, rng)
            for col in range(1, NUM_COLUNAS + 1)
        ]

    # -------------------------------------------------------------------
    # GERAR 24 APOSTAS DE UM MODELO
    # -------------------------------------------------------------------
    @staticmethod
    def gerar_apostas_modelo(modelo_id: int):
        freq, atraso, atual, ultimo_concurso, total = ModelosSuperSeteService._build_rankings()
        if freq is None:
            return {"error": "Sem dados no banco de dados."}

        cfg = MODELOS[modelo_id]
        apostas = []
        vistos  = set()
        tentativas = 0

        while len(apostas) < NUM_APOSTAS and tentativas < NUM_APOSTAS * 20:
            digitos = ModelosSuperSeteService._gerar_uma_aposta(
                modelo_id, freq, atraso, atual,
                seed_offset=tentativas + modelo_id * 1000
            )
            chave = tuple(digitos)
            if chave not in vistos:
                vistos.add(chave)
                apostas.append({
                    "aposta_num": len(apostas) + 1,
                    "digitos":    digitos,                          # [d1..d7]
                    "formatado":  " | ".join(str(d) for d in digitos),
                })
            tentativas += 1

        # Pool info para exibição
        pool_info = {
            "col_atual":    [atual[c] for c in range(1, NUM_COLUNAS + 1)],
            "col_top_freq": [
                sorted(DIGITOS, key=lambda d: -freq[c][d])[0]
                for c in range(1, NUM_COLUNAS + 1)
            ],
            "col_top_atr":  [
                sorted(DIGITOS, key=lambda d: -atraso[c][d])[0]
                for c in range(1, NUM_COLUNAS + 1)
            ],
        }

        return {
            "modelo_id":       modelo_id,
            "modelo_nome":     cfg["nome"],
            "modelo_emoji":    cfg["emoji"],
            "estrutura":       cfg["estrutura"],
            "ultimo_concurso": ultimo_concurso,
            "total_geradas":   len(apostas),
            "apostas":         apostas,
            "pool_info":       pool_info,
        }

    # -------------------------------------------------------------------
    # BACKTESTING
    # -------------------------------------------------------------------
    @staticmethod
    def backtesting_modelos():
        """
        Para cada modelo, gera 24 apostas e verifica acertos históricos.
        Prêmios contam para 4+ acertos (colunas corretas).
        """
        freq, atraso, atual, ultimo_concurso, total_sorteios = ModelosSuperSeteService._build_rankings()
        if freq is None:
            return {"error": "Sem dados no banco de dados."}

        sorteios = db.session.query(SorteioSuperSete).all()
        sorteios_lista = [(s.concurso, s.digitos()) for s in sorteios]

        ranking = []

        for modelo_id in range(1, 7):
            cfg = MODELOS[modelo_id]

            apostas_digitos = []
            vistos = set()
            tentativas = 0
            while len(apostas_digitos) < NUM_APOSTAS and tentativas < NUM_APOSTAS * 20:
                digitos = ModelosSuperSeteService._gerar_uma_aposta(
                    modelo_id, freq, atraso, atual,
                    seed_offset=tentativas + modelo_id * 1000
                )
                chave = tuple(digitos)
                if chave not in vistos:
                    vistos.add(chave)
                    apostas_digitos.append(digitos)
                tentativas += 1

            hits = {7: 0, 6: 0, 5: 0, 4: 0, 3: 0}
            total_premios = 0
            melhor_acerto = 0
            melhor_concurso = None

            for concurso, sorteio_digitos in sorteios_lista:
                for aposta in apostas_digitos:
                    # Conta colunas corretas
                    acertos = sum(
                        1 for col_idx in range(NUM_COLUNAS)
                        if aposta[col_idx] == sorteio_digitos[col_idx]
                    )
                    if acertos >= 3:
                        hits[min(acertos, 7)] += 1
                        if acertos >= 4:
                            total_premios += 1
                        if acertos > melhor_acerto:
                            melhor_acerto   = acertos
                            melhor_concurso = concurso

            score = hits[7]*500 + hits[6]*50 + hits[5]*10 + hits[4]*3 + hits[3]

            ranking.append({
                "modelo_id":       modelo_id,
                "modelo_nome":     cfg["nome"],
                "modelo_emoji":    cfg["emoji"],
                "estrutura":       cfg["estrutura"],
                "cor":             cfg["cor"],
                "total_premios":   total_premios,
                "hits_7":          hits[7],
                "hits_6":          hits[6],
                "hits_5":          hits[5],
                "hits_4":          hits[4],
                "hits_3":          hits[3],
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

    # -------------------------------------------------------------------
    # LISTAR MODELOS
    # -------------------------------------------------------------------
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
