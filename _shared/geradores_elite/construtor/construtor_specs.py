# -*- coding: utf-8 -*-
"""Especificações por modalidade — Construtor de Construções."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from geradores_elite.comportamento.specs import MESES_NOME, MESES_ABREV


def _faixas_tercos(dmin: int, dmax: int) -> Dict[str, Tuple[int, int]]:
    span = dmax - dmin + 1
    t1 = dmin + span // 3 - 1
    t2 = dmin + 2 * span // 3 - 1
    return {
        "baixas": (dmin, t1),
        "medias": (t1 + 1, t2),
        "altas": (t2 + 1, dmax),
    }


def _fmt_faixa(lo: int, hi: int, width: int = 2) -> str:
    return f"{lo:0{width}d}–{hi:0{width}d}"


@dataclass(frozen=True)
class ConstrutorSpec:
    modality_key: str
    universo: int
    dezena_min: int
    pick_min: int
    pick_max: int
    pick_default: int
    max_conjunto_base: int
    acertos_por_sorteio: int
    acertos_min_relevante: int
    acertos_max_possivel: int
    volante_cols: int = 10
    dezena_fmt_width: int = 2
    has_mes: bool = False
    has_time: bool = False
    has_trevos: bool = False
    positional: bool = False
    num_colunas: int = 7
    max_digitos_por_coluna: int = 5
    colinha_titulo: str = "Por que limitar o conjunto-base?"
    colinha_texto: str = (
        "O conjunto-base é a matéria-prima fixa. Todas as construções usam "
        "exatamente essas mesmas dezenas — só muda a forma de organizá-las. "
        "Um pool enxuto mantém o propósito do construtor: engenharia consciente, "
        "não o volante inteiro."
    )

    def faixa_limites(self) -> Dict[str, Tuple[int, int]]:
        # Dia de Sorte: linhas do volante — 01–10 / 11–20 / 21–30 / 31 isolada
        if self.modality_key == "diadesorte":
            return {
                "baixas": (1, 10),
                "medias": (11, 20),
                "altas": (21, 30),
                "isolada": (31, 31),
            }
        return _faixas_tercos(self.dezena_min, self.universo)

    def faixas_ui(self) -> Dict[str, str]:
        lim = self.faixa_limites()
        w = self.dezena_fmt_width
        out = {}
        for k, (lo, hi) in lim.items():
            if k == "isolada" and lo == hi:
                out[k] = f"{lo:0{w}d}"
            else:
                out[k] = _fmt_faixa(lo, hi, w)
        return out

    def acertos_tiers(self) -> Tuple[int, ...]:
        return tuple(range(self.acertos_min_relevante, self.acertos_max_possivel + 1))

    def colinha(self, max_pool: int | None = None) -> Dict[str, str]:
        if self.positional:
            return {
                "titulo": self.colinha_titulo,
                "texto": self.colinha_texto,
            }
        mp = max_pool or self.max_conjunto_base
        u = self.universo - self.dezena_min + 1
        return {
            "titulo": self.colinha_titulo,
            "texto": (
                f"{self.colinha_texto} "
                f"Com no máximo {mp} números de um universo de {u}, "
                "você escolhe de forma consciente."
            ),
        }


def _spec_volante(
    key: str,
    universo: int,
    pick_min: int,
    pick_max: int,
    pick_default: int,
    max_pool: int,
    sorteados: int,
    acertos_min: int,
    dmin: int = 1,
    cols: int = 10,
    fmt_w: int = 2,
    **kw,
) -> ConstrutorSpec:
    return ConstrutorSpec(
        modality_key=key,
        universo=universo,
        dezena_min=dmin,
        pick_min=pick_min,
        pick_max=pick_max,
        pick_default=pick_default,
        max_conjunto_base=max_pool,
        acertos_por_sorteio=sorteados,
        acertos_min_relevante=acertos_min,
        acertos_max_possivel=sorteados,
        volante_cols=cols,
        dezena_fmt_width=fmt_w,
        **kw,
    )


DIADESORTE_CONSTRUTOR = _spec_volante(
    "diadesorte", 31, 7, 15, 7, 16, 7, 4, has_mes=True,
    colinha_titulo="Por que só 16 dezenas?",
    colinha_texto=(
        "O conjunto-base é a sua matéria-prima fixa. Todas as construções usam "
        "exatamente essas mesmas dezenas — só muda a forma de organizá-las. "
    ),
)

MEGASENA_CONSTRUTOR = _spec_volante("megasena", 60, 6, 20, 6, 24, 6, 4, cols=10)
QUINA_CONSTRUTOR = _spec_volante("quina", 80, 5, 15, 5, 24, 5, 3, cols=10)
TIMEMANIA_CONSTRUTOR = _spec_volante(
    "timemania", 80, 10, 10, 10, 24, 10, 7, has_time=True, cols=10,
)
DUPLASENA_CONSTRUTOR = _spec_volante("duplasena", 50, 6, 15, 6, 20, 6, 4, cols=10)
MAISMILIONARIA_CONSTRUTOR = _spec_volante(
    "maismilionaria", 50, 6, 12, 6, 20, 6, 4, has_trevos=True, cols=10,
)
LOTOFACIL_CONSTRUTOR = _spec_volante("lotofacil", 25, 15, 20, 15, 20, 15, 11, cols=5)
LOTOMANIA_CONSTRUTOR = _spec_volante(
    "lotomania", 99, 50, 50, 50, 30, 20, 15, dmin=0, cols=10, fmt_w=2,
)

SUPERSETE_CONSTRUTOR = ConstrutorSpec(
    modality_key="supersete",
    universo=9,
    dezena_min=0,
    pick_min=7,
    pick_max=7,
    pick_default=7,
    max_conjunto_base=35,
    acertos_por_sorteio=7,
    acertos_min_relevante=3,
    acertos_max_possivel=7,
    volante_cols=10,
    dezena_fmt_width=1,
    positional=True,
    num_colunas=7,
    max_digitos_por_coluna=3,
    colinha_titulo="Por que limitar por coluna?",
    colinha_texto=(
        "Na Super Sete cada coluna C1–C7 é independente. No volante oficial da Caixa "
        "o máximo é 3 dígitos por coluna (apostas múltiplas). Você escolhe até 3 "
        "candidatos por coluna; as construções sorteiam um dígito de cada pool, "
        "sempre na ordem posicional — nunca reordenamos C1–C7."
    ),
)

CONSTRUTOR_SPECS: Dict[str, ConstrutorSpec] = {
    "diadesorte": DIADESORTE_CONSTRUTOR,
    "megasena": MEGASENA_CONSTRUTOR,
    "quina": QUINA_CONSTRUTOR,
    "timemania": TIMEMANIA_CONSTRUTOR,
    "duplasena": DUPLASENA_CONSTRUTOR,
    "maismilionaria": MAISMILIONARIA_CONSTRUTOR,
    "lotofacil": LOTOFACIL_CONSTRUTOR,
    "lotomania": LOTOMANIA_CONSTRUTOR,
    "supersete": SUPERSETE_CONSTRUTOR,
}


def meses_ui() -> list:
    return [
        {"num": m, "nome": MESES_NOME[m], "abrev": MESES_ABREV[m]}
        for m in range(1, 13)
    ]
