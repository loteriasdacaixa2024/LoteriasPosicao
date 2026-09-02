# -*- coding: utf-8 -*-
"""Classificações matemáticas e comportamentais — por modalidade."""
from __future__ import annotations

from collections import Counter
from functools import lru_cache
from math import isqrt
from typing import Any, Dict, FrozenSet, List, Optional, Tuple

from geradores_elite.comportamento.specs import SPECS

from analise_estudos.specs import get_estudos_config


def _primos_ate(n: int) -> FrozenSet[int]:
    if n < 2:
        return frozenset()
    sieve = [True] * (n + 1)
    sieve[0] = sieve[1] = False
    for i in range(2, isqrt(n) + 1):
        if sieve[i]:
            for j in range(i * i, n + 1, i):
                sieve[j] = False
    return frozenset(i for i, ok in enumerate(sieve) if ok)


def _fibonacci_ate(n: int, dmin: int = 1) -> FrozenSet[int]:
    out = set()
    a, b = 0, 1
    while a <= n:
        if a >= dmin:
            out.add(a)
        a, b = b, a + b
    return frozenset(out)


def _quadrados_ate(n: int, dmin: int = 1) -> FrozenSet[int]:
    return frozenset(i * i for i in range(isqrt(n) + 1) if dmin <= i * i <= n)


def _potencias(base: int, n: int, dmin: int = 1) -> FrozenSet[int]:
    out = set()
    v = 1
    while v <= n:
        if v >= dmin:
            out.add(v)
        if v > n // base:
            break
        v *= base
    return frozenset(out)


def _triangulares_ate(n: int, dmin: int = 1) -> FrozenSet[int]:
    out = set()
    i, t = 1, 1
    while t <= n:
        if t >= dmin:
            out.add(t)
        i += 1
        t = i * (i + 1) // 2
    return frozenset(out)


def _tercos(universo: range) -> Tuple[FrozenSet[int], FrozenSet[int], FrozenSet[int]]:
    nums = list(universo)
    if not nums:
        empty = frozenset()
        return empty, empty, empty
    n = len(nums)
    a = n // 3
    b = (2 * n) // 3
    return frozenset(nums[:a]), frozenset(nums[a:b]), frozenset(nums[b:])


def _quadrante_factory(dmin: int, cols: int, rows: int):
    half_r = max(1, rows // 2)
    half_c = max(1, cols // 2)

    def _quadrante(n: int) -> int:
        idx = n - dmin
        if cols <= 0:
            return 1
        row, col = idx // cols, idx % cols
        q_row = 0 if row < half_r else 1
        q_col = 0 if col < half_c else 1
        return q_row * 2 + q_col + 1

    return _quadrante


def _contar_sequencias(dezenas: List[int]) -> int:
    ordenadas = sorted(dezenas)
    grupos = 0
    i = 0
    while i < len(ordenadas):
        j = i
        while j + 1 < len(ordenadas) and ordenadas[j + 1] - ordenadas[j] == 1:
            j += 1
        if j > i:
            grupos += 1
        i = j + 1
    return grupos


def _contar_finais_iguais(dezenas: List[int]) -> int:
    finais: Counter[int] = Counter(d % 10 for d in dezenas)
    return sum(1 for d in dezenas if finais[d % 10] >= 2)


@lru_cache(maxsize=16)
def _contexto(modality_key: str) -> Dict[str, Any]:
    cfg = get_estudos_config(modality_key)
    dmin = int(cfg["dezena_min"])
    dmax = int(cfg["dezena_max"])
    universo = range(dmin, dmax + 1)
    cols = int(cfg.get("volante_cols") or 10)
    rows = int(cfg.get("volante_rows") or max(1, (dmax - dmin + 1 + cols - 1) // cols))
    extra_mes = bool(cfg.get("extra_mes"))

    try:
        spec = SPECS.get(modality_key)
        if spec is None:
            raise KeyError(modality_key)
        primos = frozenset(x for x in spec.primos if dmin <= x <= dmax)
        fibonacci = frozenset(x for x in spec.fibonacci if dmin <= x <= dmax)
        multiplos_3 = frozenset(x for x in spec.multiplos_3 if dmin <= x <= dmax)
        moldura = frozenset(x for x in spec.moldura if dmin <= x <= dmax)
    except Exception:
        primos = frozenset(x for x in _primos_ate(dmax) if x >= dmin)
        fibonacci = _fibonacci_ate(dmax, dmin)
        multiplos_3 = frozenset(d for d in universo if d % 3 == 0)
        moldura = frozenset()

    bx, md, al = _tercos(universo)
    gemeos = frozenset(d for d in universo if d >= 11 and d % 11 == 0 and d // 11 < 10)
    centro = frozenset(d for d in universo if d not in moldura) if moldura else frozenset(universo)

    conjuntos: Dict[str, Tuple[str, FrozenSet[int]]] = {
        "PA": ("Pares", frozenset(d for d in universo if d % 2 == 0)),
        "IM": ("Ímpares", frozenset(d for d in universo if d % 2 != 0)),
        "PR": ("Primos", primos),
        "FB": ("Fibonacci", fibonacci),
        "M3": ("Múltiplos de 3", multiplos_3),
        "MO": ("Moldura", moldura),
        "GE": ("Gêmeos", gemeos),
        "M5": ("Múltiplos de 5", frozenset(d for d in universo if d % 5 == 0)),
        "QP": ("Quadrados perfeitos", _quadrados_ate(dmax, dmin)),
        "P2": ("Potências de 2", _potencias(2, dmax, dmin)),
        "P3": ("Potências de 3", _potencias(3, dmax, dmin)),
        "TR": ("Triangulares", _triangulares_ate(dmax, dmin)),
        "BX": (f"Baixos ({dmin:02d}–{max(bx) if bx else dmin:02d})", bx),
        "MD": (
            f"Médios ({min(md) if md else dmin:02d}–{max(md) if md else dmax:02d})",
            md,
        ),
        "AL": (f"Altos ({min(al) if al else dmax:02d}–{dmax:02d})", al),
        "CT": ("Centro", centro),
    }

    metricas: Dict[str, str] = {
        "SQ": "Sequências",
        "RT": "Repetidas",
        "CF": "Finais iguais",
        "ES": "Espelhados",
        "AM": "Amplitude",
        "SD": "Soma dezenas",
    }
    if extra_mes:
        metricas["MS"] = "Mês da Sorte"

    indicadores = (
        "PA", "IM", "PR", "FB", "M3", "MO", "GE", "M5", "QP", "P2", "P3", "TR",
        "BX", "MD", "AL", "CT", "SQ", "RT", "CF", "ES", "AM", "SD",
    )
    if extra_mes:
        indicadores = indicadores + ("MS",)
    indicadores = indicadores + ("Q1", "Q2", "Q3", "Q4")

    labels: Dict[str, str] = {cod: nome for cod, (nome, _) in conjuntos.items()}
    labels.update(metricas)
    labels.update({q: f"Quadrante {q[1]}" for q in ("Q1", "Q2", "Q3", "Q4")})

    return {
        "dmin": dmin,
        "dmax": dmax,
        "espelho_base": dmin + dmax,
        "quadrante": _quadrante_factory(dmin, cols, rows),
        "conjuntos": conjuntos,
        "metricas": metricas,
        "indicadores": indicadores,
        "labels": labels,
        "extra_mes": extra_mes,
    }


def _contar_espelhados(dezenas: List[int], espelho_base: int) -> int:
    s = set(dezenas)
    pares = 0
    for d in dezenas:
        esp = espelho_base - d
        if esp != d and esp in s and d < esp:
            pares += 1
    return pares


def listar_classificacoes_ui(modality_key: str = "diadesorte") -> List[Dict[str, Any]]:
    ctx = _contexto(modality_key)
    out: List[Dict[str, Any]] = []
    for cod in ctx["indicadores"]:
        if cod in ctx["conjuntos"]:
            nome, nums = ctx["conjuntos"][cod]
            out.append({
                "codigo": cod,
                "label": nome,
                "numeros": sorted(nums),
                "tipo": "conjunto",
            })
        elif cod in ("Q1", "Q2", "Q3", "Q4"):
            out.append({
                "codigo": cod,
                "label": ctx["labels"][cod],
                "tipo": "quadrante",
            })
        else:
            out.append({
                "codigo": cod,
                "label": ctx["labels"].get(cod, cod),
                "tipo": "metrica",
            })
    return out


def indicadores_aba3(modality_key: str = "diadesorte") -> Tuple[str, ...]:
    return tuple(_contexto(modality_key)["indicadores"])


def indicador_labels(modality_key: str = "diadesorte") -> Dict[str, str]:
    return dict(_contexto(modality_key)["labels"])


def calcular_classificacoes_concurso(
    dezenas: List[int],
    prev_dezenas: Optional[List[int]] = None,
    mes_num: Optional[int] = None,
    modality_key: str = "diadesorte",
) -> Dict[str, int]:
    ctx = _contexto(modality_key)
    dz = [int(d) for d in dezenas]
    prev = [int(d) for d in (prev_dezenas or [])]
    out: Dict[str, int] = {}

    for cod, (_, conjunto) in ctx["conjuntos"].items():
        out[cod] = sum(1 for d in dz if d in conjunto)

    out["SQ"] = _contar_sequencias(dz)
    out["RT"] = len(set(dz) & set(prev)) if prev else 0
    out["CF"] = _contar_finais_iguais(dz)
    out["ES"] = _contar_espelhados(dz, ctx["espelho_base"])
    out["AM"] = max(dz) - min(dz) if dz else 0
    out["SD"] = sum(dz)
    if ctx["extra_mes"]:
        out["MS"] = int(mes_num) if mes_num else 0

    qtd_q = {1: 0, 2: 0, 3: 0, 4: 0}
    quadrante = ctx["quadrante"]
    for d in dz:
        qtd_q[quadrante(d)] += 1
    for i, q in enumerate(("Q1", "Q2", "Q3", "Q4"), start=1):
        out[q] = qtd_q[i]

    return out


def intersecoes_destaque(modality_key: str = "diadesorte") -> List[Dict[str, Any]]:
    conjuntos = _contexto(modality_key)["conjuntos"]
    pares = [
        ("PR", "FB", "Primos ∩ Fibonacci"),
        ("PA", "FB", "Pares ∩ Fibonacci"),
        ("TR", "FB", "Triangulares ∩ Fibonacci"),
        ("QP", "FB", "Quadrados ∩ Fibonacci"),
        ("GE", "PA", "Gêmeos (pares)"),
    ]
    out = []
    for a, b, titulo in pares:
        if a in conjuntos and b in conjuntos:
            inter = sorted(conjuntos[a][1] & conjuntos[b][1])
            if inter:
                out.append({"titulo": titulo, "numeros": inter})
    return out


# Compatibilidade com imports legados (Dia de Sorte)
INDICADORES_ABA3 = indicadores_aba3("diadesorte")
INDICADOR_LABELS = indicador_labels("diadesorte")
CONJUNTOS = _contexto("diadesorte")["conjuntos"]
METRICAS = _contexto("diadesorte")["metricas"]
QUADRANTES = ("Q1", "Q2", "Q3", "Q4")
