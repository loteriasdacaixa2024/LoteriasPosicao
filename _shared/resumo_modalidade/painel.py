# -*- coding: utf-8 -*-
"""Painel central do Resumo Geral — reúne critérios já calculados no sistema."""
from __future__ import annotations

import statistics
from collections import Counter
from typing import Any, Dict, List, Optional, Sequence

from analise_gaps_ciclo.core import analisar_regua_combinacoes, gaps_de, padrao_gaps
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
) -> Dict[str, str]:
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
    }


def _cat(cid: str, titulo: str, itens: List[Dict[str, str]]) -> Dict[str, Any]:
    return {"id": cid, "titulo": titulo, "itens": [i for i in itens if i]}


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
    for s in sorteios:
        dz = sorted(int(x) for x in s["dezenas"])[:n_s]
        if dz:
            draws.append(dz)
    if not draws:
        return {"concurso": None, "categorias": [], "geracao": [], "ausentes": []}

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

    diagonais_fn = None
    try:
        from analise_inteligentes_diadesorte.diagonais_volante import diagonais_na_aposta
        diagonais_fn = diagonais_na_aposta
    except Exception:
        diagonais_fn = None

    for dz in draws:
        gs = gaps_de(dz)
        if gs:
            gap_medios.append(sum(gs) / len(gs))
            gap_vals.update(int(g) for g in gs)
            gap_padroes[padrao_gaps(gs)] += 1
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
        ),
        _item(
            "Linhas (blocos de 10)",
            "",
            f"Quantidade de linhas mais comum: {moda_ql} ({_pct(qtd_linhas.get(moda_ql, 0), n)}%)"
            + ((" · " + " · ".join(linhas_medias[:4])) if linhas_medias else ""),
            "disponivel",
            "/analise/linhas-dd-du/ · linhas_universo.core",
        ),
    ]

    par_itens = [
        _item(
            "Pares × ímpares",
            "",
            f"O mais comum é {pi.get('moda')} ({pi.get('moda_pct')}%). Média {pi.get('media_pares')} pares e {pi.get('media_impares')} ímpares.",
            "geracao",
            "Resumo Geral · DNA e Comportamento (PA/IM)",
        ),
    ]
    if sp is not None and pr_ult is not None:
        mv, mq = _moda(pr_c)
        par_itens.append(_item(
            "Primos",
            "",
            f"Quantidade mais comum: {mv} ({_pct(mq, n)}% dos concursos).",
            "geracao",
            "Comportamento → Apostas (indicador PR)",
        ))
        mv, mq = _moda(mo_c)
        par_itens.append(_item(
            "Moldura",
            "",
            f"Quantidade mais comum: {mv} ({_pct(mq, n)}% dos concursos).",
            "geracao",
            "Comportamento → Apostas (indicador MO)",
        ))
        mv, mq = _moda(m3_c)
        par_itens.append(_item(
            "Múltiplos de 3",
            "",
            f"Quantidade mais comum: {mv} ({_pct(mq, n)}% dos concursos).",
            "geracao",
            "Comportamento → Apostas (indicador M3)",
        ))
        mv, mq = _moda(fb_c)
        par_itens.append(_item(
            "Fibonacci",
            "",
            f"Quantidade mais comum: {mv} ({_pct(mq, n)}% dos concursos).",
            "geracao",
            "Comportamento → Apostas (indicador FB)",
        ))

    rep_itens = [
        _item(
            "Repetidas do anterior",
            "",
            f"O mais comum é repetir {rep.get('moda')} dezena(s) ({rep.get('moda_pct')}%). 1 ou 2 repetidas em {rep.get('pct_1_ou_2')}% dos concursos. Média {rep.get('media')}.",
            "geracao",
            "Resumo Geral · DNA e Comportamento (RT)",
        ),
    ]

    gaps_itens = [
        _item(
            "Gaps (classificado)",
            "",
            (
                f"O gap mais comum é {gap_moda} ({_pct(gap_moda_q, sum(gap_vals.values()))}% dos intervalos). "
                f"Padrão de gaps mais frequente: «{pad_moda}» ({_pct(pad_moda_q, n)}% dos concursos)."
            ),
            "geracao",
            "Gaps e Régua · gaps_de (leitura classificada)",
        ),
        _item(
            "Média dos gaps",
            "",
            f"A média dos gaps costuma ficar em {hist_gap_medio}. Faixa habitual (percentis 20–80): {faixa_gap}.",
            "geracao",
            "Mesma série de gaps_de",
        ),
    ]

    regua_itens = [
        _item(
            "Régua (deslocamento)",
            "",
            reg_hist,
            "geracao",
            "Gaps e Régua · analisar_regua_combinacoes",
        ),
    ]

    seq_itens = [
        _item(
            "Sequências",
            "",
            f"Pelo menos uma sequência em {seq.get('pct_com_pelo_menos_uma')}% dos concursos. Quantidade mais comum: {seq.get('qtd_mais_freq')}. Tamanho mais comum: {seq.get('tamanho_mais_freq')}.",
            "geracao",
            "Resumo Geral · DNA e Comportamento (SQ)",
        ),
    ]
    if diagonais_fn is not None and diag_com >= 0:
        seq_itens.append(_item(
            "Diagonais do volante",
            "",
            f"Aparecem em {_pct(diag_com, n)}% dos concursos.",
            "disponivel",
            "Estatísticas do Ciclo · diagonais_na_aposta",
        ))

    fin_itens = [
        _item(
            "Finais iguais",
            "",
            f"Pelo menos um final repetido em {fin.get('pct_pelo_menos_um')}% dos concursos.",
            "filtro",
            "Resumo Geral · DNA (finais repetidos)",
        ),
        _item(
            "Distribuição dos finais",
            "",
            f"A quantidade mais comum de finais distintos é {du_moda} ({_pct(du_q, n)}% dos concursos).",
            "disponivel",
            "DD × DU · dígito da unidade",
        ),
    ]

    ciclo_itens = [
        _item(
            "Ciclo de cobertura",
            "",
            (
                f"O ciclo costuma fechar em {ciclo.get('duracao_media')} concursos "
                f"(mínimo {ciclo.get('min')} · máximo {ciclo.get('max')} · {ciclo.get('completos')} ciclos fechados)."
            ),
            "geracao",
            "Resumo Geral · ciclo do universo; Ciclo — Apostas e Estatísticas do Ciclo",
        ),
    ]
    novas = analise.get("ciclo", {}).get("novas") or {}
    ciclo_itens.append(_item(
        "Dezenas novas no ciclo",
        "",
        f"A quantidade mais comum de dezenas novas é {novas.get('moda')} ({novas.get('moda_pct')}%). 1 ou 2 novas em {novas.get('pct_1_ou_2')}% — não é regra da maioria.",
        "info",
        "Resumo Geral · DNA (hipótese 1–2 novas não é regra rígida)",
    ))

    freq_itens = [
        _item(
            "Mais frequentes no histórico",
            "",
            "As que mais aparecem: " + " ".join(_fmt2(r["dezena"]) for r in quentes) + ".",
            "info",
            "Resumo Geral · contagem por dezena em todos os concursos",
        ),
    ]

    soma_itens = [
        _item(
            "Soma",
            "",
            f"Média {soma.get('media')}. Faixa habitual {soma.get('recomendavel')}. Núcleo {soma.get('nucleo')}.",
            "filtro",
            "Resumo Geral · DNA (percentis 20–80)",
        ),
        _item(
            "Amplitude (máx − mín)",
            "",
            f"Média {amp_media}. Faixa habitual {amp_faixa}.",
            "disponivel",
            "Enriquecimento da Escolha Visual (conjuntos_concurso.amplitude); nenhum gerador filtra por ela",
        ),
    ]

    mf = (analise.get("padrao_inicial") or {}).get("mais_freq") or {}
    dd_itens = [
        _item(
            "DD distintos (dezena)",
            "",
            f"A quantidade mais comum de DD distintos é {dd_moda} ({_pct(dd_q, n)}% dos concursos).",
            "disponivel",
            "/analise/linhas-dd-du/ · dd_du.core.decompor_lista",
        ),
        _item(
            "DU distintos (unidade)",
            "",
            f"A quantidade mais comum de DU distintos é {du_moda} ({_pct(du_q, n)}% dos concursos).",
            "disponivel",
            "/analise/linhas-dd-du/ · mesmo decompor_lista",
        ),
        _item(
            "Padrão inicial",
            "",
            (
                f"O padrão inicial mais frequente é {mf.get('valor')} ({mf.get('pct')}% dos concursos)."
                if mf else "—"
            ),
            "geracao",
            "Análises Inteligentes · aba 4 (Padrões II) e aba Panorama",
        ),
    ]

    outros = []
    meses = [int(s["mes_num"]) for s in sorteios if s.get("mes_num")]
    if meses:
        mes_c = Counter(meses)
        mes_moda, mes_q = _moda(mes_c)
        outros.append(_item(
            "Mês da Sorte",
            "",
            f"Mês mais frequente no histórico: {mes_moda} ({_pct(mes_q, len(meses))}% dos concursos com mês).",
            "geracao",
            "Comportamento → Apostas (MS)",
        ))
    temporal = analise.get("temporal") or {}
    outros.append(_item(
        "Periodicidade (lags 1–6)",
        "",
        (
            "Há desvio pontual de periodicidade no histórico — não trate como ciclo rígido."
            if temporal.get("confirmado")
            else "Repetir o mesmo evento a cada 2, 3 ou 4 concursos não se confirma no histórico."
        ),
        "info",
        "Resumo Geral · DNA temporal",
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
    }
