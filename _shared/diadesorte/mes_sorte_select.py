# -*- coding: utf-8 -*-
"""Select padronizado — Mês da Sorte (+ Atrasado / + Frequente / meses / + Aleatório)."""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Sequence, Union

from geradores_elite.comportamento.specs import MESES_ABREV, MESES_NOME

CRITERIOS_ESPECIAIS = ("atrasado", "frequente", "aleatorio")


def _item(mn: int, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    out = {
        "mes_num": int(mn),
        "mes_nome": MESES_NOME.get(int(mn), f"Mês {mn}"),
        "mes_abrev": MESES_ABREV.get(int(mn), str(mn)),
    }
    if extra:
        out.update(extra)
    return out


def estatisticas_meses_from_rows(sorteios_desc: Sequence[Any]) -> List[Dict[str, Any]]:
    """sorteios_desc: mais recente primeiro. Retorna 12 meses com freq/atraso."""
    if not sorteios_desc:
        return [_item(m, {"freq": 0, "atraso": 0, "pct": 0.0}) for m in range(1, 13)]

    total = len(sorteios_desc)
    ultimo = int(getattr(sorteios_desc[0], "concurso", 0) or 0)
    freq = {m: 0 for m in range(1, 13)}
    visto = {m: 0 for m in range(1, 13)}

    for s in sorteios_desc:
        mn = getattr(s, "mes_num", None)
        try:
            mn = int(mn or 0)
        except (TypeError, ValueError):
            continue
        if not (1 <= mn <= 12):
            continue
        freq[mn] += 1
        if visto[mn] == 0:
            visto[mn] = int(getattr(s, "concurso", 0) or 0)

    out: List[Dict[str, Any]] = []
    for m in range(1, 13):
        atraso = (ultimo - visto[m]) if visto[m] > 0 else total
        pct = round(freq[m] / total * 100, 1) if total else 0.0
        out.append(_item(m, {"freq": freq[m], "atraso": atraso, "pct": pct}))
    return out


def carregar_estatisticas_meses(SorteioModel: Any) -> List[Dict[str, Any]]:
    from models.shared import db
    from sqlalchemy import desc

    rows = db.session.query(SorteioModel).order_by(desc(SorteioModel.concurso)).all()
    return estatisticas_meses_from_rows(rows)


def _pick_max(meses: Sequence[Dict[str, Any]], key: str) -> Dict[str, Any]:
    if not meses:
        return _item(1, {"freq": 0, "atraso": 0, "pct": 0.0})
    return max(meses, key=lambda m: (int(m.get(key, 0) or 0), -int(m.get("mes_num", 0) or 0)))


def montar_opcoes_mes_sorte(meses_stats: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Ordem do select (modelo de referência):
      1) + Atrasado (Nome)
      2) + Frequente (Nome)
      3) meses restantes (1–12, excluindo os dois acima)
      4) + Aleatório
    """
    stats = list(meses_stats) if meses_stats else [_item(m) for m in range(1, 13)]
    atrasado = _pick_max(stats, "atraso")
    frequente = _pick_max(stats, "freq")
    excluir = {int(atrasado["mes_num"]), int(frequente["mes_num"])}

    opcoes: List[Dict[str, Any]] = [
        {
            "value": "atrasado",
            "label": f"+ Atrasado ({atrasado['mes_nome']})",
            "mes_num": int(atrasado["mes_num"]),
            "criterio": "atrasado",
        },
        {
            "value": "frequente",
            "label": f"+ Frequente ({frequente['mes_nome']})",
            "mes_num": int(frequente["mes_num"]),
            "criterio": "frequente",
        },
    ]
    for m in stats:
        mn = int(m["mes_num"])
        if mn in excluir:
            continue
        opcoes.append({
            "value": str(mn),
            "label": m.get("mes_nome") or MESES_NOME.get(mn, str(mn)),
            "mes_num": mn,
            "criterio": "fixo",
        })
    opcoes.append({
        "value": "aleatorio",
        "label": "+ Aleatório",
        "mes_num": None,
        "criterio": "aleatorio",
    })

    return {
        "sucesso": True,
        "atrasado": atrasado,
        "frequente": frequente,
        "meses": stats,
        "opcoes": opcoes,
        "default": "atrasado",
    }


def opcoes_mes_sorte_diadesorte() -> Dict[str, Any]:
    from models.sorteio_diadesorte import SorteioDiaDeSorte

    return montar_opcoes_mes_sorte(carregar_estatisticas_meses(SorteioDiaDeSorte))


def resolver_mes_sorte(
    valor: Union[str, int, None],
    *,
    opcoes_payload: Optional[Dict[str, Any]] = None,
    SorteioModel: Any = None,
) -> Optional[int]:
    """
    Converte valor do select em mes_num (1–12).
    Aceita: atrasado | frequente | aleatorio | 1..12 | nome do mês.
    """
    if valor is None or valor == "":
        return None

    raw = str(valor).strip()
    low = raw.lower()

    if low.isdigit():
        n = int(low)
        return n if 1 <= n <= 12 else None

    payload = opcoes_payload
    if payload is None and SorteioModel is not None:
        payload = montar_opcoes_mes_sorte(carregar_estatisticas_meses(SorteioModel))
    if payload is None:
        try:
            payload = opcoes_mes_sorte_diadesorte()
        except Exception:
            payload = montar_opcoes_mes_sorte([])

    if low == "atrasado":
        return int((payload.get("atrasado") or {}).get("mes_num") or 1)
    if low == "frequente":
        return int((payload.get("frequente") or {}).get("mes_num") or 1)
    if low == "aleatorio":
        return random.randint(1, 12)

    # Nome completo (Janeiro, Março, …)
    for m in range(1, 13):
        if MESES_NOME.get(m, "").lower() == low:
            return m
        if MESES_ABREV.get(m, "").lower() == low:
            return m

    return None
