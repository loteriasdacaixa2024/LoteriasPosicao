# -*- coding: utf-8 -*-
"""Ciclo de cobertura — Novas × Repetidas + estratégia 2+1 (multi-modalidade)."""
from .specs import get_ciclo_spec, tem_ciclo_cobertura
from .service import contexto_dois_ultimos, metricas_padrao_2n1r
from .gerador import gerar_apostas_ciclo

__all__ = [
    "get_ciclo_spec",
    "tem_ciclo_cobertura",
    "contexto_dois_ultimos",
    "metricas_padrao_2n1r",
    "gerar_apostas_ciclo",
]
