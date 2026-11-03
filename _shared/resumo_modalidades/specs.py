# -*- coding: utf-8 -*-
"""Quais modalidades entram no Resumo Geral. Começa pelo Dia de Sorte."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class CardModalidade:
    key: str
    nome: str
    extra_valor: Optional[str] = None
    extra_rotulo: Optional[str] = None
    extra_cor: str = "mes"


# Ordem da página. Novas modalidades entram aqui quando forem aprovadas.
_PAGINA: List[CardModalidade] = [
    CardModalidade(
        key="diadesorte",
        nome="Dia de Sorte",
        extra_valor="12",
        extra_rotulo="Meses de Sorte",
        extra_cor="mes",
    ),
]


def modalidades_da_pagina() -> List[CardModalidade]:
    return list(_PAGINA)
