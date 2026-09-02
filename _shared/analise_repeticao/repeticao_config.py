# -*- coding: utf-8 -*-
"""Configuração — Repetição entre concursos + gerador."""
from analise_comparar.compare_config import get_compare_config

REPETICAO_PARAMS = {
    "lotofacil": {
        "dezenas_min": 15,
        "dezenas_max": 20,
        "dezenas_default": 15,
        "sorteadas": 15,
        "slots_por_concurso": 15,
        "show_volante_apostas": True,
    },
    "lotomania": {
        "dezenas_min": 50,
        "dezenas_max": 50,
        "dezenas_default": 50,
        "sorteadas": 20,
        "slots_por_concurso": 20,
        "show_volante_apostas": True,
    },
    "quina": {
        "dezenas_min": 5,
        "dezenas_max": 15,
        "dezenas_default": 5,
        "sorteadas": 5,
        "slots_por_concurso": 5,
        "show_volante_apostas": True,
    },
    "megasena": {
        "dezenas_min": 6,
        "dezenas_max": 15,
        "dezenas_default": 6,
        "sorteadas": 6,
        "slots_por_concurso": 6,
        "show_volante_apostas": True,
    },
    "diadesorte": {
        "dezenas_min": 7,
        "dezenas_max": 15,
        "dezenas_default": 7,
        "sorteadas": 7,
        "slots_por_concurso": 7,
        "show_volante_apostas": True,
    },
    "duplasena": {
        "dezenas_min": 6,
        "dezenas_max": 15,
        "dezenas_default": 6,
        "sorteadas": 6,
        "slots_por_concurso": 6,
        "default_sorteio": 1,
        "show_volante_apostas": True,
    },
    "maismilionaria": {
        "dezenas_min": 6,
        "dezenas_max": 12,
        "dezenas_default": 6,
        "sorteadas": 6,
        "slots_por_concurso": 6,
        "show_volante_apostas": True,
        "trevo_pick": 2,
    },
    "timemania": {
        "dezenas_min": 10,
        "dezenas_max": 10,
        "dezenas_default": 10,
        "sorteadas": 10,
        "slots_por_concurso": 10,
        "show_volante_apostas": True,
    },
    "supersete": {
        "dezenas_min": 7,
        "dezenas_max": 7,
        "dezenas_default": 7,
        "sorteadas": 7,
        "slots_por_concurso": 7,
        "show_volante_apostas": True,
        "volante_max_width": 400,
        "export_join": "-",
    },
}


def get_repeticao_config(modality_key: str) -> dict:
    if modality_key not in REPETICAO_PARAMS:
        raise ValueError(f"Modalidade sem repetição configurada: {modality_key}")
    cfg = get_compare_config(modality_key)
    cfg.update(REPETICAO_PARAMS[modality_key])
    cfg["key"] = modality_key
    return cfg


def get_repeticao_ui_context(modality_key: str) -> dict:
    """Dados extras para templates (ex.: cores dos meses no Dia de Sorte)."""
    meses_cores: dict = {}
    if modality_key == "diadesorte":
        try:
            from services.cores_meses_service import CoresMesesService

            meses_cores = CoresMesesService.obter_cores() or {}
        except Exception:
            pass
    return {"meses_cores": meses_cores}
