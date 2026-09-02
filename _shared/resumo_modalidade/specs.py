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
    padrao_hipotese: str = ""
    model_import: Optional[Tuple[str, str]] = None
    motor: str = "conjunto"  # conjunto | colunas


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
        padrao_hipotese="0-0-0-1-1-2-2",
        model_import=("models.sorteio_diadesorte", "SorteioDiaDeSorte"),
    ),
    "lotofacil": ResumoSpec(
        modality_key="lotofacil",
        nome="Lotofácil",
        enabled=True,
        dezena_min=1,
        dezena_max=25,
        sorteadas=15,
        faixas=(
            ("B", 1, 8, "Baixas 01–08"),
            ("M", 9, 17, "Médias 09–17"),
            ("A", 18, 25, "Altas 18–25"),
        ),
        model_import=("models.sorteio_lotofacil", "SorteioLotofacil"),
    ),
    "lotomania": ResumoSpec(
        modality_key="lotomania",
        nome="Lotomania",
        enabled=True,
        dezena_min=0,
        dezena_max=99,
        sorteadas=20,
        faixas=(
            ("B", 0, 32, "Baixas 00–32"),
            ("M", 33, 65, "Médias 33–65"),
            ("A", 66, 99, "Altas 66–99"),
        ),
        model_import=("models.sorteio_lotomania", "SorteioLotomania"),
    ),
    "quina": ResumoSpec(
        modality_key="quina",
        nome="Quina",
        enabled=True,
        dezena_min=1,
        dezena_max=80,
        sorteadas=5,
        faixas=(
            ("B", 1, 26, "Baixas 01–26"),
            ("M", 27, 53, "Médias 27–53"),
            ("A", 54, 80, "Altas 54–80"),
        ),
        model_import=("models.sorteio_quina", "SorteioQuina"),
    ),
    "megasena": ResumoSpec(
        modality_key="megasena",
        nome="Mega-Sena",
        enabled=True,
        dezena_min=1,
        dezena_max=60,
        sorteadas=6,
        faixas=(
            ("B", 1, 20, "Baixas 01–20"),
            ("M", 21, 40, "Médias 21–40"),
            ("A", 41, 60, "Altas 41–60"),
        ),
        model_import=("models.sorteio_megasena", "SorteioMegaSena"),
    ),
    "maismilionaria": ResumoSpec(
        modality_key="maismilionaria",
        nome="+Milionária",
        enabled=True,
        dezena_min=1,
        dezena_max=50,
        sorteadas=6,
        faixas=(
            ("B", 1, 16, "Baixas 01–16"),
            ("M", 17, 33, "Médias 17–33"),
            ("A", 34, 50, "Altas 34–50"),
        ),
        extra_label="2 Trevos",
        model_import=("models.sorteio_maismilionaria", "SorteioMaisMilionaria"),
    ),
    "duplasena": ResumoSpec(
        modality_key="duplasena",
        nome="Dupla Sena",
        enabled=True,
        dezena_min=1,
        dezena_max=50,
        sorteadas=6,
        faixas=(
            ("B", 1, 16, "Baixas 01–16"),
            ("M", 17, 33, "Médias 17–33"),
            ("A", 34, 50, "Altas 34–50"),
        ),
        extra_label="1º sorteio",
        model_import=("models.sorteio_duplasena", "SorteiosDuplaSena"),
    ),
    "timemania": ResumoSpec(
        modality_key="timemania",
        nome="Timemania",
        enabled=True,
        dezena_min=1,
        dezena_max=80,
        sorteadas=10,
        faixas=(
            ("B", 1, 26, "Baixas 01–26"),
            ("M", 27, 53, "Médias 27–53"),
            ("A", 54, 80, "Altas 54–80"),
        ),
        extra_label="Time do Coração",
        model_import=("models.sorteio_timemania", "SorteioTimemania"),
    ),
    "supersete": ResumoSpec(
        modality_key="supersete",
        nome="Super Sete",
        enabled=True,
        dezena_min=0,
        dezena_max=9,
        sorteadas=7,
        faixas=(
            ("B", 0, 3, "Baixos 0–3"),
            ("M", 4, 6, "Médios 4–6"),
            ("A", 7, 9, "Altos 7–9"),
        ),
        extra_label="",
        model_import=("models.sorteio_supersete", "SorteioSuperSete"),
        motor="colunas",
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
