"""
Constantes do módulo Des2 — Desdobramento Estrutural por Colunas.
Tabela oficial de valores de aposta da Mega-Sena (Caixa).
"""

# Quantidades de dezenas permitidas (apenas pares)
DEZENAS_PERMITIDAS = [6, 8, 10, 12, 14, 16, 18, 20]

# C(6,2) = 15 pares por coluna → 15 jogos estruturais
JOGOS_POR_COLUNA = 15
PARES_POR_COLUNA = 15

# Valores oficiais por quantidade de dezenas na aposta (R$)
TABELA_PRECOS = {
    6: 5.00,
    7: 35.00,
    8: 140.00,
    9: 504.00,
    10: 1260.00,
    11: 2772.00,
    12: 5544.00,
    13: 10296.00,
    14: 18180.00,
    15: 30030.00,
    16: 48048.00,
    17: 74613.00,
    18: 111320.00,
    19: 162316.00,
    20: 232560.00,
}

# Labels das colunas (final 0 = coluna 10 no volante)
COLUNAS_LABEL = {
    1: "Coluna 1", 2: "Coluna 2", 3: "Coluna 3", 4: "Coluna 4",
    5: "Coluna 5", 6: "Coluna 6", 7: "Coluna 7", 8: "Coluna 8",
    9: "Coluna 9", 10: "Coluna 0 (final 0)",
}
