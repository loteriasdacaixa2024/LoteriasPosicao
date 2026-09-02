# -*- coding: utf-8 -*-
"""Specs de ciclo de cobertura por modalidade — regras Caixa isoladas."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class CicloCoberturaSpec:
    modality_key: str
    nome: str
    enabled: bool
    dezena_min: int
    dezena_max: int
    sorteadas: int
    pick_default: int
    pick_min: int
    pick_max: int
    # Estratégia default: N novas + R repetidas do pool união
    novas_fixas: int = 2
    repetidas_fixas: int = 1
    # Faixas opcionais (balanceamento)
    faixas: Tuple[Tuple[str, int, int], ...] = ()
    # motor: conjunto clássico (Super Sete fica disabled)
    motor: str = "conjunto"
    # Import do modelo ORM: (module, class_name)
    model_import: Optional[Tuple[str, str]] = None

    @property
    def universo_size(self) -> int:
        return self.dezena_max - self.dezena_min + 1

    def faixa_de(self, n: int) -> Optional[str]:
        for nome, lo, hi in self.faixas:
            if lo <= n <= hi:
                return nome
        return None


_SPECS: Dict[str, CicloCoberturaSpec] = {
    "diadesorte": CicloCoberturaSpec(
        modality_key="diadesorte",
        nome="Dia de Sorte",
        enabled=True,
        dezena_min=1,
        dezena_max=31,
        sorteadas=7,
        pick_default=7,
        pick_min=7,
        pick_max=15,
        novas_fixas=2,
        repetidas_fixas=1,
        faixas=(
            ("L1", 1, 10),
            ("L2", 11, 20),
            ("L3", 21, 30),
            ("L4", 31, 31),
        ),
        motor="conjunto",
        model_import=("models.sorteio_diadesorte", "SorteioDiaDeSorte"),
    ),
    "lotofacil": CicloCoberturaSpec(
        modality_key="lotofacil",
        nome="Lotofácil",
        enabled=True,
        dezena_min=1,
        dezena_max=25,
        sorteadas=15,
        pick_default=15,
        pick_min=15,
        pick_max=20,
        novas_fixas=2,
        repetidas_fixas=1,
        faixas=(
            ("L1", 1, 5),
            ("L2", 6, 10),
            ("L3", 11, 15),
            ("L4", 16, 20),
            ("L5", 21, 25),
        ),
        model_import=("models.sorteio_lotofacil", "SorteioLotofacil"),
    ),
    "lotomania": CicloCoberturaSpec(
        modality_key="lotomania",
        nome="Lotomania",
        enabled=True,
        dezena_min=0,
        dezena_max=99,
        sorteadas=20,
        pick_default=50,
        pick_min=50,
        pick_max=50,
        novas_fixas=2,
        repetidas_fixas=1,
        faixas=(
            ("L1", 0, 24),
            ("L2", 25, 49),
            ("L3", 50, 74),
            ("L4", 75, 99),
        ),
        model_import=("models.sorteio_lotomania", "SorteioLotomania"),
    ),
    "quina": CicloCoberturaSpec(
        modality_key="quina",
        nome="Quina",
        enabled=True,
        dezena_min=1,
        dezena_max=80,
        sorteadas=5,
        pick_default=5,
        pick_min=5,
        pick_max=15,
        novas_fixas=2,
        repetidas_fixas=1,
        faixas=(
            ("B", 1, 26),
            ("M", 27, 53),
            ("A", 54, 80),
        ),
        model_import=("models.sorteio_quina", "SorteioQuina"),
    ),
    "megasena": CicloCoberturaSpec(
        modality_key="megasena",
        nome="Mega-Sena",
        enabled=True,
        dezena_min=1,
        dezena_max=60,
        sorteadas=6,
        pick_default=6,
        pick_min=6,
        pick_max=20,
        novas_fixas=2,
        repetidas_fixas=1,
        faixas=(
            ("B", 1, 20),
            ("M", 21, 40),
            ("A", 41, 60),
        ),
        model_import=("models.sorteio_megasena", "SorteioMegaSena"),
    ),
    "maismilionaria": CicloCoberturaSpec(
        modality_key="maismilionaria",
        nome="+Milionária",
        enabled=True,
        dezena_min=1,
        dezena_max=50,
        sorteadas=6,
        pick_default=6,
        pick_min=6,
        pick_max=12,
        novas_fixas=2,
        repetidas_fixas=1,
        faixas=(
            ("B", 1, 16),
            ("M", 17, 33),
            ("A", 34, 50),
        ),
        model_import=("models.sorteio_maismilionaria", "SorteioMaisMilionaria"),
    ),
    "duplasena": CicloCoberturaSpec(
        modality_key="duplasena",
        nome="Dupla Sena",
        enabled=True,
        dezena_min=1,
        dezena_max=50,
        sorteadas=6,
        pick_default=6,
        pick_min=6,
        pick_max=15,
        novas_fixas=2,
        repetidas_fixas=1,
        faixas=(
            ("B", 1, 16),
            ("M", 17, 33),
            ("A", 34, 50),
        ),
        model_import=("models.sorteio_duplasena", "SorteiosDuplaSena"),
    ),
    "timemania": CicloCoberturaSpec(
        modality_key="timemania",
        nome="Timemania",
        enabled=True,
        dezena_min=1,
        dezena_max=80,
        sorteadas=10,
        pick_default=10,
        pick_min=10,
        pick_max=10,
        novas_fixas=2,
        repetidas_fixas=1,
        faixas=(
            ("B", 1, 26),
            ("M", 27, 53),
            ("A", 54, 80),
        ),
        model_import=("models.sorteio_timemania", "SorteioTimemania"),
    ),
    "supersete": CicloCoberturaSpec(
        modality_key="supersete",
        nome="Super Sete",
        enabled=False,
        dezena_min=0,
        dezena_max=9,
        sorteadas=7,
        pick_default=7,
        pick_min=7,
        pick_max=7,
        motor="colunas",
        model_import=("models.sorteio_supersete", "SorteioSuperSete"),
    ),
}


def get_ciclo_spec(modality_key: str) -> CicloCoberturaSpec:
    key = (modality_key or "").strip().lower()
    if key not in _SPECS:
        raise ValueError(f"Modalidade sem spec de ciclo: {modality_key}")
    return _SPECS[key]


def tem_ciclo_cobertura(modality_key: str) -> bool:
    try:
        spec = get_ciclo_spec(modality_key)
        return bool(spec.enabled and spec.motor == "conjunto")
    except ValueError:
        return False


def listar_specs_habilitadas() -> List[CicloCoberturaSpec]:
    return [s for s in _SPECS.values() if s.enabled and s.motor == "conjunto"]
