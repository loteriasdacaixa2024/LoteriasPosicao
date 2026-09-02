# -*- coding: utf-8 -*-
"""Classificação Novas × Repetidas no ciclo + união dos dois últimos."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Set

from .loaders import carregar_sorteios_asc
from .specs import get_ciclo_spec


def classificar_historico(modality_key: str) -> List[dict]:
    """Percorre sorteios ASC e classifica cada concurso no ciclo de cobertura."""
    spec = get_ciclo_spec(modality_key)
    sorteios = carregar_sorteios_asc(modality_key)
    universo: Set[int] = set(range(spec.dezena_min, spec.dezena_max + 1))
    alvo = len(universo)

    ciclo_num = 1
    vistos: Set[int] = set()
    historico: List[dict] = []

    for s in sorteios:
        dez_set = set(int(x) for x in s["dezenas"])
        novas = sorted(dez_set - vistos)
        repetidas = sorted(dez_set & vistos)
        historico.append({
            "concurso": s["concurso"],
            "data": s.get("data") or "",
            "dezenas": sorted(dez_set),
            "novas": novas,
            "repetidas": repetidas,
            "qtd_novas": len(novas),
            "qtd_repetidas": len(repetidas),
            "ciclo_num": ciclo_num,
            "vistos_antes": len(vistos),
            "mes_num": s.get("mes_num"),
            "mes_nome": s.get("mes_nome") or "",
        })
        vistos |= dez_set
        if len(vistos) >= alvo:
            ciclo_num += 1
            vistos = set()

    return historico


def contexto_dois_ultimos(modality_key: str) -> Dict[str, Any]:
    """
    Pool dinâmico = UNIÃO das Novas e UNIÃO das Repetidas dos dois últimos
    concursos no banco. Sem prioridade entre concursos.
    Sempre ancora no último concurso disponível automaticamente.
    """
    spec = get_ciclo_spec(modality_key)
    if not spec.enabled:
        return {"ok": False, "erro": f"Ciclo de cobertura não habilitado para {spec.nome}."}

    historico = classificar_historico(modality_key)
    if len(historico) < 2:
        return {
            "ok": False,
            "erro": "São necessários pelo menos 2 concursos no banco.",
            "total_concursos": len(historico),
        }

    c_ant, c_ult = historico[-2], historico[-1]
    pool_novas = sorted(set(c_ant["novas"]) | set(c_ult["novas"]))
    pool_repetidas = sorted(set(c_ant["repetidas"]) | set(c_ult["repetidas"]))

    # Métricas auxiliares
    somas = [sum(h["dezenas"]) for h in historico if h.get("dezenas")]
    soma_media = round(sum(somas) / len(somas), 2) if somas else 0.0

    digitos_qtd = []
    for h in historico:
        fins = {d % 10 for d in h["dezenas"]}
        digitos_qtd.append(len(fins))
    modo_digitos = None
    if digitos_qtd:
        modo_digitos = Counter(digitos_qtd).most_common(1)[0][0]

    return {
        "ok": True,
        "modality_key": modality_key,
        "modality_nome": spec.nome,
        "spec": {
            "dezena_min": spec.dezena_min,
            "dezena_max": spec.dezena_max,
            "sorteadas": spec.sorteadas,
            "pick_min": spec.pick_min,
            "pick_max": spec.pick_max,
            "pick_default": spec.pick_default,
            "novas_fixas": spec.novas_fixas,
            "repetidas_fixas": spec.repetidas_fixas,
            "faixas": [{"nome": n, "min": lo, "max": hi} for n, lo, hi in spec.faixas],
            "universo_size": spec.universo_size,
        },
        "ultimo_concurso": c_ult["concurso"],
        "anterior_concurso": c_ant["concurso"],
        "concursos": [
            {
                "papel": "anterior",
                "concurso": c_ant["concurso"],
                "data": c_ant["data"],
                "dezenas": c_ant["dezenas"],
                "novas": c_ant["novas"],
                "repetidas": c_ant["repetidas"],
                "ciclo_num": c_ant["ciclo_num"],
                "mes_num": c_ant.get("mes_num"),
                "mes_nome": c_ant.get("mes_nome") or "",
            },
            {
                "papel": "ultimo",
                "concurso": c_ult["concurso"],
                "data": c_ult["data"],
                "dezenas": c_ult["dezenas"],
                "novas": c_ult["novas"],
                "repetidas": c_ult["repetidas"],
                "ciclo_num": c_ult["ciclo_num"],
                "mes_num": c_ult.get("mes_num"),
                "mes_nome": c_ult.get("mes_nome") or "",
            },
        ],
        "pool": {
            "novas": pool_novas,
            "repetidas": pool_repetidas,
            "fonte": "uniao_dois_ultimos",
            "prioridade": None,
        },
        "pool_ok": (
            len(pool_novas) >= spec.novas_fixas
            and len(pool_repetidas) >= spec.repetidas_fixas
        ),
        "estatisticas": {
            "soma_media_historica": soma_media,
            "digitos_distintos_modo": modo_digitos,
            "total_concursos": len(historico),
        },
    }


def metricas_padrao_2n1r(modality_key: str, janela: Optional[int] = None) -> Dict[str, Any]:
    """Frequência histórica: no concurso N+1, quantas dezenas vieram das Novas/Repetidas de N."""
    historico = classificar_historico(modality_key)
    if len(historico) < 2:
        return {"ok": False, "erro": "Histórico insuficiente.", "pares": 0}

    pares = historico if not janela else historico[-(janela + 1):]
    hits_novas = []
    hits_rep = []
    padrao_2n1r = 0
    total = 0

    for i in range(len(pares) - 1):
        ant, seg = pares[i], pares[i + 1]
        set_seg = set(seg["dezenas"])
        n_nov = len(set_seg & set(ant["novas"]))
        n_rep = len(set_seg & set(ant["repetidas"]))
        hits_novas.append(n_nov)
        hits_rep.append(n_rep)
        total += 1
        if n_nov == 2 and n_rep == 1:
            padrao_2n1r += 1

    return {
        "ok": True,
        "pares": total,
        "media_novas_no_seguinte": round(sum(hits_novas) / total, 3) if total else 0,
        "media_repetidas_no_seguinte": round(sum(hits_rep) / total, 3) if total else 0,
        "ocorrencias_exatas_2n1r": padrao_2n1r,
        "taxa_exata_2n1r_pct": round(100.0 * padrao_2n1r / total, 2) if total else 0,
        "nota": (
            "Heurística operacional — não é previsão. "
            "Mede quantas vezes o concurso seguinte repetiu exatamente 2 novas + 1 repetida do concurso anterior."
        ),
    }
