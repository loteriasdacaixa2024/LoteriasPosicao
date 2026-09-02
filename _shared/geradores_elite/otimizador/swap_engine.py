# -*- coding: utf-8 -*-
"""Motor de swaps — Otimizador de Concentração."""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from geradores_elite.comportamento.specs import SPECS
from geradores_elite.engine_final_core import build_dezena_scores, get_config
from geradores_elite.modality_config import MODALITIES

from .restricoes import (
    aplicar_swap,
    penalidade_perfil,
    perfil_aposta,
    pool_cobertura,
    pool_preservado,
    swap_compativel_faixa_paridade,
    swap_valido_restrito,
)
from .score import avaliar_conjunto, score_com_penalidade


MODALIDADES_OTIMIZADOR = frozenset({"diadesorte"})


def _carregar_historico(modality_key: str, limite: int) -> List[Set[int]]:
    from geradores_elite.construtor import get_construtor_service
    from models.shared import db
    from sqlalchemy import desc

    svc = get_construtor_service(modality_key)
    if not svc:
        return []
    lim = max(5, min(int(limite), 200))
    rows = (
        db.session.query(svc._model())
        .order_by(desc(svc._model().concurso))
        .limit(lim)
        .all()
    )
    out: List[Set[int]] = []
    for row in rows:
        out.append(set(svc._dezenas_from_sorteio(row)))
    return out


def _pesos_dezenas(modality_key: str) -> Dict[int, float]:
    scores, _ = build_dezena_scores(modality_key)
    if not scores:
        cfg = get_config(modality_key)
        return {d: 1.0 for d in range(cfg["dezena_min"], cfg["dezena_max"] + 1)}
    mx = max(scores.values()) or 1.0
    return {d: (v / mx) for d, v in scores.items()}


def _regioes_volante(universo: int) -> List[Tuple[str, List[int]]]:
    if universo <= 31:
        return [
            ("baixa", list(range(1, 11))),
            ("media", list(range(11, 21))),
            ("alta", list(range(21, universo + 1))),
        ]
    t1 = universo // 3
    t2 = 2 * universo // 3
    return [
        ("baixa", list(range(1, t1 + 1))),
        ("media", list(range(t1 + 1, t2 + 1))),
        ("alta", list(range(t2 + 1, universo + 1))),
    ]


def _regiao_circular(dezena: int, universo: int, tamanho: int = 7) -> List[int]:
    """Sequência circular a partir de dezena (ex.: 29→30→31→01…)."""
    out = []
    d = dezena
    for _ in range(tamanho):
        out.append(d)
        d = 1 if d >= universo else d + 1
    return out


def _prioridade_swap(
    di: int,
    dj: int,
    apostas: List[List[int]],
    i: int,
    j: int,
    pesos: Dict[int, float],
    universo: int,
) -> float:
    """Maior = tentar antes. Favorece juntar dezenas de alta influência."""
    wi = pesos.get(di, 0.5)
    wj = pesos.get(dj, 0.5)
    conj_i = set(apostas[i])
    conj_j = set(apostas[j])

    ganho_i = wi + sum(pesos.get(d, 0) for d in conj_i if d != di)
    ganho_j = wj + sum(pesos.get(d, 0) for d in conj_j if d != dj)

    regioes = _regioes_volante(universo)
    bonus = 0.0
    for _, nums in regioes:
        rs = set(nums)
        if di in rs and dj in rs:
            bonus += 0.3
        circ = set(_regiao_circular(di, universo, 5))
        if dj in circ:
            bonus += 0.15

    return ganho_i + ganho_j + bonus


def _candidatos_swap(
    apostas: List[List[int]],
    pesos: Dict[int, float],
    universo: int,
    limite: int = 80,
) -> List[Tuple[int, int, int, int, float]]:
    n = len(apostas)
    cands: List[Tuple[int, int, int, int, float]] = []
    for i in range(n):
        for j in range(i + 1, n):
            for pi, di in enumerate(apostas[i]):
                for pj, dj in enumerate(apostas[j]):
                    if di == dj:
                        continue
                    if not swap_compativel_faixa_paridade(di, dj, universo):
                        continue
                    pr = _prioridade_swap(di, dj, apostas, i, j, pesos, universo)
                    cands.append((i, j, pi, pj, pr))
    cands.sort(key=lambda x: -x[4])
    return cands[:limite] if len(cands) > limite else cands


def _apostas_para_listas(apostas: List[Dict[str, Any]]) -> List[List[int]]:
    return [list(ap.get("dezenas") or []) for ap in apostas]


def _listas_para_apostas(
    listas: List[List[int]],
    originais: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    out = []
    for idx, dz in enumerate(listas):
        base = dict(originais[idx]) if idx < len(originais) else {}
        base["dezenas"] = sorted(dz)
        out.append(base)
    return out


def _avaliar_rapido(
    apostas: List[List[int]],
    historico: Sequence[Set[int]],
    max_acertos: int,
) -> float:
    return avaliar_conjunto(apostas, historico, max_acertos)["score"]


def otimizar_apostas(
    modality_key: str,
    apostas: List[Dict[str, Any]],
    modo: str = "restrito",
    iteracoes: int = 5000,
    janela_historico: int = 30,
) -> Dict[str, Any]:
    if modality_key not in MODALIDADES_OTIMIZADOR:
        return {
            "sucesso": False,
            "erro": f"Otimizador ainda não disponível para {modality_key}.",
        }
    if modality_key not in MODALITIES:
        return {"sucesso": False, "erro": "Modalidade desconhecida."}

    if not apostas:
        return {"sucesso": False, "erro": "Nenhuma aposta para otimizar."}

    cfg = get_config(modality_key)
    sp = SPECS[modality_key]
    max_ac = int(cfg.get("sorteadas") or sp.sorteadas)

    listas = _apostas_para_listas(apostas)
    perfis = [perfil_aposta(dz, modality_key) for dz in listas]
    cobertura_orig = pool_cobertura(listas)

    historico = _carregar_historico(modality_key, janela_historico)
    if not historico:
        return {"sucesso": False, "erro": "Histórico insuficiente para otimização."}

    pesos = _pesos_dezenas(modality_key)
    modo_norm = (modo or "restrito").strip().lower()
    gradual = modo_norm in ("gradual", "flexivel", "flexível")

    metricas_antes = avaliar_conjunto(listas, historico, max_ac)
    score_atual = metricas_antes["score"]
    melhor = [list(a) for a in listas]
    melhor_score = score_atual

    iters = max(500, min(int(iteracoes), 15000))
    aceitos = 0
    tentativas = 0
    n_ap = len(melhor)
    k_ap = len(melhor[0]) if melhor else 0
    cands_fixos = _candidatos_swap(melhor, pesos, sp.universo, limite=120)

    for t in range(iters):
        tentativas += 1
        if cands_fixos and t % 3 == 0:
            i, j, pi, pj, _ = cands_fixos[t % len(cands_fixos)]
        else:
            if n_ap < 2 or k_ap < 1:
                break
            i = random.randint(0, n_ap - 1)
            j = random.randint(0, n_ap - 1)
            if i == j:
                continue
            pi = random.randint(0, k_ap - 1)
            pj = random.randint(0, k_ap - 1)
            di, dj = melhor[i][pi], melhor[j][pj]
            if not gradual and not swap_compativel_faixa_paridade(di, dj, sp.universo):
                continue

        if gradual:
            trial = aplicar_swap(melhor, i, j, pi, pj)
            if trial[i][pi] == melhor[i][pi]:
                continue
            pen = (
                penalidade_perfil(trial[i], perfis[i], modality_key)
                + penalidade_perfil(trial[j], perfis[j], modality_key)
            )
            novo_score = score_com_penalidade(trial, historico, pen * 3.0, max_ac)
            if novo_score > melhor_score:
                melhor = trial
                melhor_score = novo_score
                aceitos += 1
        else:
            if not swap_valido_restrito(melhor, i, j, pi, pj, perfis, modality_key):
                continue
            trial = aplicar_swap(melhor, i, j, pi, pj)
            novo_score = _avaliar_rapido(trial, historico, max_ac)
            if novo_score > melhor_score + 1e-6:
                melhor = trial
                melhor_score = novo_score
                aceitos += 1

    if not pool_preservado(listas, melhor):
        melhor = [list(a) for a in listas]
        melhor_score = score_atual

    cobertura_depois = pool_cobertura(melhor)
    metricas_depois = avaliar_conjunto(melhor, historico, max_ac)

    apostas_otim = _listas_para_apostas(melhor, apostas)
    apostas_orig = _listas_para_apostas(listas, apostas)

    melhoria = round(metricas_depois["score"] - metricas_antes["score"], 4)
    delta_max = round(
        metricas_depois["media_max_acertos"] - metricas_antes["media_max_acertos"],
        3,
    )
    sem_alteracao = aceitos == 0 or melhor == listas

    return {
        "sucesso": True,
        "modo": "gradual" if gradual else "restrito",
        "sem_alteracao": sem_alteracao,
        "mensagem": (
            "Nenhuma redistribuição melhorou a concentração no histórico recente. "
            "O conjunto gerado já está bem distribuído para as regras atuais."
            if sem_alteracao else ""
        ),
        "iteracoes": iters,
        "tentativas": tentativas,
        "swaps_aceitos": aceitos,
        "janela_historico": len(historico),
        "cobertura_original": len(cobertura_orig),
        "cobertura_otimizada": len(cobertura_depois),
        "cobertura_preservada": cobertura_orig == cobertura_depois,
        "metricas_antes": metricas_antes,
        "metricas_depois": metricas_depois,
        "melhoria_score": melhoria,
        "delta_media_max": delta_max,
        "apostas_originais": apostas_orig,
        "apostas": apostas_otim,
    }
