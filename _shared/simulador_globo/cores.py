# -*- coding: utf-8 -*-
"""
Cor da bola pela casa das unidades.

Final 1 vermelha, 2 amarela, 3 verde, 4 marrom, 5 azul, 6 rosa, 7 preta,
8 cinza, 9 laranja e 0 branca. O que o sorteio grava é o número.
Um override por modalidade entra em OVERRIDES_FINAL sem alterar as demais.
"""
from __future__ import annotations

from typing import Dict, Optional

PALETA = (
    {"id": "vermelha", "nome": "Vermelha", "hex": "#E53935", "texto": "#ffffff", "final": 1},
    {"id": "amarela", "nome": "Amarela", "hex": "#FDD835", "texto": "#212121", "final": 2},
    {"id": "verde", "nome": "Verde", "hex": "#43A047", "texto": "#ffffff", "final": 3},
    {"id": "marrom", "nome": "Marrom", "hex": "#6D4C41", "texto": "#ffffff", "final": 4},
    {"id": "azul", "nome": "Azul", "hex": "#1E88E5", "texto": "#ffffff", "final": 5},
    {"id": "rosa", "nome": "Rosa", "hex": "#EC407A", "texto": "#ffffff", "final": 6},
    {"id": "preta", "nome": "Preta", "hex": "#212121", "texto": "#ffffff", "final": 7},
    {"id": "cinza", "nome": "Cinza", "hex": "#9E9E9E", "texto": "#212121", "final": 8},
    {"id": "laranja", "nome": "Laranja", "hex": "#FB8C00", "texto": "#212121", "final": 9},
    {"id": "branca", "nome": "Branca", "hex": "#F7F7F7", "texto": "#212121", "final": 0},
)

POR_FINAL: Dict[int, dict] = {item["final"]: dict(item) for item in PALETA}
POR_ID: Dict[str, dict] = {item["id"]: dict(item) for item in PALETA}

# Ex.: {"quina": {1: "azul"}} troca só o final 1 da Quina.
OVERRIDES_FINAL: Dict[str, Dict[int, str]] = {}


def cor_da_dezena(numero: int, modalidade: Optional[str] = None) -> dict:
    final = abs(int(numero)) % 10
    override = (OVERRIDES_FINAL.get(modalidade or "") or {}).get(final)
    if override and override in POR_ID:
        return dict(POR_ID[override])
    return dict(POR_FINAL[final])


def percentual(quantidade: int, total: int) -> float:
    if not total:
        return 0.0
    return round(1000 * int(quantidade) / int(total)) / 10.0
