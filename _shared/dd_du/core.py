# -*- coding: utf-8 -*-
"""
Decomposição DD (Dígito da Dezena) × DU (Dígito da Unidade).

Exemplos:
  01 → DD=0 | DU=1
  08 → DD=0 | DU=8
  10 → DD=1 | DU=0
  00 → DD=0 | DU=0  (Lotomania — nunca excluir)
  Super Sete (0–9, pad=1): DD=0 | DU=valor
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple


def decompor_dezena(valor: int, pad_width: int = 2) -> Tuple[int, int]:
    n = int(valor)
    if pad_width <= 1:
        # Valor já é o dígito da coluna (Super Sete)
        du = abs(n) % 10
        return 0, du
    # Padrão Caixa 00–99 (e universos 1–N com pad 2)
    n = abs(n)
    if n > 99:
        # Defesa: usa os dois últimos dígitos
        n = n % 100
    return n // 10, n % 10


def reconstruir_dezena(dd: int, du: int) -> int:
    """Monta a dezena a partir de DD e DU (0–99)."""
    return int(dd) * 10 + int(du)


def decompor_lista(
    dezenas: Sequence[int],
    pad_width: int = 2,
) -> Dict[str, Any]:
    pares: List[Dict[str, Any]] = []
    dds: List[int] = []
    dus: List[int] = []
    for n in dezenas:
        dd, du = decompor_dezena(int(n), pad_width)
        dds.append(dd)
        dus.append(du)
        pares.append({"dezena": int(n), "dd": dd, "du": du})
    return {
        "pares": pares,
        "dd": dds,
        "du": dus,
        "dd_unicos": sorted(set(dds)),
        "du_unicos": sorted(set(dus)),
        "qtd_dd_unicos": len(set(dds)),
        "qtd_du_unicos": len(set(dus)),
    }
