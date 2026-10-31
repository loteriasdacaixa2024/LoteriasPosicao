# -*- coding: utf-8 -*-
"""Leitura integrada do Engine Final — Dia de Sorte.

Consulta análises já calculadas e devolve só os critérios que entraram
na decisão. Um critério sem dado não aparece na lista.
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

    criterios: List[Dict[str, str]] = []

    def add(cid: str, nome: str, papel: str, texto: str) -> None:
        criterios.append({"id": cid, "nome": nome, "papel": papel, "leitura": texto})

    n_pend = len(pendentes)
    add(
        "ciclo", "Ciclo", "forma",
        f"ciclo {ciclo.get('numero_ciclo') or '—'} · {n_pend} pendentes",
    )
    add(
        "pares", "Pares", "forma",
        f"mais frequente no histórico: {historico.get('pares')} pares / {historico.get('impares')} ímpares ({historico.get('pares_pct')}%)",
    )
    add(
        "impares", "Ímpares", "forma",
        f"acompanha os pares · {historico.get('impares')} ímpares",
    )
    add(
        "repetidas", "Repetidas", "forma",
        f"mais frequente: {historico.get('repetidas')} ({historico.get('repetidas_pct')}%)",
    )
    add(
        "sequencias", "Sequências", "forma",
        f"mais frequente: {historico.get('sequencias')} grupo(s) ({historico.get('sequencias_pct')}%)",
    )
    add(
        "finais", "Finais iguais", "forma",
        f"mais frequente: {historico.get('finais')} grupo(s) ({historico.get('finais_pct')}%)",
    )
    if soma_faixa:
        add(
            "soma", "Soma das dezenas", "forma",
            f"valor mais frequente {historico.get('soma')} · faixa {soma_faixa[0]}–{soma_faixa[1]}",
        )
    add(
        "linhas", "Linhas", "forma",
        f"assinatura mais frequente: {linha_moda or '—'}",
    )
    if diag:
        add(
            "diagonal", "Diagonal", "forma",
            f"em {diag.get('janela_pct')}% dos concursos · o lote acompanha essa presença no volante",
        )
    if ranking_padroes:
        amostra = ", ".join(r["padrao"] for r in ranking_padroes[:3])
        add(
            "padrao_inicial", "Padrão inicial", "forma",
            f"na ordem do histórico ({amostra}, …). "
            f"5 apostas usam os 5 primeiros, 10 os 10, 20 os 20",
        )
    if freq_fim:
        add("padrao_final", "Padrão final", "forma", "o final mais repetido no histórico")
    if moda_dig.get("valor") is not None:
        add(
            "digitos", "Dígitos utilizados", "forma",
            f"mais frequente: {moda_dig.get('valor')} dígitos distintos ({moda_dig.get('pct')}%)",
        )
    if dig_faixa:
        add(
            "soma_digitos", "Soma dos dígitos", "forma",
            f"mais frequente: {historico.get('soma_digitos')} · faixa {dig_faixa[0]}–{dig_faixa[1]}",
        )
    if gaps_top:
        add("gaps", "Gaps", "forma", "saltos entre as dezenas ordenadas")
    if sniper:
        add("sniper", "Sniper", "voto", f"{len(sniper)} dezenas fortes no mapa")
    if posicao:
        add("posicao", "Posição", "voto", "dezena mais frequente em cada ordem oficial")
    if pool_conc:
        add("concentracao", "Concentração", "voto", f"pool de {len(pool_conc)} dezenas por frequência")
    if dados:
        add(
            "modelos", "Central de Modelos", "voto",
            "núcleo de frequência, atraso e equilíbrio 01–15 / 16–31",
        )

    return {
        "sucesso": True,
        "concurso_referencia": ultimo.get("concurso"),
        "ultimo_numeros": ultimo_nums,
        "pendentes": pendentes,
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
        "usar_modelos": bool(dados),
        "scores": scores,
        "criterios": criterios,
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
    if pares is not None and int(forma["pares"]) != int(pares):
        return False
    if digitos is not None and int(forma["digitos"]) != int(digitos):
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


def _ajustar_paridade(nums: Sequence[int], universo: Sequence[int], pares_alvo: int) -> List[int]:
    atual = list(nums)
    for _ in range(8):
        pares = sum(1 for n in atual if n % 2 == 0)
        if pares == int(pares_alvo):
            return sorted(atual)
        quer_par = pares < int(pares_alvo)
        mudou = False
        usados = set(atual)
        for i, n in enumerate(atual):
            if (n % 2 == 0) == quer_par:
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
) -> List[int]:
    atual = list(nums)
    for _ in range(16):
        qtd = len(_digitos(atual))
        pares = sum(1 for n in atual if n % 2 == 0)
        if qtd == int(alvo) and pares == int(pares_alvo):
            return sorted(atual)
        mudou = False
        for i, n in enumerate(list(atual)):
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
) -> Optional[List[int]]:
    digs = [int(x) for x in str(padrao).replace(",", " ").split() if str(x).strip().isdigit()]
    if len(digs) != k:
        return None
    need = Counter(digs)
    universo = _universo_cfg(cfg, candidatos)
    nums: List[int] = []
    for dig, qtd in sorted(need.items()):
        pool = [n for n in universo if n // 10 == dig]
        if len(pool) < qtd:
            return None
        pool.sort(key=lambda n: (-float(busca.get(n) or 0), n))
        giro = int(idx) % len(pool)
        girado = pool[giro:] + pool[:giro]
        nums.extend(girado[:qtd])
    nums = _ajustar_paridade(nums, universo, int(pares_alvo))
    if sum(1 for n in nums if n % 2 == 0) != int(pares_alvo):
        return None
    esperado = " ".join(str(d) for d in digs)
    if padrao_inicial(sorted(nums)) != esperado:
        return None
    if digitos_alvo is not None:
        nums = _ajustar_digitos_mesmo_grupo(nums, universo, int(digitos_alvo), int(pares_alvo))
        if sum(1 for n in nums if n % 2 == 0) != int(pares_alvo):
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
    if not ranking or hist.get("pares") is None:
        return []
    if k != int(leitura.get("k_historico") or k):
        return []
    pares_alvo = int(hist["pares"])
    digitos_alvo = hist.get("digitos")
    pct_diag = float(leitura.get("diag_pct") or 0)
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
    busca = dict(scores)
    for n in leitura.get("ultimo_numeros") or []:
        if int(n) in busca:
            busca[int(n)] = float(busca[int(n)]) - float(cfg.get("sorteadas") or 7) * 0.8

    por_padrao = _lote_pelos_padroes(busca, leitura, scores, cfg, k, qtd, candidatos)
    if len(por_padrao) >= qtd:
        return por_padrao[:qtd]

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
    perfil_do_historico = pares_alvo is not None and k == int(leitura.get("k_historico") or k)
    if perfil_do_historico:
        for i in range(max(30, int(qtd) * 4)):
            montada = _montar_moda(
                busca, cfg, k, int(pares_alvo),
                int(digitos_alvo) if digitos_alvo is not None else None,
                i, candidatos,
            )
            if montada:
                _guardar(montada)

    segmentos = list(leitura.get("top_diags") or [])
    if perfil_do_historico:
        for i, seg in enumerate(segmentos[:12]):
            montada = _montar_moda(
                busca, cfg, k, int(pares_alvo),
                int(digitos_alvo) if digitos_alvo is not None else None,
                i + 3, candidatos, locked=seg.get("nums") or [],
            )
            if montada:
                _guardar(montada)
    for i, seg in enumerate(segmentos):
        plantada = _plantar_diagonal(
            seg.get("nums") or [], busca, cfg, k, candidatos, i,
        )
        if plantada:
            _guardar(plantada)
        if len(segmentos) > 8 and i >= 20:
            break

    ranqueados.sort(key=lambda x: -x[0])

    escolhidas: List[List[int]] = []
    assinaturas: List[str] = []
    pct_diag = float(leitura.get("diag_pct") or 0)
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
    return escolhidas


def aplicar_forma(apostas: Sequence[Dict[str, Any]], ultimo: Sequence[int]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for ap in apostas or []:
        item = dict(ap)
        dz = item.get("dezenas") or []
        if dz:
            item["forma"] = resumir_forma(dz, ultimo)
        out.append(item)
    return out
