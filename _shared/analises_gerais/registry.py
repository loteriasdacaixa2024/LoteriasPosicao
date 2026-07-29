# -*- coding: utf-8 -*-
"""Registro das 9 modalidades — banco SQLite e geometria do volante."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from configuracoes.config import MODALITIES


@dataclass
class ModalitySpec:
    key: str
    nome: str
    porta: int
    app_dir: str
    db_filename: str
    table: str
    total_dezenas: int
    sorteadas: int
    layout: str  # final10 | bloco5 | posicional
    grupo: str = "volante"  # volante | supersete
    linhas: int = 0
    colunas: int = 0
    col_prefixes: List[str] = field(default_factory=list)
    skip_columns: List[str] = field(default_factory=lambda: ["concurso", "data", "mes_num", "id"])


def _spec(
    key,
    app_suffix,
    db,
    table,
    total,
    sort,
    layout,
    linhas=0,
    colunas=0,
    prefixes=None,
    skip_extra=None,
    app_dir: Optional[str] = None,
):
    m = MODALITIES[key]
    skip = ["concurso", "data", "mes_num", "id", "time_id", "time_nome"]
    if skip_extra:
        skip.extend(skip_extra)
    if app_dir is None:
        suf = app_suffix if app_suffix.startswith("-") else f"-{app_suffix}"
        app_dir = f"AnalisePorPosicao{suf}"
    return ModalitySpec(
        key=key,
        nome=m["nome"],
        porta=m["porta"],
        app_dir=app_dir,
        db_filename=db,
        table=table,
        total_dezenas=total,
        sorteadas=sort,
        layout=layout,
        linhas=linhas,
        colunas=colunas,
        col_prefixes=prefixes or [],
        skip_columns=skip,
        grupo="volante",
    )


SPECS: List[ModalitySpec] = [
    _spec("lotofacil", "Lotofacil-Only", "lotofacil.db", "sorteio_lotofacil", 25, 15, "bloco5", 5, 5),
    _spec(
        "diadesorte",
        "DiaDeSorte-Only",
        "diadesorte.db",
        "sorteio_diadesorte",
        31,
        7,
        "final10",
        4,
        10,
        app_dir="AnalisePorPosicao--DiaDeSorte-Only",
    ),
    _spec("lotomania", "Lotomania-Only", "lotomania.db", "sorteio_lotomania", 100, 20, "final10", 10, 10),
    _spec("quina", "Quina-Only", "quina.db", "sorteio_quina", 80, 5, "final10", 8, 10),
    _spec("megasena", "MegaSena-Only", "megasena.db", "sorteio_megasena", 60, 6, "final10", 6, 10),
    _spec(
        "maismilionaria",
        "MaisMilionaria-Only",
        "maismilionaria.db",
        "sorteio_maismilionaria",
        50,
        6,
        "final10",
        5,
        10,
        skip_extra=["trevo1", "trevo2"],
    ),
    _spec(
        "duplasena",
        "DuplaSena-Only",
        "duplasena.db",
        "sorteio_duplasena",
        50,
        6,
        "final10",
        5,
        10,
        skip_extra=[f"s2_d{i}" for i in range(1, 7)],
    ),
    _spec(
        "timemania",
        "Timemania-Only",
        "timemania.db",
        "sorteio_timemania",
        80,
        7,
        "final10",
        8,
        10,
        skip_extra=["time_num", "time_nome"],
    ),
    ModalitySpec(
        key="supersete",
        nome=MODALITIES["supersete"]["nome"],
        porta=MODALITIES["supersete"]["porta"],
        app_dir="AnalisePorPosicao-SuperSete-Only",
        db_filename="supersete.db",
        table="sorteio_supersete",
        total_dezenas=10,
        sorteadas=7,
        layout="posicional",
        linhas=7,
        colunas=7,
        grupo="supersete",
    ),
]

VOLANTE_KEYS = [s.key for s in SPECS if s.grupo == "volante"]
SUPERSETE_KEY = "supersete"

SPECS_BY_KEY = {s.key: s for s in SPECS}
