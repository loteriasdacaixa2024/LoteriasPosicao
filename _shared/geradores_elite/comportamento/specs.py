# -*- coding: utf-8 -*-
"""Especificações por modalidade — Comportamento → Apostas."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Tuple

EXTRA_INDS = frozenset({"MS", "TM", "T1", "T2"})

MESES_NOME = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}

MESES_ABREV = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}

IND_PADRAO = ("PA", "IM", "PR", "RT", "MO", "SQ", "M3", "FB")
LBL_PADRAO = {
    "PA": "Pares",
    "IM": "Ímpares",
    "PR": "Primos",
    "RT": "Repetidas",
    "MO": "Moldura",
    "SQ": "Sequências",
    "M3": "Múltiplos de 3",
    "FB": "Fibonacci",
}


def _primos_ate(n: int, dmin: int = 1) -> FrozenSet[int]:
    ps = []
    for x in range(max(2, dmin), n + 1):
        if all(x % d for d in range(2, int(x ** 0.5) + 1)):
            ps.append(x)
    return frozenset(ps)


def _fib_ate(n: int, dmin: int = 1) -> FrozenSet[int]:
    fib = set()
    if dmin <= 0:
        fib.add(0)
    if dmin <= 1:
        fib.add(1)
    a, b = 1, 2
    while b <= n:
        fib.add(b)
        a, b = b, a + b
    return frozenset(fib)


def _m3_ate(n: int, dmin: int = 1) -> FrozenSet[int]:
    start = 3 if dmin <= 3 else ((dmin + 2) // 3) * 3
    return frozenset(d for d in range(start, n + 1, 3))


def _moldura_grid(linhas: int, colunas: int, dmin: int = 1) -> FrozenSet[int]:
    total = linhas * colunas
    moldura = set()
    for n in range(dmin, dmin + total):
        idx = n - dmin
        row, col = idx // colunas, idx % colunas
        if row == 0 or row == linhas - 1 or col == 0 or col == colunas - 1:
            moldura.add(n)
    return frozenset(moldura)


@dataclass(frozen=True)
class ComportamentoSpec:
    modality_key: str
    motor: str
    page_subtitle: str
    universo: int
    dezenas_min: int
    dezenas_max: int
    dezenas_default: int
    janelas_validas: FrozenSet[int]
    janelas_ui: Tuple[int, ...]
    janela_default: int
    indicadores: Tuple[str, ...]
    indicador_labels: Dict[str, str]
    primos: FrozenSet[int]
    fibonacci: FrozenSet[int]
    multiplos_3: FrozenSet[int]
    moldura: FrozenSet[int]
    regras_fallback: Tuple[str, ...]
    dezena_min: int = 1
    indicadores_dezena: Tuple[str, ...] = field(default_factory=tuple)
    has_mes: bool = False
    has_time: bool = False
    has_trevos: bool = False
    sorteadas: int = 0
    pool_panorama: int = 16
    acertos_min_conferencia: int = 4
    volante_cols: int = 10

    def sorteadas_efetivas(self) -> int:
        return self.sorteadas or self.dezenas_min

    def acertos_tiers(self) -> Tuple[int, ...]:
        s = self.sorteadas_efetivas()
        lo = min(self.acertos_min_conferencia, s)
        return tuple(range(lo, s + 1))

    def __post_init__(self) -> None:
        if not self.indicadores_dezena:
            object.__setattr__(
                self,
                "indicadores_dezena",
                tuple(c for c in self.indicadores if c not in EXTRA_INDS),
            )


def _spec_volante(
    key: str,
    motor: str,
    subtitle: str,
    universo: int,
    dmin_pick: int,
    dmax_pick: int,
    ddefault: int,
    janelas: Tuple[int, ...],
    grid: Tuple[int, int],
    janela_default: int | None = None,
    dmin_val: int = 1,
    extras: Tuple[str, ...] = (),
    extra_lbl: Dict[str, str] | None = None,
    fallback: Tuple[str, ...] | None = None,
    has_mes: bool = False,
    has_time: bool = False,
    has_trevos: bool = False,
    sorteadas: int | None = None,
    pool_panorama: int | None = None,
    acertos_min_conferencia: int | None = None,
    volante_cols: int = 10,
) -> ComportamentoSpec:
    inds = IND_PADRAO + extras
    lbl = dict(LBL_PADRAO)
    if extra_lbl:
        lbl.update(extra_lbl)
    fb = fallback or ("PA", "PR", "RT", "MO", "SQ", "FB")
    return ComportamentoSpec(
        modality_key=key,
        motor=motor,
        page_subtitle=subtitle,
        universo=universo,
        dezenas_min=dmin_pick,
        dezenas_max=dmax_pick,
        dezenas_default=ddefault,
        dezena_min=dmin_val,
        janelas_validas=frozenset(janelas),
        janelas_ui=janelas,
        janela_default=janela_default if janela_default is not None else janelas[0],
        indicadores=inds,
        indicador_labels=lbl,
        primos=_primos_ate(universo, dmin_val),
        fibonacci=_fib_ate(universo, dmin_val),
        multiplos_3=_m3_ate(universo, dmin_val),
        moldura=_moldura_grid(grid[0], grid[1], dmin_val),
        regras_fallback=fb,
        has_mes=has_mes,
        has_time=has_time,
        has_trevos=has_trevos,
        sorteadas=sorteadas or ddefault,
        pool_panorama=pool_panorama or 16,
        acertos_min_conferencia=acertos_min_conferencia or 4,
        volante_cols=volante_cols,
    )


LOTOFACIL_SPEC = ComportamentoSpec(
    modality_key="lotofacil",
    motor="comportamento_lf",
    page_subtitle="PA · IM · PR · RT · MO · SQ · M3 · FB — evidências e geração inteligente",
    universo=25,
    dezenas_min=15,
    dezenas_max=20,
    dezenas_default=15,
    janelas_validas=frozenset({10, 20, 25, 0}),
    janelas_ui=(10, 20, 25, 0),
    janela_default=10,
    indicadores=IND_PADRAO,
    indicador_labels=dict(LBL_PADRAO),
    primos=frozenset({2, 3, 5, 7, 11, 13, 17, 19, 23}),
    fibonacci=frozenset({1, 2, 3, 5, 8, 13, 21}),
    multiplos_3=frozenset({3, 6, 9, 12, 15, 18, 21, 24}),
    moldura=frozenset({1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25}),
    regras_fallback=("PA", "PR", "RT", "MO", "M3", "FB"),
    sorteadas=15,
    pool_panorama=20,
    acertos_min_conferencia=11,
    volante_cols=5,
)

MEGASENA_SPEC = _spec_volante(
    "megasena", "comportamento_ms",
    "PA · IM · PR · RT · MO · SQ · M3 · FB — evidências e geração inteligente",
    60, 6, 20, 6, (10, 20, 60, 0), (6, 10),
    sorteadas=6, pool_panorama=24, acertos_min_conferencia=4,
)

DIADESORTE_SPEC = _spec_volante(
    "diadesorte", "comportamento_ds",
    "PA · IM · PR · RT · MO · SQ · M3 · FB · MS — evidências e geração inteligente",
    31, 7, 15, 7, (10, 20, 31, 0), (4, 10), janela_default=10,
    extras=("MS",), extra_lbl={"MS": "Mês da Sorte"},
    fallback=("PA", "PR", "RT", "MO", "M3", "FB", "MS"),
    has_mes=True,
    sorteadas=7,
    pool_panorama=16,
    acertos_min_conferencia=4,
)

QUINA_SPEC = _spec_volante(
    "quina", "comportamento_qn",
    "PA · IM · PR · RT · MO · SQ · M3 · FB — evidências e geração inteligente",
    80, 5, 15, 5, (10, 20, 50, 80, 0), (8, 10),
    sorteadas=5, pool_panorama=24, acertos_min_conferencia=3,
)

TIMEMANIA_SPEC = _spec_volante(
    "timemania", "comportamento_tm",
    "PA · IM · PR · RT · MO · SQ · M3 · FB · TM — evidências e geração inteligente",
    80, 10, 10, 10, (10, 20, 50, 80, 0), (8, 10), janela_default=50,
    extras=("TM",), extra_lbl={"TM": "Time do Coração"},
    fallback=("PA", "PR", "RT", "MO", "M3", "FB", "TM"),
    has_time=True,
    sorteadas=7, pool_panorama=24, acertos_min_conferencia=7,
)

DUPLASENA_SPEC = _spec_volante(
    "duplasena", "comportamento_ds2",
    "1º sorteio · PA · IM · PR · RT · MO · SQ · M3 · FB — evidências e geração",
    50, 6, 15, 6, (10, 20, 50, 0), (5, 10),
    sorteadas=6, pool_panorama=20, acertos_min_conferencia=4,
)

MAISMILIONARIA_SPEC = _spec_volante(
    "maismilionaria", "comportamento_mm",
    "PA · IM · PR · RT · MO · SQ · M3 · FB · T1 · T2 — evidências e geração",
    50, 6, 12, 6, (10, 20, 50, 0), (5, 10),
    extras=("T1", "T2"), extra_lbl={"T1": "Trevo 1", "T2": "Trevo 2"},
    fallback=("PA", "PR", "RT", "MO", "FB", "T1", "T2"),
    has_trevos=True,
    sorteadas=6, pool_panorama=20, acertos_min_conferencia=4,
)

LOTOMANIA_SPEC = _spec_volante(
    "lotomania", "comportamento_lm",
    "Comportamento das 20 sorteadas → apostas de 50 dezenas (00–99)",
    99, 50, 50, 50, (10, 20, 50, 100, 0), (10, 10),
    dmin_val=0,
    fallback=("PA", "PR", "RT", "MO", "M3", "FB"),
    sorteadas=20,
    pool_panorama=30,
    acertos_min_conferencia=15,
    volante_cols=10,
)

SUPERSETE_SPEC = ComportamentoSpec(
    modality_key="supersete",
    motor="comportamento_ss",
    page_subtitle="PA · IM · PR · RP · EX · SQ — por coluna C1–C7 (dígitos 0–9)",
    universo=9,
    dezenas_min=7,
    dezenas_max=7,
    dezenas_default=7,
    dezena_min=0,
    janelas_validas=frozenset({10, 20, 30, 0}),
    janelas_ui=(10, 20, 30, 0),
    janela_default=10,
    indicadores=("PA", "IM", "PR", "RP", "EX", "SQ"),
    indicador_labels={
        "PA": "Pares",
        "IM": "Ímpares",
        "PR": "Primos",
        "RP": "Repetição posicional",
        "EX": "Extremos (0/9)",
        "SQ": "Seq. adjacentes",
    },
    primos=frozenset({2, 3, 5, 7}),
    fibonacci=frozenset({0, 1, 2, 3, 5, 8}),
    multiplos_3=frozenset({0, 3, 6, 9}),
    moldura=frozenset({0, 9}),
    regras_fallback=("PA", "PR", "RP", "EX", "SQ"),
    indicadores_dezena=("PA", "IM", "PR", "RP", "EX", "SQ"),
    sorteadas=7,
    pool_panorama=10,
    acertos_min_conferencia=3,
    volante_cols=10,
)

SPECS = {
    "lotofacil": LOTOFACIL_SPEC,
    "megasena": MEGASENA_SPEC,
    "diadesorte": DIADESORTE_SPEC,
    "quina": QUINA_SPEC,
    "timemania": TIMEMANIA_SPEC,
    "duplasena": DUPLASENA_SPEC,
    "maismilionaria": MAISMILIONARIA_SPEC,
    "lotomania": LOTOMANIA_SPEC,
    "supersete": SUPERSETE_SPEC,
}

MOTOR_LABELS = {
    "perfil_sorteio": "Perfil real da tabela",
    "hibrido": "Híbrido (perfil + moda)",
    "moda": "Resumo (moda da janela)",
}
MOTORES_GERACAO = frozenset({"perfil_sorteio", "hibrido", "moda"})

BASES_ESTATISTICA = frozenset({"geral", "vencedores", "acumulados"})
BASES_ESTATISTICA_LABEL = {
    "geral": "Geral",
    "vencedores": "Concursos com Vencedores",
    "acumulados": "Concursos Acumulados",
}

COMPORTAMENTO_TITLES = {
    "lotofacil": "Comportamento LF",
    "megasena": "Comportamento MS",
    "diadesorte": "Comportamento DS",
    "quina": "Comportamento QN",
    "timemania": "Comportamento TM",
    "duplasena": "Comportamento DS2",
    "maismilionaria": "Comportamento +M",
    "lotomania": "Comportamento LM",
    "supersete": "Comportamento SS",
}
