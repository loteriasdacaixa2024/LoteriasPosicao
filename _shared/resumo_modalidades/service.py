# -*- coding: utf-8 -*-
"""Monta os cards da modalidade e do ciclo a partir das fontes já usadas no sistema."""
from __future__ import annotations

from typing import Any, Dict, List

from ciclo_cobertura.analise_service import AnaliseCicloCoberturaService
from ciclo_cobertura.loaders import _resolver_model
from ciclo_cobertura.specs import get_ciclo_spec

from resumo_modalidades.specs import CardModalidade, modalidades_da_pagina


def _fmt_milhar(n: int) -> str:
    return f"{int(n):,}".replace(",", ".")


def _contagem_banco(modality_key: str) -> Dict[str, int]:
    """Mesma conta da home: total de registros e maior concurso gravado."""
    from models.shared import db

    spec = get_ciclo_spec(modality_key)
    Model = _resolver_model(spec)
    total = db.session.query(Model).count()
    ultimo = db.session.query(db.func.max(Model.concurso)).scalar() or 0
    return {"total": int(total or 0), "ultimo": int(ultimo or 0)}


def _top3(modality_key: str, pendentes: List[int]) -> List[int]:
    try:
        bruto = AnaliseCicloCoberturaService.obter_dezenas_sugeridas(modality_key, 3)
    except Exception:
        bruto = pendentes[:3]
    faltam = set(pendentes)
    top: List[int] = []
    for n in bruto or []:
        d = int(n)
        if d in faltam and d not in top:
            top.append(d)
        if len(top) == 3:
            break
    if len(top) < 3:
        for d in pendentes:
            if d not in top:
                top.append(d)
            if len(top) == 3:
                break
    return top


def montar_modalidade(card: CardModalidade) -> Dict[str, Any]:
    ciclo_spec = get_ciclo_spec(card.key)
    banco = _contagem_banco(card.key)
    ciclo = AnaliseCicloCoberturaService.obter_ciclo_atual(card.key)
    pendentes = [int(n) for n in (ciclo or {}).get("dezenas_pendentes") or []]
    top = _top3(card.key, pendentes) if pendentes else []
    ranks = {d: i + 1 for i, d in enumerate(top)}
    universo = int((ciclo or {}).get("universo") or ciclo_spec.universo_size)
    saidas = int((ciclo or {}).get("total_dezenas_saidas") or 0)

    return {
        "key": card.key,
        "nome": card.nome,
        "concursos": _fmt_milhar(banco["total"]) if banco["total"] else "0",
        "ultimo": f"#{banco['ultimo']}" if banco["ultimo"] else "—",
        "dezenas": str(universo),
        "extra_valor": card.extra_valor,
        "extra_rotulo": card.extra_rotulo,
        "extra_cor": card.extra_cor,
        "ciclo_numero": f"#{ciclo['numero_ciclo']}" if ciclo else "—",
        "ciclo_concursos": str(ciclo["quantidade_concursos"]) if ciclo else "—",
        "ciclo_saidas": f"{saidas}/{universo}" if ciclo else "—",
        "ciclo_pendentes": str(len(pendentes)) if ciclo else "—",
        "n_pendentes": len(pendentes),
        "chips": [
            {"txt": f"{d:02d}", "rank": ranks.get(d)}
            for d in pendentes
        ],
    }


def montar_pagina() -> Dict[str, Any]:
    blocos = [montar_modalidade(card) for card in modalidades_da_pagina()]
    return {"sucesso": bool(blocos), "modalidades": blocos}
