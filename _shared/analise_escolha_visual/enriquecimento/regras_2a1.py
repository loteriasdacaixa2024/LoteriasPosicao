# -*- coding: utf-8 -*-
"""Regras da análise 2A1. Não altera os conjuntos da seção 2A."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from analise_escolha_visual.enriquecimento.motor import conjuntos_concurso


def _ints(nums: Optional[Iterable[Any]]) -> List[int]:
    out: List[int] = []
    for n in nums or []:
        try:
            out.append(int(n))
        except (TypeError, ValueError):
            continue
    return out


def _grupos(det: Dict[str, Any], chave: str) -> List[List[int]]:
    bloco = ((det.get("basicos") or {}).get(chave) or {})
    detalhe = bloco.get("detalhe") or {}
    grupos = detalhe.get("grupos") or []
    norm: List[List[int]] = []
    for g in grupos:
        if isinstance(g, dict):
            nums = _ints(g.get("nums") or [])
            if len(nums) >= 2:
                norm.append(nums)
        else:
            nums = _ints(g)
            if len(nums) >= 2:
                norm.append(nums)
    return norm


def _diagonais(det: Dict[str, Any]) -> List[Dict[str, Any]]:
    bloco = ((det.get("basicos") or {}).get("diagonais") or {})
    detalhe = bloco.get("detalhe") or {}
    out: List[Dict[str, Any]] = []
    for g in detalhe.get("grupos") or []:
        if not isinstance(g, dict):
            nums = _ints(g)
            if len(nums) >= 2:
                out.append({"dir": "down", "dir_sym": "↘", "nums": nums})
            continue
        nums = _ints(g.get("nums") or [])
        if len(nums) < 2:
            continue
        direc = str(g.get("dir") or "down")
        out.append({
            "dir": direc,
            "dir_sym": g.get("dir_sym") or ("↘" if direc == "down" else "↗"),
            "nums": nums,
        })
    return out


def _detalhe(nums: Sequence[int], *, dmin: int, dmax: int, cols: int) -> Dict[str, Any]:
    return conjuntos_concurso(
        list(nums),
        None,
        com_cruzamentos=False,
        com_diagonais=True,
        dmin=int(dmin),
        dmax=int(dmax),
        cols=int(cols),
    )


def montar_linha_2a1(
    atual: Sequence[int],
    anterior: Optional[Sequence[int]],
    *,
    dmin: int = 1,
    dmax: int = 31,
    cols: int = 10,
) -> Dict[str, Any]:
    """Uma linha da tabela 2A1, sempre em relação ao concurso imediatamente anterior."""
    agora = _ints(atual)
    ant = _ints(anterior)
    ant_set = set(ant)
    agora_set = set(agora)
    # O que saiu no anterior e o que a 2a mostra neste concurso ficam de fora.
    pares = [
        n for n in range(int(dmin), int(dmax) + 1)
        if n % 2 == 0 and n not in ant_set and n not in agora_set
    ]
    impares = [
        n for n in range(int(dmin), int(dmax) + 1)
        if n % 2 != 0 and n not in ant_set and n not in agora_set
    ]
    repetidos = sorted(n for n in agora if n in ant_set)
    seqs: List[List[int]] = []
    finais: List[List[int]] = []
    diags: List[Dict[str, Any]] = []
    if ant:
        det = _detalhe(ant, dmin=dmin, dmax=dmax, cols=cols)
        seqs = _grupos(det, "sequencias")
        finais = _grupos(det, "finais")
        diags = _diagonais(det)
    return {
        "pares": pares,
        "impares": impares,
        "repetidos": repetidos,
        "sequencias": seqs,
        "finais": finais,
        "diagonais": diags,
    }


def montar_restricoes(
    ultimo: Sequence[int],
    penultimo: Optional[Sequence[int]] = None,
    *,
    dmin: int = 1,
    dmax: int = 31,
    cols: int = 10,
) -> Dict[str, Any]:
    """Restrições da próxima aposta. `ultimo` é o concurso imediatamente anterior."""
    base = montar_linha_2a1([], ultimo, dmin=dmin, dmax=dmax, cols=cols)
    ult = _ints(ultimo)
    ant = set(_ints(penultimo))
    banidos = sorted(n for n in ult if n in ant)
    ban_set = set(banidos)
    pode = sorted(n for n in ult if n not in ban_set)
    det = _detalhe(ult, dmin=dmin, dmax=dmax, cols=cols) if ult else {}
    return {
        "ultimo": ult,
        "pares_disponiveis": base["pares"],
        "impares_disponiveis": base["impares"],
        "repetidos_proibidos": banidos,
        "pode_repetir": pode,
        "sequencias_proibidas": _grupos(det, "sequencias") if det else [],
        "finais_proibidos": _grupos(det, "finais") if det else [],
        "diagonais_proibidas": _diagonais(det) if det else [],
    }


def _seq_maximas(nums: Sequence[int]) -> List[Tuple[int, ...]]:
    ordered = sorted(set(_ints(nums)))
    grupos: List[Tuple[int, ...]] = []
    i = 0
    while i < len(ordered):
        if i < len(ordered) - 1 and ordered[i + 1] - ordered[i] == 1:
            g = [ordered[i]]
            while i < len(ordered) - 1 and ordered[i + 1] - ordered[i] == 1:
                i += 1
                g.append(ordered[i])
            grupos.append(tuple(g))
        i += 1
    return grupos


def _finais_maximos(nums: Sequence[int]) -> List[Tuple[int, ...]]:
    by: Dict[int, List[int]] = {}
    for n in _ints(nums):
        by.setdefault(n % 10, []).append(n)
    return [tuple(sorted(g)) for g in by.values() if len(g) > 1]


def _chave_diag(item: Dict[str, Any]) -> Tuple[str, Tuple[int, ...]]:
    return (str(item.get("dir") or "down"), tuple(_ints(item.get("nums") or [])))


def viola_restricoes(
    dezenas: Sequence[int],
    restr: Dict[str, Any],
    *,
    dmin: int = 1,
    dmax: int = 31,
    cols: int = 10,
) -> Optional[str]:
    """Motivo da rejeição, ou None quando a aposta pode seguir."""
    nums = _ints(dezenas)
    ban = set(_ints(restr.get("repetidos_proibidos")))
    achou = sorted(n for n in nums if n in ban)
    if achou:
        return "usa repetido proibido " + " ".join(f"{n:02d}" for n in achou)

    proib_seq = {tuple(_ints(g)) for g in (restr.get("sequencias_proibidas") or [])}
    for g in _seq_maximas(nums):
        if g in proib_seq:
            return "repete a sequência " + "-".join(f"{n:02d}" for n in g)

    proib_fin = {tuple(_ints(g)) for g in (restr.get("finais_proibidos") or [])}
    for g in _finais_maximos(nums):
        if g in proib_fin:
            return "repete o final " + ",".join(f"{n:02d}" for n in g)

    proib_diag = {_chave_diag(g) for g in (restr.get("diagonais_proibidas") or []) if isinstance(g, dict)}
    if proib_diag:
        det = _detalhe(nums, dmin=dmin, dmax=dmax, cols=cols)
        for g in _diagonais(det):
            if _chave_diag(g) in proib_diag:
                sym = g.get("dir_sym") or "↘"
                return f"repete a diagonal {sym} " + "-".join(f"{n:02d}" for n in g["nums"])
    return None


def faixa_repetidos(modo: str) -> Tuple[int, int, bool]:
    """(mínimo, máximo, pode cair para zero se a faixa 1–2 não fechar)."""
    txt = str(modo or "1-2").strip().lower().replace(" ", "")
    if txt in ("0", "nenhum"):
        return 0, 0, False
    if txt in ("1", "um"):
        return 1, 1, False
    if txt in ("2", "dois"):
        return 2, 2, False
    return 1, 2, True
