# -*- coding: utf-8 -*-
"""Motor compartilhado — Construtor de Construções."""
from __future__ import annotations

import itertools
import math
import random
from collections import Counter
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

FAIXA_LIMITES_PADRAO = {
    "baixas": (1, 10),
    "medias": (11, 20),
    "altas": (21, 31),
}

FAIXA_LIMITES = FAIXA_LIMITES_PADRAO

# Ordem canônica das faixas (isolada é opcional — Dia de Sorte: 31)
FAIXAS_BASE = ("baixas", "medias", "altas")
FAIXAS_TODAS = ("baixas", "medias", "altas", "isolada")

QTD_APOSTAS_FIXA = 10


def estrategias_ui(faixas: Dict[str, str]) -> List[Dict[str, str]]:
    b, m, a = faixas.get("baixas", ""), faixas.get("medias", ""), faixas.get("altas", "")
    return [
        {"id": "automatica", "label": "Automática", "desc": "Diversifica com padrões históricos + distribuição do pool"},
        {"id": "balanceada", "label": "Balanceada", "desc": "Distribui equilibrado entre B/M/A"},
        {"id": "somente_baixas", "label": "Somente Baixas", "desc": f"Apenas dezenas {b}"},
        {"id": "somente_medias", "label": "Somente Médias", "desc": f"Apenas dezenas {m}"},
        {"id": "somente_altas", "label": "Somente Altas", "desc": f"Apenas dezenas {a}"},
        {"id": "baixas_medias", "label": "Baixas + Médias", "desc": "Exclui altas"},
        {"id": "medias_altas", "label": "Médias + Altas", "desc": "Exclui baixas"},
        {"id": "baixas_altas", "label": "Baixas + Altas", "desc": "Exclui médias"},
        {"id": "personalizada", "label": "Personalizada", "desc": "Você define B + M + A"},
        {"id": "conforme_comportamento", "label": "Conforme o Comportamento", "desc": "Usa padrão histórico da análise"},
    ]


ESTRATEGIAS = estrategias_ui({"baixas": "01–10", "medias": "11–20", "altas": "21–31"})


def _faixas_ativas(limites: Optional[Dict[str, Tuple[int, int]]] = None) -> Tuple[str, ...]:
    lim = limites or FAIXA_LIMITES
    return tuple(f for f in FAIXAS_TODAS if f in lim)


def faixa_dezena(d: int, limites: Optional[Dict[str, Tuple[int, int]]] = None) -> str:
    lim = limites or FAIXA_LIMITES
    if "isolada" in lim:
        lo, hi = lim["isolada"]
        if lo <= d <= hi:
            return "isolada"
    for nome in FAIXAS_BASE:
        if nome not in lim:
            continue
        lo, hi = lim[nome]
        if lo <= d <= hi:
            return nome
    if d < lim.get("baixas", (1, 10))[0]:
        return "baixas"
    return "altas"


def pool_por_faixa(
    pool: List[int],
    limites: Optional[Dict[str, Tuple[int, int]]] = None,
) -> Dict[str, List[int]]:
    out = {f: [] for f in _faixas_ativas(limites)}
    for f in FAIXAS_BASE:
        out.setdefault(f, [])
    for d in pool:
        f = faixa_dezena(d, limites)
        out.setdefault(f, []).append(d)
    for k in out:
        out[k].sort()
    return out


def padrao_inicial_de(dezenas: Sequence[int]) -> str:
    """Primeiro dígito de cada dezena em ordem crescente (ex.: 0 0 1 1 2 2 3)."""
    return " ".join(str(int(d) // 10) for d in sorted(int(x) for x in dezenas))


def pool_por_digito_inicial(pool: Sequence[int]) -> Dict[int, List[int]]:
    out: Dict[int, List[int]] = {}
    for d in sorted(set(int(x) for x in pool)):
        dig = int(d) // 10
        out.setdefault(dig, []).append(d)
    return out


def parse_padrao(padrao: str) -> List[int]:
    return [int(x) for x in str(padrao).replace(",", " ").split() if x.strip().isdigit()]


def padrao_viavel(padrao: Sequence[int], pool: Sequence[int]) -> bool:
    """Verifica se o pool consegue montar o padrão (contagem por dígito inicial)."""
    need = Counter(int(x) for x in padrao)
    disp = {dig: len(nums) for dig, nums in pool_por_digito_inicial(pool).items()}
    return all(disp.get(dig, 0) >= qtd for dig, qtd in need.items())


def _montar_por_padrao(
    pool: List[int],
    padrao: Sequence[int],
    rng: random.Random,
) -> Optional[List[int]]:
    groups = {dig: list(nums) for dig, nums in pool_por_digito_inicial(pool).items()}
    pick: List[int] = []
    for dig in padrao:
        dig = int(dig)
        cand = groups.get(dig) or []
        if not cand:
            return None
        escolha = rng.choice(cand)
        cand.remove(escolha)
        groups[dig] = cand
        pick.append(escolha)
    if len(pick) != len(padrao):
        return None
    return sorted(pick)


def selecionar_padroes_lote(
    padroes_historicos: Sequence[str],
    pool: List[int],
    k: int,
    qtd: int,
    rng: random.Random,
    padroes_evitar: Optional[Set[str]] = None,
    permitir_sinteticos: bool = True,
) -> List[List[int]]:
    """Escolhe até qtd padrões distintos viáveis (histórico primeiro, depois sintéticos)."""
    evitar = set(padroes_evitar or ())
    viaveis: List[List[int]] = []
    vistos: Set[str] = set()

    # Frequência histórica (mais comuns primeiro), com shuffle leve entre iguais
    cont = Counter(str(p).strip() for p in padroes_historicos if str(p).strip())
    ordenados = sorted(cont.keys(), key=lambda p: (-cont[p], p))
    rng.shuffle(ordenados)  # diversidade entre cliques
    ordenados.sort(key=lambda p: -cont[p])

    for pstr in ordenados:
        digs = parse_padrao(pstr)
        if len(digs) != k:
            continue
        if pstr in evitar or pstr in vistos:
            continue
        if not padrao_viavel(digs, pool):
            continue
        vistos.add(pstr)
        viaveis.append(digs)
        if len(viaveis) >= qtd:
            return viaveis

    if not permitir_sinteticos:
        return viaveis

    # Completa com padrões sintéticos derivados do pool
    grupos = pool_por_digito_inicial(pool)
    digitos_disp = [d for d, nums in grupos.items() if nums]
    if not digitos_disp:
        return viaveis
    tentativas = 0
    while len(viaveis) < qtd and tentativas < 400:
        tentativas += 1
        # amostra multiplicidades respeitando disponibilidade
        need: Dict[int, int] = {d: 0 for d in digitos_disp}
        restante = k
        ordem = list(digitos_disp)
        rng.shuffle(ordem)
        for dig in ordem:
            if restante <= 0:
                break
            max_n = min(len(grupos[dig]), restante)
            if max_n <= 0:
                continue
            # favorece espalhar, mas permite concentração
            n = rng.randint(0, max_n) if rng.random() < 0.35 else min(max_n, max(1, restante // max(1, len(ordem))))
            n = min(n, max_n, restante)
            need[dig] = n
            restante -= n
        if restante > 0:
            for dig in ordem:
                sobra = min(restante, len(grupos[dig]) - need[dig])
                if sobra > 0:
                    need[dig] += sobra
                    restante -= sobra
                if restante <= 0:
                    break
        if restante != 0 or sum(need.values()) != k:
            continue
        digs: List[int] = []
        for dig in sorted(need.keys()):
            digs.extend([dig] * need[dig])
        if len(digs) != k:
            continue
        pstr = " ".join(str(x) for x in digs)
        if pstr in vistos or pstr in evitar or not padrao_viavel(digs, pool):
            continue
        vistos.add(pstr)
        viaveis.append(digs)
    return viaveis


def distribuicao_historica_moda(
    sorteios_dezenas: List[List[int]],
    limites: Optional[Dict[str, Tuple[int, int]]] = None,
) -> Dict[str, int]:
    """Moda de contagem B/M/A(+isolada) por sorteio."""
    faixas = _faixas_ativas(limites)
    if not sorteios_dezenas:
        base = {"baixas": 2, "medias": 3, "altas": 2}
        if "isolada" in faixas:
            base["isolada"] = 0
        return base
    contadores: Dict[Tuple[int, ...], int] = {}
    for dz in sorteios_dezenas:
        pf = pool_por_faixa(dz, limites)
        chave = tuple(len(pf.get(f, [])) for f in faixas)
        contadores[chave] = contadores.get(chave, 0) + 1
    moda = max(contadores.items(), key=lambda x: x[1])[0]
    return {f: moda[i] for i, f in enumerate(faixas)}


def _dist_vazio(limites: Optional[Dict[str, Tuple[int, int]]] = None) -> Dict[str, int]:
    return {f: 0 for f in _faixas_ativas(limites)}


def _ajustar_distribuicao_total(
    dist: Dict[str, int],
    k: int,
    pool_faixas: Dict[str, List[int]],
    limites: Optional[Dict[str, Tuple[int, int]]] = None,
) -> Dict[str, int]:
    """Garante soma = k respeitando limites do pool."""
    faixas = _faixas_ativas(limites)
    out = {f: 0 for f in faixas}
    restante = k
    ordem = sorted(
        list(faixas),
        key=lambda f: len(pool_faixas.get(f, [])),
        reverse=True,
    )
    for faixa in ordem:
        max_possivel = min(len(pool_faixas.get(faixa, [])), restante)
        alvo = dist.get(faixa, 0)
        usar = min(alvo, max_possivel)
        out[faixa] = usar
        restante -= usar
    idx = 0
    while restante > 0 and ordem:
        faixa = ordem[idx % len(ordem)]
        if out[faixa] < len(pool_faixas.get(faixa, [])):
            out[faixa] += 1
            restante -= 1
        idx += 1
        if idx > 40:
            break
    return out


def calcular_distribuicao(
    estrategia: str,
    pool: List[int],
    k: int,
    personalizada: Optional[Dict[str, int]] = None,
    comportamento_moda: Optional[Dict[str, int]] = None,
    limites: Optional[Dict[str, Tuple[int, int]]] = None,
) -> Dict[str, int]:
    pf = pool_por_faixa(pool, limites)

    if estrategia == "somente_baixas":
        return _ajustar_distribuicao_total({"baixas": k}, k, pf, limites)
    if estrategia == "somente_medias":
        return _ajustar_distribuicao_total({"medias": k}, k, pf, limites)
    if estrategia == "somente_altas":
        # Altas + isolada (31) quando existir
        alvo = {"altas": k, "isolada": 0}
        return _ajustar_distribuicao_total(alvo, k, pf, limites)
    if estrategia == "baixas_medias":
        return _distribuir_duas_faixas(k, pf, "baixas", "medias", limites)
    if estrategia == "medias_altas":
        return _distribuir_duas_faixas(k, pf, "medias", "altas", limites)
    if estrategia == "baixas_altas":
        return _distribuir_duas_faixas(k, pf, "baixas", "altas", limites)
    if estrategia == "personalizada" and personalizada:
        return _ajustar_distribuicao_total(personalizada, k, pf, limites)
    if estrategia == "conforme_comportamento":
        moda = comportamento_moda or {"baixas": 2, "medias": 3, "altas": 2}
        return _ajustar_distribuicao_total(moda, k, pf, limites)
    if estrategia == "balanceada":
        return _distribuir_balanceado(k, pf, limites)
    return _distribuir_proporcional(k, pf, limites)


def _distribuir_duas_faixas(
    k: int,
    pf: Dict[str, List[int]],
    f1: str,
    f2: str,
    limites: Optional[Dict[str, Tuple[int, int]]] = None,
) -> Dict[str, int]:
    out = _dist_vazio(limites)
    # Para medias_altas / baixas_altas, soma isolada às altas se existir
    pool_f2 = list(pf.get(f2, []))
    if f2 == "altas" and pf.get("isolada"):
        # Conta isolada como extensão de altas na disponibilidade
        n_iso = len(pf["isolada"])
    else:
        n_iso = 0
    total_disp = len(pf.get(f1, [])) + len(pool_f2) + (n_iso if f2 == "altas" else 0)
    if total_disp == 0:
        return out
    p1 = len(pf.get(f1, [])) / total_disp
    n1 = min(len(pf.get(f1, [])), round(k * p1))
    n2_alvo = k - n1
    n2 = min(len(pool_f2), n2_alvo)
    n_iso_usar = 0
    if f2 == "altas" and n2 + n_iso_usar < n2_alvo and n_iso:
        n_iso_usar = min(n_iso, n2_alvo - n2)
    if n1 + n2 + n_iso_usar < k:
        sobra = k - n1 - n2 - n_iso_usar
        if len(pf.get(f1, [])) - n1 >= sobra:
            n1 += sobra
        elif len(pool_f2) - n2 >= sobra:
            n2 += sobra
        elif n_iso - n_iso_usar >= sobra:
            n_iso_usar += sobra
    out[f1] = n1
    out[f2] = n2
    if "isolada" in out:
        out["isolada"] = n_iso_usar
    return out


def _distribuir_balanceado(
    k: int,
    pf: Dict[str, List[int]],
    limites: Optional[Dict[str, Tuple[int, int]]] = None,
) -> Dict[str, int]:
    faixas = _faixas_ativas(limites)
    faixas_ativas = [f for f in faixas if pf.get(f)]
    if not faixas_ativas:
        return _dist_vazio(limites)
    base = k // len(faixas_ativas)
    sobra = k % len(faixas_ativas)
    out = _dist_vazio(limites)
    for i, f in enumerate(faixas_ativas):
        out[f] = min(len(pf[f]), base + (1 if i < sobra else 0))
    return _ajustar_distribuicao_total(out, k, pf, limites)


def _distribuir_proporcional(
    k: int,
    pf: Dict[str, List[int]],
    limites: Optional[Dict[str, Tuple[int, int]]] = None,
) -> Dict[str, int]:
    faixas = _faixas_ativas(limites)
    total = sum(len(pf.get(f, [])) for f in faixas)
    if total == 0:
        return _dist_vazio(limites)
    dist = {}
    for f in faixas:
        dist[f] = round(k * len(pf.get(f, [])) / total) if pf.get(f) else 0
    return _ajustar_distribuicao_total(dist, k, pf, limites)


def _max_apostas_unicas(
    pool: List[int],
    dist: Dict[str, int],
    limites: Optional[Dict[str, Tuple[int, int]]] = None,
) -> int:
    pf = pool_por_faixa(pool, limites)
    ways = 1
    for faixa in _faixas_ativas(limites):
        n = dist.get(faixa, 0)
        if n <= 0:
            continue
        disp = len(pf.get(faixa, []))
        if disp < n:
            return 0
        ways *= math.comb(disp, n)
        if ways >= QTD_APOSTAS_FIXA * 100:
            return QTD_APOSTAS_FIXA * 100
    return ways


def validar_estrategia(
    estrategia: str,
    pool: List[int],
    k: int,
    personalizada: Optional[Dict[str, int]] = None,
    limites: Optional[Dict[str, Tuple[int, int]]] = None,
    quantidade: int = QTD_APOSTAS_FIXA,
) -> Tuple[bool, str, Optional[Dict[str, int]]]:
    qtd_alvo = max(1, int(quantidade or QTD_APOSTAS_FIXA))
    if len(pool) < k:
        return False, f"Conjunto-base precisa de pelo menos {k} dezenas.", None
    pf = pool_por_faixa(pool, limites)

    if estrategia == "somente_baixas" and len(pf.get("baixas", [])) < k:
        return False, f"Somente {len(pf.get('baixas', []))} baixas no conjunto-base; aposta exige {k}.", None
    if estrategia == "somente_medias" and len(pf.get("medias", [])) < k:
        return False, f"Somente {len(pf.get('medias', []))} médias no conjunto-base; aposta exige {k}.", None
    if estrategia == "somente_altas":
        n_alt = len(pf.get("altas", [])) + len(pf.get("isolada", []))
        if n_alt < k:
            return False, f"Somente {n_alt} altas(+31) no conjunto-base; aposta exige {k}.", None
    if estrategia == "baixas_medias" and len(pf.get("baixas", [])) + len(pf.get("medias", [])) < k:
        return False, "Baixas + Médias insuficientes no conjunto-base.", None
    if estrategia == "medias_altas":
        if len(pf.get("medias", [])) + len(pf.get("altas", [])) + len(pf.get("isolada", [])) < k:
            return False, "Médias + Altas insuficientes no conjunto-base.", None
    if estrategia == "baixas_altas":
        if len(pf.get("baixas", [])) + len(pf.get("altas", [])) + len(pf.get("isolada", [])) < k:
            return False, "Baixas + Altas insuficientes no conjunto-base.", None
    if estrategia == "personalizada" and personalizada:
        soma = sum(personalizada.get(f, 0) for f in FAIXAS_BASE)
        if soma != k:
            return False, f"Personalizada deve somar {k} (atual: {soma}).", None
        for f in FAIXAS_BASE:
            ped = personalizada.get(f, 0)
            disp = len(pf.get(f, []))
            if f == "altas":
                disp += len(pf.get("isolada", []))
            if ped > disp:
                return False, f"Faixa {f}: pedido {ped}, disponível {disp}.", None

    dist = calcular_distribuicao(
        estrategia, pool, k, personalizada, limites=limites
    )
    total_dist = sum(dist.values())
    if total_dist != k:
        return False, "Não foi possível montar distribuição válida com este conjunto-base.", dist
    for f in _faixas_ativas(limites):
        if dist.get(f, 0) > len(pf.get(f, [])):
            return False, f"Distribuição exige {dist[f]} {f}, mas o pool tem {len(pf.get(f, []))}.", dist
    max_unicas = _max_apostas_unicas(pool, dist, limites)
    if max_unicas < qtd_alvo:
        return False, (
            f"Esta estratégia permite no máximo {max_unicas} apostas distintas; "
            f"são necessárias {qtd_alvo}. Amplie o conjunto-base ou mude a estratégia."
        ), dist
    return True, "", dist


def _montar_aposta(
    pool: List[int],
    dist: Dict[str, int],
    rng: random.Random,
    limites: Optional[Dict[str, Tuple[int, int]]] = None,
) -> Optional[List[int]]:
    pf = pool_por_faixa(pool, limites)
    pick: List[int] = []
    for faixa in _faixas_ativas(limites):
        n = dist.get(faixa, 0)
        if n <= 0:
            continue
        disp = list(pf.get(faixa, []))
        # Personalizada/somente_altas: altas podem consumir isolada se faltar
        if faixa == "altas" and len(disp) < n and pf.get("isolada"):
            # só se isolada não foi pedida na dist
            if dist.get("isolada", 0) == 0:
                disp = disp + list(pf["isolada"])
        if len(disp) < n:
            return None
        pick.extend(rng.sample(disp, n))
    if len(pick) != sum(dist.values()):
        return None
    # Dedup caso altas+isolada tenham overlapped
    if len(set(pick)) != len(pick):
        return None
    return sorted(pick)


def _pares_aposta(aposta: List[int]) -> Set[Tuple[int, int]]:
    return set(itertools.combinations(sorted(aposta), 2))


def _jaccard(a: Set[int], b: Set[int]) -> float:
    if not a and not b:
        return 0.0
    u = a | b
    return len(a & b) / len(u) if u else 0.0


def calcular_similaridade(
    apostas_a: List[List[int]],
    apostas_b: List[List[int]],
) -> Dict[str, float]:
    """Retorna similaridade 0–1 e diferença percentual."""
    if not apostas_a or not apostas_b:
        return {"similaridade": 0.0, "diferenca_pct": 100.0}

    sets_a = [frozenset(a) for a in apostas_a]
    sets_b = [frozenset(b) for b in apostas_b]
    exact = len(set(sets_a) & set(sets_b))
    exact_sim = exact / max(len(sets_a), len(sets_b))

    all_a: Set[int] = set()
    all_b: Set[int] = set()
    for s in sets_a:
        all_a |= set(s)
    for s in sets_b:
        all_b |= set(s)
    uniao = all_a | all_b
    jaccard = len(all_a & all_b) / len(uniao) if uniao else 0.0

    pares_a: Set[Tuple[int, int]] = set()
    pares_b: Set[Tuple[int, int]] = set()
    for a in apostas_a:
        pares_a |= _pares_aposta(a)
    for b in apostas_b:
        pares_b |= _pares_aposta(b)
    uniao_p = pares_a | pares_b
    pair_sim = len(pares_a & pares_b) / len(uniao_p) if uniao_p else 0.0

    similaridade = 0.5 * exact_sim + 0.3 * jaccard + 0.2 * pair_sim
    return {
        "similaridade": round(similaridade, 4),
        "diferenca_pct": round((1 - similaridade) * 100, 1),
        "apostas_iguais": exact,
    }


def _aposta_ok_diversidade(
    ap: List[int],
    usadas: Set[frozenset],
    padroes_usados: Set[str],
    historico_sorteados: Optional[Set[frozenset]],
    apostas_excluidas: Optional[Set[frozenset]],
    jaccard_max_lote: float,
    apostas_lote: List[List[int]],
    exigir_padrao_distinto: bool,
) -> bool:
    chave = frozenset(ap)
    if chave in usadas:
        return False
    if apostas_excluidas and chave in apostas_excluidas:
        return False
    if historico_sorteados and chave in historico_sorteados:
        return False
    pstr = padrao_inicial_de(ap)
    if exigir_padrao_distinto and pstr in padroes_usados and len(padroes_usados) < QTD_APOSTAS_FIXA:
        # permite repetir padrão só se já esgotou diversidade possível
        pass  # checked by caller with soft flag
    sa = set(ap)
    for outra in apostas_lote:
        if _jaccard(sa, set(outra)) > jaccard_max_lote:
            return False
    return True


def gerar_construcao(
    pool: List[int],
    k: int,
    estrategia: str,
    *,
    personalizada: Optional[Dict[str, int]] = None,
    comportamento_moda: Optional[Dict[str, int]] = None,
    construcoes_anteriores: Optional[List[List[List[int]]]] = None,
    similaridade_max: float = 0.20,
    seed: Optional[int] = None,
    max_tentativas: int = 500,
    limites: Optional[Dict[str, Tuple[int, int]]] = None,
    historico_sorteados: Optional[Set[frozenset]] = None,
    apostas_excluidas: Optional[Set[frozenset]] = None,
    padroes_historicos: Optional[List[str]] = None,
    padroes_selecionados: Optional[List[str]] = None,
    jaccard_max_lote: float = 0.85,
    quantidade: int = QTD_APOSTAS_FIXA,
) -> Dict[str, Any]:
    """
    Gera N apostas distintas (padrão 10) com:
    - rejeição de jogos já sorteados (historico_sorteados);
    - rejeição de apostas já usadas na sessão (apostas_excluidas);
    - diversidade de padrão inicial dentro do lote (quando possível);
    - similaridade controlada vs construções anteriores da sessão.
    - padroes_selecionados: força uso dos padrões da análise Padrões II (1 ou mais).
    """
    qtd_alvo = max(1, int(quantidade or QTD_APOSTAS_FIXA))
    pool = sorted(set(int(x) for x in pool))
    ok, msg, dist = validar_estrategia(
        estrategia, pool, k, personalizada, limites=limites, quantidade=qtd_alvo
    )
    if not ok:
        return {"sucesso": False, "erro": msg}

    rng = random.Random(seed)
    construcoes_anteriores = construcoes_anteriores or []
    selecionados = [
        " ".join(str(x) for x in parse_padrao(p))
        for p in (padroes_selecionados or [])
        if parse_padrao(p)
    ]
    # remove vazios / inválidos
    selecionados = [p for p in selecionados if len(parse_padrao(p)) == k]
    padroes_hist = list(selecionados) if selecionados else list(padroes_historicos or [])
    usar_padroes = (
        bool(selecionados)
        or (estrategia in ("automatica", "balanceada", "conforme_comportamento") and k >= 5)
    )

    # Padrões já usados em construções anteriores da sessão
    padroes_evitar: Set[str] = set()
    for ant in construcoes_anteriores:
        for ap in ant:
            padroes_evitar.add(padrao_inicial_de(ap))

    melhor: Optional[Dict[str, Any]] = None
    melhor_diff = -1.0
    melhor_score = -1.0

    for tentativa in range(max_tentativas):
        apostas: List[List[int]] = []
        usadas: Set[frozenset] = set()
        padroes_usados: Set[str] = set()
        falhou = False

        alvos_padrao: List[List[int]] = []
        if usar_padroes:
            if selecionados:
                # Cicla pelos padrões escolhidos na análise (Padrões II)
                for i in range(qtd_alvo):
                    pstr = selecionados[i % len(selecionados)]
                    digs = parse_padrao(pstr)
                    if padrao_viavel(digs, pool):
                        alvos_padrao.append(digs)
                if not alvos_padrao:
                    return {
                        "sucesso": False,
                        "erro": (
                            "Nenhum dos padrões selecionados é viável com este conjunto-base. "
                            "Amplie o pool ou escolha outros padrões."
                        ),
                    }
            else:
                alvos_padrao = selecionar_padroes_lote(
                    padroes_hist, pool, k, qtd_alvo, rng, padroes_evitar
                )

        for i in range(qtd_alvo):
            ok_ap = False
            alvo = alvos_padrao[i] if i < len(alvos_padrao) else None
            for _try in range(220):
                if alvo is not None and _try < 120:
                    ap = _montar_por_padrao(pool, alvo, rng)
                else:
                    # fallback / demais estratégias: distribuição B-M-A(+31)
                    # varia levemente a dist a cada aposta na automática
                    dist_uso = dist
                    if estrategia == "automatica" and _try % 7 == 3:
                        dist_uso = _distribuir_proporcional(k, pool_por_faixa(pool, limites), limites)
                    ap = _montar_aposta(pool, dist_uso, rng, limites=limites)
                if ap is None:
                    continue
                pstr = padrao_inicial_de(ap)
                # Preferir padrões distintos no lote
                if pstr in padroes_usados and _try < 160 and len(padroes_usados) < i + 1:
                    continue
                if not _aposta_ok_diversidade(
                    ap, usadas, padroes_usados, historico_sorteados,
                    apostas_excluidas, jaccard_max_lote, apostas,
                    exigir_padrao_distinto=True,
                ):
                    continue
                usadas.add(frozenset(ap))
                padroes_usados.add(pstr)
                apostas.append(ap)
                ok_ap = True
                break
            if not ok_ap:
                falhou = True
                break
        if falhou or len(apostas) < qtd_alvo:
            continue

        max_sim = 0.0
        diffs: List[float] = []
        for ant in construcoes_anteriores:
            sim_info = calcular_similaridade(apostas, ant)
            max_sim = max(max_sim, sim_info["similaridade"])
            diffs.append(sim_info["diferenca_pct"])

        diff_min = min(diffs) if diffs else 100.0
        # Score: diversidade de padrões no lote + diferença vs anteriores
        score = len(padroes_usados) * 10.0 + diff_min

        meta = {
            "sucesso": True,
            "apostas": apostas,
            "distribuicao": dist,
            "padroes_iniciais": [padrao_inicial_de(a) for a in apostas],
            "qtd_padroes_distintos": len(padroes_usados),
            "similaridade_max_anterior": round(max_sim, 4) if construcoes_anteriores else None,
            "diferenca_min_pct": round(diff_min, 1) if diffs else None,
            "tentativa": tentativa + 1,
        }

        if max_sim <= similaridade_max or not construcoes_anteriores:
            return meta
        if score > melhor_score or (score == melhor_score and diff_min > melhor_diff):
            melhor_score = score
            melhor_diff = diff_min
            melhor = dict(meta)
            melhor["aviso"] = (
                f"Similaridade acima do limiar ({similaridade_max:.0%}); "
                f"melhor resultado encontrado ({len(padroes_usados)} padrões distintos)."
            )

    if melhor:
        return melhor
    return {
        "sucesso": False,
        "erro": (
            "Não foi possível gerar construção distinta o suficiente. "
            "Tente outra estratégia, amplie o conjunto-base ou reduza o limiar de similaridade."
        ),
    }
