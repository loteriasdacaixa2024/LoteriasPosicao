# -*- coding: utf-8 -*-
"""Constantes — Desdobramento especial Quina (PAR/ÍMPAR por colunas)."""

MIN_COLUNAS = 3
MIN_DEZENAS_APOSTA = 5
MAX_DEZENAS_APOSTA = 15
JOGOS_POR_COLUNA = 28  # C(8,2) por coluna no volante 01–80
DEZENAS_POR_COLUNA = 8

TABELA_PRECOS = {
    5: 3.0,
    6: 18.0,
    7: 63.0,
    8: 168.0,
    9: 378.0,
    10: 756.0,
    11: 1386.0,
    12: 2376.0,
    13: 3861.0,
    14: 6006.0,
    15: 9009.0,
}

COLUNAS_LABEL = {
    1: "Coluna 1 (final 1)",
    2: "Coluna 2 (final 2)",
    3: "Coluna 3 (final 3)",
    4: "Coluna 4 (final 4)",
    5: "Coluna 5 (final 5)",
    6: "Coluna 6 (final 6)",
    7: "Coluna 7 (final 7)",
    8: "Coluna 8 (final 8)",
    9: "Coluna 9 (final 9)",
    10: "Coluna 10 (final 0)",
}

# Faixas válidas de colunas por modo (total de dezenas na aposta Caixa)
COLUNAS_VALIDAS_PAR = {3, 4, 5, 6, 7}  # 6, 8, 10, 12, 14
COLUNAS_VALIDAS_IMPAR = {3, 4, 5, 6, 7, 8}  # 5, 7, 9, 11, 13, 15

# Pacotes de jogos estruturais (subconjunto dos 28 alinhamentos C(8,2))
GARANTIAS_ESPECIAL = {
    "bronze": {
        "jogos": 7,
        "titulo": "7 Apostas",
        "desc": "Primeiros 7 alinhamentos estruturais (amostra conservadora)",
    },
    "prata": {
        "jogos": 14,
        "titulo": "14 Apostas",
        "desc": "Metade do desdobramento — 14 combinações alinhadas",
    },
    "ouro": {
        "jogos": 21,
        "titulo": "21 Apostas",
        "desc": "Cobertura ampla — 21 combinações alinhadas",
    },
    "diamante": {
        "jogos": 28,
        "titulo": "28 Apostas",
        "desc": "Desdobramento integral C(8,2) em todas as colunas",
    },
}
