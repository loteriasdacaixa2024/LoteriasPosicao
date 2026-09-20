# -*- coding: utf-8 -*-
"""Gerador Elite — Estatísticas Básicas + dezenas pendentes do ciclo."""
from .gerador import gerar_apostas_de_contexto
from .service import contexto_estatisticas_ciclo, gerar_apostas_estatisticas_ciclo

__all__ = [
    "contexto_estatisticas_ciclo",
    "gerar_apostas_de_contexto",
    "gerar_apostas_estatisticas_ciclo",
]
