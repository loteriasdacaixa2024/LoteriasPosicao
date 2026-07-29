# -*- coding: utf-8 -*-
"""Motor posicional — Construtor Super Sete (C1–C7)."""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Set, Tuple

from geradores_elite.construtor.construcoes_core import (
    ESTRATEGIAS,
    QTD_APOSTAS_FIXA,
    _ajustar_distribuicao_total,
    _distribuir_balanceado,
    _distribuir_proporcional,
    calcular_distribuicao,
    estrategias_ui,
)

NUM_COLUNAS = 7
FAIXA_LIMITES_SS = {"baixas": (0, 3), "medias": (4, 6), "altas": (7, 9)}

ESTRATEGIAS_SS = estrategias_ui({"baixas": "0–3", "medias": "4–6", "altas": "7–9"})


def faixa_digito(d: int) -> str:
    for nome, (lo, hi) in FAIXA_LIMITES_SS.items():
        if lo <= d <= hi:
            return nome
    return "altas"


def encode_pool_colunas(pool: Dict[int, List[int]]) -> str:
    import json
    norm = {str(c): sorted(set(pool.get(c, pool.get(int(c), [])))) for c in range(1, NUM_COLUNAS + 1)}
    return json.dumps(norm, ensure_ascii=False, separators=(",", ":"))


def decode_pool_colunas(raw: str) -> Dict[int, List[int]]:
    import json
    if not raw:
        return {c: [] for c in range(1, NUM_COLUNAS + 1)}
    if raw.strip().startswith("{"):
        data = json.loads(raw)
        out: Dict[int, List[int]] = {}
        for c in range(1, NUM_COLUNAS + 1):
            key = str(c)
            out[c] = sorted(int(x) for x in (data.get(key) or data.get(c) or []))
        return out
    return {c: [] for c in range(1, NUM_COLUNAS + 1)}


def pool_por_faixa_colunas(pool: Dict[int, List[int]]) -> Dict[str, Dict[int, List[int]]]:
    out: Dict[str, Dict[int, List[int]]] = {"baixas": {}, "medias": {}, "altas": {}}
    for col in range(1, NUM_COLUNAS + 1):
        for d in pool.get(col, []):
            out[faixa_digito(d)].setdefault(col, []).append(d)
        for f in out:
            if col in out[f]:
                out[f][col] = sorted(out[f][col])
    return out


def _digitos_faixa_coluna(pool_col: List[int], faixa: str) -> List[int]:
    lo, hi = FAIXA_LIMITES_SS[faixa]
    return [d for d in pool_col if lo <= d <= hi]


def _atribuir_colunas_faixas(dist: Dict[str, int]) -> List[str]:
    """Retorna lista de 7 faixas, uma por coluna C1..C7."""
    slots: List[str] = []
    for faixa in ("baixas", "medias", "altas"):
        slots.extend([faixa] * dist.get(faixa, 0))
    while len(slots) < NUM_COLUNAS:
        slots.append("medias")
    return slots[:NUM_COLUNAS]


def validar_estrategia_ss(
    pool: Dict[int, List[int]],
    estrategia: str,
    personalizada: Optional[Dict[str, int]] = None,
    comportamento_moda: Optional[Dict[str, int]] = None,
) -> Tuple[bool, str, Optional[Dict[str, int]]]:
    for col in range(1, NUM_COLUNAS + 1):
        if not pool.get(col):
            return False, f"Coluna C{col} sem dígitos no conjunto-base.", None
    k = NUM_COLUNAS
    flat = [d for col in range(1, NUM_COLUNAS + 1) for d in pool[col]]
    dist = calcular_distribuicao(
        estrategia, flat, k, personalizada, comportamento_moda, limites=FAIXA_LIMITES_SS
    )
    slots = _atribuir_colunas_faixas(dist)
    for col in range(1, NUM_COLUNAS + 1):
        faixa = slots[col - 1]
        if not _digitos_faixa_coluna(pool[col], faixa):
            return (
                False,
                f"Coluna C{col}: estratégia exige faixa {faixa}, mas o pool não tem dígito compatível.",
                dist,
            )
    return True, "", dist


def _montar_aposta_ss(
    pool: Dict[int, List[int]],
    slots: List[str],
    rng: random.Random,
) -> Optional[List[int]]:
    aposta: List[int] = []
    for col in range(1, NUM_COLUNAS + 1):
        faixa = slots[col - 1]
        candidatos = _digitos_faixa_coluna(pool[col], faixa)
        if not candidatos:
            return None
        aposta.append(rng.choice(candidatos))
    return aposta


def calcular_similaridade_ss(
    apostas_a: List[List[int]],
    apostas_b: List[List[int]],
) -> Dict[str, float]:
    if not apostas_a or not apostas_b:
        return {"similaridade": 0.0, "diferenca_pct": 100.0, "apostas_iguais": 0}

    tuples_a = [tuple(a) for a in apostas_a]
    tuples_b = [tuple(a) for a in apostas_b]
    exact = len(set(tuples_a) & set(tuples_b))
    exact_sim = exact / max(len(tuples_a), len(tuples_b))

    pos_sims: List[float] = []
    for ta in tuples_a:
        for tb in tuples_b:
            matches = sum(1 for i in range(NUM_COLUNAS) if ta[i] == tb[i])
            pos_sims.append(matches / NUM_COLUNAS)
    pair_sim = sum(pos_sims) / len(pos_sims) if pos_sims else 0.0

    similaridade = 0.6 * exact_sim + 0.4 * pair_sim
    return {
        "similaridade": round(similaridade, 4),
        "diferenca_pct": round((1 - similaridade) * 100, 1),
        "apostas_iguais": exact,
    }


def gerar_construcao_ss(
    pool: Dict[int, List[int]],
    estrategia: str,
    *,
    personalizada: Optional[Dict[str, int]] = None,
    comportamento_moda: Optional[Dict[str, int]] = None,
    construcoes_anteriores: Optional[List[List[List[int]]]] = None,
    similaridade_max: float = 0.20,
    seed: Optional[int] = None,
    max_tentativas: int = 400,
) -> Dict[str, Any]:
    ok, msg, dist = validar_estrategia_ss(
        pool, estrategia, personalizada, comportamento_moda
    )
    if not ok or not dist:
        return {"sucesso": False, "erro": msg}
    slots = _atribuir_colunas_faixas(dist)
    rng = random.Random(seed)
    construcoes_anteriores = construcoes_anteriores or []
    melhor: Optional[Dict[str, Any]] = None
    melhor_diff = -1.0

    for tentativa in range(max_tentativas):
        apostas: List[List[int]] = []
        usadas: Set[tuple] = set()
        falhou = False
        for _ in range(QTD_APOSTAS_FIXA):
            ok_ap = False
            for _try in range(200):
                ap = _montar_aposta_ss(pool, slots, rng)
                if ap is None:
                    falhou = True
                    break
                chave = tuple(ap)
                if chave not in usadas:
                    usadas.add(chave)
                    apostas.append(ap)
                    ok_ap = True
                    break
            if not ok_ap:
                falhou = True
                break
        if falhou or len(apostas) < QTD_APOSTAS_FIXA:
            continue

        max_sim = 0.0
        diffs: List[float] = []
        for ant in construcoes_anteriores:
            sim_info = calcular_similaridade_ss(apostas, ant)
            max_sim = max(max_sim, sim_info["similaridade"])
            diffs.append(sim_info["diferenca_pct"])

        diff_min = min(diffs) if diffs else 100.0
        if max_sim <= similaridade_max or not construcoes_anteriores:
            return {
                "sucesso": True,
                "apostas": apostas,
                "distribuicao": dist,
                "similaridade_max_anterior": round(max_sim, 4) if construcoes_anteriores else None,
                "diferenca_min_pct": round(diff_min, 1) if diffs else None,
                "tentativa": tentativa + 1,
            }
        if diff_min > melhor_diff:
            melhor_diff = diff_min
            melhor = {
                "sucesso": True,
                "apostas": apostas,
                "distribuicao": dist,
                "similaridade_max_anterior": round(max_sim, 4),
                "diferenca_min_pct": round(diff_min, 1),
                "tentativa": tentativa + 1,
                "aviso": f"Similaridade acima do limiar ({similaridade_max:.0%}); melhor resultado encontrado.",
            }

    if melhor:
        return melhor
    return {
        "sucesso": False,
        "erro": "Não foi possível gerar construção distinta o suficiente. Tente outra estratégia ou amplie os pools.",
    }


def distribuicao_historica_moda_ss(sorteios_digitos: List[List[int]]) -> Dict[str, int]:
    if not sorteios_digitos:
        return {"baixas": 2, "medias": 3, "altas": 2}
    contadores: Dict[Tuple[int, int, int], int] = {}
    for dz in sorteios_digitos:
        b = sum(1 for d in dz if faixa_digito(d) == "baixas")
        m = sum(1 for d in dz if faixa_digito(d) == "medias")
        a = sum(1 for d in dz if faixa_digito(d) == "altas")
        chave = (b, m, a)
        contadores[chave] = contadores.get(chave, 0) + 1
    moda = max(contadores.items(), key=lambda x: x[1])[0]
    return {"baixas": moda[0], "medias": moda[1], "altas": moda[2]}
