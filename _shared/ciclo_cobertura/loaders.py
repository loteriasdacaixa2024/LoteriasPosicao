# -*- coding: utf-8 -*-
"""Carrega sorteios em ordem crescente — adapter por modalidade."""
from __future__ import annotations

import importlib
from typing import Any, List

from .specs import CicloCoberturaSpec, get_ciclo_spec


def _resolver_model(spec: CicloCoberturaSpec):
    if not spec.model_import:
        raise RuntimeError(f"Spec {spec.modality_key} sem model_import")
    mod_name, cls_name = spec.model_import
    mod = importlib.import_module(mod_name)
    return getattr(mod, cls_name)


def _dezenas_sorteio(s: Any) -> List[int]:
    if hasattr(s, "dezenas_lista"):
        return [int(x) for x in s.dezenas_lista()]
    if hasattr(s, "dezenas"):
        dz = s.dezenas()
        if isinstance(dz, set):
            return sorted(int(x) for x in dz)
        return [int(x) for x in dz]
    return []


def carregar_sorteios_asc(modality_key: str) -> List[dict]:
    """Lista [{concurso, data, dezenas}] em ordem crescente de concurso."""
    from models.shared import db

    spec = get_ciclo_spec(modality_key)
    Model = _resolver_model(spec)
    rows = db.session.query(Model).order_by(Model.concurso.asc()).all()
    out = []
    for s in rows:
        dez = _dezenas_sorteio(s)
        if not dez:
            continue
        out.append({
            "concurso": int(s.concurso),
            "data": getattr(s, "data", "") or "",
            "dezenas": dez,
            "mes_num": getattr(s, "mes_num", None),
            "mes_nome": getattr(s, "mes_nome", None) or "",
        })
    return out
