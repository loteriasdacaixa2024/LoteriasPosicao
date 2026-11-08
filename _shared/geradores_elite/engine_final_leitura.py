# -*- coding: utf-8 -*-
"""Leitura integrada do Engine Final — Dia de Sorte.

Toda análise que participa da geração entra em `analises` com um
veredito: cabe, nao_cabe ou nao_opina. Análise sem veredito não
influencia o lote. Se o veredito é nao_cabe, a análise não é usada.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

from analise_escolha_visual.enriquecimento.motor import conjuntos_concurso
from analise_gaps_ciclo.core import gaps_de, padrao_gaps
from analise_inteligentes_diadesorte.service import (
    descricao_bma_do_padrao,
    padrao_final,
    padrao_inicial,
)
from linhas_universo.core import linha_da_dezena
from posicao_analise.core import soma_digitos

from .engine_final_sintonia import (
    CATALOGO_ANALISES as _CATALOGO_ANALISES,
    aplicar_trava,
    cortar_universo as _cortar_universo,
    diag_alcanca as _diag_alcanca,
    padroes_na_hora,
    resolver_ciclo,
    voto_intersecta as _voto_intersecta,
)


def _moda(cont: Counter) -> Dict[str, Any]:
    total = int(sum(cont.values()))
    if not total:
        return {"valor": None, "pct": 0.0, "vezes": 0, "total": 0}
    valor, vezes = cont.most_common(1)[0]
    return {
        "valor": valor,
        "pct": round(100.0 * int(vezes) / total, 1),
        "vezes": int(vezes),
        "total": total,
    }


def _pts_moda(valor: int, moda: Any, peso: float = 14.0) -> float:
    if moda is None:
        return 0.0
    dist = abs(int(valor) - int(moda))
    if dist == 0:
        return peso
    if dist == 1:
        return peso * 0.2
    return -peso


def _faixa(vals: Sequence[float], lo: float = 0.25, hi: float = 0.75) -> Optional[Tuple[int, int]]:
    nums = sorted(int(v) for v in vals)
    if not nums:
        return None

    def q(p: float) -> int:
        i = int(round((len(nums) - 1) * p))
        return nums[max(0, min(len(nums) - 1, i))]

    a, b = q(lo), q(hi)
    return (a, b) if a <= b else (b, a)


def _linhas_de(nums: Sequence[int]) -> List[str]:
    return sorted({linha_da_dezena(int(n)) for n in nums}, key=lambda x: int(x[1:]))


def _digitos(nums: Sequence[int]) -> Set[str]:
    out: Set[str] = set()
    for n in nums:
        out.update(f"{int(n):02d}")
    return out


def _soma_digitos_jogo(nums: Sequence[int]) -> int:
    return sum(soma_digitos(int(n), 2) for n in nums)


def resumir_forma(nums: Sequence[int], ultimo: Sequence[int]) -> Dict[str, Any]:
    s = sorted(int(x) for x in nums)
    ant = {int(x) for x in ultimo}
    det = conjuntos_concurso(s, sorted(ant) if ant else None)
    b = det["basicos"]
    seqs = (b["sequencias"].get("detalhe") or {}).get("grupos") or []
    fins = (b["finais"].get("detalhe") or {}).get("grupos") or []
    try:
        from analise_inteligentes_diadesorte.diagonais_volante import diagonais_na_aposta

        diags = diagonais_na_aposta(s, dmin=1, dmax=31) or []
    except Exception:
        diags = []
    diag_txt = ""
    if diags:
        primeiro = diags[0]
        diag_txt = primeiro.get("nums_fmt") or "-".join(f"{int(n):02d}" for n in (primeiro.get("nums") or []))
    pini = padrao_inicial(s)
    return {
        "pares": int(b["pares"]["quantidade"]),
        "impares": int(b["impares"]["quantidade"]),
        "repetidas": int(b["repetidos"]["quantidade"]),
        "sequencias": len(seqs),
        "finais": len(fins),
        "soma": int(det["soma"]),
        "linhas": " ".join(_linhas_de(s)),
        "diagonal": diag_txt,
        "padrao_inicial": pini,
        "padrao_bma": descricao_bma_do_padrao(pini),
        "padrao_final": padrao_final(s),
        "digitos": len(_digitos(s)),
        "soma_digitos": _soma_digitos_jogo(s),
    }


def _carregar_recorrencia(modality_key: str):
    try:
        from analise_inteligentes_diadesorte.service import make_inteligentes_service

        out = make_inteligentes_service(modality_key).recorrencia_padroes(base="geral")
    except Exception:
        return None
    if not out or not out.get("sucesso"):
        return None
    return out


def _voto_posicao_sniper() -> Tuple[Optional[Set[int]], Optional[Set[int]]]:
    """Posição (top por ordem oficial) e Sniper (fortes), se a consulta responder."""
    posicao: Optional[Set[int]] = None
    sniper: Optional[Set[int]] = None
    try:
        from posicao_analise.service_factory import make_service

        data = make_service("diadesorte").analise_agregada(janela=30)
        fortes: Set[int] = set()
        for pos in data.get("posicoes") or []:
            top = pos.get("top_freq") or []
            if top:
                fortes.add(int(top[0]))
        if fortes:
            posicao = fortes
        plugins = data.get("plugins_resumo") or {}
        sni = {int(x) for x in (plugins.get("sniper_fortes") or [])}
        if sni:
            sniper = sni
    except Exception:
        posicao = None
    if sniper is None:
        try:
            from geradores_elite.inteligente import get_inteligente_service

            intel = get_inteligente_service("diadesorte")
            if intel:
                ev = intel.painel_evidencias(intel.montar_contexto())
                sni = set()
                for item in (ev.get("numeros_fortes") or [])[:8]:
                    d = item.get("dezena", item.get("digito"))
                    if d is not None:
                        sni.add(int(d))
                if sni:
                    sniper = sni
        except Exception:
            sniper = None
    return posicao, sniper


def preparar_leitura(
    modality_key: str,
    scores: Dict[int, float],
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if modality_key != "diadesorte":
        return {"sucesso": False, "erro": "Leitura integrada disponível no Dia de Sorte."}

    from geradores_elite.estatisticas_ciclo.gerador import _atrasos
    from geradores_elite.estatisticas_ciclo.service import contexto_estatisticas_ciclo

    ctx = contexto_estatisticas_ciclo(modality_key)
    if not ctx.get("sucesso"):
        return {"sucesso": False, "erro": ctx.get("erro") or "Contexto indisponível."}

    linhas = list(ctx.get("linhas_basicas") or [])
    ultimo = linhas[0] if linhas else {}
    ultimo_nums = [int(x) for x in (ultimo.get("numeros") or [])]
    ciclo = ctx.get("ciclo") or {}
    pendentes = {int(x) for x in (ciclo.get("dezenas_pendentes") or [])}
    dmin = int(ctx.get("dezena_min") or 1)
    dmax = int(ctx.get("dezena_max") or 31)

    somas: List[int] = []
    somas_dig: List[int] = []
    qtd_dig: List[int] = []
    freq_ini: Counter = Counter()
    freq_fim: Counter = Counter()
    freq_linhas: Counter = Counter()
    freq_gaps: Counter = Counter()
    freq_pares: Counter = Counter()
    freq_rep: Counter = Counter()
    freq_seq: Counter = Counter()
    freq_fin: Counter = Counter()
    freq_qtd_linhas: Counter = Counter()
    k_jogo = int(ctx.get("sorteadas") or 7)
    for row in linhas:
        nums = [int(x) for x in (row.get("numeros") or [])]
        if len(nums) < 2:
            continue
        det = conjuntos_concurso(nums, None)
        somas.append(int(det["soma"]))
        somas_dig.append(_soma_digitos_jogo(nums))
        qtd_dig.append(len(_digitos(nums)))
        freq_pares[int((row.get("pares") or {}).get("quantidade") or 0)] += 1
        freq_rep[int((row.get("repetidos") or {}).get("quantidade") or 0)] += 1
        freq_seq[int(((row.get("sequencias") or {}).get("detalhe") or {}).get("qtd_grupos") or 0)] += 1
        freq_fin[int(((row.get("finais") or {}).get("detalhe") or {}).get("qtd_grupos") or 0)] += 1
        freq_qtd_linhas[len(_linhas_de(nums))] += 1
        freq_ini[padrao_inicial(sorted(nums))] += 1
        freq_fim[padrao_final(sorted(nums))] += 1
        freq_linhas[" ".join(_linhas_de(nums))] += 1
        freq_gaps[padrao_gaps(gaps_de(nums))] += 1

    soma_faixa = _faixa(somas)
    dig_faixa = _faixa(somas_dig)
    moda_pares = _moda(freq_pares)
    moda_rep = _moda(freq_rep)
    moda_seq = _moda(freq_seq)
    moda_fin = _moda(freq_fin)
    moda_dig = _moda(Counter(qtd_dig))
    moda_soma_dig = _moda(Counter(somas_dig))
    moda_linhas_qtd = _moda(freq_qtd_linhas)
    moda_soma = _moda(Counter(somas))
    linha_moda = freq_linhas.most_common(1)[0][0] if freq_linhas else ""
    total_pad = sum(freq_ini.values()) or 1
    ranking_padroes = [
        {
            "padrao": p,
            "vezes": int(v),
            "pct": round(100.0 * int(v) / total_pad, 1),
            "bma": descricao_bma_do_padrao(p),
        }
        for p, v in freq_ini.most_common(50)
    ]
    padrao_moda = ranking_padroes[0]["padrao"] if ranking_padroes else ""
    pares_moda = moda_pares.get("valor")
    alvo = {
        "pares": int(pares_moda) if pares_moda is not None else 3,
        "rep_min": int(moda_rep["valor"]) if moda_rep.get("valor") is not None else 1,
        "rep_max": int(moda_rep["valor"]) if moda_rep.get("valor") is not None else 1,
        "quer_seq": True,
        "quer_fin": True,
        "soma_lo": soma_faixa[0] if soma_faixa else 95,
        "soma_hi": soma_faixa[1] if soma_faixa else 130,
    }
    historico = {
        "pares": pares_moda,
        "impares": (k_jogo - int(pares_moda)) if pares_moda is not None else None,
        "pares_pct": moda_pares.get("pct"),
        "repetidas": moda_rep.get("valor"),
        "repetidas_pct": moda_rep.get("pct"),
        "sequencias": moda_seq.get("valor"),
        "sequencias_pct": moda_seq.get("pct"),
        "finais": moda_fin.get("valor"),
        "finais_pct": moda_fin.get("pct"),
        "digitos": moda_dig.get("valor"),
        "digitos_pct": moda_dig.get("pct"),
        "soma_digitos": moda_soma_dig.get("valor"),
        "soma": moda_soma.get("valor"),
        "soma_faixa": list(soma_faixa) if soma_faixa else None,
        "linhas": linha_moda,
        "linhas_qtd": moda_linhas_qtd.get("valor"),
        "padrao_inicial": padrao_moda,
        "padroes_ranking": [
            {"padrao": r["padrao"], "pct": r["pct"], "bma": r["bma"]}
            for r in ranking_padroes[:20]
        ],
        "diagonal_pct": float((ctx.get("diagonais") or {}).get("janela_pct") or 0),
    }
    gaps_top = {p for p, _ in freq_gaps.most_common(12) if p}
    freq_diag: Counter = Counter()
    try:
        from analise_inteligentes_diadesorte.diagonais_volante import (
            diag_lines,
            diag_runs_in_draw,
            pos_map,
            volante_rows,
        )

        rows_v = volante_rows(dmin, dmax, 10)
        linhas_diag = diag_lines(rows_v)
        mapa_pos = pos_map(rows_v)
        for row in linhas:
            nums = [int(x) for x in (row.get("numeros") or [])]
            if len(nums) < 2:
                continue
            for run in diag_runs_in_draw(set(nums), linhas_diag, mapa_pos):
                if int(run.get("len") or 0) < 2:
                    continue
                freq_diag[tuple(int(n) for n in run.get("nums") or [])] += 1
    except Exception:
        freq_diag = Counter()
    top_diags = [
        {"nums": list(nums), "vezes": int(vezes)}
        for nums, vezes in freq_diag.most_common(24)
        if len(nums) >= 2
    ]
    linhas_ultimo = _linhas_de(ultimo_nums) if ultimo_nums else []
    padrao_ultimo = padrao_inicial(sorted(ultimo_nums)) if ultimo_nums else ""
    gaps_ultimo = padrao_gaps(gaps_de(ultimo_nums)) if len(ultimo_nums) >= 2 else ""
    diag = ctx.get("diagonais") or {}

    pool_conc: Optional[List[int]] = None
    dados = list((meta or {}).get("dados_dezenas") or [])
    if dados:
        try:
            from concentracao_acertos.core import pool_sugerido

            pool_conc = pool_sugerido(dados, 16, "freq", dezena_min=dmin, dezena_max=dmax)
        except Exception:
            pool_conc = None

    posicao, sniper = _voto_posicao_sniper()
    ciclo_info = resolver_ciclo(pendentes, k_jogo, dmin, dmax)
    numero_ciclo = ciclo.get("numero_ciclo") or "—"
    ciclo_leitura = f"ciclo {numero_ciclo} · {ciclo_info['leitura']}"
    rec_raw = _carregar_recorrencia(modality_key)
    freq_padrao = Counter(freq_ini)
    if rec_raw:
        na_hora, n_hora = padroes_na_hora(
            rec_raw.get("padroes") or [],
            rec_raw.get("ultimo_concurso"),
            ciclo_info["pool_padrao"],
            k_jogo,
            bool(ciclo_info["travar_padrao"]),
            freq_padrao,
        )
        if na_hora:
            total_vezes = sum(int(r["vezes"]) for r in na_hora) or 1
            for r in na_hora:
                r["pct"] = round(100.0 * int(r["vezes"]) / total_vezes, 1)
            ranking_padroes = na_hora
            rec_veredito = "cabe"
            amostra_hora = ", ".join(r["padrao"] for r in na_hora[:3])
            rec_leitura = (
                f"{len(na_hora)} de {n_hora} padrão(ões) na hora cabem no ciclo "
                f"({amostra_hora}). O lote usa só esses formatos."
            )
            padrao_veredito = "cabe"
            padrao_leitura = f"Formatos na hora que cabem no ciclo: {amostra_hora}."
        else:
            ranking_padroes = []
            rec_veredito = "nao_cabe"
            rec_leitura = (
                f"{n_hora} padrão(ões) na hora, nenhum cabe nas dezenas deste ciclo. "
                "Recorrência não entra neste lote."
            )
            padrao_veredito = "nao_cabe"
            padrao_leitura = "O padrão frequente da janela fica de fora: a recorrência não coube no ciclo."
    else:
        rec_veredito = "nao_opina"
        rec_leitura = "A aba Recorrências não respondeu. O lote não usa a hora do padrão."
        if ranking_padroes:
            amostra = ", ".join(r["padrao"] for r in ranking_padroes[:3])
            padrao_veredito = "cabe"
            padrao_leitura = f"Sem a hora da recorrência, entram os formatos mais vistos na janela ({amostra})."
        else:
            padrao_veredito = "nao_opina"
            padrao_leitura = "Sem ranking de padrão nesta janela."

    locked = list(ciclo_info["locked"])
    pares_alvo = alvo.get("pares")
    exigir_pares = True
    if pares_alvo is not None and locked:
        pares_lock = sum(1 for n in locked if int(n) % 2 == 0)
        impares_lock = len(locked) - pares_lock
        if pares_lock > int(pares_alvo) or impares_lock > (k_jogo - int(pares_alvo)):
            exigir_pares = False
    exigir_digitos = True
    if historico.get("digitos") is not None and locked:
        if len({int(n) // 10 for n in locked}) > int(historico["digitos"]):
            exigir_digitos = False

    universo = list(ciclo_info["universo"])
    sniper_v = _voto_intersecta(sniper, universo)
    posicao_v = _voto_intersecta(posicao, universo)
    conc_set = set(pool_conc or [])
    conc_v = _voto_intersecta(conc_set, universo) if pool_conc else "nao_opina"
    if sniper_v == "nao_cabe":
        sniper = None
    if posicao_v == "nao_cabe":
        posicao = None
    if conc_v == "nao_cabe":
        pool_conc = None

    usar_diagonal = True
    diag_v = "nao_opina"
    diag_leitura = "Sem leitura de diagonal nesta janela."
    if diag:
        pct_diag = float(diag.get("janela_pct") or 0)
        if pct_diag >= 55 and top_diags and not _diag_alcanca(top_diags, universo):
            usar_diagonal = False
            diag_v = "nao_cabe"
            diag_leitura = (
                f"A janela tem diagonal em {pct_diag}% dos concursos, "
                "mas nenhuma dessas diagonais cabe no universo deste ciclo. Não entra na nota."
            )
        else:
            diag_v = "cabe"
            diag_leitura = (
                f"Em {pct_diag}% dos concursos. O lote acompanha essa presença dentro do ciclo."
            )

    pares_v = "cabe" if historico.get("pares") is not None else "nao_opina"
    pares_leitura = (
        f"mais frequente no histórico: {historico.get('pares')} pares / {historico.get('impares')} ímpares ({historico.get('pares_pct')}%)"
    )
    if pares_v == "cabe" and not exigir_pares:
        pares_v = "nao_cabe"
        pares_leitura = (
            "As pendentes travadas já estouram o par/ímpar da janela. "
            "Pares não entram como trava neste lote."
        )
    impares_v = pares_v
    impares_leitura = (
        pares_leitura
        if pares_v == "nao_cabe"
        else f"acompanha os pares · {historico.get('impares')} ímpares"
    )
    if historico.get("impares") is None and pares_v != "nao_cabe":
        impares_v = "nao_opina"
        impares_leitura = "Sem leitura de ímpares nesta janela."

    digitos_v = "cabe" if historico.get("digitos") is not None else "nao_opina"
    digitos_leitura = (
        f"mais frequente: {historico.get('digitos')} dígitos distintos ({historico.get('digitos_pct')}%)"
    )
    if digitos_v == "cabe" and not exigir_digitos:
        digitos_v = "nao_cabe"
        digitos_leitura = (
            "As pendentes travadas já usam mais grupos de dígito do que a moda. "
            "A quantidade de dígitos não trava este lote."
        )

    def _tem(valor: Any, texto: str, vazio: str) -> Tuple[str, str]:
        if valor is None or valor == "" or valor == []:
            return "nao_opina", vazio
        return "cabe", texto

    rep_v, rep_l = _tem(
        historico.get("repetidas"),
        f"mais frequente: {historico.get('repetidas')} ({historico.get('repetidas_pct')}%)",
        "Sem leitura de repetidas nesta janela.",
    )
    seq_v, seq_l = _tem(
        historico.get("sequencias"),
        f"mais frequente: {historico.get('sequencias')} grupo(s) ({historico.get('sequencias_pct')}%)",
        "Sem leitura de sequências nesta janela.",
    )
    fin_v, fin_l = _tem(
        historico.get("finais"),
        f"mais frequente: {historico.get('finais')} grupo(s) ({historico.get('finais_pct')}%)",
        "Sem leitura de finais nesta janela.",
    )
    if soma_faixa:
        soma_v, soma_l = "cabe", f"valor mais frequente {historico.get('soma')} · faixa {soma_faixa[0]}–{soma_faixa[1]}"
    else:
        soma_v, soma_l = "nao_opina", "Sem faixa de soma nesta janela."
    if linha_moda:
        lin_v, lin_l = "cabe", f"assinatura mais frequente: {linha_moda}"
    else:
        lin_v, lin_l = "nao_opina", "Sem assinatura de linhas nesta janela."
    if freq_fim:
        pf_v, pf_l = "cabe", "o final mais repetido no histórico entra na nota"
    else:
        pf_v, pf_l = "nao_opina", "Sem padrão final nesta janela."
    if dig_faixa:
        sd_v, sd_l = "cabe", f"mais frequente: {historico.get('soma_digitos')} · faixa {dig_faixa[0]}–{dig_faixa[1]}"
    else:
        sd_v, sd_l = "nao_opina", "Sem faixa da soma dos dígitos nesta janela."
    if gaps_top:
        gap_v, gap_l = "cabe", "saltos entre as dezenas ordenadas entram na nota quando batem com a janela"
    else:
        gap_v, gap_l = "nao_opina", "Sem leitura de gaps nesta janela."
    if sniper_v == "cabe":
        sn_l = f"{len(sniper or [])} dezenas fortes que ainda cabem no ciclo"
    elif sniper_v == "nao_cabe":
        sn_l = "As dezenas fortes do sniper estão fora do universo deste ciclo. Sniper não entra."
    else:
        sn_l = "Sniper sem dezenas fortes nesta leitura."
    if posicao_v == "cabe":
        po_l = "dezena mais frequente em cada ordem oficial, dentro do ciclo"
    elif posicao_v == "nao_cabe":
        po_l = "O favorito de cada posição está fora do universo deste ciclo. Posição não entra."
    else:
        po_l = "Posição sem voto nesta leitura."
    if conc_v == "cabe":
        co_l = f"pool de {len(pool_conc or [])} dezenas por frequência, dentro do ciclo"
    elif conc_v == "nao_cabe":
        co_l = "O pool da concentração não cruza o universo deste ciclo. Concentração não entra."
    else:
        co_l = "Concentração sem pool nesta leitura."
    if dados:
        mod_v, mod_l = "cabe", "núcleo de frequência, atraso e equilíbrio 01–15 / 16–31"
    else:
        mod_v, mod_l = "nao_opina", "Central de Modelos sem núcleo nesta geração."

    textos = {
        "ciclo": (ciclo_info["veredito"], ciclo_leitura),
        "recorrencia": (rec_veredito, rec_leitura),
        "padrao_inicial": (padrao_veredito, padrao_leitura),
        "pares": (pares_v, pares_leitura),
        "impares": (impares_v, impares_leitura),
        "repetidas": (rep_v, rep_l),
        "sequencias": (seq_v, seq_l),
        "finais": (fin_v, fin_l),
        "soma": (soma_v, soma_l),
        "linhas": (lin_v, lin_l),
        "diagonal": (diag_v, diag_leitura),
        "padrao_final": (pf_v, pf_l),
        "digitos": (digitos_v, digitos_leitura),
        "soma_digitos": (sd_v, sd_l),
        "gaps": (gap_v, gap_l),
        "sniper": (sniper_v, sn_l),
        "posicao": (posicao_v, po_l),
        "concentracao": (conc_v, co_l),
        "modelos": (mod_v, mod_l),
    }
    analises = [
        {"id": cid, "nome": nome, "veredito": textos[cid][0], "leitura": textos[cid][1]}
        for cid, nome in _CATALOGO_ANALISES
    ]
    criterios = [
        {"id": a["id"], "nome": a["nome"], "papel": "veredito", "leitura": a["leitura"], "veredito": a["veredito"]}
        for a in analises
    ]

    return {
        "sucesso": True,
        "concurso_referencia": ultimo.get("concurso"),
        "ultimo_numeros": ultimo_nums,
        "pendentes": pendentes,
        "ciclo_modo": ciclo_info["modo"],
        "universo": list(ciclo_info["universo"]),
        "locked": locked,
        "exigir_pares": exigir_pares and pares_v == "cabe",
        "exigir_digitos": exigir_digitos and digitos_v == "cabe",
        "usar_diagonal": usar_diagonal and diag_v == "cabe",
        "alvo": alvo,
        "atrasos": _atrasos(linhas, dmin, dmax),
        "soma_faixa": soma_faixa,
        "dig_faixa": dig_faixa,
        "digitos_med": historico.get("digitos"),
        "historico": historico,
        "k_historico": k_jogo,
        "linhas_ultimo": linhas_ultimo,
        "padrao_ultimo": padrao_ultimo,
        "freq_ini": freq_ini,
        "freq_fim": freq_fim,
        "gaps_top": gaps_top,
        "gaps_ultimo": gaps_ultimo,
        "diag_pct": float(diag.get("janela_pct") or 0),
        "top_diags": top_diags,
        "ranking_padroes": ranking_padroes,
        "sniper": sniper,
        "posicao": posicao,
        "pool_concentracao": set(pool_conc or []),
        "usar_modelos": bool(dados) and mod_v == "cabe",
        "scores": scores,
        "criterios": criterios,
        "analises": analises,
    }


def _tem_diagonal(nums: Sequence[int]) -> bool:
    try:
        from analise_inteligentes_diadesorte.diagonais_volante import diagonais_na_aposta

        return bool(diagonais_na_aposta(nums, dmin=1, dmax=31))
    except Exception:
        return False


def _plantar_diagonal(
    segmento: Sequence[int],
    busca: Dict[int, float],
    cfg: Dict[str, Any],
    k: int,
    candidatos: Optional[List[int]],
    idx: int,
) -> Optional[List[int]]:
    permitidos = set(int(n) for n in candidatos) if candidatos else None
    locked = [int(n) for n in segmento if permitidos is None or int(n) in permitidos]
    if len(locked) < 2 or len(locked) > k:
        return None
    dmin = int(cfg.get("dezena_min") or 1)
    dmax = int(cfg.get("dezena_max") or 31)
    universo = sorted(int(n) for n in candidatos) if candidatos else list(range(dmin, dmax + 1))
    pool = [n for n in universo if n not in set(locked)]
    pool.sort(key=lambda n: (-float(busca.get(n) or 0), n))
    falta = k - len(locked)
    if len(pool) < falta:
        return None
    janela = pool[: max(falta + 10, 16)]
    giro = int(idx) % max(1, len(janela))
    girado = janela[giro:] + janela[:giro]
    nums = sorted(locked + girado[:falta])
    if len(nums) != k or not _tem_diagonal(nums):
        return None
    return nums


def leitura_publica(leitura: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "sucesso": True,
        "concurso_referencia": leitura.get("concurso_referencia"),
        "ultimo_numeros": list(leitura.get("ultimo_numeros") or []),
        "criterios": list(leitura.get("criterios") or []),
        "analises": list(leitura.get("analises") or []),
        "ciclo_modo": leitura.get("ciclo_modo") or "livre",
        "historico": dict(leitura.get("historico") or {}),
    }


def _pontuar(nums: Sequence[int], leitura: Dict[str, Any], scores_base: Dict[int, float]) -> float:
    from geradores_elite.estatisticas_ciclo.gerador import _score_jogo

    s = sorted(int(x) for x in nums)
    ultimo = set(int(x) for x in (leitura.get("ultimo_numeros") or []))
    pts = _score_jogo(
        s,
        ultimo_set=ultimo,
        alvo=leitura.get("alvo") or {},
        atrasos=leitura.get("atrasos") or {},
    )
    reps = [n for n in s if n in ultimo]
    alvo = leitura.get("alvo") or {}
    extra = len(reps) - int(alvo.get("rep_max") or 2)
    if extra > 0:
        pts -= 1.6 * extra

    hist = leitura.get("historico") or {}
    forma = resumir_forma(s, list(ultimo))
    pts += _pts_moda(int(forma["pares"]), hist.get("pares"), 16)
    pts += _pts_moda(int(forma["digitos"]), hist.get("digitos"), 16)
    pts += _pts_moda(int(forma["repetidas"]), hist.get("repetidas"), 8)
    pts += _pts_moda(int(forma["sequencias"]), hist.get("sequencias"), 8)
    pts += _pts_moda(int(forma["finais"]), hist.get("finais"), 6)
    pts += _pts_moda(len(_linhas_de(s)), hist.get("linhas_qtd"), 6)
    pts += _pts_moda(int(forma["soma_digitos"]), hist.get("soma_digitos"), 6)
    if forma.get("linhas") and forma.get("linhas") == hist.get("linhas"):
        pts += 5.0
    ranking_pos = {
        r.get("padrao"): i
        for i, r in enumerate(leitura.get("ranking_padroes") or [])
    }
    pos_padrao = ranking_pos.get(forma.get("padrao_inicial"))
    if pos_padrao is not None:
        pts += max(3.0, 8.0 - pos_padrao * 0.2)

    pend = leitura.get("pendentes") or set()
    na_pend = [n for n in s if n in pend]
    pts += min(4.0, 0.7 * len(na_pend))
    por_linha: Dict[str, int] = Counter(linha_da_dezena(n) for n in na_pend)
    if any(q >= 3 for q in por_linha.values()):
        pts -= 1.2

    pfim = padrao_final(s)
    freq_fim: Counter = leitura.get("freq_fim") or Counter()
    if freq_fim and freq_fim.get(pfim, 0) > 0:
        pts += 1.0

    sm = sum(s)
    faixa = leitura.get("soma_faixa")
    if faixa and faixa[0] <= sm <= faixa[1]:
        pts += 2.0
    elif faixa and (sm < faixa[0] - 15 or sm > faixa[1] + 15):
        pts -= 1.5

    qd = len(_digitos(s))
    med = leitura.get("digitos_med")
    if med is not None and abs(qd - int(med)) <= 1:
        pts += 1.5

    sd = _soma_digitos_jogo(s)
    df = leitura.get("dig_faixa")
    if df and df[0] <= sd <= df[1]:
        pts += 1.5

    if leitura.get("usar_diagonal", True):
        tem_diag = _tem_diagonal(s)
        pct_diag = float(leitura.get("diag_pct") or 0)
        if tem_diag:
            pts += 9.0 if pct_diag >= 60 else 4.0
        elif pct_diag >= 60:
            pts -= 7.0

    gp = padrao_gaps(gaps_de(s))
    if gp and gp in (leitura.get("gaps_top") or set()):
        pts += 2.0
    if gp and gp == leitura.get("gaps_ultimo"):
        pts -= 1.0

    sniper = leitura.get("sniper") or set()
    if sniper:
        pts += min(1.5, 0.35 * len(set(s) & sniper))
    pos = leitura.get("posicao") or set()
    if pos:
        pts += min(1.2, 0.3 * len(set(s) & pos))
    pool = leitura.get("pool_concentracao") or set()
    if pool:
        pts += min(1.5, 0.15 * len(set(s) & pool))

    if leitura.get("usar_modelos"):
        baixas = sum(1 for n in s if n <= 15)
        altas = len(s) - baixas
        if min(baixas, altas) >= 2:
            pts += 1.5
        top_score = sorted(scores_base, key=lambda d: -float(scores_base.get(d) or 0))[:12]
        pts += min(1.2, 0.15 * len(set(s) & set(top_score)))

    mx = max(scores_base.values()) if scores_base else 1.0
    if mx:
        pts += 4.0 * (sum(float(scores_base.get(n) or 0) for n in s) / (mx * max(len(s), 1)))
    return pts


def _casa_historico(nums: Sequence[int], leitura: Dict[str, Any]) -> bool:
    hist = leitura.get("historico") or {}
    forma = resumir_forma(nums, leitura.get("ultimo_numeros") or [])
    k_hist = int(leitura.get("k_historico") or 0)
    if k_hist and len(list(nums)) != k_hist:
        return True
    pares = hist.get("pares")
    digitos = hist.get("digitos")
    if leitura.get("exigir_pares", True) and pares is not None and int(forma["pares"]) != int(pares):
        return False
    if leitura.get("exigir_digitos", True) and digitos is not None and int(forma["digitos"]) != int(digitos):
        return False
    return True


def _montar_moda(
    busca: Dict[int, float],
    cfg: Dict[str, Any],
    k: int,
    pares_alvo: int,
    digitos_alvo: Optional[int],
    idx: int,
    candidatos: Optional[List[int]],
    locked: Optional[Sequence[int]] = None,
) -> Optional[List[int]]:
    dmin = int(cfg.get("dezena_min") or 1)
    dmax = int(cfg.get("dezena_max") or 31)
    universo = sorted(int(n) for n in candidatos) if candidatos else list(range(dmin, dmax + 1))
    fixos = [int(n) for n in (locked or []) if n in set(universo)]
    if len(fixos) > k:
        return None
    pares_fixos = sum(1 for n in fixos if n % 2 == 0)
    impares_fixos = len(fixos) - pares_fixos
    precisa_par = int(pares_alvo) - pares_fixos
    precisa_impar = (k - int(pares_alvo)) - impares_fixos
    if precisa_par < 0 or precisa_impar < 0:
        return None
    ocupados = set(fixos)
    pares = [n for n in universo if n % 2 == 0 and n not in ocupados]
    impares = [n for n in universo if n % 2 == 1 and n not in ocupados]
    pares.sort(key=lambda n: (-float(busca.get(n) or 0), n))
    impares.sort(key=lambda n: (-float(busca.get(n) or 0), n))

    def giro(pool: List[int], qtd: int, salt: int) -> Optional[List[int]]:
        if qtd == 0:
            return []
        if len(pool) < qtd:
            return None
        janela = pool[: max(qtd + 12, min(len(pool), 18))]
        g = int(salt) % max(1, len(janela))
        girado = janela[g:] + janela[:g]
        return girado[:qtd]

    bloco_p = giro(pares, precisa_par, idx)
    bloco_i = giro(impares, precisa_impar, idx * 3 + 1)
    if bloco_p is None or bloco_i is None:
        return None
    nums = sorted(fixos + bloco_p + bloco_i)
    if len(nums) != k:
        return None
    if digitos_alvo is None:
        return nums
    alvo_d = int(digitos_alvo)
    for _ in range(18):
        atual = len(_digitos(nums))
        if atual == alvo_d:
            return nums
        substituido = False
        for i, n in enumerate(list(nums)):
            if n in ocupados:
                continue
            paridade = n % 2
            for cand in universo:
                if cand in nums or cand % 2 != paridade:
                    continue
                trial = sorted(nums[:i] + nums[i + 1 :] + [cand])
                novo = len(_digitos(trial))
                if (atual < alvo_d and novo > atual) or (atual > alvo_d and novo < atual):
                    nums = trial
                    substituido = True
                    break
            if substituido:
                break
        if not substituido:
            break
    return nums if len(_digitos(nums)) == alvo_d else None


def _universo_cfg(cfg: Dict[str, Any], candidatos: Optional[Sequence[int]]) -> List[int]:
    dmin = int(cfg.get("dezena_min") or 1)
    dmax = int(cfg.get("dezena_max") or 31)
    if candidatos:
        return sorted(int(n) for n in candidatos)
    return list(range(dmin, dmax + 1))


def _ajustar_paridade(
    nums: Sequence[int],
    universo: Sequence[int],
    pares_alvo: int,
    congelados: Optional[Sequence[int]] = None,
) -> List[int]:
    atual = list(nums)
    fixos = {int(n) for n in (congelados or [])}
    for _ in range(8):
        pares = sum(1 for n in atual if n % 2 == 0)
        if pares == int(pares_alvo):
            return sorted(atual)
        quer_par = pares < int(pares_alvo)
        mudou = False
        usados = set(atual)
        for i, n in enumerate(atual):
            if n in fixos or (n % 2 == 0) == quer_par:
                continue
            dig = n // 10
            for cand in universo:
                if cand in usados or cand // 10 != dig or ((cand % 2 == 0) != quer_par):
                    continue
                atual[i] = cand
                mudou = True
                break
            if mudou:
                break
        if not mudou:
            break
    return sorted(atual)


def _ajustar_digitos_mesmo_grupo(
    nums: Sequence[int],
    universo: Sequence[int],
    alvo: int,
    pares_alvo: int,
    congelados: Optional[Sequence[int]] = None,
) -> List[int]:
    atual = list(nums)
    fixos = {int(n) for n in (congelados or [])}
    for _ in range(16):
        qtd = len(_digitos(atual))
        pares = sum(1 for n in atual if n % 2 == 0)
        if qtd == int(alvo) and pares == int(pares_alvo):
            return sorted(atual)
        mudou = False
        for i, n in enumerate(list(atual)):
            if n in fixos:
                continue
            for cand in universo:
                if cand in atual or cand // 10 != n // 10 or cand % 2 != n % 2:
                    continue
                trial = sorted(cand if x == n else x for x in atual)
                novo = len(_digitos(trial))
                if (qtd < int(alvo) and novo > qtd) or (qtd > int(alvo) and novo < qtd):
                    atual = trial
                    mudou = True
                    break
            if mudou:
                break
        if not mudou:
            break
    return sorted(atual)


def _montar_no_padrao(
    padrao: str,
    busca: Dict[int, float],
    cfg: Dict[str, Any],
    k: int,
    pares_alvo: int,
    digitos_alvo: Optional[int],
    idx: int,
    candidatos: Optional[List[int]],
    locked: Optional[Sequence[int]] = None,
    exigir_pares: bool = True,
    exigir_digitos: bool = True,
) -> Optional[List[int]]:
    digs = [int(x) for x in str(padrao).replace(",", " ").split() if str(x).strip().isdigit()]
    if len(digs) != k:
        return None
    need = Counter(digs)
    universo = _universo_cfg(cfg, candidatos)
    uni = set(universo)
    fixos = [int(n) for n in (locked or []) if int(n) in uni or not uni]
    if len(fixos) > k:
        return None
    have = Counter(n // 10 for n in fixos)
    for dig, qtd in have.items():
        if need.get(dig, 0) < qtd:
            return None
    nums: List[int] = list(fixos)
    ocupados = set(fixos)
    for dig, qtd in sorted(need.items()):
        falta = qtd - have.get(dig, 0)
        if falta < 0:
            return None
        pool = [n for n in universo if n // 10 == dig and n not in ocupados]
        if len(pool) < falta:
            return None
        if not pool or falta == 0:
            continue
        pool.sort(key=lambda n: (-float(busca.get(n) or 0), n))
        giro = int(idx) % len(pool)
        girado = pool[giro:] + pool[:giro]
        nums.extend(girado[:falta])
    if exigir_pares:
        nums = _ajustar_paridade(nums, universo, int(pares_alvo), fixos)
        if sum(1 for n in nums if n % 2 == 0) != int(pares_alvo):
            return None
    esperado = " ".join(str(d) for d in digs)
    if padrao_inicial(sorted(nums)) != esperado:
        return None
    if exigir_digitos and digitos_alvo is not None:
        nums = _ajustar_digitos_mesmo_grupo(nums, universo, int(digitos_alvo), int(pares_alvo), fixos)
        if exigir_pares and sum(1 for n in nums if n % 2 == 0) != int(pares_alvo):
            return None
        if padrao_inicial(sorted(nums)) != esperado:
            return None
    return sorted(nums) if len(nums) == k else None


def _lote_pelos_padroes(
    busca: Dict[int, float],
    leitura: Dict[str, Any],
    scores: Dict[int, float],
    cfg: Dict[str, Any],
    k: int,
    qtd: int,
    candidatos: Optional[List[int]],
) -> List[List[int]]:
    ranking = list(leitura.get("ranking_padroes") or [])
    hist = leitura.get("historico") or {}
    exigir_pares = bool(leitura.get("exigir_pares", True))
    exigir_digitos = bool(leitura.get("exigir_digitos", True))
    if not ranking:
        return []
    if exigir_pares and hist.get("pares") is None:
        return []
    if k != int(leitura.get("k_historico") or k):
        return []
    pares_alvo = int(hist["pares"]) if hist.get("pares") is not None else 0
    digitos_alvo = hist.get("digitos") if exigir_digitos else None
    locked = [int(n) for n in (leitura.get("locked") or [])]
    pct_diag = float(leitura.get("diag_pct") or 0) if leitura.get("usar_diagonal", True) else 0
    quota_diag = int(round(qtd * pct_diag / 100.0)) if pct_diag >= 55 else 0
    out: List[List[int]] = []
    usados: Set[Tuple[int, ...]] = set()
    ocupadas: Set[frozenset] = set()
    try:
        from geradores_elite.validacao.validador_global import ValidadorGeradoresElite

        ocupadas = set(ValidadorGeradoresElite._memoria("diadesorte"))
    except Exception:
        ocupadas = set()
    com_diag = 0
    for rank, item in enumerate(ranking):
        if len(out) >= qtd:
            break
        padrao = str(item.get("padrao") or "")
        melhores: List[Tuple[float, List[int], bool, bool]] = []
        for t in range(48):
            nums = _montar_no_padrao(
                padrao, busca, cfg, k, pares_alvo, digitos_alvo, rank * 7 + t, candidatos,
                locked=locked, exigir_pares=exigir_pares, exigir_digitos=exigir_digitos,
            )
            if not nums:
                continue
            chave = tuple(nums)
            if chave in usados or frozenset(chave) in ocupadas:
                continue
            sc = _pontuar(nums, leitura, scores)
            tem = _tem_diagonal(nums)
            dig_ok = digitos_alvo is None or len(_digitos(nums)) == int(digitos_alvo)
            if dig_ok:
                sc += 10
            if tem and com_diag < quota_diag:
                sc += 12
            melhores.append((sc, nums, tem, dig_ok))
        if not melhores:
            continue
        com_digito = [m for m in melhores if m[3]]
        pool = com_digito or melhores
        pool.sort(key=lambda m: -m[0])
        escolhido = pool[0]
        out.append(escolhido[1])
        usados.add(tuple(escolhido[1]))
        if escolhido[2]:
            com_diag += 1
    return out


def escolher_lote(
    scores: Dict[int, float],
    leitura: Dict[str, Any],
    cfg: Dict[str, Any],
    k: int,
    qtd: int,
    montar: Callable[..., List[int]],
    candidatos: Optional[List[int]] = None,
) -> List[List[int]]:
    """Monta um lote diversificado. A nota usa a leitura; a busca não copia o último concurso inteiro."""
    universo, locked, conjunto_rejeitado = _cortar_universo(leitura, candidatos)
    if conjunto_rejeitado:
        analises = [a for a in (leitura.get("analises") or []) if a.get("id") != "conjunto_base"]
        analises.append({
            "id": "conjunto_base",
            "nome": "Conjunto-base",
            "veredito": "nao_cabe",
            "leitura": "O conjunto não inclui as dezenas que o ciclo exige. O lote segue o ciclo.",
        })
        leitura["analises"] = analises
        criterios = [c for c in (leitura.get("criterios") or []) if c.get("id") != "conjunto_base"]
        criterios.append({
            "id": "conjunto_base",
            "nome": "Conjunto-base",
            "papel": "veredito",
            "veredito": "nao_cabe",
            "leitura": analises[-1]["leitura"],
        })
        leitura["criterios"] = criterios
    elif candidatos:
        analises = [a for a in (leitura.get("analises") or []) if a.get("id") != "conjunto_base"]
        analises.append({
            "id": "conjunto_base",
            "nome": "Conjunto-base",
            "veredito": "cabe",
            "leitura": "O conjunto cabe no ciclo. O lote usa a interseção.",
        })
        leitura["analises"] = analises
    leitura["locked"] = locked
    candidatos = universo or candidatos
    busca = dict(scores)
    for n in leitura.get("ultimo_numeros") or []:
        if int(n) in busca:
            busca[int(n)] = float(busca[int(n)]) - float(cfg.get("sorteadas") or 7) * 0.8

    por_padrao = _lote_pelos_padroes(busca, leitura, scores, cfg, k, qtd, candidatos)

    def _fechar(lista: Sequence[Sequence[int]]) -> List[List[int]]:
        saida: List[List[int]] = []
        vistos_trava: Set[Tuple[int, ...]] = set()
        base = list(candidatos or [])
        for nums in lista:
            travado = aplicar_trava(nums, locked, base, k)
            chave = tuple(travado)
            if len(chave) != k or chave in vistos_trava:
                continue
            if locked and any(n not in chave for n in locked):
                continue
            if leitura.get("ciclo_modo") == "recorte" and base and any(n not in set(base) for n in chave):
                continue
            vistos_trava.add(chave)
            saida.append(list(chave))
            if len(saida) >= qtd:
                break
        return saida

    fechado_padrao = _fechar(por_padrao)
    if len(fechado_padrao) >= qtd:
        return fechado_padrao

    vistos: Set[Tuple[int, ...]] = set()
    ranqueados: List[Tuple[float, List[int], bool]] = []

    def _guardar(nums: Sequence[int]) -> None:
        chave = tuple(sorted(int(x) for x in nums))
        if len(chave) != k or chave in vistos:
            return
        vistos.add(chave)
        ranqueados.append((_pontuar(chave, leitura, scores), list(chave), _tem_diagonal(chave)))

    tentativas = max(48, int(qtd) * 10)
    for i in range(tentativas):
        _guardar(montar(busca, cfg, k, i, [list(t) for t in vistos], candidatos))

    hist = leitura.get("historico") or {}
    pares_alvo = hist.get("pares")
    digitos_alvo = hist.get("digitos")
    perfil_do_historico = (
        leitura.get("exigir_pares", True)
        and pares_alvo is not None
        and k == int(leitura.get("k_historico") or k)
    )
    digitos_moda = digitos_alvo if leitura.get("exigir_digitos", True) else None
    if perfil_do_historico:
        for i in range(max(30, int(qtd) * 4)):
            montada = _montar_moda(
                busca, cfg, k, int(pares_alvo),
                int(digitos_moda) if digitos_moda is not None else None,
                i, candidatos, locked=locked,
            )
            if montada:
                _guardar(montada)

    segmentos = list(leitura.get("top_diags") or []) if leitura.get("usar_diagonal", True) else []
    if perfil_do_historico:
        for i, seg in enumerate(segmentos[:12]):
            trava_diag = list(locked)
            for n in seg.get("nums") or []:
                if int(n) not in trava_diag:
                    trava_diag.append(int(n))
            if len(trava_diag) > k:
                continue
            montada = _montar_moda(
                busca, cfg, k, int(pares_alvo),
                int(digitos_moda) if digitos_moda is not None else None,
                i + 3, candidatos, locked=trava_diag,
            )
            if montada:
                _guardar(montada)
    for i, seg in enumerate(segmentos):
        segmento = list(locked)
        for n in seg.get("nums") or []:
            if int(n) not in segmento:
                segmento.append(int(n))
        if len(segmento) > k:
            continue
        plantada = _plantar_diagonal(segmento, busca, cfg, k, candidatos, i)
        if plantada:
            _guardar(plantada)
        if len(segmentos) > 8 and i >= 20:
            break

    ranqueados.sort(key=lambda x: -x[0])

    escolhidas: List[List[int]] = []
    assinaturas: List[str] = []
    pct_diag = float(leitura.get("diag_pct") or 0) if leitura.get("usar_diagonal", True) else 0
    quota_diag = int(round(qtd * pct_diag / 100.0)) if pct_diag >= 55 else 0

    def cabe(nums: Sequence[int], rigor: int) -> bool:
        sig = " ".join(_linhas_de(nums))
        if any(len(set(nums) & set(p)) >= k - 1 for p in escolhidas):
            return False
        if rigor >= 2 and assinaturas.count(sig) >= 3:
            return False
        if rigor >= 3 and assinaturas.count(sig) >= 2:
            return False
        return True

    def _pegar(somente_diag: bool, rigor: int, exige_casa: bool) -> None:
        for _sc, nums, tem in ranqueados:
            if len(escolhidas) >= qtd:
                return
            if exige_casa and not _casa_historico(nums, leitura):
                continue
            if somente_diag and not tem:
                continue
            if any(nums == p for p in escolhidas):
                continue
            if not cabe(nums, rigor):
                continue
            if somente_diag and sum(1 for escolhida in escolhidas if _tem_diagonal(escolhida)) >= quota_diag:
                return
            escolhidas.append(nums)
            assinaturas.append(" ".join(_linhas_de(nums)))

    if quota_diag:
        for rigor in (3, 2, 1):
            _pegar(True, rigor, True)
            if sum(1 for escolhida in escolhidas if _tem_diagonal(escolhida)) >= quota_diag:
                break
    for rigor in (3, 2, 1):
        _pegar(False, rigor, True)
        if len(escolhidas) >= qtd:
            break
    if len(escolhidas) < qtd:
        for rigor in (2, 1):
            _pegar(False, rigor, False)
            if len(escolhidas) >= qtd:
                break
    return _fechar(list(por_padrao) + escolhidas)


def aplicar_forma(apostas: Sequence[Dict[str, Any]], ultimo: Sequence[int]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for ap in apostas or []:
        item = dict(ap)
        dz = item.get("dezenas") or []
        if dz:
            item["forma"] = resumir_forma(dz, ultimo)
        out.append(item)
    return out
