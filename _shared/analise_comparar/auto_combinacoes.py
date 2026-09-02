# -*- coding: utf-8 -*-
"""Geração e teste histórico de pools de 15 dezenas — independente da SUPER manual."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

POOL_SIZE = 15


def _completar_15(pool: Sequence[Any], dados: List[Dict[str, Any]], dmin: int, dmax: int) -> List[int]:
    out: List[int] = []
    used = set()
    for n in pool or []:
        n = int(n)
        if dmin <= n <= dmax and n not in used:
            out.append(n)
            used.add(n)
        if len(out) >= POOL_SIZE:
            break
    if len(out) < POOL_SIZE:
        for r in sorted(dados, key=lambda x: (-int(x.get("freq") or 0), int(x.get("dezena") or 0))):
            d = int(r["dezena"])
            if dmin <= d <= dmax and d not in used:
                out.append(d)
                used.add(d)
            if len(out) >= POOL_SIZE:
                break
    return sorted(out[:POOL_SIZE])


def _stats_historico(concursos: List[Dict[str, Any]], dmin: int, dmax: int) -> List[Dict[str, Any]]:
    freq = {d: 0 for d in range(dmin, dmax + 1)}
    last_seen: Dict[int, int] = {}
    ordered = sorted(concursos, key=lambda c: int(c.get("concurso") or 0), reverse=True)
    ultimo = int(ordered[0]["concurso"]) if ordered else 0
    for c in ordered:
        conc = int(c.get("concurso") or 0)
        for d in c.get("dezenas") or []:
            d = int(d)
            if dmin <= d <= dmax:
                freq[d] += 1
                if d not in last_seen:
                    last_seen[d] = conc
    out = []
    for d in range(dmin, dmax + 1):
        atraso = (ultimo - last_seen[d]) if d in last_seen else (ultimo + 1 if ultimo else 0)
        out.append({"dezena": d, "freq": freq[d], "atraso": atraso})
    return out


def _acertos_pool(pool: Sequence[int], drawn: Sequence[Any]) -> int:
    s = set(int(n) for n in pool)
    return sum(1 for n in drawn if int(n) in s)


def _medir(pool: List[int], concursos: List[Dict[str, Any]], max_faixa: int) -> Dict[str, Any]:
    pool_set = {int(n) for n in pool}
    faixas = {i: 0 for i in range(max_faixa + 1)}
    soma = 0
    melhor = 0
    melhores_detalhe: List[Dict[str, Any]] = []
    for c in concursos:
        drawn = c.get("dezenas") or []
        hits = _acertos_pool(pool, drawn)
        if hits > max_faixa:
            hits = max_faixa
        faixas[hits] = faixas.get(hits, 0) + 1
        soma += hits
        conc = int(c.get("concurso") or 0)
        ordem = c.get("dezenas_exibicao") or drawn
        ordem_n = [int(n) for n in ordem]
        acertadas = [n for n in ordem_n if n in pool_set]
        nao = [n for n in ordem_n if n not in pool_set]
        item = {
            "concurso": conc,
            "data": c.get("data") or "",
            "dezenas": ordem_n,
            "acertadas": acertadas,
            "nao_acertadas": nao,
            "acertos": hits,
        }
        if hits > melhor:
            melhor = hits
            melhores_detalhe = [item] if conc else []
        elif hits == melhor and hits > 0 and conc:
            melhores_detalhe.append(item)
    n = len(concursos)
    return {
        "concursos_testados": n,
        "faixas": faixas,
        "melhor_acerto": melhor,
        "melhores_concursos": [d["concurso"] for d in melhores_detalhe],
        "melhores_detalhe": melhores_detalhe,
        "media": round((soma / n), 2) if n else 0.0,
    }


def _chave(pool: Sequence[int]) -> Tuple[int, ...]:
    return tuple(sorted(int(n) for n in pool))


def gerar_e_testar(
    *,
    concursos: List[Dict[str, Any]],
    dmin: int,
    dmax: int,
    modality_key: str = "",
    dezenas_manual: Optional[Sequence[Any]] = None,
) -> Dict[str, Any]:
    """Gera pools de 15, testa no histórico completo e ranqueia por 7, depois 6."""
    if not concursos:
        return {"sucesso": False, "erro": "Sem concursos no histórico."}

    max_faixa = 0
    for c in concursos:
        max_faixa = max(max_faixa, len(c.get("dezenas") or []))
    if max_faixa <= 0:
        max_faixa = 7

    dados = _stats_historico(concursos, dmin, dmax)
    candidatas: List[Dict[str, Any]] = []

    def add(cid: str, label: str, nums: Sequence[Any], referencia: bool = False) -> None:
        pool = _completar_15(nums, dados, dmin, dmax)
        if len(pool) < POOL_SIZE:
            return
        candidatas.append({"id": cid, "label": label, "dezenas": pool, "referencia": referencia})

    add(
        "freq",
        "Dezenas mais frequentes",
        [r["dezena"] for r in sorted(dados, key=lambda x: (-x["freq"], x["dezena"]))],
    )
    add(
        "atraso",
        "Dezenas com maior atraso",
        [r["dezena"] for r in sorted(dados, key=lambda x: (-x["atraso"], x["dezena"]))],
    )

    try:
        from concentracao_acertos.specs import get_concentracao_config, tem_concentracao_acertos
        from concentracao_acertos.core import pool_sugerido
        if tem_concentracao_acertos(modality_key):
            cc = get_concentracao_config(modality_key)
            for est in (cc.get("estrategias") or []):
                eid = str(est.get("id") or "")
                size = int(est.get("pool_size") or POOL_SIZE)
                for criterio, suf, clbl in (("freq", "freq", "frequência"), ("atraso", "atraso", "atraso")):
                    dez = pool_sugerido(
                        dados, size, criterio, dezena_min=dmin, dezena_max=dmax,
                    )
                    add(
                        f"conc-{eid}-{suf}",
                        f"Concentração {eid} ({clbl}, pool {size} limitada a {POOL_SIZE})",
                        dez,
                    )
    except Exception:
        pass

    if dezenas_manual:
        add("manual", "SUPER manual (referência)", dezenas_manual, referencia=True)

    vistos: Dict[Tuple[int, ...], Dict[str, Any]] = {}
    unicas: List[Dict[str, Any]] = []
    for cand in candidatas:
        k = _chave(cand["dezenas"])
        if k in vistos:
            prev = vistos[k]
            if cand["label"] not in prev["label"]:
                prev["label"] = prev["label"] + " · " + cand["label"]
            if cand.get("referencia"):
                prev["referencia"] = True
            continue
        vistos[k] = cand
        unicas.append(cand)

    ranking = []
    for cand in unicas:
        med = _medir(cand["dezenas"], concursos, max_faixa)
        faixas = med["faixas"]
        ranking.append({
            "id": cand["id"],
            "label": cand["label"],
            "dezenas": cand["dezenas"],
            "referencia": bool(cand.get("referencia")),
            "concursos_testados": med["concursos_testados"],
            "faixas": faixas,
            "qtd_7": int(faixas.get(7, 0) or 0),
            "qtd_6": int(faixas.get(6, 0) or 0),
            "melhor_acerto": med["melhor_acerto"],
            "melhores_concursos": med["melhores_concursos"],
            "melhores_detalhe": med["melhores_detalhe"],
            "media": med["media"],
        })

    ranking.sort(key=lambda r: (-int(r["qtd_7"]), -int(r["qtd_6"]), -float(r["media"])))
    for i, r in enumerate(ranking, 1):
        r["posicao"] = i

    return {
        "sucesso": True,
        "pool_size": POOL_SIZE,
        "max_faixa": max_faixa,
        "concursos_testados": len(concursos),
        "aviso": (
            "Desempenho histórico na base já sorteada — não é previsão do próximo concurso. "
            "Ranking: mais concursos com 7 acertos, depois com 6."
        ),
        "ranking": ranking,
    }
