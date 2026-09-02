# -*- coding: utf-8 -*-
"""Configuração por modalidade — Gaps + Inicial/Ciclo."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

from analise_estudos.specs import get_estudos_config, tem_analise_estudos

# Restrição de inicial e do valor máximo de GAP (Dia de Sorte: 26–31 fora da inicial;
# GAP 26 não é válido — impediria sequências tipo 25–31 como “vão” de 26).
_INICIAL_MAX_OVERRIDE = {
    "diadesorte": 25,
}
_GAP_MAX_OVERRIDE = {
    "diadesorte": 25,
}


def tem_gaps_ciclo(modality_key: str) -> bool:
    return tem_analise_estudos(modality_key)


def get_gaps_ciclo_spec(modality_key: str) -> Dict[str, Any]:
    est = get_estudos_config(modality_key)
    dmin = int(est["dezena_min"])
    dmax = int(est["dezena_max"])
    k = int(est["sorteadas"])
    pad = int(est.get("pad_width") or (1 if dmax < 10 else 2))
    default_max = max(dmin, dmax - max(0, k - 1))
    inicial_max = int(_INICIAL_MAX_OVERRIDE.get(modality_key, default_max))
    inicial_max = min(max(inicial_max, dmin), dmax)
    iniciais = list(range(dmin, inicial_max + 1))
    gap_max = int(_GAP_MAX_OVERRIDE.get(modality_key, min(dmax - dmin, 25)))
    gap_max = max(1, min(gap_max, dmax - dmin))
    if dmax >= 10:
        pad = max(2, pad)
    return {
        "key": modality_key,
        "nome": est["nome"],
        "dezena_min": dmin,
        "dezena_max": dmax,
        "sorteadas": k,
        "pad_width": pad,
        "janelas_ui": list(est["janelas_ui"]),
        "janela_default": int(est["janela_default"]),
        "extra_mes": bool(est.get("extra_mes")),
        "inicial_min": dmin,
        "inicial_max": inicial_max,
        "iniciais_permitidas": iniciais,
        "qtd_apostas_default": 10,
        "qtd_apostas_max": 30,
        "analise_url": "/analise/gaps-ciclo/",
        "gerador_url": "/geradores-elite/gaps-ciclo-apostas/",
    }


def iniciais_permitidas(modality_key: str) -> List[int]:
    return list(get_gaps_ciclo_spec(modality_key)["iniciais_permitidas"])


def spec_copy(modality_key: str) -> Dict[str, Any]:
    return deepcopy(get_gaps_ciclo_spec(modality_key))
