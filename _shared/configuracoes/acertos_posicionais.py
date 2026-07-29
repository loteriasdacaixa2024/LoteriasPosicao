# -*- coding: utf-8 -*-
"""Acertos posicionais — Super Sete (7 colunas independentes)."""
from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

NUM_COLUNAS_SS = 7


def is_supersete(modality_key: str) -> bool:
    return (modality_key or "").strip().lower() == "supersete"


def contar_acertos_posicional(
    aposta: Sequence[int],
    sorteadas: Sequence[int],
    *,
    colunas: int = NUM_COLUNAS_SS,
) -> int:
    """Compara coluna a coluna (ordem importa; repetições permitidas)."""
    n = min(len(aposta), len(sorteadas), colunas)
    if n <= 0:
        return 0
    return sum(1 for i in range(n) if int(aposta[i]) == int(sorteadas[i]))


def colunas_acertadas(
    aposta: Sequence[int],
    sorteadas: Sequence[int],
    *,
    colunas: int = NUM_COLUNAS_SS,
) -> List[Dict[str, int]]:
    n = min(len(aposta), len(sorteadas), colunas)
    return [
        {"coluna": i + 1, "digito": int(aposta[i])}
        for i in range(n)
        if int(aposta[i]) == int(sorteadas[i])
    ]


def digitos_acertados(
    aposta: Sequence[int],
    sorteadas: Sequence[int],
    *,
    colunas: int = NUM_COLUNAS_SS,
) -> List[int]:
    """Dígitos nas colunas acertadas (com multiplicidade posicional)."""
    return [c["digito"] for c in colunas_acertadas(aposta, sorteadas, colunas=colunas)]


def normalizar_aposta_ss(numeros: Sequence[Any], colunas: int = NUM_COLUNAS_SS) -> List[int]:
    """Extrai até `colunas` dígitos 0–9 preservando ordem (repetições ok)."""
    out: List[int] = []
    for n in numeros:
        try:
            v = int(n)
        except (TypeError, ValueError):
            continue
        if 0 <= v <= 9:
            out.append(v)
        if len(out) >= colunas:
            break
    return out


def validar_aposta_ss(numeros: Sequence[Any], colunas: int = NUM_COLUNAS_SS) -> Tuple[bool, str, List[int]]:
    seq = normalizar_aposta_ss(numeros, colunas=colunas)
    if len(seq) != colunas:
        return False, f"Informe exatamente {colunas} dígitos (0–9), um por coluna.", seq
    return True, "", seq
