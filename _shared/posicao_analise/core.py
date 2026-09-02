# -*- coding: utf-8 -*-
"""Núcleo analítico posicional — parametrizado por PosicaoSpec."""
from __future__ import annotations

import random
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .specs import PosicaoSpec


def matriz_numeros(spec: PosicaoSpec) -> List[int]:
    return list(range(spec.valor_min, spec.valor_max + 1))


def extrair_digitos(valor: int, pad_width: int = 2) -> List[str]:
    if pad_width <= 1:
        return [str(int(valor))]
    return list(f"{int(valor):0{pad_width}d}")


def soma_digitos(valor: int, pad_width: int = 2) -> int:
    return sum(int(d) for d in extrair_digitos(valor, pad_width))


def analisar_concurso_geral(dezenas_ordem: List[int], spec: PosicaoSpec) -> Dict[str, Any]:
    n = spec.num_posicoes
    ordem = [int(d) for d in dezenas_ordem[:n]]
    soma = sum(ordem)
    digitos_set: set[str] = set()
    for dez in ordem:
        digitos_set.update(extrair_digitos(dez, spec.pad_width))
    digitos_distintos = sorted(digitos_set, key=lambda x: int(x))
    qtd = len(digitos_distintos)
    fmt = spec.fmt
    return {
        "soma_dezenas": soma,
        "soma_dezenas_expressao": " + ".join(fmt(d) for d in ordem) + f" = {soma}",
        "digitos_distintos": digitos_distintos,
        "qtd_digitos_distintos": qtd,
        "digitos_distintos_fmt": ", ".join(digitos_distintos),
        "resumo_dig_soma": f"{qtd}/{soma}",
    }


def analisar_por_posicao(dezenas_ordem: List[int], spec: PosicaoSpec) -> Dict[str, Any]:
    n = spec.num_posicoes
    if not dezenas_ordem or len(dezenas_ordem) < n:
        raise ValueError(f"Ordem incompleta: esperadas {n} valores.")

    ordem = [int(d) for d in dezenas_ordem[:n]]
    posicoes: List[Dict[str, Any]] = []

    for idx, dez in enumerate(ordem):
        digs = extrair_digitos(dez, spec.pad_width)
        soma = sum(int(d) for d in digs)
        posicoes.append({
            "posicao": idx + 1,
            "dezena": dez,
            "dezena_fmt": spec.fmt(dez),
            "digitos": digs,
            "soma": soma,
            "soma_expressao": " + ".join(digs) + f" = {soma}",
        })

    out: Dict[str, Any] = {
        "dezenas_ordem": ordem,
        "dezenas_ordem_fmt": [spec.fmt(d) for d in ordem],
        "posicoes": posicoes,
        "matriz_numeros": matriz_numeros(spec),
    }
    if spec.show_dig_soma:
        out.update(analisar_concurso_geral(ordem, spec))
    return out


def _stats_posicao(
    historico: Sequence[Sequence[int]],
    pos_idx: int,
    total: int,
    spec: PosicaoSpec,
) -> List[Dict[str, Any]]:
    freq = {d: 0 for d in range(spec.valor_min, spec.valor_max + 1)}
    ultimo_idx: Dict[int, int] = {}
    for i, draw in enumerate(historico):
        if len(draw) <= pos_idx:
            continue
        d = int(draw[pos_idx])
        if d < spec.valor_min or d > spec.valor_max:
            continue
        freq[d] += 1
        if d not in ultimo_idx:
            ultimo_idx[d] = i
    out: List[Dict[str, Any]] = []
    for d in range(spec.valor_min, spec.valor_max + 1):
        atraso = ultimo_idx.get(d, total)
        out.append({
            "dezena": d,
            "dezena_fmt": spec.fmt(d),
            "freq": freq[d],
            "pct": round(freq[d] / total * 100, 1) if total else 0.0,
            "atraso": atraso,
        })
    return out


def analise_agregada_posicional(
    historico_ordem: Sequence[Sequence[int]],
    spec: PosicaoSpec,
    janela: Optional[int] = None,
) -> Dict[str, Any]:
    if not historico_ordem:
        return {
            "total_sorteios": 0,
            "posicoes": [],
            "matriz_numeros": matriz_numeros(spec),
        }

    historico = list(historico_ordem[:janela] if janela and janela > 0 else historico_ordem)
    total = len(historico)
    posicoes: List[Dict[str, Any]] = []
    top_n = min(7, max(3, spec.num_posicoes // 2))

    for p in range(spec.num_posicoes):
        stats = _stats_posicao(historico, p, total, spec)
        top_freq = sorted(stats, key=lambda x: (-x["freq"], x["dezena"]))[:top_n]
        top_atraso = sorted(stats, key=lambda x: (-x["atraso"], -x["freq"], x["dezena"]))[:top_n]
        posicoes.append({
            "posicao": p + 1,
            "dezenas": stats,
            "top_freq": [x["dezena"] for x in top_freq],
            "top_atraso": [x["dezena"] for x in top_atraso],
        })

    somas: List[int] = []
    qtd_digs: List[int] = []
    ultimo_geral: Dict[str, Any] = {}
    if spec.show_dig_soma:
        for draw in historico:
            if len(draw) >= spec.num_posicoes:
                geral = analisar_concurso_geral(list(draw), spec)
                somas.append(geral["soma_dezenas"])
                qtd_digs.append(geral["qtd_digitos_distintos"])
        if historico and len(historico[0]) >= spec.num_posicoes:
            ultimo_geral = analisar_concurso_geral(list(historico[0]), spec)

    return {
        "total_sorteios": total,
        "posicoes": posicoes,
        "matriz_numeros": matriz_numeros(spec),
        "ultimo_resumo_dig_soma": ultimo_geral.get("resumo_dig_soma"),
        "ultimo_qtd_digitos": ultimo_geral.get("qtd_digitos_distintos"),
        "ultimo_soma": ultimo_geral.get("soma_dezenas"),
        "media_soma": round(sum(somas) / len(somas), 1) if somas else None,
        "media_digitos": round(sum(qtd_digs) / len(qtd_digs), 1) if qtd_digs else None,
        "soma_min": min(somas) if somas else None,
        "soma_max": max(somas) if somas else None,
    }


def _score_dezena_pos(
    stat: Dict[str, Any],
    perfil: str,
    max_freq: int,
    max_atraso: int,
    rng: random.Random,
) -> float:
    freq = int(stat["freq"])
    atraso = int(stat["atraso"])
    jitter = rng.random() * 0.02
    if perfil == "frequencia":
        return freq + jitter
    if perfil == "atraso":
        return atraso + jitter
    nf = freq / max(max_freq, 1)
    na = atraso / max(max_atraso, 1)
    return nf * 0.55 + na * 0.45 + jitter


def _dig_soma_ok(geral: Dict[str, Any], alvo: Optional[Tuple[int, int]], tol_dig: int, tol_soma: int) -> bool:
    if not alvo:
        return True
    qtd_alvo, soma_alvo = alvo
    qtd = int(geral["qtd_digitos_distintos"])
    soma = int(geral["soma_dezenas"])
    return abs(qtd - qtd_alvo) <= tol_dig and abs(soma - soma_alvo) <= tol_soma


def montar_aposta_posicional(
    posicoes_stats: Sequence[Dict[str, Any]],
    spec: PosicaoSpec,
    perfil: str = "equilibrado",
    alvo_dig_soma: Optional[Tuple[int, int]] = None,
    tol_digitos: int = 1,
    tol_soma: int = 12,
    max_tentativas: int = 250,
    rng: Optional[random.Random] = None,
    score_boost: Optional[Callable[[int, Dict[str, Any], float], float]] = None,
) -> List[int]:
    r = rng or random.Random()
    perfil = perfil if perfil in ("equilibrado", "frequencia", "atraso") else "equilibrado"
    n = spec.num_posicoes
    distinct = spec.distinct_across_positions

    for _ in range(max_tentativas):
        usados: set[int] = set()
        aposta: List[int] = []
        ok = True
        for pos_idx, pos in enumerate(posicoes_stats):
            stats = pos["dezenas"]
            max_freq = max((s["freq"] for s in stats), default=1)
            max_atraso = max((s["atraso"] for s in stats), default=1)
            candidatos = [s for s in stats if (not distinct) or s["dezena"] not in usados]
            if not candidatos:
                ok = False
                break

            def _final_score(s: Dict[str, Any]) -> float:
                base = _score_dezena_pos(s, perfil, max_freq, max_atraso, r)
                if score_boost:
                    return score_boost(pos_idx, s, base)
                return base

            candidatos.sort(key=lambda s: -_final_score(s))
            top_k = min(5, len(candidatos))
            pick = candidatos[r.randrange(top_k)]["dezena"]
            if distinct:
                usados.add(pick)
            aposta.append(pick)
        if not ok or len(aposta) != n:
            continue
        if spec.show_dig_soma:
            geral = analisar_concurso_geral(aposta, spec)
            if not _dig_soma_ok(geral, alvo_dig_soma, tol_digitos, tol_soma):
                continue
        return aposta

    usados_fallback: set[int] = set()
    aposta_fb: List[int] = []
    for pos_idx, pos in enumerate(posicoes_stats):
        stats = pos["dezenas"]
        max_freq = max((s["freq"] for s in stats), default=1)
        max_atraso = max((s["atraso"] for s in stats), default=1)
        candidatos = [s for s in stats if (not distinct) or s["dezena"] not in usados_fallback]

        def _final_score_fb(s: Dict[str, Any]) -> float:
            base = _score_dezena_pos(s, perfil, max_freq, max_atraso, r)
            if score_boost:
                return score_boost(pos_idx, s, base)
            return base

        candidatos.sort(key=lambda s: -_final_score_fb(s))
        pick = candidatos[0]["dezena"]
        if distinct:
            usados_fallback.add(pick)
        aposta_fb.append(pick)
    return aposta_fb


def formatar_aposta_posicional(dezenas_ordem: Sequence[int], spec: PosicaoSpec) -> Dict[str, Any]:
    n = spec.num_posicoes
    ordem = [int(d) for d in dezenas_ordem[:n]]
    out: Dict[str, Any] = {
        "dezenas_ordem": ordem,
        "dezenas_ordem_fmt": [spec.fmt(d) for d in ordem],
    }
    if spec.show_dig_soma:
        out.update(analisar_concurso_geral(ordem, spec))
    return out


def gerar_apostas_posicionais(
    posicoes_stats: Sequence[Dict[str, Any]],
    spec: PosicaoSpec,
    quantidade: int = 10,
    perfil: str = "equilibrado",
    filtrar_dig_soma: bool = False,
    alvo_dig_soma: Optional[Tuple[int, int]] = None,
    seed: Optional[int] = None,
) -> List[Dict[str, Any]]:
    qtd = max(1, min(int(quantidade), 100))
    r = random.Random(seed)
    alvo = alvo_dig_soma if filtrar_dig_soma else None
    apostas: List[Dict[str, Any]] = []
    vistos: set[tuple[int, ...]] = set()
    tentativas = 0
    max_total = qtd * 80
    while len(apostas) < qtd and tentativas < max_total:
        tentativas += 1
        ordem = montar_aposta_posicional(
            posicoes_stats,
            spec,
            perfil=perfil,
            alvo_dig_soma=alvo,
            rng=r,
        )
        chave = tuple(ordem)
        if chave in vistos:
            continue
        vistos.add(chave)
        apostas.append(formatar_aposta_posicional(ordem, spec))
    return apostas
