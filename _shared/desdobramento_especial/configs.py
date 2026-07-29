# -*- coding: utf-8 -*-
"""Configuração por modalidade — desdobramento especial (colunas + PAR/ÍMPAR)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Set


def _garantias(jmax: int) -> Dict:
    return {
        "bronze": {
            "jogos": max(1, jmax // 4),
            "titulo": f"{max(1, jmax // 4)} Apostas",
            "desc": "Amostra inicial dos alinhamentos estruturais",
        },
        "prata": {
            "jogos": max(2, jmax // 2),
            "titulo": f"{max(2, jmax // 2)} Apostas",
            "desc": "Metade do desdobramento alinhado",
        },
        "ouro": {
            "jogos": max(3, (3 * jmax) // 4),
            "titulo": f"{max(3, (3 * jmax) // 4)} Apostas",
            "desc": "Cobertura ampla dos pares alinhados",
        },
        "diamante": {
            "jogos": jmax,
            "titulo": f"{jmax} Apostas",
            "desc": "Desdobramento integral 2 em 2 por coluna",
        },
    }


def _cols_validas(min_c: int, max_col: int, min_d: int, max_d: int, modo: str) -> Set[int]:
    out: Set[int] = set()
    for n in range(min_c, max_col + 1):
        t = n * 2 if modo == "par" else 1 + (n - 1) * 2
        if min_d <= t <= max_d:
            out.add(n)
    return out


@dataclass
class ModalidadeConfig:
    slug: str
    titulo_especial: str
    emoji: str
    max_dezena: int
    ciclo_total: int
    volante_linhas: int
    colunas_header: int
    layout: str  # final10 | bloco5
    min_colunas: int
    min_dezenas: int
    max_dezenas: int
    tabela_precos: Dict[int, float]
    garantias: Dict
    colunas_validas_par: Set[int] = field(default_factory=set)
    colunas_validas_impar: Set[int] = field(default_factory=set)
    nota_aposta: str = ""
    sorteio_bolas: int = 5

    def label_coluna(self, col: int) -> str:
        if self.layout == "bloco5":
            a = (col - 1) * 5 + 1
            b = min(col * 5, self.max_dezena)
            return f"Coluna {col} ({a:02d}–{b:02d})"
        fim = 0 if col == 10 else col
        return f"Coluna {col} (final {fim})"


def _mk(
    slug,
    titulo,
    emoji,
    max_d,
    linhas,
    ncols,
    layout,
    min_dez,
    max_dez,
    precos,
    jmax,
    min_col=3,
    nota="",
    bolas=5,
):
    cfg = ModalidadeConfig(
        slug=slug,
        titulo_especial=titulo,
        emoji=emoji,
        max_dezena=max_d,
        ciclo_total=max_d,
        volante_linhas=linhas,
        colunas_header=ncols,
        layout=layout,
        min_colunas=min_col,
        min_dezenas=min_dez,
        max_dezenas=max_dez,
        tabela_precos=precos,
        garantias=_garantias(jmax),
        nota_aposta=nota,
        sorteio_bolas=bolas,
    )
    cfg.colunas_validas_par = _cols_validas(min_col, ncols, min_dez, max_dez, "par")
    cfg.colunas_validas_impar = _cols_validas(min_col, ncols, min_dez, max_dez, "impar")
    return cfg


MODALIDADES: Dict[str, ModalidadeConfig] = {
    "quina": _mk(
        "quina",
        "Quina de São João",
        "☀️",
        80,
        8,
        10,
        "final10",
        5,
        15,
        {5: 3.0, 6: 18.0, 7: 63.0, 8: 168.0, 9: 378.0, 10: 756.0, 11: 1386.0, 12: 2376.0, 13: 3861.0, 14: 6006.0, 15: 9009.0},
        28,
        bolas=5,
    ),
    "megasena": _mk(
        "megasena",
        "Mega da Virada",
        "🎆",
        60,
        6,
        10,
        "final10",
        6,
        15,
        {6: 6.0, 7: 42.0, 8: 168.0, 9: 504.0, 10: 1260.0, 11: 2772.0, 12: 5544.0, 13: 10296.0, 14: 18018.0, 15: 30030.0},
        15,
        bolas=6,
    ),
    "duplasena": _mk(
        "duplasena",
        "Dupla de Páscoa",
        "🐣",
        50,
        5,
        10,
        "final10",
        6,
        15,
        {6: 3.0, 7: 21.0, 8: 84.0, 9: 252.0, 10: 630.0, 11: 1386.0, 12: 2772.0, 13: 5148.0, 14: 9009.0, 15: 15015.0},
        10,
        bolas=6,
    ),
    "lotofacil": _mk(
        "lotofacil",
        "Lotofácil da Independência",
        "🇧🇷",
        25,
        5,
        5,
        "bloco5",
        6,
        10,
        {6: 6.0, 7: 42.0, 8: 168.0, 9: 378.0, 10: 756.0},
        10,
        min_col=3,
        nota=(
            "Na Caixa a aposta simples usa 15–20 dezenas. "
            "Neste modo estrutural por colunas (5 blocos no volante), a montagem válida é de "
            "<strong>6 a 10 dezenas</strong> (até 5 colunas). Para 15+ dezenas use o Desdobramento Inteligente."
        ),
        bolas=15,
    ),
}


def get_config(slug: str) -> ModalidadeConfig:
    if slug not in MODALIDADES:
        raise KeyError(f"Modalidade especial não configurada: {slug}")
    return MODALIDADES[slug]
