# -*- coding: utf-8 -*-
"""Gerador Ciclo — Estratégias: plano de ciclo (novas, evolução, repetidas, progresso)."""
from __future__ import annotations

import itertools
import math
import random
from collections import Counter
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from .inteligencia_service import CicloInteligenciaService
from .loaders import carregar_sorteios_asc
from .specs import get_ciclo_spec

DESDOBRAMENTO_OK = (2, 3, 4, 5, 6)
MAX_CANDIDATOS_BRUTOS = 8000
MAX_SCORE_POOL = 400


def _chave(dezenas: List[int]) -> Tuple[int, ...]:
    return tuple(sorted(int(x) for x in dezenas))


def _historico_exato(modality_key: str) -> Set[Tuple[int, ...]]:
    return {_chave(s["dezenas"]) for s in carregar_sorteios_asc(modality_key)}


def _padrao_estrutura(dezenas: List[int]) -> Tuple[int, int, int]:
    """(pares, faixa_soma_bucket, baixa_count) — saturacao recente."""
    pares = sum(1 for d in dezenas if d % 2 == 0)
    soma = sum(dezenas)
    # buckets de ~20 pontos (Dia de Sorte típico ~80–160)
    bucket = soma // 20
    baixas = sum(1 for d in dezenas if d <= 10)
    return pares, bucket, baixas


def _estruturas_recentes(modality_key: str, janela: int = 40) -> Counter:
    sorteios = carregar_sorteios_asc(modality_key)
    recentes = sorteios[-janela:] if janela else sorteios
    return Counter(_padrao_estrutura(list(s["dezenas"])) for s in recentes)


def _score_jogo(
    jogo: List[int],
    faltantes: List[int],
    scores_map: Dict[int, float],
    ultimo: List[int],
    *,
    evo: Optional[Dict[str, Any]] = None,
    modality_key: str = "diadesorte",
) -> float:
    s = 0.0
    if faltantes:
        s = sum(scores_map.get(d, 40.0) for d in faltantes) / len(faltantes)
    ult = set(ultimo)
    s += 4.0 * len(ult & set(jogo))
    pares = sum(1 for d in jogo if d % 2 == 0)
    s -= abs(pares - 3.5) * 2.5
    s -= abs(sum(jogo) - 112) / 18.0
    if evo:
        k = len(faltantes)
        sug = int(evo.get("k_faltantes_sugerido") or 2)
        pesos = evo.get("pesos_amostra_k") or {}
        chave = "0" if k <= 0 else ("4+" if k >= 4 else str(k))
        s += float(pesos.get(chave, 0)) / 8.0
        s -= abs(k - sug) * 8.0
        if k == sug:
            s += 12.0
        if k >= sug + 2:
            s -= 15.0 * (k - sug)

        # Novas Dezenas → favorece faltantes na faixa que mais preencheu
        faixa_prior = evo.get("faixa_nova_prioritaria") or (
            (evo.get("observacoes") or {}).get("novas_dezenas") or {}
        ).get("faixa_prioritaria")
        if faixa_prior:
            from .inteligencia_service import CicloInteligenciaService
            for d in faltantes:
                if CicloInteligenciaService._faixa(d, modality_key) == faixa_prior:
                    s += 3.5

        # Repetidas no Ciclo → favorece âncoras que mais voltam
        top_rep = set(evo.get("top_repetidas_ciclo") or [])
        if top_rep:
            s += 2.5 * len(top_rep & set(jogo))

        # Progresso → se já avançado, penaliza jogos “fechamento total”
        pct = float(evo.get("progresso_pct") or 0)
        n_pend = int(((evo.get("observacoes") or {}).get("progresso") or {}).get("faltantes") or 0)
        if pct >= 75 and n_pend and k >= max(3, n_pend - 1):
            s -= 20.0
    return s


def _atraso_saidas(modality_key: str, saidas: List[int]) -> List[int]:
    """Já saídas no ciclo, das mais atrasadas para as mais recentes."""
    af = CicloInteligenciaService._atraso_e_frequencia(modality_key)
    return sorted(
        [int(d) for d in saidas],
        key=lambda d: (-int(af.get(d, {}).get("atraso", 0)), d),
    )


def _pesos_k_evolucao(
    evo: Dict[str, Any],
    n_pend: int,
    pick_n: int,
) -> Dict[int, float]:
    """
    Converte Qtd. Evolução observada em pesos de k faltantes (1..6).
    Ex.: às vezes vem 1 nova, 2, 5… — replica o que mais acontece.
    """
    pesos: Dict[int, float] = {}
    # Preferir distribuição recente; fallback ciclo
    dist = dict(evo.get("distribuicao_recente_pct") or {})
    if sum(dist.values()) <= 0:
        dist = dict(evo.get("distribuicao_qtd_pct") or {})
    pesos_amostra = dict(evo.get("pesos_amostra_k") or {})

    def _add(k: int, w: float) -> None:
        if 1 <= k <= min(6, n_pend, pick_n - 1 if pick_n > 1 else pick_n):
            pesos[k] = pesos.get(k, 0.0) + max(0.0, w)

    for chave, w in {**dist, **{k: pesos_amostra.get(k, 0) for k in dist}}.items():
        if chave == "0":
            continue
        if chave == "4+":
            # reparte 4/5/6 (7 = jogo inteiro de novas — raro no fim)
            for ki, frac in ((4, 0.5), (5, 0.3), (6, 0.2)):
                _add(ki, float(w) * frac)
        else:
            try:
                _add(int(chave), float(w))
            except ValueError:
                continue

    # Reforça pesos_amostra se dist veio vazio
    if not pesos:
        for chave, w in pesos_amostra.items():
            if chave == "0":
                continue
            if chave == "4+":
                for ki in (4, 5):
                    _add(ki, float(w))
            else:
                try:
                    _add(int(chave), float(w))
                except ValueError:
                    continue

    sug = int(evo.get("k_faltantes_sugerido") or 2)
    _add(sug, 25.0)
    # Garante pelo menos 1 e 2 (casos do exemplo do usuário)
    _add(1, 8.0)
    _add(2, 8.0)
    if n_pend >= 3:
        _add(3, 5.0)

    # Finalização: não esgotar todas as faltantes
    if n_pend <= 8 and n_pend in pesos and n_pend > 1:
        pesos[n_pend] = min(pesos.get(n_pend, 0), 3.0)

    return {k: w for k, w in pesos.items() if w > 0}


def _cotas_por_k(pesos: Dict[int, float], quantidade: int) -> Dict[int, int]:
    """Quantas apostas por k (método do maior resto), espelhando frequências."""
    if not pesos or quantidade <= 0:
        return {}
    total_w = sum(pesos.values()) or 1.0
    keys = sorted(pesos.keys())
    exact = {k: quantidade * pesos[k] / total_w for k in keys}
    cotas = {k: int(exact[k]) for k in keys}
    falta = quantidade - sum(cotas.values())
    # Garante presença dos k mais pesados se quantidade permitir
    ordenados = sorted(keys, key=lambda k: (-(exact[k] - cotas[k]), -pesos[k], k))
    i = 0
    while falta > 0 and ordenados:
        cotas[ordenados[i % len(ordenados)]] += 1
        falta -= 1
        i += 1
    # Se algum k ficou 0 mas tem peso relevante e ainda há sobra em outros, redistribui mínimo
    for k in sorted(keys, key=lambda x: -pesos[x]):
        if cotas.get(k, 0) == 0 and pesos[k] >= 5 and quantidade >= len([x for x in cotas if cotas[x] > 0]) + 1:
            # tira 1 do maior bucket
            doador = max(cotas.keys(), key=lambda x: cotas[x])
            if cotas[doador] > 1:
                cotas[doador] -= 1
                cotas[k] = 1
    return {k: n for k, n in cotas.items() if n > 0}


def _completar_com_atrasadas(
    faltantes: List[int],
    atrasadas: List[int],
    pick_n: int,
) -> List[int]:
    """Completa o jogo até pick_n com as já saídas mais atrasadas."""
    jogo = list(faltantes)
    usados = set(jogo)
    for d in atrasadas:
        if len(jogo) >= pick_n:
            break
        if d not in usados:
            jogo.append(d)
            usados.add(d)
    return sorted(jogo)


def _limitar_combinacoes(pool: List[int], k: int, scores_map: Dict[int, float], rng: random.Random):
    """Se C(n,k) explode, amostra as melhores por score. k=0 = jogo só de já saídas."""
    if k == 0:
        return [()]
    n = len(pool)
    if k < 0 or n < k:
        return []
    total = math.comb(n, k) if n <= 40 else 10**9
    if total <= MAX_CANDIDATOS_BRUTOS:
        return list(itertools.combinations(sorted(pool), k))

    ordenado = sorted(pool, key=lambda d: scores_map.get(d, 0), reverse=True)
    top_n = min(n, max(k + 6, 14))
    base = ordenado[:top_n]
    combos = list(itertools.combinations(base, k))
    if len(combos) > MAX_CANDIDATOS_BRUTOS:
        rng.shuffle(combos)
        combos = combos[:MAX_CANDIDATOS_BRUTOS]
    return combos


def _completar_com_plano(
    faltantes: List[int],
    plano: Dict[str, Any],
    pick_n: int,
    variante: int,
    atrasadas_fallback: List[int],
) -> List[int]:
    """Núcleo compartilhado + grupo de repetidas da variante + âncoras de variação."""
    jogo = list(faltantes)
    usados = set(jogo)
    aliviar = set(int(x) for x in (plano.get("repetidas_aliviar") or []))
    grupos = plano.get("grupos_repetidas") or [[]]
    grupo = list(grupos[variante % len(grupos)]) if grupos else []
    nucleo = [int(x) for x in (plano.get("nucleo_ancoras") or [])]
    variacao = [int(x) for x in (plano.get("variacao_ancoras") or [])]

    def _add(seq, *, aceitar_alivio: bool = False) -> None:
        for d in seq:
            if len(jogo) >= pick_n:
                return
            di = int(d)
            if di in usados:
                continue
            if (not aceitar_alivio) and di in aliviar:
                continue
            jogo.append(di)
            usados.add(di)

    _add(grupo)
    _add(nucleo)
    _add(variacao)
    _add(atrasadas_fallback)
    _add(grupo + nucleo + variacao + atrasadas_fallback, aceitar_alivio=True)
    return sorted(jogo)


def _contador_diagonais(dmin: int, dmax: int):
    from analise_inteligentes_diadesorte.diagonais_volante import (
        diag_lines,
        diag_runs_in_draw,
        pos_map,
        volante_rows,
    )

    rows = volante_rows(dmin, dmax)
    lines = diag_lines(rows)
    pmap = pos_map(rows)

    def contar(dezenas: Sequence[int]) -> int:
        nums = {int(x) for x in dezenas}
        return len([
            r for r in diag_runs_in_draw(nums, lines, pmap)
            if int(r.get("len") or 0) >= 2
        ])

    return contar


def _aproximar_diagonais(
    jogo: Sequence[int],
    locked: Sequence[int],
    alvo: int,
    pool: Sequence[int],
    contar,
    segmentos: Sequence[Sequence[int]],
    pick_n: int,
) -> List[int]:
    """Aproxima a aposta da quantidade de diagonais pedida, sem tirar as faltantes."""
    atual = sorted({int(x) for x in jogo})
    fixos = {int(x) for x in locked}
    reserva = [int(x) for x in pool if int(x) not in fixos][:16]
    segs = [list(s) for s in segmentos if len(s) >= 2][:8]

    def dist(q: int) -> int:
        return abs(int(q) - int(alvo))

    for _ in range(16):
        qtd = contar(atual)
        if qtd == alvo or len(atual) != pick_n:
            break
        melhor = None
        if qtd < alvo:
            for seg in segs:
                faltam = [n for n in seg if n not in atual]
                if not faltam:
                    continue
                livres = [d for d in atual if d not in fixos and d not in seg]
                if len(livres) < len(faltam):
                    continue
                drop = set(livres[:len(faltam)])
                trial = sorted((d for d in atual if d not in drop)) 
                trial = sorted(set(trial + faltam))
                if len(trial) != pick_n:
                    continue
                nq = contar(trial)
                if dist(nq) < dist(qtd) and (melhor is None or dist(nq) < dist(melhor[0])):
                    melhor = (nq, trial)
                    if nq == alvo:
                        break
        else:
            livres = [d for d in atual if d not in fixos]
            for d in livres:
                base = [x for x in atual if x != d]
                for p in reserva:
                    if p in atual:
                        continue
                    trial = sorted(set(base + [p]))
                    if len(trial) != pick_n:
                        continue
                    nq = contar(trial)
                    if dist(nq) < dist(qtd) and (melhor is None or dist(nq) < dist(melhor[0])):
                        melhor = (nq, trial)
                        if nq == alvo:
                            break
                if melhor and melhor[0] == alvo:
                    break
        if not melhor:
            break
        atual = melhor[1]
        if melhor[0] == alvo:
            break
    return atual


def _escolher_diversos(bucket: List[dict], n_alvo: int) -> List[dict]:
    """Prioriza score, mas rotaciona pendentes para todas aparecerem no conjunto."""
    if n_alvo <= 0 or not bucket:
        return []
    restantes = list(bucket)
    escolhidos: List[dict] = []
    usados_ch: Set[Tuple[int, ...]] = set()
    uso_falt: Counter = Counter()
    while restantes and len(escolhidos) < n_alvo:
        restantes.sort(key=lambda x: (
            sum(uso_falt[d] for d in (x.get("faltantes") or [])),
            -float(x.get("score") or 0),
            x.get("soma") or 0,
            x.get("dezenas") or [],
        ))
        item = restantes.pop(0)
        ch = _chave(item["dezenas"])
        if ch in usados_ch:
            continue
        usados_ch.add(ch)
        escolhidos.append(item)
        for d in item.get("faltantes") or []:
            uso_falt[int(d)] += 1
    return escolhidos


def _como_influenciou(finais: List[dict], plano: Dict[str, Any]) -> str:
    if not finais:
        return ""
    freq: Counter = Counter()
    for a in finais:
        freq.update(int(x) for x in a.get("dezenas") or [])
    n = len(finais)
    pend = [int(x) for x in (plano.get("pendentes") or [])]
    nucleo = [int(x) for x in (plano.get("nucleo_ancoras") or [])]
    aliviar = [int(x) for x in (plano.get("repetidas_aliviar") or [])]
    ativas = [int(x) for x in (plano.get("repetidas_ativas") or [])]

    def _fr(xs: List[int], lim: int = 6) -> str:
        partes = [f"{d:02d} em {freq.get(d, 0)}/{n}" for d in xs[:lim]]
        return "; ".join(partes) if partes else "—"

    mist = Counter(int(a.get("k_faltantes") or 0) for a in finais)
    mist_txt = ", ".join(f"{v}×k={k}" for k, v in sorted(mist.items()))
    return (
        f"Pendentes nas {n} apostas: {_fr(pend)}. "
        f"Núcleo (âncoras): {_fr(nucleo)}. "
        f"Repetidas ativas distribuídas: {_fr(ativas)}. "
        f"Excesso/quebra (alívio): {_fr(aliviar)}. "
        f"Cotas geradas: {mist_txt}. "
        "Não é previsão do próximo concurso."
    )


def _k_alvo_diadesorte(
    n_pend: int,
    pick_n: int,
    n_saidas: int,
    k_fixo: Optional[int],
) -> Tuple[Optional[int], str]:
    """
    Dia de Sorte: no automático, 4 faltantes quando cabe; senão 3; senão 2.
    k explícito vale para todas as apostas. Se o jogo não fecha, ajusta e avisa.
    """
    k_min = max(0, int(pick_n) - int(n_saidas))
    k_max = min(int(n_pend), int(pick_n))
    if k_min > k_max:
        return None, "inviavel"
    if k_fixo is not None:
        pedido = int(k_fixo)
        k = min(max(pedido, k_min), k_max, 6)
        return k, ("fixo" if k == pedido else "ajustado")
    for k in (4, 3, 2):
        if k_min <= k <= k_max:
            return k, "auto"
    k = min(k_max, max(k_min, 1 if k_max >= 1 else 0))
    return k, "excecao"


def _combos_cobertura(
    pendentes: List[int],
    k: int,
    scores_map: Dict[int, float],
    quantidade: int,
) -> List[Tuple[int, ...]]:
    """Combinações de faltantes que cobrem o conjunto antes de repetir as mesmas."""
    nums = sorted(
        (int(x) for x in pendentes),
        key=lambda d: (-float(scores_map.get(d, 0) or 0), d),
    )
    n = len(nums)
    if k <= 0 or n < k or quantidade <= 0:
        return []
    vistos: Set[Tuple[int, ...]] = set()
    out: List[Tuple[int, ...]] = []
    for start in range(n):
        if len(out) >= quantidade:
            break
        picked = [nums[(start + i) % n] for i in range(k)]
        if len(set(picked)) < k:
            continue
        combo = tuple(sorted(picked))
        if combo in vistos:
            continue
        vistos.add(combo)
        out.append(combo)
    if len(out) < quantidade:
        for combo in _limitar_combinacoes(nums, k, scores_map, random.Random(0)):
            if len(out) >= quantidade:
                break
            if combo not in vistos:
                vistos.add(combo)
                out.append(combo)
    return out


def _segmentos_top(diag_info: Dict[str, Any]) -> Tuple[List[List[int]], Optional[List[int]]]:
    duplas: List[List[int]] = []
    fonte = diag_info.get("top_duplas") or diag_info.get("ranking") or []
    for s in fonte:
        nums = [int(x) for x in (s.get("nums") or [])]
        if len(nums) == 2 and nums not in duplas:
            duplas.append(nums)
        if len(duplas) >= 3:
            break
    trinca = None
    top_t = diag_info.get("top_trinca") or None
    if top_t and top_t.get("nums"):
        nums_t = [int(x) for x in top_t["nums"]]
        if len(nums_t) >= 3:
            trinca = nums_t
    return duplas, trinca


def _plantar_segmento(
    jogo: Sequence[int],
    locked: Sequence[int],
    segmento: Sequence[int],
    pool: Sequence[int],
    pick_n: int,
) -> Optional[List[int]]:
    """Inclui o trecho trocando só dezenas que não são faltantes do jogo."""
    atual = {int(x) for x in jogo}
    fixos = {int(x) for x in locked}
    permitidos = set(int(x) for x in pool) | fixos | atual
    seg = [int(x) for x in segmento]
    if any(n not in permitidos for n in seg):
        return None
    if any(n not in fixos and n not in pool for n in seg):
        return None
    faltam = [n for n in seg if n not in atual]
    if not faltam:
        return sorted(atual)
    livres = [d for d in sorted(atual) if d not in fixos and d not in seg]
    if len(livres) < len(faltam):
        return None
    drop = set(livres[:len(faltam)])
    trial = (atual - drop) | set(faltam)
    if len(trial) != pick_n:
        return None
    return sorted(trial)


def _fechar_com_segmento(
    faltantes: Sequence[int],
    segmento: Sequence[int],
    pool: Sequence[int],
    alvo: int,
    pick_n: int,
    contar,
    ordem: int = 0,
) -> Optional[List[int]]:
    """Monta o jogo em volta do trecho e completa sem passar da quantidade de diagonais."""
    fixos: List[int] = []
    for n in list(faltantes) + list(segmento):
        n = int(n)
        if n not in fixos:
            fixos.append(n)
    if len(fixos) > pick_n:
        return None
    reserva = [int(p) for p in pool if int(p) not in fixos]
    atual = list(fixos)
    need = pick_n - len(atual)
    if need == 1:
        achados: List[List[int]] = []
        for p in reserva:
            trial = sorted(atual + [p])
            if contar(trial) != int(alvo):
                continue
            if any(int(n) not in trial for n in segmento):
                continue
            achados.append(trial)
        if not achados:
            return None
        return achados[int(ordem) % len(achados)]
    for _ in range(need):
        melhor_p = None
        for p in reserva:
            if p in atual:
                continue
            trial = atual + [p]
            nq = contar(trial)
            dist = abs(nq - int(alvo))
            if melhor_p is None or (dist, p) < melhor_p[0]:
                melhor_p = ((dist, p), p)
        if not melhor_p:
            return None
        atual.append(melhor_p[1])
    trial = _aproximar_diagonais(atual, fixos, alvo, reserva, contar, [list(segmento)], pick_n)
    if len(trial) != pick_n or contar(trial) != int(alvo):
        return None
    if any(int(n) not in trial for n in segmento):
        return None
    return sorted(trial)


def _aposta_aceitavel(
    dezenas: Sequence[int],
    pick_n: int,
    *,
    hist: Set[Tuple[int, ...]],
    estrut_cnt: Counter,
    limiar_estrut: int,
    bloquear_exato: bool,
    filtro_estrutura: bool,
    dmin: int,
    dmax: int,
) -> bool:
    nums = [int(x) for x in dezenas]
    if len(nums) != pick_n or len(set(nums)) != pick_n:
        return False
    if any(n < dmin or n > dmax for n in nums):
        return False
    chave = tuple(sorted(nums))
    if bloquear_exato and chave in hist:
        return False
    if filtro_estrutura and estrut_cnt.get(_padrao_estrutura(nums), 0) >= limiar_estrut:
        return False
    return True


def gerar_apostas_estrategia(
    modality_key: str,
    *,
    quantidade: int = 10,
    pick: Optional[int] = None,
    desdobramento: Any = "auto",
    k_repeticao: Optional[int] = None,
    bloquear_exato: bool = True,
    filtro_estrutura: bool = True,
    usar_evolucao: bool = True,
    n_diagonais: Optional[int] = None,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Observa novas + evolução + repetidas + progresso e monta apostas com
    núcleo compartilhado e variação controlada (não prevê o próximo sorteio).
    """
    spec = get_ciclo_spec(modality_key)
    if not spec.enabled:
        return {"ok": False, "erro": f"Ciclo não habilitado para {spec.nome}."}

    raw_desdob = desdobramento
    auto_desdob = False
    if raw_desdob is None or str(raw_desdob).strip().lower() in ("", "auto", "evolucao", "evolução"):
        auto_desdob = True
        k_fixo: Optional[int] = None
    else:
        k_fixo = int(raw_desdob)
        if k_fixo == 7:
            return {"ok": False, "erro": "Desdobramento 7-em-7 está bloqueado (jogo só de novas)."}
        if k_fixo not in (1,) + DESDOBRAMENTO_OK:
            return {"ok": False, "erro": f"Desdobramento inválido ({k_fixo}). Use 1–6 ou auto."}

    ctx = CicloInteligenciaService.contexto_estrategia(modality_key)
    if not ctx or not ctx.get("sucesso"):
        return {"ok": False, "erro": "Contexto de estratégia indisponível."}

    pendentes = sorted(int(x) for x in (ctx.get("dezenas_pendentes") or []))
    saidas = [int(x) for x in (ctx.get("dezenas_saidas") or [])]
    ultimo = list(ctx.get("ultimo_sorteio") or [])
    fase = ctx.get("fase") or {}
    rep = ctx.get("repeticoes_historicas") or {}
    scores_falt = ctx.get("scores_faltantes") or []
    est = ctx.get("estado_atual") or {}
    numero_ciclo = ctx.get("numero_ciclo") or est.get("numero_ciclo")
    evo = ctx.get("evolucao_ciclo") or CicloInteligenciaService.analisar_evolucao_ciclo(modality_key) or {}

    pick_n = int(pick if pick is not None else spec.pick_default)
    pick_n = max(spec.pick_min, min(spec.pick_max, pick_n))
    qtd = max(1, min(int(quantidade or 10), 80))
    n_pend = len(pendentes)

    if n_pend < 1:
        return {"ok": False, "erro": "Não há faltantes neste ciclo."}
    if len(saidas) < 1:
        return {"ok": False, "erro": "Ciclo sem dezenas já saídas para completar as apostas."}

    rng = random.Random(seed)

    # Pool de completar = já saídas, ordenadas por atraso (mais atrasadas primeiro)
    atrasadas = _atraso_saidas(modality_key, saidas)
    plano = None
    if usar_evolucao:
        plano = CicloInteligenciaService.montar_estrategia_ciclo(
            modality_key, quantidade=qtd, pick=pick_n,
        )

    scores_map = {int(s["dezena"]): float(s.get("score") or 0) for s in scores_falt}
    for d in pendentes:
        scores_map.setdefault(int(d), 50.0)
    # Atraso das faltantes também ajuda a priorizar quais combos tentar primeiro
    af = CicloInteligenciaService._atraso_e_frequencia(modality_key)
    for d in pendentes:
        scores_map[int(d)] = float(scores_map.get(int(d), 50)) + min(15, int(af.get(d, {}).get("atraso", 0)))
    if usar_evolucao and evo.get("faixa_nova_prioritaria"):
        fp = evo["faixa_nova_prioritaria"]
        for d in pendentes:
            if CicloInteligenciaService._faixa(int(d), modality_key) == fp:
                scores_map[int(d)] = float(scores_map.get(int(d), 50)) + 8.0

    hist = _historico_exato(modality_key) if bloquear_exato else set()
    estrut_cnt = _estruturas_recentes(modality_key) if filtro_estrutura else Counter()
    limiar_estrut = max(3, int(0.12 * max(1, sum(estrut_cnt.values()))))

    # Cotas de k: plano de estágio (inclui k=0) ou mistura antiga / k fixo
    if usar_evolucao and plano and (auto_desdob or k_fixo is None):
        cotas = {int(k): int(n) for k, n in (plano.get("cotas_k") or {}).items()}
        pesos_k = {int(k): float(n) * 10.0 for k, n in cotas.items()}
        if not cotas:
            pesos_k = _pesos_k_evolucao(evo, n_pend, pick_n)
            cotas = _cotas_por_k(pesos_k, qtd)
    elif k_fixo is not None:
        k0 = max(0, min(int(k_fixo), n_pend, 6))
        if usar_evolucao and plano:
            cotas = {int(k): int(n) for k, n in (plano.get("cotas_k") or {}).items()}
            cotas[k0] = cotas.get(k0, 0) + max(1, int(qtd * 0.55))
            s = sum(cotas.values()) or 1
            cotas = {k: max(1, int(round(v * qtd / s))) for k, v in cotas.items() if k <= n_pend}
            pesos_k = {int(k): float(n) for k, n in cotas.items()}
        else:
            cotas = {k0: qtd}
            pesos_k = {k0: 100.0}
    else:
        k0 = max(1, min(int(evo.get("k_faltantes_sugerido") or 2), n_pend, 6))
        cotas = {k0: qtd}
        pesos_k = {k0: 100.0}

    k_repeticao_alvo = k_repeticao

    analisadas = 0
    eliminadas = 0
    motivos: Counter = Counter()
    candidatos: List[dict] = []
    vistos: Set[Tuple[int, ...]] = set()
    por_k_ok: Counter = Counter()

    # Garante exemplos do usuário: pelo menos 1 aposta com k=1 e k=2 se possível
    k_ds: Optional[int] = None
    k_ds_motivo = ""
    if modality_key == "diadesorte":
        k_ds, k_ds_motivo = _k_alvo_diadesorte(
            n_pend, pick_n, len(atrasadas), None if auto_desdob else k_fixo,
        )
        if k_ds is None:
            return {
                "ok": False,
                "erro": "Não há dezenas suficientes para fechar o jogo com as faltantes do ciclo.",
            }
        cotas = {int(k_ds): qtd}
        pesos_k = {int(k_ds): 100.0}
    elif usar_evolucao and auto_desdob:
        if 1 <= n_pend and cotas.get(1, 0) == 0 and 1 in pesos_k:
            cotas[1] = 1
        if 2 <= n_pend and cotas.get(2, 0) == 0 and 2 in pesos_k:
            cotas[2] = 1

    for k, n_alvo in sorted(cotas.items()):
        if n_alvo <= 0 or k > n_pend:
            continue
        need = pick_n - k
        if need < 0 or need > len(atrasadas):
            continue

        if modality_key == "diadesorte":
            combos = _combos_cobertura(pendentes, k, scores_map, max(n_alvo * 6, n_alvo))
            vistos_combo = set(combos)
            for extra in _limitar_combinacoes(pendentes, k, scores_map, rng):
                if extra not in vistos_combo:
                    combos.append(extra)
                    vistos_combo.add(extra)
        else:
            combos = _limitar_combinacoes(pendentes, k, scores_map, rng)
        if not combos:
            continue
        if modality_key != "diadesorte":
            combos = sorted(
                combos,
                key=lambda t: (-sum(scores_map.get(x, 0) for x in t), t),
            )

        geradas_k = 0
        for idx_combo, falt_t in enumerate(combos):
            if geradas_k >= n_alvo and len(candidatos) >= qtd * 3:
                break
            if len(candidatos) >= MAX_SCORE_POOL:
                break

            falt = list(falt_t)
            if modality_key == "diadesorte":
                n_var = max(qtd * 3, 24)
            else:
                n_var = 3 if plano else 1
            for variante in range(n_var):
                analisadas += 1
                if modality_key == "diadesorte" and atrasadas:
                    shift = variante % len(atrasadas)
                    atrasadas_var = atrasadas[shift:] + atrasadas[:shift]
                else:
                    atrasadas_var = atrasadas
                if plano:
                    jogo = _completar_com_plano(
                        falt, plano, pick_n, idx_combo + variante + k, atrasadas_var,
                    )
                else:
                    jogo = _completar_com_atrasadas(falt, atrasadas_var, pick_n)
                if modality_key == "diadesorte" and atrasadas_var:
                    livres = [d for d in jogo if d not in set(falt)]
                    if livres:
                        drop = livres[variante % len(livres)]
                        for p in atrasadas_var:
                            if p in jogo or p in falt:
                                continue
                            trial = sorted((set(jogo) - {drop}) | {p})
                            if len(trial) == pick_n:
                                jogo = trial
                                break
                if len(jogo) != pick_n:
                    motivos["tamanho"] += 1
                    eliminadas += 1
                    continue

                chave = _chave(jogo)
                if chave in vistos:
                    motivos["duplicata"] += 1
                    eliminadas += 1
                    continue
                vistos.add(chave)

                if bloquear_exato and chave in hist:
                    motivos["historico_exato"] += 1
                    eliminadas += 1
                    continue

                if filtro_estrutura:
                    pad = _padrao_estrutura(jogo)
                    if estrut_cnt.get(pad, 0) >= limiar_estrut:
                        motivos["estrutura_saturada"] += 1
                        eliminadas += 1
                        continue

                complemento = [d for d in jogo if d not in set(falt)]
                sc = _score_jogo(
                    jogo, falt, scores_map, ultimo,
                    evo=evo if usar_evolucao else None,
                    modality_key=modality_key,
                )
                if atrasadas:
                    top_atr = set(atrasadas[: max(1, pick_n - k)])
                    sc += 2.0 * len(top_atr & set(complemento))
                if plano:
                    pesos_r = plano.get("pesos_repeticao") or {}
                    sc += sum(float(pesos_r.get(d, 0) or 0) for d in jogo) / 3.0
                    nucleo_set = set(plano.get("nucleo_ancoras") or [])
                    sc += 1.8 * len(nucleo_set & set(jogo))

                candidatos.append({
                    "dezenas": jogo,
                    "faltantes": sorted(falt),
                    "novas_ciclo": sorted(falt),
                    "repetentes": sorted(complemento),
                    "ja_saidas": sorted(complemento),
                    "atrasadas": sorted(complemento),
                    "k_desdobramento": k,
                    "k_faltantes": k,
                    "k_repeticao": len(complemento),
                    "qtd_evolucao_alvo": k,
                    "soma": sum(jogo),
                    "pares": sum(1 for d in jogo if d % 2 == 0),
                    "score": round(sc, 2),
                    "digitos_distintos": len({d % 10 for d in jogo}),
                    "alinhado_evolucao": bool(
                        usar_evolucao and k == int(evo.get("k_faltantes_sugerido") or -1)
                    ),
                    "modo_completacao": "plano" if plano else "atrasadas",
                })
                por_k_ok[k] += 1
                geradas_k += 1
                if geradas_k >= max(n_alvo * 4, n_alvo + 2):
                    break
            if geradas_k >= max(n_alvo * 4, n_alvo + 2):
                break

    alvo_diag: Optional[int] = None
    diag_info: Dict[str, Any] = {}
    try:
        diag_info = CicloInteligenciaService._diagonais_historico(modality_key) or {}
    except Exception:
        diag_info = {}
    bruto = "" if n_diagonais is None else str(n_diagonais).strip().lower()
    if bruto in ("", "auto", "costume", "none"):
        alvo_diag = int(diag_info.get("quantidade_costumeira", diag_info.get("sugerida", 1)) or 0)
    else:
        try:
            alvo_diag = int(n_diagonais)
        except (TypeError, ValueError):
            alvo_diag = int(diag_info.get("sugerida") or 0)
    alvo_diag = max(0, min(4, int(alvo_diag)))
    contar_diag = None
    segmentos_diag: List[List[int]] = []
    if candidatos:
        contar_diag = _contador_diagonais(spec.dezena_min, spec.dezena_max)
        segmentos_diag = [
            [int(x) for x in (s.get("nums") or [])]
            for s in (diag_info.get("ranking") or [])
            if s.get("nums")
        ]
        for c in candidatos:
            nd = contar_diag(c["dezenas"])
            c["n_diagonais"] = nd
            c["score"] = round(float(c["score"]) + (40.0 if nd == alvo_diag else -6.0 * abs(nd - alvo_diag)), 2)

    # Seleção final: respeita cotas por k (mistura realista)
    finais: List[dict] = []
    por_bucket: Dict[int, List[dict]] = {}
    for c in candidatos:
        por_bucket.setdefault(int(c["k_faltantes"]), []).append(c)
    for k in por_bucket:
        por_bucket[k].sort(key=lambda x: (-x["score"], x["soma"], x["dezenas"]))

    for k, n_alvo in sorted(cotas.items(), key=lambda kv: (-pesos_k.get(kv[0], 0), kv[0])):
        bucket = por_bucket.get(k) or []
        for item in _escolher_diversos(bucket, n_alvo):
            if len(finais) >= qtd:
                break
            if _chave(item["dezenas"]) in {_chave(a["dezenas"]) for a in finais}:
                continue
            finais.append(item)
        if len(finais) >= qtd:
            break

    # Completa se cotas não encheram
    if len(finais) < qtd:
        usados_ch = {_chave(a["dezenas"]) for a in finais}
        resto = [
            c for c in sorted(candidatos, key=lambda x: (-x["score"], x["soma"]))
            if _chave(c["dezenas"]) not in usados_ch
        ]
        for c in resto:
            if len(finais) >= qtd:
                break
            finais.append(c)

    if alvo_diag is not None and contar_diag is not None:
        from analise_inteligentes_diadesorte.diagonais_volante import diagonais_na_aposta

        duplas_top, trinca_top = _segmentos_top(diag_info) if modality_key == "diadesorte" else ([], None)
        if modality_key == "diadesorte":
            pool_diag = list(atrasadas)
            segmentos_diag = duplas_top or segmentos_diag
        else:
            pool_diag = list(dict.fromkeys(
                list(atrasadas) + [n for seg in segmentos_diag for n in seg]
            ))
        for idx_item, item in enumerate(finais):
            antes = list(item["dezenas"])
            falt_set = set(int(x) for x in (item.get("faltantes") or []))
            if modality_key == "diadesorte":
                preferido = None
                if alvo_diag >= 1 and duplas_top:
                    preferido = duplas_top[idx_item % len(duplas_top)]
                usar_trinca = bool(alvo_diag >= 1 and idx_item % 8 == 0 and trinca_top)
                novo = None
                usados_finais = {_chave(a["dezenas"]) for a in finais[:idx_item]}
                for salto in range(8):
                    cand = None
                    if usar_trinca and trinca_top and all(n in falt_set or n in pool_diag for n in trinca_top):
                        cand = _fechar_com_segmento(
                            list(falt_set), trinca_top, pool_diag, alvo_diag, pick_n, contar_diag,
                            ordem=idx_item + salto,
                        )
                    if cand is None and preferido and all(n in falt_set or n in pool_diag for n in preferido):
                        cand = _fechar_com_segmento(
                            list(falt_set), preferido, pool_diag, alvo_diag, pick_n, contar_diag,
                            ordem=idx_item + salto,
                        )
                    if not cand or _chave(cand) in usados_finais:
                        continue
                    if _aposta_aceitavel(
                        cand, pick_n,
                        hist=hist, estrut_cnt=estrut_cnt, limiar_estrut=limiar_estrut,
                        bloquear_exato=bloquear_exato, filtro_estrutura=filtro_estrutura,
                        dmin=spec.dezena_min, dmax=spec.dezena_max,
                    ) and falt_set.issubset(cand):
                        novo = cand
                        break
                if novo is None:
                    novo = _aproximar_diagonais(
                        antes, list(falt_set), alvo_diag, pool_diag, contar_diag,
                        segmentos_diag, pick_n,
                    )
                if not _aposta_aceitavel(
                    novo, pick_n,
                    hist=hist, estrut_cnt=estrut_cnt, limiar_estrut=limiar_estrut,
                    bloquear_exato=bloquear_exato, filtro_estrutura=filtro_estrutura,
                    dmin=spec.dezena_min, dmax=spec.dezena_max,
                ) or not falt_set.issubset(novo):
                    novo = antes
            else:
                novo = _aproximar_diagonais(
                    antes, list(falt_set), alvo_diag, pool_diag, contar_diag,
                    segmentos_diag, pick_n,
                )
            diags = diagonais_na_aposta(novo, dmin=spec.dezena_min, dmax=spec.dezena_max)
            item["dezenas"] = novo
            item["repetentes"] = sorted(d for d in novo if d not in falt_set)
            item["ja_saidas"] = item["repetentes"]
            item["atrasadas"] = item["repetentes"]
            item["n_diagonais"] = len(diags)
            item["diagonais"] = diags
            item["soma"] = sum(novo)
            item["pares"] = sum(1 for d in novo if d % 2 == 0)
            item["diagonais_alvo"] = alvo_diag
            item["diagonal_atingida"] = len(diags) == alvo_diag

    aviso_fase = None
    if fase.get("fase") == "andamento" and not fase.get("estrategia_recomendada"):
        aviso_fase = (
            "Fase intermediária do ciclo: geração disponível com aviso — "
            "preferível no início ou na finalização."
        )
    dist_txt = ", ".join(
        f"k={k}:{n}" for k, n in sorted(Counter(a["k_faltantes"] for a in finais).items())
    )
    aviso_evo = None
    if modality_key == "diadesorte":
        aviso_evo = None
    elif usar_evolucao and (plano or evo):
        if plano:
            aviso_evo = plano.get("leitura_curta")
        else:
            aviso_evo = (
                f"Evolução ciclo #{evo.get('numero_ciclo')}: replica Qtd. Evolução "
                f"(tendência {evo.get('tendencia')}, sugerido {evo.get('k_faltantes_sugerido')}). "
                f"Mistura gerada: {dist_txt or '—'}."
            )

    como = _como_influenciou(finais, plano) if plano else ""
    relatorio = {
        "ciclo": numero_ciclo,
        "fase": fase.get("fase"),
        "fase_label": fase.get("label"),
        "sorteadas_ciclo": fase.get("dezenas_saidas_ciclo"),
        "faltantes": n_pend,
        "faltantes_lista": pendentes,
        "k_desdobramento": "auto" if auto_desdob else k_fixo,
        "k_faltantes_regra": k_ds,
        "k_faltantes_motivo": k_ds_motivo or None,
        "k_repeticao": k_repeticao_alvo,
        "n_diagonais": alvo_diag,
        "diagonais_leitura": diag_info.get("leitura"),
        "diagonais_pct_tres_ou_mais": diag_info.get("pct_tres_ou_mais"),
        "diagonais_acertadas": (
            sum(1 for a in finais if int(a.get("n_diagonais") or 0) == alvo_diag)
            if alvo_diag is not None else None
        ),
        "completacao": "plano" if plano else "atrasadas",
        "usar_evolucao": usar_evolucao,
        "cotas_k": cotas,
        "pesos_k": {str(k): round(v, 1) for k, v in pesos_k.items()},
        "estrategia_ciclo": {
            "estagio": (plano or {}).get("estagio"),
            "tendencia": (plano or {}).get("tendencia_evolucao") or evo.get("tendencia"),
            "k_esperado": (plano or {}).get("k_esperado") or evo.get("k_faltantes_sugerido"),
            "nucleo": (plano or {}).get("nucleo_ancoras") or [],
            "aliviar": (plano or {}).get("repetidas_aliviar") or [],
            "ativas": (plano or {}).get("repetidas_ativas") or [],
            "leitura_curta": (plano or {}).get("leitura_curta") or aviso_evo,
            "aviso_nao_previsao": (plano or {}).get("aviso_nao_previsao"),
        } if plano or evo else {},
        "como_influenciou": como,
        "evolucao": {
            "dominante": evo.get("dominante"),
            "tendencia": (plano or {}).get("tendencia_evolucao") or evo.get("tendencia"),
            "media_recente": evo.get("media_recente"),
            "k_sugerido": evo.get("k_faltantes_sugerido"),
            "distribuicao_qtd_pct": evo.get("distribuicao_qtd_pct"),
            "distribuicao_recente_pct": evo.get("distribuicao_recente_pct"),
            "novas_recentes": evo.get("novas_recentes"),
            "progresso": evo.get("progresso_pct"),
            "mistura_gerada": dict(Counter(a["k_faltantes"] for a in finais)),
            "media_k_gerado": round(
                sum(a["k_faltantes"] for a in finais) / len(finais), 2
            ) if finais else 0,
        },
        "filtros": {
            "bloquear_exato": bloquear_exato,
            "filtro_estrutura": filtro_estrutura,
        },
        "analisadas": analisadas,
        "eliminadas": eliminadas,
        "geradas": len(finais),
        "motivos_eliminacao": dict(motivos),
        "cenario_repeticao": rep.get("cenario_dominante"),
    }

    avisos = [a for a in (aviso_fase, aviso_evo) if a]
    if modality_key == "diadesorte" and k_ds is not None:
        if k_ds_motivo == "auto":
            avisos.append(f"Cada aposta leva {k_ds} dezena(s) que ainda faltam no ciclo.")
        elif k_ds_motivo == "excecao":
            avisos.append(
                f"A faixa de 2 a 4 faltantes não coube: cada aposta ficou com {k_ds}."
            )
        elif k_ds_motivo == "ajustado":
            avisos.append(
                f"O desdobramento foi ajustado para {k_ds} faltante(s) para fechar o jogo."
            )
        elif k_ds_motivo == "fixo":
            avisos.append(f"Cada aposta leva {k_ds} faltante(s), como marcado no Desdobramento.")
    if len(finais) < qtd:
        avisos.append(f"Geradas {len(finais)} de {qtd} após filtros (qualidade > volume).")

    return {
        "ok": True,
        "sucesso": True,
        "estrategia": "estrategia_ciclo",
        "apostas": finais,
        "geradas": len(finais),
        "aviso": " · ".join(avisos) if avisos else None,
        "relatorio": relatorio,
        "indicadores": {
            "ciclo": numero_ciclo,
            "fase": fase,
            "classificacao": est.get("classificacao"),
            "pressao": est.get("pressao"),
            "faltando": n_pend,
            "pendentes": pendentes,
            "atrasadas_top": atrasadas[:10],
            "ultimo_sorteio": ultimo,
            "repeticoes": rep,
            "evolucao_ciclo": evo,
            "estrategia_ciclo": plano,
            "scores_faltantes": scores_falt[:15],
            "cotas_k": cotas,
        },
    }


def contexto_estrategia_geracao(modality_key: str) -> Dict[str, Any]:
    ctx = CicloInteligenciaService.contexto_estrategia(modality_key)
    if not ctx or not ctx.get("sucesso"):
        return {"ok": False, "erro": "Contexto de estratégia indisponível."}
    return {
        "ok": True,
        **ctx,
        "desdobramento_default": "auto",
        "desdobramento_opcoes": [1, 2, 3, 4, 5, 6],
        "desdobramento_bloqueado": [7],
        "usar_evolucao_default": True,
        "modo_completacao": "plano",
        "leitura_geracao": (
            "Observa novas, evolução, repetidas (com sequência) e progresso; "
            "monta núcleo + variação controlada. Não prevê o próximo sorteio."
        ),
    }
