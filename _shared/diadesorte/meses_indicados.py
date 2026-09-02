# -*- coding: utf-8 -*-
"""Mês da Sorte — pool por eliminação (últimos 10 concursos)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Type

from sqlalchemy import desc

from geradores_elite.comportamento.specs import MESES_ABREV, MESES_NOME

JANELA_MS = 10


def _mes_num_row(row: Any) -> int:
    mn = getattr(row, "mes_num", None)
    if mn is None and isinstance(row, dict):
        mn = row.get("mes_num") or row.get("mes") or row.get("MS")
    try:
        mn = int(mn or 0)
    except (TypeError, ValueError):
        return 0
    return mn if 1 <= mn <= 12 else 0


def _mes_nome_row(row: Any, mn: int) -> str:
    nome = getattr(row, "mes_nome", None) if not isinstance(row, dict) else row.get("mes_nome")
    return (nome or MESES_NOME.get(mn, "") or "").strip()


def _item_mes(mn: int) -> Dict[str, Any]:
    nome = MESES_NOME.get(mn, f"Mês {mn}")
    return {
        "mes_num": mn,
        "mes_nome": nome,
        "mes_abrev": MESES_ABREV.get(mn, str(mn)),
    }


def analisar_meses_indicados(
    sorteios_desc: Sequence[Any],
    janela: int = JANELA_MS,
) -> Dict[str, Any]:
    """sorteios_desc: concursos mais recentes primeiro."""
    if not sorteios_desc:
        return {
            "sucesso": False,
            "erro": "Nenhum sorteio no banco.",
            "janela": janela,
        }

    ultimo = int(getattr(sorteios_desc[0], "concurso", 0) or sorteios_desc[0].get("concurso", 0))
    n_disp = min(janela, len(sorteios_desc))
    janela_rows = list(sorteios_desc[:n_disp])
    janela_asc = list(reversed(janela_rows))

    meses_vistos: set[int] = set()
    linhas_janela: List[Dict[str, Any]] = []
    for row in janela_asc:
        concurso = getattr(row, "concurso", None) if not isinstance(row, dict) else row.get("concurso")
        mn = _mes_num_row(row)
        if mn:
            meses_vistos.add(mn)
        linhas_janela.append({
            "concurso": concurso,
            "mes_num": mn or None,
            "mes_nome": _mes_nome_row(row, mn) if mn else "",
            "mes_abrev": MESES_ABREV.get(mn, "") if mn else "",
        })

    eliminados = sorted(meses_vistos)
    indicados_nums = [m for m in range(1, 13) if m not in meses_vistos]
    meses_sairam = [_item_mes(m) for m in eliminados]
    meses_indicados = [_item_mes(m) for m in indicados_nums]

    return {
        "sucesso": True,
        "janela": janela,
        "janela_efetiva": n_disp,
        "janela_completa": n_disp >= janela,
        "janela_label": f"Últimos {janela}",
        "ultimo_concurso": ultimo,
        "proximo_concurso": ultimo + 1,
        "concursos_janela": [r["concurso"] for r in linhas_janela],
        "linhas_janela": linhas_janela,
        "meses_sairam": meses_sairam,
        "meses_indicados": meses_indicados,
        "meses_indicados_nums": indicados_nums,
        "qtd_sairam": len(meses_sairam),
        "qtd_indicados": len(meses_indicados),
        "sem_indicados": len(indicados_nums) == 0,
        "metodologia": (
            f"Analisados os {janela} concursos imediatamente anteriores ao próximo sorteio. "
            "Meses que já saíram nessa janela são eliminados; os que não apareceram "
            "formam o pool indicado (ordem Jan–Dez)."
        ),
    }


def carregar_meses_indicados(SorteioModel: Type[Any], janela: int = JANELA_MS) -> Dict[str, Any]:
    from models.shared import db

    rows = (
        db.session.query(SorteioModel)
        .order_by(desc(SorteioModel.concurso))
        .limit(janela)
        .all()
    )
    return analisar_meses_indicados(rows, janela=janela)


def mes_ciclo(indicados: Sequence[int], aposta_idx: int) -> Optional[int]:
    if not indicados:
        return None
    return int(indicados[aposta_idx % len(indicados)])


def extra_mes_ciclo(analise: Dict[str, Any], aposta_idx: int) -> Dict[str, Any]:
    if not analise.get("sucesso") or analise.get("sem_indicados"):
        return {}
    nums = analise.get("meses_indicados_nums") or [
        int(m["mes_num"]) for m in (analise.get("meses_indicados") or [])
    ]
    mn = mes_ciclo(nums, aposta_idx)
    if not mn:
        return {}
    item = _item_mes(mn)
    return {
        "mes": mn,
        "mes_num": mn,
        "mes_nome": item["mes_nome"],
        "mes_abrev": item["mes_abrev"],
    }


def anexar_mes_abrev_texto(texto: str, mes_abrev: str) -> str:
    base = (texto or "").strip()
    ab = (mes_abrev or "").strip()
    if not ab:
        return base
    if base.endswith(ab):
        return base
    return f"{base} {ab}".strip()
