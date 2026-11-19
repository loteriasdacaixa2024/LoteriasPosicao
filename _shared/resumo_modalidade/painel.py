# -*- coding: utf-8 -*-
"""Painel central do Resumo Geral — reúne critérios já calculados no sistema."""
from __future__ import annotations

import statistics
from collections import Counter
from typing import Any, Dict, List, Optional, Sequence

from analise_gaps_ciclo.core import (
    analisar_regua_combinacoes,
    gaps_de,
    gaps_sequencia,
    padrao_gaps,
)
from dd_du.core import decompor_lista
from linhas_universo.core import classificar_dezenas
from resumo_modalidade.specs import ResumoSpec


def _fmt2(n: int) -> str:
    return f"{int(n):02d}"


def _moda(counter: Counter):
    if not counter:
        return None, 0
    val, q = counter.most_common(1)[0]
    return val, int(q)


def _pct(n: int, total: int) -> float:
    if not total:
        return 0.0
    return round(100.0 * n / total, 1)


def _faixa(series: Sequence[int]) -> str:
    if not series:
        return "—"
    ss = sorted(series)
    n = len(ss)
    p20 = ss[int(0.20 * (n - 1))]
    p80 = ss[int(0.80 * (n - 1))]
    return f"{p20}–{p80}"


def _item(
    criterio: str,
    atual: str,
    historico: str,
    uso: str,
    fonte: str,
    *,
    tipo: str = "info",
    regra: str = "",
) -> Dict[str, str]:
    """Uma análise. `regra` vazia significa que ela não manda o que seguir."""
    labels = {
        "geracao": "Geração",
        "filtro": "Filtro",
        "disponivel": "Disponível",
        "info": "Informativa",
    }
    return {
        "criterio": criterio,
        "atual": atual,
        "historico": historico,
        "uso": uso,
        "uso_label": labels.get(uso, uso),
        "fonte": fonte,
        "tipo": tipo,
        "regra": (regra or "").strip(),
    }


def _cat(cid: str, titulo: str, itens: List[Dict[str, str]]) -> Dict[str, Any]:
    return {"id": cid, "titulo": titulo, "itens": [i for i in itens if i]}


def _projetar(categorias: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Checklist e regras nascem das análises. Sem segunda lista escrita à mão."""
    checklist: List[Dict[str, Any]] = []
    regras: List[Dict[str, Any]] = []
    for cat in categorias:
        for item in cat["itens"]:
            checklist.append({
                "criterio": item["criterio"],
                "ref": item["historico"],
                "uso": item.get("regra") or item.get("uso_label") or "",
                "tipo": item.get("tipo") or "info",
            })
            texto = str(item.get("regra") or "").strip()
            if not texto:
                continue
            regras.append({
                "n": len(regras) + 1,
                "tipo": item.get("tipo") or "info",
                "texto": texto,
                "criterio": item["criterio"],
            })
    return {"checklist": checklist, "regras": regras}


def _comportamento(modality_key: str):
    try:
        from geradores_elite.comportamento.specs import SPECS
        return SPECS.get((modality_key or "").strip().lower())
    except Exception:
        return None


def montar_painel(
    spec: ResumoSpec,
    sorteios: List[Dict[str, Any]],
    analise: Dict[str, Any],
) -> Dict[str, Any]:
    """Consolida o DNA já calculado com gaps, régua, linhas, DD/DU e indicadores do gerador."""
    n_s = spec.sorteadas
    draws = []
    ordens = []
    for s in sorteios:
        dz = sorted(int(x) for x in s["dezenas"])[:n_s]
        if not dz:
            continue
        draws.append(dz)
        od = [int(x) for x in (s.get("ordem") or []) if x is not None][:n_s]
        ordens.append(od)
    if not draws:
        return {
            "concurso": None,
            "categorias": [],
            "geracao": [],
            "ausentes": [],
            "checklist": [],
            "regras": [],
        }

    ult = draws[-1]
    prev = draws[-2] if len(draws) > 1 else []
    n = len(draws)
    sp = _comportamento(spec.modality_key)

    gap_medios: List[float] = []
    gap_vals: Counter = Counter()
    gap_padroes: Counter = Counter()
    amplitudes: List[int] = []
    qtd_linhas: Counter = Counter()
    cont_linha: Dict[str, Counter] = {}
    qtd_dd: Counter = Counter()
    qtd_du: Counter = Counter()
    pr_c: Counter = Counter()
    mo_c: Counter = Counter()
    m3_c: Counter = Counter()
    fb_c: Counter = Counter()
    diag_com = 0
    gap_ord_vals: Counter = Counter()
    gap_ord_padroes: Counter = Counter()

    diagonais_fn = None
    try:
        from analise_inteligentes_diadesorte.diagonais_volante import diagonais_na_aposta
        diagonais_fn = diagonais_na_aposta
    except Exception:
        diagonais_fn = None

    for dz, od in zip(draws, ordens):
        gs = gaps_de(dz)
        if gs:
            gap_medios.append(sum(gs) / len(gs))
            gap_vals.update(int(g) for g in gs)
            gap_padroes[padrao_gaps(gs)] += 1
        if len(od) >= 2:
            gs_o = gaps_sequencia(od)
            if gs_o:
                gap_ord_vals.update(int(g) for g in gs_o)
                gap_ord_padroes[padrao_gaps(gs_o)] += 1
        amplitudes.append((max(dz) - min(dz)) if dz else 0)
        cl = classificar_dezenas(dz)
        qtd_linhas[cl["qtd_linhas"]] += 1
        for lid, nums in (cl.get("por_linha") or {}).items():
            cont_linha.setdefault(lid, Counter())[len(nums)] += 1
        dec = decompor_lista(dz, 1 if spec.motor == "colunas" else 2)
        qtd_dd[dec["qtd_dd_unicos"]] += 1
        qtd_du[dec["qtd_du_unicos"]] += 1
        if sp is not None:
            pr_c[sum(1 for d in dz if d in sp.primos)] += 1
            mo_c[sum(1 for d in dz if d in sp.moldura)] += 1
            m3_c[sum(1 for d in dz if d in sp.multiplos_3)] += 1
            fb_c[sum(1 for d in dz if d in sp.fibonacci)] += 1
        if diagonais_fn is not None:
            try:
                if diagonais_fn(dz, dmin=spec.dezena_min, dmax=spec.dezena_max):
                    diag_com += 1
            except Exception:
                diagonais_fn = None

    ult_gaps = gaps_de(ult)
    ult_gap_medio = round(sum(ult_gaps) / len(ult_gaps), 2) if ult_gaps else 0
    hist_gap_medio = round(statistics.mean(gap_medios), 2) if gap_medios else 0
    gap_moda, gap_moda_q = _moda(gap_vals)
    pad_moda, pad_moda_q = _moda(gap_padroes)
    ult_pad = padrao_gaps(ult_gaps)
    faixa_gap = _faixa([int(round(x)) for x in gap_medios]) if gap_medios else "—"
    gap_normal = False
    if gap_medios:
        ss = sorted(gap_medios)
        lo = ss[int(0.20 * (len(ss) - 1))]
        hi = ss[int(0.80 * (len(ss) - 1))]
        gap_normal = lo <= ult_gap_medio <= hi

    regua = analisar_regua_combinacoes(list(reversed(draws)), limite_linhas=1)
    reg_ult = regua.get("ultimo") or {}
    refs = regua.get("referencias") or []
    refs_txt = " · ".join(
        f"P{r['posicao']}={_fmt2(r['referencia'])}"
        for r in refs if r.get("referencia") is not None
    ) or "—"
    deltas = [
        p.get("deslocamento")
        for p in (reg_ult.get("posicoes") or [])
        if p.get("deslocamento") is not None
    ]
    if reg_ult.get("conjunto_uniforme"):
        reg_atual = f"conjunto {reg_ult.get('deslocamento_conjunto'):+d} (uniforme)"
    elif deltas:
        na = sum(1 for d in deltas if d == 0)
        reg_atual = f"médio {reg_ult.get('deslocamento_medio')} · {na}/{len(deltas)} na referência"
    else:
        reg_atual = "—"
    reg_hist = "referência = moda de cada posição ordenada"
    if refs:
        reg_hist += f" · {refs_txt}"

    ult_cl = classificar_dezenas(ult)
    linhas_atual = " · ".join(
        f"{lid} {len(nums)}"
        for lid, nums in sorted(
            (ult_cl.get("por_linha") or {}).items(),
            key=lambda kv: int(kv[0][1:]) if kv[0][1:].isdigit() else 0,
        )
    ) or "—"
    moda_ql, _ = _moda(qtd_linhas)
    linhas_medias = []
    for lid in sorted(cont_linha, key=lambda x: int(x[1:]) if x[1:].isdigit() else 0):
        mv, mq = _moda(cont_linha[lid])
        if mv:
            linhas_medias.append(f"{lid} moda {mv} ({_pct(mq, n)}%)")

    ult_dec = decompor_lista(ult, 1 if spec.motor == "colunas" else 2)
    fins = Counter(d % 10 for d in ult)
    fins_txt = " ".join(f"{k}:{v}" for k, v in sorted(fins.items()))
    dd_moda, dd_q = _moda(qtd_dd)
    du_moda, du_q = _moda(qtd_du)

    amp_ult = amplitudes[-1] if amplitudes else 0
    amp_media = round(statistics.mean(amplitudes), 1) if amplitudes else 0
    amp_faixa = _faixa(amplitudes)

    soma = analise.get("soma") or {}
    pi = analise.get("par_impar") or {}
    seq = analise.get("sequencias") or {}
    fin = analise.get("finais") or {}
    rep = analise.get("repeticao") or {}
    faixas = analise.get("faixas") or {}
    ciclo = analise.get("ciclo") or {}
    atual_c = ciclo.get("atual") or {}
    ultimo = analise.get("ultimo") or {}
    dez_stats = (analise.get("dezenas") or {}).get("stats") or []
    quentes = sorted(dez_stats, key=lambda r: (-r["qtd"], r["dezena"]))[:5]
    atrasadas = sorted(dez_stats, key=lambda r: (-r["atraso"], r["dezena"]))[:5]
    top_bma = (faixas.get("top3") or [None])[0] or {}

    pr_ult = sum(1 for d in ult if sp and d in sp.primos) if sp else None
    mo_ult = sum(1 for d in ult if sp and d in sp.moldura) if sp else None
    m3_ult = sum(1 for d in ult if sp and d in sp.multiplos_3) if sp else None
    fb_ult = sum(1 for d in ult if sp and d in sp.fibonacci) if sp else None

    pct_seq = float(seq.get("pct_com_pelo_menos_uma") or 0)
    if pct_seq >= 55:
        seq_tipo = "frequente"
        seq_regra = (
            f"Inclua pelo menos 1 sequência ({pct_seq}% dos concursos). "
            f"Quantidade mais comum: {seq.get('qtd_mais_freq')}."
        )
    else:
        seq_tipo = "nao_confirmado"
        seq_regra = f"Hipótese de sequência em todo concurso não confirmada ({pct_seq}%)."
    pct_fin = float(fin.get("pct_pelo_menos_um") or 0)
    if pct_fin >= 55:
        fin_tipo = "frequente"
        fin_regra = f"Repita pelo menos um final. Isso ocorre em {pct_fin}% dos concursos."
    else:
        fin_tipo = "nao_confirmado"
        fin_regra = f"Hipótese de finais iguais em todo concurso não confirmada ({pct_fin}%)."
    novas = ciclo.get("novas") or {}
    pct_novas = float(novas.get("pct_1_ou_2") or 0)
    if pct_novas < 55:
        novas_tipo = "nao_confirmado"
        novas_regra = (
            f"Não force 1 ou 2 dezenas novas em todo concurso ({pct_novas}%). "
            f"A quantidade mais comum é {novas.get('moda')} ({novas.get('moda_pct')}%)."
        )
    else:
        novas_tipo = "frequente"
        novas_regra = (
            f"A quantidade mais comum de dezenas novas é {novas.get('moda')} "
            f"({novas.get('moda_pct')}%). 1 ou 2 novas em {pct_novas}%."
        )
    mf = (analise.get("padrao_inicial") or {}).get("mais_freq") or {}
    hip = (analise.get("padrao_inicial") or {}).get("hipotese") or {}
    if mf and hip.get("padrao") and hip.get("confirmado_lider"):
        pad_tipo = "frequente"
        pad_hist = (
            f"O padrão inicial mais frequente é {mf.get('valor')} ({mf.get('pct')}% dos concursos)."
        )
        pad_regra = f"O padrão inicial mais frequente é {hip.get('padrao')} ({mf.get('pct')}%)."
    elif mf and hip.get("padrao"):
        pad_tipo = "nao_confirmado"
        pad_hist = (
            f"O padrão inicial mais frequente é {mf.get('valor')} ({mf.get('pct')}%). "
            f"A hipótese {hip.get('padrao')} fica em {hip.get('pct')}%."
        )
        pad_regra = (
            f"Não use {hip.get('padrao')} como padrão obrigatório ({hip.get('pct')}%). "
            f"O mais frequente é {mf.get('valor')} ({mf.get('pct')}%)."
        )
    elif mf:
        pad_tipo = "tendencia"
        pad_hist = (
            f"O padrão inicial mais frequente é {mf.get('valor')} ({mf.get('pct')}% dos concursos)."
        )
        pad_regra = (
            f"Use {mf.get('valor')} como referência de padrão inicial, não como regra rígida "
            f"({mf.get('pct')}%)."
        )
    else:
        pad_tipo, pad_hist, pad_regra = "info", "—", ""
    temporal = analise.get("temporal") or {}
    if temporal.get("confirmado"):
        per_tipo = "tendencia"
        per_hist = "Há desvio pontual de periodicidade no histórico. Não trate como ciclo rígido."
    else:
        per_tipo = "nao_confirmado"
        per_hist = "Repetir o mesmo evento a cada 2, 3 ou 4 concursos não se confirma no histórico."
    n_ord = sum(1 for od in ordens if len(od) >= 2)
    tem_ordem = n_ord >= max(1, int(0.8 * n))
    gap_ord_moda, gap_ord_q = _moda(gap_ord_vals) if tem_ordem else (None, 0)
    pad_ord, pad_ord_q = _moda(gap_ord_padroes) if tem_ordem else (None, 0)
    pct_diag = _pct(diag_com, n) if diagonais_fn is not None else None

    dist_itens = [
        _item(
            "Faixas B/M/A",
            "",
            (
                f"Distribuição mais comum: {top_bma.get('dist')} ({top_bma.get('pct')}% dos concursos)."
                if top_bma else "—"
            ),
            "filtro",
            "Resumo Geral · DNA (faixas da modalidade)",
            tipo="frequente" if top_bma else "info",
            regra=(
                f"Use a distribuição {top_bma.get('dist')} ({top_bma.get('pct')}%) "
                "ou as duas seguintes do ranking. Não zere uma faixa."
                if top_bma else ""
            ),
        ),
        _item(
            "Linhas (blocos de 10)",
            "",
            f"Quantidade de linhas mais comum: {moda_ql} ({_pct(qtd_linhas.get(moda_ql, 0), n)}%)"
            + ((" · " + " · ".join(linhas_medias[:4])) if linhas_medias else ""),
            "disponivel",
            "/analise/linhas-dd-du/ · linhas_universo.core",
            tipo="frequente",
            regra=f"A quantidade de linhas mais comum é {moda_ql}. Use como referência de ocupação do volante.",
        ),
    ]

    def _grupo(nome: str, counter: Counter, fonte: str) -> Dict[str, str]:
        mv, mq = _moda(counter)
        frase = f"Quantidade mais comum de {nome.lower()}: {mv} ({_pct(mq, n)}% dos concursos)."
        return _item(
            nome, "", frase, "geracao", fonte,
            tipo="frequente",
            regra=frase,
        )

    par_itens = [
        _item(
            "Pares × ímpares",
            "",
            f"O mais comum é {pi.get('moda')} ({pi.get('moda_pct')}%). Média {pi.get('media_pares')} pares e {pi.get('media_impares')} ímpares.",
            "geracao",
            "Resumo Geral · DNA e Comportamento (PA/IM)",
            tipo="frequente",
            regra=f"Fique perto de {pi.get('moda')}.",
        ),
    ]
    if sp is not None and pr_ult is not None:
        par_itens.append(_grupo("Primos", pr_c, "Comportamento → Apostas (indicador PR)"))
        par_itens.append(_grupo("Moldura", mo_c, "Comportamento → Apostas (indicador MO)"))
        par_itens.append(_grupo("Múltiplos de 3", m3_c, "Comportamento → Apostas (indicador M3)"))
        par_itens.append(_grupo("Fibonacci", fb_c, "Comportamento → Apostas (indicador FB)"))

    rep_itens = [
        _item(
            "Repetidas do anterior",
            "",
            f"O mais comum é repetir {rep.get('moda')} dezena(s) ({rep.get('moda_pct')}%). 1 ou 2 repetidas em {rep.get('pct_1_ou_2')}% dos concursos. Média {rep.get('media')}.",
            "geracao",
            "Resumo Geral · DNA e Comportamento (RT)",
            tipo="frequente",
            regra=(
                f"Leve {rep.get('moda')} dezena(s) do concurso anterior. "
                f"1 ou 2 repetidas ocorrem em {rep.get('pct_1_ou_2')}% dos concursos."
            ),
        ),
    ]

    pct_gap = _pct(gap_moda_q, sum(gap_vals.values()))
    pct_pad = _pct(pad_moda_q, n)
    gaps_txt = (
        f"O gap mais comum é {gap_moda} ({pct_gap}% dos intervalos). "
        f"Padrão de gaps mais frequente: «{pad_moda}» ({pct_pad}% dos concursos)."
    )
    if pct_pad >= 5:
        gaps_regra = (
            f"Na leitura classificada, o gap de referência é {gap_moda} ({pct_gap}% dos intervalos) "
            f"e o padrão «{pad_moda}» ({pct_pad}%)."
        )
        gaps_tipo = "frequente"
    else:
        gaps_regra = (
            f"Na leitura classificada, o gap mais comum é {gap_moda} ({pct_gap}% dos intervalos). "
            f"O padrão completo mais visto, «{pad_moda}», aparece em {pct_pad}% e não vira regra."
        )
        gaps_tipo = "info"
    partes_faixa = str(faixa_gap).split("–")
    if len(partes_faixa) == 2 and partes_faixa[0] == partes_faixa[1]:
        media_regra = (
            f"A média dos gaps do jogo deve ficar perto de {partes_faixa[0]} "
            f"(média histórica {hist_gap_medio})."
        )
    else:
        media_regra = (
            f"A média dos gaps do jogo deve ficar em {faixa_gap} (média histórica {hist_gap_medio})."
        )
    gaps_itens = [
        _item(
            "Gaps (classificado)",
            "",
            gaps_txt,
            "geracao",
            "Gaps e Régua · gaps_de (leitura classificada)",
            tipo=gaps_tipo,
            regra=gaps_regra,
        ),
        _item(
            "Média dos gaps",
            "",
            f"A média dos gaps costuma ficar em {hist_gap_medio}. Faixa habitual (percentis 20–80): {faixa_gap}.",
            "geracao",
            "Mesma série de gaps_de",
            tipo="frequente",
            regra=media_regra,
        ),
    ]
    if tem_ordem and gap_ord_moda is not None:
        pct_salto = _pct(gap_ord_q, sum(gap_ord_vals.values()))
        pct_ord = _pct(pad_ord_q, n_ord)
        ordem_txt = (
            f"Na ordem de sorteio, o salto mais comum é {int(gap_ord_moda):+d} "
            f"({pct_salto}% dos intervalos). "
            f"Padrão mais frequente: «{pad_ord}» ({pct_ord}% dos concursos)."
        )
        if pct_salto >= 15:
            ordem_tipo = "info"
            ordem_regra = ordem_txt
        else:
            ordem_tipo = "nao_confirmado"
            ordem_regra = (
                f"Na ordem de sorteio, nenhum salto domina "
                f"(o mais comum, {int(gap_ord_moda):+d}, aparece em {pct_salto}% dos intervalos). "
                "Não use essa leitura como filtro."
            )
        gaps_itens.append(_item(
            "Gaps (ordem de sorteio)",
            "",
            ordem_txt,
            "disponivel",
            "Gaps e Régua · gaps_sequencia",
            tipo=ordem_tipo,
            regra=ordem_regra,
        ))

    regua_itens = [
        _item(
            "Régua (deslocamento)",
            "",
            f"{reg_hist}. No último concurso: {reg_atual}.",
            "geracao",
            "Gaps e Régua · analisar_regua_combinacoes",
            tipo="frequente",
            regra=f"Monte cada posição ordenada perto da referência da régua ({refs_txt}).",
        ),
    ]

    seq_itens = [
        _item(
            "Sequências",
            "",
            f"Pelo menos uma sequência em {seq.get('pct_com_pelo_menos_uma')}% dos concursos. Quantidade mais comum: {seq.get('qtd_mais_freq')}. Tamanho mais comum: {seq.get('tamanho_mais_freq')}.",
            "geracao",
            "Resumo Geral · DNA e Comportamento (SQ)",
            tipo=seq_tipo,
            regra=seq_regra,
        ),
    ]
    if pct_diag is not None:
        seq_itens.append(_item(
            "Diagonais do volante",
            "",
            f"Aparecem em {pct_diag}% dos concursos.",
            "disponivel",
            "Estatísticas do Ciclo · diagonais_na_aposta",
            tipo="frequente" if pct_diag >= 55 else "info",
            regra=(
                f"Diagonais aparecem em {pct_diag}% dos concursos."
                if pct_diag >= 55
                else f"Não exija diagonal em todo jogo. Elas aparecem em {pct_diag}% dos concursos."
            ),
        ))

    fin_itens = [
        _item(
            "Finais iguais",
            "",
            f"Pelo menos um final repetido em {fin.get('pct_pelo_menos_um')}% dos concursos.",
            "filtro",
            "Resumo Geral · DNA (finais repetidos)",
            tipo=fin_tipo,
            regra=fin_regra,
        ),
        _item(
            "Distribuição dos finais",
            "",
            f"A quantidade mais comum de finais distintos é {du_moda} ({_pct(du_q, n)}% dos concursos).",
            "disponivel",
            "DD × DU · dígito da unidade",
            tipo="frequente",
            regra=f"A quantidade mais comum de finais distintos é {du_moda}.",
        ),
    ]

    ciclo_txt = (
        f"O ciclo costuma fechar em {ciclo.get('duracao_media')} concursos "
        f"(mínimo {ciclo.get('min')} · máximo {ciclo.get('max')} · {ciclo.get('completos')} ciclos fechados)."
    )
    ciclo_itens = [
        _item(
            "Ciclo de cobertura",
            "",
            ciclo_txt,
            "geracao",
            "Resumo Geral · ciclo do universo; Ciclo — Apostas e Estatísticas do Ciclo",
            tipo="info",
            regra=ciclo_txt,
        ),
    ]
    if atual_c:
        pend = atual_c.get("pendentes") or []
        pend_txt = (
            f"Ciclo {atual_c.get('numero')} · {atual_c.get('concursos')} concursos · "
            f"{atual_c.get('pct')}% do universo · {atual_c.get('pendentes_qtd')} pendentes"
            + (f": {', '.join(pend)}." if pend else ".")
        )
        ciclo_itens.append(_item(
            "Dezenas pendentes do ciclo",
            "",
            pend_txt,
            "geracao",
            "Resumo Geral · ciclo aberto",
            tipo="info",
            regra=(
                f"O ciclo atual ainda não sorteou: {', '.join(pend)}."
                if pend else "O ciclo atual não tem dezena pendente."
            ),
        ))
    ciclo_itens.append(_item(
        "Dezenas novas no ciclo",
        "",
        f"A quantidade mais comum de dezenas novas é {novas.get('moda')} ({novas.get('moda_pct')}%). 1 ou 2 novas em {novas.get('pct_1_ou_2')}%.",
        "info",
        "Resumo Geral · DNA (dezenas novas no ciclo)",
        tipo=novas_tipo,
        regra=novas_regra,
    ))
    fech = ciclo.get("fechamento_1a5") or {}
    if fech.get("n"):
        fech_txt = (
            f"Com 1 a 5 dezenas pendentes, a média de dezenas novas é {fech.get('media')}."
        )
        ciclo_itens.append(_item(
            "Perto do fechamento do ciclo",
            "",
            fech_txt,
            "info",
            "Resumo Geral · concursos com 1 a 5 pendentes",
            tipo="info",
            regra=fech_txt + " Não force dezena nova só porque o ciclo está no fim.",
        ))

    quentes_txt = "As que mais aparecem: " + " ".join(_fmt2(r["dezena"]) for r in quentes) + "."
    atras_txt = "As que há mais concursos não saem: " + " ".join(
        f"{_fmt2(r['dezena'])} ({r['atraso']})" for r in atrasadas
    ) + "."
    freq_itens = [
        _item(
            "Mais frequentes no histórico",
            "",
            quentes_txt,
            "info",
            "Resumo Geral · contagem por dezena em todos os concursos",
            tipo="info",
            regra=quentes_txt + " Filtro de construção, não previsão.",
        ),
        _item(
            "Mais atrasadas",
            "",
            atras_txt,
            "disponivel",
            "Resumo Geral · atraso por dezena",
            tipo="info",
            regra=atras_txt + " Filtro de construção, não previsão.",
        ),
    ]

    soma_itens = [
        _item(
            "Soma",
            "",
            f"Média {soma.get('media')}. Faixa habitual {soma.get('recomendavel')}. Núcleo {soma.get('nucleo')}.",
            "filtro",
            "Resumo Geral · DNA (percentis 20–80)",
            tipo="frequente",
            regra=f"Mire a soma entre {soma.get('recomendavel')}. Núcleo {soma.get('nucleo')}.",
        ),
        _item(
            "Amplitude (máx − mín)",
            "",
            f"Média {amp_media}. Faixa habitual {amp_faixa}.",
            "disponivel",
            "Enriquecimento da Escolha Visual (conjuntos_concurso.amplitude); nenhum gerador filtra por ela",
            tipo="info",
            regra=f"A amplitude (maior menos menor) costuma ficar em {amp_faixa}.",
        ),
    ]

    dd_itens = [
        _item(
            "DD distintos (dezena)",
            "",
            f"A quantidade mais comum de DD distintos é {dd_moda} ({_pct(dd_q, n)}% dos concursos).",
            "disponivel",
            "/analise/linhas-dd-du/ · dd_du.core.decompor_lista",
            tipo="frequente",
            regra=f"A quantidade mais comum de dígitos da dezena distintos é {dd_moda}.",
        ),
        _item(
            "DU distintos (unidade)",
            "",
            f"A quantidade mais comum de DU distintos é {du_moda} ({_pct(du_q, n)}% dos concursos).",
            "disponivel",
            "/analise/linhas-dd-du/ · mesmo decompor_lista",
            tipo="frequente",
            regra=f"A quantidade mais comum de dígitos da unidade distintos é {du_moda}.",
        ),
        _item(
            "Padrão inicial",
            "",
            pad_hist,
            "geracao",
            "Análises Inteligentes · aba 4 (Padrões II) e aba Panorama",
            tipo=pad_tipo,
            regra=pad_regra,
        ),
    ]

    outros = []
    meses = [int(s["mes_num"]) for s in sorteios if s.get("mes_num")]
    if meses:
        mes_c = Counter(meses)
        mes_moda, mes_q = _moda(mes_c)
        nomes_mes: Dict[int, str] = {}
        ultimo_mes: Dict[int, int] = {}
        for i, s in enumerate(sorteios):
            bruto = s.get("mes_num")
            if not bruto:
                continue
            m = int(bruto)
            ultimo_mes[m] = i
            if s.get("mes_nome"):
                nomes_mes[m] = str(s["mes_nome"])
        atraso_mes = sorted(
            ((len(sorteios) - 1 - idx, m) for m, idx in ultimo_mes.items()),
            reverse=True,
        )
        if atraso_mes:
            atr_n, atr_m = atraso_mes[0]
            nome_atr = nomes_mes.get(atr_m) or str(atr_m)
        else:
            atr_n, nome_atr = 0, "—"
        nome_moda = nomes_mes.get(int(mes_moda)) or str(mes_moda)
        mes_hist = (
            f"Mês mais frequente: {nome_moda} ({_pct(mes_q, len(meses))}% dos concursos com mês). "
            f"Mês mais atrasado: {nome_atr}, há {atr_n} concursos."
        )
        outros.append(_item(
            "Mês da Sorte",
            "",
            mes_hist,
            "geracao",
            "Comportamento → Apostas (MS)",
            tipo="tendencia",
            regra=mes_hist,
        ))
    outros.append(_item(
        "Periodicidade (lags 1–6)",
        "",
        per_hist,
        "info",
        "Resumo Geral · DNA temporal",
        tipo=per_tipo,
        regra=(
            per_hist
            if temporal.get("confirmado")
            else "Não monte a aposta em cima de periodicidade a cada 2, 3 ou 4 concursos. O histórico não confirma."
        ),
    ))

    categorias = [
        _cat("distribuicao", "A. Distribuição", dist_itens),
        _cat("paridade", "B. Paridade e grupos", par_itens),
        _cat("repeticao", "C. Repetição", rep_itens),
        _cat("gaps", "D. Gaps / intervalos", gaps_itens),
        _cat("regua", "E. Régua", regua_itens),
        _cat("sequencias", "F. Sequências", seq_itens),
        _cat("finais", "G. Finais", fin_itens),
        _cat("ciclos", "H. Ciclos", ciclo_itens),
        _cat("frequencia", "I. Frequência", freq_itens),
        _cat("soma", "J. Soma e amplitude", soma_itens),
        _cat("dddu", "K. Padrões DD/DU e inicial", dd_itens),
        _cat("outros", "L. Outros critérios já existentes", outros),
    ]

    geracao = []
    for cat in categorias:
        for item in cat["itens"]:
            if item["uso"] in ("geracao", "filtro", "disponivel"):
                geracao.append({**item, "categoria": cat["titulo"]})
    projetado = _projetar(categorias)

    ausentes = [
        {
            "nome": "Concentração / dispersão do resultado",
            "nota": (
                "O módulo /analise/concentracao-acertos/ mede concentração de acertos "
                "de apostas conferidas, não um índice do concurso sorteado. "
                "A dispersão do volante já aparece aqui como amplitude (máx − mín)."
            ),
        },
        {
            "nome": "Quadrantes",
            "nota": "Calculados só na Mega-Sena, em Análises Gerais. Não há quadrante no DNA das demais modalidades.",
        },
    ]

    return {
        "concurso": ultimo.get("concurso"),
        "dezenas": ultimo.get("dezenas") or [_fmt2(d) for d in ult],
        "categorias": categorias,
        "geracao": geracao,
        "ausentes": ausentes,
        "checklist": projetado["checklist"],
        "regras": projetado["regras"],
    }
