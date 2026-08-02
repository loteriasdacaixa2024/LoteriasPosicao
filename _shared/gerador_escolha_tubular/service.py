# -*- coding: utf-8 -*-
"""Gerador Escolha/Tubular — apostas a partir dos padrões das análises."""
from __future__ import annotations

import random
import re
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from analise_estudos.service_factory import make_estudos_base
from analise_estudos.specs import get_estudos_config, tem_analise_estudos
from analise_tubular_inteligente.service import AnaliseTubularInteligenteService
from geradores_elite.modality_config import MODALITIES

MESES_NOME_NUM = {
    "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4,
    "Maio": 5, "Junho": 6, "Julho": 7, "Agosto": 8,
    "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12,
}


def tem_gerador_escolha_tubular(modality_key: str) -> bool:
    return tem_analise_estudos(modality_key) and modality_key in MODALITIES


def _parse_pares_impares(desc: str) -> Optional[Tuple[int, int]]:
    m = re.search(r"(\d+)\s*P\s*/\s*(\d+)\s*I", desc or "", re.I)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _parse_soma(desc: str) -> Optional[int]:
    m = re.search(r"Soma\s+(\d+)", desc or "", re.I)
    return int(m.group(1)) if m else None


def _parse_digitos(desc: str) -> Optional[int]:
    m = re.search(r"(\d+)\s+d[ií]gitos", desc or "", re.I)
    return int(m.group(1)) if m else None


def _tem_sequencia(nums: Sequence[int]) -> bool:
    s = sorted(int(x) for x in nums)
    return any(s[i + 1] - s[i] == 1 for i in range(len(s) - 1))


def _tem_finais_iguais(nums: Sequence[int]) -> bool:
    seen: Dict[int, int] = {}
    for n in nums:
        d = int(n) % 10
        seen[d] = seen.get(d, 0) + 1
        if seen[d] > 1:
            return True
    return False


def _digitos_unicos(nums: Sequence[int]) -> int:
    return len({int(d) for n in nums for d in f"{int(n):02d}"})


def _alvo_de_analise(analise: Dict[str, Any]) -> Dict[str, Any]:
    pi = (analise.get("pares_impares") or [{}])[0]
    soma = ((analise.get("somas") or {}).get("padroes") or [{}])[0]
    dig = (analise.get("digitos_unicos") or [{}])[0]
    seq = ((analise.get("sequencias") or {}).get("padroes") or [{}])[0]
    finais = (analise.get("finais") or [{}])[0]
    meses = analise.get("meses") or []
    rep = analise.get("repeticoes") or {}

    pares_alvo = _parse_pares_impares(pi.get("descricao", ""))
    soma_alvo = _parse_soma(soma.get("descricao", ""))
    dig_alvo = _parse_digitos(dig.get("descricao", ""))
    quer_seq = bool(seq.get("descricao") and seq["descricao"] != "Sem sequência")
    quer_finais = bool(finais.get("frequencia")) and "Sem finais" not in str(finais.get("descricao", ""))
    mes_top = None
    if meses:
        mes_top = MESES_NOME_NUM.get(meses[0].get("descricao", ""))

    return {
        "pares": pares_alvo[0] if pares_alvo else None,
        "impares": pares_alvo[1] if pares_alvo else None,
        "soma": soma_alvo,
        "digitos": dig_alvo,
        "quer_sequencia": quer_seq,
        "quer_finais": quer_finais,
        "mes_sugerido": mes_top,
        "rep_pct": float(rep.get("percentual") or 0),
        "padroes_resumo": {
            "par_impar": pi.get("descricao"),
            "soma": soma.get("descricao"),
            "digitos": dig.get("descricao"),
            "sequencia": seq.get("descricao"),
            "finais": finais.get("descricao"),
            "mes": meses[0].get("descricao") if meses else None,
            "repeticoes_pct": rep.get("percentual"),
        },
    }


def _score_aposta(
    nums: List[int],
    alvo: Dict[str, Any],
    *,
    ultimo: Optional[List[int]],
    usar_pi: bool,
    usar_soma: bool,
    usar_seq: bool,
    usar_finais: bool,
    usar_rep: bool,
    usar_dig: bool,
) -> float:
    score = 0.0
    pares = sum(1 for n in nums if n % 2 == 0)

    if usar_pi and alvo.get("pares") is not None:
        score -= abs(pares - int(alvo["pares"])) * 4.0

    if usar_soma and alvo.get("soma") is not None:
        score -= abs(sum(nums) - int(alvo["soma"])) * 0.35

    if usar_dig and alvo.get("digitos") is not None:
        score -= abs(_digitos_unicos(nums) - int(alvo["digitos"])) * 2.5

    if usar_seq:
        tem = _tem_sequencia(nums)
        if alvo.get("quer_sequencia") and tem:
            score += 3.0
        elif alvo.get("quer_sequencia") and not tem:
            score -= 3.0
        elif not alvo.get("quer_sequencia") and tem:
            score -= 1.0

    if usar_finais:
        tem = _tem_finais_iguais(nums)
        if alvo.get("quer_finais") and tem:
            score += 2.5
        elif alvo.get("quer_finais") and not tem:
            score -= 2.5

    if usar_rep and ultimo:
        reps = sum(1 for n in nums if n in ultimo)
        # tipicamente 1–2 repetidas no Dia de Sorte
        alvo_rep = 2 if float(alvo.get("rep_pct") or 0) >= 55 else 1
        score -= abs(reps - alvo_rep) * 2.0

    return score


def contexto_gerador(
    modality_key: str,
    *,
    janela: int = 0,
    base: str = "geral",
) -> Dict[str, Any]:
    if not tem_gerador_escolha_tubular(modality_key):
        return {"sucesso": False, "erro": "Indisponível para esta modalidade."}

    analise = AnaliseTubularInteligenteService.analisar(
        modality_key, base_estatistica=base, janela=janela,
    )
    if not analise.get("sucesso"):
        return analise

    alvo = _alvo_de_analise(analise)
    Base = make_estudos_base(modality_key)
    cfg = get_estudos_config(modality_key)
    mod = MODALITIES[modality_key]
    rows = Base.carregar_sorteios_asc(base_estatistica=base, janela=0)
    ultimo = [int(x) for x in Base.dezenas_ordem(rows[-1])] if rows else []
    # frequência recente (janela efetiva para peso do volante)
    janela_freq = janela if janela and janela > 0 else min(50, len(rows))
    recentes = rows[-janela_freq:] if janela_freq else rows
    freq: Dict[int, int] = {}
    for r in recentes:
        for n in Base.dezenas_ordem(r):
            freq[int(n)] = freq.get(int(n), 0) + 1

    return {
        "sucesso": True,
        "modality_key": modality_key,
        "modality_nome": cfg["nome"],
        "dezena_min": mod["dezena_min"],
        "dezena_max": mod["dezena_max"],
        "pick_default": mod["pick_default"],
        "pick_min": mod["pick_min"],
        "pick_max": mod["pick_max"],
        "sorteadas": mod["sorteadas"],
        "extra_mes": bool(cfg.get("extra_mes")),
        "janela": janela,
        "base": base,
        "total_concursos": analise.get("total_concursos"),
        "alvo": alvo,
        "ultimo_sorteio": {
            "concurso": int(rows[-1].concurso) if rows else None,
            "dezenas": ultimo,
        },
        "frequencias": [
            {"dezena": k, "freq": v}
            for k, v in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))
        ],
        "analise_links": {
            "escolha": "/analise/escolha-visual/",
            "tubular": "/analise/analise-tubular/",
        },
    }


def gerar_apostas(
    modality_key: str,
    *,
    quantidade: int = 10,
    pick: Optional[int] = None,
    janela: int = 0,
    base: str = "geral",
    usar_pares_impares: bool = True,
    usar_soma: bool = True,
    usar_sequencia: bool = True,
    usar_finais: bool = True,
    usar_repetidos: bool = True,
    usar_digitos: bool = True,
    mes_num: Optional[int] = None,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    ctx = contexto_gerador(modality_key, janela=janela, base=base)
    if not ctx.get("sucesso"):
        return ctx

    mod = MODALITIES[modality_key]
    pick_n = int(pick if pick is not None else ctx["pick_default"])
    pick_n = max(int(ctx["pick_min"]), min(int(ctx["pick_max"]), pick_n))
    qtd = max(1, min(int(quantidade or 10), 100))
    alvo = ctx["alvo"]
    ultimo = list(ctx.get("ultimo_sorteio", {}).get("dezenas") or [])
    universo = list(range(int(ctx["dezena_min"]), int(ctx["dezena_max"]) + 1))

    # peso por frequência recente (escolha visual / comportamento histórico)
    freq_map = {int(i["dezena"]): int(i["freq"]) for i in ctx.get("frequencias") or []}
    pesos = [1.0 + float(freq_map.get(n, 0)) for n in universo]

    rng = random.Random(seed)
    apostas: List[Dict[str, Any]] = []
    vistos: Set[Tuple[int, ...]] = set()
    tentativas = max(qtd * 80, 200)

    for _ in range(tentativas):
        if len(apostas) >= qtd:
            break

        # amostragem ponderada sem reposição
        pool = list(universo)
        w = list(pesos)
        escolhidos: List[int] = []
        for __ in range(pick_n):
            if not pool:
                break
            total_w = sum(w) or 1.0
            r = rng.random() * total_w
            acc = 0.0
            idx = 0
            for i, pw in enumerate(w):
                acc += pw
                if acc >= r:
                    idx = i
                    break
            escolhidos.append(pool.pop(idx))
            w.pop(idx)

        if len(escolhidos) != pick_n:
            continue
        nums = sorted(escolhidos)
        key = tuple(nums)
        if key in vistos:
            continue
        vistos.add(key)

        sc = _score_aposta(
            nums, alvo,
            ultimo=ultimo,
            usar_pi=usar_pares_impares,
            usar_soma=usar_soma,
            usar_seq=usar_sequencia,
            usar_finais=usar_finais,
            usar_rep=usar_repetidos,
            usar_dig=usar_digitos,
        )
        pares = sum(1 for n in nums if n % 2 == 0)
        item: Dict[str, Any] = {
            "dezenas": nums,
            "soma": sum(nums),
            "pares": pares,
            "impares": pick_n - pares,
            "tem_sequencia": _tem_sequencia(nums),
            "tem_finais_iguais": _tem_finais_iguais(nums),
            "digitos_unicos": _digitos_unicos(nums),
            "repetidas_ultimo": [n for n in nums if n in ultimo],
            "score": round(sc, 2),
        }
        apostas.append(item)

    apostas.sort(key=lambda a: a["score"], reverse=True)
    apostas = apostas[:qtd]
    for i, a in enumerate(apostas, start=1):
        a["indice"] = i

    mes_final = mes_num
    if mes_final is None and ctx.get("extra_mes"):
        mes_final = alvo.get("mes_sugerido")

    return {
        "sucesso": True,
        "ok": True,
        "modality_key": modality_key,
        "quantidade": len(apostas),
        "pick": pick_n,
        "janela": janela,
        "base": base,
        "alvo": alvo,
        "mes_num": mes_final,
        "apostas": apostas,
        "contexto": {
            "padroes_resumo": alvo.get("padroes_resumo"),
            "ultimo_sorteio": ctx.get("ultimo_sorteio"),
            "total_concursos": ctx.get("total_concursos"),
        },
    }
