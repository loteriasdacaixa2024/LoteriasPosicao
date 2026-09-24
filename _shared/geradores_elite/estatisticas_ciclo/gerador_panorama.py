# -*- coding: utf-8 -*-
"""
Gerador Elite — modo Panorama (padrão · sequência · soma · status).

Sorteia sementes da tabela «Sequência sorteada vs média do padrão» e monta
apostas inéditas no mesmo padrão, mirando o mesmo status de soma.

Ciclo: só entra no fim (poucas pendentes). No começo fica aleatório.
Quando o ciclo fecha (0 pendentes), o próximo sorteio reabre — até lá
não há o que encaixar.
"""
from __future__ import annotations

import random
from collections import Counter
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from analise_escolha_visual.enriquecimento.motor import conjuntos_concurso
from analise_inteligentes_diadesorte.soma_media import calcular_faixa_soma, classificar_soma

from .gerador import (
    _atrasos,
    _completar_com_padrao,
    _diagonais_da_aposta,
    _freq,
    _norm_padrao,
    _perfil_alvo,
    _resumo_diagonais_janela,
)

# Poucas pendentes = ciclo no fim. 0 = fechado (próximo sorteio reabre).
CICLO_FIM_MAX = 10


def modo_ciclo_panorama(n_pendentes: int, n_sorteadas: int = 0) -> str:
    n = int(n_pendentes or 0)
    if n <= 0:
        return "fechado"
    limiar = max(int(CICLO_FIM_MAX), int(n_sorteadas or 0))
    return "fim" if n <= limiar else "inicio"


def resumo_ciclo_panorama(n_pendentes: int, n_sorteadas: int = 0) -> Dict[str, Any]:
    modo = modo_ciclo_panorama(n_pendentes, n_sorteadas)
    return {
        "modo": modo,
        "ligado": modo == "fim",
        "limiar": max(int(CICLO_FIM_MAX), int(n_sorteadas or 0)),
        "pendentes": int(n_pendentes or 0),
    }


def _dezenas_da_linha(row: Dict[str, Any]) -> Tuple[int, ...]:
    raw = row.get("dezenas") or []
    if raw:
        return tuple(sorted(int(n) for n in raw if str(n).strip() != ""))
    fmt = str(row.get("dezenas_fmt") or "").replace("-", " ")
    nums = [int(x) for x in fmt.split() if x.isdigit()]
    return tuple(sorted(nums)) if nums else ()


def _pendentes_compativeis(
    pendentes: Sequence[int],
    padrao: str,
    *,
    k: int,
    rng: random.Random,
) -> List[int]:
    need = Counter(int(x) for x in str(_norm_padrao(padrao)).split() if x.isdigit())
    pool = [int(n) for n in pendentes]
    rng.shuffle(pool)
    chosen: List[int] = []
    have: Counter = Counter()
    for n in pool:
        d = n // 10
        if have[d] >= need.get(d, 0):
            continue
        chosen.append(n)
        have[d] += 1
        if len(chosen) >= k:
            break
    return sorted(chosen)


def _sementes_distintas(
    linhas: Sequence[Dict[str, Any]],
    qtd: int,
    rng: random.Random,
) -> List[Dict[str, Any]]:
    candidatos = [row for row in linhas if _norm_padrao(row.get("padrao") or "")]
    rng.shuffle(candidatos)
    vistos: Set[Tuple[str, int]] = set()
    out: List[Dict[str, Any]] = []
    for row in candidatos:
        chave = (_norm_padrao(row.get("padrao") or ""), int(row.get("sequencia_n") or 0))
        if chave in vistos:
            continue
        vistos.add(chave)
        out.append(row)
        if len(out) >= qtd:
            break
    if len(out) < qtd:
        extra = [r for r in candidatos if r not in out]
        out.extend(extra[: qtd - len(out)])
    return out[:qtd]


def _faixas_por_padrao(linhas: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    somas: Dict[str, List[int]] = {}
    for row in linhas:
        pad = _norm_padrao(row.get("padrao") or "")
        if not pad:
            continue
        try:
            somas.setdefault(pad, []).append(int(row.get("soma") or 0))
        except (TypeError, ValueError):
            continue
    return {
        pad: faixa
        for pad, vals in somas.items()
        if (faixa := calcular_faixa_soma(vals, fonte="historico"))
    }


def gerar_apostas_panorama(
    *,
    pendentes: Sequence[int],
    linhas_basicas: Sequence[Dict[str, Any]],
    medias: Optional[Dict[str, Any]] = None,
    quantidade: int = 10,
    dezena_min: int = 1,
    dezena_max: int = 31,
    k: int = 7,
    rng: Optional[random.Random] = None,
    historico: Optional[Set] = None,
    modality_key: str = "diadesorte",
) -> Dict[str, Any]:
    from analise_inteligentes_diadesorte.service import make_inteligentes_service

    rng = rng or random.Random()
    dmin, dmax, k = int(dezena_min), int(dezena_max), int(k)
    pends = sorted({int(x) for x in pendentes if dmin <= int(x) <= dmax})
    hist = set(historico or [])
    qtd_pedida = max(1, min(200, int(quantidade or 10)))
    qtd = qtd_pedida
    ciclo_info = resumo_ciclo_panorama(len(pends), k)
    ciclo_ligado = bool(ciclo_info["ligado"])

    ultimo = linhas_basicas[0] if linhas_basicas else None
    ultimo_nums = [int(x) for x in (ultimo or {}).get("numeros") or (ultimo or {}).get("dezenas") or []]
    ultimo_set = set(ultimo_nums)
    alvo = _perfil_alvo(medias or {}, ultimo)
    atrasos = _atrasos(linhas_basicas, dmin, dmax)
    freq20 = _freq(linhas_basicas, 20)
    persistentes = set(ultimo_nums)

    svc = make_inteligentes_service(modality_key)
    payload = svc.sequencias_sorteadas()
    linhas = list(payload.get("linhas") or [])
    if not linhas:
        return {"sucesso": False, "erro": "Sem sequências sorteadas para semear o Panorama."}

    faixas = _faixas_por_padrao(linhas)
    ja_saiu: Set[Tuple[int, ...]] = set()
    for row in linhas:
        dez = _dezenas_da_linha(row)
        if dez:
            ja_saiu.add(dez)
    for item in hist:
        try:
            ja_saiu.add(tuple(sorted(int(x) for x in item)))
        except (TypeError, ValueError):
            continue

    sementes = _sementes_distintas(linhas, qtd, rng)
    usados: Set[Tuple[int, ...]] = set()
    apostas_out: List[Dict[str, Any]] = []

    for seed_row in sementes:
        pad = _norm_padrao(seed_row.get("padrao") or "")
        if not pad:
            continue
        faixa = faixas.get(pad)
        status_alvo = str(seed_row.get("status_media") or "dentro")
        locked: List[int] = []
        if ciclo_ligado:
            locked = _pendentes_compativeis(pends, pad, k=k, rng=rng)
        jogo: List[int] = []
        melhor: List[int] = []
        melhor_ad = 10**9
        for _t in range(36):
            cand = _completar_com_padrao(
                locked,
                pad,
                k=k,
                dmin=dmin,
                dmax=dmax,
                pendentes=pends if ciclo_ligado else [],
                ultimo_set=ultimo_set,
                alvo=alvo,
                atrasos=atrasos,
                freq20=freq20,
                persistentes=persistentes,
                rng=rng,
                max_pendentes=len(locked) if ciclo_ligado else 0,
                proibidos=usados,
            )
            if not cand:
                continue
            chave = tuple(cand)
            if chave in usados or chave in ja_saiu:
                continue
            if hist and frozenset(cand) in hist:
                continue
            soma = sum(cand)
            cls = classificar_soma(soma, faixa)
            dist = cls.get("distancia")
            ad = abs(int(dist)) if dist is not None else abs(soma - int((faixa or {}).get("media") or soma))
            if ad < melhor_ad:
                melhor_ad = ad
                melhor = cand
            if cls.get("status_media") == status_alvo:
                jogo = cand
                break
        if not jogo:
            jogo = melhor
        if not jogo:
            continue
        chave = tuple(jogo)
        if chave in usados:
            continue
        usados.add(chave)
        det = conjuntos_concurso(jogo, ultimo_nums or None)
        cls = classificar_soma(sum(jogo), faixa)
        pad_real = _norm_padrao(" ".join(str(n // 10) for n in jogo))
        apostas_out.append({
            "dezenas": list(jogo),
            "obrigatorias": sorted(n for n in jogo if n in set(pends)) if ciclo_ligado else [],
            "complemento": sorted(n for n in jogo if n not in set(pends)) if ciclo_ligado else list(jogo),
            "pares": det["basicos"]["pares"]["quantidade"],
            "impares": det["basicos"]["impares"]["quantidade"],
            "repetidos": det["basicos"]["repetidos"]["dezenas"],
            "sequencias": det["basicos"]["sequencias"].get("detalhe", {}).get("grupos") or [],
            "finais": det["basicos"]["finais"].get("detalhe", {}).get("grupos") or [],
            "soma": det["soma"],
            "diagonais": _diagonais_da_aposta(jogo, dmin, dmax),
            "padrao_inicial": pad_real,
            "padrao_inedito": False,
            "padrao_freq": int(seed_row.get("frequencia") or 0),
            "padrao_descricao": seed_row.get("descricao") or "",
            "semente": {
                "concurso": seed_row.get("concurso"),
                "sequencia_n": seed_row.get("sequencia_n"),
                "padrao": pad,
                "soma": seed_row.get("soma"),
                "status_media": seed_row.get("status_media"),
                "status_media_label": seed_row.get("status_media_label"),
            },
            "status_media": cls.get("status_media"),
            "status_media_label": cls.get("status_media_label"),
            "soma_media": (faixa or {}).get("media"),
        })

    union_pend: Set[int] = set()
    for a in apostas_out:
        union_pend.update(a.get("obrigatorias") or [])
    cobertos = sorted(union_pend)
    faltou = [n for n in pends if n not in union_pend] if ciclo_ligado else []
    pads = [a.get("padrao_inicial") for a in apostas_out]
    return {
        "sucesso": True,
        "modo_geracao": "panorama",
        "apostas": apostas_out,
        "quantidade": len(apostas_out),
        "quantidade_solicitada": qtd_pedida,
        "quantidade_ajustada": len(apostas_out) != qtd_pedida,
        "pendentes": pends,
        "pendentes_cobertos": cobertos,
        "pendentes_faltando": faltou,
        "todas_pendentes_no_lote": (not faltou) if ciclo_ligado else True,
        "modo_ciclo": ciclo_info["modo"],
        "ciclo_ligado": ciclo_ligado,
        "ciclo_fim_max": ciclo_info["limiar"],
        "ciclo_panorama": ciclo_info,
        "k": k,
        "dezena_min": dmin,
        "dezena_max": dmax,
        "ultimo_numeros": ultimo_nums,
        "alvo": alvo,
        "diagonais": _resumo_diagonais_janela(linhas_basicas, dmin, dmax),
        "padroes_usados": pads,
        "padroes_distintos": len(set(pads)),
        "padrao_inedito": None,
        "apostas_unicas": len({tuple(a["dezenas"]) for a in apostas_out}) == len(apostas_out),
        "sementes": len(sementes),
    }
