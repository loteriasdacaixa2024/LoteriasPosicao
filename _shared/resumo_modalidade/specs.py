# -*- coding: utf-8 -*-
"""Faixas e rótulos do resumo operacional por modalidade."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class ResumoSpec:
    modality_key: str
    nome: str
    enabled: bool
    dezena_min: int
    dezena_max: int
    sorteadas: int
    faixas: Tuple[Tuple[str, int, int, str], ...]  # codigo, lo, hi, label
    extra_label: str = ""


_SPECS: Dict[str, ResumoSpec] = {
    "diadesorte": ResumoSpec(
        modality_key="diadesorte",
        nome="Dia de Sorte",
        enabled=True,
        dezena_min=1,
        dezena_max=31,
        sorteadas=7,
        faixas=(
            ("B", 1, 10, "Baixas 01–10"),
            ("M", 11, 20, "Médias 11–20"),
            ("A", 21, 31, "Altas 21–31"),
        ),
        extra_label="Mês da Sorte",
    ),
}


def get_resumo_spec(key: str) -> ResumoSpec:
    spec = _SPECS.get((key or "").strip().lower())
    if spec is None:
        raise KeyError(f"Resumo operacional não definido para {key}")
    return spec


def tem_resumo_modalidade(key: str) -> bool:
    spec = _SPECS.get((key or "").strip().lower())
    return bool(spec and spec.enabled)


def faixa_de(n: int, spec: ResumoSpec) -> Optional[str]:
    for codigo, lo, hi, _lbl in spec.faixas:
        if lo <= n <= hi:
            return codigo
    return None
