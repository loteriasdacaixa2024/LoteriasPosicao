# -*- coding: utf-8 -*-
"""Configuração por modalidade — Análises Gerais."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, FrozenSet, Optional

BASES_ESTATISTICA = ("geral", "vencedores", "acumulados")
BASES_LABEL = {
    "geral": "Geral",
    "vencedores": "Concursos com Vencedores",
    "acumulados": "Concursos Acumulados",
}

_LINKS_PADRAO = {
    "posicao": "/analise/por-posicao/",
    "gerador_posicao": "/geradores-elite/gerador-por-posicao/",
    "comportamento": "/analise/comportamento/",
    "comportamento_apostas": "/geradores-elite/comportamento-apostas/",
    "analises_gerais": "/analise/analises-gerais/",
    "somas_digitos": "/analise/somas-digitos/",
    "construtor": "/geradores-elite/construtor-construcoes/",
    "concentracao": "/analise/concentracao-acertos/",
}

LINKS_MODALIDADE: Dict[str, Dict[str, str]] = {
    key: dict(_LINKS_PADRAO)
    for key in (
        "diadesorte",
        "quina",
        "megasena",
        "lotofacil",
        "timemania",
        "lotomania",
        "supersete",
        "maismilionaria",
        "duplasena",
    )
}


def links_modalidade(modality_key: str) -> Dict[str, str]:
    return dict(LINKS_MODALIDADE.get(modality_key, _LINKS_PADRAO))


def _estudos(
    key: str,
    nome: str,
    dmin: int,
    dmax: int,
    sorteadas: int,
    janelas: tuple,
    *,
    janela_default: int = 10,
    extra_mes: bool = False,
    extra_time: bool = False,
    extra_trevo: bool = False,
    volante_cols: int = 10,
    volante_rows: Optional[int] = None,
    ganhadores_field: Optional[str] = None,
    model_module: str = "",
    model_class: str = "",
    page_subtitle: str = "Estudos exploratórios — dígitos, somas e classificações",
) -> Dict[str, Any]:
    rows = volante_rows
    if rows is None:
        span = dmax - dmin + 1
        rows = max(1, (span + volante_cols - 1) // volante_cols)
    return {
        "key": key,
        "nome": nome,
        "dezena_min": dmin,
        "dezena_max": dmax,
        "sorteadas": sorteadas,
        "pad_width": 1 if dmax < 10 else 2,
        "janelas_ui": janelas,
        "janela_default": janela_default,
        "extra_mes": extra_mes,
        "extra_time": extra_time,
        "extra_trevo": extra_trevo,
        "volante_cols": volante_cols,
        "volante_rows": rows,
        "ganhadores_field": ganhadores_field,
        "model_module": model_module,
        "model_class": model_class,
        "page_subtitle": page_subtitle,
        "bases_ui": ("geral", "vencedores", "acumulados") if ganhadores_field else ("geral",),
    }


ESTUDOS_MODALITIES: Dict[str, Dict[str, Any]] = {
    "diadesorte": _estudos(
        "diadesorte", "Dia de Sorte", 1, 31, 7, (10, 20, 31, 0),
        extra_mes=True, volante_rows=4, ganhadores_field="ganhadores_7",
        model_module="models.sorteio_diadesorte", model_class="SorteioDiaDeSorte",
    ),
    "quina": _estudos(
        "quina", "Quina", 1, 80, 5, (10, 20, 50, 80, 0),
        volante_rows=8,
        model_module="models.sorteio_quina", model_class="SorteioQuina",
    ),
    "megasena": _estudos(
        "megasena", "Mega-Sena", 1, 60, 6, (10, 20, 60, 0),
        volante_rows=6,
        model_module="models.sorteio_megasena", model_class="SorteioMegaSena",
    ),
    "lotofacil": _estudos(
        "lotofacil", "Lotofácil", 1, 25, 15, (10, 20, 50, 0),
        volante_cols=5, volante_rows=5,
        model_module="models.sorteio_lotofacil", model_class="SorteioLotofacil",
    ),
    "timemania": _estudos(
        "timemania", "Timemania", 1, 80, 7, (10, 20, 50, 80, 0),
        janela_default=50, volante_rows=8, extra_time=True,
        model_module="models.sorteio_timemania", model_class="SorteioTimemania",
    ),
    "lotomania": _estudos(
        "lotomania", "Lotomania", 0, 99, 20, (10, 20, 50, 100, 0),
        volante_rows=10,
        model_module="models.sorteio_lotomania", model_class="SorteioLotomania",
    ),
    "maismilionaria": _estudos(
        "maismilionaria", "+Milionária", 1, 50, 6, (10, 20, 50, 0),
        volante_rows=5, extra_trevo=True,
        model_module="models.sorteio_maismilionaria", model_class="SorteioMaisMilionaria",
    ),
    "duplasena": _estudos(
        "duplasena", "Dupla Sena", 1, 50, 6, (10, 20, 50, 0),
        volante_rows=5,
        model_module="models.sorteio_duplasena", model_class="SorteiosDuplaSena",
        page_subtitle="Estudos exploratórios — perfil do 1º sorteio (aposta compete nos dois)",
    ),
    "supersete": _estudos(
        "supersete", "Super Sete", 0, 9, 7, (10, 20, 30, 0),
        volante_cols=10, volante_rows=1,
        model_module="models.sorteio_supersete", model_class="SorteioSuperSete",
        page_subtitle="Estudos exploratórios — dígitos e classificações por coluna",
    ),
}


def get_estudos_config(modality_key: str) -> Dict[str, Any]:
    if modality_key not in ESTUDOS_MODALITIES:
        raise ValueError(f"Modalidade sem Análises Gerais: {modality_key}")
    return deepcopy(ESTUDOS_MODALITIES[modality_key])


def tem_analise_estudos(modality_key: str) -> bool:
    return modality_key in ESTUDOS_MODALITIES


def janelas_validas(modality_key: str) -> FrozenSet[int]:
    cfg = get_estudos_config(modality_key)
    return frozenset(cfg["janelas_ui"])
