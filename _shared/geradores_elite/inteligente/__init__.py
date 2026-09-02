# -*- coding: utf-8 -*-
"""Registro do gerador inteligente por modalidade."""
from __future__ import annotations

from typing import Any, Dict, Optional, Type

from analise_repeticao.repeticao_config import REPETICAO_PARAMS

from .extras import DiaDeSorteInteligente, MaisMilionariaInteligente, TimemaniaInteligente
from .lotofacil import LotofacilInteligente
from .pool import (
    DuplaSenaInteligente,
    LotomaniaInteligente,
    MegaSenaInteligente,
    PoolInteligenteService,
    QuinaInteligente,
)

REGISTRY: Dict[str, Type[PoolInteligenteService]] = {
    "lotofacil": LotofacilInteligente,
    "quina": QuinaInteligente,
    "megasena": MegaSenaInteligente,
    "lotomania": LotomaniaInteligente,
    "duplasena": DuplaSenaInteligente,
    "diadesorte": DiaDeSorteInteligente,
    "timemania": TimemaniaInteligente,
    "maismilionaria": MaisMilionariaInteligente,
}


def get_inteligente_service(modality_key: str) -> Optional[Any]:
    """Retorna a classe do serviço inteligente ou None."""
    if modality_key in REGISTRY:
        return REGISTRY[modality_key]
    if modality_key == "supersete":
        try:
            from services.sniper_gerador_service import SniperGeradorService

            return SniperGeradorService
        except ImportError:
            pass
    return None


def modalidades_inteligentes() -> list:
    keys = list(REGISTRY.keys())
    if "supersete" not in keys:
        keys.append("supersete")
    return sorted(keys)


def tem_gerador_inteligente(modality_key: str) -> bool:
    if modality_key in REGISTRY:
        return True
    if modality_key == "supersete":
        return True
    return modality_key in REPETICAO_PARAMS


GERADORES_ELITE_MENU_TITLES = (
    "Engine Final",
    "Repetição → Apostas",
    "Sniper → Apostas",
)


def _load_comportamento_registry() -> Dict[str, Type]:
    from .comportamento_modalidades import (
        ComportamentoDiaDeSorteInteligente,
        ComportamentoDuplaSenaInteligente,
        ComportamentoLotofacilInteligente,
        ComportamentoLotomaniaInteligente,
        ComportamentoMaisMilionariaInteligente,
        ComportamentoMegaSenaInteligente,
        ComportamentoQuinaInteligente,
        ComportamentoSuperSeteInteligente,
        ComportamentoTimemaniaInteligente,
    )

    return {
        "lotofacil": ComportamentoLotofacilInteligente,
        "megasena": ComportamentoMegaSenaInteligente,
        "diadesorte": ComportamentoDiaDeSorteInteligente,
        "quina": ComportamentoQuinaInteligente,
        "timemania": ComportamentoTimemaniaInteligente,
        "duplasena": ComportamentoDuplaSenaInteligente,
        "maismilionaria": ComportamentoMaisMilionariaInteligente,
        "lotomania": ComportamentoLotomaniaInteligente,
        "supersete": ComportamentoSuperSeteInteligente,
    }


def get_comportamento_service(modality_key: str) -> Optional[Any]:
    reg = _load_comportamento_registry()
    return reg.get(modality_key)


def tem_gerador_comportamento(modality_key: str) -> bool:
    return get_comportamento_service(modality_key) is not None
