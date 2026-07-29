# -*- coding: utf-8 -*-
"""Factory de serviços por modalidade."""
from __future__ import annotations

from typing import Type

from analise_estudos.base_service import AnaliseEstudosBase
from analise_estudos.specs import get_estudos_config


def make_estudos_base(modality_key: str) -> Type[AnaliseEstudosBase]:
    get_estudos_config(modality_key)
    name = "".join(p.capitalize() for p in modality_key.replace("diadesorte", "dia_de_sorte").split("_"))
    return type(
        f"AnaliseEstudos{name}Base",
        (AnaliseEstudosBase,),
        {"modality_key": modality_key},
    )
