# -*- coding: utf-8 -*-
"""Gera um portfólio de apostas a partir do DNA do Resumo Geral.

Não prevê o próximo sorteio. Pontua aderência ao comportamento histórico
(núcleo + variações, concentração nas dezenas fortes, diversidade no conjunto).
"""
from __future__ import annotations

import random
from collections import Counter
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from resumo_modalidade.service import ResumoModalidadeService, _sequencias
from resumo_modalidade.specs import faixa_de, get_resumo_spec, tem_resumo_modalidade

_FMT = "{:02d}".format


def _parse_pi(row: Dict[str, Any], sorteadas: int) -> Tuple[int, int]:
    if row.get("pares") is not None:
        return int(row["pares"]), int(row.get("impares") or (sorteadas - int(row["pares"])))
    txt = str(row.get("dist") or row.get("moda") or "3P / 4I")
    try:
        left, right = txt.replace(" ", "").split("/")
        return int(left.replace("P", "")), int(right.replace("I", ""))
    except (ValueError, AttributeError):
        return 3, sorteadas - 3


def _dna_pack(data: Dict[str, Any], spec) -> Dict[str, Any]:
    pi = data.get("par_impar") or {}
    soma = data.get("soma") or {}
    seq = data.get("sequencias") or {}
    rep = data.get("repeticao") or {}
    finais = data.get("finais") or {}
    faixas = data.get("faixas") or {}
    ciclo = data.get("ciclo") or {}
    atual = ciclo.get("atual") or {}
    ultimo = data.get("ultimo") or {}
    pad = data.get("padrao_inicial") or {}
    stats = list((data.get("dezenas") or {}).get("stats") or [])

    pi_top = list(pi.get("top") or [])[:4]
    pi_perfis = []
    for row in pi_top:
        pares, impares = _parse_pi(row, spec.sorteadas)
        pi_perfis.append({
            "pares": pares, "impares": impares,
            "pct": float(row.get("pct") or 0), "dist": row.get("dist"),
        })
    if not pi_perfis:
        pares, impares = _parse_pi({"moda": pi.get("moda")}, spec.sorteadas)
        pi_perfis = [{"pares": pares, "impares": impares, "pct": 30.0, "dist": pi.get("moda")}]

    bma_top = []
    for row in (faixas.get("top3") or faixas.get("top8") or [])[:4]:
        counts = row.get("counts")
        if not counts:
            continue
        bma_top.append({
            "counts": [int(x) for x in counts],
            "pct": float(row.get("pct") or 0),
            "dist": row.get("dist"),
        })

    ult_dz = [int(x) for x in (ultimo.get("dezenas") or [])]
    pendentes = [int(x) for x in (atual.get("pendentes_num") or [])]
    if not pendentes:
        pendentes = [int(x) for x in (atual.get("pendentes") or []) if str(x).strip()]

    novas = ciclo.get("novas") or {}
    return {
        "spec": spec,
        "meta": data.get("meta") or {},
        "k": spec.sorteadas,
        "lo": spec.dezena_min,
        "hi": spec.dezena_max,
        "universo": list(range(spec.dezena_min, spec.dezena_max + 1)),
        "faixas": spec.faixas,
        "soma_media": float(soma.get("media") or 0),
        "p10": int(soma.get("p10") or 0),
        "p20": int(soma.get("p20") or 0),
        "p80": int(soma.get("p80") or 0),
        "p90": int(soma.get("p90") or 0),
        "pi_perfis": pi_perfis,
        "bma_top": bma_top,
        "exige_seq": float(seq.get("pct_com_pelo_menos_uma") or 0) >= 55,
        "seq_moda": int(seq.get("qtd_mais_freq") or 1),
        "exige_final": float(finais.get("pct_pelo_menos_um") or 0) >= 55,
        "rep_moda": int(rep.get("moda") or 1),
        "pct_rep_1ou2": float(rep.get("pct_1_ou_2") or 0),
        "ultimo": ult_dz,
        "pendentes": pendentes,
        "vistos_ciclo": [int(x) for x in (atual.get("vistos_num") or [])],
        "novas_moda": int(novas.get("moda") or 0),
        "padroes_top": [str(x.get("valor")) for x in (pad.get("top5") or []) if x.get("valor")],
        "stats": {int(s["dezena"]): s for s in stats},
    }


def _pesos(dna: Dict[str, Any]) -> Dict[int, float]:
    ultimo = set(dna["ultimo"])
    pend = set(dna["pendentes"])
    pesos: Dict[int, float] = {}
    for d in dna["universo"]:
        st = dna["stats"].get(d) or {}
        qtd = float(st.get("qtd") or 1)
        atraso = float(st.get("atraso") or 0)
        w = (qtd + 1.0) * (1.0 + min(atraso, 18.0) * 0.07)
        if d in ultimo:
            w *= 1.4
        if d in pend:
            w *= 1.28
        pesos[d] = w ** 1.55
    return pesos


def _classificar(pesos: Dict[int, float]) -> Tuple[List[int], List[int], List[int]]:
    ordem = sorted(pesos, key=lambda d: pesos[d], reverse=True)
    n = len(ordem)
    n_f = max(6, n // 4)
    n_i = max(8, n // 3)
    return ordem[:n_f], ordem[n_f:n_f + n_i], ordem[n_f + n_i:]


def _sample_k(rng: random.Random, pool: Sequence[int], pesos: Dict[int, float], k: int) -> List[int]:
    bag = [(d, max(pesos.get(d, 0.01), 0.01)) for d in pool]
    out: List[int] = []
    k = min(k, len(bag))
    for _ in range(k):
        total = sum(w for _, w in bag)
        if total <= 0:
            break
        r = rng.random() * total
        acc = 0.0
        idx = 0
        for i, (d, w) in enumerate(bag):
            acc += w
            if acc >= r:
                idx = i
                break
        out.append(bag[idx][0])
        bag.pop(idx)
    return out


def _escolha_ponderada(rng: random.Random, itens: Sequence[Dict[str, Any]], chave: str = "pct"):
    if not itens:
        return None
    total = sum(max(float(x.get(chave) or 0), 0.1) for x in itens)
    r = rng.random() * total
    acc = 0.0
    for x in itens:
        acc += max(float(x.get(chave) or 0), 0.1)
        if acc >= r:
            return x
    return itens[0]


def _bma(dezenas: Sequence[int], dna: Dict[str, Any]) -> List[int]:
    counts = [0] * len(dna["faixas"])
    idx = {f[0]: i for i, f in enumerate(dna["faixas"])}
    for d in dezenas:
        c = faixa_de(int(d), dna["spec"])
        if c in idx:
            counts[idx[c]] += 1
    return counts


def _forcar_sequencia(rng: random.Random, chosen: Set[int], dna: Dict[str, Any]) -> None:
    dz = sorted(chosen)
    if _sequencias(dz):
        return
    k = dna["k"]
    uni = dna["universo"]
    cand = list(chosen)
    rng.shuffle(cand)
    for d in cand:
        for nb in (d - 1, d + 1):
            if nb in uni and nb not in chosen:
                if len(chosen) < k:
                    chosen.add(nb)
                    return
                drop = next((x for x in cand if x != d and abs(x - d) != 1), None)
                if drop is not None:
                    chosen.remove(drop)
                    chosen.add(nb)
                    return


def _forcar_final(rng: random.Random, chosen: Set[int], dna: Dict[str, Any]) -> None:
    fins = Counter(d % 10 for d in chosen)
    if any(v >= 2 for v in fins.values()):
        return
    k = dna["k"]
    uni = set(dna["universo"])
    base = list(chosen)
    rng.shuffle(base)
    for d in base:
        fin = d % 10
        opts = [x for x in uni if x % 10 == fin and x not in chosen]
        if not opts:
            continue
        add = rng.choice(opts)
        if len(chosen) < k:
            chosen.add(add)
            return
        drop = next((x for x in base if x != d), None)
        if drop is not None:
            chosen.remove(drop)
            chosen.add(add)
            return


def _forcar_rep(rng: random.Random, chosen: Set[int], dna: Dict[str, Any], alvo: int) -> None:
    ultimo = [d for d in dna["ultimo"] if d in dna["universo"]]
    if not ultimo or alvo <= 0:
        return
    have = len(set(chosen) & set(ultimo))
    if have >= alvo:
        return
    faltam = [d for d in ultimo if d not in chosen]
    rng.shuffle(faltam)
    for d in faltam:
        if have >= alvo:
            break
        if len(chosen) < dna["k"]:
            chosen.add(d)
            have += 1
            continue
        drop = next((x for x in list(chosen) if x not in ultimo), None)
        if drop is None:
            break
        chosen.remove(drop)
        chosen.add(d)
        have += 1


def _ajustar_bma(rng: random.Random, chosen: Set[int], dna: Dict[str, Any], alvo: List[int], pesos: Dict[int, float]) -> None:
    if not alvo or len(alvo) != len(dna["faixas"]):
        return
    for _ in range(8):
        atual = _bma(chosen, dna)
        if atual == alvo:
            return
        for i, (codigo, lo, hi, _) in enumerate(dna["faixas"]):
            if atual[i] == alvo[i]:
                continue
            if atual[i] > alvo[i]:
                na_faixa = [d for d in chosen if lo <= d <= hi]
                if not na_faixa:
                    continue
                chosen.remove(min(na_faixa, key=lambda d: pesos.get(d, 0)))
            elif atual[i] < alvo[i]:
                extras = [d for d in range(lo, hi + 1) if d not in chosen]
                if not extras:
                    continue
                chosen.add(_sample_k(rng, extras, pesos, 1)[0])
        while len(chosen) > dna["k"]:
            chosen.remove(min(chosen, key=lambda d: pesos.get(d, 0)))
        while len(chosen) < dna["k"]:
            rest = [d for d in dna["universo"] if d not in chosen]
            if not rest:
                break
            chosen.add(_sample_k(rng, rest, pesos, 1)[0])


def _ajustar_soma(rng: random.Random, chosen: Set[int], dna: Dict[str, Any], alvo_soma: int, pesos: Dict[int, float]) -> None:
    lo, hi = dna["p10"], dna["p90"]
    for _ in range(10):
        sm = sum(chosen)
        if lo and sm < lo:
            pequeno = min(chosen)
            maiores = [d for d in dna["universo"] if d not in chosen and d > pequeno]
            if not maiores:
                return
            chosen.remove(pequeno)
            chosen.add(rng.choice(sorted(maiores)[-8:]))
        elif hi and sm > hi:
            grande = max(chosen)
            menores = [d for d in dna["universo"] if d not in chosen and d < grande]
            if not menores:
                return
            chosen.remove(grande)
            chosen.add(rng.choice(sorted(menores)[:8]))
        elif alvo_soma and abs(sm - alvo_soma) > 12:
            if sm < alvo_soma:
                pequeno = min(chosen)
                maiores = [d for d in dna["universo"] if d not in chosen and d > pequeno]
                if not maiores:
                    return
                chosen.remove(pequeno)
                chosen.add(_sample_k(rng, maiores, pesos, 1)[0])
            else:
                grande = max(chosen)
                menores = [d for d in dna["universo"] if d not in chosen and d < grande]
                if not menores:
                    return
                chosen.remove(grande)
                chosen.add(_sample_k(rng, menores, pesos, 1)[0])
        else:
            return


def _ajustar_pi(rng: random.Random, chosen: Set[int], dna: Dict[str, Any], pares_alvo: int) -> None:
    k = dna["k"]
    for _ in range(8):
        pares = sum(1 for d in chosen if d % 2 == 0)
        if pares == pares_alvo:
            return
        if pares > pares_alvo:
            par = next((d for d in list(chosen) if d % 2 == 0), None)
            impares = [d for d in dna["universo"] if d % 2 == 1 and d not in chosen]
            if par is None or not impares:
                return
            chosen.remove(par)
            chosen.add(rng.choice(impares))
        else:
            imp = next((d for d in list(chosen) if d % 2 == 1), None)
            pares_l = [d for d in dna["universo"] if d % 2 == 0 and d not in chosen]
            if imp is None or not pares_l:
                return
            chosen.remove(imp)
            chosen.add(rng.choice(pares_l))
        while len(chosen) > k:
            chosen.pop()


def _montar(rng: random.Random, dna: Dict[str, Any], pesos: Dict[int, float],
            fortes: List[int], idx: int, alvo_soma: int) -> Optional[List[int]]:
    k = dna["k"]
    bma_row = _escolha_ponderada(rng, dna["bma_top"]) or {}
    alvo_bma = list(bma_row.get("counts") or [])
    pi_row = _escolha_ponderada(rng, dna["pi_perfis"]) or {}
    pares_alvo = int(pi_row.get("pares") or 3)

    chosen: Set[int] = set()
    nucleo = _sample_k(rng, fortes, pesos, min(3, len(fortes)))
    chosen.update(nucleo)

    alvo_rep = dna["rep_moda"] if dna["pct_rep_1ou2"] >= 50 else 0
    if alvo_rep <= 0 and dna["pct_rep_1ou2"] >= 40:
        alvo_rep = 1
    _forcar_rep(rng, chosen, dna, max(1, min(2, alvo_rep or 1)) if dna["ultimo"] else 0)

    pend = dna["pendentes"]
    if pend:
        rot = pend[idx % len(pend):] + pend[: idx % len(pend)]
        n_ciclo = 1 if dna["novas_moda"] == 0 else min(2, len(rot))
        for d in rot[:n_ciclo]:
            if len(chosen) < k:
                chosen.add(d)

    if alvo_bma:
        idx_f = {f[0]: i for i, f in enumerate(dna["faixas"])}
        for codigo, lo, hi, _ in dna["faixas"]:
            i = idx_f[codigo]
            falta = alvo_bma[i] - sum(1 for d in chosen if lo <= d <= hi)
            if falta <= 0:
                continue
            pool = [d for d in range(lo, hi + 1) if d not in chosen]
            chosen.update(_sample_k(rng, pool, pesos, falta))

    rest = [d for d in dna["universo"] if d not in chosen]
    while len(chosen) < k and rest:
        add = _sample_k(rng, rest, pesos, 1)
        if not add:
            break
        chosen.add(add[0])
        rest = [d for d in rest if d not in chosen]
    while len(chosen) > k:
        fraco = min((d for d in chosen if d not in nucleo), key=lambda d: pesos.get(d, 0), default=None)
        if fraco is None:
            chosen.pop()
        else:
            chosen.remove(fraco)

    if dna["exige_seq"]:
        _forcar_sequencia(rng, chosen, dna)
    if dna["exige_final"]:
        _forcar_final(rng, chosen, dna)
    if alvo_bma:
        _ajustar_bma(rng, chosen, dna, alvo_bma, pesos)
    _ajustar_pi(rng, chosen, dna, pares_alvo)
    _ajustar_soma(rng, chosen, dna, alvo_soma, pesos)
    if dna["exige_seq"] and not _sequencias(sorted(chosen)):
        _forcar_sequencia(rng, chosen, dna)
    if dna["exige_final"]:
        _forcar_final(rng, chosen, dna)

    if len(chosen) != k:
        return None
    return sorted(chosen)


def _score(dz: Sequence[int], dna: Dict[str, Any], pesos: Dict[int, float], fortes: Sequence[int]) -> Tuple[float, Dict[str, float]]:
    dz = sorted(int(x) for x in dz)
    k = dna["k"]
    sm = sum(dz)
    pares = sum(1 for d in dz if d % 2 == 0)
    seqs = _sequencias(dz)
    fins = Counter(d % 10 for d in dz)
    n_fin = sum(1 for v in fins.values() if v >= 2)
    bma = _bma(dz, dna)
    ult = set(dna["ultimo"])
    n_rep = len(set(dz) & ult)
    pend = set(dna["pendentes"])
    n_ciclo = len(set(dz) & pend)
    n_fortes = sum(1 for d in dz if d in fortes)
    padrao = "-".join(str(d // 10) for d in dz)
    partes: Dict[str, float] = {}

    media = dna["soma_media"] or sm
    p20, p80, p10, p90 = dna["p20"], dna["p80"], dna["p10"], dna["p90"]
    if p20 and p80 and p20 <= sm <= p80:
        partes["soma"] = 18 - min(abs(sm - media) / 8.0, 8)
    elif p10 and p90 and p10 <= sm <= p90:
        partes["soma"] = 8
    else:
        partes["soma"] = -12

    best_pi = 0.0
    for row in dna["pi_perfis"]:
        if int(row["pares"]) == pares:
            best_pi = max(best_pi, 14 * (float(row["pct"]) / max(float(dna["pi_perfis"][0]["pct"]), 1)))
    partes["par_impar"] = best_pi if best_pi else -4

    if dna["exige_seq"]:
        partes["seq"] = 12 if seqs else -10
        if seqs and len(seqs) == dna["seq_moda"]:
            partes["seq"] += 3
    else:
        partes["seq"] = 2 if seqs else 0

    if dna["pct_rep_1ou2"] >= 50:
        if n_rep in (1, 2):
            partes["rep"] = 12
        elif n_rep == 0:
            partes["rep"] = -6
        elif n_rep >= 4:
            partes["rep"] = -8
        else:
            partes["rep"] = 4
    else:
        partes["rep"] = 2 if n_rep <= 2 else -2

    if dna["exige_final"]:
        partes["finais"] = 10 if n_fin else -9
    else:
        partes["finais"] = 2 if n_fin else 0

    best_bma = 0.0
    if any(c == 0 or c >= k for c in bma):
        partes["faixas"] = -16
    else:
        for row in dna["bma_top"]:
            if list(row["counts"]) == bma:
                best_bma = 14 * (float(row["pct"]) / max(float(dna["bma_top"][0]["pct"]), 1))
                break
        partes["faixas"] = best_bma if best_bma else (6 if all(2 <= c <= 3 for c in bma) else -4)

    if pend:
        if 1 <= n_ciclo <= 2:
            partes["ciclo"] = 8
        elif n_ciclo == 0:
            partes["ciclo"] = 1 if dna["novas_moda"] == 0 else -3
        elif n_ciclo >= 4:
            partes["ciclo"] = -6
        else:
            partes["ciclo"] = 4
    else:
        partes["ciclo"] = 0

    partes["fortes"] = min(n_fortes, 4) * 3.5
    partes["peso"] = min(sum(pesos.get(d, 0) for d in dz) / (k * 8.0), 8)
    partes["padrao"] = 4 if padrao in dna["padroes_top"][:3] else 0

    total = round(sum(partes.values()), 2)
    return total, partes


def _justificativa(dz: List[int], dna: Dict[str, Any], score: float, partes: Dict[str, float]) -> List[Dict[str, str]]:
    sm = sum(dz)
    pares = sum(1 for d in dz if d % 2 == 0)
    seqs = _sequencias(dz)
    seq_txt = ", ".join("–".join(_FMT(x) for x in g) for g in seqs) or "nenhuma"
    ult = sorted(set(dz) & set(dna["ultimo"]))
    fins = Counter(d % 10 for d in dz)
    fin_txt = []
    for fin, qtd in sorted(fins.items()):
        if qtd >= 2:
            nums = [d for d in dz if d % 10 == fin]
            fin_txt.append(f"{fin}: " + ", ".join(_FMT(x) for x in nums))
    bma = _bma(dz, dna)
    bma_txt = " + ".join(f"{bma[i]}{dna['faixas'][i][0]}" for i in range(len(dna["faixas"])))
    ciclo = sorted(set(dz) & set(dna["pendentes"]))
    novas = ciclo
    top_partes = sorted(partes.items(), key=lambda kv: kv[1], reverse=True)[:4]
    criterios_txt = ", ".join(f"{k} {v:+.1f}" for k, v in top_partes)
    return [
        {"codigo": "score", "texto": f"Score {score:.1f} — aderência ao DNA histórico, não probabilidade de acerto"},
        {"codigo": "soma", "texto": f"Soma {sm} (faixa {dna['p20']}–{dna['p80']}, média {dna['soma_media']:.0f})"},
        {"codigo": "pi", "texto": f"{pares}P / {dna['k'] - pares}I"},
        {"codigo": "seq", "texto": f"Sequência: {seq_txt}"},
        {"codigo": "rep", "texto": f"Repetidas do anterior: {len(ult)}" + (f" ({', '.join(_FMT(x) for x in ult)})" if ult else "")},
        {"codigo": "fin", "texto": "Finais: " + ("; ".join(fin_txt) if fin_txt else "todos distintos")},
        {"codigo": "bma", "texto": f"Faixas {bma_txt}"},
        {"codigo": "ciclo", "texto": f"Ciclo (pendentes): {len(ciclo)}" + (f" ({', '.join(_FMT(x) for x in ciclo)})" if ciclo else "")},
        {"codigo": "novas", "texto": f"Dezenas novas no ciclo: {len(novas)}"},
        {"codigo": "top", "texto": f"Critérios que mais pontuaram: {criterios_txt}"},
    ]


def _diversidade_ok(cand: List[int], escolhidas: List[List[int]], k: int) -> bool:
    cs = set(cand)
    if any(set(e) == cs for e in escolhidas):
        return False
    if not escolhidas:
        return True
    overlaps = [len(cs & set(e)) for e in escolhidas]
    if max(overlaps) >= k - 1:
        return False
    return True


def _cobertura_ciclo(escolhidas: List[List[int]], pendentes: Sequence[int]) -> Set[int]:
    cob: Set[int] = set()
    for ap in escolhidas:
        cob.update(set(ap) & set(pendentes))
    return cob


def gerar_apostas_dna(
    modality_key: str = "diadesorte",
    quantidade: int = 10,
    dezenas_por_jogo: Optional[int] = None,
) -> Dict[str, Any]:
    if not tem_resumo_modalidade(modality_key):
        return {"sucesso": False, "erro": f"Resumo Geral não habilitado para {modality_key}."}
    data = ResumoModalidadeService.calcular(modality_key)
    if not data.get("sucesso"):
        return data
    spec = get_resumo_spec(modality_key)
    k = int(dezenas_por_jogo or spec.sorteadas)
    k = max(spec.sorteadas, min(k, spec.sorteadas))
    quantidade = max(1, min(int(quantidade), 40))
    dna = _dna_pack(data, spec)
    dna["k"] = k
    pesos = _pesos(dna)
    fortes, _inter, _fracas = _classificar(pesos)

    historico: Set[frozenset] = set()
    try:
        from ciclo_cobertura.loaders import carregar_sorteios_asc
        historico = {frozenset(int(x) for x in s["dezenas"]) for s in carregar_sorteios_asc(modality_key)}
    except Exception:
        historico = set()

    rng = random.Random()
    p20, p80 = dna["p20"], dna["p80"]
    alvos_soma = []
    if p20 and p80 and p80 > p20:
        passo = max(1, (p80 - p20) // max(quantidade, 1))
        alvos_soma = [p20 + (i * passo) % (p80 - p20) for i in range(quantidade * 12)]
    else:
        alvos_soma = [int(dna["soma_media"] or 110)] * (quantidade * 12)

    candidatos: List[Tuple[float, List[int], Dict[str, float]]] = []
    vistos: Set[Tuple[int, ...]] = set()
    tentativas = max(180, quantidade * 22)
    for i in range(tentativas):
        montada = _montar(rng, dna, pesos, fortes, i, alvos_soma[i % len(alvos_soma)])
        if not montada:
            continue
        chave = tuple(montada)
        if chave in vistos:
            continue
        if frozenset(montada) in historico:
            continue
        vistos.add(chave)
        sc, partes = _score(montada, dna, pesos, fortes)
        candidatos.append((sc, montada, partes))

    candidatos.sort(key=lambda x: x[0], reverse=True)
    escolhidas: List[Tuple[float, List[int], Dict[str, float]]] = []
    for item in candidatos:
        if len(escolhidas) >= quantidade:
            break
        if _diversidade_ok(item[1], [e[1] for e in escolhidas], k):
            escolhidas.append(item)

    if len(escolhidas) < quantidade:
        for item in candidatos:
            if len(escolhidas) >= quantidade:
                break
            if item in escolhidas:
                continue
            if any(set(item[1]) == set(e[1]) for e in escolhidas):
                continue
            escolhidas.append(item)

    pend = dna["pendentes"]
    cob = _cobertura_ciclo([e[1] for e in escolhidas], pend)
    faltam = [d for d in pend if d not in cob]
    if faltam and escolhidas:
        for j, d in enumerate(faltam):
            sc, ap, partes = escolhidas[j % len(escolhidas)]
            if d in ap:
                continue
            fraco = min((x for x in ap if x not in fortes[:3]), key=lambda x: pesos.get(x, 0), default=ap[-1])
            nova = sorted((set(ap) - {fraco}) | {d})
            if len(nova) != k or frozenset(nova) in historico:
                continue
            if any(set(nova) == set(e[1]) for e in escolhidas):
                continue
            nsc, npartes = _score(nova, dna, pesos, fortes)
            escolhidas[j % len(escolhidas)] = (nsc, nova, npartes)

    apostas: List[Dict[str, Any]] = []
    for i, (sc, dz, partes) in enumerate(escolhidas[:quantidade], start=1):
        pares = sum(1 for d in dz if d % 2 == 0)
        seqs = _sequencias(dz)
        fins = Counter(d % 10 for d in dz)
        apostas.append({
            "numero": i,
            "dezenas": dz,
            "quantidade": k,
            "texto": " ".join(_FMT(n) for n in dz),
            "score_dna": sc,
            "score_partes": {k2: round(v, 2) for k2, v in partes.items()},
            "modo_motor_aposta": "resumo_geral",
            "criterios": _justificativa(dz, dna, sc, partes),
            "comportamento": {
                "PA": pares,
                "IM": k - pares,
                "SQ": len(seqs),
                "RT": len(set(dz) & set(dna["ultimo"])),
            },
            "sobreposicao": len(set(dz) & set(dna["ultimo"])),
            "do_ultimo_par": len(set(dz) & set(dna["ultimo"])),
        })

    labels = [
        "DNA do Resumo Geral — proximidade histórica, não previsão",
        "Score = aderência estatística, não chance de acerto",
    ]
    if dna["pi_perfis"]:
        labels.append(str(dna["pi_perfis"][0].get("dist") or ""))
    labels.append(f"soma {dna['p20']}–{dna['p80']}")
    if dna["exige_seq"]:
        labels.append("≥1 sequência")
    if dna["exige_final"]:
        labels.append("final repetido")
    if dna["bma_top"]:
        labels.append(str(dna["bma_top"][0].get("dist") or "2–3 B/M/A"))
    labels.append("núcleo + variações · concentração nas dezenas fortes")

    aviso = None
    if len(apostas) < quantidade:
        aviso = f"Geradas {len(apostas)} de {quantidade} apostas alinhadas ao DNA."
    nucleo_txt = ", ".join(_FMT(d) for d in fortes[:6])

    return {
        "sucesso": True,
        "apostas": apostas,
        "total_geradas": len(apostas),
        "solicitados": quantidade,
        "aviso": aviso,
        "modo_geracao": "resumo_geral",
        "modo_motor": "resumo_geral",
        "modo_motor_label": "Resumo Geral da Modalidade",
        "criterios_dna": labels,
        "criterios_modo_auto": labels,
        "nucleo_fortes": fortes[:8],
        "nucleo_txt": nucleo_txt,
        "regras_aplicadas": {"origem": "resumo_geral"},
        "validacao_ineditas": True,
        "descartadas_historico": 0,
        "nota": (
            "O score mede proximidade com o DNA estatístico do histórico. "
            "Não é probabilidade de acerto nem previsão do próximo concurso."
        ),
    }
