# -*- coding: utf-8 -*-
"""Soma e conjunto de dígitos — reutiliza posicao_analise."""
from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Any, Dict, List, Set, Tuple

from posicao_analise.core import (
    analisar_concurso_geral,
    extrair_digitos,
    soma_digitos,
)
from posicao_analise.specs import get_posicao_spec

_DIGITOS = [str(i) for i in range(10)]


def soma_digitos_dezena(valor: int, pad_width: int = 2) -> int:
    return soma_digitos(valor, pad_width)


def digitos_de_dezena(valor: int, pad_width: int = 2) -> List[str]:
    return extrair_digitos(valor, pad_width)


def mapa_soma_por_dezena(
    dezena_min: int = 1,
    dezena_max: int = 31,
    pad_width: int = 2,
) -> List[Dict[str, Any]]:
    """Tabela fixa: cada dezena do universo → soma dos seus dígitos."""
    fmt = (lambda n: f"{n:02d}") if pad_width >= 2 else str
    return [
        {
            "dezena": d,
            "dezena_fmt": fmt(d),
            "soma_digitos": soma_digitos(d, pad_width),
            "digitos": extrair_digitos(d, pad_width),
        }
        for d in range(dezena_min, dezena_max + 1)
    ]


def analisar_digitos_concurso(
    dezenas_ordem: List[int],
    modality_key: str = "diadesorte",
) -> Dict[str, Any]:
    spec = get_posicao_spec(modality_key)
    geral = analisar_concurso_geral(dezenas_ordem, spec)
    somas_por_dezena = [
        {
            "dezena": int(d),
            "dezena_fmt": spec.fmt(int(d)),
            "digitos": extrair_digitos(int(d), spec.pad_width),
            "soma_digitos": soma_digitos(int(d), spec.pad_width),
        }
        for d in dezenas_ordem[: spec.num_posicoes]
    ]
    soma_total_digitos = sum(x["soma_digitos"] for x in somas_por_dezena)
    return {
        **geral,
        "somas_por_dezena": somas_por_dezena,
        "soma_total_digitos": soma_total_digitos,
        "media_soma_digitos": round(soma_total_digitos / len(somas_por_dezena), 2) if somas_por_dezena else 0,
    }


def calcular_coocorrencia_digitos(
    conjuntos_por_concurso: List[Set[str]],
) -> Tuple[List[List[int]], List[Dict[str, Any]]]:
    """
    Matriz 10×10 e top pares de dígitos que aparecem juntos no mesmo concurso.
    """
    mat = [[0 for _ in _DIGITOS] for _ in _DIGITOS]
    pares: Counter[Tuple[str, str]] = Counter()

    for conj in conjuntos_por_concurso:
        digs = sorted(conj, key=lambda x: int(x))
        for d in digs:
            mat[int(d)][int(d)] += 1
        for a, b in combinations(digs, 2):
            pares[(a, b)] += 1
            mat[int(a)][int(b)] += 1
            mat[int(b)][int(a)] += 1

    total = len(conjuntos_por_concurso)
    top = [
        {
            "par": f"{a}+{b}",
            "digito_a": a,
            "digito_b": b,
            "ocorrencias": n,
            "pct": round(n / total * 100, 1) if total else 0,
        }
        for (a, b), n in pares.most_common(20)
    ]
    return mat, top


def calcular_atraso_digitos(
    conjuntos_por_concurso: List[Set[str]],
) -> List[Dict[str, Any]]:
    """Atraso atual de cada dígito 0–9 (concursos desde última aparição)."""
    total = len(conjuntos_por_concurso)
    ultimo_idx: Dict[str, int] = {}
    for i, conj in enumerate(conjuntos_por_concurso):
        for d in conj:
            ultimo_idx[d] = i

    out = []
    for dig in _DIGITOS:
        if dig not in ultimo_idx:
            atraso = total
            ultimo = None
        else:
            atraso = total - 1 - ultimo_idx[dig]
            ultimo = ultimo_idx[dig]
        out.append({
            "digito": dig,
            "atraso": atraso,
            "ultimo_indice": ultimo,
        })
    out.sort(key=lambda x: -x["atraso"])
    return out


def sobreposicao_digitos_consecutivos(
    conjuntos_por_concurso: List[Set[str]],
) -> Dict[str, Any]:
    """Quantos dígitos se repetem entre concursos consecutivos."""
    overlaps: List[int] = []
    for i in range(1, len(conjuntos_por_concurso)):
        prev = conjuntos_por_concurso[i - 1]
        cur = conjuntos_por_concurso[i]
        overlaps.append(len(prev & cur))
    if not overlaps:
        return {"media": 0, "moda": 0, "max": 0, "serie": []}
    cnt = Counter(overlaps)
    moda, _ = cnt.most_common(1)[0]
    return {
        "media": round(sum(overlaps) / len(overlaps), 2),
        "moda": moda,
        "max": max(overlaps),
        "serie": overlaps[-30:],
    }

