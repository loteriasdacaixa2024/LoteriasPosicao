# -*- coding: utf-8 -*-
"""Pontuação de concentração — histórico recente."""
from __future__ import annotations

import math
from typing import Any, Dict, List, Sequence, Set


def _acertos(dezenas: List[int], sorteadas: Set[int], max_ac: int) -> int:
    return min(len(set(dezenas) & sorteadas), max_ac)


def avaliar_conjunto(
    apostas: List[List[int]],
    historico: Sequence[Set[int]],
    max_acertos: int = 7,
) -> Dict[str, Any]:
    if not apostas or not historico:
        return {
            "score": 0.0,
            "media_max_acertos": 0.0,
            "media_top2": 0.0,
            "indice_concentracao": 0.0,
            "dist_4": 0,
            "dist_5": 0,
            "dist_6": 0,
            "dist_7": 0,
        }

    total_max = 0.0
    total_top2 = 0.0
    total_sq = 0.0
    dist = {4: 0, 5: 0, 6: 0, 7: 0}

    for sorteadas in historico:
        hits = sorted(
            (_acertos(dz, sorteadas, max_acertos) for dz in apostas),
            reverse=True,
        )
        mx = hits[0] if hits else 0
        top2 = sum(hits[:2]) if len(hits) >= 2 else mx
        total_max += mx
        total_top2 += top2
        total_sq += sum(h * h for h in hits)

        if mx in dist:
            dist[mx] += 1

    n = len(historico)
    media_max = total_max / n
    media_top2 = total_top2 / n
    indice = total_sq / (n * max(len(apostas), 1))

    # Score composto: prioriza pico de acertos e penaliza dispersão
    score = (
        media_max * 12.0
        + media_top2 * 4.0
        + indice * 2.5
        + dist[7] * 8.0
        + dist[6] * 4.0
        + dist[5] * 2.0
        + dist[4] * 0.5
    )

    return {
        "score": round(score, 4),
        "media_max_acertos": round(media_max, 3),
        "media_top2": round(media_top2, 3),
        "indice_concentracao": round(indice, 3),
        "dist_4": dist[4],
        "dist_5": dist[5],
        "dist_6": dist[6],
        "dist_7": dist[7],
    }


def score_com_penalidade(
    apostas: List[List[int]],
    historico: Sequence[Set[int]],
    penalidade: float,
    max_acertos: int = 7,
) -> float:
    base = avaliar_conjunto(apostas, historico, max_acertos)
    return base["score"] - penalidade
