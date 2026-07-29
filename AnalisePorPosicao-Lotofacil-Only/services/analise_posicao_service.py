# -*- coding: utf-8 -*-
"""Análise por Posição — delegação ao módulo compartilhado."""
import os
import sys

_SHARED = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from posicao_analise.service_factory import make_service

AnalisePosicaoService = make_service("lotofacil")
