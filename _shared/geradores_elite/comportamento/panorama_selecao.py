# -*- coding: utf-8 -*-
"""Panorama Top-3 — volante 16, seleção guiada e validação por rank."""
from __future__ import annotations

from itertools import combinations
from typing import Any, Dict, List, Optional, Set, Tuple

from geradores_elite.comportamento.panorama_top_geracao import (
    label_rank_escolhido,
    montar_alvos_por_rank,
    normalizar_rank_escolhido,
    score_minimo_panorama,
)
from geradores_elite.comportamento.specs import MESES_ABREV, MESES_NOME

POOL_MAX_PADRAO = 16


def _fmt_dez(n: int) -> str:
    return f"{int(n):02d}"


def listar_categorias_dezenas(
    dezena_range: range,
    cats: Dict[str, Set[int]],
    ultimo_dezenas: Optional[List[int]] = None,
) -> Dict[str, List[int]]:
    ultimo_set = set(ultimo_dezenas or [])
    universo = sorted(dezena_range)
    return {
        "par": sorted(cats.get("par") or []),
        "impar": sorted(cats.get("impar") or []),
        "primo": sorted(cats.get("primo") or []),
        "fibonacci": sorted(cats.get("fb") or []),
        "multiplos_3": sorted(cats.get("m3") or []),
        "moldura": sorted(cats.get("moldura") or []),
        "nao_primo": sorted(cats.get("nao_primo") or []),
        "ultimo_concurso": sorted(ultimo_set),
        "demais": sorted(set(universo) - ultimo_set),
    }


def validar_selecao_panorama(
    dezenas: List[int],
    k: int,
    alvos: Dict[str, int],
    indicadores_dezena: Tuple[str, ...],
    calc_ind_fn,
    ultimo_prev: Optional[List[int]] = None,
    extras: Optional[Dict[str, int]] = None,
    modo: str = "estrito",
) -> Dict[str, Any]:
    """Valida conjunto de dezenas contra alvos do rank (estrito ou relaxar ±1)."""
    modo = (modo or "estrito").strip().lower()
    relaxar = modo == "relaxar"
    dz = sorted({int(d) for d in (dezenas or [])})

    if len(dz) != k:
        return {
            "valido": False,
            "motivo": f"Selecione exatamente {k} dezenas (atual: {len(dz)}).",
            "dezenas": dz,
            "quantidade": len(dz),
            "quantidade_alvo": k,
        }

    ind = calc_ind_fn(dz, ultimo_prev, extras)
    ativos_dez = [c for c in indicadores_dezena if c in alvos]
    detalhes: List[Dict[str, Any]] = []
    acertos_exatos = 0
    acertos_relax = 0
    score = 0

    for cod in ativos_dez:
        alvo = int(alvos.get(cod, 0))
        atual = int(ind.get(cod, 0))
        diff = abs(atual - alvo)
        exato = diff == 0
        ok_relax = diff <= 1
        if exato:
            acertos_exatos += 1
            score += 10
        elif ok_relax:
            acertos_relax += 1
            score += 5
        detalhes.append({
            "codigo": cod,
            "alvo": alvo,
            "atual": atual,
            "diff": diff,
            "ok_estrito": exato,
            "ok_relaxar": ok_relax,
        })

    extras_det: List[Dict[str, Any]] = []
    for cod in ("MS", "TM", "T1", "T2"):
        if cod not in alvos:
            continue
        alvo = int(alvos[cod])
        atual = int(ind.get(cod, extras.get(cod) if extras else alvo))
        exato = atual == alvo
        extras_det.append({
            "codigo": cod,
            "alvo": alvo,
            "atual": atual,
            "ok_estrito": exato,
            "ok_relaxar": exato,
        })

    n_dez = len(ativos_dez) or 1
    score_min_estrito = score_minimo_panorama(n_dez, 1, "estrito")
    score_min_relax = score_minimo_panorama(n_dez, 1, "relaxar")
    valido_estrito = acertos_exatos == len(ativos_dez) and score >= score_min_estrito
    valido_relax = (acertos_exatos + acertos_relax) >= max(3, int(n_dez * 0.5)) and score >= score_min_relax
    valido = valido_relax if relaxar else valido_estrito

    return {
        "valido": valido,
        "modo": modo,
        "dezenas": dz,
        "texto": " ".join(_fmt_dez(d) for d in dz),
        "indicadores": ind,
        "detalhes": detalhes,
        "extras_detalhes": extras_det,
        "acertos_exatos": acertos_exatos,
        "acertos_relax": acertos_relax,
        "total_indicadores": len(ativos_dez),
        "score": score,
        "score_min_estrito": score_min_estrito,
        "score_min_relax": score_min_relax,
        "valido_estrito": valido_estrito,
        "valido_relaxar": valido_relax,
        "motivo": None if valido else (
            f"Indicadores: {acertos_exatos}/{len(ativos_dez)} exatos"
            + (f", {acertos_relax} próximos (±1)" if acertos_relax else "")
        ),
    }


def buscar_variacoes_pool(
    pool: List[int],
    k: int,
    alvos: Dict[str, int],
    indicadores_dezena: Tuple[str, ...],
    calc_ind_fn,
    ultimo_prev: Optional[List[int]] = None,
    extras: Optional[Dict[str, int]] = None,
    modo: str = "estrito",
    limite: int = 50,
    max_avaliar: int = 12000,
) -> List[List[int]]:
    """Lista combinações válidas de k dezenas dentro do pool (limitado)."""
    pool_u = sorted({int(d) for d in pool})
    if len(pool_u) < k:
        return []
    relaxar = (modo or "estrito").strip().lower() == "relaxar"
    out: List[List[int]] = []
    avaliados = 0
    for combo in combinations(pool_u, k):
        avaliados += 1
        if avaliados > max_avaliar:
            break
        r = validar_selecao_panorama(
            list(combo), k, alvos, indicadores_dezena,
            calc_ind_fn, ultimo_prev, extras, modo,
        )
        if r.get("valido"):
            out.append(r["dezenas"])
            if len(out) >= limite:
                break
    return out
