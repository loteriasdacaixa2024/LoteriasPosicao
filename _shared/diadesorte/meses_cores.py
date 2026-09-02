# -*- coding: utf-8 -*-
"""Cores padronizadas dos meses — Dia de Sorte (config_meses.json)."""
from __future__ import annotations

import json
import os
from typing import Dict, Optional

MESES_NOME = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}

DEFAULT_MESES_CORES: Dict[str, str] = {
    "Janeiro": "#e74c3c",
    "Fevereiro": "#9b59b6",
    "Março": "#3498db",
    "Abril": "#e67e22",
    "Maio": "#f1c40f",
    "Junho": "#2ecc71",
    "Julho": "#1abc9c",
    "Agosto": "#34495e",
    "Setembro": "#196f3d",
    "Outubro": "#d35400",
    "Novembro": "#8e44ad",
    "Dezembro": "#c0392b",
}


def _base_dir() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def obter_meses_cores(base_dir: Optional[str] = None) -> Dict[str, str]:
    root = base_dir or _base_dir()
    path = os.path.join(root, "AnalisePorPosicao--DiaDeSorte-Only", "config_meses.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and data:
            out = dict(DEFAULT_MESES_CORES)
            out.update(data)
            return out
    except Exception:
        pass
    return dict(DEFAULT_MESES_CORES)


def cor_do_mes(
    mes_num: Optional[int] = None,
    mes_nome: Optional[str] = None,
    meses_cores: Optional[Dict[str, str]] = None,
) -> str:
    cores = meses_cores or obter_meses_cores()
    nome = mes_nome or MESES_NOME.get(int(mes_num or 0), "")
    return cores.get(nome, "#6c757d")
