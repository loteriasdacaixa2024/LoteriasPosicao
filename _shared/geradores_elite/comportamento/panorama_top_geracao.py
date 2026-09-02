# -*- coding: utf-8 -*-
"""Geração de apostas com alvos do Panorama Top-3."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

_MS_IGNORAR = {0}

RANK_LABELS = {1: "1º ranking", 2: "2º ranking", 3: "3º ranking"}


def normalizar_rank_escolhido(rank: Any) -> int:
    try:
        r = int(rank)
    except (TypeError, ValueError):
        return 1
    return max(1, min(3, r))


def label_rank_escolhido(rank: int) -> str:
    return RANK_LABELS.get(normalizar_rank_escolhido(rank), f"{rank}º ranking")


def montar_alvos_por_rank(
    indicadores_out: List[Dict[str, Any]],
    indicadores: List[str],
    rank_escolhido: int = 1,
) -> Tuple[Dict[str, int], Dict[str, Any]]:
    """
    Usa a linha do panorama (1º, 2º ou 3º rank) como alvo fixo para cada indicador.
    MS: ignora valor 0 na linha escolhida (sem alvo de mês).
    """
    rank_escolhido = normalizar_rank_escolhido(rank_escolhido)
    idx = rank_escolhido - 1
    by_cod = {ind.get("codigo"): ind for ind in indicadores_out}
    alvos: Dict[str, int] = {}
    meta: Dict[str, Any] = {}

    for cod in indicadores:
        ind = by_cod.get(cod)
        if not ind:
            continue
        ranking = ind.get("ranking") or []
        if idx >= len(ranking):
            continue
        pick = ranking[idx]
        if cod == "MS" and int(pick.get("valor", 0)) in _MS_IGNORAR:
            continue
        alvos[cod] = int(pick["valor"])
        meta[cod] = {
            "ranking": pick.get("ranking"),
            "rank_linha": rank_escolhido,
            "valor_label": pick.get("valor_label"),
            "percentual": pick.get("percentual"),
        }
    return alvos, meta


def score_minimo_panorama(
    n_indicadores: int,
    rank_escolhido: int = 1,
    modo: str = "estrito",
) -> int:
    """Mínimo de pontos (cada acerto exato = 10) para aceitar a aposta."""
    _ = normalizar_rank_escolhido(rank_escolhido)
    if n_indicadores <= 0:
        return 0
    if (modo or "estrito").strip().lower() == "relaxar":
        min_acertos = max(3, int(n_indicadores * 0.5))
    else:
        min_acertos = max(5, int(n_indicadores * 0.75))
    return min_acertos * 10
