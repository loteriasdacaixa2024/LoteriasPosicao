# -*- coding: utf-8 -*-
"""Faixas de repetição volante por modalidade — alinhadas à quantidade sorteada."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

# (chave, rótulo, mínimo, máximo) — contagem de dezenas repetidas entre concursos seguidos
Bucket = Tuple[str, str, int, int]

# Quina, Mega, Dupla, +Milionária (5–6 dezenas sorteadas)
_FAIXAS_5_6: List[Bucket] = [
    ("0", "0 repetidas", 0, 0),
    ("1_2", "1–2 repetidas", 1, 2),
    ("3_4", "3–4 repetidas", 3, 4),
    ("5_mais", "5+ repetidas", 5, 99),
]

_FAIXAS_6: List[Bucket] = [
    ("0", "0 repetidas", 0, 0),
    ("1_2", "1–2 repetidas", 1, 2),
    ("3_4", "3–4 repetidas", 3, 4),
    ("5_6", "5–6 repetidas", 5, 6),
]

_FAIXAS_7: List[Bucket] = [
    ("0", "0 repetidas", 0, 0),
    ("1_2", "1–2 repetidas", 1, 2),
    ("3_4", "3–4 repetidas", 3, 4),
    ("5_7", "5–7 repetidas", 5, 7),
]

_FAIXAS_10: List[Bucket] = [
    ("0_2", "0–2 repetidas", 0, 2),
    ("3_5", "3–5 repetidas", 3, 5),
    ("6_8", "6–8 repetidas", 6, 8),
    ("9_mais", "9+ repetidas", 9, 99),
]

_FAIXAS_15: List[Bucket] = [
    ("0_4", "0–4 repetidas", 0, 4),
    ("5_7", "5–7 repetidas", 5, 7),
    ("8_10", "8–10 repetidas", 8, 10),
    ("11_mais", "11+ repetidas", 11, 99),
]

_FAIXAS_20: List[Bucket] = [
    ("0_6", "0–6 repetidas", 0, 6),
    ("7_12", "7–12 repetidas", 7, 12),
    ("13_17", "13–17 repetidas", 13, 17),
    ("18_mais", "18+ repetidas", 18, 99),
]

MODALITY_FAIXAS: Dict[str, List[Bucket]] = {
    "quina": _FAIXAS_5_6,
    "megasena": _FAIXAS_6,
    "duplasena": _FAIXAS_6,
    "maismilionaria": _FAIXAS_6,
    "diadesorte": _FAIXAS_7,
    "timemania": _FAIXAS_10,
    "lotomania": _FAIXAS_20,
    "lotofacil": _FAIXAS_15,
}

# Faixas com repetição “alta” — usadas nas regras automáticas
HIGH_REP_KEYS: Dict[str, Tuple[str, ...]] = {
    "quina": ("3_4", "5_mais"),
    "megasena": ("3_4", "5_6"),
    "duplasena": ("3_4", "5_6"),
    "maismilionaria": ("3_4", "5_6"),
    "diadesorte": ("3_4", "5_7"),
    "timemania": ("6_8", "9_mais"),
    "lotomania": ("13_17", "18_mais"),
    "lotofacil": ("8_10", "11_mais"),
}


def get_faixas_buckets(modality_key: str) -> List[Bucket]:
    if modality_key in MODALITY_FAIXAS:
        return MODALITY_FAIXAS[modality_key]
    try:
        from analise_repeticao.repeticao_config import REPETICAO_PARAMS

        sorteadas = int(REPETICAO_PARAMS[modality_key]["sorteadas"])
    except (KeyError, ValueError, TypeError):
        return _FAIXAS_5_6
    if sorteadas <= 5:
        return _FAIXAS_5_6
    if sorteadas <= 6:
        return _FAIXAS_6
    if sorteadas <= 7:
        return _FAIXAS_7
    if sorteadas <= 10:
        return _FAIXAS_10
    if sorteadas <= 15:
        return _FAIXAS_15
    return _FAIXAS_20


def classificar_repeticao(n: int, buckets: List[Bucket]) -> str:
    for chave, _label, lo, hi in buckets:
        if lo <= n <= hi:
            return chave
    return buckets[-1][0] if buckets else "outros"


def contar_faixas_volante(svc: Any, modality_key: str) -> Dict[str, int]:
    """Conta pares consecutivos por faixa — mesma lógica do volante em RepeticaoConcursosService."""
    buckets = get_faixas_buckets(modality_key)
    sorteios = svc._carregar_sorteios_asc()
    out: Dict[str, int] = {b[0]: 0 for b in buckets}
    for i in range(1, len(sorteios)):
        n = len(svc._set_dezenas(sorteios[i - 1]) & svc._set_dezenas(sorteios[i]))
        chave = classificar_repeticao(n, buckets)
        out[chave] = out.get(chave, 0) + 1
    return out


def tipos_sorteio_from_faixas(
    faixas: Dict[str, int],
    total_pares: int,
    modality_key: str,
    pct_fn,
) -> List[Dict[str, Any]]:
    buckets = get_faixas_buckets(modality_key)
    tipos = [
        {
            "chave": chave,
            "label": label,
            "vezes": int(faixas.get(chave, 0)),
            "pct": pct_fn(int(faixas.get(chave, 0)), total_pares),
        }
        for chave, label, _lo, _hi in buckets
    ]
    tipos.sort(key=lambda x: -x["vezes"])
    return tipos


def high_repeticao_keys(modality_key: str) -> Tuple[str, ...]:
    return HIGH_REP_KEYS.get(modality_key, ("3_4", "5_mais", "5_6", "5_7"))
