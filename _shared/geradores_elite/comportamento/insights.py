# -*- coding: utf-8 -*-
"""Conclusões automáticas — comparação entre bases estatísticas (Geral / Vencedores / Acumulados)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

BASES_ORDEM = ("geral", "vencedores", "acumulados")

BASES_LABEL = {
    "geral": "Geral",
    "vencedores": "Concursos com Vencedores",
    "acumulados": "Concursos Acumulados",
}


def _resumo_seguro(analise: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not analise or not analise.get("sucesso"):
        return {}
    return analise.get("resumo") or {}


def _moda_ind(resumo: Dict[str, Any], cod: str) -> Optional[int]:
    r = resumo.get(cod) or {}
    m = r.get("moda")
    return int(m) if m is not None else None


def gerar_insights_comparativo(
    analises: Dict[str, Dict[str, Any]],
    indicadores: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Compara análises das três bases e produz conclusões objetivas.
    `analises` = { "geral": {...}, "vencedores": {...}, "acumulados": {...} }
    """
    inds = list(indicadores or [])
    if not inds:
        for key in BASES_ORDEM:
            a = analises.get(key) or {}
            if a.get("sucesso") and a.get("indicadores"):
                inds = [x["codigo"] for x in a["indicadores"]]
                break
        if not inds:
            inds = ["PA", "IM", "PR", "RT", "MO", "SQ", "M3", "FB", "MS"]

    resumos = {k: _resumo_seguro(analises.get(k)) for k in BASES_ORDEM}
    totais = {
        k: int((analises.get(k) or {}).get("total_concursos_base")
               or (analises.get(k) or {}).get("total_concursos") or 0)
        for k in BASES_ORDEM
    }
    conclusoes: List[str] = []

    g = analises.get("geral") or {}
    if g.get("aviso_base"):
        conclusoes.append(g["aviso_base"])

    for cod in inds:
        modas = {b: _moda_ind(resumos[b], cod) for b in BASES_ORDEM if resumos[b]}
        valores = {b: v for b, v in modas.items() if v is not None}
        if len(valores) < 2:
            continue
        unicos = set(valores.values())
        if len(unicos) == 1:
            conclusoes.append(
                f"{cod}: moda igual ({list(unicos)[0]}) nas bases comparadas."
            )
        else:
            partes = [f"{BASES_LABEL.get(b, b)}={v}" for b, v in valores.items()]
            conclusoes.append(f"{cod}: diferença entre bases — " + ", ".join(partes) + ".")

    # Destaque maior base vencedores vs acumulados em PA (pares)
    pa_v = _moda_ind(resumos.get("vencedores", {}), "PA")
    pa_a = _moda_ind(resumos.get("acumulados", {}), "PA")
    if pa_v is not None and pa_a is not None and pa_v != pa_a:
        if pa_v > pa_a:
            conclusoes.append(
                "Em concursos com vencedor predomina mais pares (PA) do que em acumulados."
            )
        else:
            conclusoes.append(
                "Em concursos acumulados predomina mais pares (PA) do que em concursos com vencedor."
            )

    rt_v = _moda_ind(resumos.get("vencedores", {}), "RT")
    rt_a = _moda_ind(resumos.get("acumulados", {}), "RT")
    if rt_v is not None and rt_a is not None and rt_v != rt_a:
        conclusoes.append(
            f"Repetição (RT): moda {rt_v} com vencedor vs {rt_a} em acumulados."
        )

    if totais["vencedores"] and totais["acumulados"]:
        pct_v = round(totais["vencedores"] / max(totais["geral"], 1) * 100, 1)
        pct_a = round(totais["acumulados"] / max(totais["geral"], 1) * 100, 1)
        conclusoes.insert(
            0,
            f"Base Geral: {totais['geral']} concursos — "
            f"{totais['vencedores']} com vencedor ({pct_v}%) · "
            f"{totais['acumulados']} acumulados ({pct_a}%).",
        )

    if not conclusoes:
        conclusoes.append("Dados insuficientes para comparar as três bases.")

    return {
        "conclusoes": conclusoes,
        "totais": totais,
        "modas_por_base": {
            b: {cod: _moda_ind(resumos[b], cod) for cod in inds}
            for b in BASES_ORDEM
            if resumos[b]
        },
    }
