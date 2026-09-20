# -*- coding: utf-8 -*-
"""
Motor de geração — Estatísticas Básicas (carro-chefe) + pendentes do ciclo.

Regras:
- Cada aposta tem exatamente `k` dezenas distintas no universo oficial.
- Se houver até `k` pendentes, TODAS entram em CADA aposta.
- Se houver mais de `k` pendentes, TODAS entram no LOTE (cobertura).
  A quantidade mínima de apostas sobe para caber todas, se necessário.
- O complemento segue o perfil da janela (pares/ímpares, repetidos,
  sequências, finais iguais, atraso). Não inventa estatística.
- Cada aposta usa um padrão inicial diferente (aba 4 · 85 padrões).
- Pelo menos uma aposta usa um padrão que ainda não saiu.
- Não há volantes idênticos no lote.
"""
from __future__ import annotations

import math
import random
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from analise_escolha_visual.enriquecimento.motor import conjuntos_concurso


def _diagonais_da_aposta(dezenas: Sequence[int], dmin: int, dmax: int) -> List[Dict[str, Any]]:
    try:
        from analise_inteligentes_diadesorte.diagonais_volante import diagonais_na_aposta
        return diagonais_na_aposta(dezenas, dmin=dmin, dmax=dmax) or []
    except Exception:
        return []


def _resumo_diagonais_janela(
    linhas: Sequence[Dict[str, Any]],
    dmin: int,
    dmax: int,
) -> Dict[str, Any]:
    ultimo = linhas[0] if linhas else None
    ult_nums = [int(x) for x in (ultimo or {}).get("numeros") or []]
    ultimo_diags = _diagonais_da_aposta(ult_nums, dmin, dmax)
    n = 0
    com = 0
    for row in linhas:
        nums = [int(x) for x in (row.get("numeros") or [])]
        if not nums:
            continue
        n += 1
        if _diagonais_da_aposta(nums, dmin, dmax):
            com += 1
    return {
        "ultimo": ultimo_diags,
        "ultimo_concurso": (ultimo or {}).get("concurso"),
        "ultimo_numeros": ult_nums,
        "janela_total": n,
        "janela_com_diagonal": com,
        "janela_pct": round(100.0 * com / n, 1) if n else 0,
    }


def _padrao_de(dezenas: Sequence[int]) -> str:
    return " ".join(str(int(n) // 10) for n in sorted(int(x) for x in dezenas))


def _digs_padrao(padrao: str) -> List[int]:
    return [int(x) for x in str(padrao or "").replace(",", " ").split() if str(x).strip().isdigit()]


def _norm_padrao(padrao: str) -> str:
    return " ".join(str(d) for d in _digs_padrao(padrao))


def _eh_faltante(p: Dict[str, Any]) -> bool:
    return int(p.get("frequencia") or 0) <= 0 or str(p.get("status") or "") == "faltante"


def _padrao_compativel(padrao: str, locked: Sequence[int]) -> bool:
    need = Counter(_digs_padrao(padrao))
    have = Counter(int(n) // 10 for n in locked)
    return all(need[d] >= have[d] for d in have)


def _padroes_teoricos(k: int, dmin: int, dmax: int) -> List[str]:
    disp: Counter = Counter()
    for n in range(int(dmin), int(dmax) + 1):
        disp[n // 10] += 1
    digitos = sorted(disp)
    out: List[str] = []

    def rec(i: int, restante: int, atual: List[int]) -> None:
        if i == len(digitos):
            if restante == 0 and atual:
                out.append(" ".join(str(x) for x in atual))
            return
        dig = digitos[i]
        for qtd in range(0, min(restante, int(disp[dig])) + 1):
            rec(i + 1, restante - qtd, atual + ([dig] * qtd))

    rec(0, int(k), [])
    return out


def _catalogo_padroes_fallback(
    linhas: Sequence[Dict[str, Any]],
    k: int,
    dmin: int,
    dmax: int,
) -> List[Dict[str, Any]]:
    teoricos = _padroes_teoricos(k, dmin, dmax)
    seen: Counter = Counter()
    for row in linhas:
        nums = [int(x) for x in (row.get("numeros") or [])]
        if len(nums) == k:
            seen[_padrao_de(nums)] += 1
    out = []
    for p in teoricos:
        freq = int(seen.get(p, 0))
        out.append({
            "padrao": p,
            "frequencia": freq,
            "status": "faltante" if freq <= 0 else "frequente",
            "atraso": None,
        })
    return out


def _cover_key(padrao: str, need: Counter) -> Tuple[int, int]:
    have = Counter(_digs_padrao(padrao))
    covered = sum(min(have[d], need[d]) for d in need)
    tipos = sum(1 for d in need if need[d] > 0 and have[d] > 0)
    return (-covered, -tipos)


def _escolher_padroes(
    catalogo: Sequence[Dict[str, Any]],
    n: int,
    locked_ref: Sequence[int],
    rng: random.Random,
    pendentes: Optional[Sequence[int]] = None,
) -> List[Dict[str, Any]]:
    """N padrões distintos. Pelo menos um ainda não saiu (aba 4 / aba 7)."""
    seen: Set[str] = set()
    cat: List[Dict[str, Any]] = []
    for raw in catalogo:
        txt = _norm_padrao(raw.get("padrao") or "")
        if not txt or txt in seen:
            continue
        item = dict(raw)
        item["padrao"] = txt
        item["inedito"] = _eh_faltante(item)
        cat.append(item)
        seen.add(txt)
    if not cat:
        return []
    n = max(1, int(n))
    need = Counter(int(x) // 10 for x in (locked_ref or pendentes or []))

    def _ok(p: Dict[str, Any], locked: Sequence[int]) -> bool:
        return _padrao_compativel(p.get("padrao") or "", locked)

    faltantes = [p for p in cat if p.get("inedito")]
    usados = [p for p in cat if not p.get("inedito")]
    escolhidos: List[Dict[str, Any]] = []
    usados_txt: Set[str] = set()

    ineditos_ok = [p for p in faltantes if _ok(p, locked_ref)]
    ineditos = ineditos_ok or list(faltantes)
    if ineditos:
        ineditos.sort(key=lambda p: (_cover_key(p.get("padrao") or "", need), rng.random()))
        pick = dict(ineditos[0])
        pick["inedito"] = True
        escolhidos.append(pick)
        usados_txt.add(pick["padrao"])
        for d in _digs_padrao(pick["padrao"]):
            if need[d]:
                need[d] -= 1

    def _encaixar(pool: List[Dict[str, Any]], prefer_ok: bool) -> None:
        nonlocal need
        remaining = [p for p in pool if p.get("padrao") not in usados_txt]
        while len(escolhidos) < n and remaining:
            remaining.sort(key=lambda p: (
                0 if (not prefer_ok or not locked_ref or _ok(p, locked_ref)) else 1,
                _cover_key(p.get("padrao") or "", need),
                -int(p.get("atraso") or 0),
                int(p.get("frequencia") or 0),
                rng.random(),
            ))
            escolhido = None
            for p in remaining:
                if prefer_ok and locked_ref and not _ok(p, locked_ref):
                    continue
                escolhido = p
                break
            if escolhido is None:
                return
            txt = escolhido.get("padrao")
            remaining = [p for p in remaining if p.get("padrao") != txt]
            item = dict(escolhido)
            item["inedito"] = _eh_faltante(item)
            escolhidos.append(item)
            usados_txt.add(txt)
            for d in _digs_padrao(txt):
                if need[d]:
                    need[d] -= 1

    _encaixar([p for p in (usados + faltantes) if p.get("padrao") not in usados_txt], True)
    if len(escolhidos) < n:
        _encaixar([p for p in cat if p.get("padrao") not in usados_txt], False)
    return escolhidos[:n]


def _atribuir_pendentes(
    pendentes: Sequence[int],
    padroes: Sequence[str],
    k: int,
) -> List[List[int]]:
    """Encaixa pendentes nos padrões sem estourar o dígito de cada um."""
    pends = sorted({int(x) for x in pendentes})
    pads = [p for p in padroes if _digs_padrao(p)]
    n_bets = max(1, len(pads))
    k = max(1, int(k))
    assigned: List[List[int]] = [[] for _ in range(n_bets)]
    if not pends:
        return assigned
    if not pads:
        return [list(pends[: min(len(pends), k)]) for _ in range(n_bets)]
    quotas = [Counter(_digs_padrao(p)) for p in pads]
    todas_em_cada = 0 < len(pends) < k
    if todas_em_cada:
        for i, q in enumerate(quotas):
            for n in pends:
                d = n // 10
                if q[d] > 0:
                    assigned[i].append(n)
                    q[d] -= 1
        return assigned
    teto = k if len(pends) > n_bets * max(1, k - 2) else max(1, k - 2)
    for n in pends:
        d = n // 10
        candidatos = [
            j for j in range(n_bets)
            if quotas[j][d] > 0 and len(assigned[j]) < teto
        ]
        if not candidatos:
            candidatos = [
                j for j in range(n_bets)
                if quotas[j][d] > 0 and len(assigned[j]) < k
            ]
        if not candidatos:
            continue
        j = min(candidatos, key=lambda x: (len(assigned[x]), -quotas[x][d]))
        assigned[j].append(n)
        quotas[j][d] -= 1
    return assigned


def _pick_stoch(
    pool: Sequence[int],
    chosen: Sequence[int],
    *,
    pendentes: Set[int],
    ultimo_set: Set[int],
    alvo: Dict[str, Any],
    atrasos: Dict[int, int],
    freq20: Counter,
    persistentes: Set[int],
    rng: random.Random,
    max_pendentes: Optional[int] = None,
) -> Optional[int]:
    if not pool:
        return None
    ranked = sorted(
        pool,
        key=lambda n: (
            -_rank_candidato(
                n, chosen, pendentes=pendentes, ultimo_set=ultimo_set,
                alvo=alvo, atrasos=atrasos, freq20=freq20,
                persistentes=persistentes, max_pendentes=max_pendentes,
            ),
            rng.random(),
        ),
    )
    topo = ranked[: max(2, min(len(ranked), 6))]
    if rng.random() < 0.4:
        return topo[0]
    return rng.choice(topo)


def _montar_estrito_padrao(
    locked: Sequence[int],
    padrao: str,
    *,
    k: int,
    dmin: int,
    dmax: int,
    pendentes: Sequence[int],
    ultimo_set: Set[int],
    alvo: Dict[str, Any],
    atrasos: Dict[int, int],
    freq20: Counter,
    persistentes: Set[int],
    rng: random.Random,
    max_pendentes: Optional[int] = None,
) -> List[int]:
    need = Counter(_digs_padrao(padrao))
    if sum(need.values()) != k:
        return []
    chosen: List[int] = []
    for n in locked:
        n = int(n)
        if not (dmin <= n <= dmax) or n in chosen:
            continue
        d = n // 10
        if need[d] <= 0:
            continue
        chosen.append(n)
        need[d] -= 1
    pend_set = {int(x) for x in pendentes}
    for dig, qtd in list(need.items()):
        if qtd <= 0:
            continue
        pool = [n for n in range(dmin, dmax + 1) if n // 10 == dig and n not in chosen]
        if len(pool) < qtd:
            return []
        for _ in range(qtd):
            pick = _pick_stoch(
                pool, chosen, pendentes=pend_set, ultimo_set=ultimo_set,
                alvo=alvo, atrasos=atrasos, freq20=freq20,
                persistentes=persistentes, rng=rng, max_pendentes=max_pendentes,
            )
            if pick is None:
                return []
            chosen.append(int(pick))
            pool = [n for n in pool if n != pick]
    chosen = sorted(set(chosen))
    if len(chosen) != k or _padrao_de(chosen) != _norm_padrao(padrao):
        return []
    return chosen


def _completar_com_padrao(
    locked: Sequence[int],
    padrao: str,
    *,
    k: int,
    dmin: int,
    dmax: int,
    pendentes: Sequence[int],
    ultimo_set: Set[int],
    alvo: Dict[str, Any],
    atrasos: Dict[int, int],
    freq20: Counter,
    persistentes: Set[int],
    rng: random.Random,
    max_pendentes: Optional[int] = None,
    proibidos: Optional[Set[Tuple[int, ...]]] = None,
) -> List[int]:
    pad = _norm_padrao(padrao)
    if not pad:
        return _completar_aposta(
            locked, k=k, dmin=dmin, dmax=dmax, pendentes=pendentes,
            ultimo_set=ultimo_set, alvo=alvo, atrasos=atrasos, freq20=freq20,
            persistentes=persistentes, rng=rng, max_pendentes=max_pendentes,
        )
    ultimo: List[int] = []
    for _ in range(28):
        jogo = _montar_estrito_padrao(
            locked, pad, k=k, dmin=dmin, dmax=dmax, pendentes=pendentes,
            ultimo_set=ultimo_set, alvo=alvo, atrasos=atrasos, freq20=freq20,
            persistentes=persistentes, rng=rng, max_pendentes=max_pendentes,
        )
        if not jogo:
            continue
        ultimo = jogo
        if not proibidos or tuple(jogo) not in proibidos:
            return jogo
    return ultimo


def _evitar_historico(
    jogo: Sequence[int],
    historico: Set[frozenset],
    *,
    pendentes: Sequence[int],
    dmin: int,
    dmax: int,
    rng: random.Random,
) -> List[int]:
    atual = sorted(int(x) for x in jogo)
    if not historico:
        return atual
    pend_set = {int(x) for x in pendentes}
    for _ in range(16):
        if frozenset(atual) not in historico:
            return atual
        livres = [n for n in range(dmin, dmax + 1) if n not in atual]
        trocavel = [n for n in atual if n not in pend_set]
        if not livres or not trocavel:
            break
        sai = trocavel[rng.randrange(len(trocavel))]
        entra = livres[rng.randrange(len(livres))]
        atual = sorted([n for n in atual if n != sai] + [entra])
    return atual[: len(jogo)] if len(atual) >= len(jogo) else sorted(int(x) for x in jogo)


def _seqs(nums: Sequence[int]) -> List[List[int]]:
    s = sorted(int(x) for x in nums)
    grupos: List[List[int]] = []
    i = 0
    while i < len(s):
        if i < len(s) - 1 and s[i + 1] - s[i] == 1:
            g = [s[i]]
            while i < len(s) - 1 and s[i + 1] - s[i] == 1:
                i += 1
                g.append(s[i])
            grupos.append(g)
        i += 1
    return grupos


def _finais(nums: Sequence[int]) -> List[List[int]]:
    by: Dict[int, List[int]] = defaultdict(list)
    for n in nums:
        by[int(n) % 10].append(int(n))
    return [sorted(g) for g in by.values() if len(g) > 1]


def _paridade(nums: Sequence[int]) -> Tuple[int, int]:
    p = sum(1 for n in nums if int(n) % 2 == 0)
    return p, len(nums) - p


def _faixas(nums: Sequence[int]) -> Tuple[int, int, int]:
    a = sum(1 for n in nums if n <= 10)
    b = sum(1 for n in nums if 11 <= n <= 20)
    c = sum(1 for n in nums if n >= 21)
    return a, b, c


def quantidade_minima(n_pendentes: int, k: int, quantidade: int) -> int:
    q = max(1, int(quantidade or 1))
    k = max(1, int(k))
    n = max(0, int(n_pendentes))
    if n > k:
        q = max(q, int(math.ceil(n / k)))
    return q


def distribuir_pendentes(
    pendentes: Sequence[int],
    n_bets: int,
    k: int,
) -> List[List[int]]:
    """Atribui pendentes a cada aposta. Cobre 100% do conjunto.

    Se cabem com folga (N < k), entram em todas as apostas e o
    complemento segue as estatísticas. Se N >= k, espalha no lote e
    reserva slots para o perfil estatístico (carro-chefe).
    """
    pends = sorted({int(x) for x in pendentes})
    n_bets = max(1, int(n_bets))
    k = max(1, int(k))
    if not pends:
        return [[] for _ in range(n_bets)]
    if 0 < len(pends) < k:
        return [list(pends) for _ in range(n_bets)]
    # Reserva pelo menos 2 casas para o perfil da janela
    teto = max(1, k - 2)
    assigned: List[List[int]] = [[] for _ in range(n_bets)]
    for i, n in enumerate(pends):
        alvo = i % n_bets
        if len(assigned[alvo]) >= teto:
            alvo = min(range(n_bets), key=lambda j: len(assigned[j]))
        assigned[alvo].append(n)
    for bloco in assigned:
        if len(bloco) > k:
            raise ValueError(
                f"Distribuição inválida: {len(bloco)} pendentes em aposta de {k}."
            )
    return assigned


def _atrasos(
    linhas: Sequence[Dict[str, Any]],
    dmin: int,
    dmax: int,
) -> Dict[int, int]:
    last_seen: Dict[int, int] = {}
    ultimo = 0
    for row in linhas:
        c = int(row.get("concurso") or 0)
        if c > ultimo:
            ultimo = c
        for n in row.get("numeros") or []:
            n = int(n)
            if n not in last_seen:
                last_seen[n] = c
    out = {}
    for n in range(dmin, dmax + 1):
        if n in last_seen and ultimo:
            out[n] = max(0, ultimo - last_seen[n])
        else:
            out[n] = 999
    return out


def _freq(linhas: Sequence[Dict[str, Any]], n_last: int = 20) -> Counter:
    c: Counter = Counter()
    for row in list(linhas)[: max(1, n_last)]:
        for n in row.get("numeros") or []:
            c[int(n)] += 1
    return c


def _perfil_alvo(medias: Dict[str, Any], ultimo: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    pares_med = float((medias or {}).get("pares") or 3.5)
    pares_alvo = 3 if pares_med < 3.5 else 4
    if ultimo:
        up = int((ultimo.get("pares") or {}).get("quantidade") or 0)
        if up <= 2:
            pares_alvo = 4
        elif up >= 5:
            pares_alvo = 3
    return {
        "pares": pares_alvo,
        "rep_min": 1,
        "rep_max": 2,
        "quer_seq": True,
        "quer_fin": True,
        "soma_lo": 95,
        "soma_hi": 130,
    }


def _score_jogo(
    nums: Sequence[int],
    *,
    ultimo_set: Set[int],
    alvo: Dict[str, Any],
    atrasos: Dict[int, int],
) -> float:
    s = sorted(int(x) for x in nums)
    p, _i = _paridade(s)
    reps = [n for n in s if n in ultimo_set]
    sg = _seqs(s)
    fg = _finais(s)
    sm = sum(s)
    pts = 0.0
    if p == alvo["pares"]:
        pts += 8
    elif abs(p - alvo["pares"]) == 1:
        pts += 4
    else:
        pts -= 3
    if alvo["rep_min"] <= len(reps) <= alvo["rep_max"]:
        pts += 5
    elif len(reps) == 0:
        pts += 1
    if sg:
        pts += 6 if len(sg) == 1 else 3
        if sg and len(sg[0]) == 2:
            pts += 1.5
    if fg:
        pts += 5 if len(fg) == 1 else 3
    if alvo["soma_lo"] <= sm <= alvo["soma_hi"]:
        pts += 4
    elif 85 <= sm <= 145:
        pts += 1
    else:
        pts -= 2
    fx = _faixas(s)
    if fx in ((2, 2, 3), (2, 3, 2), (3, 2, 2), (3, 3, 1), (1, 3, 3)):
        pts += 3
    pts += min(6.0, 0.15 * sum(atrasos.get(n, 0) for n in s))
    return pts


def _rank_candidato(
    n: int,
    chosen: Sequence[int],
    *,
    pendentes: Set[int],
    ultimo_set: Set[int],
    alvo: Dict[str, Any],
    atrasos: Dict[int, int],
    freq20: Counter,
    persistentes: Set[int],
    max_pendentes: Optional[int] = None,
) -> float:
    trial = sorted(list(chosen) + [n])
    pts = _score_jogo(trial, ultimo_set=ultimo_set, alvo=alvo, atrasos=atrasos)
    ja_pend = sum(1 for x in chosen if x in pendentes)
    if n in pendentes:
        if max_pendentes is None or ja_pend < max_pendentes:
            pts += 8
        else:
            pts -= 2
    if n in persistentes:
        pts += 2
    if n in ultimo_set and alvo["rep_min"] <= 1:
        pts += 1.5
    # finais / sequência com o que já está
    if any(abs(n - c) == 1 for c in chosen):
        pts += 3
    if any(n % 10 == c % 10 for c in chosen):
        pts += 2.5
    # atraso alto vale (17, 23…), frequência recente baixa também
    pts += min(5.0, atrasos.get(n, 0) * 0.25)
    pts -= freq20.get(n, 0) * 0.15
    return pts


def _completar_aposta(
    locked: Sequence[int],
    *,
    k: int,
    dmin: int,
    dmax: int,
    pendentes: Sequence[int],
    ultimo_set: Set[int],
    alvo: Dict[str, Any],
    atrasos: Dict[int, int],
    freq20: Counter,
    persistentes: Set[int],
    rng: random.Random,
    max_pendentes: Optional[int] = None,
) -> List[int]:
    chosen = sorted({int(x) for x in locked})
    if len(chosen) > k:
        raise ValueError("Mais dezenas obrigatórias do que o tamanho da aposta.")
    pend_set = {int(x) for x in pendentes}
    universo = [n for n in range(dmin, dmax + 1) if n not in chosen]
    while len(chosen) < k and universo:
        ranked = sorted(
            universo,
            key=lambda n: (
                -_rank_candidato(
                    n,
                    chosen,
                    pendentes=pend_set,
                    ultimo_set=ultimo_set,
                    alvo=alvo,
                    atrasos=atrasos,
                    freq20=freq20,
                    persistentes=persistentes,
                    max_pendentes=max_pendentes,
                ),
                rng.random(),
            ),
        )
        pick = ranked[0]
        chosen.append(pick)
        chosen.sort()
        universo = [n for n in universo if n != pick]
    return sorted(chosen)[:k]


def _injetar_cobertura(
    apostas: List[List[int]],
    pendentes: Sequence[int],
    k: int,
) -> List[List[int]]:
    """Garante cobertura das pendentes sem mudar o padrão inicial da aposta."""
    cobertos: Set[int] = set()
    for a in apostas:
        cobertos.update(a)
    faltando = [n for n in pendentes if n not in cobertos]
    if not faltando:
        return apostas
    pend_set = {int(x) for x in pendentes}
    out = [list(a) for a in apostas]
    idx = 0
    for n in faltando:
        n = int(n)
        dig = n // 10
        for _t in range(len(out)):
            ap = out[idx % len(out)]
            idx += 1
            if n in ap:
                break
            mesmo_dig = [x for x in ap if x // 10 == dig and x not in pend_set]
            if not mesmo_dig:
                continue
            ap.remove(mesmo_dig[-1])
            ap.append(n)
            ap.sort()
            break
    return out


def gerar_apostas_de_contexto(
    *,
    pendentes: Sequence[int],
    linhas_basicas: Sequence[Dict[str, Any]],
    medias: Optional[Dict[str, Any]] = None,
    quantidade: int = 10,
    dezena_min: int = 1,
    dezena_max: int = 31,
    k: int = 7,
    rng: Optional[random.Random] = None,
    historico: Optional[Set[frozenset]] = None,
    catalogo_padroes: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    rng = rng or random.Random()
    dmin, dmax, k = int(dezena_min), int(dezena_max), int(k)
    pends = sorted({int(x) for x in pendentes if dmin <= int(x) <= dmax})
    hist = set(historico or [])
    qtd_pedida = max(1, min(200, int(quantidade or 10)))
    qtd = quantidade_minima(len(pends), k, qtd_pedida)
    catalogo = [p for p in list(catalogo_padroes or []) if _norm_padrao(p.get("padrao") or "")]
    if not catalogo:
        catalogo = _catalogo_padroes_fallback(linhas_basicas, k, dmin, dmax)

    ultimo = linhas_basicas[0] if linhas_basicas else None
    ultimo_nums = [int(x) for x in (ultimo or {}).get("numeros") or []]
    ultimo_set = set(ultimo_nums)
    alvo = _perfil_alvo(medias or {}, ultimo)
    atrasos = _atrasos(linhas_basicas, dmin, dmax)
    freq20 = _freq(linhas_basicas, 20)

    persistentes: Set[int] = set()
    if ultimo_nums:
        det = conjuntos_concurso(ultimo_nums, None)
        # 25 e 31 etc. não vêm daqui; usamos as do último como candidatas a repetir
        persistentes = set(ultimo_nums)

    locked_ref = list(pends) if 0 < len(pends) < k else []
    metas = [m for m in _escolher_padroes(catalogo, qtd, locked_ref, rng, pends) if _norm_padrao(m.get("padrao") or "")]
    reserva = [p for p in catalogo if _norm_padrao(p.get("padrao") or "") not in {
        _norm_padrao(m.get("padrao") or "") for m in metas
    }]
    if len(metas) < qtd:
        extras = _escolher_padroes(reserva or catalogo, qtd - len(metas), [], rng, pends)
        metas.extend(m for m in extras if _norm_padrao(m.get("padrao") or ""))
    metas = [m for m in metas if _norm_padrao(m.get("padrao") or "")]
    if not metas:
        metas = _catalogo_padroes_fallback(linhas_basicas, k, dmin, dmax)[:qtd]

    padroes_txt = [_norm_padrao(m.get("padrao") or "") for m in metas if _norm_padrao(m.get("padrao") or "")]
    blocos = _atribuir_pendentes(pends, padroes_txt, k)
    max_pend = None if 0 < len(pends) < k else max(1, k - 2)

    def _montar(locked, pad, proibidos):
        jogo = _completar_com_padrao(
            locked, pad, k=k, dmin=dmin, dmax=dmax, pendentes=pends,
            ultimo_set=ultimo_set, alvo=alvo, atrasos=atrasos, freq20=freq20,
            persistentes=persistentes, rng=rng, max_pendentes=max_pend,
            proibidos=proibidos,
        )
        if jogo and hist and frozenset(jogo) in hist:
            jogo = _completar_com_padrao(
                locked, pad, k=k, dmin=dmin, dmax=dmax, pendentes=pends,
                ultimo_set=ultimo_set, alvo=alvo, atrasos=atrasos, freq20=freq20,
                persistentes=persistentes, rng=rng, max_pendentes=max_pend,
                proibidos=proibidos | {tuple(jogo)},
            )
        return jogo

    jogos: List[List[int]] = []
    metas_usadas: List[Dict[str, Any]] = []
    vistos: Set[Tuple[int, ...]] = set()
    padroes_usados: Set[str] = set()
    fila_pad = list(range(len(metas)))
    extra_idx = 0
    while len(jogos) < qtd and fila_pad:
        i = fila_pad.pop(0)
        meta = dict(metas[i] if i < len(metas) else {})
        pad = _norm_padrao(meta.get("padrao") or "")
        if not pad or pad in padroes_usados:
            continue
        locked = list(blocos[i]) if i < len(blocos) else []
        if pad and locked and not _padrao_compativel(pad, locked):
            acc: List[int] = []
            for n in locked:
                if _padrao_compativel(pad, acc + [n]):
                    acc.append(n)
            locked = acc
        jogo = _montar(locked, pad, vistos)
        if not jogo or _padrao_de(jogo) != pad or tuple(jogo) in vistos:
            substitutos = [
                p for p in (reserva + catalogo)
                if _norm_padrao(p.get("padrao") or "") not in padroes_usados
                and _norm_padrao(p.get("padrao") or "") != pad
            ]
            if extra_idx < len(substitutos):
                metas.append(dict(substitutos[extra_idx]))
                padroes_txt.append(_norm_padrao(substitutos[extra_idx].get("padrao") or ""))
                blocos.append(_atribuir_pendentes(pends, padroes_txt[-1:], k)[0] if padroes_txt[-1] else [])
                fila_pad.append(len(metas) - 1)
                extra_idx += 1
            continue
        vistos.add(tuple(jogo))
        padroes_usados.add(pad)
        jogos.append(jogo)
        meta["padrao"] = pad
        meta["inedito"] = _eh_faltante(meta) or int(meta.get("frequencia") or 0) <= 0
        metas_usadas.append(meta)

    jogos = _injetar_cobertura(jogos, pends, k)

    vistos = set()
    for i, jogo in enumerate(jogos):
        pad = (metas_usadas[i].get("padrao") if i < len(metas_usadas) else "") or _padrao_de(jogo)
        if _padrao_de(jogo) != pad or tuple(jogo) in vistos or (hist and frozenset(jogo) in hist):
            locked = [n for n in jogo if n in pends and _padrao_compativel(pad, [n])]
            acc: List[int] = []
            for n in locked:
                if _padrao_compativel(pad, acc + [n]):
                    acc.append(n)
            novo = _montar(acc, pad, vistos)
            if novo and _padrao_de(novo) == pad and tuple(novo) not in vistos:
                jogos[i] = novo
                jogo = novo
        vistos.add(tuple(jogo))
        if i < len(metas_usadas):
            metas_usadas[i]["padrao"] = _padrao_de(jogos[i])

    union_pend = set()
    apostas_out: List[Dict[str, Any]] = []
    vistos_final: Set[Tuple[int, ...]] = set()
    for i, jogo in enumerate(jogos):
        pad_real = _padrao_de(jogo)
        key = tuple(jogo)
        if key in vistos_final:
            locked = [n for n in jogo if n in pends]
            acc = []
            for n in locked:
                if _padrao_compativel(pad_real, acc + [n]):
                    acc.append(n)
            for _t in range(16):
                cand = _montar(acc, pad_real, vistos_final)
                if cand and tuple(cand) not in vistos_final and _padrao_de(cand) == pad_real:
                    jogo = cand
                    key = tuple(jogo)
                    pad_real = _padrao_de(jogo)
                    break
        vistos_final.add(key)
        info_cat = next(
            (p for p in catalogo if _norm_padrao(p.get("padrao") or "") == pad_real),
            {},
        )
        freq_real = int(info_cat.get("frequencia") or 0)
        inedito = freq_real <= 0 or str(info_cat.get("status") or "") == "faltante"
        if i < len(metas_usadas) and metas_usadas[i].get("inedito"):
            inedito = True
        obr = sorted(n for n in jogo if n in pends)
        union_pend.update(obr)
        det = conjuntos_concurso(jogo, ultimo_nums or None)
        apostas_out.append({
            "dezenas": list(jogo),
            "obrigatorias": obr,
            "complemento": sorted(n for n in jogo if n not in pends),
            "pares": det["basicos"]["pares"]["quantidade"],
            "impares": det["basicos"]["impares"]["quantidade"],
            "repetidos": det["basicos"]["repetidos"]["dezenas"],
            "sequencias": det["basicos"]["sequencias"].get("detalhe", {}).get("grupos") or [],
            "finais": det["basicos"]["finais"].get("detalhe", {}).get("grupos") or [],
            "soma": det["soma"],
            "diagonais": _diagonais_da_aposta(jogo, dmin, dmax),
            "padrao_inicial": pad_real,
            "padrao_inedito": inedito,
            "padrao_freq": freq_real,
            "padrao_descricao": info_cat.get("descricao") or "",
        })

    if apostas_out and not any(a.get("padrao_inedito") for a in apostas_out):
        usados = {a["padrao_inicial"] for a in apostas_out}
        faltantes = [
            p for p in catalogo
            if _eh_faltante(p) and _norm_padrao(p.get("padrao") or "") not in usados
        ]
        if faltantes:
            alvo_p = _norm_padrao(rng.choice(faltantes).get("padrao") or "")
            idx = len(apostas_out) - 1
            acc = []
            for n in apostas_out[idx]["dezenas"]:
                if n in pends and _padrao_compativel(alvo_p, acc + [n]):
                    acc.append(n)
            novo = _montar(acc, alvo_p, {tuple(a["dezenas"]) for a in apostas_out})
            if novo and _padrao_de(novo) == alvo_p:
                det = conjuntos_concurso(novo, ultimo_nums or None)
                apostas_out[idx] = {
                    **apostas_out[idx],
                    "dezenas": list(novo),
                    "obrigatorias": sorted(n for n in novo if n in pends),
                    "complemento": sorted(n for n in novo if n not in pends),
                    "pares": det["basicos"]["pares"]["quantidade"],
                    "impares": det["basicos"]["impares"]["quantidade"],
                    "repetidos": det["basicos"]["repetidos"]["dezenas"],
                    "sequencias": det["basicos"]["sequencias"].get("detalhe", {}).get("grupos") or [],
                    "finais": det["basicos"]["finais"].get("detalhe", {}).get("grupos") or [],
                    "soma": det["soma"],
                    "diagonais": _diagonais_da_aposta(novo, dmin, dmax),
                    "padrao_inicial": alvo_p,
                    "padrao_inedito": True,
                    "padrao_freq": 0,
                    "padrao_descricao": next(
                        (p.get("descricao") or "" for p in faltantes if _norm_padrao(p.get("padrao") or "") == alvo_p),
                        "",
                    ),
                }
                union_pend = set()
                for a in apostas_out:
                    union_pend.update(a["obrigatorias"])

    cobertos = sorted(union_pend)
    faltou = [n for n in pends if n not in union_pend]
    pads = [a.get("padrao_inicial") for a in apostas_out]
    return {
        "sucesso": True,
        "apostas": apostas_out,
        "quantidade": len(apostas_out),
        "quantidade_solicitada": qtd_pedida,
        "quantidade_ajustada": qtd != qtd_pedida,
        "pendentes": pends,
        "pendentes_cobertos": cobertos,
        "pendentes_faltando": faltou,
        "todas_pendentes_no_lote": not faltou,
        "modo_ciclo": "todas_em_cada" if 0 < len(pends) < k else "cobertura_do_lote",
        "k": k,
        "dezena_min": dmin,
        "dezena_max": dmax,
        "ultimo_numeros": ultimo_nums,
        "alvo": alvo,
        "diagonais": _resumo_diagonais_janela(linhas_basicas, dmin, dmax),
        "padroes_usados": pads,
        "padroes_distintos": len(set(pads)),
        "padrao_inedito": next((a.get("padrao_inicial") for a in apostas_out if a.get("padrao_inedito")), None),
        "apostas_unicas": len({tuple(a["dezenas"]) for a in apostas_out}) == len(apostas_out),
    }
