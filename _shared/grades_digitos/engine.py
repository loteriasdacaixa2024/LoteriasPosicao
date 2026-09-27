# -*- coding: utf-8 -*-
"""Monta a grade 4×11 e lê dezenas formadas por dois dígitos adjacentes."""
from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Set, Tuple

LINHAS = 11
COLUNAS = 4
IMPARES = (1, 3, 5, 7, 9)
PARES = (0, 2, 4, 6, 8)
_VIZINHOS = ((0, 1), (1, 0), (1, 1), (1, -1))
Celula = Tuple[int, int]


def validar_inicios(inicios: Sequence[int]) -> List[int]:
    if not isinstance(inicios, (list, tuple)) or len(inicios) != 4:
        raise ValueError("Informe o início das 4 colunas.")
    saida: List[int] = []
    for i, bruto in enumerate(inicios):
        try:
            n = int(bruto)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Coluna {i + 1}: início inválido.") from exc
        permitidos = IMPARES if i in (0, 2) else PARES
        if n not in permitidos:
            tipo = "ímpar (1, 3, 5, 7 ou 9)" if i in (0, 2) else "par (0, 2, 4, 6 ou 8)"
            raise ValueError(f"Coluna {i + 1} só aceita número {tipo}.")
        saida.append(n)
    return saida


def montar_coluna(inicio: int, linhas: int = LINHAS) -> List[int]:
    return [(inicio + 2 * i) % 10 for i in range(linhas)]


def montar_grade(inicios: Sequence[int]) -> List[List[int]]:
    nums = validar_inicios(inicios)
    colunas = [montar_coluna(n) for n in nums]
    return [[colunas[c][r] for c in range(COLUNAS)] for r in range(LINHAS)]


def dezenas_da_grade(
    grade: Sequence[Sequence[int]],
    dezena_min: int,
    dezena_max: int,
) -> Dict[int, Set[Celula]]:
    """Dezena = dois dígitos vizinhos, lidos nos dois sentidos.

    Vizinhos: horizontal, vertical e as duas diagonais.
    """
    linhas = len(grade)
    colunas = len(grade[0]) if linhas else 0
    por_dezena: Dict[int, Set[Celula]] = {}
    for r in range(linhas):
        for c in range(colunas):
            for dr, dc in _VIZINHOS:
                rr, cc = r + dr, c + dc
                if not (0 <= rr < linhas and 0 <= cc < colunas):
                    continue
                a = int(grade[r][c])
                b = int(grade[rr][cc])
                for dez in (a * 10 + b, b * 10 + a):
                    if dezena_min <= dez <= dezena_max:
                        celulas = por_dezena.setdefault(dez, set())
                        celulas.add((r, c))
                        celulas.add((rr, cc))
    return por_dezena


def conferir_grade(
    grade: Sequence[Sequence[int]],
    sorteios: Iterable[Tuple[int, Set[int]]],
    dezena_min: int,
    dezena_max: int,
) -> dict:
    por_dezena = dezenas_da_grade(grade, dezena_min, dezena_max)
    universo = set(por_dezena)
    pontos = 0
    primeiro = None
    ultimo = None
    por_concurso = []
    for concurso, dezenas in sorteios:
        if primeiro is None:
            primeiro = concurso
        ultimo = concurso
        acertos = sorted(dezenas & universo)
        pontos_concurso = len(acertos)
        pontos += pontos_concurso
        por_concurso.append({
            "concurso": concurso,
            "pontos": pontos_concurso,
            "dezenas": acertos,
        })

    return {
        "pontos": pontos,
        "concursos": len(por_concurso),
        "primeiro": primeiro,
        "ultimo": ultimo,
        "dezenas_formadas": len(universo),
        "por_concurso": por_concurso,
        "mapa_celulas": {
            str(dez): sorted(list(par) for par in celulas)
            for dez, celulas in por_dezena.items()
        },
    }
