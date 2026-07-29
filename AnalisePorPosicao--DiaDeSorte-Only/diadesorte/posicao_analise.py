# -*- coding: utf-8 -*-
"""
Análise posicional — Dia de Sorte (camada pura, reutilizável).

Utiliza exclusivamente a ordem oficial do sorteio (dezenas_ordem),
nunca a ordem crescente.
"""
from __future__ import annotations

import random
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

TOTAL_DEZENAS = 31
NUM_POSICOES = 7
COLUNAS_MATRIZ = 10


def matriz_numeros() -> List[int]:
    """Números 01–31 exibidos na matriz fixa de cada posição."""
    return list(range(1, TOTAL_DEZENAS + 1))


def extrair_digitos(dezena: int) -> List[str]:
    """Retorna os dígitos da dezena com zero à esquerda (ex.: 06 → ['0','6'])."""
    return list(f"{int(dezena):02d}")


def soma_digitos(dezena: int) -> int:
    return sum(int(d) for d in extrair_digitos(dezena))


def soma_expressao(dezena: int) -> str:
    digs = extrair_digitos(dezena)
    return " + ".join(digs) + f" = {soma_digitos(dezena)}"


def analisar_concurso_geral(dezenas_ordem: List[int]) -> Dict[str, Any]:
    """Soma das dezenas e dígitos distintos usados nas 7 posições (ordem oficial)."""
    ordem = [int(d) for d in dezenas_ordem[:NUM_POSICOES]]
    soma = sum(ordem)
    digitos_set: set[str] = set()
    for dez in ordem:
        digitos_set.update(extrair_digitos(dez))
    digitos_distintos = sorted(digitos_set, key=lambda x: int(x))
    qtd = len(digitos_distintos)
    return {
        "soma_dezenas": soma,
        "soma_dezenas_expressao": " + ".join(f"{d:02d}" for d in ordem) + f" = {soma}",
        "digitos_distintos": digitos_distintos,
        "qtd_digitos_distintos": qtd,
        "digitos_distintos_fmt": ", ".join(digitos_distintos),
        "resumo_dig_soma": f"{qtd}/{soma}",
    }


def analisar_por_posicao(dezenas_ordem: List[int]) -> Dict[str, Any]:
    """
    Analisa as 7 posições a partir da ordem oficial do sorteio.

    Raises:
        ValueError: se houver menos de 7 dezenas na ordem informada.
    """
    if not dezenas_ordem or len(dezenas_ordem) < NUM_POSICOES:
        raise ValueError(f"Ordem do sorteio incompleta: esperadas {NUM_POSICOES} dezenas.")

    ordem = [int(d) for d in dezenas_ordem[:NUM_POSICOES]]
    posicoes: List[Dict[str, Any]] = []

    for idx, dez in enumerate(ordem):
        digs = extrair_digitos(dez)
        soma = sum(int(d) for d in digs)
        posicoes.append({
            "posicao": idx + 1,
            "dezena": dez,
            "dezena_fmt": f"{dez:02d}",
            "digitos": digs,
            "soma": soma,
            "soma_expressao": " + ".join(digs) + f" = {soma}",
        })

    return {
        "dezenas_ordem": ordem,
        "dezenas_ordem_fmt": [f"{d:02d}" for d in ordem],
        "posicoes": posicoes,
        "matriz_numeros": matriz_numeros(),
        **analisar_concurso_geral(ordem),
    }


def _stats_posicao(historico: Sequence[Sequence[int]], pos_idx: int, total: int) -> List[Dict[str, Any]]:
    freq = {d: 0 for d in range(1, TOTAL_DEZENAS + 1)}
    ultimo_idx: Dict[int, int] = {}
    for i, draw in enumerate(historico):
        if len(draw) <= pos_idx:
            continue
        d = int(draw[pos_idx])
        freq[d] += 1
        if d not in ultimo_idx:
            ultimo_idx[d] = i
    out: List[Dict[str, Any]] = []
    for d in range(1, TOTAL_DEZENAS + 1):
        atraso = ultimo_idx.get(d, total)
        out.append({
            "dezena": d,
            "dezena_fmt": f"{d:02d}",
            "freq": freq[d],
            "pct": round(freq[d] / total * 100, 1) if total else 0.0,
            "atraso": atraso,
        })
    return out


def analise_agregada_posicional(
    historico_ordem: Sequence[Sequence[int]],
    janela: Optional[int] = None,
) -> Dict[str, Any]:
    """Estatísticas por posição P1–P7 a partir do histórico (mais recente primeiro)."""
    if not historico_ordem:
        return {
            "total_sorteios": 0,
            "posicoes": [],
            "matriz_numeros": matriz_numeros(),
        }

    historico = list(historico_ordem[:janela] if janela and janela > 0 else historico_ordem)
    total = len(historico)
    posicoes: List[Dict[str, Any]] = []

    for p in range(NUM_POSICOES):
        stats = _stats_posicao(historico, p, total)
        top_freq = sorted(stats, key=lambda x: (-x["freq"], x["dezena"]))[:7]
        top_atraso = sorted(stats, key=lambda x: (-x["atraso"], -x["freq"], x["dezena"]))[:7]
        posicoes.append({
            "posicao": p + 1,
            "dezenas": stats,
            "top_freq": [x["dezena"] for x in top_freq],
            "top_atraso": [x["dezena"] for x in top_atraso],
        })

    somas: List[int] = []
    qtd_digs: List[int] = []
    for draw in historico:
        if len(draw) >= NUM_POSICOES:
            geral = analisar_concurso_geral(list(draw))
            somas.append(geral["soma_dezenas"])
            qtd_digs.append(geral["qtd_digitos_distintos"])

    ultimo_geral: Dict[str, Any] = {}
    if historico and len(historico[0]) >= NUM_POSICOES:
        ultimo_geral = analisar_concurso_geral(list(historico[0]))

    return {
        "total_sorteios": total,
        "posicoes": posicoes,
        "matriz_numeros": matriz_numeros(),
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
    perfil: str = "equilibrado",
    alvo_dig_soma: Optional[Tuple[int, int]] = None,
    tol_digitos: int = 1,
    tol_soma: int = 12,
    max_tentativas: int = 250,
    rng: Optional[random.Random] = None,
    score_boost: Optional[Callable[[int, Dict[str, Any], float], float]] = None,
) -> List[int]:
    """Monta 7 dezenas distintas em ordem oficial (P1→P7)."""
    r = rng or random.Random()
    perfil = perfil if perfil in ("equilibrado", "frequencia", "atraso") else "equilibrado"

    for _ in range(max_tentativas):
        usados: set[int] = set()
        aposta: List[int] = []
        ok = True
        for pos_idx, pos in enumerate(posicoes_stats):
            stats = pos["dezenas"]
            max_freq = max((s["freq"] for s in stats), default=1)
            max_atraso = max((s["atraso"] for s in stats), default=1)
            candidatos = [s for s in stats if s["dezena"] not in usados]
            if not candidatos:
                ok = False
                break

            def _final_score(s: Dict[str, Any]) -> float:
                base = _score_dezena_pos(s, perfil, max_freq, max_atraso, r)
                if score_boost:
                    return score_boost(pos_idx, s, base)
                return base

            candidatos.sort(key=lambda s: -_final_score(s))
            top_n = min(5, len(candidatos))
            pick = candidatos[r.randrange(top_n)]["dezena"]
            usados.add(pick)
            aposta.append(pick)
        if not ok or len(aposta) != NUM_POSICOES:
            continue
        geral = analisar_concurso_geral(aposta)
        if _dig_soma_ok(geral, alvo_dig_soma, tol_digitos, tol_soma):
            return aposta

    usados_fallback: set[int] = set()
    aposta_fb: List[int] = []
    for pos_idx, pos in enumerate(posicoes_stats):
        stats = pos["dezenas"]
        max_freq = max((s["freq"] for s in stats), default=1)
        max_atraso = max((s["atraso"] for s in stats), default=1)
        candidatos = [s for s in stats if s["dezena"] not in usados_fallback]

        def _final_score_fb(s: Dict[str, Any]) -> float:
            base = _score_dezena_pos(s, perfil, max_freq, max_atraso, r)
            if score_boost:
                return score_boost(pos_idx, s, base)
            return base

        candidatos.sort(key=lambda s: -_final_score_fb(s))
        pick = candidatos[0]["dezena"]
        usados_fallback.add(pick)
        aposta_fb.append(pick)
    return aposta_fb


def formatar_aposta_posicional(dezenas_ordem: Sequence[int]) -> Dict[str, Any]:
    """Payload de aposta com ordem oficial e resumo dígitos/soma."""
    ordem = [int(d) for d in dezenas_ordem[:NUM_POSICOES]]
    geral = analisar_concurso_geral(ordem)
    return {
        "dezenas_ordem": ordem,
        "dezenas_ordem_fmt": [f"{d:02d}" for d in ordem],
        **geral,
    }


def gerar_apostas_posicionais(
    posicoes_stats: Sequence[Dict[str, Any]],
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
            perfil=perfil,
            alvo_dig_soma=alvo,
            rng=r,
        )
        chave = tuple(ordem)
        if chave in vistos:
            continue
        vistos.add(chave)
        apostas.append(formatar_aposta_posicional(ordem))
    return apostas
