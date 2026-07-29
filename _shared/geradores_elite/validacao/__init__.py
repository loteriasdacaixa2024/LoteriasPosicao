# -*- coding: utf-8 -*-
"""Validação pós-geração dos Geradores de Elite."""
from geradores_elite.validacao.apostas_ineditas import (
    aposta_ja_sorteada,
    carregar_combinacoes_historicas,
)
from geradores_elite.validacao.validador_global import ValidadorGeradoresElite

__all__ = [
    "ValidadorGeradoresElite",
    "aposta_ja_sorteada",
    "carregar_combinacoes_historicas",
]
