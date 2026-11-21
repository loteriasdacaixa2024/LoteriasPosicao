# -*- coding: utf-8 -*-
"""Liga a 2A1 ao ciclo, ao Panorama e ao último concurso. Só Dia de Sorte."""
from __future__ import annotations

from typing import Any, Dict, Optional

from analise_escolha_visual.enriquecimento.regras_2a1 import montar_restricoes

from .gerador_2a1 import gerar_lote_2a1
from .service import contexto_estatisticas_ciclo


def _ultimo_par(linhas: list) -> tuple:
    orden = sorted(linhas, key=lambda r: int(r.get("concurso") or 0))
    if not orden:
        return [], []
    ultimo = [int(n) for n in (orden[-1].get("numeros") or orden[-1].get("dezenas") or [])]
    penultimo = []
    if len(orden) > 1:
        penultimo = [int(n) for n in (orden[-2].get("numeros") or orden[-2].get("dezenas") or [])]
    return ultimo, penultimo


def _resumo_restricoes(restr: Dict[str, Any], concurso: Any, data: str) -> Dict[str, Any]:
    def _fmt_seq(grupos):
        return ["-".join(f"{int(n):02d}" for n in g) for g in grupos or []]

    def _fmt_diag(grupos):
        out = []
        for g in grupos or []:
            sym = g.get("dir_sym") or "↘"
            seq = [int(n) for n in (g.get("nums") or [])]
            if sym == "↗" or g.get("dir") == "up":
                seq = list(reversed(seq))
            nums = "-".join(f"{n:02d}" for n in seq)
            out.append(f"{sym} {nums}")
        return out

    return {
        "concurso": concurso,
        "data": data,
        "ultimo": restr.get("ultimo") or [],
        "pares_disponiveis": restr.get("pares_disponiveis") or [],
        "impares_disponiveis": restr.get("impares_disponiveis") or [],
        "repetidos_proibidos": restr.get("repetidos_proibidos") or [],
        "pode_repetir": restr.get("pode_repetir") or [],
        "sequencias_proibidas": _fmt_seq(restr.get("sequencias_proibidas")),
        "finais_proibidos": [",".join(f"{int(n):02d}" for n in g) for g in (restr.get("finais_proibidos") or [])],
        "diagonais_proibidas": _fmt_diag(restr.get("diagonais_proibidas")),
    }


def _cols(modality_key: str) -> int:
    try:
        from analise_estudos.specs import get_estudos_config
        return int(get_estudos_config(modality_key).get("volante_cols") or 10)
    except Exception:
        return 10


def contexto_2a1(modality_key: str = "diadesorte") -> Dict[str, Any]:
    ctx = contexto_estatisticas_ciclo(modality_key)
    if not ctx.get("sucesso"):
        return ctx
    linhas = list(ctx.get("linhas_basicas") or [])
    ultimo, penultimo = _ultimo_par(linhas)
    if not ultimo:
        return {"sucesso": False, "erro": "Não há sorteio para montar a 2A1."}
    orden = sorted(linhas, key=lambda r: int(r.get("concurso") or 0))
    ref = orden[-1]
    restr = montar_restricoes(
        ultimo,
        penultimo,
        dmin=int(ctx["dezena_min"]),
        dmax=int(ctx["dezena_max"]),
        cols=_cols(modality_key),
    )
    ciclo = ctx.get("ciclo") or {}
    panorama = None
    try:
        from analise_inteligentes_diadesorte.service import make_inteligentes_service
        cat = make_inteligentes_service(modality_key).catalogo_padroes(base="geral")
        if cat.get("sucesso"):
            panorama = {
                "total_padroes": cat.get("total_padroes"),
                "ja_sairam": cat.get("total_padroes_com_frequencia"),
                "faltam_sair": cat.get("total_padroes_faltantes"),
                "concursos": cat.get("total_sorteios_analisados"),
            }
    except Exception:
        panorama = None
    return {
        "sucesso": True,
        "modality_key": modality_key,
        "dezena_min": ctx["dezena_min"],
        "dezena_max": ctx["dezena_max"],
        "sorteadas": ctx["sorteadas"],
        "extra_mes": ctx.get("extra_mes"),
        "extra_time": ctx.get("extra_time"),
        "extra_trevo": ctx.get("extra_trevo"),
        "ciclo": {
            "numero_ciclo": ciclo.get("numero_ciclo"),
            "concurso_atual": ciclo.get("concurso_atual"),
            "dezenas_pendentes": ciclo.get("dezenas_pendentes") or [],
            "total_dezenas_pendentes": ciclo.get("total_dezenas_pendentes"),
            "percentual_completo": ciclo.get("percentual_completo"),
        },
        "restricoes": _resumo_restricoes(restr, ref.get("concurso"), ref.get("data") or ""),
        "fontes": {
            "escolha": "/analise/escolha-visual/",
            "panorama": "/analise/analises-inteligentes/?aba=panorama",
            "ciclo": "/analise/ciclo-cobertura/",
            "gerador_2a": "/geradores-elite/estatisticas-ciclo/",
        },
        "panorama": panorama,
    }


def _anexar_meses(out: Dict[str, Any], mes_valor: Optional[Any]) -> None:
    apostas = out.get("apostas") or []
    if not apostas:
        return
    try:
        from diadesorte.mes_sorte_select import MESES_ABREV, MESES_NOME, resolver_meses_para_lote
    except Exception:
        return
    meses = resolver_meses_para_lote(mes_valor or "atrasado", len(apostas))
    while len(meses) < len(apostas):
        meses.append(meses[-1] if meses else 6)
    for i, ap in enumerate(apostas):
        mn = int(meses[i])
        ap["mes_num"] = mn
        ap["mes_nome"] = MESES_NOME.get(mn, f"Mês {mn}")
        ap["mes_abrev"] = MESES_ABREV.get(mn, str(mn))


def gerar_2a1(
    modality_key: str = "diadesorte",
    *,
    quantidade: int = 10,
    repetidos: str = "1-2",
    mes_valor: Optional[Any] = None,
) -> Dict[str, Any]:
    ctx = contexto_estatisticas_ciclo(modality_key)
    if not ctx.get("sucesso"):
        return ctx
    linhas = list(ctx.get("linhas_basicas") or [])
    ultimo, penultimo = _ultimo_par(linhas)
    try:
        from analise_inteligentes_diadesorte.service import make_inteligentes_service
        svc = make_inteligentes_service(modality_key)
        cat = svc.catalogo_padroes(base="geral")
        seq = svc.sequencias_sorteadas(base="geral")
    except Exception as exc:
        return {"sucesso": False, "erro": f"Não foi possível ler o Panorama: {exc}"}
    if not cat.get("sucesso") or not seq.get("sucesso"):
        return {"sucesso": False, "erro": cat.get("erro") or seq.get("erro") or "Panorama indisponível."}

    mapa_hist: Dict[Any, Any] = {}
    historico = set()
    try:
        from geradores_elite.validacao.pipeline import carregar_mapa_historico_detalhado
        mapa_hist = carregar_mapa_historico_detalhado(modality_key) or {}
        historico = set(mapa_hist.keys())
    except Exception:
        mapa_hist = {}
        historico = set()

    ciclo = ctx.get("ciclo") or {}
    mais_saem = list((cat.get("cruzamento_diagonais") or {}).get("mais_saem") or [])
    out = gerar_lote_2a1(
        catalogo=list(cat.get("padroes") or []),
        padroes_cruzamento=mais_saem,
        linhas_panorama=list(seq.get("linhas") or []),
        ultimo=ultimo,
        penultimo=penultimo,
        pendentes=list(ciclo.get("dezenas_pendentes") or []),
        historico=historico,
        quantidade=quantidade,
        repetidos=repetidos,
        dezena_min=int(ctx["dezena_min"]),
        dezena_max=int(ctx["dezena_max"]),
        k=int(ctx["sorteadas"]),
        cols=_cols(modality_key),
    )
    if not out.get("sucesso"):
        return out
    from .service import anexar_extra_apostas
    anexar_extra_apostas(out, modality_key, mes_valor)
    for ap in out.get("apostas") or []:
        chave = frozenset(int(n) for n in (ap.get("dezenas") or []))
        ocor = list(mapa_hist.get(chave) or [])
        ap["ja_sorteada"] = bool(ocor)
        ultima_ocor = ocor[-1] if ocor else {}
        ap["concurso_historico"] = ultima_ocor.get("concurso")
        ap["data_historico"] = ultima_ocor.get("data") or ""
    orden = sorted(linhas, key=lambda r: int(r.get("concurso") or 0))
    ref = orden[-1] if orden else {}
    out["restricoes"] = _resumo_restricoes(
        out.get("restricoes") or {},
        ref.get("concurso"),
        ref.get("data") or "",
    )
    out["panorama"] = {
        "total_padroes": cat.get("total_padroes"),
        "ja_sairam": cat.get("total_padroes_com_frequencia"),
        "faltam_sair": cat.get("total_padroes_faltantes"),
        "concursos": seq.get("total_concursos"),
    }
    out["ciclo"] = {
        "numero_ciclo": ciclo.get("numero_ciclo"),
        "total_dezenas_pendentes": ciclo.get("total_dezenas_pendentes"),
        "dezenas_pendentes": ciclo.get("dezenas_pendentes") or [],
    }
    out["modo_geracao"] = "2a1"
    return out
