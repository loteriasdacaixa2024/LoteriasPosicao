# -*- coding: utf-8 -*-
"""Restrições preservadas durante swaps — perfil estatístico por aposta."""
from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

from geradores_elite.comportamento.specs import SPECS

# Modo restrito: preserva distribuição B/M/A e pares/ímpares por aposta
CHAVES_RESTRITO = frozenset({"baixas", "medias", "altas", "pares", "impares"})


def _faixa_limites(universo: int) -> Dict[str, Tuple[int, int]]:
    if universo <= 31:
        return {"baixas": (1, 10), "medias": (11, 20), "altas": (21, universo)}
    t1 = universo // 3
    t2 = 2 * universo // 3
    return {"baixas": (1, t1), "medias": (t1 + 1, t2), "altas": (t2 + 1, universo)}


def perfil_aposta(dezenas: List[int], modality_key: str) -> Dict[str, int]:
    sp = SPECS[modality_key]
    dz = sorted(set(int(d) for d in dezenas))
    faixas = _faixa_limites(sp.universo)
    b, m, a = faixas["baixas"], faixas["medias"], faixas["altas"]

    pares = sum(1 for d in dz if d % 2 == 0)
    impares = len(dz) - pares
    primos = sum(1 for d in dz if d in sp.primos)
    moldura = sum(1 for d in dz if d in sp.moldura)
    m3 = sum(1 for d in dz if d in sp.multiplos_3)
    fb = sum(1 for d in dz if d in sp.fibonacci)

    return {
        "baixas": sum(1 for d in dz if b[0] <= d <= b[1]),
        "medias": sum(1 for d in dz if m[0] <= d <= m[1]),
        "altas": sum(1 for d in dz if a[0] <= d <= a[1]),
        "pares": pares,
        "impares": impares,
        "primos": primos,
        "moldura": moldura,
        "m3": m3,
        "fb": fb,
    }


def perfil_compativel(dezenas: List[int], perfil_alvo: Dict[str, int], modality_key: str) -> bool:
    atual = perfil_aposta(dezenas, modality_key)
    for chave, val in perfil_alvo.items():
        if atual.get(chave, 0) != val:
            return False
    return True


def perfil_compativel_restrito(dezenas: List[int], perfil_alvo: Dict[str, int], modality_key: str) -> bool:
    atual = perfil_aposta(dezenas, modality_key)
    for chave in CHAVES_RESTRITO:
        if atual.get(chave, 0) != perfil_alvo.get(chave, 0):
            return False
    return True


def _faixa_dezena(d: int, universo: int) -> str:
    faixas = _faixa_limites(universo)
    for nome, (lo, hi) in faixas.items():
        if lo <= d <= hi:
            return nome
    return "altas"


def swap_compativel_faixa_paridade(di: int, dj: int, universo: int) -> bool:
    """Troca só faz sentido se mesma faixa e mesma paridade (preserva B/M/A e PA/IM)."""
    if di == dj:
        return False
    if _faixa_dezena(di, universo) != _faixa_dezena(dj, universo):
        return False
    if (di % 2) != (dj % 2):
        return False
    return True


def apostas_unicas(apostas: List[List[int]]) -> bool:
    for dz in apostas:
        if len(dz) != len(set(dz)):
            return False
    return True


def pool_multiset(apostas: List[List[int]]) -> Dict[int, int]:
    out: Dict[int, int] = {}
    for dz in apostas:
        for d in dz:
            out[int(d)] = out.get(int(d), 0) + 1
    return out


def pool_preservado(original: List[List[int]], novo: List[List[int]]) -> bool:
    return pool_multiset(original) == pool_multiset(novo)


def pool_cobertura(apostas: List[List[int]]) -> Set[int]:
    out: Set[int] = set()
    for dz in apostas:
        out.update(int(d) for d in dz)
    return out


def penalidade_perfil(
    dezenas: List[int],
    perfil_alvo: Dict[str, int],
    modality_key: str,
) -> float:
    atual = perfil_aposta(dezenas, modality_key)
    pen = 0.0
    for chave, val in perfil_alvo.items():
        diff = abs(atual.get(chave, 0) - val)
        peso = 2.0 if chave in ("baixas", "medias", "altas", "pares", "impares") else 1.0
        pen += diff * peso
    return pen


def swap_valido_restrito(
    apostas: List[List[int]],
    i: int,
    j: int,
    pos_i: int,
    pos_j: int,
    perfis: List[Dict[str, int]],
    modality_key: str,
) -> bool:
    if i == j:
        return False
    ai = list(apostas[i])
    aj = list(apostas[j])
    di, dj = ai[pos_i], aj[pos_j]
    if di == dj:
        return False
    ai[pos_i], aj[pos_j] = dj, di
    ai.sort()
    aj.sort()
    if not perfil_compativel_restrito(ai, perfis[i], modality_key):
        return False
    if not perfil_compativel_restrito(aj, perfis[j], modality_key):
        return False
    return True


def aplicar_swap(apostas: List[List[int]], i: int, j: int, pos_i: int, pos_j: int) -> List[List[int]]:
    novo = [list(a) for a in apostas]
    di, dj = novo[i][pos_i], novo[j][pos_j]
    novo[i][pos_i] = dj
    novo[j][pos_j] = di
    novo[i].sort()
    novo[j].sort()
    return novo
