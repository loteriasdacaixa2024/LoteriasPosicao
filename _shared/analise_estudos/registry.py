# -*- coding: utf-8 -*-
"""Registro de abas — plug-in para novas análises."""
from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Tuple, Type

from analise_estudos.abas.classificacao_numeros import ClassificacaoNumerosAba
from analise_estudos.abas.diferencial_cruzado import DiferencialCruzadoAba
from analise_estudos.abas.digitos_utilizados import DigitosUtilizadosAba
from analise_estudos.abas.soma_digitos import SomaDigitosAba


# Modalidades com Análises Gerais habilitadas
_MODS_ESTUDOS = frozenset({
    "diadesorte",
    "quina",
    "megasena",
    "lotofacil",
    "timemania",
    "lotomania",
    "supersete",
})


@dataclass(frozen=True)
class AbaSpec:
    id: str
    titulo: str
    descricao: str
    icone: str
    ordem: int
    service_cls: Type
    modalidades: FrozenSet[str] = _MODS_ESTUDOS


ABAS: Tuple[AbaSpec, ...] = (
    AbaSpec(
        id="classificacao-numeros",
        titulo="Classificação dos Números",
        descricao="PA · PR · GE · TR · BX/MD/AL e demais grupos",
        icone="fas fa-layer-group",
        ordem=1,
        service_cls=ClassificacaoNumerosAba,
    ),
    AbaSpec(
        id="digitos-utilizados",
        titulo="Dígitos Utilizados",
        descricao="Conjunto de dígitos 0–9 presentes em cada concurso",
        icone="fas fa-hashtag",
        ordem=2,
        service_cls=DigitosUtilizadosAba,
    ),
    AbaSpec(
        id="diferencial-cruzado",
        titulo="Diferencial Cruzado",
        descricao="Último − penúltimo · soma cruzada · números à apostar",
        icone="fas fa-exchange-alt",
        ordem=4,
        service_cls=DiferencialCruzadoAba,
    ),
    AbaSpec(
        id="soma-digitos",
        titulo="Soma dos Dígitos",
        descricao="Soma dos algarismos de cada dezena sorteada",
        icone="fas fa-plus-circle",
        ordem=5,
        service_cls=SomaDigitosAba,
    ),
)

ABAS_BY_ID = {a.id: a for a in ABAS}


def abas_para_modalidade(modality_key: str) -> Tuple[AbaSpec, ...]:
    return tuple(
        a for a in sorted(ABAS, key=lambda x: x.ordem)
        if modality_key in a.modalidades
    )


def get_aba(aba_id: str) -> AbaSpec:
    if aba_id not in ABAS_BY_ID:
        raise KeyError(f"Aba desconhecida: {aba_id}")
    return ABAS_BY_ID[aba_id]
