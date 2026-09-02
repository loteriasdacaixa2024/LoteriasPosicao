# -*- coding: utf-8 -*-
"""Factory — classe de serviço por modalidade."""
from __future__ import annotations

from typing import Type

from .service import AnalisePosicaoService
from .specs import get_posicao_spec


def make_service(modality_key: str) -> Type[AnalisePosicaoService]:
    spec = get_posicao_spec(modality_key)
    name = "".join(p.capitalize() for p in modality_key.replace("diadesorte", "dia_de_sorte").split("_"))
    return type(
        f"AnalisePosicao{name}Service",
        (AnalisePosicaoService,),
        {"modality_key": modality_key, "spec": spec},
    )
