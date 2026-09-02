# -*- coding: utf-8 -*-
"""Parâmetros do volante por modalidade (layout final10)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class ModalidadeVolante:
    slug: str
    nome: str
    total_dezenas: int
    sorteadas: int
    colunas: int
    linhas: int
    dezenas_por_coluna: int
    dezenas_por_linha: int


MODALIDADES: Dict[str, ModalidadeVolante] = {
    "megasena": ModalidadeVolante(
        "megasena", "Mega-Sena", 60, 6, 10, 6, 6, 10
    ),
    "quina": ModalidadeVolante(
        "quina", "Quina", 80, 5, 10, 8, 8, 10
    ),
    "duplasena": ModalidadeVolante(
        "duplasena", "Dupla Sena", 50, 6, 10, 5, 5, 10
    ),
}


def lista_comparativo() -> List[dict]:
    from _shared.coluna_final_vivo.engine import pct_teorico_coluna_2plus

    out = []
    for m in MODALIDADES.values():
        t = pct_teorico_coluna_2plus(m)
        out.append({
            "slug": m.slug,
            "nome": m.nome,
            "sorteadas": m.sorteadas,
            "teorico_pct_coluna_2plus": t,
            "teorico_pct_finais_distintos": round(100 - t, 1),
        })
    return out
