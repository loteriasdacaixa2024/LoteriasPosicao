# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List


def pct(n: int, total: int) -> float:
    return round(n / total * 100, 1) if total else 0.0


def labels_regras_auto(regras: Dict[str, Any], extras: List[tuple] | None = None) -> List[str]:
    out: List[str] = []
    mapa = [
        ("usar_repeticao", "Repetição"),
        ("usar_dupla", "Priorizar dupla"),
        ("usar_trinca", "Priorizar trinca"),
        ("usar_numeros_quentes", "Números quentes"),
        ("usar_numeros_frios", "Números frios"),
        ("usar_colunas_fortes", "Colunas fortes"),
        ("usar_colunas_fracas", "Colunas fracas"),
        ("usar_posicional", "Repetição posicional"),
        ("usar_permanencia", "Permanência"),
        ("usar_par_impar", "Par/ímpar"),
        ("usar_sequencial", "Sequencial"),
        ("usar_ultimo_par", "Último par"),
        ("usar_pares_colunas", "Par de colunas"),
        ("usar_atraso", "Atraso"),
        ("usar_ciclo", "Ciclo"),
        ("usar_mes", "Mês da sorte"),
        ("usar_time", "Time do coração"),
        ("usar_trevos", "Trevos"),
    ]
    if extras:
        mapa = mapa + list(extras)
    for k, lbl in mapa:
        if regras.get(k):
            out.append(lbl)
    if regras.get("tipo_sorteio_alvo"):
        out.append(f"Tipo alvo: {regras['tipo_sorteio_alvo']}")
    return out
