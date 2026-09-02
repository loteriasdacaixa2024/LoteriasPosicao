# -*- coding: utf-8 -*-
"""
Padronização Universal de Linhas (blocos de 10).

Padrão oficial:
  L1  01–10   L2  11–20  …  L10 91–100

Regras:
  - 00 (Lotomania / Super Sete) NUNCA é excluído → L1.
  - Cada modalidade recebe apenas as linhas que intersectam seu universo.
  - Faixas parciais (ex.: Dia L4={31}, Lotofácil L3={21–25}) são naturais.
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

# Faixas oficiais (início, fim) — referência documental; 00 tratado à parte.
LINHAS_OFICIAIS: Tuple[Tuple[str, int, int], ...] = (
    ("L1", 1, 10),
    ("L2", 11, 20),
    ("L3", 21, 30),
    ("L4", 31, 40),
    ("L5", 41, 50),
    ("L6", 51, 60),
    ("L7", 61, 70),
    ("L8", 71, 80),
    ("L9", 81, 90),
    ("L10", 91, 100),
)


def mapa_oficial() -> List[Dict[str, Any]]:
    return [
        {"id": lid, "inicio": lo, "fim": hi, "label": f"{lo:02d}–{hi:02d}"}
        for lid, lo, hi in LINHAS_OFICIAIS
    ]


def linha_da_dezena(valor: int) -> str:
    """
    Classifica uma dezena na linha oficial.
    0 → L1 (obrigatório). n>=1 → ((n-1)//10)+1, limitado a L10.
    """
    n = int(valor)
    if n <= 0:
        return "L1"
    idx = ((n - 1) // 10) + 1
    if idx < 1:
        idx = 1
    if idx > 10:
        idx = 10
    return f"L{idx}"


def _universo(modality_key: str) -> Tuple[int, int]:
    from analise_estudos.specs import get_estudos_config

    cfg = get_estudos_config(modality_key)
    return int(cfg["dezena_min"]), int(cfg["dezena_max"])


def dezenas_da_linha(
    linha_id: str,
    dezena_min: int,
    dezena_max: int,
) -> List[int]:
    """Dezenas do universo que pertencem à linha."""
    out: List[int] = []
    for n in range(int(dezena_min), int(dezena_max) + 1):
        if linha_da_dezena(n) == linha_id:
            out.append(n)
    return out


def linhas_para_modalidade(modality_key: str) -> Dict[str, Any]:
    """
    Retorna apenas as linhas necessárias para a modalidade,
    com as dezenas efetivas de cada bloco.
    """
    dmin, dmax = _universo(modality_key)
    from analise_estudos.specs import get_estudos_config

    cfg = get_estudos_config(modality_key)
    linhas: List[Dict[str, Any]] = []
    for lid, lo, hi in LINHAS_OFICIAIS:
        dezenas = dezenas_da_linha(lid, dmin, dmax)
        if not dezenas:
            continue
        linhas.append({
            "id": lid,
            "inicio_oficial": lo,
            "fim_oficial": hi,
            "dezenas": dezenas,
            "qtd": len(dezenas),
            "label": _label_faixa(dezenas),
        })
    return {
        "modality_key": modality_key,
        "modality_nome": cfg.get("nome", modality_key),
        "dezena_min": dmin,
        "dezena_max": dmax,
        "pad_width": int(cfg.get("pad_width") or 2),
        "linhas": linhas,
        "qtd_linhas": len(linhas),
        "mapa_oficial": mapa_oficial(),
    }


def _label_faixa(dezenas: Sequence[int]) -> str:
    if not dezenas:
        return "—"
    a, b = int(dezenas[0]), int(dezenas[-1])
    if a == b:
        return f"{a:02d}"
    return f"{a:02d}–{b:02d}"


def classificar_dezenas(dezenas: Sequence[int]) -> Dict[str, Any]:
    """Classifica uma lista de dezenas: por linha e ordem."""
    por_linha: Dict[str, List[int]] = {}
    detalhe: List[Dict[str, Any]] = []
    for n in dezenas:
        lid = linha_da_dezena(int(n))
        por_linha.setdefault(lid, []).append(int(n))
        detalhe.append({"dezena": int(n), "linha": lid})
    linhas_presentes = sorted(
        por_linha.keys(),
        key=lambda x: int(x[1:]) if x[1:].isdigit() else 0,
    )
    return {
        "por_linha": {k: sorted(v) for k, v in por_linha.items()},
        "linhas_presentes": linhas_presentes,
        "qtd_linhas": len(linhas_presentes),
        "detalhe": detalhe,
    }
