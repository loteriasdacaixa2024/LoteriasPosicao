# -*- coding: utf-8 -*-
"""Último sorteio — Concentração de Acertos."""
from __future__ import annotations

from typing import Any, Dict, Optional

from .specs import get_concentracao_config, tem_concentracao_acertos


def obter_ultimo_sorteio(modality_key: str) -> Optional[Dict[str, Any]]:
    if not tem_concentracao_acertos(modality_key):
        return None
    try:
        from geradores_elite.construtor.construtor_modalidades import CONSTRUTOR_REGISTRY

        svc = CONSTRUTOR_REGISTRY.get(modality_key)
        if svc:
            ult = svc.obter_ultimo_sorteio()
            if ult.get("sucesso"):
                return ult
    except Exception:
        pass
    try:
        import importlib

        cfg = get_concentracao_config(modality_key)
        mod = importlib.import_module(cfg["analise_module"])
        cls = getattr(mod, cfg["analise_class"])
        ultimos = cls.ultimos_sorteios()
        if not ultimos:
            return None
        u = ultimos[0]
        return {
            "sucesso": True,
            "concurso": u["concurso"],
            "data": u["data"],
            "dezenas": u.get("dezenas_ordem") or u.get("dezenas") or [],
            "mes_nome": u.get("mes_nome"),
            "mes_abrev": u.get("mes_abrev"),
            "mes_num": u.get("mes_num"),
        }
    except Exception:
        return None
