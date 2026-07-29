# -*- coding: utf-8 -*-
"""Exportação composta — apostas de múltiplas bases estatísticas."""
from __future__ import annotations

from typing import Any, Dict, List

from geradores_elite.engine_final_core import get_config, _fmt_dezena
from geradores_elite.comportamento.specs import MESES_ABREV


def _linha_dezenas_mes(cfg: Dict[str, Any], item: Dict[str, Any]) -> str:
    joiner = cfg.get("export_join", " ")
    nums = item.get("dezenas") or []
    if cfg.get("export_is_columns"):
        dez = "".join(str(n) for n in nums)
    else:
        dez = joiner.join(_fmt_dezena(n, cfg) for n in nums)
    mes = item.get("mes") or item.get("mes_num")
    if mes and cfg.get("extra") == "mes":
        abrev = item.get("mes_abrev") or MESES_ABREV.get(int(mes), "")
        if abrev:
            return f"{dez} {abrev}"
    return dez


def formatar_export_composto(modality_key: str, itens: List[Dict[str, Any]]) -> str:
    """Uma linha por aposta: dezenas + mês abreviado (sem cabeçalhos)."""
    cfg = get_config(modality_key)
    lines = [_linha_dezenas_mes(cfg, item) for item in itens]
    return "\n".join(lines).rstrip() + "\n"
