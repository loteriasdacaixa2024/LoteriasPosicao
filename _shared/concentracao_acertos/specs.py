# -*- coding: utf-8 -*-
"""Especificações — Concentração de Acertos (por modalidade)."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional

_GESTAO_PADRAO = {
    "estrategia_padrao": "A",
    "estrategias_ativas": ["A"],
    "parametros_padrao": {
        "criterio_pool": "freq",
        "perfil": "equilibrado",
        "quantidade": 10,
    },
    "msg_desativada": (
        "Estratégia temporariamente desativada. "
        "Com base nos testes mais recentes, esta não é a estratégia recomendada "
        "no momento. Ela foi mantida no sistema porque novos testes futuros poderão "
        "indicar novamente sua utilização."
    ),
}


def _conc(
    key: str,
    nome: str,
    dmin: int,
    dmax: int,
    aposta: int,
    pools: List[int],
    *,
    extra_mes: bool = False,
    pico_min: Optional[int] = None,
    media_min: float = 3.0,
    analise_module: str = "",
    analise_class: str = "",
    model_module: str = "",
    model_class: str = "",
) -> Dict[str, Any]:
    estrategias = []
    for i, size in enumerate(pools):
        eid = chr(ord("A") + i)
        estrategias.append({
            "id": eid,
            "nome": f"Estratégia {eid}",
            "pool_size": size,
            "desc": f"Seleção de {size} dezenas — toda geração restrita a este pool",
        })
    if pico_min is None:
        pico_min = max(2, aposta - 1)
    return {
        "key": key,
        "nome": nome,
        "dezena_min": dmin,
        "dezena_max": dmax,
        "aposta_dezenas": aposta,
        "extra_mes": extra_mes,
        "pico_min": pico_min,
        "media_min": media_min,
        "analise_module": analise_module,
        "analise_class": analise_class,
        "model_module": model_module,
        "model_class": model_class,
        "subtitle_analise": (
            "Maximizar acertos concentrados em uma única aposta — estudos e validações"
        ),
        "subtitle_gerador": (
            "Geração por pool restrito · concentração de acertos (experimental)"
        ),
        "estrategias": estrategias,
        "gestao_estrategias": deepcopy(_GESTAO_PADRAO),
    }


CONCENTRACAO_MODALITIES: Dict[str, Dict[str, Any]] = {
    "diadesorte": _conc(
        "diadesorte", "Dia de Sorte", 1, 31, 7, [16, 18, 20],
        extra_mes=True, pico_min=6,
        analise_module="services.analise_diadesorte_service",
        analise_class="AnaliseDiaDeSorteService",
        model_module="models.sorteio_diadesorte",
        model_class="SorteioDiaDeSorte",
    ),
    "quina": _conc(
        "quina", "Quina", 1, 80, 5, [20, 24, 30],
        pico_min=4, media_min=2.5,
        analise_module="services.analise_quina_service",
        analise_class="AnaliseQuinaService",
        model_module="models.sorteio_quina",
        model_class="SorteioQuina",
    ),
    "megasena": _conc(
        "megasena", "Mega-Sena", 1, 60, 6, [20, 24, 30],
        pico_min=5, media_min=2.8,
        analise_module="services.analise_megasena_service",
        analise_class="AnaliseMegaSenaService",
        model_module="models.sorteio_megasena",
        model_class="SorteioMegaSena",
    ),
    "lotofacil": _conc(
        "lotofacil", "Lotofácil", 1, 25, 15, [18, 20, 22],
        pico_min=13, media_min=10.0,
        analise_module="services.analise_lotofacil_service",
        analise_class="AnaliseLotofacilService",
        model_module="models.sorteio_lotofacil",
        model_class="SorteioLotofacil",
    ),
    "timemania": _conc(
        "timemania", "Timemania", 1, 80, 10, [24, 30, 36],
        pico_min=7, media_min=5.0,
        analise_module="services.analise_timemania_service",
        analise_class="AnaliseTimemaniaSService",
        model_module="models.sorteio_timemania",
        model_class="SorteioTimemania",
    ),
    "lotomania": _conc(
        "lotomania", "Lotomania", 0, 99, 50, [60, 70, 80],
        pico_min=15, media_min=12.0,
        analise_module="services.analise_lotomania_service",
        analise_class="AnaliseLotomaniaService",
        model_module="models.sorteio_lotomania",
        model_class="SorteioLotomania",
    ),
    "supersete": _conc(
        "supersete", "Super Sete", 0, 9, 7, [7, 8, 9],
        pico_min=3, media_min=2.5,
        analise_module="services.analise_supersete_service",
        analise_class="AnaliseSuperSeteService",
        model_module="models.sorteio_supersete",
        model_class="SorteioSuperSete",
    ),
}

# Pool 7–9 dígitos; geração posicional permite várias apostas com repetição.
CONCENTRACAO_MODALITIES["supersete"]["gestao_estrategias"]["parametros_padrao"] = {
    "criterio_pool": "freq",
    "perfil": "equilibrado",
    "quantidade": 10,
}

MSG_ESTRATEGIA_DESATIVADA_PADRAO = _GESTAO_PADRAO["msg_desativada"]


def _aplicar_gestao_estrategias(cfg: Dict[str, Any]) -> Dict[str, Any]:
    gestao = cfg.get("gestao_estrategias") or {}
    padrao = gestao.get("estrategia_padrao") or "A"
    ativas = set(gestao.get("estrategias_ativas") or [padrao])
    if padrao not in ativas:
        ativas.add(padrao)
    for est in cfg.get("estrategias", []):
        est["ativa"] = est["id"] in ativas
        est["padrao"] = est["id"] == padrao
    cfg["estrategia_padrao"] = padrao
    cfg["estrategias_ativas"] = sorted(ativas, key=lambda x: x)
    cfg["parametros_padrao"] = gestao.get("parametros_padrao") or {
        "criterio_pool": "freq",
        "perfil": "equilibrado",
        "quantidade": 10,
    }
    cfg["msg_estrategia_desativada"] = gestao.get(
        "msg_desativada", MSG_ESTRATEGIA_DESATIVADA_PADRAO
    )
    return cfg


def get_concentracao_config(modality_key: str) -> Dict[str, Any]:
    if modality_key not in CONCENTRACAO_MODALITIES:
        raise ValueError(f"Modalidade sem Concentração de Acertos: {modality_key}")
    return _aplicar_gestao_estrategias(deepcopy(CONCENTRACAO_MODALITIES[modality_key]))


def estrategia_esta_ativa(modality_key: str, estrategia_id: str) -> bool:
    cfg = get_concentracao_config(modality_key)
    return estrategia_id in set(cfg.get("estrategias_ativas") or [])


def tem_concentracao_acertos(modality_key: str) -> bool:
    return modality_key in CONCENTRACAO_MODALITIES
