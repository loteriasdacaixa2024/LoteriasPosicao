# -*- coding: utf-8 -*-
"""Geração sob a regra dura da ordem crescente (Excel): dezena × posição."""
from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple


def _padrao_inicial(nums: Sequence[int]) -> str:
    return " ".join(str(int(n) // 10) for n in sorted(int(x) for x in nums))


def _gaps(nums: Sequence[int]) -> List[int]:
    o = sorted(int(x) for x in nums)
    return [o[i + 1] - o[i] for i in range(len(o) - 1)]


def _n_sequencias(nums: Sequence[int]) -> int:
    o = sorted(int(x) for x in nums)
    n = 0
    i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and o[j + 1] - o[j] == 1:
            j += 1
        if j > i:
            n += 1
        i = j + 1
    return n


def _faixa_meio(k: int) -> Set[int]:
    return {k // 2, (k + 1) // 2}


def extrair_faixas(analise: Dict[str, Any]) -> Dict[str, Any]:
    posicoes = analise.get("posicoes") or []
    matriz = analise.get("matriz") or {}
    n = int(matriz.get("num_posicoes") or len(posicoes) or 0)
    vmin = int(matriz.get("valor_min") or 1)
    vmax = int(matriz.get("valor_max") or 31)
    universo = list(range(vmin, vmax + 1))
    allowed: List[List[int]] = [[] for _ in range(n)]
    freqs: List[Dict[int, int]] = [{} for _ in range(n)]
    minmax: List[Dict[str, Any]] = []
    vetos: List[List[int]] = [[] for _ in range(n)]

    linhas = {int(r["dezena"]): (r.get("contagens") or []) for r in (matriz.get("linhas") or [])}
    for i, p in enumerate(posicoes):
        fmap = {int(x["valor"]): int(x["freq"]) for x in (p.get("frequencias") or [])}
        freqs[i] = fmap
        permitidas = sorted(d for d, c in fmap.items() if c > 0)
        if not permitidas:
            permitidas = [d for d in universo if (linhas.get(d) or [0] * n)[i] > 0]
        allowed[i] = permitidas
        vetos[i] = [d for d in universo if d not in set(permitidas)]
        minmax.append({
            "pos": i + 1,
            "label": p.get("label") or f"P{i + 1}",
            "min": p.get("min"),
            "max": p.get("max"),
            "n_permitidas": len(permitidas),
            "n_vetadas": len(vetos[i]),
            "permitidas": permitidas,
            "vetadas": vetos[i],
        })

    return {
        "num_posicoes": n,
        "valor_min": vmin,
        "valor_max": vmax,
        "allowed": allowed,
        "freqs": freqs,
        "minmax": minmax,
        "vetos": vetos,
        "universo": universo,
        "total_concursos": (analise.get("universo") or {}).get("total"),
        "origem": analise.get("origem"),
        "modo": analise.get("modo") or "crescente",
    }


def respeita_veto(dezenas: Sequence[int], allowed: Sequence[Sequence[int]]) -> bool:
    o = sorted(int(x) for x in dezenas)
    n = min(len(o), len(allowed))
    for i in range(n):
        if o[i] not in set(allowed[i]):
            return False
    return True


def _peso(dez: int, pos_idx: int, ctx: Dict[str, Any], extras: Dict[str, Any]) -> float:
    w = 1.0 + math.sqrt(float((ctx["freqs"][pos_idx] or {}).get(dez, 0)))
    if extras.get("ciclo") and dez in extras["ciclo"]:
        w += 18
    if extras.get("ultimo") and dez in extras["ultimo"]:
        w += 8
    if extras.get("gaps_pref") and dez in extras["gaps_pref"]:
        w += 6
    if extras.get("usar_pares") and dez % 2 == 0:
        w += 3
    if extras.get("usar_impares") and dez % 2 == 1:
        w += 3
    sets = extras.get("conjuntos") or {}
    if extras.get("usar_primos") and dez in sets.get("primos", set()):
        w += 4
    if extras.get("usar_moldura") and dez in sets.get("moldura", set()):
        w += 3
    if extras.get("usar_m3") and dez in sets.get("m3", set()):
        w += 3
    if extras.get("usar_fb") and dez in sets.get("fb", set()):
        w += 3
    return w


def _nucleo_crescente(ctx: Dict[str, Any], k_official: int, extras: Dict[str, Any], rng: random.Random) -> Optional[List[int]]:
    allowed = ctx["allowed"]
    picks: List[int] = []

    def bt(i: int) -> bool:
        if i == k_official:
            return True
        prev = picks[-1] if picks else ctx["valor_min"] - 1
        pool = [d for d in allowed[i] if d > prev and d not in picks]
        if not pool:
            return False
        pesos = [_peso(d, i, ctx, extras) for d in pool]
        escolhidos = []
        restante = pool[:]
        rest_w = pesos[:]
        n_try = min(10, len(restante))
        for _ in range(n_try):
            total = sum(rest_w)
            if total <= 0 or not restante:
                break
            x = rng.random() * total
            acc = 0.0
            idx = 0
            for j, p in enumerate(rest_w):
                acc += p
                if x <= acc:
                    idx = j
                    break
            escolhidos.append(restante.pop(idx))
            rest_w.pop(idx)
        for d in escolhidos + restante:
            picks.append(d)
            if bt(i + 1):
                return True
            picks.pop()
        return False

    if bt(0):
        return list(picks)
    return None


def _score(
    dz: List[int],
    extras: Dict[str, Any],
    soma_lo: Optional[int],
    soma_hi: Optional[int],
) -> Tuple[int, List[str]]:
    notas: List[str] = []
    score = 0
    s = sum(dz)
    if extras.get("usar_ciclo"):
        n = len(set(dz) & extras.get("ciclo", set()))
        score += n * 10
        notas.append(f"Ciclo: {n} pendente(s)")
    if extras.get("usar_soma") and soma_lo is not None and soma_hi is not None:
        ok = soma_lo <= s <= soma_hi
        score += 8 if ok else -4
        notas.append(f"Soma {s} ({'ok' if ok else 'fora'} {soma_lo}–{soma_hi})")
    if extras.get("usar_repeticao"):
        ult = extras.get("ultimo") or set()
        n = len(set(dz) & ult)
        if n in (1, 2):
            score += 8
        else:
            score -= 3
        notas.append(f"Rep.: {n}")
    if extras.get("usar_padrao"):
        pad = _padrao_inicial(dz)
        alvo = extras.get("padrao_alvo") or ""
        ok = bool(alvo) and pad == alvo
        if ok:
            score += 10
        notas.append(f"Padrão {pad}" + (" · último" if ok else ""))
    if extras.get("usar_gap"):
        g = _gaps(dz)
        moda = extras.get("gaps_moda") or []
        hits = 0
        for i, v in enumerate(g):
            if i < len(moda) and moda[i] is not None and v == moda[i]:
                hits += 1
        if moda:
            score += hits * 4
            notas.append(f"Gaps: {hits}/{len(moda)} no moda")
    k = len(dz)
    meio = _faixa_meio(k)
    pares = sum(1 for n in dz if n % 2 == 0)
    impares = k - pares
    sets = extras.get("conjuntos") or {}
    if extras.get("usar_pares"):
        ok = pares in meio
        score += 6 if ok else -2
        notas.append(f"{pares}P")
    if extras.get("usar_impares"):
        ok = impares in meio
        score += 6 if ok else -2
        notas.append(f"{impares}I")
    if extras.get("usar_primos"):
        n = sum(1 for d in dz if d in sets.get("primos", set()))
        ok = 2 <= n <= max(3, k // 3 + 1)
        score += 5 if ok else -1
        notas.append(f"{n} primos")
    if extras.get("usar_moldura"):
        n = sum(1 for d in dz if d in sets.get("moldura", set()))
        ok = n >= 2
        score += 5 if ok else -1
        notas.append(f"{n} moldura")
    if extras.get("usar_seq"):
        n = _n_sequencias(dz)
        ok = 1 <= n <= 2
        score += 6 if ok else -2
        notas.append(f"Seq {n}")
    if extras.get("usar_m3"):
        n = sum(1 for d in dz if d in sets.get("m3", set()))
        ok = 2 <= n <= 4
        score += 4 if ok else -1
        notas.append(f"{n}×3")
    if extras.get("usar_fb"):
        n = sum(1 for d in dz if d in sets.get("fb", set()))
        ok = 1 <= n <= 3
        score += 4 if ok else -1
        notas.append(f"{n} Fib")
    if extras.get("usar_finais"):
        fins: Dict[int, int] = {}
        for d in dz:
            f = d % 10
            fins[f] = fins.get(f, 0) + 1
        grupos = [f for f, q in fins.items() if q >= 2]
        ok = len(grupos) >= 1
        score += 7 if ok else -2
        notas.append("Finais " + (",".join(str(x) for x in grupos) if grupos else "distintos"))
    return score, notas


def contexto_api(modality_key: str) -> Dict[str, Any]:
    from filtros_posicao.service import analisar

    raw = analisar(modality_key, modo="crescente")
    if not raw.get("sucesso"):
        return raw
    faixas = extrair_faixas(raw)
    univ = raw.get("universo") or {}
    return {
        "sucesso": True,
        "modo": "crescente",
        "origem": raw.get("origem"),
        "universo": univ,
        "minmax": faixas["minmax"],
        "num_posicoes": faixas["num_posicoes"],
        "valor_min": faixas["valor_min"],
        "valor_max": faixas["valor_max"],
        "regra": (
            "Regra dura (ordem crescente / Excel): depois de ordenar a aposta, "
            "a dezena da posição N só pode ser uma que já saiu nessa coluna. "
            "Zero histórico = proibida."
        ),
        "link_analise": "/dados/filtros-posicao/",
    }


def gerar(
    modality_key: str,
    *,
    quantidade: int = 10,
    dezenas_por_jogo: int = 7,
    usar_ciclo: bool = False,
    usar_soma: bool = False,
    usar_repeticao: bool = False,
    usar_padrao: bool = False,
    usar_gap: bool = False,
    usar_pares: bool = False,
    usar_impares: bool = False,
    usar_primos: bool = False,
    usar_moldura: bool = False,
    usar_seq: bool = False,
    usar_m3: bool = False,
    usar_fb: bool = False,
    usar_finais: bool = False,
    conjuntos: Optional[Dict[str, Set[int]]] = None,
    ciclo_pendentes: Optional[Sequence[int]] = None,
    soma_lo: Optional[int] = None,
    soma_hi: Optional[int] = None,
    soma_media: Optional[float] = None,
    ultimo: Optional[Dict[str, Any]] = None,
    gaps_moda: Optional[Sequence[Optional[int]]] = None,
    gaps_pref: Optional[Sequence[int]] = None,
) -> Dict[str, Any]:
    from filtros_posicao.service import analisar

    raw = analisar(modality_key, modo="crescente")
    if not raw.get("sucesso"):
        return raw
    ctx = extrair_faixas(raw)
    n_pos = ctx["num_posicoes"]
    if n_pos < 2:
        return {"sucesso": False, "erro": "Sem posições na matriz crescente."}

    k = max(n_pos, min(int(dezenas_por_jogo), n_pos + 8))
    k_official = min(k, n_pos)
    qtd = max(1, min(int(quantidade), 80))
    rng = random.Random()

    ult_dz = [int(x) for x in ((ultimo or {}).get("dezenas") or [])]
    extras = {
        "usar_ciclo": usar_ciclo,
        "usar_soma": usar_soma,
        "usar_repeticao": usar_repeticao,
        "usar_padrao": usar_padrao,
        "usar_gap": usar_gap,
        "usar_pares": usar_pares,
        "usar_impares": usar_impares,
        "usar_primos": usar_primos,
        "usar_moldura": usar_moldura,
        "usar_seq": usar_seq,
        "usar_m3": usar_m3,
        "usar_fb": usar_fb,
        "usar_finais": usar_finais,
        "conjuntos": conjuntos or {},
        "ciclo": set(int(x) for x in (ciclo_pendentes or [])),
        "ultimo": set(ult_dz),
        "padrao_alvo": _padrao_inicial(ult_dz) if ult_dz else "",
        "gaps_moda": list(gaps_moda or []),
        "gaps_pref": set(int(x) for x in (gaps_pref or [])),
    }

    vistos: Set[Tuple[int, ...]] = set()
    candidatas: List[Tuple[int, Dict[str, Any]]] = []
    tentativas = 0
    teto = max(qtd * 40, 80)
    while len(vistos) < qtd * 6 and tentativas < teto:
        tentativas += 1
        nucleo = _nucleo_crescente(ctx, k_official, extras, rng)
        if not nucleo:
            continue
        jogo = list(nucleo)
        if k > k_official:
            resto = [d for d in ctx["universo"] if d not in jogo]
            rng.shuffle(resto)
            resto.sort(key=lambda d: -(_peso(d, min(k_official - 1, n_pos - 1), ctx, extras) + rng.random()))
            jogo.extend(resto[: k - k_official])
        jogo = sorted(set(jogo))
        if len(jogo) < k_official:
            continue
        if not respeita_veto(jogo[:k_official], ctx["allowed"]):
            continue
        key = tuple(jogo)
        if key in vistos:
            continue
        vistos.add(key)
        sc, notas = _score(jogo, extras, soma_lo, soma_hi)
        pos_txt = " · ".join(
            f"P{i + 1}={jogo[i]:02d}" for i in range(k_official)
        )
        candidatas.append((sc, {
            "dezenas": jogo,
            "dezenas_nucleo": jogo[:k_official],
            "posicoes": [
                {"pos": i + 1, "dezena": jogo[i], "permitida": True}
                for i in range(k_official)
            ],
            "criterios": [f"Veto crescente: {pos_txt}"] + notas,
            "soma": sum(jogo),
            "padrao_inicial": _padrao_inicial(jogo),
            "modo_motor_aposta": "faixas_crescente",
        }))

    candidatas.sort(key=lambda x: (-x[0], x[1]["dezenas"]))
    apostas = []
    for i, (_, ap) in enumerate(candidatas[:qtd], start=1):
        apostas.append({**ap, "numero": i})

    if not apostas:
        return {
            "sucesso": False,
            "erro": "Não foi possível montar apostas que respeitem o veto crescente.",
        }

    criterios = [
        "Regra dura: ordem crescente (Excel) — dezena × posição",
        f"{ctx['num_posicoes']} posições · {ctx.get('total_concursos') or '—'} concursos",
    ]
    if usar_ciclo:
        criterios.append(f"Ciclo: {len(extras['ciclo'])} pendente(s)")
    if usar_soma and soma_lo is not None:
        criterios.append(f"Soma: {soma_lo}–{soma_hi}" + (f" (média {int(soma_media)})" if soma_media else ""))
    if usar_repeticao:
        nult = (ultimo or {}).get("concurso") or "—"
        criterios.append(f"Repetição vs #{nult} (preferir 1–2)")
    if usar_padrao and extras["padrao_alvo"]:
        criterios.append(f"Padrão alvo: {extras['padrao_alvo']}")
    if usar_gap:
        criterios.append("Gaps: preferir moda histórica")
    if usar_pares:
        criterios.append("Pares")
    if usar_impares:
        criterios.append("Ímpares")
    if usar_primos:
        criterios.append("Primos")
    if usar_moldura:
        criterios.append("Moldura")
    if usar_seq:
        criterios.append("Sequências")
    if usar_m3:
        criterios.append("Múltiplos de 3")
    if usar_fb:
        criterios.append("Fibonacci")
    if usar_finais:
        criterios.append("Finais iguais")

    return {
        "sucesso": True,
        "apostas": apostas,
        "total_geradas": len(apostas),
        "solicitados": qtd,
        "modo_geracao": "faixas_crescente",
        "modo_motor": "faixas_crescente",
        "modo_motor_label": "Posição crescente (Excel)",
        "criterios_modo_auto": criterios,
        "minmax": ctx["minmax"],
        "regra": (
            "Cada aposta é ordenada. A 1ª dezena só usa o que já saiu na 1ª coluna do Excel; "
            "a 2ª, só o da 2ª coluna; e assim por diante. Zero = proibida."
        ),
        "link_analise": "/dados/filtros-posicao/",
        "universo": raw.get("universo"),
        "aviso": None if len(apostas) >= qtd else f"Geradas {len(apostas)} de {qtd} apostas válidas no veto.",
    }
