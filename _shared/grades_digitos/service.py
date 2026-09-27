# -*- coding: utf-8 -*-
"""Conferência da grade contra todos os concursos da modalidade."""
from __future__ import annotations

import importlib
from typing import Dict, List, Tuple

from grades_digitos.engine import conferir_grade, montar_grade, validar_inicios
from grades_digitos.specs import get_grades_config

_CACHE: Dict[str, Tuple[tuple, List[tuple]]] = {}


def _dezenas_do_sorteio(sorteio) -> set:
    if hasattr(sorteio, "dezenas_lista"):
        return set(int(n) for n in sorteio.dezenas_lista())
    bruto = sorteio.dezenas()
    return set(int(n) for n in bruto)


def _carregar_sorteios(modality_key: str) -> List[tuple]:
    cfg = get_grades_config(modality_key)
    mod = importlib.import_module(cfg["model_module"])
    model = getattr(mod, cfg["model_class"])
    from models.shared import db

    rows = (
        db.session.query(model)
        .order_by(model.concurso.asc())
        .all()
    )
    chave = (len(rows), int(rows[-1].concurso) if rows else 0)
    guardado = _CACHE.get(modality_key)
    if guardado and guardado[0] == chave:
        return guardado[1]
    sorteios = [
        (int(s.concurso), _dezenas_do_sorteio(s))
        for s in rows
    ]
    _CACHE[modality_key] = (chave, sorteios)
    return sorteios


def conferir(modality_key: str, inicios) -> dict:
    cfg = get_grades_config(modality_key)
    nums = validar_inicios(inicios)
    grade = montar_grade(nums)
    sorteios = _carregar_sorteios(modality_key)
    resultado = conferir_grade(
        grade,
        sorteios,
        int(cfg["dezena_min"]),
        int(cfg["dezena_max"]),
    )
    return {
        "inicios": nums,
        "grade": grade,
        "dezena_min": int(cfg["dezena_min"]),
        "dezena_max": int(cfg["dezena_max"]),
        **resultado,
    }
