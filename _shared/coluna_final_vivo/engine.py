# -*- coding: utf-8 -*-
from __future__ import annotations

from math import comb
from typing import Any, Dict, List, Optional, Tuple

from _shared.coluna_final_vivo.configs import (
    MODALIDADES,
    ModalidadeVolante,
    lista_comparativo,
)


def final_coluna(d: int) -> int:
    return 10 if d % 10 == 0 else d % 10


def linha_dezena(d: int) -> int:
    return (d - 1) // 10 + 1


def pct_teorico_coluna_2plus(cfg: ModalidadeVolante) -> float:
    """Prob. de ≥1 coluna com 2+ dezenas (finais todos diferentes no complemento)."""
    distintos = comb(cfg.colunas, cfg.sorteadas) * (cfg.dezenas_por_coluna ** cfg.sorteadas)
    total = comb(cfg.total_dezenas, cfg.sorteadas)
    if total <= 0:
        return 0.0
    return round((1 - distintos / total) * 100, 1)


def analisar_sorteio(dezenas: List[int], max_linhas: int = 8) -> Dict[str, Any]:
    col_counts = {c: 0 for c in range(1, 11)}
    lin_counts = {l: 0 for l in range(1, max_linhas + 1)}
    for d in dezenas:
        col_counts[final_coluna(d)] += 1
        lin = linha_dezena(d)
        if lin not in lin_counts:
            lin_counts[lin] = 0
        lin_counts[lin] += 1

    cols_2plus = [c for c, n in col_counts.items() if n >= 2]
    lins_2plus = [l for l, n in lin_counts.items() if n >= 2]
    max_col = max(col_counts.values()) if dezenas else 0
    max_lin = max(lin_counts.values()) if dezenas else 0

    return {
        "tem_coluna_2plus": len(cols_2plus) > 0,
        "tem_linha_2plus": len(lins_2plus) > 0,
        "finais_todos_distintos": len(dezenas) == len({final_coluna(d) for d in dezenas}),
        "colunas_com_2plus": cols_2plus,
        "linhas_com_2plus": lins_2plus,
        "max_coluna": max_col,
        "max_linha": max_lin,
        "col_counts": col_counts,
        "lin_counts": lin_counts,
    }


def agregar_historico(
    sorteios: List[Tuple[int, str, List[int]]],
    cfg: ModalidadeVolante,
) -> Dict[str, Any]:
    total = len(sorteios)
    if total == 0:
        return {
            "total_concursos": 0,
            "pct_coluna_2plus": 0.0,
            "pct_linha_2plus": 0.0,
            "pct_finais_distintos": 0.0,
            "qtd_coluna_2plus": 0,
            "qtd_linha_2plus": 0,
            "qtd_finais_distintos": 0,
            "ultimo": None,
            "serie_ultimos_20": [],
        }

    q_col = q_lin = q_dist = 0
    serie = []
    ultimo = None

    for concurso, data, dezenas in sorteios:
        geo = analisar_sorteio(dezenas, cfg.linhas)
        if geo["tem_coluna_2plus"]:
            q_col += 1
        if geo["tem_linha_2plus"]:
            q_lin += 1
        if geo["finais_todos_distintos"]:
            q_dist += 1
        item = {
            "concurso": concurso,
            "data": data,
            "tem_coluna_2plus": geo["tem_coluna_2plus"],
            "max_coluna": geo["max_coluna"],
        }
        serie.append(item)
        ultimo = {
            "concurso": concurso,
            "data": data,
            "dezenas": dezenas,
            **geo,
        }

    return {
        "total_concursos": total,
        "pct_coluna_2plus": round(q_col / total * 100, 1),
        "pct_linha_2plus": round(q_lin / total * 100, 1),
        "pct_finais_distintos": round(q_dist / total * 100, 1),
        "qtd_coluna_2plus": q_col,
        "qtd_linha_2plus": q_lin,
        "qtd_finais_distintos": q_dist,
        "ultimo": ultimo,
        "serie_ultimos_20": serie[-20:],
    }


def montar_payload(slug: str, sorteios: List[Tuple[int, str, List[int]]]) -> Dict[str, Any]:
    from datetime import datetime

    cfg = MODALIDADES.get(slug)
    if not cfg:
        raise KeyError(f"Modalidade não configurada: {slug}")

    vivo = agregar_historico(sorteios, cfg)
    teorico_col = pct_teorico_coluna_2plus(cfg)

    delta = None
    if vivo["total_concursos"] > 0:
        delta = round(vivo["pct_coluna_2plus"] - teorico_col, 1)

    return {
        "modalidade": slug,
        "nome": cfg.nome,
        "volante": {
            "sorteadas_por_concurso": cfg.sorteadas,
            "colunas_finais": cfg.colunas,
            "linhas": cfg.linhas,
        },
        "atualizado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "vivo": vivo,
        "teorico": {
            "pct_coluna_2plus": teorico_col,
            "pct_finais_distintos": round(100 - teorico_col, 1),
        },
        "delta_vs_teorico": delta,
        "comparativo_modalidades": lista_comparativo(),
        "legenda": (
            "Ao vivo = % de concursos no banco em que pelo menos uma coluna (final) "
            "teve 2 ou mais dezenas. Atualiza a cada consulta conforme novos sorteios entram."
        ),
    }
