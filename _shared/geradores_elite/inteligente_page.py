# -*- coding: utf-8 -*-
"""Contexto de página — Apostas inteligentes (todas as modalidades)."""
from __future__ import annotations

from typing import Any, Dict

from analise_comparar.compare_config import get_compare_config
from analise_repeticao.repeticao_config import get_repeticao_config, get_repeticao_ui_context

from geradores_elite.inteligente import get_inteligente_service, tem_gerador_inteligente
from geradores_elite.modality_config import MODALITIES


def repeticao_cfg_for_page(modality_key: str) -> Dict[str, Any]:
    if modality_key == "lotofacil":
        mod = MODALITIES["lotofacil"]
        return {
            "key": "lotofacil",
            "nome": mod["nome"],
            "dezenas_min": 15,
            "dezenas_max": 20,
            "dezenas_default": 15,
            "sorteadas": 15,
            "slots_por_concurso": 15,
            "show_volante_apostas": True,
            "modos": ["volante", "posicional", "hibrido"],
            "dezena_min": 1,
            "dezena_max": 25,
            "grid_cols": 10,
            "export_join": " ",
        }
    return get_repeticao_config(modality_key)


def compare_cfg_for_page(modality_key: str) -> Dict[str, Any]:
    if modality_key == "lotofacil":
        return {
            "key": "lotofacil",
            "layout": "posicional",
            "dezena_min": 1,
            "dezena_max": 25,
        }
    return get_compare_config(modality_key)


def page_context(modality_key: str) -> Dict[str, Any]:
    if not tem_gerador_inteligente(modality_key):
        raise ValueError(f"Modalidade sem gerador inteligente: {modality_key}")

    mod = MODALITIES[modality_key]
    rep_cfg = repeticao_cfg_for_page(modality_key)
    ui_ctx = get_repeticao_ui_context(modality_key)
    cmp = compare_cfg_for_page(modality_key)

    svc = get_inteligente_service(modality_key)
    inteligente_ui: Dict[str, Any] = {
        "layout": "colunas" if cmp.get("layout") == "colunas" else "pool",
        "foco_min": cmp.get("dezena_min", 0),
        "foco_max": cmp.get("dezena_max", 9),
        "show_extra_mes": bool(cmp.get("extra_mes")),
        "show_extra_time": bool(cmp.get("extra_time")),
        "show_extra_trevo": bool(cmp.get("extra_trevos")),
        "tipos_box_title": "Faixas de repetição" if modality_key != "supersete" else "Tipo de sorteio",
        "colunas_box_title": "Colunas mais fortes" if cmp.get("layout") == "colunas" else "Maior permanência",
    }
    if svc and hasattr(svc, "ui_config"):
        inteligente_ui.update(svc.ui_config())

    if modality_key == "supersete":
        api_base = "/geradores-elite/api/sniper-coluna"
        page_subtitle = "Colunas C1–C7 · evidências · automático ou manual"
        inteligente_ui["layout"] = "colunas"
    else:
        api_base = "/geradores-elite/api/inteligente"
        page_subtitle = f"{mod['nome']} · evidências · automático ou manual"
    page_title = "Sniper → Apostas"

    return {
        "modality_key": modality_key,
        "modality_nome": rep_cfg.get("nome", mod["nome"]),
        "cfg": rep_cfg,
        "meses_cores": ui_ctx.get("meses_cores", {}),
        "api_base": api_base,
        "page_title": page_title,
        "page_subtitle": page_subtitle,
        "inteligente_ui": inteligente_ui,
    }
