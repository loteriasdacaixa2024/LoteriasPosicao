# -*- coding: utf-8 -*-
"""Geometria Analítica do volante Dia de Sorte.

Volante fixo:
    linha 1: 01–10
    linha 2: 11–20
    linha 3: 21–30
    linha 4: somente 31

Novos indicadores entram em `indicadores_de` sem mudar Gaps nem Régua.
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

Coord = Tuple[int, int]
_VIZ_DIAG = ((1, 1), (1, -1), (-1, 1), (-1, -1))


def coord_dezena(n: int) -> Optional[Coord]:
    """Linha e coluna 0-based. O 31 fica isolado na linha 4, coluna 1."""
    v = int(n)
    if v == 31:
        return (3, 0)
    if 1 <= v <= 30:
        return ((v - 1) // 10, (v - 1) % 10)
    return None


def _fmt(n: int) -> str:
    return f"{int(n):02d}"


def _dist(a: Coord, b: Coord) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _sequencias_horizontais(dezenas: Sequence[int]) -> List[str]:
    por_linha: Dict[int, List[int]] = defaultdict(list)
    for n in dezenas:
        if int(n) == 31:
            continue
        c = coord_dezena(int(n))
        if c is None or c[0] > 2:
            continue
        por_linha[c[0]].append(int(n))
    saida: List[str] = []
    for nums in por_linha.values():
        ordenados = sorted(set(nums))
        grupo = [ordenados[0]] if ordenados else []
        for atual in ordenados[1:]:
            if atual == grupo[-1] + 1:
                grupo.append(atual)
                continue
            if len(grupo) >= 2:
                saida.append("-".join(_fmt(x) for x in grupo))
            grupo = [atual]
        if len(grupo) >= 2:
            saida.append("-".join(_fmt(x) for x in grupo))
    return saida


def _diagonais(dezenas: Sequence[int]) -> List[str]:
    celulas: Dict[Coord, int] = {}
    for n in dezenas:
        if int(n) == 31:
            continue
        c = coord_dezena(int(n))
        if c is None or c[0] > 2:
            continue
        celulas[c] = int(n)
    vistos: Set[Coord] = set()
    saida: List[str] = []
    for origem in celulas:
        if origem in vistos:
            continue
        pilha = [origem]
        comp: List[Coord] = []
        vistos.add(origem)
        while pilha:
            atual = pilha.pop()
            comp.append(atual)
            for dr, dc in _VIZ_DIAG:
                viz = (atual[0] + dr, atual[1] + dc)
                if viz in celulas and viz not in vistos:
                    vistos.add(viz)
                    pilha.append(viz)
        if len(comp) < 2:
            continue
        comp.sort()
        saida.append("-".join(_fmt(celulas[p]) for p in comp))
    return saida


def _rotulo_centro(linha_media: float, coluna_media: float) -> str:
    if linha_media >= 2.5:
        linha = "linha do 31"
    else:
        linha = f"linha {int(round(linha_media)) + 1}"
    coluna = int(round(coluna_media)) + 1
    return f"{linha} · coluna {coluna}"


def indicadores_de(dezenas: Iterable[int]) -> Dict[str, Any]:
    """Indicadores de um concurso. Campos novos podem ser acrescentados aqui."""
    nums = sorted({int(n) for n in dezenas if coord_dezena(int(n)) is not None})
    coords = {n: coord_dezena(n) for n in nums}
    linhas = [
        sum(1 for n in nums if coords[n][0] == 0),
        sum(1 for n in nums if coords[n][0] == 1),
        sum(1 for n in nums if coords[n][0] == 2),
        1 if 31 in coords else 0,
    ]
    no_grid = [n for n in nums if n != 31]
    colunas = [coords[n][1] + 1 for n in no_grid]
    cont_col = Counter(colunas)
    repetidas = [
        {
            "coluna": col,
            "qtd": qtd,
            "dezenas": [n for n in no_grid if coords[n][1] + 1 == col],
        }
        for col, qtd in sorted(cont_col.items())
        if qtd > 1
    ]
    faixas = {"esquerda": 0, "centro": 0, "direita": 0}
    for n in no_grid:
        col = coords[n][1] + 1
        if col <= 3:
            faixas["esquerda"] += 1
        elif col <= 7:
            faixas["centro"] += 1
        else:
            faixas["direita"] += 1
    faixa_mais = max(faixas, key=lambda nome: (faixas[nome], nome))
    linha_contagens = linhas[:3]
    linha_max = max(linha_contagens) if linha_contagens else 0
    linhas_mais = [i + 1 for i, qtd in enumerate(linha_contagens) if qtd == linha_max and qtd]

    pontos = [coords[n] for n in nums]
    if len(pontos) >= 2:
        pares = []
        maior = 0.0
        par_maior = [nums[0], nums[1]]
        for i, a in enumerate(nums):
            for b in nums[i + 1:]:
                d = _dist(coords[a], coords[b])
                pares.append(d)
                if d > maior:
                    maior = d
                    par_maior = [a, b]
        media = sum(pares) / len(pares)
    else:
        media = 0.0
        maior = 0.0
        par_maior = []
    media_r = sum(p[0] for p in pontos) / len(pontos) if pontos else 0.0
    media_c = sum(p[1] for p in pontos) / len(pontos) if pontos else 0.0
    if len(pontos) >= 2:
        var_r = sum((p[0] - media_r) ** 2 for p in pontos) / len(pontos)
        var_c = sum((p[1] - media_c) ** 2 for p in pontos) / len(pontos)
        desvio_r = math.sqrt(var_r)
        desvio_c = math.sqrt(var_c)
    else:
        desvio_r = 0.0
        desvio_c = 0.0
    indice = int(round(min(100.0, (media / math.hypot(3, 9)) * 100))) if pontos else 0

    outras = [n for n in nums if n != 31]
    if 31 in coords and outras:
        dist_31 = [_dist(coords[31], coords[n]) for n in outras]
        media_31 = sum(dist_31) / len(dist_31)
        outras_linhas = [
            sum(1 for n in outras if coords[n][0] == 0),
            sum(1 for n in outras if coords[n][0] == 1),
            sum(1 for n in outras if coords[n][0] == 2),
        ]
    else:
        media_31 = None
        outras_linhas = []

    return {
        "linhas": linhas,
        "linhas_fmt": " - ".join(str(x) for x in linhas),
        "tem_31": 31 in coords,
        "colunas": colunas,
        "colunas_distintas": len(cont_col),
        "colunas_repetidas": repetidas,
        "concentracao": {
            "linhas_mais": linhas_mais,
            "faixas": faixas,
            "faixa_mais": faixa_mais,
        },
        "dispersao": {
            "desvio_linha": round(desvio_r, 2),
            "desvio_coluna": round(desvio_c, 2),
            "indice": indice,
        },
        "sequencias": _sequencias_horizontais(nums),
        "diagonais": _diagonais(nums),
        "distancias": {
            "media": round(media, 2),
            "maior": round(maior, 2),
            "par_maior": par_maior,
        },
        "centro": {
            "linha": round(media_r, 2),
            "coluna": round(media_c, 2),
            "rotulo": _rotulo_centro(media_r, media_c),
        },
        "analise_31": {
            "presente": 31 in coords,
            "outras_linhas": outras_linhas,
            "distancia_media": None if media_31 is None else round(media_31, 2),
        },
    }


def analisar_geometria(linhas: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Um registro por concurso já carregado em Gaps/Régua, mais o resumo da janela."""
    por_concurso: Dict[str, Dict[str, Any]] = {}
    padroes: Counter = Counter()
    com_31 = 0
    for row in linhas or []:
        dezenas = list(row.get("dezenas_classificado") or row.get("dezenas") or [])
        ind = indicadores_de(dezenas)
        concurso = row.get("concurso")
        por_concurso[str(concurso)] = ind
        padroes[ind["linhas_fmt"]] += 1
        if ind["tem_31"]:
            com_31 += 1
    total = len(por_concurso)
    return {
        "sucesso": True,
        "sessao": "geometria",
        "volante": [
            list(range(1, 11)),
            list(range(11, 21)),
            list(range(21, 31)),
            [31],
        ],
        "por_concurso": por_concurso,
        "historico": {
            "total": total,
            "com_31": com_31,
            "sem_31": max(0, total - com_31),
            "padroes_linha": [
                {"padrao": padrao, "frequencia": int(qtd)}
                for padrao, qtd in padroes.most_common(8)
            ],
        },
    }
