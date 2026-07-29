# -*- coding: utf-8 -*-
"""Varredura de concursos gravados vs. faixa 1..último oficial."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def auditar_concursos(
    sorteios: List[Tuple[int, str, List[int]]],
    ultimo_oficial: Optional[int] = None,
    status_caixa: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    st = status_caixa or {}
    proximo_regular = int(st.get("proximo_regular") or 0)
    especiais = list(st.get("especiais") or [])

    if not sorteios:
        return {
            "total_gravados": 0,
            "concurso_min": 0,
            "concurso_max_local": 0,
            "ultimo_oficial_api": ultimo_oficial or 0,
            "proximo_regular": proximo_regular,
            "concursos_especiais": especiais,
            "alvo_sincronizacao": ultimo_oficial or 0,
            "faltantes_qtd": 0,
            "faltantes_amostra": [],
            "desatualizado": False,
            "tem_lacunas": False,
            "sincronizado": False,
        }

    numeros = sorted({s[0] for s in sorteios})
    total = len(numeros)
    min_c = numeros[0]
    max_c = numeros[-1]
    presentes = set(numeros)

    alvo = ultimo_oficial if ultimo_oficial and ultimo_oficial > 0 else max_c
    faltantes = [i for i in range(1, alvo + 1) if i not in presentes]

    desatualizado = bool(ultimo_oficial and ultimo_oficial > 0 and max_c < ultimo_oficial)
    tem_lacunas = len(faltantes) > 0
    sincronizado = (
        not desatualizado
        and not tem_lacunas
        and min_c == 1
        and bool(ultimo_oficial)
        and max_c >= ultimo_oficial
    )

    especiais_faltando = []
    for esp in especiais:
        n = int(esp.get("concurso") or 0)
        if n and n not in presentes:
            especiais_faltando.append(esp)

    return {
        "total_gravados": total,
        "concurso_min": min_c,
        "concurso_max_local": max_c,
        "ultimo_oficial_api": ultimo_oficial or 0,
        "proximo_regular": proximo_regular,
        "concursos_especiais": especiais,
        "especiais_faltando": especiais_faltando,
        "alvo_sincronizacao": alvo,
        "faltantes_qtd": len(faltantes),
        "faltantes_amostra": faltantes[:20],
        "desatualizado": desatualizado,
        "tem_lacunas": tem_lacunas,
        "sincronizado": sincronizado,
    }
