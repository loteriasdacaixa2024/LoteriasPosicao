# -*- coding: utf-8 -*-
"""Concentração de Acertos — módulo experimental."""
from .service import ConcentracaoAcertosService
from .specs import (
    CONCENTRACAO_MODALITIES,
    estrategia_esta_ativa,
    get_concentracao_config,
    tem_concentracao_acertos,
)

__all__ = [
    "CONCENTRACAO_MODALITIES",
    "ConcentracaoAcertosService",
    "estrategia_esta_ativa",
    "get_concentracao_config",
    "tem_concentracao_acertos",
]
