# -*- coding: utf-8 -*-
"""Análise por Posição + Gerador — módulo compartilhado por modalidade."""
from .specs import POSICAO_SPECS, get_posicao_spec, tem_posicao_analise
from .service_factory import make_service

__all__ = [
    "POSICAO_SPECS",
    "get_posicao_spec",
    "tem_posicao_analise",
    "make_service",
]
