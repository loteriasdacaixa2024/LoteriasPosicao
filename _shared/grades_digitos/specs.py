# -*- coding: utf-8 -*-
"""Modalidades em que a análise Grades de Dígitos entra no menu."""
from __future__ import annotations

from typing import Any, Dict

GRADES_MODALITIES: Dict[str, Dict[str, Any]] = {
    "diadesorte": {
        "nome": "Dia de Sorte",
        "dezena_min": 1,
        "dezena_max": 31,
        "model_module": "models.sorteio_diadesorte",
        "model_class": "SorteioDiaDeSorte",
    },
}


def tem_grades_digitos(modality_key: str) -> bool:
    return modality_key in GRADES_MODALITIES


def get_grades_config(modality_key: str) -> Dict[str, Any]:
    if modality_key not in GRADES_MODALITIES:
        raise KeyError(f"Grades de dígitos não configurada para {modality_key}")
    return GRADES_MODALITIES[modality_key]
