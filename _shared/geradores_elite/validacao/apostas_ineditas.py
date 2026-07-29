# -*- coding: utf-8 -*-
"""Validação de apostas inéditas vs histórico oficial."""
from __future__ import annotations

from typing import Any, Callable, FrozenSet, List, Set, Type

from models.shared import db


def carregar_combinacoes_historicas(
    sorteio_model: Type[Any],
    dezenas_fn: Callable[[Any], List[int]],
) -> Set[FrozenSet[int]]:
    """Carrega todas as combinações já sorteadas (normalizadas, ordem irrelevante)."""
    rows = db.session.query(sorteio_model).all()
    out: Set[FrozenSet[int]] = set()
    for s in rows:
        dz = dezenas_fn(s)
        if dz:
            out.add(frozenset(dz))
    return out


def aposta_ja_sorteada(dezenas: List[int], historico: Set[FrozenSet[int]]) -> bool:
    if not dezenas:
        return True
    return frozenset(dezenas) in historico
