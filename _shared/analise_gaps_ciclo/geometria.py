# -*- coding: utf-8 -*-
"""Geometria Analítica do volante.

O Dia de Sorte permanece com o volante validado:
    linha 1: 01–10
    linha 2: 11–20
    linha 3: 21–30
    linha 4: somente 31

As demais modalidades usam a mesma leitura (linhas, colunas, concentração,
dispersão, sequências, diagonais, distâncias e centro) sobre a grade do
próprio volante. O 31 isolado só existe no Dia de Sorte.

Novos indicadores entram em `indicadores_de` sem mudar Gaps nem Régua.
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

Coord = Tuple[int, int]
Ponto = Tuple[int, Coord]
_VIZ_DIAG = ((1, 1), (1, -1), (-1, 1), (-1, -1))


@dataclass(frozen=True)
class LayoutVolante:
    dmin: int
    dmax: int
    cols: int
    rows: int
    volante: Tuple[Tuple[int, ...], ...]
    isolado: Optional[int]
    posicional: bool

    def linha_isolada(self, row: int) -> bool:
        if row < 0 or row >= len(self.volante):
            return False
        return len(self.volante[row]) < self.cols


def layout_de(modality_key: str) -> LayoutVolante:
    from analise_estudos.specs import get_estudos_config

    est = get_estudos_config(modality_key)
    dmin = int(est["dezena_min"])
    dmax = int(est["dezena_max"])
    if modality_key == "supersete":
        cols, rows = 7, 10
        volante = tuple(tuple(d for _c in range(cols)) for d in range(rows))
        return LayoutVolante(dmin, dmax, cols, rows, volante, None, True)

    cols = int(est["volante_cols"])
    rows = int(est["volante_rows"])
    nums = list(range(dmin, dmax + 1))
    fatias: List[Tuple[int, ...]] = []
    for r in range(rows):
        fatia = tuple(nums[r * cols:(r + 1) * cols])
        if fatia:
            fatias.append(fatia)
    isolado = fatias[-1][0] if len(fatias) > 1 and len(fatias[-1]) == 1 else None
    return LayoutVolante(dmin, dmax, cols, len(fatias), tuple(fatias), isolado, False)


def legenda_layout(layout: LayoutVolante) -> str:
    if layout.posicional:
        return "7 colunas, dígitos 0–9"
    partes: List[str] = []
    for row in layout.volante:
        if len(row) == 1:
            partes.append(f"o {_fmt(row[0])} isolado")
        else:
            partes.append(f"{_fmt(row[0])}–{_fmt(row[-1])}")
    if not partes:
        return "volante"
    if len(partes) == 1:
        return "linha " + partes[0]
    return "linhas " + ", ".join(partes[:-1]) + " e " + partes[-1]


def resumo_layout(modality_key: str) -> Dict[str, Any]:
    layout = layout_de(modality_key)
    return {
        "geo_legenda": legenda_layout(layout),
        "geo_posicional": layout.posicional,
        "geo_isolado": layout.isolado,
        "geo_rows": layout.rows,
        "geo_cols": layout.cols,
    }


def _fmt(n: int) -> str:
    return f"{int(n):02d}"


def _dist(a: Coord, b: Coord) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _coord_grade(n: int, layout: LayoutVolante) -> Optional[Coord]:
    v = int(n)
    if v < layout.dmin or v > layout.dmax or layout.cols <= 0:
        return None
    idx = v - layout.dmin
    r, c = divmod(idx, layout.cols)
    if r >= len(layout.volante) or c >= len(layout.volante[r]):
        return None
    return (r, c)


def _pontos(dezenas: Iterable[int], layout: LayoutVolante) -> List[Ponto]:
    if layout.posicional:
        pts: List[Ponto] = []
        for i, n in enumerate(dezenas):
            if i >= layout.cols:
                break
            d = int(n)
            if 0 <= d < layout.rows:
                pts.append((d, (d, i)))
        return pts
    nums = sorted({
        int(n) for n in dezenas if _coord_grade(int(n), layout) is not None
    })
    return [(n, _coord_grade(n, layout)) for n in nums]  # type: ignore[misc]


def _sequencias_horizontais(pontos: Sequence[Ponto], layout: LayoutVolante) -> List[str]:
    if layout.posicional:
        por_linha: Dict[int, List[Tuple[int, int]]] = defaultdict(list)
        for label, (r, c) in pontos:
            por_linha[r].append((c, int(label)))
        saida: List[str] = []
        for itens in por_linha.values():
            ordenados = sorted(set(itens))
            grupo = [ordenados[0]] if ordenados else []
            for atual in ordenados[1:]:
                if atual[0] == grupo[-1][0] + 1:
                    grupo.append(atual)
                    continue
                if len(grupo) >= 2:
                    saida.append("-".join(_fmt(lab) for _, lab in grupo))
                grupo = [atual]
            if len(grupo) >= 2:
                saida.append("-".join(_fmt(lab) for _, lab in grupo))
        return saida

    por: Dict[int, List[int]] = defaultdict(list)
    for label, (r, _c) in pontos:
        if layout.linha_isolada(r):
            continue
        por[r].append(int(label))
    saida = []
    for nums in por.values():
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


def _diagonais(pontos: Sequence[Ponto], layout: LayoutVolante) -> List[str]:
    celulas: Dict[Coord, int] = {}
    for label, coord in pontos:
        if layout.linha_isolada(coord[0]):
            continue
        celulas[coord] = int(label)
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


def _rotulo_centro(linha_media: float, coluna_media: float, layout: LayoutVolante) -> str:
    if layout.isolado is not None and linha_media >= (layout.rows - 1) - 0.5:
        linha = f"linha do {layout.isolado}"
    elif layout.posicional:
        linha = f"dígito {int(round(linha_media))}"
    else:
        linha = f"linha {int(round(linha_media)) + 1}"
    coluna = int(round(coluna_media)) + 1
    return f"{linha} · coluna {coluna}"


def _faixa(col: int, cols: int) -> str:
    borda = max(1, cols // 3)
    if col <= borda:
        return "esquerda"
    if col <= cols - borda:
        return "centro"
    return "direita"


def indicadores_de(
    dezenas: Iterable[int],
    layout: Optional[LayoutVolante] = None,
) -> Dict[str, Any]:
    """Indicadores de um concurso. Campos novos podem ser acrescentados aqui."""
    lay = layout or layout_de("diadesorte")
    pontos = _pontos(dezenas, lay)
    linhas = [
        sum(1 for _lab, (r, _c) in pontos if r == i)
        for i in range(len(lay.volante))
    ]
    principais = [p for p in pontos if not lay.linha_isolada(p[1][0])]
    colunas = [c + 1 for _lab, (_r, c) in principais]
    cont_col = Counter(colunas)
    repetidas = [
        {
            "coluna": col,
            "qtd": qtd,
            "dezenas": [lab for lab, (_r, c) in principais if c + 1 == col],
        }
        for col, qtd in sorted(cont_col.items())
        if qtd > 1
    ]
    faixas = {"esquerda": 0, "centro": 0, "direita": 0}
    for col in colunas:
        faixas[_faixa(col, lay.cols)] += 1
    faixa_mais = max(faixas, key=lambda nome: (faixas[nome], nome)) if faixas else "centro"
    idxs_cheias = [i for i in range(len(lay.volante)) if not lay.linha_isolada(i)]
    contagens = [linhas[i] for i in idxs_cheias]
    linha_max = max(contagens) if contagens else 0
    linhas_mais = [i + 1 for i in idxs_cheias if linhas[i] == linha_max and linha_max]

    todos_coord = [c for _lab, c in pontos]
    labels = [lab for lab, _c in pontos]
    if len(todos_coord) >= 2:
        pares = []
        maior = 0.0
        par_maior = [labels[0], labels[1]]
        for i, a in enumerate(labels):
            for j, b in enumerate(labels[i + 1:], start=i + 1):
                d = _dist(todos_coord[i], todos_coord[j])
                pares.append(d)
                if d > maior:
                    maior = d
                    par_maior = [a, b]
        media = sum(pares) / len(pares)
    else:
        media = 0.0
        maior = 0.0
        par_maior = []
    media_r = sum(p[0] for p in todos_coord) / len(todos_coord) if todos_coord else 0.0
    media_c = sum(p[1] for p in todos_coord) / len(todos_coord) if todos_coord else 0.0
    if len(todos_coord) >= 2:
        var_r = sum((p[0] - media_r) ** 2 for p in todos_coord) / len(todos_coord)
        var_c = sum((p[1] - media_c) ** 2 for p in todos_coord) / len(todos_coord)
        desvio_r = math.sqrt(var_r)
        desvio_c = math.sqrt(var_c)
    else:
        desvio_r = 0.0
        desvio_c = 0.0
    diag = math.hypot(max(lay.rows - 1, 0), max(lay.cols - 1, 0))
    indice = int(round(min(100.0, (media / diag) * 100))) if todos_coord and diag else 0

    tem_isolado = False
    media_iso = None
    outras_linhas: List[int] = []
    if lay.isolado is not None:
        iso = [p for p in pontos if p[0] == lay.isolado]
        outras = [p for p in pontos if p[0] != lay.isolado]
        tem_isolado = bool(iso)
        if iso and outras:
            dist_iso = [_dist(iso[0][1], p[1]) for p in outras]
            media_iso = sum(dist_iso) / len(dist_iso)
            outras_linhas = [
                sum(1 for _lab, (r, _c) in outras if r == i)
                for i in range(len(lay.volante))
                if not lay.linha_isolada(i)
            ]

    return {
        "linhas": linhas,
        "linhas_fmt": " - ".join(str(x) for x in linhas),
        "tem_31": tem_isolado,
        "celulas": [f"{r},{c}" for _lab, (r, c) in pontos],
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
        "sequencias": _sequencias_horizontais(pontos, lay),
        "diagonais": _diagonais(pontos, lay),
        "distancias": {
            "media": round(media, 2),
            "maior": round(maior, 2),
            "par_maior": par_maior,
        },
        "centro": {
            "linha": round(media_r, 2),
            "coluna": round(media_c, 2),
            "rotulo": _rotulo_centro(media_r, media_c, lay),
        },
        "analise_31": {
            "presente": tem_isolado,
            "outras_linhas": outras_linhas,
            "distancia_media": None if media_iso is None else round(media_iso, 2),
        },
    }


def analisar_geometria(
    linhas: Sequence[Dict[str, Any]],
    modality_key: str = "diadesorte",
) -> Dict[str, Any]:
    """Um registro por concurso já carregado em Gaps/Régua, mais o resumo da janela."""
    layout = layout_de(modality_key)
    por_concurso: Dict[str, Dict[str, Any]] = {}
    padroes: Counter = Counter()
    com_isolado = 0
    for row in linhas or []:
        if layout.posicional:
            dezenas = list(row.get("dezenas_sorteio") or row.get("dezenas") or [])
        else:
            dezenas = list(row.get("dezenas_classificado") or row.get("dezenas") or [])
        ind = indicadores_de(dezenas, layout)
        concurso = row.get("concurso")
        por_concurso[str(concurso)] = ind
        padroes[ind["linhas_fmt"]] += 1
        if ind["tem_31"]:
            com_isolado += 1
    total = len(por_concurso)
    return {
        "sucesso": True,
        "sessao": "geometria",
        "isolado": layout.isolado,
        "posicional": layout.posicional,
        "rows": layout.rows,
        "cols": layout.cols,
        "volante": [list(row) for row in layout.volante],
        "por_concurso": por_concurso,
        "historico": {
            "total": total,
            "com_31": com_isolado,
            "sem_31": max(0, total - com_isolado),
            "padroes_linha": [
                {"padrao": padrao, "frequencia": int(qtd)}
                for padrao, qtd in padroes.most_common(8)
            ],
        },
    }
