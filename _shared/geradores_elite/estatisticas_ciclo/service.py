# -*- coding: utf-8 -*-
"""Consome as análises existentes — não recria Estatísticas Básicas nem o ciclo."""
from __future__ import annotations

from typing import Any, Dict, Optional

from diadesorte.mes_sorte_select import MESES_ABREV, MESES_NOME, resolver_meses_para_lote

from .gerador import _eh_faltante, _resumo_diagonais_janela, gerar_apostas_de_contexto
from .gerador_panorama import gerar_apostas_panorama, resumo_ciclo_panorama


def _resumo_diagonais_ctx(linhas, dmin, dmax):
    return _resumo_diagonais_janela(linhas or [], dmin, dmax)


def tem_gerador_estatisticas_ciclo(modality_key: str) -> bool:
    """Mesmo gerador do Dia de Sorte nas modalidades com ciclo de cobertura."""
    key = (modality_key or "").strip().lower()
    try:
        from ciclo_cobertura.specs import tem_ciclo_cobertura
        return bool(tem_ciclo_cobertura(key))
    except Exception:
        return key == "diadesorte"


def _extra_flags(modality_key: str) -> Dict[str, bool]:
    extra = None
    try:
        from geradores_elite.modality_config import MODALITIES
        extra = (MODALITIES.get(modality_key) or {}).get("extra")
    except Exception:
        extra = "mes" if (modality_key or "").strip().lower() == "diadesorte" else None
    return {
        "extra_mes": extra == "mes",
        "extra_time": extra == "time",
        "extra_trevo": extra == "trevo",
    }


def anexar_extra_apostas(out: Dict[str, Any], modality_key: str, valor: Optional[Any]) -> None:
    """Grava mês, time ou trevos em cada aposta, no mesmo critério do select."""
    apostas = list(out.get("apostas") or [])
    if not apostas:
        return
    flags = _extra_flags(modality_key)
    n = len(apostas)
    bruto = valor if valor not in (None, "", 0, "0") else "atrasado"
    try:
        if flags["extra_mes"]:
            meses = resolver_meses_para_lote(bruto, n)
            if len(meses) < n:
                meses = (meses + [meses[-1] if meses else 6])[:n]
                while len(meses) < n:
                    meses.append(6)
            for i, ap in enumerate(apostas):
                mn = int(meses[i])
                ap["mes_num"] = mn
                ap["mes_nome"] = MESES_NOME.get(mn, f"Mês {mn}")
                ap["mes_abrev"] = MESES_ABREV.get(mn, str(mn))
                ap["extras"] = {"tipo": "mes", "num": mn, "label": ap["mes_nome"]}
        elif flags["extra_time"]:
            from geradores_elite.extra_analise_select import (
                opcoes_time_coracao,
                resolver_time_para_lote,
            )
            payload = opcoes_time_coracao()
            itens = resolver_time_para_lote(bruto, n, opcoes_payload=payload)
            for i, ap in enumerate(apostas):
                it = itens[i] if i < len(itens) else {"time_num": 1, "time_nome": "Time 1"}
                ap["time_num"] = int(it.get("time_num") or 1)
                ap["time_nome"] = it.get("time_nome") or f"Time {ap['time_num']}"
                ap["extras"] = {"tipo": "time", "num": ap["time_num"], "label": ap["time_nome"]}
        elif flags["extra_trevo"]:
            from geradores_elite.extra_analise_select import (
                opcoes_trevos,
                resolver_trevos_para_lote,
            )
            payload = opcoes_trevos()
            pares = resolver_trevos_para_lote(bruto, n, opcoes_payload=payload)
            for i, ap in enumerate(apostas):
                par = list(pares[i] if i < len(pares) else (pares[-1] if pares else [1, 2]))
                ap["trevos"] = par
                ap["trevos_label"] = " ".join(f"{int(x):02d}" for x in par)
                ap["extras"] = {"tipo": "trevo", "numeros": par, "label": ap["trevos_label"]}
    except Exception:
        return


def aba_panorama_num(modality_key: str) -> int:
    """Número da aba Panorama Histórico na análise real."""
    if (modality_key or "").strip().lower() in ("diadesorte", "supersete"):
        return 7
    return 6


def _carregar_padroes(modality_key: str) -> Dict[str, Any]:
    """Catálogo das abas 4 (Padrões II) e do Panorama Histórico."""
    vazio = {
        "ok": False,
        "catalogo": [],
        "total": 0,
        "ja_sairam": 0,
        "faltam_sair": 0,
        "faltantes": [],
        "aba_panorama": aba_panorama_num(modality_key),
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
            "ok": True,
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
            "aba_panorama": aba_panorama_num(modality_key),
            "fonte_aba4": "/analise/analises-inteligentes/?aba=padroes-ii",
            "fonte_aba7": "/analise/analises-inteligentes/?aba=panorama",
            "cruzamento_diagonais": cat.get("cruzamento_diagonais") or {},
        }
    except Exception:
        return vazio


def _padroes_para_tela(modality_key: str) -> Dict[str, Any]:
    """Resumo da análise real, sem o catálogo completo."""
    info = _carregar_padroes(modality_key)
    tela = {
        "aba_panorama": info.get("aba_panorama") or aba_panorama_num(modality_key),
        "fonte_aba4": info.get("fonte_aba4"),
        "fonte_aba7": info.get("fonte_aba7"),
    }
    if info.get("ok"):
        cruz = info.get("cruzamento_diagonais") or {}
        tela.update({
            "total": info.get("total"),
            "ja_sairam": info.get("ja_sairam"),
            "faltam_sair": info.get("faltam_sair"),
            "faltantes": info.get("faltantes") or [],
            "cruzamento_diagonais": {
                "n_concursos": cruz.get("n_concursos") or 0,
                "n_com_diagonal": cruz.get("n_com_diagonal") or 0,
                "pct_com_diagonal": cruz.get("pct_com_diagonal") or 0,
                "mais_saem": list(cruz.get("mais_saem") or [])[:5],
            },
        })
    return tela


def contexto_estatisticas_ciclo(modality_key: str = "diadesorte") -> Dict[str, Any]:
    if not tem_gerador_estatisticas_ciclo(modality_key):
        return {"sucesso": False, "erro": "Gerador indisponível nesta modalidade."}

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
        **_extra_flags(modality_key),
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
        "padroes": _padroes_para_tela(modality_key),
        "ciclo_panorama": resumo_ciclo_panorama(len(pendentes), int(ui.get("sorteadas") or 7)),
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

    anexar_extra_apostas(out, modality_key, mes_valor)

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
            "aba_panorama": info_pad.get("aba_panorama"),
            "fonte_aba4": info_pad.get("fonte_aba4"),
            "fonte_aba7": info_pad.get("fonte_aba7"),
        },
        "diagonais": ctx.get("diagonais") or out.get("diagonais") or {},
        "mes_criterio": mes_valor or "atrasado",
        "pad_width": ctx["pad_width"],
        "ciclo_panorama": ctx.get("ciclo_panorama"),
        "modo_geracao": "ciclo",
    })
    return out


def _anexar_meses(out: Dict[str, Any], ctx: Dict[str, Any], mes_valor: Optional[Any]) -> Dict[str, Any]:
    if not out.get("sucesso"):
        return out
    if not ctx.get("extra_mes"):
        anexar_extra_apostas(out, str(ctx.get("modality_key") or ""), mes_valor)
        est = ctx.get("estatisticas") or {}
        out.update({
            "ciclo": ctx.get("ciclo"),
            "estatisticas": {
                "total_sorteios": est.get("total_sorteios"),
                "medias": est.get("medias") or {},
                "pct_com": est.get("pct_com") or {},
                "ultimo": est.get("ultimo"),
            },
            "fontes": ctx.get("fontes"),
            "diagonais": ctx.get("diagonais") or out.get("diagonais") or {},
            "pad_width": ctx.get("pad_width"),
            "ciclo_panorama": ctx.get("ciclo_panorama") or out.get("ciclo_panorama"),
        })
        return out
    n = len(out.get("apostas") or [])
    meses = resolver_meses_para_lote(mes_valor or "atrasado", n)
    if n and len(meses) < n:
        meses = (meses + [meses[-1] if meses else 6])[:n]
        while len(meses) < n:
            meses.append(6)
    for i, ap in enumerate(out.get("apostas") or []):
        mn = int(meses[i]) if i < len(meses) else 6
        ap["mes_num"] = mn
        ap["mes_nome"] = MESES_NOME.get(mn, f"Mês {mn}")
        ap["mes_abrev"] = MESES_ABREV.get(mn, str(mn))
        ap["extras"] = {
            "tipo": "mes",
            "num": mn,
            "label": ap["mes_nome"],
        }
    est = ctx.get("estatisticas") or {}
    out.update({
        "ciclo": ctx.get("ciclo"),
        "estatisticas": {
            "total_sorteios": est.get("total_sorteios"),
            "medias": est.get("medias") or {},
            "pct_com": est.get("pct_com") or {},
            "ultimo": est.get("ultimo"),
        },
        "fontes": ctx.get("fontes"),
        "diagonais": ctx.get("diagonais") or out.get("diagonais") or {},
        "mes_criterio": mes_valor or "atrasado",
        "pad_width": ctx.get("pad_width"),
        "ciclo_panorama": ctx.get("ciclo_panorama") or out.get("ciclo_panorama"),
    })
    return out


def gerar_apostas_estatisticas_ciclo_panorama(
    modality_key: str = "diadesorte",
    *,
    quantidade: int = 10,
    mes_valor: Optional[Any] = None,
) -> Dict[str, Any]:
    ctx = contexto_estatisticas_ciclo(modality_key)
    if not ctx.get("sucesso"):
        return ctx

    historico = set()
    try:
        from geradores_elite.validacao.pipeline import carregar_mapa_historico_detalhado
        historico = set(carregar_mapa_historico_detalhado(modality_key).keys())
    except Exception:
        historico = set()

    est = ctx["estatisticas"]
    out = gerar_apostas_panorama(
        pendentes=ctx["ciclo"]["dezenas_pendentes"],
        linhas_basicas=ctx.get("linhas_basicas") or [],
        medias=est.get("medias") or {},
        quantidade=quantidade,
        dezena_min=ctx["dezena_min"],
        dezena_max=ctx["dezena_max"],
        k=ctx["sorteadas"],
        historico=historico,
        modality_key=modality_key,
    )
    out = _anexar_meses(out, ctx, mes_valor)
    if out.get("sucesso"):
        info_pad = _carregar_padroes(modality_key)
        out["padroes"] = {
            "total": info_pad.get("total"),
            "ja_sairam": info_pad.get("ja_sairam"),
            "faltam_sair": info_pad.get("faltam_sair"),
            "inedito": out.get("padrao_inedito"),
            "distintos": out.get("padroes_distintos"),
            "usados": out.get("padroes_usados"),
            "faltantes": info_pad.get("faltantes"),
            "aba_panorama": info_pad.get("aba_panorama"),
            "fonte_aba4": info_pad.get("fonte_aba4"),
            "fonte_aba7": info_pad.get("fonte_aba7"),
        }
    return out
