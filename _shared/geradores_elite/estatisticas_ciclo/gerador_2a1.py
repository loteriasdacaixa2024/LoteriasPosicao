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
    from .gerador import _ajustar_seq_e_finais, _forma_seq_finais
except ImportError:
    from gerador import _ajustar_seq_e_finais, _forma_seq_finais

from analise_inteligentes_diadesorte.analise_sequencias import (
    classificar_faixa_sequencia,
    limites_faixa,
)
from analise_inteligentes_diadesorte.sequencias_sorteadas import dezenas_na_sequencia
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
    """O único corte duro de identidade é o repetido proibido.

    Pendentes e repetidos permitidos não bastam quando o ciclo está no fim:
    uma aposta de k dezenas com no máximo rep_max repetidos precisa de
    números que não saíram no concurso anterior, mesmo que já tenham saído
    do ciclo.
    """
    ban = set(_ints(restr.get("repetidos_proibidos")))
    ultimo = set(_ints(restr.get("ultimo")))
    allowed = {n for n in range(int(dmin), int(dmax) + 1) if n not in ban}
    fora = {
        int(n)
        for n in pendentes
        if int(dmin) <= int(n) <= int(dmax) and int(n) not in ultimo and int(n) not in ban
    }
    ampliado = len(fora) < max(0, int(k) - int(rep_max))
    return allowed, ampliado


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
) -> float:
    reps = [n for n in dez if n in ultimo]
    pts = 0.0
    if rep_pref[0] <= len(reps) <= rep_pref[1]:
        pts += 6
    elif len(reps) == 0:
        pts += 1
    pts += 0.4 * sum(1 for n in dez if n in pendentes)
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
            "As pendentes do ciclo não bastavam para a aposta. O complemento usou dezenas que não saíram no concurso anterior."
        )
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
    rep_min, rep_max, folga_zero = faixa_repetidos(repetidos)
    allowed, ampliado = _pool_permitido(
        restr, pends, dmin=dmin, dmax=dmax, k=k, rep_max=rep_max,
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
    pend_exigidas = set(pend_set) if 0 < len(pend_set) <= k else set()
    freq_n: Dict[str, int] = {}
    for raw in catalogo:
        p = _norm_padrao(str(raw.get("padrao") or ""))
        if p:
            freq_n[p] = int(raw.get("frequencia") or 0)
    n_por_padrao = {
        p: i + 1
        for i, p in enumerate(sorted(freq_n, key=lambda x: (-freq_n[x], x)))
    }
    lote = _escolher_padroes(
        catalogo, allowed, k, qtd, rng, obrigatorias=sorted(pend_exigidas),
        limite_distintos=10**6,
    )
    if not lote:
        return {
            "sucesso": False,
            "erro": "Nenhum padrão do Panorama cabe nas dezenas permitidas.",
            "restricoes": restr,
        }

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
    cursor = 0
    guard = 0
    while len(apostas) < qtd and guard < max(qtd * 8, len(lote)):
        guard += 1
        vivos = [p for p in lote if p["padrao"] not in falhos]
        if not vivos:
            break
        spec = vivos[cursor % len(vivos)]
        cursor += 1
        pad = spec["padrao"]
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
        melhor: Optional[Tuple[float, List[int], int, str, Dict[str, Any]]] = None
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
            nome_faixa = faixas_por_n.get(seq_n) or faixa
            if melhor is None or pts > melhor[0]:
                melhor = (pts, list(dez), int(seq_n), nome_faixa, cls)
            if (
                melhor
                and melhor[0] >= 20
                and (ja7 > qtd // 2 or _n_digitos(melhor[1]) == 7)
                and rep_min <= sum(1 for n in melhor[1] if n in ult_set) <= rep_max
            ):
                break
        if not melhor:
            falhos.add(pad)
            avisos.append(f"Padrão {pad} não produziu aposta dentro das restrições.")
            continue
        _pts, dez, seq_n, nome_faixa, cls = melhor
        chave = tuple(dez)
        usados_dez.add(chave)
        usados_seq.add((pad, seq_n))
        pend_usados = sorted(n for n in dez if n in pend_set)
        inedito = int(spec.get("frequencia") or 0) <= 0
        apostas.append({
            "dezenas": list(dez),
            "padrao": pad,
            "padrao_inicial": pad,
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
            ),
        })

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
        "repetidos_modo": str(repetidos or "1-2"),
    }
