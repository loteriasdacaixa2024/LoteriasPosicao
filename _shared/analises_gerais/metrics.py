# -*- coding: utf-8 -*-
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from _shared.analises_gerais.registry import ModalitySpec
from _shared.coluna_final_vivo.engine import (
    agregar_historico,
    analisar_sorteio,
    final_coluna,
    linha_dezena,
    pct_teorico_coluna_2plus,
)
PRIMOS_ATE_100 = {
    2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97
}


def _teorico_coluna_2plus(spec: ModalitySpec) -> Optional[float]:
    if spec.layout not in ("final10", "bloco5"):
        return None
    from math import comb

    cols = spec.colunas or 10
    dpc = 5 if spec.layout == "bloco5" else (spec.linhas or 6)
    distintos = comb(cols, spec.sorteadas) * (dpc ** spec.sorteadas)
    total = comb(spec.total_dezenas, spec.sorteadas)
    if total <= 0:
        return None
    return round((1 - distintos / total) * 100, 1)


def _ciclo_faltantes(
    sorteios: List[Tuple[int, str, List[int]]],
    total: int,
    zero_based: bool = False,
) -> Dict[str, Any]:
    universo = set(range(0, total)) if zero_based else set(range(1, total + 1))
    vistos: set = set()
    concursos_ciclo = 0
    for _, _, dz in sorteios:
        vistos.update(dz)
        concursos_ciclo += 1
        if vistos >= universo:
            vistos = set()
            concursos_ciclo = 0
    falt = sorted(universo - vistos)
    n_uni = len(universo)
    return {
        "faltantes": len(falt),
        "total_universo": n_uni,
        "pct_ciclo": round(len(vistos) / n_uni * 100, 1) if n_uni else 0,
        "concursos_no_ciclo": concursos_ciclo,
        "amostra_faltantes": [f"{x:02d}" for x in falt[:12]],
    }


def _geo_draw(dz: List[int], spec: ModalitySpec, max_lin: int) -> Optional[Dict[str, Any]]:
    if spec.layout == "bloco5":
        col_counts = Counter((d - 1) // 5 + 1 for d in dz)
        lin_counts = Counter(linha_dezena(d) for d in dz if d <= spec.total_dezenas)
        cols_2 = [c for c, n in col_counts.items() if n >= 2]
        lins_2 = [l for l, n in lin_counts.items() if n >= 2]
        return {
            "tem_coluna_2plus": len(cols_2) > 0,
            "tem_linha_2plus": len(lins_2) > 0,
            "finais_todos_distintos": len(col_counts) == len(dz),
        }
    if spec.layout == "final10":
        return analisar_sorteio(dz, max_lin)
    return None


def _quadrantes_mega(dezenas: List[int]) -> Tuple[int, int, int, int]:
    q = {1: 0, 2: 0, 3: 0, 4: 0}
    sets = {
        1: {1, 2, 3, 4, 5, 11, 12, 13, 14, 15, 21, 22, 23, 24, 25},
        2: {6, 7, 8, 9, 10, 16, 17, 18, 19, 20, 26, 27, 28, 29, 30},
        3: {31, 32, 33, 34, 35, 41, 42, 43, 44, 45, 51, 52, 53, 54, 55},
        4: {36, 37, 38, 39, 40, 46, 47, 48, 49, 50, 56, 57, 58, 59, 60},
    }
    for d in dezenas:
        for qi, st in sets.items():
            if d in st:
                q[qi] += 1
    return q[1], q[2], q[3], q[4]


def calcular_resumo_supersete(
    spec: ModalitySpec,
    sorteios: List[Tuple[int, str, List[int]]],
) -> Dict[str, Any]:
    """Métricas próprias: 7 colunas C1–C7, um dígito 0–9 por coluna (não é volante de dezenas)."""
    total = len(sorteios)
    porta = spec.porta
    base = {
        "key": spec.key,
        "nome": spec.nome,
        "porta": porta,
        "grupo": "supersete",
        "layout": "posicional",
        "aposta_label": "7 colunas (0–9 cada)",
        "links": {
            "analise": f"http://localhost:{porta}/analise/",
            "gerador": f"http://localhost:{porta}/geradores-elite/apostas-inteligentes/",
            "desdobramento": f"http://localhost:{porta}/desdobramento/",
        },
    }
    if total == 0:
        return {**base, "total_concursos": 0, "erro": "Sem sorteios no banco"}

    rep_mesmo_concurso = 0
    sete_distintos = 0
    par_impar = Counter()
    primos_qtd = Counter()
    soma_total = []

    for _, _, dz in sorteios:
        if len(dz) < 7:
            continue
        cols = dz[:7]
        if len(set(cols)) < 7:
            rep_mesmo_concurso += 1
        if len(set(cols)) == 7:
            sete_distintos += 1
        pares = sum(1 for d in cols if d % 2 == 0)
        par_impar[(pares, 7 - pares)] += 1
        primos_qtd[sum(1 for d in cols if d in {2, 3, 5, 7})] += 1
        soma_total.append(sum(cols))

    colunas_rank = []
    for i in range(7):
        freq = Counter()
        for _, _, dz in sorteios:
            if len(dz) > i:
                freq[dz[i]] += 1
        dig, q = freq.most_common(1)[0] if freq else (None, 0)
        colunas_rank.append({
            "coluna": f"C{i + 1}",
            "digito_mais_freq": dig,
            "pct": round(q / total * 100, 1) if total else 0,
        })

    # Ciclo por coluna: em cada Ck, quantos dígitos 0–9 ainda não saíram no “ciclo” atual
    faltantes_por_col = []
    for i in range(7):
        vistos: set = set()
        concursos_ciclo = 0
        for _, _, dz in reversed(sorteios):
            if len(dz) <= i:
                continue
            vistos.add(dz[i])
            concursos_ciclo += 1
            if len(vistos) == 10:
                vistos = set()
                concursos_ciclo = 0
        faltantes_por_col.append(10 - len(vistos))

    moda_pi = par_impar.most_common(1)[0] if par_impar else (0, 0)
    soma_media = round(sum(soma_total) / len(soma_total), 1) if soma_total else 0

    ultimo = sorteios[-1][2][:7]
    return {
        **base,
        "total_concursos": total,
        "ultimo_concurso": sorteios[-1][0],
        "ultimo_data": sorteios[-1][1],
        "ultimo_digitos": ultimo,
        "pct_mesmo_digito_2colunas": round(rep_mesmo_concurso / total * 100, 1),
        "pct_7_digitos_distintos": round(sete_distintos / total * 100, 1),
        "par_impar_moda": f"{moda_pi[0]}P/{moda_pi[1]}I",
        "primos_moda": primos_qtd.most_common(1)[0][0] if primos_qtd else 0,
        "soma_media": soma_media,
        "colunas_rank": colunas_rank,
        "ciclo_faltantes_media": round(sum(faltantes_por_col) / 7, 1),
        "ciclo_faltantes_por_coluna": faltantes_por_col,
        "nota": (
            "Cada coluna C1–C7 sorteia 1 dígito (0–9). Não usa “final de dezena” nem "
            "volante 6×10. Compare repetição do mesmo dígito em colunas diferentes no mesmo concurso."
        ),
    }


def calcular_resumo(
    spec: ModalitySpec,
    sorteios: List[Tuple[int, str, List[int]]],
) -> Dict[str, Any]:
    if spec.layout == "posicional" or spec.grupo == "supersete":
        return calcular_resumo_supersete(spec, sorteios)

    total = len(sorteios)
    if total == 0:
        return {
            "key": spec.key,
            "nome": spec.nome,
            "porta": spec.porta,
            "aposta_label": f"{spec.sorteadas} de {spec.total_dezenas}",
            "total_concursos": 0,
            "erro": "Sem sorteios no banco",
        }

    par_impar = Counter()
    primos_qtd = Counter()
    linha_2plus = 0
    col_2plus = 0
    finais_dist = 0
    quadrante_dom = Counter()

    max_lin = spec.linhas or 8

    for _, _, dz in sorteios:
        pares = sum(1 for d in dz if d % 2 == 0)
        imp = len(dz) - pares
        par_impar[(pares, imp)] += 1

        primos_qtd[sum(1 for d in dz if d in PRIMOS_ATE_100)] += 1

        geo = _geo_draw(dz, spec, max_lin)
        if geo:
            if geo["tem_coluna_2plus"]:
                col_2plus += 1
            if geo["finais_todos_distintos"]:
                finais_dist += 1
            if geo["tem_linha_2plus"]:
                linha_2plus += 1
        if spec.key == "megasena":
            q = _quadrantes_mega(dz)
            quadrante_dom[max(range(4), key=lambda i: q[i]) + 1] += 1

    moda_pi = par_impar.most_common(1)[0][0] if par_impar else (0, 0)
    moda_primos = primos_qtd.most_common(1)[0][0] if primos_qtd else 0

    linha_freq = Counter()
    if spec.layout == "final10":
        for _, _, dz in sorteios:
            for d in dz:
                linha_freq[linha_dezena(d)] += 1
    linha_top = linha_freq.most_common(1)[0] if linha_freq else (None, 0)

    col_freq = Counter()
    if spec.layout in ("final10", "bloco5"):
        for _, _, dz in sorteios:
            for d in dz:
                if spec.layout == "bloco5":
                    c = (d - 1) // 5 + 1
                else:
                    c = final_coluna(d)
                col_freq[c] += 1
    col_top = col_freq.most_common(1)[0] if col_freq else (None, 0)

    ciclo = _ciclo_faltantes(
        sorteios,
        spec.total_dezenas,
        zero_based=(spec.key == "lotomania"),
    )

    teorico_col = _teorico_coluna_2plus(spec)
    teorico_dist = round(100 - teorico_col, 1) if teorico_col is not None else None

    ultimo = sorteios[-1]
    ult_geo = None
    ult_geo = _geo_draw(ultimo[2], spec, max_lin)

    has_geo = spec.layout in ("final10", "bloco5")
    pct_col = round(col_2plus / total * 100, 1) if has_geo else None
    pct_dist = round(finais_dist / total * 100, 1) if has_geo else None
    pct_lin = round(linha_2plus / total * 100, 1) if has_geo else None

    return {
        "key": spec.key,
        "nome": spec.nome,
        "porta": spec.porta,
        "aposta_label": f"{spec.sorteadas} de {spec.total_dezenas}",
        "total_concursos": total,
        "ultimo_concurso": ultimo[0],
        "ultimo_data": ultimo[1],
        "pct_coluna_2plus": pct_col,
        "pct_finais_distintos": pct_dist,
        "pct_linha_2plus": pct_lin,
        "teorico_pct_coluna_2plus": teorico_col,
        "teorico_pct_finais_distintos": teorico_dist,
        "delta_coluna_2plus": round(pct_col - teorico_col, 1) if pct_col is not None and teorico_col else None,
        "par_impar_moda": f"{moda_pi[0]}P/{moda_pi[1]}I",
        "primos_moda": moda_primos,
        "primos_media": round(sum(k * v for k, v in primos_qtd.items()) / total, 2),
        "linha_mais_freq": linha_top[0],
        "coluna_mais_freq": col_top[0] if col_top[0] is not None else None,
        "coluna_mais_freq_label": "0" if col_top[0] == 10 else str(col_top[0]) if col_top[0] else "—",
        "quadrante_mais_freq": quadrante_dom.most_common(1)[0][0] if quadrante_dom else None,
        "ciclo_faltantes": ciclo["faltantes"],
        "ciclo_pct": ciclo["pct_ciclo"],
        "ciclo_total_universo": ciclo["total_universo"],
        "ciclo_faltantes_amostra": ciclo["amostra_faltantes"],
        "ultimo_tem_coluna_2plus": ult_geo["tem_coluna_2plus"] if ult_geo else None,
        "layout": spec.layout,
        "grupo": spec.grupo,
        "links": {
            "analise": f"http://localhost:{spec.porta}/analise/",
            "gerador": f"http://localhost:{spec.porta}/geradores-elite/apostas-inteligentes/",
            "desdobramento": f"http://localhost:{spec.porta}/desdobramento/",
        },
    }
