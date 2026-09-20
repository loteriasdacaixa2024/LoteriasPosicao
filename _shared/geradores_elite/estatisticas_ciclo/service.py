# -*- coding: utf-8 -*-
"""Consome as análises existentes — não recria Estatísticas Básicas nem o ciclo."""
from __future__ import annotations

from typing import Any, Dict, Optional

from diadesorte.mes_sorte_select import MESES_ABREV, MESES_NOME, resolver_meses_para_lote

from .gerador import _eh_faltante, _resumo_diagonais_janela, gerar_apostas_de_contexto


def _resumo_diagonais_ctx(linhas, dmin, dmax):
    return _resumo_diagonais_janela(linhas or [], dmin, dmax)


def tem_gerador_estatisticas_ciclo(modality_key: str) -> bool:
    return (modality_key or "").strip().lower() == "diadesorte"


def _carregar_padroes(modality_key: str) -> Dict[str, Any]:
    """Catálogo das abas 4 (Padrões II) e 7 (Panorama Histórico)."""
    vazio = {
        "catalogo": [],
        "total": 0,
        "ja_sairam": 0,
        "faltam_sair": 0,
        "faltantes": [],
        "fonte_aba4": "/analise/analises-inteligentes/?aba=padroes-ii",
        "fonte_aba7": "/analise/analises-inteligentes/?aba=panorama",
    }
    try:
        from analise_inteligentes_diadesorte.service import make_inteligentes_service
        cat = make_inteligentes_service(modality_key).catalogo_padroes(base="geral")
        if not cat.get("sucesso"):
            return vazio
        padroes = list(cat.get("padroes") or [])
        faltantes = [p for p in padroes if _eh_faltante(p)]
        return {
            "catalogo": padroes,
            "total": int(cat.get("total_padroes") or len(padroes)),
            "ja_sairam": int(cat.get("total_padroes_com_frequencia") or (len(padroes) - len(faltantes))),
            "faltam_sair": int(cat.get("total_padroes_faltantes") or len(faltantes)),
            "faltantes": [
                {
                    "padrao": p.get("padrao"),
                    "descricao": p.get("descricao") or "",
                    "jogos_possiveis": p.get("jogos_possiveis"),
                }
                for p in faltantes[:20]
            ],
            "fonte_aba4": "/analise/analises-inteligentes/?aba=padroes-ii",
            "fonte_aba7": "/analise/analises-inteligentes/?aba=panorama",
        }
    except Exception:
        return vazio


def contexto_estatisticas_ciclo(modality_key: str = "diadesorte") -> Dict[str, Any]:
    if not tem_gerador_estatisticas_ciclo(modality_key):
        return {"sucesso": False, "erro": "Gerador disponível apenas no Dia de Sorte."}

    from analise_escolha_visual.service import AnaliseEscolhaVisualService
    from ciclo_cobertura.analise_service import AnaliseCicloCoberturaService

    ciclo = AnaliseCicloCoberturaService.obter_ciclo_atual(modality_key)
    if not ciclo:
        return {
            "sucesso": False,
            "erro": "Nenhum ciclo encontrado. Verifique se há sorteios cadastrados.",
        }

    enriq = AnaliseEscolhaVisualService.enriquecimento(
        modality_key, ordem="desc", limite=0, base_estatistica="geral",
    )
    if not enriq.get("sucesso"):
        return {
            "sucesso": False,
            "erro": enriq.get("erro") or "Falha ao ler Estatísticas Básicas.",
        }

    resumo = enriq.get("resumo") or {}
    linhas = enriq.get("linhas_basicas") or []
    pendentes = [int(x) for x in (ciclo.get("dezenas_pendentes") or [])]
    saidas = [int(x) for x in (ciclo.get("dezenas_saidas") or [])]
    ui = AnaliseEscolhaVisualService.ui_meta(modality_key)

    return {
        "sucesso": True,
        "modality_key": modality_key,
        "modality_nome": ciclo.get("modalidade") or "Dia de Sorte",
        "dezena_min": int(ciclo.get("dezena_min") or ui.get("dezena_min") or 1),
        "dezena_max": int(ciclo.get("dezena_max") or ui.get("dezena_max") or 31),
        "sorteadas": int(ui.get("sorteadas") or 7),
        "pad_width": int(ui.get("pad_width") or 2),
        "extra_mes": True,
        "ciclo": {
            "numero_ciclo": ciclo.get("numero_ciclo"),
            "concurso_inicio": ciclo.get("concurso_inicio"),
            "concurso_atual": ciclo.get("concurso_atual"),
            "quantidade_concursos": ciclo.get("quantidade_concursos"),
            "dezenas_saidas": saidas,
            "dezenas_pendentes": pendentes,
            "total_dezenas_saidas": ciclo.get("total_dezenas_saidas"),
            "total_dezenas_pendentes": len(pendentes),
            "percentual_completo": ciclo.get("percentual_completo"),
            "universo": ciclo.get("universo"),
            "em_andamento": ciclo.get("em_andamento"),
        },
        "estatisticas": {
            "total_sorteios": resumo.get("total_sorteios"),
            "medias": resumo.get("medias") or {},
            "pct_com": resumo.get("pct_com") or {},
            "ultimo": linhas[0] if linhas else None,
        },
        "linhas_basicas": linhas,
        "diagonais": _resumo_diagonais_ctx(linhas, int(ciclo.get("dezena_min") or 1), int(ciclo.get("dezena_max") or 31)),
        "padroes": {
            "fonte_aba4": "/analise/analises-inteligentes/?aba=padroes-ii",
            "fonte_aba7": "/analise/analises-inteligentes/?aba=panorama",
        },
        "fontes": {
            "estatisticas_basicas": "/analise/escolha-visual/",
            "progresso_ciclo": "/analise/ciclo-cobertura/",
            "padroes_ii": "/analise/analises-inteligentes/?aba=padroes-ii",
            "panorama": "/analise/analises-inteligentes/?aba=panorama",
        },
    }


def gerar_apostas_estatisticas_ciclo(
    modality_key: str = "diadesorte",
    *,
    quantidade: int = 10,
    mes_valor: Optional[Any] = None,
) -> Dict[str, Any]:
    ctx = contexto_estatisticas_ciclo(modality_key)
    if not ctx.get("sucesso"):
        return ctx

    ciclo = ctx["ciclo"]
    est = ctx["estatisticas"]
    historico = set()
    try:
        from geradores_elite.validacao.pipeline import carregar_mapa_historico_detalhado
        historico = set(carregar_mapa_historico_detalhado(modality_key).keys())
    except Exception:
        historico = set()

    info_pad = _carregar_padroes(modality_key)
    catalogo_padroes = list(info_pad.get("catalogo") or [])

    out = gerar_apostas_de_contexto(
        pendentes=ciclo["dezenas_pendentes"],
        linhas_basicas=ctx.get("linhas_basicas") or [],
        medias=est.get("medias") or {},
        quantidade=quantidade,
        dezena_min=ctx["dezena_min"],
        dezena_max=ctx["dezena_max"],
        k=ctx["sorteadas"],
        historico=historico,
        catalogo_padroes=catalogo_padroes,
    )
    if not out.get("sucesso"):
        return out

    n = len(out["apostas"])
    meses = resolver_meses_para_lote(mes_valor or "atrasado", n)
    if len(meses) < n:
        meses = (meses + [meses[-1] if meses else 6])[:n]
        while len(meses) < n:
            meses.append(6)

    for i, ap in enumerate(out["apostas"]):
        mn = int(meses[i])
        ap["mes_num"] = mn
        ap["mes_nome"] = MESES_NOME.get(mn, f"Mês {mn}")
        ap["mes_abrev"] = MESES_ABREV.get(mn, str(mn))
        ap["extras"] = {
            "tipo": "mes",
            "num": mn,
            "label": ap["mes_nome"],
        }

    out.update({
        "ciclo": ciclo,
        "estatisticas": {
            "total_sorteios": est.get("total_sorteios"),
            "medias": est.get("medias") or {},
            "pct_com": est.get("pct_com") or {},
            "ultimo": est.get("ultimo"),
        },
        "fontes": ctx["fontes"],
        "padroes": {
            "total": info_pad.get("total"),
            "ja_sairam": info_pad.get("ja_sairam"),
            "faltam_sair": info_pad.get("faltam_sair"),
            "inedito": out.get("padrao_inedito"),
            "distintos": out.get("padroes_distintos"),
            "usados": out.get("padroes_usados"),
            "faltantes": info_pad.get("faltantes"),
            "fonte_aba4": info_pad.get("fonte_aba4"),
            "fonte_aba7": info_pad.get("fonte_aba7"),
        },
        "diagonais": ctx.get("diagonais") or out.get("diagonais") or {},
        "mes_criterio": mes_valor or "atrasado",
        "pad_width": ctx["pad_width"],
    })
    return out
