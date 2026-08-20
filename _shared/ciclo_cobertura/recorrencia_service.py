# -*- coding: utf-8 -*-
"""Recorrência das Repetidas no Ciclo — janela dos últimos N concursos."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from .analise_service import AnaliseCicloCoberturaService
from .specs import get_ciclo_spec

JANELAS = (4, 5, 6, 8, 10)
JANELA_DEFAULT = 4


def _fmt(nums: List[int]) -> str:
    return " · ".join(f"{int(n):02d}" for n in nums) if nums else "—"


def _rotulo(freq: int, max_f: int) -> str:
    if freq <= 0:
        return "Ausente"
    if freq == 1:
        return "Baixa presença"
    if freq == 2:
        return "Repetida"
    if freq >= 3 and freq == max_f:
        return "Muito forte"
    return "Forte"


def analisar_recorrencia(
    modality_key: str,
    n: int = JANELA_DEFAULT,
) -> Dict[str, Any]:
    spec = get_ciclo_spec(modality_key)
    pedido = int(n or JANELA_DEFAULT)
    if pedido not in JANELAS:
        pedido = JANELA_DEFAULT

    ciclo = AnaliseCicloCoberturaService.obter_ciclo_atual(modality_key)
    if not ciclo:
        return {"ok": False, "erro": "Sem ciclo em andamento no banco."}

    detalhes = list(ciclo.get("detalhes_concursos") or [])
    detalhes.sort(key=lambda d: int(d.get("concurso") or 0), reverse=True)
    janela = detalhes[:pedido]
    if not janela:
        return {"ok": False, "erro": "Sem concursos na coluna Repetidas no Ciclo."}

    univ = list(range(int(spec.dezena_min), int(spec.dezena_max) + 1))
    freq: Counter = Counter()
    linhas: List[Dict[str, Any]] = []
    ocorrencias = 0
    for row in janela:
        reps = sorted(int(x) for x in (row.get("repetidas") or []))
        for d in reps:
            freq[d] += 1
            ocorrencias += 1
        linhas.append({
            "concurso": row.get("concurso"),
            "data": row.get("data") or "",
            "numero_ciclo": row.get("numero_ciclo"),
            "repetidas": reps,
        })

    max_f = max(freq.values()) if freq else 0
    tabela = []
    for d in univ:
        f = int(freq.get(d, 0))
        tabela.append({
            "dezena": d,
            "vezes": f,
            "rotulo": _rotulo(f, max_f),
        })

    def grupo(pred) -> List[int]:
        return [t["dezena"] for t in tabela if pred(t["vezes"])]

    ausentes = grupo(lambda f: f == 0)
    baixa = grupo(lambda f: f == 1)
    repetidas = grupo(lambda f: f == 2)
    fortes = grupo(lambda f: f >= 3 and f < max_f) if max_f >= 4 else []
    muito_fortes = grupo(lambda f: f >= 3 and f == max_f) if max_f >= 3 else []
    if max_f == 3:
        muito_fortes = grupo(lambda f: f == 3)
        fortes = []

    nucleo_forte = sorted(set(muito_fortes) | set(fortes))
    ranking = sorted(
        [t for t in tabela if t["vezes"] >= 2],
        key=lambda t: (-t["vezes"], t["dezena"]),
    )
    por_frequencia = []
    for v in range(max_f, -1, -1):
        nums = grupo(lambda f, vv=v: f == vv)
        if not nums:
            continue
        por_frequencia.append({
            "vezes": v,
            "dezenas": nums,
            "fmt": _fmt(nums),
            "rotulo": _rotulo(v, max_f) if v else "Ausente",
            "qtd": len(nums),
        })

    usadas = [t["dezena"] for t in tabela if t["vezes"] > 0]
    n_univ = len(univ)
    n_usadas = len(usadas)
    n_aus = len(ausentes)
    cobertura_pct = round(100.0 * n_usadas / n_univ, 1) if n_univ else 0.0
    ausentes_pct = round(100.0 * n_aus / n_univ, 1) if n_univ else 0.0

    top2 = ranking[:2]
    top2_ocor = sum(t["vezes"] for t in top2)
    top2_pct = round(100.0 * top2_ocor / ocorrencias, 1) if ocorrencias else 0.0
    lider = ranking[0] if ranking else None
    lider_pct = round(100.0 * lider["vezes"] / ocorrencias, 1) if lider and ocorrencias else 0.0

    faixas = []
    for nome, lo, hi in spec.faixas:
        nums = list(range(lo, hi + 1))
        pres = [d for d in nums if freq.get(d, 0) > 0]
        aus = [d for d in nums if freq.get(d, 0) == 0]
        faixas.append({
            "nome": nome,
            "label": f"{lo:02d}–{hi:02d}",
            "de": lo,
            "ate": hi,
            "tamanho": len(nums),
            "presentes": pres,
            "ausentes": aus,
            "qtd_presentes": len(pres),
            "qtd_ausentes": len(aus),
        })

    pendentes_ciclo = [int(x) for x in (ciclo.get("dezenas_pendentes") or [])]
    pool = sorted(set(ausentes) | set(baixa))
    pool_com_ciclo = sorted(set(pool) | set(pendentes_ciclo))

    concursos = [r["concurso"] for r in linhas]
    return {
        "ok": True,
        "fonte": "repetidas_no_ciclo",
        "janela": pedido,
        "janela_efetiva": len(linhas),
        "janelas": list(JANELAS),
        "concursos": concursos,
        "linhas": linhas,
        "ocorrencias": ocorrencias,
        "leitura": (
            f"Universo {spec.dezena_min:02d}–{spec.dezena_max:02d}: "
            f"{len(linhas)} linha(s) da coluna Repetidas no Ciclo "
            f"({ocorrencias} ocorrências)."
        ),
        "universo": n_univ,
        "dezena_min": spec.dezena_min,
        "dezena_max": spec.dezena_max,
        "tabela": tabela,
        "ranking": ranking,
        "por_frequencia": por_frequencia,
        "grupos": {
            "nucleo_forte": nucleo_forte,
            "muito_forte": muito_fortes,
            "forte": fortes,
            "repetido": repetidas,
            "baixa_presenca": baixa,
            "ausentes": ausentes,
        },
        "fmt": {
            "nucleo_forte": _fmt(nucleo_forte),
            "muito_forte": _fmt(muito_fortes),
            "forte": _fmt(fortes),
            "repetido": _fmt(repetidas),
            "baixa_presenca": _fmt(baixa),
            "ausentes": _fmt(ausentes),
            "pool": _fmt(pool),
        },
        "cobertura": {
            "usadas": n_usadas,
            "ausentes": n_aus,
            "pct_usadas": cobertura_pct,
            "pct_ausentes": ausentes_pct,
        },
        "destaques": {
            "lider": lider,
            "lider_pct": lider_pct,
            "top2": top2,
            "top2_ocor": top2_ocor,
            "top2_pct": top2_pct,
            "n_repetidas": len(ranking),
            "n_baixa": len(baixa),
            "n_ausentes": n_aus,
        },
        "faixas": faixas,
        "ciclo": {
            "numero": ciclo.get("numero_ciclo"),
            "percentual": ciclo.get("percentual_completo"),
            "pendentes": pendentes_ciclo,
            "fmt_pendentes": _fmt(pendentes_ciclo),
            "em_andamento": bool(ciclo.get("em_andamento")),
        },
        "pool": {
            "ausentes_x_baixa": pool,
            "com_faltantes_ciclo": pool_com_ciclo,
            "qtd_baixa_no_pool": len(baixa),
            "qtd_ausentes_no_pool": len(ausentes),
        },
    }
