# -*- coding: utf-8 -*-
"""
Análise da coluna Sequência (aba Panorama), calculada sobre as linhas
já produzidas por montar_sequencias_sorteadas.

A faixa baixa/média/alta do número da sequência reutiliza
`_faixa_limites`: até 31 jogos, 1–10 / 11–20 / 21–N; acima disso,
três terços do universo de jogos do padrão.
"""
from __future__ import annotations

import statistics
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from geradores_elite.otimizador.restricoes import _faixa_limites

_FAIXAS = ("baixa", "media", "alta")
_FONTE = {"baixa": "baixas", "media": "medias", "alta": "altas"}
_ROTULO = {"baixa": "Baixa", "media": "Média", "alta": "Alta"}
_ROTULO_MAIUSC = {"baixa": "BAIXA", "media": "MÉDIA", "alta": "ALTA"}
_NOME = {"baixa": "baixa", "media": "média", "alta": "alta"}


def _norm_padrao(padrao: str) -> str:
    digs = [x for x in str(padrao or "").replace(",", " ").split() if x.strip().isdigit()]
    return " ".join(digs)


def _pct(n: int, total: int, nd: int = 1) -> float:
    if not total:
        return 0.0
    return round(100.0 * float(n) / float(total), nd)


def _fmt_int(n: int) -> str:
    return f"{int(n):,}".replace(",", ".")


def _fmt_pct(p: float, nd: int = 1) -> str:
    q = round(float(p), nd)
    txt = f"{q:.{nd}f}".replace(".", ",")
    return txt + "%"


def _fmt_dec(p: float, nd: int = 1) -> str:
    return f"{round(float(p), nd):.{nd}f}".replace(".", ",")


def _occ(n: int) -> str:
    return f"{_fmt_int(n)} ocorrência" if int(n) == 1 else f"{_fmt_int(n)} ocorrências"


def _juntar(nomes: Sequence[str]) -> str:
    itens = [str(x) for x in nomes if str(x)]
    if not itens:
        return ""
    if len(itens) == 1:
        return itens[0]
    if len(itens) == 2:
        return f"{itens[0]} e {itens[1]}"
    return ", ".join(itens[:-1]) + f" e {itens[-1]}"


def _seq_label(nums: Sequence[int], *, limite: int = 5) -> str:
    orden = [int(n) for n in nums]
    if len(orden) <= limite:
        return _juntar([f"sequência {n}" for n in orden])
    vis = orden[:limite]
    resto = len(orden) - limite
    return _juntar([f"sequência {n}" for n in vis]) + f" e outras {resto}"


def classificar_faixa_sequencia(sequencia: Any, universo: Any) -> str:
    """Faixa do nº da sequência dentro dos jogos possíveis do padrão."""
    try:
        n = int(sequencia)
        u = int(universo)
    except (TypeError, ValueError):
        return ""
    if n < 1 or u < 1:
        return ""
    limites = _faixa_limites(u)
    for chave in _FAIXAS:
        lo, hi = limites[_FONTE[chave]]
        if int(lo) <= n <= int(hi):
            return chave
    if n > int(limites["medias"][1]):
        return "alta"
    if n > int(limites["baixas"][1]):
        return "media"
    return "baixa"


def limites_faixa(universo: Any) -> Dict[str, List[int]]:
    try:
        u = int(universo)
    except (TypeError, ValueError):
        u = 0
    if u < 1:
        return {k: [0, 0] for k in _FAIXAS}
    raw = _faixa_limites(u)
    return {
        chave: [int(raw[_FONTE[chave]][0]), int(raw[_FONTE[chave]][1])]
        for chave in _FAIXAS
    }


def _txt_limites(universo: int) -> str:
    if int(universo) < 1:
        return ""
    partes = []
    for chave in _FAIXAS:
        lo, hi = limites_faixa(universo)[chave]
        if hi < lo:
            continue
        partes.append(f"{_ROTULO[chave]} {lo}–{hi}")
    return " · ".join(partes)


def _contagem_faixa(contador: Counter) -> Dict[str, int]:
    return {k: int(contador.get(k, 0)) for k in _FAIXAS}


def _equilibrada_pct(pcts: Sequence[float]) -> bool:
    if len(pcts) < 3:
        return False
    if min(pcts) < 20.0:
        return False
    return (max(pcts) - min(pcts)) <= 15.0


def avaliar_predominancia(contagens: Dict[str, int]) -> Dict[str, Any]:
    """Líder com pelo menos 40% e 10 p.p. à frente da segunda."""
    total = int(sum(int(contagens.get(k, 0) or 0) for k in _FAIXAS))
    pcts = {k: _pct(int(contagens.get(k, 0) or 0), total, 1) for k in _FAIXAS}
    ranking = sorted(_FAIXAS, key=lambda k: (-int(contagens.get(k, 0) or 0), k))
    lider = ranking[0]
    segunda = ranking[1]
    c_lider = int(contagens.get(lider, 0) or 0)
    c_segunda = int(contagens.get(segunda, 0) or 0)
    gap = round(pcts[lider] - pcts[segunda], 1)
    significativa = total > 0 and c_lider > c_segunda and pcts[lider] >= 40.0 and gap >= 10.0
    equilibrada = total > 0 and (not significativa) and _equilibrada_pct([pcts[k] for k in _FAIXAS])
    if significativa:
        rotulo = _ROTULO_MAIUSC[lider]
        faixa = lider
    else:
        rotulo = "Não existe predominância significativa."
        faixa = None
    return {
        "faixa": faixa,
        "significativa": significativa,
        "equilibrada": equilibrada,
        "rotulo": rotulo,
        "percentual_lider": pcts[lider] if total else 0.0,
        "vantagem_pp": gap if total else 0.0,
    }


def _bloco_faixas(contador: Counter) -> Dict[str, Any]:
    total = int(sum(contador.get(k, 0) for k in _FAIXAS))
    bruto = _contagem_faixa(contador)
    out: Dict[str, Any] = {}
    for chave in _FAIXAS:
        out[chave] = {
            "rotulo": _ROTULO[chave],
            "ocorrencias": bruto[chave],
            "percentual": _pct(bruto[chave], total, 1),
        }
    pred = avaliar_predominancia(bruto)
    out["predominancia"] = pred
    out["equilibrada"] = bool(pred["equilibrada"])
    out["classificadas"] = total
    return out


def _frase_faixa_global(bloco: Dict[str, Any]) -> str:
    pred = bloco.get("predominancia") or {}
    if pred.get("equilibrada"):
        return "As sequências apresentam distribuição equilibrada entre baixa, média e alta."
    if pred.get("significativa") and pred.get("faixa"):
        return f"No histórico, predominam sequências da faixa {_NOME[pred['faixa']]}."
    return "Não existe predominância significativa de faixa no histórico."


def _frase_faixa_padrao(padrao: str, bloco: Dict[str, Any]) -> str:
    pred = bloco.get("predominancia") or {}
    if pred.get("equilibrada"):
        return f"No padrão {padrao}, as sequências apresentam distribuição equilibrada entre baixa, média e alta."
    if pred.get("significativa") and pred.get("faixa"):
        return f"No padrão {padrao}, predominam sequências da faixa {_NOME[pred['faixa']]}."
    return f"No padrão {padrao}, não existe predominância significativa de faixa."


def _nivel_repeticao(taxa: float) -> str:
    if taxa < 25.0:
        return "baixa"
    if taxa < 50.0:
        return "moderada"
    return "alta"


def _frase_repeticao_historica(taxa: float, diferentes: int) -> Dict[str, Any]:
    if diferentes <= 0:
        return {"nivel": "sem_amostra", "frase": "Ainda não há sequências no histórico."}
    nivel = _nivel_repeticao(taxa)
    pct = _fmt_pct(taxa, 1)
    if nivel == "baixa":
        frase = f"As sequências se repetem pouco: a taxa de repetição é {pct}."
    elif nivel == "moderada":
        frase = f"A repetição de sequências é moderada: a taxa de repetição é {pct}."
    else:
        frase = f"As sequências se repetem com frequência: a taxa de repetição é {pct}."
    return {"nivel": nivel, "frase": frase}


def _frase_entre_padroes(repetidas: int, em_varios: int) -> Dict[str, Any]:
    if repetidas <= 0:
        return {
            "nivel": "sem_amostra",
            "percentual": None,
            "frase": "Não há sequências repetidas para medir a diversidade entre padrões.",
        }
    pct = _pct(em_varios, repetidas, 1)
    nivel = _nivel_repeticao(pct)
    adjetivo = {"baixa": "baixa", "moderada": "moderada", "alta": "alta"}[nivel]
    frase = (
        f"A repetição de sequências entre padrões é {adjetivo} "
        f"({_fmt_pct(pct, 1)} das sequências repetidas aparecem em mais de um padrão)."
    )
    return {"nivel": nivel, "percentual": pct, "frase": frase}


def _faixa_modal(contador: Counter) -> Tuple[str, str, bool]:
    """Faixa mais frequente. Empate não escolhe um lado."""
    bruto = _contagem_faixa(contador)
    total = sum(bruto.values())
    if total <= 0:
        return "", "Sem predominância", False
    lider_c = max(bruto.values())
    lideres = [k for k in _FAIXAS if bruto[k] == lider_c]
    if len(lideres) != 1:
        return "", "Sem predominância", True
    chave = lideres[0]
    return chave, _ROTULO[chave], False


def _grupos_frequencia(seqs_ord: Sequence[Tuple[int, int]]) -> List[Tuple[int, List[int]]]:
    grupos: List[Tuple[int, List[int]]] = []
    i = 0
    n = len(seqs_ord)
    while i < n:
        qtd = int(seqs_ord[i][1])
        seqs: List[int] = []
        while i < n and int(seqs_ord[i][1]) == qtd:
            seqs.append(int(seqs_ord[i][0]))
            i += 1
        grupos.append((qtd, seqs))
    return grupos


def _top_sem_cortar_empate(
    grupos: Sequence[Tuple[int, List[int]]],
    jogos: int,
    ocorrencias_padrao: int,
    limite: int = 3,
) -> List[Dict[str, Any]]:
    """Não corta um empate para fabricar um top 3."""
    top: List[Dict[str, Any]] = []
    for qtd, seqs in grupos:
        if len(top) >= limite:
            break
        if len(top) + len(seqs) > limite:
            break
        for seq_n in seqs:
            faixa = classificar_faixa_sequencia(seq_n, jogos)
            top.append({
                "posicao": len(top) + 1,
                "sequencia": int(seq_n),
                "ocorrencias": int(qtd),
                "percentual": _pct(int(qtd), ocorrencias_padrao, 1),
                "faixa": faixa,
                "faixa_rotulo": _ROTULO.get(faixa, "Sem predominância"),
            })
    return top


def _destaque_padrao(grupos: Sequence[Tuple[int, List[int]]], ocorrencias_padrao: int) -> Dict[str, Any]:
    if not grupos or ocorrencias_padrao <= 0:
        return {"forte": False, "sequencia": None, "frase": ""}
    qtd, seqs = grupos[0]
    if len(seqs) != 1:
        return {"forte": False, "sequencia": int(seqs[0]), "frase": ""}
    occ = int(qtd)
    segunda_occ = int(grupos[1][0]) if len(grupos) > 1 else 0
    pct = _pct(occ, ocorrencias_padrao, 1)
    forte = occ >= (2 * segunda_occ) or pct >= 25.0
    if not forte:
        return {"forte": False, "sequencia": int(seqs[0]), "frase": ""}
    primeiro = {"sequencia": int(seqs[0]), "ocorrencias": occ}
    return {
        "forte": True,
        "sequencia": int(primeiro["sequencia"]),
        "frase": (
            f"A sequência {primeiro['sequencia']} se destaca neste padrão: "
            f"{_occ(occ)} ({_fmt_pct(pct, 1)} do padrão)."
        ),
    }


def _conclusoes_padrao(
    bloco: Dict[str, Any],
    destaque: Dict[str, Any],
    *,
    top3_share: float,
    taxa_repeticao_padrao: float,
    ocorrencias: int,
) -> List[str]:
    frases: List[str] = []
    pred = bloco.get("predominancia") or {}
    if pred.get("equilibrada"):
        frases.append("As sequências apresentam distribuição equilibrada entre baixa, média e alta.")
    elif pred.get("significativa") and pred.get("faixa"):
        frases.append(
            f"As sequências deste padrão estão concentradas na faixa {_NOME[pred['faixa']]}."
        )
    else:
        frases.append("Não existe predominância significativa de faixa neste padrão.")
    if destaque.get("forte") and destaque.get("frase"):
        frases.append(str(destaque["frase"]))
    elif top3_share >= 50.0 and ocorrencias >= 4:
        frases.append(
            "Existe forte concentração de determinadas sequências dentro deste padrão "
            f"(o top 3 soma {_fmt_pct(top3_share, 1)})."
        )
    if taxa_repeticao_padrao < 25.0:
        frases.append("As sequências apresentam baixa repetição histórica neste padrão.")
    return frases


def _conclusoes_com_empate(frases: List[str], empate_topo: Optional[Dict[str, Any]]) -> List[str]:
    if not empate_topo:
        return frases
    aviso = (
        "Não há sequência mais frequente neste padrão: "
        f"{_fmt_int(int(empate_topo['quantidade']))} sequências apareceram "
        f"{_occ(int(empate_topo['ocorrencias']))} cada."
    )
    return [aviso] + list(frases)


def agregar_sequencias(linhas: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Agrega frequência, repetição, padrões e faixa a partir das linhas prontas."""
    por_seq: Dict[int, Dict[str, Any]] = {}
    por_padrao: Dict[str, Dict[str, Any]] = {}
    faixa_global: Counter = Counter()
    ignoradas = 0

    for row in linhas or []:
        if not isinstance(row, dict):
            ignoradas += 1
            continue
        try:
            seq = int(row.get("sequencia_n"))
        except (TypeError, ValueError):
            ignoradas += 1
            continue
        if seq < 1:
            ignoradas += 1
            continue
        pad = _norm_padrao(str(row.get("padrao") or ""))
        if not pad:
            ignoradas += 1
            continue
        try:
            jogos = int(row.get("jogos_possiveis") or 0)
        except (TypeError, ValueError):
            jogos = 0
        faixa = classificar_faixa_sequencia(seq, jogos)
        desc = str(row.get("descricao") or "").strip()

        acc = por_seq.get(seq)
        if acc is None:
            acc = {"ocorrencias": 0, "padroes": Counter(), "faixas": Counter()}
            por_seq[seq] = acc
        acc["ocorrencias"] += 1
        acc["padroes"][pad] += 1
        if faixa:
            acc["faixas"][faixa] += 1
            faixa_global[faixa] += 1

        gp = por_padrao.get(pad)
        if gp is None:
            gp = {
                "ocorrencias": 0,
                "jogos_possiveis": jogos,
                "descricao": desc,
                "seqs": Counter(),
                "faixas": Counter(),
            }
            por_padrao[pad] = gp
        gp["ocorrencias"] += 1
        if jogos > int(gp.get("jogos_possiveis") or 0):
            gp["jogos_possiveis"] = jogos
        if desc and not gp.get("descricao"):
            gp["descricao"] = desc
        gp["seqs"][seq] += 1
        if faixa:
            gp["faixas"][faixa] += 1

    total = int(sum(int(a["ocorrencias"]) for a in por_seq.values()))
    diferentes = len(por_seq)
    ocorrencias_lista = [int(a["ocorrencias"]) for a in por_seq.values()]
    unicas = sum(1 for n in ocorrencias_lista if n == 1)
    repetidas = sum(1 for n in ocorrencias_lista if n >= 2)
    taxa_rep = _pct(repetidas, diferentes, 1) if diferentes else 0.0
    media_occ = round(float(total) / float(diferentes), 2) if diferentes else 0.0

    if len(ocorrencias_lista) > 1:
        desvio = float(statistics.pstdev(ocorrencias_lista))
    else:
        desvio = 0.0
    limiar = (statistics.mean(ocorrencias_lista) if ocorrencias_lista else 0.0) + (2.0 * desvio)

    ranking: List[Dict[str, Any]] = []
    for seq, acc in por_seq.items():
        faixa_key, faixa_rotulo, empate = _faixa_modal(acc["faixas"])
        ranking.append({
            "sequencia": int(seq),
            "ocorrencias": int(acc["ocorrencias"]),
            "percentual": _pct(int(acc["ocorrencias"]), total, 2),
            "padroes_diferentes": len(acc["padroes"]),
            "padroes": sorted(acc["padroes"].keys()),
            "faixa": faixa_key,
            "faixa_rotulo": faixa_rotulo,
            "faixa_empate": empate,
        })
    ranking.sort(key=lambda r: (-int(r["ocorrencias"]), int(r["sequencia"])))

    def _card_freq(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not rows:
            return []
        topo = int(rows[0]["ocorrencias"])
        return [
            {"sequencia": int(r["sequencia"]), "ocorrencias": int(r["ocorrencias"]), "percentual": r["percentual"]}
            for r in rows if int(r["ocorrencias"]) == topo
        ]

    mais = _card_freq(ranking)
    if ranking:
        piso = min(int(r["ocorrencias"]) for r in ranking)
        menos_rows = [r for r in ranking if int(r["ocorrencias"]) == piso]
    else:
        piso = 0
        menos_rows = []

    extremas = [
        {"sequencia": int(r["sequencia"]), "ocorrencias": int(r["ocorrencias"]), "percentual": r["percentual"]}
        for r in ranking
        if int(r["ocorrencias"]) > limiar and int(r["ocorrencias"]) >= 3
    ]

    em_multiplos = sum(1 for r in ranking if int(r["padroes_diferentes"]) >= 2)
    concentradas = sum(1 for r in ranking if int(r["ocorrencias"]) >= 2 and int(r["padroes_diferentes"]) == 1)
    distribuidas = sum(1 for r in ranking if int(r["padroes_diferentes"]) >= 3)
    maior_qtd = max((int(r["padroes_diferentes"]) for r in ranking), default=0)
    maior_div = sorted(int(r["sequencia"]) for r in ranking if int(r["padroes_diferentes"]) == maior_qtd and maior_qtd > 0)
    repetidas_em_varios = sum(
        1 for r in ranking if int(r["ocorrencias"]) >= 2 and int(r["padroes_diferentes"]) >= 2
    )

    bloco_global = _bloco_faixas(faixa_global)

    padroes_ord = sorted(
        por_padrao.items(),
        key=lambda kv: (-int(kv[1]["ocorrencias"]), -int(kv[1]["jogos_possiveis"] or 0), kv[0]),
    )
    top_padroes: List[Dict[str, Any]] = []
    for pos, (pad, gp) in enumerate(padroes_ord[:5], start=1):
        occ_p = int(gp["ocorrencias"])
        seqs_ord = sorted(gp["seqs"].items(), key=lambda kv: (-int(kv[1]), int(kv[0])))
        grupos = _grupos_frequencia(seqs_ord)
        top3 = _top_sem_cortar_empate(grupos, int(gp["jogos_possiveis"] or 0), occ_p)
        empate_topo = None
        if grupos and len(grupos[0][1]) > 3:
            empate_topo = {
                "ocorrencias": int(grupos[0][0]),
                "quantidade": len(grupos[0][1]),
            }
        bloco_p = _bloco_faixas(gp["faixas"])
        destaque = _destaque_padrao(grupos, occ_p)
        share3 = _pct(sum(int(t["ocorrencias"]) for t in top3), occ_p, 1)
        seqs_rep = sum(1 for _s, q in gp["seqs"].items() if int(q) >= 2)
        taxa_p = _pct(seqs_rep, len(gp["seqs"]), 1) if gp["seqs"] else 0.0
        top_padroes.append({
            "posicao": pos,
            "padrao": pad,
            "descricao": gp.get("descricao") or "",
            "ocorrencias": occ_p,
            "percentual_historico": _pct(occ_p, total, 2),
            "jogos_possiveis": int(gp["jogos_possiveis"] or 0),
            "faixa_limites_txt": _txt_limites(int(gp["jogos_possiveis"] or 0)),
            "faixas": bloco_p,
            "top3": top3,
            "empate_topo": empate_topo,
            "destaque": destaque,
            "conclusoes": _conclusoes_com_empate(
                _conclusoes_padrao(
                    bloco_p,
                    destaque,
                    top3_share=share3,
                    taxa_repeticao_padrao=taxa_p,
                    ocorrencias=occ_p,
                ),
                empate_topo,
            ),
        })

    rep_hist = _frase_repeticao_historica(taxa_rep, diferentes)
    rep_entre = _frase_entre_padroes(repetidas, repetidas_em_varios)
    repeticoes_no_mesmo_padrao = sum(
        1
        for gp in por_padrao.values()
        for q in gp["seqs"].values()
        if int(q) >= 2
    )
    aviso = _aviso_apostas(
        taxa_rep=taxa_rep,
        diferentes=diferentes,
        unicas=unicas,
        repetidas=repetidas,
        concentradas=concentradas,
        em_multiplos=em_multiplos,
        repeticoes_no_mesmo_padrao=repeticoes_no_mesmo_padrao,
        rep_entre=rep_entre,
        bloco_global=bloco_global,
        top_padroes=top_padroes,
    )
    insights = _montar_insights(
        total=total,
        diferentes=diferentes,
        unicas=unicas,
        media_occ=media_occ,
        mais=mais,
        piso=piso,
        menos_qtd=len(menos_rows),
        menos_seqs=[int(r["sequencia"]) for r in sorted(menos_rows, key=lambda r: int(r["sequencia"]))],
        extremas=extremas,
        limiar=limiar,
        em_multiplos=em_multiplos,
        maior_qtd=maior_qtd,
        maior_div=maior_div,
        concentradas=concentradas,
        distribuidas=distribuidas,
        rep_hist=rep_hist,
        rep_entre=rep_entre,
        bloco_global=bloco_global,
        top_padroes=top_padroes,
        ranking=ranking,
    )
    apoio = _apoio_escolha(top_padroes)

    return {
        "sucesso": True,
        "total_ocorrencias": total,
        "linhas_ignoradas": ignoradas,
        "indicadores": {
            "sequencias_diferentes": diferentes,
            "sequencias_unicas": unicas,
            "sequencias_repetidas": repetidas,
            "taxa_repeticao": taxa_rep,
            "media_ocorrencias": media_occ,
            "mais_frequentes": mais,
            "menos_frequente_ocorrencias": piso,
            "menos_frequente_quantidade": len(menos_rows),
            "menos_frequentes": [int(r["sequencia"]) for r in sorted(menos_rows, key=lambda r: int(r["sequencia"]))][:8],
            "extremamente_recorrentes": extremas,
            "limiar_recorrencia": round(float(limiar), 2),
            "em_multiplos_padroes": em_multiplos,
            "maior_qtd_padroes": maior_qtd,
            "maior_diversidade": maior_div,
            "concentradas_um_padrao": concentradas,
            "distribuidas_tres_ou_mais": distribuidas,
            "repeticao_historica": rep_hist,
            "repeticao_entre_padroes": rep_entre,
        },
        "faixas": bloco_global,
        "insights": insights,
        "aviso_apostas": aviso,
        "apoio_escolha": apoio,
        "top_padroes": top_padroes,
        "ranking": ranking,
        "criterios": {
            "faixa": (
                "Mesma divisão de _faixa_limites: até 31 jogos, 1–10 / 11–20 / 21–N; "
                "acima disso, três terços dos jogos possíveis do padrão."
            ),
            "predominancia": "Faixa líder com pelo menos 40% e 10 pontos percentuais à frente da segunda.",
            "destaque": "A primeira sequência tem pelo menos o dobro da segunda, ou pelo menos 25% do padrão.",
            "recorrencia_extrema": "Ocorrências estritamente acima da média mais dois desvios, e no mínimo 3.",
            "repeticao_entre_padroes": (
                "Entre as sequências com 2 ou mais ocorrências, a parcela que aparece em mais de um padrão: "
                "baixa abaixo de 25%, alta a partir de 50%, moderada no intervalo."
            ),
        },
    }


def _montar_insights(
    *,
    total: int,
    diferentes: int,
    unicas: int,
    media_occ: float,
    mais: Sequence[Dict[str, Any]],
    piso: int,
    menos_qtd: int,
    menos_seqs: Sequence[int],
    extremas: Sequence[Dict[str, Any]],
    limiar: float,
    em_multiplos: int,
    maior_qtd: int,
    maior_div: Sequence[int],
    concentradas: int,
    distribuidas: int,
    rep_hist: Dict[str, Any],
    rep_entre: Dict[str, Any],
    bloco_global: Dict[str, Any],
    top_padroes: Sequence[Dict[str, Any]],
    ranking: Sequence[Dict[str, Any]],
) -> List[str]:
    if total <= 0 or diferentes <= 0:
        return ["Ainda não há sequências calculadas no histórico."]

    frases: List[str] = []
    frases.append(f"Há {_fmt_int(diferentes)} sequências diferentes em {_fmt_int(total)} sorteios com sequência.")
    frases.append(f"A média é de {_fmt_dec(media_occ, 2)} ocorrências por sequência.")

    if len(mais) == 1:
        m = mais[0]
        frases.append(
            f"A sequência {m['sequencia']} é a mais frequente do histórico "
            f"({_occ(int(m['ocorrencias']))}, {_fmt_pct(float(m['percentual']), 2)})."
        )
    elif mais:
        nums = [int(m["sequencia"]) for m in mais]
        vis = _juntar(str(n) for n in nums[:5])
        extra = f", entre outras {len(nums) - 5}," if len(nums) > 5 else ""
        frases.append(
            f"As sequências {vis}{extra} empatam como as mais frequentes "
            f"({_occ(int(mais[0]['ocorrencias']))} cada)."
        )

    if menos_qtd <= 0:
        pass
    elif menos_qtd <= 3:
        frases.append(
            f"A menor frequência é {_occ(piso)}: {_seq_label(menos_seqs)}."
        )
    else:
        frases.append(
            f"A menor frequência é {_occ(piso)}, compartilhada por {_fmt_int(menos_qtd)} sequências."
        )

    if unicas:
        frases.append(f"{_fmt_int(unicas)} sequências aparecem apenas uma vez.")
    else:
        frases.append("Nenhuma sequência aparece apenas uma vez.")

    if rep_hist.get("frase"):
        frases.append(str(rep_hist["frase"]))

    if extremas:
        nomes = _juntar(
            f"sequência {e['sequencia']} ({_occ(int(e['ocorrencias']))})"
            for e in extremas[:5]
        )
        extra = f", entre outras {len(extremas) - 5}" if len(extremas) > 5 else ""
        qtd_ext = len(extremas)
        substantivo = "sequência extremamente recorrente" if qtd_ext == 1 else "sequências extremamente recorrentes"
        frases.append(
            f"Há {_fmt_int(qtd_ext)} {substantivo}, "
            f"acima de {_fmt_dec(limiar, 2)} ocorrências (média + 2 desvios, mínimo de 3): {nomes}{extra}."
        )
    else:
        frases.append(
            "Não há sequência extremamente recorrente "
            f"(acima de {_fmt_dec(limiar, 2)} ocorrências, média + 2 desvios, com pelo menos 3)."
        )

    if maior_qtd > 0 and maior_div:
        if len(maior_div) == 1:
            frases.append(
                f"A sequência {maior_div[0]} aparece associada a {_fmt_int(maior_qtd)} "
                f"{'padrão diferente' if maior_qtd == 1 else 'padrões diferentes'}."
            )
        else:
            vis = _juntar(str(n) for n in list(maior_div)[:5])
            extra = f", entre outras {len(maior_div) - 5}," if len(maior_div) > 5 else ""
            frases.append(
                f"As sequências {vis}{extra} apresentam a maior diversidade de padrões "
                f"({_fmt_int(maior_qtd)} padrões)."
            )
    if em_multiplos:
        frases.append(
            f"{_fmt_int(em_multiplos)} sequências aparecem em padrões diferentes. "
            "A mesma sequência não fica, nesses casos, exclusiva de um único padrão."
        )
    else:
        frases.append("Nenhuma sequência aparece em mais de um padrão.")
    if rep_entre.get("frase"):
        frases.append(str(rep_entre["frase"]))
    if concentradas:
        frases.append(
            f"{_fmt_int(concentradas)} sequências se repetem sempre no mesmo padrão."
        )
    if distribuidas:
        frases.append(
            f"{_fmt_int(distribuidas)} sequências estão distribuídas em 3 ou mais padrões."
        )

    frases.append(_frase_faixa_global(bloco_global))
    for p in top_padroes:
        frases.append(_frase_faixa_padrao(str(p["padrao"]), p.get("faixas") or {}))

    if mais and bloco_global.get("predominancia", {}).get("significativa"):
        seq_top = int(mais[0]["sequencia"])
        row = next((r for r in ranking if int(r["sequencia"]) == seq_top), None)
        faixa_seq = (row or {}).get("faixa") or ""
        faixa_g = bloco_global["predominancia"].get("faixa") or ""
        if faixa_seq and faixa_g and faixa_seq != faixa_g:
            frases.append(
                f"A sequência mais frequente ({seq_top}) predomina na faixa {_NOME[faixa_seq]}, "
                f"enquanto o histórico geral predomina na faixa {_NOME[faixa_g]}."
            )
    return frases


def _aviso_apostas(
    *,
    taxa_rep: float,
    diferentes: int,
    unicas: int,
    repetidas: int,
    concentradas: int,
    em_multiplos: int,
    repeticoes_no_mesmo_padrao: int,
    rep_entre: Dict[str, Any],
    bloco_global: Dict[str, Any],
    top_padroes: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """Texto curto para montar apostas, a partir dos indicadores já calculados."""
    if diferentes <= 0:
        return {"titulo": "Para criar apostas", "frases": []}
    frases: List[str] = []
    pct = _fmt_pct(taxa_rep, 1)
    if taxa_rep < 25.0:
        frases.append(
            f"Em cada aposta do mesmo padrão, use uma sequência diferente. "
            f"A taxa de repetição é {pct}: {_fmt_int(unicas)} de {_fmt_int(diferentes)} "
            f"sequências saíram uma única vez."
        )
    elif taxa_rep < 50.0:
        frases.append(
            f"A repetição de sequências é moderada ({pct}). "
            f"Varie o número da sequência entre as apostas do mesmo padrão."
        )
    else:
        frases.append(
            f"As sequências se repetem com frequência ({pct}). "
            f"O ranking mostra quais números voltam."
        )
    if repeticoes_no_mesmo_padrao <= 0:
        frases.append("Nenhuma sequência voltou dentro do mesmo padrão.")
    elif concentradas:
        frases.append(
            f"{_fmt_int(concentradas)} sequências se repetem sempre no mesmo padrão. "
            f"O ranking mostra quais são essas exceções."
        )
    tops_uma_vez = [
        p for p in top_padroes
        if int((p.get("empate_topo") or {}).get("ocorrencias") or 0) == 1
    ]
    if top_padroes and len(tops_uma_vez) == len(top_padroes):
        frases.append(
            f"Nos {len(top_padroes)} principais padrões, cada sequência sorteada saiu uma vez. "
            f"Não há número de sequência para reaproveitar dentro deles."
        )
    pred = bloco_global.get("predominancia") or {}
    if pred.get("equilibrada"):
        frases.append(
            "Não fixe a faixa. Baixa, média e alta estão equilibradas: "
            "espalhe as sequências entre as três."
        )
    elif pred.get("significativa") and pred.get("faixa"):
        frases.append(
            f"No histórico, a faixa {_NOME[pred['faixa']]} predomina. "
            f"Ela pode entrar como um critério, junto com uma sequência diferente em cada aposta."
        )
    else:
        frases.append(
            "Não há faixa predominante. Não concentre as apostas só em baixa, "
            "só em média ou só em alta."
        )
    if rep_entre.get("nivel") == "alta" and taxa_rep < 25.0 and repetidas:
        extra = ""
        if em_multiplos:
            extra = f", {_fmt_int(em_multiplos)} delas em mais de um padrão"
        frases.append(
            f"A repetição entre padrões ({_fmt_pct(float(rep_entre.get('percentual') or 0), 1)}) "
            f"vale só para as {_fmt_int(repetidas)} sequências que se repetiram{extra}. "
            f"Não é motivo para repetir a mesma sequência."
        )
    frases.append("Leitura do histórico, sem garantia de resultado futuro.")
    return {"titulo": "Para criar apostas", "frases": frases}


def _apoio_escolha(top_padroes: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    if not top_padroes:
        return {
            "padrao": "",
            "texto": "Ainda não há padrão frequente para esta leitura histórica.",
        }
    top = top_padroes[0]
    pred = (top.get("faixas") or {}).get("predominancia") or {}
    if pred.get("significativa"):
        faixa_txt = str(pred.get("rotulo") or "")
    else:
        faixa_txt = "Não existe predominância significativa."
    seqs = []
    for item in top.get("top3") or []:
        faixa = item.get("faixa_rotulo") or "sem faixa"
        seqs.append(
            f"sequência {item['sequencia']} ({_occ(int(item['ocorrencias']))}, {faixa})"
        )
    empate = top.get("empate_topo") or {}
    if seqs:
        assoc = f"Sequências mais associadas: {_juntar(seqs)}."
    elif empate:
        assoc = (
            f"Não há sequência mais frequente neste padrão: "
            f"{_fmt_int(int(empate.get('quantidade') or 0))} sequências apareceram "
            f"{_occ(int(empate.get('ocorrencias') or 0))} cada."
        )
    else:
        assoc = "Não há sequência mais frequente neste padrão."
    texto = (
        "Leitura histórica, sem garantia de resultado futuro. "
        f"O padrão mais frequente é {top['padrao']}"
        f" ({_occ(int(top['ocorrencias']))}"
        + (f", {top['descricao']}" if top.get("descricao") else "")
        + "). "
        f"Predominância de faixa nesse padrão: {faixa_txt.rstrip('.')}. "
        f"{assoc}"
    )
    return {
        "padrao": top["padrao"],
        "descricao": top.get("descricao") or "",
        "ocorrencias": int(top["ocorrencias"]),
        "faixa_rotulo": faixa_txt,
        "top_sequencias": list(top.get("top3") or []),
        "texto": texto,
    }
