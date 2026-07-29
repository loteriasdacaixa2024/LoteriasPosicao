# -*- coding: utf-8 -*-
"""Extração de ganhadores da faixa principal (7 acertos) — API Caixa Dia de Sorte."""
from __future__ import annotations

from typing import Any, Dict, Optional


def extrair_ganhadores_7(dados: Dict[str, Any]) -> Optional[int]:
    """
    Retorna quantidade de ganhadores na faixa principal (7 acertos).
    None se a API não trouxer listaRateioPremio utilizável.
    """
    if not dados:
        return None
    lista = dados.get("listaRateioPremio")
    if not isinstance(lista, list):
        return None
    for item in lista:
        if not isinstance(item, dict):
            continue
        desc = (item.get("descricaoFaixa") or "").strip().lower()
        faixa = item.get("faixa")
        if desc == "7 acertos" or faixa == 1:
            try:
                return max(0, int(item.get("numeroDeGanhadores", 0)))
            except (TypeError, ValueError):
                return 0
    return None


def classificar_base_concurso(ganhadores_7: Optional[int]) -> Optional[str]:
    """'vencedores' | 'acumulados' | None (desconhecido)."""
    if ganhadores_7 is None:
        return None
    return "vencedores" if ganhadores_7 >= 1 else "acumulados"
