# -*- coding: utf-8 -*-
"""Pós-geração Ciclo — delega ao pipeline global dos Geradores Elite."""
from __future__ import annotations

from typing import Any, Dict, Optional

from geradores_elite.validacao.pipeline import pipeline_pos_geracao

MESES_ABREV = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}
MESES_NOME = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}


def resolver_mes_entrada(mes_raw) -> Optional[int]:
    """Aceita 1–12, atrasado/frequente/aleatorio ou nome do mês."""
    if mes_raw is None or mes_raw == "":
        return None
    try:
        from diadesorte.mes_sorte_select import resolver_mes_sorte
        return resolver_mes_sorte(mes_raw)
    except Exception:
        try:
            n = int(mes_raw)
            return n if 1 <= n <= 12 else None
        except (TypeError, ValueError):
            return None


def aplicar_mes_apostas(apostas: list, mes_num=None) -> list:
    mn = resolver_mes_entrada(mes_num)
    if not mn or not (1 <= int(mn) <= 12):
        return apostas
    mn = int(mn)
    out = []
    for ap in apostas or []:
        item = dict(ap) if isinstance(ap, dict) else {"dezenas": ap}
        item["mes_num"] = mn
        item["mes"] = mn
        item["mes_abrev"] = MESES_ABREV[mn]
        item["mes_nome"] = MESES_NOME[mn]
        item["extras"] = {"tipo": "mes", "num": mn, "label": MESES_ABREV[mn]}
        out.append(item)
    return out


def pos_processar_geracao(
    resultado: Dict[str, Any],
    modality_key: str,
    *,
    mes_num=None,
    descartar_historico: bool = False,
    executar_backtest: bool = True,
    limite_backtest: int = 30,
    origem: str = "ciclo",
) -> Dict[str, Any]:
    """Compatível com a API do Ciclo; usa o pipeline global."""
    if not resultado.get("ok") and resultado.get("sucesso") is not True:
        return resultado

    payload = dict(resultado)
    payload["sucesso"] = True

    out = pipeline_pos_geracao(
        payload,
        modality_key=modality_key,
        origem=origem,
        descartar_historico=descartar_historico,
        executar_backtest=executar_backtest,
        limite_backtest=limite_backtest,
        campo_lista="apostas",
    )

    mn = resolver_mes_entrada(mes_num)
    if mn:
        out["apostas"] = aplicar_mes_apostas(out.get("apostas") or [], mn)
        out["mes_num"] = mn
        out["mes_abrev"] = MESES_ABREV[mn]
        out["mes_nome"] = MESES_NOME[mn]

    out["ok"] = True
    return out
