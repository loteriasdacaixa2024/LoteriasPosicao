# -*- coding: utf-8 -*-
"""
Nº da sequência sorteada em cada concurso (aba 7 · Panorama).

É o mesmo Nº da coluna da aba 5 quando se clica em «Mostrar vencedor»:
posição 1-based da aposta no padrão, com a lista completa ordenada por
|distância da média| e, no empate, pela soma. Empate total preserva a
ordem de `expandir_jogos_padrao` (sort estável).
"""
from __future__ import annotations

import time
from collections import Counter, defaultdict
from itertools import combinations
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from analise_inteligentes_diadesorte.service import (
    descricao_bma_do_padrao,
    jogos_possiveis_padrao,
    padrao_inicial,
    pool_por_digito_universo,
)
from analise_inteligentes_diadesorte.soma_media import (
    calcular_faixa_soma,
    classificar_soma,
    somas_historicas_do_padrao,
)

_CACHE: Dict[Tuple[Any, ...], Dict[str, Any]] = {}


def _norm_padrao(padrao: str) -> str:
    digs = [x for x in str(padrao or "").replace(",", " ").split() if x.strip().isdigit()]
    return " ".join(digs)


def _grupos_somas(
    padrao: str,
    *,
    min_dezena: int,
    max_dezena: int,
) -> Optional[List[List[int]]]:
    """Somas das combinações de cada dígito, na ordem de itertools.combinations."""
    digs = [int(x) for x in _norm_padrao(padrao).split() if x.strip().isdigit()]
    if not digs:
        return None
    need = Counter(digs)
    pools = pool_por_digito_universo(min_dezena, max_dezena)
    for dig, qtd in need.items():
        if len(pools.get(dig) or []) < qtd:
            return None
    return [
        [sum(combo) for combo in combinations(pools[d], need[d])]
        for d in sorted(need.keys())
    ]


def _sufixos_por_soma(grupos: Sequence[Sequence[int]]) -> List[Counter]:
    """suffix[i][soma] = jogos formados só com os grupos i..fim."""
    n = len(grupos)
    suffix: List[Counter] = [Counter() for _ in range(n + 1)]
    suffix[n][0] = 1
    for i in range(n - 1, -1, -1):
        nxt: Counter = Counter()
        tail = suffix[i + 1]
        for gs in grupos[i]:
            for prev_s, prev_c in tail.items():
                nxt[int(gs) + int(prev_s)] += int(prev_c)
        suffix[i] = nxt
    return suffix


def _antes_mesma_soma(
    grupos: Sequence[Sequence[int]],
    ranks: Sequence[int],
    soma_alvo: int,
    suffix: Sequence[Counter],
) -> int:
    """Quantas apostas com a mesma soma vêm antes, na ordem do produto."""
    antes = 0
    prefixo = 0
    ultimo = len(grupos) - 1
    for gi, grupo in enumerate(grupos):
        rank = int(ranks[gi])
        for r in range(rank):
            parcial = prefixo + int(grupo[r])
            need = int(soma_alvo) - parcial
            if gi == ultimo:
                if need == 0:
                    antes += 1
            else:
                antes += int(suffix[gi + 1].get(need) or 0)
        prefixo += int(grupo[rank])
    return antes


def _ranks_dos_grupos(
    dezenas: Sequence[int],
    padrao: str,
    *,
    min_dezena: int,
    max_dezena: int,
) -> Optional[List[int]]:
    dez = sorted(int(x) for x in dezenas)
    digs = [int(x) for x in _norm_padrao(padrao).split() if x.strip().isdigit()]
    if not digs or padrao_inicial(dez) != " ".join(str(d) for d in digs):
        return None
    need = Counter(digs)
    pools = pool_por_digito_universo(min_dezena, max_dezena)
    grupos_dez: Dict[int, Tuple[int, ...]] = defaultdict(tuple)
    tmp: Dict[int, List[int]] = defaultdict(list)
    for n in dez:
        tmp[int(n) // 10].append(int(n))
    for d, vals in tmp.items():
        grupos_dez[d] = tuple(vals)
    ranks: List[int] = []
    for d in sorted(need.keys()):
        combos = list(combinations(pools.get(d) or [], int(need[d])))
        alvo = grupos_dez.get(d) or tuple()
        try:
            ranks.append(combos.index(alvo))
        except ValueError:
            return None
    return ranks


def mapa_sequencia_no_padrao(
    padrao: str,
    dezenas_alvos: Iterable[Sequence[int]],
    faixa: Optional[Dict[str, Any]],
    *,
    min_dezena: int = 1,
    max_dezena: int = 31,
) -> Dict[Tuple[int, ...], int]:
    """
    Mapa dezena-sorteada → Nº (1-based) na ordem padrão da aba 5.

    A ordenação da aba 5 é |soma − média| e, no empate, a soma. Apostas
    com a mesma soma ficam na ordem de expandir_jogos_padrao. O histograma
    de somas sai por programação dinâmica; a posição entre somas iguais
    conta os predecessores no produto das combinações.
    """
    vistos: Dict[Tuple[int, ...], None] = {}
    for dez in dezenas_alvos:
        if not dez:
            continue
        vistos[tuple(sorted(int(x) for x in dez))] = None
    if not vistos:
        return {}

    grupos = _grupos_somas(padrao, min_dezena=min_dezena, max_dezena=max_dezena)
    if not grupos:
        return {}
    suffix = _sufixos_por_soma(grupos)
    hist = suffix[0]
    media = None if not faixa else faixa.get("media")
    sem_media = media is None

    def _ad(soma: int) -> int:
        if sem_media:
            return 99999
        return abs(int(soma) - int(media))

    antes_da_soma: Dict[Tuple[int, int], int] = {}
    out: Dict[Tuple[int, ...], int] = {}
    for dez in vistos:
        ranks = _ranks_dos_grupos(dez, padrao, min_dezena=min_dezena, max_dezena=max_dezena)
        if not ranks:
            continue
        soma = int(sum(dez))
        ad = _ad(soma)
        chave = (ad, soma)
        n = antes_da_soma.get(chave)
        if n is None:
            n = 0
            for s, qtd in hist.items():
                a2 = _ad(int(s))
                if a2 < ad or (a2 == ad and int(s) < soma):
                    n += int(qtd)
            antes_da_soma[chave] = n
        antes = _antes_mesma_soma(grupos, ranks, soma, suffix)
        out[dez] = n + antes + 1
    return out


def montar_sequencias_sorteadas(svc, *, base: str = "geral") -> Dict[str, Any]:
    """Um registro por concurso: padrão sorteado e o Nº da sequência na aba 5."""
    t0 = time.perf_counter()
    lim = svc._limites()
    dmin = int(lim["min_dezena"])
    dmax = int(lim["max_dezena"])

    dados = svc.listar_resultados(janela=0, base=base)
    linhas_src = list(dados.get("linhas") or [])
    total = len(linhas_src)
    primeiro = dados.get("primeiro_concurso")
    ultimo = dados.get("ultimo_concurso")
    cache_key = (
        getattr(svc, "modality_key", ""),
        str(base or "geral"),
        int(ultimo or 0),
        int(total),
        dmin,
        dmax,
    )
    hit = _CACHE.get(cache_key)
    if hit:
        out = dict(hit)
        out["cache_hit"] = True
        out["elapsed_ms"] = int((time.perf_counter() - t0) * 1000)
        return out

    por_padrao: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for l in linhas_src:
        dez = sorted(int(x) for x in (l.get("dezenas") or []) if str(x).strip() != "")
        pad = _norm_padrao(str(l.get("padrao_inicial") or ""))
        if not pad and dez:
            pad = padrao_inicial(dez)
        if not pad or not dez:
            continue
        por_padrao[pad].append({
            "concurso": int(l.get("concurso") or 0),
            "data": l.get("data") or "",
            "dezenas": dez,
            "dezenas_fmt": l.get("dezenas_fmt") or " ".join(f"{d:02d}" for d in dez),
            "padrao": pad,
            "soma": int(l.get("soma") or 0) or sum(dez),
        })

    linhas: List[Dict[str, Any]] = []
    for pad, itens in por_padrao.items():
        somas = somas_historicas_do_padrao(
            [{"padrao_inicial": pad, "soma": it["soma"], "dezenas": it["dezenas"]} for it in itens],
            pad,
        )
        faixa = calcular_faixa_soma(somas, fonte="historico")
        ranks = mapa_sequencia_no_padrao(
            pad,
            (it["dezenas"] for it in itens),
            faixa,
            min_dezena=dmin,
            max_dezena=dmax,
        )
        jogos = jogos_possiveis_padrao(pad, min_dezena=dmin, max_dezena=dmax)
        desc = descricao_bma_do_padrao(pad)
        for it in itens:
            cls = classificar_soma(it["soma"], faixa)
            linhas.append({
                "concurso": it["concurso"],
                "data": it["data"],
                "padrao": pad,
                "descricao": desc,
                "dezenas_fmt": it["dezenas_fmt"],
                "soma": it["soma"],
                "media": cls.get("media"),
                "sequencia_n": ranks.get(tuple(it["dezenas"])),
                "status_media": cls.get("status_media") or "",
                "status_media_label": cls.get("status_media_label") or "",
                "jogos_possiveis": jogos,
            })

    linhas.sort(key=lambda r: int(r["concurso"] or 0))
    payload = {
        "sucesso": True,
        "base": base,
        "total_concursos": len(linhas),
        "primeiro_concurso": int(primeiro) if primeiro is not None else (linhas[0]["concurso"] if linhas else None),
        "ultimo_concurso": int(ultimo) if ultimo is not None else (linhas[-1]["concurso"] if linhas else None),
        "linhas": linhas,
        "api": "/analise/api/inteligentes/sequencias-sorteadas",
    }
    _CACHE[cache_key] = payload
    if len(_CACHE) > 8:
        for old in list(_CACHE.keys())[:-4]:
            _CACHE.pop(old, None)
    out = dict(payload)
    out["cache_hit"] = False
    out["elapsed_ms"] = int((time.perf_counter() - t0) * 1000)
    return out
