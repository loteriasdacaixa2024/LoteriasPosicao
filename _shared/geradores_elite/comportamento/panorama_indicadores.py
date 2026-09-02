# -*- coding: utf-8 -*-
"""Panorama comportamental — ranking histórico por indicador."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Sequence

from geradores_elite.comportamento.specs import MESES_NOME

_TOP_DESTAQUE = 3
_TOP_PANORAMA = 3
_MS_MIN = 1
_MS_MAX = 12


def _valor_exibicao(codigo: str, valor: int) -> str:
    if codigo == "MS":
        v = int(valor)
        if v < _MS_MIN or v > _MS_MAX:
            return "Sem mês"
        return MESES_NOME.get(v, str(valor))
    return str(valor)


def _mes_valido(valor: Any) -> bool:
    try:
        v = int(valor)
    except (TypeError, ValueError):
        return False
    return _MS_MIN <= v <= _MS_MAX


def _vals_indicador(cod: str, linhas: Sequence[Dict[str, Any]]) -> List[int]:
    if cod == "MS":
        return [
            int(row[cod])
            for row in linhas
            if cod in row and row[cod] is not None and _mes_valido(row[cod])
        ]
    return [
        int(row[cod])
        for row in linhas
        if cod in row and row[cod] is not None
    ]


def _concursos_sem_mes(linhas: Sequence[Dict[str, Any]]) -> int:
    return sum(
        1 for row in linhas
        if not _mes_valido(row.get("MS"))
    )


def calcular_panorama_indicadores(
    linhas: Sequence[Dict[str, Any]],
    indicadores: Sequence[str],
    indicador_labels: Dict[str, str],
) -> Dict[str, Any]:
    """
    Agrupa e classifica os valores de cada indicador em todo o histórico fornecido.
    MS: só entram meses 1–12 no ranking (0 = dado ausente no banco).
    Retorna no máximo os 3 primeiros ranks por indicador.
    """
    total = len(linhas)
    if total <= 0:
        return {
            "total_concursos": 0,
            "indicadores": [],
            "conclusoes": ["Nenhum concurso na base para panorama."],
            "concursos_sem_mes": 0,
        }

    indicadores_out: List[Dict[str, Any]] = []
    conclusoes: List[str] = []
    sem_mes = _concursos_sem_mes(linhas) if "MS" in indicadores else 0

    for cod in indicadores:
        vals = _vals_indicador(cod, linhas)
        if not vals:
            item: Dict[str, Any] = {
                "codigo": cod,
                "label": indicador_labels.get(cod, cod),
                "total_concursos": 0,
                "ranking": [],
                "predominante": None,
            }
            if cod == "MS" and sem_mes:
                item["concursos_sem_mes"] = sem_mes
            indicadores_out.append(item)
            continue

        cnt = Counter(vals)
        ranking: List[Dict[str, Any]] = []
        for pos, (valor, qtd) in enumerate(cnt.most_common(_TOP_PANORAMA), start=1):
            pct = round(qtd / total * 100, 1)
            ranking.append({
                "ranking": pos,
                "valor": int(valor),
                "valor_label": _valor_exibicao(cod, int(valor)),
                "ocorrencias": int(qtd),
                "percentual": pct,
                "destaque": pos <= _TOP_DESTAQUE,
            })

        pred = ranking[0] if ranking else None
        out_item: Dict[str, Any] = {
            "codigo": cod,
            "label": indicador_labels.get(cod, cod),
            "total_concursos": len(vals),
            "valores_distintos": len(cnt),
            "ranking": ranking,
            "predominante": pred,
        }
        if cod == "MS":
            out_item["concursos_sem_mes"] = sem_mes
            out_item["total_com_mes"] = len(vals)
        indicadores_out.append(out_item)

        if pred:
            conclusoes.append(
                f"{cod} ({indicador_labels.get(cod, cod)}): "
                f"predomina **{pred['valor_label']}** — "
                f"{pred['ocorrencias']} ocorrências ({pred['percentual']}%)."
            )

    aviso_mes: Optional[str] = None
    if sem_mes > 0:
        pct_sem = round(sem_mes / total * 100, 1)
        aviso_mes = (
            f"{sem_mes} concurso(s) ({pct_sem}%) sem mês da sorte no banco — "
            "excluídos do ranking MS. Execute backfill_meses_diadesorte.py para corrigir."
        )
        conclusoes.append(f"MS: **{sem_mes}** concursos sem mês registrado ({pct_sem}%).")

    return {
        "total_concursos": total,
        "indicadores": indicadores_out,
        "conclusoes": conclusoes,
        "concursos_sem_mes": sem_mes,
        "aviso_mes": aviso_mes,
    }
