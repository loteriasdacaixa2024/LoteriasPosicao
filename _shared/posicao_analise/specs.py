# -*- coding: utf-8 -*-
"""Especificações por modalidade — Análise por Posição."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class PosicaoSpec:
    key: str
    nome: str
    num_posicoes: int
    valor_min: int
    valor_max: int
    pad_width: int = 2
    pos_prefix: str = "P"
    pos_label: str = "Posição"
    distinct_across_positions: bool = True
    show_dig_soma: bool = True
    matriz_cols: int = 10
    ordered_fields: List[str] = field(default_factory=list)
    duplasena: bool = False
    extra_mes: bool = False
    extra_time: bool = False
    extra_trevo: bool = False
    export_join: str = " "
    subtitle_analise: str = ""
    subtitle_gerador: str = ""
    min_panel_width: int = 42

    def fmt(self, valor: int) -> str:
        if self.pad_width <= 1:
            return str(int(valor))
        return f"{int(valor):0{self.pad_width}d}"

    def ordered_fields_for(self, sorteio: int = 1) -> List[str]:
        if not self.duplasena:
            return list(self.ordered_fields)
        s = 1 if int(sorteio) != 2 else 2
        return [f"s{s}_d{i}" for i in range(1, self.num_posicoes + 1)]

    def to_ui(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "nome": self.nome,
            "num_posicoes": self.num_posicoes,
            "valor_min": self.valor_min,
            "valor_max": self.valor_max,
            "pad_width": self.pad_width,
            "pos_prefix": self.pos_prefix,
            "pos_label": self.pos_label,
            "distinct_across_positions": self.distinct_across_positions,
            "show_dig_soma": self.show_dig_soma,
            "matriz_cols": self.matriz_cols,
            "duplasena": self.duplasena,
            "extra_mes": self.extra_mes,
            "extra_time": self.extra_time,
            "extra_trevo": self.extra_trevo,
            "export_join": self.export_join,
            "subtitle_analise": self.subtitle_analise,
            "subtitle_gerador": self.subtitle_gerador,
            "min_panel_width": self.min_panel_width,
        }


def _spec(
    key: str,
    nome: str,
    n: int,
    vmin: int,
    vmax: int,
    fields: List[str],
    *,
    pad: int = 2,
    prefix: str = "P",
    label: str = "Posição",
    distinct: bool = True,
    dig_soma: bool = True,
    cols: int = 10,
    duplasena: bool = False,
    extra_mes: bool = False,
    extra_time: bool = False,
    extra_trevo: bool = False,
    export_join: str = " ",
    subtitle: str = "",
    min_w: int = 42,
) -> PosicaoSpec:
    sub_a = subtitle or f"{n} {label.lower()}s · ordem oficial"
    if dig_soma and pad >= 2:
        sub_a += " · dígitos e soma"
    return PosicaoSpec(
        key=key,
        nome=nome,
        num_posicoes=n,
        valor_min=vmin,
        valor_max=vmax,
        pad_width=pad,
        pos_prefix=prefix,
        pos_label=label,
        distinct_across_positions=distinct,
        show_dig_soma=dig_soma,
        matriz_cols=cols,
        ordered_fields=fields,
        duplasena=duplasena,
        extra_mes=extra_mes,
        extra_time=extra_time,
        extra_trevo=extra_trevo,
        export_join=export_join,
        subtitle_analise=sub_a,
        subtitle_gerador=sub_a,
        min_panel_width=min_w,
    )


POSICAO_SPECS: Dict[str, PosicaoSpec] = {
    "supersete": _spec(
        "supersete",
        "Super Sete",
        7,
        0,
        9,
        [f"coluna_{i}" for i in range(1, 8)],
        pad=1,
        prefix="C",
        label="Coluna",
        distinct=False,
        cols=10,
        export_join="-",
        subtitle="7 colunas · dígitos 0–9 · ordem oficial",
        min_w=36,
    ),
    "lotofacil": _spec(
        "lotofacil",
        "Lotofácil",
        15,
        1,
        25,
        [f"posicao_{i}" for i in range(1, 16)],
        cols=5,
        subtitle="15 posições · matriz 01–25 · ordem de sorteio",
        min_w=32,
    ),
    "timemania": _spec(
        "timemania",
        "Timemania",
        7,
        1,
        80,
        [f"d{i}" for i in range(1, 8)],
        extra_time=True,
        subtitle="7 dezenas sorteadas · ordem oficial + Time do Coração",
        min_w=36,
    ),
    "maismilionaria": _spec(
        "maismilionaria",
        "+Milionária",
        6,
        1,
        50,
        [f"d{i}" for i in range(1, 7)],
        extra_trevo=True,
        subtitle="6 dezenas · ordem oficial + trevos",
    ),
    "megasena": _spec(
        "megasena",
        "Mega-Sena",
        6,
        1,
        60,
        [f"d{i}" for i in range(1, 7)],
        subtitle="6 dezenas · ordem de sorteio (volante na aposta)",
    ),
    "quina": _spec(
        "quina",
        "Quina",
        5,
        1,
        80,
        [f"d{i}" for i in range(1, 6)],
        subtitle="5 dezenas · ordem de sorteio (volante na aposta)",
    ),
    "duplasena": _spec(
        "duplasena",
        "Dupla Sena",
        6,
        1,
        50,
        [f"s1_d{i}" for i in range(1, 7)],
        duplasena=True,
        subtitle="6 dezenas por sorteio · escolha 1º ou 2º sorteio",
    ),
    "lotomania": _spec(
        "lotomania",
        "Lotomania",
        20,
        0,
        99,
        [f"d{i:02d}" for i in range(1, 21)],
        subtitle="20 posições · matriz 00–99 · ordem oficial",
        min_w=28,
    ),
    "diadesorte": _spec(
        "diadesorte",
        "Dia de Sorte",
        7,
        1,
        31,
        [f"d{i}" for i in range(1, 8)],
        extra_mes=True,
        subtitle="7 dezenas · matriz 01–31 · ordem oficial · mês",
    ),
}

# Ordem de rollout solicitada pelo usuário
POSICAO_ROLLOUT_ORDER: List[str] = [
    "supersete",
    "lotofacil",
    "timemania",
    "maismilionaria",
    "megasena",
    "quina",
    "duplasena",
    "lotomania",
    "diadesorte",
]


def get_posicao_spec(modality_key: str) -> PosicaoSpec:
    if modality_key not in POSICAO_SPECS:
        raise ValueError(f"Modalidade sem análise por posição: {modality_key}")
    return POSICAO_SPECS[modality_key]


def tem_posicao_analise(modality_key: str) -> bool:
    return modality_key in POSICAO_SPECS


def posicao_nav_desc(modality_key: str) -> str:
    sp = get_posicao_spec(modality_key)
    vmin = sp.fmt(sp.valor_min)
    vmax = sp.fmt(sp.valor_max)
    if sp.key == "supersete":
        return f"Matriz {vmin}–{vmax} · ordem oficial por coluna"
    if sp.extra_mes:
        return f"Matriz {vmin}–{vmax} · ordem oficial · dígitos e soma"
    if sp.num_posicoes >= 15:
        return f"{sp.num_posicoes} posições · {vmin}–{vmax} · ordem oficial"
    return f"Matriz {vmin}–{vmax} · ordem oficial · dígitos e soma"
