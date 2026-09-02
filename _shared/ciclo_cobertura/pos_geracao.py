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


def _aplicar_um_mes(item: dict, mn: int) -> dict:
    mn = int(mn)
    item["mes_num"] = mn
    item["mes"] = mn
    item["mes_abrev"] = MESES_ABREV[mn]
    item["mes_nome"] = MESES_NOME[mn]
    item["extras"] = {"tipo": "mes", "num": mn, "label": MESES_ABREV[mn]}
    return item


def aplicar_mes_apostas(apostas: list, mes_num=None) -> list:
    """
    Aplica Mês da Sorte às apostas.
    Em + Aleatório, distribui meses de forma equilibrada (1 por aposta).
    Demais critérios: mesmo mês em todas.
    """
    if mes_num is None or mes_num == "":
        return apostas
    raw = list(apostas or [])
    if not raw:
        return apostas

    try:
        from diadesorte.mes_sorte_select import eh_criterio_aleatorio, resolver_meses_para_lote
        meses = resolver_meses_para_lote(mes_num, len(raw))
    except Exception:
        meses = []
        mn = resolver_mes_entrada(mes_num)
        if mn:
            meses = [mn] * len(raw)

    if not meses or len(meses) != len(raw):
        return apostas

    out = []
    for ap, mn in zip(raw, meses):
        item = dict(ap) if isinstance(ap, dict) else {"dezenas": ap}
        out.append(_aplicar_um_mes(item, mn))
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

    if mes_num is not None and mes_num != "":
        out["apostas"] = aplicar_mes_apostas(out.get("apostas") or [], mes_num)
        apostas_out = out.get("apostas") or []
        if apostas_out:
            # Representativo: 1º mês do lote (em aleatório cada linha pode diferir).
            mn0 = int(apostas_out[0].get("mes_num") or 0)
            if 1 <= mn0 <= 12:
                out["mes_num"] = mn0
                out["mes_abrev"] = MESES_ABREV[mn0]
                out["mes_nome"] = MESES_NOME[mn0]
                try:
                    from diadesorte.mes_sorte_select import eh_criterio_aleatorio
                    if eh_criterio_aleatorio(mes_num):
                        out["mes_criterio"] = "aleatorio"
                        out["meses_distribuidos"] = [
                            int(a.get("mes_num")) for a in apostas_out if a.get("mes_num")
                        ]
                except Exception:
                    pass

    out["ok"] = True
    return out
