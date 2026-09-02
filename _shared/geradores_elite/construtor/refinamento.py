# -*- coding: utf-8 -*-
"""Refinamento inteligente de apostas do Construtor — pós-processamento do lote."""
from __future__ import annotations

import random
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from geradores_elite.otimizador.restricoes import perfil_aposta

from .construcoes_core import padrao_inicial_de

INTENSIDADE_TROCAS = {
    "leve": (1, 2),
    "media": (3, 4),
    "forte": (4, 6),
}
DISTANCIA_MIN = {"baixa": 2, "media": 3, "alta": 4}
CANDIDATAS_POR_SLOT = 24


def distancia_conjunto(a: Sequence[int], b: Sequence[int]) -> int:
    k = max(len(a), len(b), 1)
    return k - len(set(a) & set(b))


def diffs_posicao(jogado: Sequence[int], sorteado: Sequence[int]) -> List[int]:
    """Mesma convenção da conferência: jogado ordenado − sorteado ordenado."""
    j = sorted(int(x) for x in jogado)
    s = sorted(int(x) for x in sorteado)
    n = min(len(j), len(s))
    return [j[i] - s[i] for i in range(n)]


def abs_interno(a: Sequence[int], b: Sequence[int]) -> int:
    return sum(abs(d) for d in diffs_posicao(a, b))


def _seq_max(dz: Sequence[int]) -> int:
    s = sorted(int(x) for x in dz)
    best = cur = 1
    for i in range(1, len(s)):
        if s[i] == s[i - 1] + 1:
            cur += 1
            best = max(best, cur)
        else:
            cur = 1
    return best if s else 0


def _estrutura_ok(orig: Dict[str, int], nova: Dict[str, int]) -> bool:
    for k in ("pares", "impares", "baixas", "medias", "altas"):
        if abs(orig.get(k, 0) - nova.get(k, 0)) > 1:
            return False
    return True


def _moda_delta_posicoes(
    apostas: Sequence[Sequence[int]],
    sorteios: Sequence[Sequence[int]],
    k: int,
) -> List[int]:
    contagens = [Counter() for _ in range(k)]
    for ap in apostas:
        a = sorted(int(x) for x in ap)[:k]
        if len(a) < k:
            continue
        for sor in sorteios:
            r = sorted(int(x) for x in sor)[:k]
            if len(r) < k:
                continue
            for i in range(k):
                contagens[i][a[i] - r[i]] += 1
    out: List[int] = []
    for c in contagens:
        if not c:
            out.append(0)
            continue
        prefer = [(abs(d), -c[d], d) for d in c if abs(d) <= 2]
        if prefer:
            prefer.sort()
            out.append(prefer[0][2])
        else:
            out.append(c.most_common(1)[0][0])
    return out


def _direcao_pos(modo: str, moda_delta: int) -> int:
    """+1 sobe a dezena no volante; -1 desce; 0 ambos."""
    if modo == "mais":
        return 1
    if modo == "menos":
        return -1
    if modo == "inteligente":
        # delta = jogado − sorteado: +1 ⇒ resultado costuma ser menor → descer
        if moda_delta > 0:
            return -1
        if moda_delta < 0:
            return 1
        return 0
    return 0


def _vizinhos(d: int, pool: Set[int], direcao: int) -> List[int]:
    passos = (1, 2, -1, -2) if direcao == 0 else ((1, 2) if direcao > 0 else (-1, -2))
    out = []
    for st in passos:
        n = d + st
        if n in pool and n != d:
            out.append(n)
    return out


def _substituiveis(
    ap: Sequence[int],
    nucleo: Set[int],
    faltantes: Set[int],
) -> List[int]:
    rest = [d for d in ap if d not in faltantes]
    frias = [d for d in rest if d not in nucleo]
    quentes = [d for d in rest if d in nucleo]
    return frias + quentes


def _montar_candidata(
    original: List[int],
    pool: Set[int],
    n_trocas: int,
    modo: str,
    moda_pos: List[int],
    nucleo: Set[int],
    faltantes: Set[int],
    rng: random.Random,
) -> Optional[List[int]]:
    k = len(original)
    atual = list(original)
    pos_idx = {d: i for i, d in enumerate(sorted(original))}
    alvos = _substituiveis(original, nucleo, faltantes)
    if not alvos:
        alvos = list(original)
    rng.shuffle(alvos)
    alvos = alvos[: max(1, n_trocas)]
    usadas = set(atual)
    for d in alvos:
        i = pos_idx.get(d, 0)
        direcao = _direcao_pos(modo, moda_pos[i] if i < len(moda_pos) else 0)
        cands = [n for n in _vizinhos(d, pool, direcao) if n not in usadas]
        if not cands:
            cands = [n for n in sorted(pool) if n not in usadas]
        if not cands:
            continue
        escolhida = rng.choice(cands)
        atuais_sem = [x for x in atual if x != d]
        atuais_sem.append(escolhida)
        if len(set(atuais_sem)) != k:
            continue
        atual = atuais_sem
        usadas = set(atual)
        pos_idx = {x: i for i, x in enumerate(sorted(atual))}
    novo = sorted(set(int(x) for x in atual))
    if len(novo) != k:
        return None
    if novo == sorted(original):
        return None
    if faltantes and (set(original) & faltantes) and not (set(novo) & faltantes):
        inj = sorted(faltantes - set(novo))
        if inj:
            sair = _substituiveis(novo, nucleo, faltantes)
            if sair:
                novo = sorted((set(novo) - {sair[0]}) | {inj[0]})
    if len(novo) != k:
        return None
    return novo


def _score(
    original: List[int],
    cand: List[int],
    modality_key: str,
    dmin: int,
    faltantes: Set[int],
    lote_sel: Sequence[Sequence[int]],
) -> Optional[float]:
    d = distancia_conjunto(original, cand)
    if d < dmin:
        return None
    po = perfil_aposta(original, modality_key)
    pc = perfil_aposta(cand, modality_key)
    if not _estrutura_ok(po, pc):
        return None
    pts = 20.0
    pts += 8.0 - abs(sum(original) - sum(cand)) * 0.15
    if faltantes:
        if set(cand) & faltantes:
            pts += 10.0
        elif not (set(original) & faltantes):
            pts += 2.0
        else:
            pts -= 12.0
    pts += min(d, 5) * 2.0
    if _seq_max(cand) >= 4:
        pts -= 6.0
    try:
        if padrao_inicial_de(cand) == padrao_inicial_de(original):
            pts += 3.0
    except Exception:
        pass
    for outra in lote_sel:
        if distancia_conjunto(cand, outra) < dmin:
            pts -= 18.0
    pts -= abs_interno(original, cand) * 0.08
    return pts


def refinar_apostas(
    originais: Sequence[Sequence[int]],
    pool: Sequence[int],
    *,
    modality_key: str = "diadesorte",
    modo: str = "inteligente",
    intensidade: str = "leve",
    qtd_apostas: Any = "todas",
    variacoes: int = 1,
    distancia: str = "media",
    faltantes_ciclo: Optional[Sequence[int]] = None,
    sorteios: Optional[Sequence[Sequence[int]]] = None,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    origs = [sorted(int(x) for x in a) for a in originais if a]
    if not origs:
        return {"ok": False, "erro": "Não há apostas originais para refinar."}
    k = len(origs[0])
    pool_set = {int(x) for x in pool}
    if len(pool_set) < k:
        return {"ok": False, "erro": "Conjunto-base menor que o tamanho da aposta."}
    modo = (modo or "inteligente").lower()
    if modo not in ("mais", "menos", "misto", "inteligente"):
        modo = "inteligente"
    intens = (intensidade or "leve").lower()
    if intens not in INTENSIDADE_TROCAS:
        intens = "leve"
    dist_key = (distancia or "media").lower()
    dmin = DISTANCIA_MIN.get(dist_key, 3)
    n_var = max(1, min(int(variacoes or 1), 5))
    n_orig = len(origs)
    if str(qtd_apostas).lower() in ("todas", "all", ""):
        n_ref = n_orig
    else:
        n_ref = max(1, min(int(qtd_apostas), n_orig))

    freq = Counter(d for a in origs for d in a)
    nucleo = {d for d, c in freq.items() if c >= max(2, n_orig // 3)}
    faltantes = {int(x) for x in (faltantes_ciclo or []) if int(x) in pool_set}
    moda_pos = _moda_delta_posicoes(origs, sorteios or [], k)
    lo_t, hi_t = INTENSIDADE_TROCAS[intens]
    rng = random.Random(seed)

    indices = list(range(n_orig))
    rng.shuffle(indices)
    indices = sorted(indices[:n_ref])

    escolhidas: List[List[int]] = []
    pares: List[Dict[str, Any]] = []
    for idx in indices:
        original = origs[idx]
        intens_slot = intens
        if modo == "inteligente" and n_ref >= 4:
            ciclo_i = indices.index(idx)
            intens_slot = ("leve", "leve", "media", "forte")[ciclo_i % 4]
        lo, hi = INTENSIDADE_TROCAS.get(intens_slot, (lo_t, hi_t))
        modo_slot = modo
        if modo == "misto":
            modo_slot = rng.choice(("mais", "menos", "inteligente"))
        ranked: List[Tuple[float, List[int]]] = []
        seen: Set[Tuple[int, ...]] = set()
        for _ in range(CANDIDATAS_POR_SLOT * n_var):
            n_trocas = rng.randint(lo, hi)
            cand = _montar_candidata(
                original, pool_set, n_trocas, modo_slot, moda_pos, nucleo, faltantes, rng
            )
            if not cand:
                continue
            key = tuple(cand)
            if key in seen:
                continue
            seen.add(key)
            sc = _score(original, cand, modality_key, dmin, faltantes, escolhidas)
            if sc is None:
                continue
            ranked.append((sc, cand))
        ranked.sort(key=lambda x: -x[0])
        keep = ranked[:n_var]
        po = perfil_aposta(original, modality_key)
        for sc, cand in keep:
            escolhidas.append(cand)
            pc = perfil_aposta(cand, modality_key)
            mantidas = sorted(set(original) & set(cand))
            substituidas = sorted(set(original) - set(cand))
            novas = sorted(set(cand) - set(original))
            pares.append({
                "linha_origem": idx + 1,
                "original": original,
                "refinada": cand,
                "mantidas": mantidas,
                "substituidas": substituidas,
                "novas": novas,
                "n_trocadas": len(substituidas),
                "distancia": distancia_conjunto(original, cand),
                "abs_interno": abs_interno(original, cand),
                "score": round(sc, 2),
                "intensidade": intens_slot,
                "estrutura_original": po,
                "estrutura_refinada": pc,
                "faltante_ciclo": sorted(set(cand) & faltantes),
            })

    if not pares:
        return {
            "ok": False,
            "erro": (
                "Nenhuma candidata passou nos filtros (estrutura, distância ou pool). "
                "Tente intensidade menor ou distância baixa."
            ),
        }
    return {
        "ok": True,
        "config": {
            "modo": modo,
            "intensidade": intens,
            "qtd_apostas": n_ref,
            "variacoes": n_var,
            "distancia": dist_key,
            "distancia_min": dmin,
        },
        "faltantes_ciclo": sorted(faltantes),
        "n_originais": n_orig,
        "n_refinadas": len(pares),
        "apostas": pares,
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
    }
