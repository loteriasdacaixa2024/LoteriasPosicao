# -*- coding: utf-8 -*-
"""Gerador 2A1. Lê o Panorama e o ciclo e só então monta a aposta.

Não usa o motor de Estatísticas e Ciclo nem o modo Panorama já existente.
"""
from __future__ import annotations

import random
import statistics
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from analise_escolha_visual.enriquecimento.regras_2a1 import (
    faixa_repetidos,
    montar_restricoes,
    viola_restricoes,
)
try:
    from .gerador import _ajustar_seq_e_finais, _atrasos, _forma_seq_finais
except ImportError:
    from gerador import _ajustar_seq_e_finais, _atrasos, _forma_seq_finais

from analise_inteligentes_diadesorte.analise_sequencias import (
    classificar_faixa_sequencia,
    limites_faixa,
)
from analise_inteligentes_diadesorte.sequencias_sorteadas import (
    dezenas_na_sequencia,
    mapa_sequencia_no_padrao,
)
from analise_inteligentes_diadesorte.service import padrao_inicial
from analise_inteligentes_diadesorte.soma_media import calcular_faixa_soma, classificar_soma

_FAIXAS = ("baixa", "media", "alta")


def _diagonais_da_aposta(dezenas: Sequence[int], dmin: int, dmax: int) -> List[Dict[str, Any]]:
    try:
        from analise_inteligentes_diadesorte.diagonais_volante import diagonais_na_aposta
        return diagonais_na_aposta(dezenas, dmin=dmin, dmax=dmax) or []
    except Exception:
        return [{}]


def _n_digitos(nums: Sequence[int]) -> int:
    chars: Set[str] = set()
    for n in nums:
        chars.update(f"{int(n):02d}")
    return len(chars)


def _norm_padrao(padrao: str) -> str:
    digs = [x for x in str(padrao or "").replace(",", " ").split() if str(x).strip().isdigit()]
    return " ".join(digs)


def _ints(nums: Iterable[Any]) -> List[int]:
    out: List[int] = []
    for n in nums or []:
        try:
            v = int(n)
        except (TypeError, ValueError):
            continue
        out.append(v)
    return out


def _need(padrao: str) -> Counter:
    return Counter(int(x) for x in _norm_padrao(padrao).split() if x.isdigit())


def _padrao_cabe(padrao: str, pool: Sequence[int], k: int) -> bool:
    need = _need(padrao)
    if sum(need.values()) != int(k):
        return False
    have = Counter(int(n) // 10 for n in pool)
    return all(have[d] >= q for d, q in need.items())


def _contagens_faixa(linhas: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    por: Dict[str, Dict[str, Any]] = {}
    for row in linhas:
        pad = _norm_padrao(str(row.get("padrao") or ""))
        if not pad:
            continue
        try:
            seq = int(row.get("sequencia_n"))
            jogos = int(row.get("jogos_possiveis") or 0)
        except (TypeError, ValueError):
            continue
        if seq < 1:
            continue
        item = por.setdefault(pad, {"counts": Counter(), "ns": [], "media": None, "somas": []})
        faixa = classificar_faixa_sequencia(seq, jogos) or "media"
        item["counts"][faixa] += 1
        item["ns"].append(seq)
        if row.get("media") is not None and item["media"] is None:
            try:
                item["media"] = int(row.get("media"))
            except (TypeError, ValueError):
                pass
        try:
            item["somas"].append(int(row.get("soma") or 0))
        except (TypeError, ValueError):
            pass
    return por


def _escolher_faixa(counts: Counter, rng: random.Random) -> str:
    vivos = [(f, int(counts.get(f) or 0)) for f in _FAIXAS if int(counts.get(f) or 0) > 0]
    if not vivos:
        return "media"
    return rng.choices([f for f, _q in vivos], weights=[q for _f, q in vivos], k=1)[0]


def _ordem_na_faixa(
    universo: int,
    faixa: str,
    historico: Sequence[int],
    *,
    limite: int = 80,
) -> List[int]:
    limites = limites_faixa(universo)
    lo, hi = limites.get(faixa) or limites.get("media") or [1, max(1, int(universo))]
    lo, hi = int(lo), int(hi)
    if hi < lo:
        lo, hi = 1, max(1, int(universo))
    dentro = [int(n) for n in historico if lo <= int(n) <= hi]
    centro = int(statistics.median(dentro)) if dentro else (lo + hi) // 2
    centro = min(hi, max(lo, centro))
    ordem = [centro]
    dist = 1
    while len(ordem) < int(limite) and (centro - dist >= lo or centro + dist <= hi):
        if centro - dist >= lo:
            ordem.append(centro - dist)
        if len(ordem) >= int(limite):
            break
        if centro + dist <= hi:
            ordem.append(centro + dist)
        dist += 1
    return ordem


def _pool_permitido(
    restr: Dict[str, Any],
    pendentes: Sequence[int],
    *,
    dmin: int,
    dmax: int,
    k: int,
    rep_max: int,
) -> Tuple[Set[int], bool]:
    """Dezenas que não saíram no último concurso.

    Com repetição pedida, também entram as dezenas daquele concurso que a
    análise deixa repetir. Pendente do ciclo só entra se estiver nessa lista.
    """
    del pendentes, k
    ultimo = set(_ints(restr.get("ultimo")))
    disponiveis = set(_ints(restr.get("pares_disponiveis"))) | set(_ints(restr.get("impares_disponiveis")))
    if not disponiveis:
        disponiveis = {n for n in range(int(dmin), int(dmax) + 1) if n not in ultimo}
    allowed = {
        int(n) for n in disponiveis
        if int(n) not in ultimo and int(dmin) <= int(n) <= int(dmax)
    }
    if int(rep_max) > 0:
        for n in _ints(restr.get("pode_repetir")):
            if int(dmin) <= int(n) <= int(dmax):
                allowed.add(int(n))
    return allowed, False


def _encaixar_no_pool(
    dezenas: Sequence[int],
    allowed: Set[int],
    pendentes: Set[int],
    atrasos: Dict[int, int],
    dmin: int,
    dmax: int,
) -> Optional[List[int]]:
    """Mantém o padrão e troca o que saiu por dezena que não saiu.

    Na mesma casa, a pendente do ciclo vem na frente. Depois, a mais atrasada.
    """
    atual = [int(n) for n in dezenas]
    ocup = set(atual)

    def escolher(dec: int) -> Optional[int]:
        lo = max(int(dmin), dec * 10)
        hi = min(int(dmax), dec * 10 + 9)
        cand = [x for x in range(lo, hi + 1) if x not in ocup and x in allowed]
        if not cand:
            return None
        cand.sort(key=lambda x: (0 if x in pendentes else 1, -int(atrasos.get(x, 0)), x))
        return cand[0]

    for i, n in enumerate(list(atual)):
        if n in allowed:
            continue
        novo = escolher(n // 10)
        if novo is None:
            return None
        ocup.discard(n)
        ocup.add(novo)
        atual[i] = novo

    for p in sorted(pendentes):
        if p in ocup or p not in allowed:
            continue
        dec = p // 10
        for i, n in enumerate(atual):
            if n // 10 == dec and n not in pendentes:
                ocup.discard(n)
                ocup.add(p)
                atual[i] = p
                break
    return sorted(atual)


def _ajustar_repetidos(
    dezenas: Sequence[int],
    allowed: Set[int],
    ultimo: Set[int],
    pode: Set[int],
    rep_min: int,
    rep_max: int,
    pendentes: Set[int],
    atrasos: Dict[int, int],
    dmin: int,
    dmax: int,
    *,
    folga_zero: bool,
) -> Optional[List[int]]:
    """Leva a aposta à quantidade pedida, trocando só dentro da mesma casa."""
    atual = [int(n) for n in dezenas]
    if any(n not in allowed for n in atual):
        return None

    def nreps(nums: Sequence[int]) -> List[int]:
        return [n for n in nums if n in ultimo]

    if int(rep_max) <= 0:
        return None if nreps(atual) else sorted(atual)

    for _ in range(12):
        reps = nreps(atual)
        if int(rep_min) <= len(reps) <= int(rep_max):
            return sorted(atual)
        ocup = set(atual)
        if len(reps) > int(rep_max):
            extras = sorted(
                reps,
                key=lambda n: (0 if n in pendentes else 1, int(atrasos.get(n, 0)), n),
            )
            trocou = False
            for sai in extras:
                lo = max(int(dmin), (sai // 10) * 10)
                hi = min(int(dmax), (sai // 10) * 10 + 9)
                cand = [
                    x for x in range(lo, hi + 1)
                    if x not in ocup and x in allowed and x not in ultimo
                ]
                if not cand:
                    continue
                cand.sort(key=lambda x: (0 if x in pendentes else 1, -int(atrasos.get(x, 0)), x))
                novo = cand[0]
                atual = [novo if n == sai else n for n in atual]
                trocou = True
                break
            if not trocou:
                return None
            continue
        livres = sorted(
            [n for n in atual if n not in ultimo],
            key=lambda n: (0 if n not in pendentes else 1, int(atrasos.get(n, 0)), n),
        )
        trocou = False
        for sai in livres:
            lo = max(int(dmin), (sai // 10) * 10)
            hi = min(int(dmax), (sai // 10) * 10 + 9)
            cand = [x for x in range(lo, hi + 1) if x not in ocup and x in pode]
            if not cand:
                continue
            cand.sort(key=lambda x: (0 if x in pendentes else 1, -int(atrasos.get(x, 0)), x))
            novo = cand[0]
            atual = [novo if n == sai else n for n in atual]
            trocou = True
            break
        if not trocou:
            if folga_zero and not nreps(atual):
                return sorted(atual)
            return None
    return None


def _identidade_valida(
    dezenas: Sequence[int],
    faixa: Optional[Dict[str, Any]],
    *,
    dmin: int,
    dmax: int,
) -> Tuple[str, Optional[int]]:
    """O inverso do resultado real: a aposta pronta revela o padrão e a sequência válida."""
    dez = tuple(sorted(int(x) for x in dezenas))
    pad = padrao_inicial(list(dez))
    if not pad:
        return "", None
    mapa = mapa_sequencia_no_padrao(
        pad, [dez], faixa, min_dezena=int(dmin), max_dezena=int(dmax),
    )
    seq = mapa.get(dez)
    return pad, (int(seq) if seq else None)


def _padrao_aceita_obrigatorias(pad: str, obrigatorias: Sequence[int]) -> bool:
    if not obrigatorias:
        return True
    tem = Counter(str(pad).split())
    precisa = Counter(str(int(n) // 10) for n in obrigatorias)
    return all(tem[decada] >= qtd for decada, qtd in precisa.items())


def _escolher_padroes(
    catalogo: Sequence[Dict[str, Any]],
    pool: Set[int],
    k: int,
    qtd: int,
    rng: random.Random,
    obrigatorias: Sequence[int] = (),
    limite_distintos: Optional[int] = None,
) -> List[Dict[str, Any]]:
    ok = []
    for raw in catalogo:
        pad = _norm_padrao(str(raw.get("padrao") or ""))
        if not pad or not _padrao_cabe(pad, list(pool), k):
            continue
        if not _padrao_aceita_obrigatorias(pad, obrigatorias):
            continue
        item = dict(raw)
        item["padrao"] = pad
        item["frequencia"] = int(raw.get("frequencia") or 0)
        item["jogos_possiveis"] = int(raw.get("jogos_possiveis") or 0)
        if item["jogos_possiveis"] <= 0:
            continue
        ok.append(item)
    ocorridos = [p for p in ok if p["frequencia"] > 0]
    faltantes = [p for p in ok if p["frequencia"] <= 0]
    rng.shuffle(ocorridos)
    ocorridos.sort(key=lambda p: -int(p["frequencia"]))
    bolsa = list(ocorridos)
    escolhidos: List[Dict[str, Any]] = []
    teto = int(limite_distintos) if limite_distintos else int(qtd)
    alvo = max(1, min(teto, len(ok) or 1))
    while bolsa and len(escolhidos) < alvo:
        pesos = [max(1, int(p["frequencia"])) for p in bolsa]
        i = rng.choices(range(len(bolsa)), weights=pesos, k=1)[0]
        escolhidos.append(bolsa.pop(i))
    if faltantes:
        faltantes.sort(key=lambda p: (int(p["jogos_possiveis"]), p["padrao"]))
        if escolhidos:
            escolhidos[-1] = dict(faltantes[0])
        else:
            escolhidos.append(dict(faltantes[0]))
    if not escolhidos:
        return []
    if limite_distintos:
        return escolhidos
    lote: List[Dict[str, Any]] = []
    i = 0
    while len(lote) < int(qtd):
        lote.append(escolhidos[i % len(escolhidos)])
        i += 1
    return lote


_PESOS_POSTO = (3, 2, 2, 2, 1)


def cotas_relevancia(qtd: int, n_padroes: int) -> List[int]:
    """Maiores sobras com pesos 3, 2, 2, 2, 1. Dez apostas viram 3, 2, 2, 2, 1."""
    n = max(0, int(qtd))
    k = max(0, min(len(_PESOS_POSTO), int(n_padroes)))
    if n <= 0 or k <= 0:
        return []
    pesos = _PESOS_POSTO[:k]
    total = sum(pesos)
    numeradores = [n * p for p in pesos]
    cotas = [num // total for num in numeradores]
    resto = n - sum(cotas)
    sobras = [num % total for num in numeradores]
    for i in sorted(range(k), key=lambda ix: (-sobras[ix], ix)):
        if resto <= 0:
            break
        cotas[i] += 1
        resto -= 1
    return cotas


def fila_intercalada(cotas: Sequence[int]) -> List[int]:
    """Percorre os postos e só emite quem ainda tem cota."""
    rest = [max(0, int(c)) for c in cotas]
    ordem: List[int] = []
    while any(r > 0 for r in rest):
        for i, r in enumerate(rest):
            if r > 0:
                ordem.append(i)
                rest[i] -= 1
    return ordem


def _resolver_cinco(
    catalogo: Sequence[Dict[str, Any]],
    fonte: Sequence[Dict[str, Any]],
    pool: Set[int],
    k: int,
    obrigatorias: Sequence[int] = (),
) -> List[Dict[str, Any]]:
    """Mantém a ordem da análise. Padrão sem ocorrência não entra."""
    por: Dict[str, Dict[str, Any]] = {}
    for raw in catalogo:
        pad = _norm_padrao(str(raw.get("padrao") or ""))
        if pad and pad not in por:
            por[pad] = raw
    out: List[Dict[str, Any]] = []
    vistos: Set[str] = set()
    for card in fonte:
        if len(out) >= 5:
            break
        pad = _norm_padrao(str(card.get("padrao") or ""))
        if not pad or pad in vistos:
            continue
        raw = por.get(pad) or card
        freq = int(raw.get("frequencia") or 0)
        jogos = int(raw.get("jogos_possiveis") or card.get("jogos_possiveis") or 0)
        if freq <= 0 or jogos <= 0:
            continue
        if not _padrao_cabe(pad, list(pool), k):
            continue
        if not _padrao_aceita_obrigatorias(pad, obrigatorias):
            continue
        item = dict(raw)
        item["padrao"] = pad
        item["frequencia"] = freq
        item["jogos_possiveis"] = jogos
        item["descricao"] = card.get("descricao") or raw.get("descricao") or ""
        item["top_diagonais"] = list(card.get("top_diagonais") or raw.get("top_diagonais") or [])
        item["posto"] = len(out) + 1
        vistos.add(pad)
        out.append(item)
    return out


def _proximo_vivo(
    cinco: Sequence[Dict[str, Any]],
    padrao_morto: str,
    falhos: Set[str],
) -> Optional[Dict[str, Any]]:
    pads = [p["padrao"] for p in cinco]
    try:
        inicio = pads.index(padrao_morto)
    except ValueError:
        inicio = -1
    for passo in range(1, len(cinco) + 1):
        cand = cinco[(inicio + passo) % len(cinco)]
        if cand["padrao"] not in falhos:
            return cand
    return None


def _casa_diagonal_padrao(
    dezenas: Sequence[int],
    tops: Sequence[Dict[str, Any]],
    dmin: int,
    dmax: int,
) -> bool:
    alvos = list(tops or [])
    if not alvos:
        return False
    runs = _diagonais_da_aposta(dezenas, dmin, dmax)
    if not runs:
        return False
    chaves = {str(r.get("key") or "") for r in runs}
    conjuntos = [set(_ints(r.get("nums") or [])) for r in runs]
    for alvo in alvos:
        chave = str(alvo.get("key") or "")
        if chave and chave in chaves:
            return True
        nums = set(_ints(alvo.get("nums") or []))
        if len(nums) >= 2 and any(nums.issubset(grupo) for grupo in conjuntos):
            return True
    return False


def _score(
    dez: Sequence[int],
    *,
    ultimo: Set[int],
    pendentes: Set[int],
    status: str,
    rep_pref: Tuple[int, int],
    seq_n: int,
    seq_recente: Optional[int],
    ciclo_fim: bool,
    atrasos: Optional[Dict[int, int]] = None,
) -> float:
    reps = [n for n in dez if n in ultimo]
    pts = 0.0
    if rep_pref[0] <= len(reps) <= rep_pref[1]:
        pts += 6
    elif len(reps) == 0:
        pts += 1
    pts += 4.0 * sum(1 for n in dez if n in pendentes)
    if atrasos:
        atraso_pend = sum(min(int(atrasos.get(n, 0)), 40) for n in dez if n in pendentes)
        atraso_resto = sum(min(int(atrasos.get(n, 0)), 40) for n in dez if n not in pendentes)
        pts += min(10.0, atraso_pend * 0.2)
        pts += min(4.0, atraso_resto * 0.05)
    if status == "dentro":
        pts += 5
    elif status == "proxima":
        pts += 3
    if ciclo_fim:
        faltam = [n for n in pendentes if n not in dez]
        if not faltam:
            pts += 4
        else:
            pts -= min(4, len(faltam))
    if seq_recente and int(seq_n) == int(seq_recente):
        pts -= 3
    return pts


def _fmt_grupos(grupos: Sequence[Sequence[int]], sep: str) -> str:
    if not grupos:
        return "nenhuma"
    return " · ".join(sep.join(f"{int(n):02d}" for n in g) for g in grupos)


def _fmt_diags(grupos: Sequence[Dict[str, Any]]) -> str:
    if not grupos:
        return "nenhuma"
    partes = []
    for g in grupos:
        sym = g.get("dir_sym") or ("↘" if g.get("dir") != "up" else "↗")
        nums = "-".join(f"{int(n):02d}" for n in (g.get("nums") or []))
        partes.append(f"{sym} {nums}")
    return " · ".join(partes)


def _justificativa(
    *,
    padrao: str,
    descricao: str,
    frequencia: int,
    jogos: int,
    inedito: bool,
    faixa: str,
    seq_n: int,
    cls: Dict[str, Any],
    dez: Sequence[int],
    ultimo: Sequence[int],
    restr: Dict[str, Any],
    pendentes_usados: Sequence[int],
    pool_ampliado: bool,
    diagonal_padrao: bool = False,
) -> str:
    ult_set = set(ultimo)
    reps = [n for n in dez if n in ult_set]
    faixa_nome = {"baixa": "baixa", "media": "média", "alta": "alta"}.get(faixa, faixa)
    if inedito:
        origem = "padrão que ainda não ocorreu no histórico"
    else:
        origem = f"padrão com {frequencia} ocorrência(s); a faixa segue essa distribuição"
    soma_txt = cls.get("status_media_label") or cls.get("status_media") or ""
    media = cls.get("media")
    partes = [
        f"Padrão {padrao}" + (f" ({descricao})" if descricao else "") + f", {jogos} jogos possíveis.",
        f"{origem.capitalize()}. Sequência {seq_n} na faixa {faixa_nome}, perto do centro do que esse padrão já mostrou.",
        f"Soma {sum(dez)}" + (f", média {media}" if media is not None else "") + (f", {soma_txt}." if soma_txt else "."),
        (
            "Usa só dezenas que não saíram no último concurso."
            if not reps
            else "O restante da aposta não saiu no último concurso."
        ),
        "Repetidos em relação ao concurso anterior: "
        + (" ".join(f"{n:02d}" for n in reps) if reps else "nenhum")
        + f" ({len(reps)}).",
        "Não usa os repetidos proibidos "
        + (" ".join(f"{n:02d}" for n in restr.get("repetidos_proibidos") or []) or "—")
        + ".",
        "Não reproduz as sequências " + _fmt_grupos(restr.get("sequencias_proibidas") or [], "-")
        + ", os finais " + _fmt_grupos(restr.get("finais_proibidos") or [], ",")
        + " nem as diagonais " + _fmt_diags(restr.get("diagonais_proibidas") or [])
        + ".",
    ]
    if pendentes_usados:
        partes.append(
            "Pendentes do ciclo nesta aposta: " + " ".join(f"{n:02d}" for n in pendentes_usados) + "."
        )
    if pool_ampliado:
        partes.append(
            "As pendentes do ciclo que não saíram entram primeiro. O complemento usa as mais atrasadas dessa mesma lista."
        )
    if diagonal_padrao:
        partes.append("Inclui uma diagonal que a análise já registrou junto com este padrão.")
    return " ".join(partes)


def gerar_lote_2a1(
    *,
    catalogo: Sequence[Dict[str, Any]],
    linhas_panorama: Sequence[Dict[str, Any]],
    ultimo: Sequence[int],
    penultimo: Optional[Sequence[int]],
    pendentes: Sequence[int],
    historico: Optional[Iterable[Sequence[int]]] = None,
    quantidade: int = 10,
    repetidos: str = "1-2",
    dezena_min: int = 1,
    dezena_max: int = 31,
    k: int = 7,
    cols: int = 10,
    padroes_cruzamento: Optional[Sequence[Dict[str, Any]]] = None,
    rng: Optional[random.Random] = None,
) -> Dict[str, Any]:
    rng = rng or random.Random()
    dmin, dmax = int(dezena_min), int(dezena_max)
    k = int(k)
    qtd = max(1, min(30, int(quantidade or 10)))
    ult = _ints(ultimo)
    if len(ult) < 1:
        return {"sucesso": False, "erro": "Não há concurso anterior para orientar a 2A1."}

    restr = montar_restricoes(ult, penultimo, dmin=dmin, dmax=dmax, cols=cols)
    pends = [n for n in _ints(pendentes) if dmin <= n <= dmax]
    modo_rep = str(repetidos or "0")
    rep_min, rep_max, folga_zero = faixa_repetidos(modo_rep)
    allowed, ampliado = _pool_permitido(
        restr, pends, dmin=dmin, dmax=dmax, k=k, rep_max=rep_max,
    )
    atrasos = _atrasos(
        [
            {
                "concurso": row.get("concurso") or 0,
                "numeros": row.get("numeros") or row.get("dezenas") or [],
            }
            for row in linhas_panorama
        ],
        dmin,
        dmax,
    )
    if len(allowed) < k:
        return {
            "sucesso": False,
            "erro": "O pool permitido não alcança o tamanho da aposta.",
            "restricoes": restr,
        }

    perfis = _contagens_faixa(linhas_panorama)
    ciclo_fim = 0 < len(pends) <= max(10, k)
    pend_set = {n for n in pends if n in allowed}
    # Prioridade no placar. Não tira um dos cinco padrões só porque a pendente é de outra dezena.
    pend_exigidas: Set[int] = set()
    freq_n: Dict[str, int] = {}
    for raw in catalogo:
        p = _norm_padrao(str(raw.get("padrao") or ""))
        if p:
            freq_n[p] = int(raw.get("frequencia") or 0)
    jogos_n: Dict[str, int] = {}
    for raw in catalogo:
        p = _norm_padrao(str(raw.get("padrao") or ""))
        if p:
            jogos_n[p] = int(raw.get("jogos_possiveis") or 0)
    n_por_padrao = {
        p: i + 1
        for i, p in enumerate(
            sorted(freq_n, key=lambda x: (-freq_n[x], -jogos_n.get(x, 0), x))
        )
    }
    fonte = list(catalogo if padroes_cruzamento is None else padroes_cruzamento)
    cinco = _resolver_cinco(
        catalogo, fonte, allowed, k, obrigatorias=sorted(pend_exigidas),
    )
    if not cinco:
        return {
            "sucesso": False,
            "erro": (
                "A análise não devolveu os cinco padrões do cruzamento."
                if not fonte
                else "Nenhum dos cinco padrões do cruzamento cabe nas dezenas permitidas."
            ),
            "restricoes": restr,
        }
    cotas = cotas_relevancia(qtd, len(cinco))
    fila = [cinco[ix] for ix in fila_intercalada(cotas)]

    ja_saiu: Set[Tuple[int, ...]] = set()
    for item in historico or []:
        chave = tuple(sorted(_ints(item)))
        if len(chave) == k:
            ja_saiu.add(chave)
    for row in linhas_panorama:
        chave = tuple(sorted(_ints(row.get("dezenas") or [])))
        if len(chave) == k:
            ja_saiu.add(chave)

    rep_pref = (rep_min, rep_max)
    ult_set = set(ult)
    usados_seq: Set[Tuple[str, int]] = set()
    usados_dez: Set[Tuple[int, ...]] = set()
    apostas: List[Dict[str, Any]] = []
    avisos: List[str] = []
    if padroes_cruzamento is not None:
        ficaram = {p["padrao"] for p in cinco}
        vistos_aviso: Set[str] = set()
        for card in list(padroes_cruzamento)[:5]:
            p = _norm_padrao(str(card.get("padrao") or ""))
            if not p or p in vistos_aviso:
                continue
            vistos_aviso.add(p)
            if p not in ficaram:
                avisos.append(f"Padrão {p} ficou de fora: não cabe nas dezenas permitidas.")

    recente_seq: Dict[str, Tuple[int, int]] = {}
    for row in linhas_panorama:
        pad = _norm_padrao(str(row.get("padrao") or ""))
        try:
            conc = int(row.get("concurso") or 0)
            seq = int(row.get("sequencia_n") or 0)
        except (TypeError, ValueError):
            continue
        atual = recente_seq.get(pad)
        if atual is None or conc >= atual[0]:
            recente_seq[pad] = (conc, seq)

    falhos: Set[str] = set()
    i = 0
    guard = 0
    limite = max(qtd * (len(cinco) + 2), len(fila) + 5)

    def _repassar(pad_morto: str) -> bool:
        sub = _proximo_vivo(cinco, pad_morto, falhos)
        if not sub:
            return False
        for j in range(i, len(fila)):
            if fila[j].get("padrao") == pad_morto:
                fila[j] = sub
        return True

    while i < len(fila) and len(apostas) < qtd and guard < limite:
        guard += 1
        spec = fila[i]
        pad = spec["padrao"]
        if pad in falhos:
            if not _repassar(pad):
                break
            continue
        perfil = perfis.get(pad) or {"counts": Counter(), "ns": [], "media": None, "somas": []}
        faixa_soma = calcular_faixa_soma(perfil.get("somas") or [], fonte="historico")
        if faixa_soma is None and perfil.get("media") is not None:
            faixa_soma = {"media": int(perfil["media"]), "tol_dentro": 1, "tol_proxima": 2}
        media_rank = {"media": (faixa_soma or {}).get("media", perfil.get("media"))}
        if media_rank["media"] is None:
            media_rank = None
        faixa = _escolher_faixa(perfil["counts"], rng)
        ordem = _ordem_na_faixa(int(spec["jogos_possiveis"]), faixa, perfil["ns"])
        # Se a faixa escolhida não fechar, as outras entram na sequência.
        for extra in _FAIXAS:
            if extra == faixa:
                continue
            ordem.extend(_ordem_na_faixa(int(spec["jogos_possiveis"]), extra, perfil["ns"]))
        melhor: Optional[Tuple[float, List[int], int, str, Dict[str, Any], bool]] = None
        vistos_local: Set[int] = set()
        faixas_por_n = {}
        for nome in _FAIXAS:
            for n in _ordem_na_faixa(int(spec["jogos_possiveis"]), nome, perfil["ns"])[:80]:
                faixas_por_n.setdefault(n, nome)
        tentativas = 0
        for seq_n in ordem:
            if tentativas >= 480:
                break
            if seq_n in vistos_local or (pad, seq_n) in usados_seq:
                continue
            vistos_local.add(seq_n)
            tentativas += 1
            dez = dezenas_na_sequencia(
                pad, seq_n, media_rank, min_dezena=dmin, max_dezena=dmax,
            )
            if not dez or len(dez) != k:
                continue
            if padrao_inicial(dez) != pad:
                continue
            dez = _encaixar_no_pool(dez, allowed, pend_set, atrasos, dmin, dmax)
            if not dez or len(dez) != k or padrao_inicial(dez) != pad:
                continue
            pode_rep = {int(n) for n in _ints(restr.get("pode_repetir"))}
            dez = _ajustar_repetidos(
                dez, allowed, ult_set, pode_rep,
                rep_min, rep_max, pend_set, atrasos, dmin, dmax,
                folga_zero=folga_zero,
            )
            if not dez or len(dez) != k or padrao_inicial(dez) != pad:
                continue
            chave = tuple(dez)
            if chave in usados_dez or chave in ja_saiu:
                continue
            if any(n not in allowed for n in dez):
                continue
            if pend_exigidas and not pend_exigidas.issubset(set(dez)):
                continue
            reps = sum(1 for n in dez if n in ult_set)
            if not (rep_min <= reps <= rep_max):
                if not (folga_zero and reps == 0):
                    continue
            motivo = viola_restricoes(dez, restr, dmin=dmin, dmax=dmax, cols=cols)
            if motivo:
                continue
            if not _diagonais_da_aposta(dez, dmin, dmax):
                continue

            def _aceita_forma(trial: Sequence[int]) -> bool:
                if len(trial) != k or padrao_inicial(trial) != pad:
                    return False
                tchave = tuple(trial)
                if tchave in usados_dez or tchave in ja_saiu:
                    return False
                if any(n not in allowed for n in trial):
                    return False
                if pend_exigidas and not pend_exigidas.issubset(set(trial)):
                    return False
                treps = sum(1 for n in trial if n in ult_set)
                if not (rep_min <= treps <= rep_max) and not (folga_zero and treps == 0):
                    return False
                if viola_restricoes(trial, restr, dmin=dmin, dmax=dmax, cols=cols):
                    return False
                return bool(_diagonais_da_aposta(trial, dmin, dmax))

            if not _forma_seq_finais(dez):
                dez = _ajustar_seq_e_finais(
                    dez, dmin=dmin, dmax=dmax,
                    travadas=sorted(pend_exigidas),
                    aceitar=_aceita_forma,
                )
                if not _forma_seq_finais(dez) and any(n not in pend_exigidas for n in dez):
                    continue
                reps = sum(1 for n in dez if n in ult_set)
            cls = classificar_soma(sum(dez), faixa_soma)
            seq_rec = (recente_seq.get(pad) or (0, 0))[1] or None
            pts = _score(
                dez,
                ultimo=ult_set,
                pendentes=pend_set,
                status=str(cls.get("status_media") or ""),
                rep_pref=rep_pref,
                seq_n=seq_n,
                seq_recente=seq_rec,
                ciclo_fim=ciclo_fim,
                atrasos=atrasos,
            )
            nd = _n_digitos(dez)
            ndiag = len(_diagonais_da_aposta(dez, dmin, dmax))
            ja7 = sum(1 for a in apostas if _n_digitos(a.get("dezenas") or []) == 7)
            if nd == 7:
                pts += 14
            elif ja7 <= len(apostas) // 2:
                pts -= 4
            if 2 <= ndiag <= 3:
                pts += 6
            casa = _casa_diagonal_padrao(dez, spec.get("top_diagonais") or [], dmin, dmax)
            if casa:
                pts += 5
            nome_faixa = faixas_por_n.get(seq_n) or faixa
            if melhor is None or pts > melhor[0]:
                melhor = (pts, list(dez), int(seq_n), nome_faixa, cls, casa)
            n_pend_melhor = sum(1 for n in melhor[1] if n in pend_set) if melhor else 0
            precisa_pend = min(2, len(pend_set)) if pend_set else 0
            if (
                melhor
                and melhor[0] >= 24
                and n_pend_melhor >= precisa_pend
                and (ja7 > qtd // 2 or _n_digitos(melhor[1]) == 7)
                and rep_min <= sum(1 for n in melhor[1] if n in ult_set) <= rep_max
            ):
                break
        if not melhor:
            falhos.add(pad)
            avisos.append(f"Padrão {pad} não produziu aposta dentro das restrições.")
            if not _repassar(pad):
                break
            continue
        _pts, dez, seq_semente, nome_faixa, cls, casa_diag = melhor
        pad_real, seq_real = _identidade_valida(
            dez, faixa_soma, dmin=dmin, dmax=dmax,
        )
        if pad_real:
            pad = pad_real
        seq_n = int(seq_real) if seq_real else int(seq_semente)
        nome_faixa = classificar_faixa_sequencia(
            seq_n, int(spec.get("jogos_possiveis") or 0),
        ) or nome_faixa
        chave = tuple(dez)
        usados_dez.add(chave)
        usados_seq.add((pad, seq_n))
        pend_usados = sorted(n for n in dez if n in pend_set)
        inedito = int(spec.get("frequencia") or 0) <= 0
        apostas.append({
            "dezenas": list(dez),
            "padrao": pad,
            "padrao_inicial": pad,
            "posto": int(spec.get("posto") or 0),
            "n_padrao": n_por_padrao.get(pad),
            "descricao": spec.get("descricao") or "",
            "frequencia": int(spec.get("frequencia") or 0),
            "jogos_possiveis": int(spec.get("jogos_possiveis") or 0),
            "inedito": inedito,
            "faixa_sequencia": nome_faixa,
            "sequencia_n": seq_n,
            "soma": int(sum(dez)),
            "status_media": cls.get("status_media"),
            "status_media_label": cls.get("status_media_label"),
            "media_soma": cls.get("media"),
            "repetidos": sorted(n for n in dez if n in ult_set),
            "pendentes": pend_usados,
            "diagonal_padrao": bool(casa_diag),
            "justificativa": _justificativa(
                padrao=pad,
                descricao=str(spec.get("descricao") or ""),
                frequencia=int(spec.get("frequencia") or 0),
                jogos=int(spec.get("jogos_possiveis") or 0),
                inedito=inedito,
                faixa=nome_faixa,
                seq_n=seq_n,
                cls=cls,
                dez=dez,
                ultimo=ult,
                restr=restr,
                pendentes_usados=pend_usados,
                pool_ampliado=ampliado,
                diagonal_padrao=bool(casa_diag),
            ),
        })
        i += 1

    if not apostas:
        return {
            "sucesso": False,
            "erro": "Nenhuma aposta fechou as restrições da 2A1 com os padrões disponíveis.",
            "avisos": avisos,
            "restricoes": restr,
        }
    return {
        "sucesso": True,
        "apostas": apostas,
        "quantidade": len(apostas),
        "quantidade_solicitada": qtd,
        "restricoes": restr,
        "pool_ampliado": ampliado,
        "avisos": avisos,
        "ciclo_fim": ciclo_fim,
        "repetidos_modo": modo_rep,
        "padroes_cinco": [
            {
                "posto": int(p.get("posto") or ix + 1),
                "padrao": p.get("padrao"),
                "descricao": p.get("descricao") or "",
                "frequencia": int(p.get("frequencia") or 0),
                "cota": int(cotas[ix]) if ix < len(cotas) else 0,
            }
            for ix, p in enumerate(cinco)
        ],
    }
