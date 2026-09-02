# -*- coding: utf-8 -*-
"""Conferência e insights — desempenho das 3 bases estatísticas."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

BASES = ("geral", "vencedores", "acumulados")
BASES_LABEL = {
    "geral": "Geral",
    "vencedores": "Concursos com Vencedores",
    "acumulados": "Concursos Acumulados",
}


def contar_acertos_dezenas(dezenas: List[int], sorteadas: set, max_acertos: int = 7) -> int:
    return min(len(set(dezenas) & sorteadas), max_acertos)


def conferir_apostas_pontual(
    apostas: List[Dict[str, Any]],
    sorteadas: List[int],
    max_acertos: int = 7,
    *,
    positional: bool = False,
) -> Dict[str, Any]:
    set_sort = set(sorteadas)
    scores = []
    for i, ap in enumerate(apostas or [], start=1):
        dz = list(ap.get("dezenas") or [])
        if positional:
            n = min(len(dz), len(sorteadas), max_acertos)
            ac = sum(1 for j in range(n) if int(dz[j]) == int(sorteadas[j]))
            acertadas = [int(dz[j]) for j in range(n) if int(dz[j]) == int(sorteadas[j])]
        else:
            ac = contar_acertos_dezenas(dz, set_sort, max_acertos)
            acertadas = sorted(set(dz) & set_sort)
        scores.append({
            "numero": ap.get("numero", i),
            "dezenas": dz,
            "acertos": ac,
            "acertadas": acertadas,
        })
    dist = {3: 0, 4: 0, 5: 0, 6: 0, 7: 0}
    for s in scores:
        a = s["acertos"]
        if a in dist:
            dist[a] += 1
    total = sum(s["acertos"] for s in scores)
    n = len(scores)
    return {
        "qtd_apostas": n,
        "apostas": scores,
        "max_acertos": max((s["acertos"] for s in scores), default=0),
        "media_acertos": round(total / n, 2) if n else 0.0,
        "total_acertos": total,
        "dist_3": dist[3],
        "dist_4": dist[4],
        "dist_5": dist[5],
        "dist_6": dist[6],
        "dist_7": dist[7],
    }


def conferir_estrategias_pontual(
    apostas_por_base: Dict[str, List[Dict[str, Any]]],
    sorteadas: List[int],
    max_acertos: int = 7,
) -> Dict[str, Any]:
    resultado = {}
    for base in BASES:
        resultado[base] = conferir_apostas_pontual(
            apostas_por_base.get(base) or [], sorteadas, max_acertos,
        )
    ranking = sorted(
        BASES,
        key=lambda b: (
            -resultado[b]["max_acertos"],
            -resultado[b]["media_acertos"],
            -resultado[b]["total_acertos"],
        ),
    )
    return {"por_base": resultado, "ranking": ranking, "lider": ranking[0] if ranking else None}


def gerar_insights_panorama(registros: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Agrega registros persistidos e produz conclusões."""
    if not registros:
        return {"conclusoes": ["Nenhuma conferência registrada ainda."]}

    agg: Dict[str, Dict[str, float]] = {b: {"media_sum": 0.0, "max_sum": 0, "n": 0} for b in BASES}
    for reg in registros:
        for base in BASES:
            item = (reg.get("itens") or {}).get(base)
            if not item:
                continue
            agg[base]["media_sum"] += float(item.get("media_acertos") or 0)
            agg[base]["max_sum"] += int(item.get("max_acertos") or 0)
            agg[base]["n"] += 1

    medias = {}
    for base in BASES:
        n = agg[base]["n"]
        medias[base] = round(agg[base]["media_sum"] / n, 2) if n else 0.0

    conclusoes: List[str] = []
    com_dados = [b for b in BASES if agg[b]["n"] > 0]
    if com_dados:
        lider_media = max(com_dados, key=lambda b: medias[b])
        conclusoes.append(
            f"Maior média de acertos: **{BASES_LABEL[lider_media]}** ({medias[lider_media]} por conferência)."
        )
        ultimos = registros[:5]
        if len(ultimos) >= 2:
            recente = {}
            for base in BASES:
                vals = [
                    float((r.get("itens") or {}).get(base, {}).get("media_acertos") or 0)
                    for r in ultimos
                    if (r.get("itens") or {}).get(base)
                ]
                recente[base] = round(sum(vals) / len(vals), 2) if vals else 0.0
            lider_rec = max(com_dados, key=lambda b: recente.get(b, 0))
            conclusoes.append(
                f"Nos últimos {len(ultimos)} registros, lidera: **{BASES_LABEL[lider_rec]}** "
                f"(média {recente.get(lider_rec, 0)})."
            )

    estavel = None
    if len(registros) >= 3:
        variancias = {}
        for base in BASES:
            vals = [
                float((r.get("itens") or {}).get(base, {}).get("media_acertos") or 0)
                for r in registros
                if (r.get("itens") or {}).get(base)
            ]
            if len(vals) >= 2:
                m = sum(vals) / len(vals)
                variancias[base] = sum((v - m) ** 2 for v in vals) / len(vals)
        if variancias:
            estavel = min(variancias, key=variancias.get)
            conclusoes.append(
                f"Maior estabilidade histórica: **{BASES_LABEL[estavel]}** (menor variação de média)."
            )

    return {
        "conclusoes": conclusoes or ["Dados insuficientes para conclusões automáticas."],
        "medias_por_base": medias,
        "total_registros": len(registros),
    }
