# -*- coding: utf-8 -*-
"""Gerador: 2 Novas + 1 Repetida (união dos 2 últimos) + complemento com filtros opcionais."""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Set

from .service import contexto_dois_ultimos
from .specs import get_ciclo_spec


def _digitos_distintos(dezenas: List[int]) -> int:
    return len({d % 10 for d in dezenas})


def _score_faixas(dezenas: List[int], faixas) -> float:
    if not faixas:
        return 0.0
    counts = []
    for _nome, lo, hi in faixas:
        counts.append(sum(1 for d in dezenas if lo <= d <= hi))
    # penaliza concentração extrema
    if not counts:
        return 0.0
    media = sum(counts) / len(counts)
    var = sum((c - media) ** 2 for c in counts) / len(counts)
    return -var


def _score_soma(dezenas: List[int], alvo: float) -> float:
    if not alvo:
        return 0.0
    return -abs(sum(dezenas) - alvo)


def _score_digitos(dezenas: List[int], modo: Optional[int]) -> float:
    if modo is None:
        return 0.0
    return -abs(_digitos_distintos(dezenas) - int(modo))


def _completar(
    base: List[int],
    *,
    precisamos: int,
    universo: Set[int],
    proibidas: Set[int],
    rng: random.Random,
) -> Optional[List[int]]:
    livres = sorted(universo - set(base) - proibidas)
    if precisamos <= 0:
        return sorted(base)
    if len(livres) < precisamos:
        return None
    extra = rng.sample(livres, precisamos)
    return sorted(set(base) | set(extra))


def gerar_apostas_ciclo(
    modality_key: str,
    *,
    quantidade: int = 10,
    pick: Optional[int] = None,
    filtro_faixas: bool = False,
    filtro_soma: bool = False,
    filtro_digitos: bool = False,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    spec = get_ciclo_spec(modality_key)
    ctx = contexto_dois_ultimos(modality_key)
    if not ctx.get("ok"):
        return ctx

    pick_n = int(pick if pick is not None else spec.pick_default)
    pick_n = max(spec.pick_min, min(spec.pick_max, pick_n))
    qtd = max(1, min(int(quantidade or 10), 200))

    pool_novas = list(ctx["pool"]["novas"])
    pool_rep = list(ctx["pool"]["repetidas"])
    n_fix = int(spec.novas_fixas)
    r_fix = int(spec.repetidas_fixas)

    if len(pool_novas) < n_fix:
        return {
            "ok": False,
            "erro": f"Pool de Novas insuficiente ({len(pool_novas)} < {n_fix}).",
            "contexto": ctx,
        }
    if len(pool_rep) < r_fix:
        return {
            "ok": False,
            "erro": f"Pool de Repetidas insuficiente ({len(pool_rep)} < {r_fix}).",
            "contexto": ctx,
        }

    precisa_livres = pick_n - n_fix - r_fix
    if precisa_livres < 0:
        return {
            "ok": False,
            "erro": f"Aposta de {pick_n} dezenas é menor que {n_fix}+{r_fix} fixas.",
            "contexto": ctx,
        }

    universo = set(range(spec.dezena_min, spec.dezena_max + 1))
    stats = ctx.get("estatisticas") or {}
    soma_alvo = float(stats.get("soma_media_historica") or 0)
    modo_dig = stats.get("digitos_distintos_modo")

    rng = random.Random(seed)
    apostas: List[dict] = []
    tentativas_max = max(qtd * 40, 80)
    vistos_jogos: Set[tuple] = set()

    for _ in range(tentativas_max):
        if len(apostas) >= qtd:
            break
        # Sem prioridade: amostra uniforme da união
        novas_pick = rng.sample(pool_novas, n_fix)
        # repetida não pode coincidir com as novas já escolhidas
        rep_candidatas = [x for x in pool_rep if x not in novas_pick]
        if len(rep_candidatas) < r_fix:
            continue
        rep_pick = rng.sample(rep_candidatas, r_fix)
        base = list(novas_pick) + list(rep_pick)

        # candidatos a complemento — gera alguns e escolhe o melhor score
        melhores = []
        for __ in range(12):
            jogo = _completar(
                base,
                precisamos=precisa_livres,
                universo=universo,
                proibidas=set(),
                rng=rng,
            )
            if not jogo or len(jogo) != pick_n:
                continue
            chave = tuple(jogo)
            if chave in vistos_jogos:
                continue
            score = 0.0
            if filtro_faixas:
                score += 3.0 * _score_faixas(jogo, spec.faixas)
            if filtro_soma:
                score += 2.0 * _score_soma(jogo, soma_alvo)
            if filtro_digitos:
                score += 2.0 * _score_digitos(jogo, modo_dig)
            # leve preferência por diversidade de faixas mesmo sem filtro
            if not filtro_faixas and spec.faixas:
                score += 0.15 * _score_faixas(jogo, spec.faixas)
            melhores.append((score, jogo, novas_pick, rep_pick))

        if not melhores:
            continue
        melhores.sort(key=lambda t: t[0], reverse=True)
        score, jogo, npick, rpick = melhores[0]
        chave = tuple(jogo)
        if chave in vistos_jogos:
            continue
        vistos_jogos.add(chave)
        livres = sorted(set(jogo) - set(npick) - set(rpick))
        apostas.append({
            "dezenas": jogo,
            "novas": sorted(npick),
            "repetidas": sorted(rpick),
            "livres": livres,
            "soma": sum(jogo),
            "digitos_distintos": _digitos_distintos(jogo),
            "score": round(score, 3),
        })

    return {
        "ok": True,
        "contexto": ctx,
        "parametros": {
            "quantidade": qtd,
            "pick": pick_n,
            "novas_fixas": n_fix,
            "repetidas_fixas": r_fix,
            "filtro_faixas": bool(filtro_faixas),
            "filtro_soma": bool(filtro_soma),
            "filtro_digitos": bool(filtro_digitos),
        },
        "geradas": len(apostas),
        "apostas": apostas,
        "aviso": (
            None
            if len(apostas) >= qtd
            else f"Geradas {len(apostas)} de {qtd} (pool/filtros restritivos)."
        ),
    }
