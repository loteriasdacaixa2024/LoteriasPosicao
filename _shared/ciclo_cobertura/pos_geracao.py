# -*- coding: utf-8 -*-
"""Pós-geração Ciclo: histórico oficial, mês da sorte, export helpers."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, FrozenSet

from .loaders import carregar_sorteios_asc
from .specs import get_ciclo_spec

MESES_ABREV = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}
MESES_NOME = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}


def mapa_combinacoes_historico(modality_key: str) -> Dict[FrozenSet[int], Dict[str, Any]]:
    """frozenset(dezenas) → {concurso, data} do sorteio oficial."""
    mapa: Dict[FrozenSet[int], Dict[str, Any]] = {}
    for s in carregar_sorteios_asc(modality_key):
        dz = s.get("dezenas") or []
        if not dz:
            continue
        key = frozenset(int(x) for x in dz)
        # mantém o concurso mais recente se houver duplicata improvável
        info = {"concurso": s["concurso"], "data": s.get("data") or ""}
        prev = mapa.get(key)
        if not prev or int(s["concurso"]) >= int(prev["concurso"]):
            mapa[key] = info
    return mapa


def anotar_historico(
    apostas: List[dict],
    modality_key: str,
    *,
    descartar: bool = False,
) -> Dict[str, Any]:
    """
    Anota cada aposta com ja_sorteada / concurso_historico.
    Se descartar=True, remove as já sorteadas do retorno.
    """
    mapa = mapa_combinacoes_historico(modality_key)
    mantidas: List[dict] = []
    ja_sorteadas: List[dict] = []
    for i, ap in enumerate(apostas or []):
        dez = [int(x) for x in (ap.get("dezenas") or [])]
        key = frozenset(dez)
        hit = mapa.get(key)
        item = dict(ap)
        if hit:
            item["ja_sorteada"] = True
            item["concurso_historico"] = hit["concurso"]
            item["data_historico"] = hit.get("data") or ""
            ja_sorteadas.append(item)
            if not descartar:
                mantidas.append(item)
        else:
            item["ja_sorteada"] = False
            item["concurso_historico"] = None
            item["data_historico"] = ""
            mantidas.append(item)

    # renumerar
    for idx, ap in enumerate(mantidas, 1):
        ap["numero"] = idx

    return {
        "apostas": mantidas,
        "ja_sorteadas_count": len(ja_sorteadas),
        "ja_sorteadas": [
            {
                "dezenas": a.get("dezenas"),
                "concurso": a.get("concurso_historico"),
                "data": a.get("data_historico"),
            }
            for a in ja_sorteadas
        ],
        "descartadas": len(ja_sorteadas) if descartar else 0,
        "total_antes": len(apostas or []),
    }


def aplicar_mes_apostas(
    apostas: List[dict],
    mes_num: Optional[int],
) -> List[dict]:
    if not mes_num or not (1 <= int(mes_num) <= 12):
        return apostas
    mn = int(mes_num)
    out = []
    for ap in apostas or []:
        item = dict(ap)
        item["mes_num"] = mn
        item["mes"] = mn
        item["mes_abrev"] = MESES_ABREV[mn]
        item["mes_nome"] = MESES_NOME[mn]
        item["extras"] = {
            "tipo": "mes",
            "num": mn,
            "label": MESES_ABREV[mn],
        }
        out.append(item)
    return out


def pos_processar_geracao(
    resultado: Dict[str, Any],
    modality_key: str,
    *,
    mes_num: Optional[int] = None,
    descartar_historico: bool = False,
) -> Dict[str, Any]:
    """Aplica histórico + mês sobre um resultado {ok, apostas, ...}."""
    if not resultado.get("ok"):
        return resultado
    out = dict(resultado)
    anot = anotar_historico(
        out.get("apostas") or [],
        modality_key,
        descartar=bool(descartar_historico),
    )
    apostas = aplicar_mes_apostas(anot["apostas"], mes_num)
    out["apostas"] = apostas
    out["geradas"] = len(apostas)
    out["historico"] = {
        "ja_sorteadas_count": anot["ja_sorteadas_count"],
        "descartadas": anot["descartadas"],
        "total_antes": anot["total_antes"],
        "itens": anot["ja_sorteadas"],
    }
    partes = []
    if out.get("aviso"):
        partes.append(str(out["aviso"]))
    if anot["ja_sorteadas_count"]:
        if descartar_historico:
            partes.append(
                f"{anot['descartadas']} aposta(s) descartada(s) por já existirem "
                "no histórico oficial."
            )
        else:
            partes.append(
                f"{anot['ja_sorteadas_count']} aposta(s) já sorteada(s) no histórico "
                "(marcadas — você pode removê-las)."
            )
    out["aviso"] = " ".join(partes) if partes else out.get("aviso")
    if mes_num and 1 <= int(mes_num) <= 12:
        out["mes_num"] = int(mes_num)
        out["mes_abrev"] = MESES_ABREV[int(mes_num)]
        out["mes_nome"] = MESES_NOME[int(mes_num)]
    return out
