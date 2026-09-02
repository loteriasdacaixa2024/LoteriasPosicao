# -*- coding: utf-8 -*-
"""Gerador Ritmo de Evolução — k faltantes dinâmico a partir da análise oficial."""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

from .analise_service import AnaliseCicloCoberturaService
from .inteligencia_service import CicloInteligenciaService
from .specs import get_ciclo_spec


def _amostrar_k(
    dist: Dict[str, float],
    n_pend: int,
    pressao: str,
    rng: random.Random,
) -> int:
    """Amostra k faltantes pela distribuição de cenários semelhantes + teto de pressão."""
    chaves = ["0", "1", "2", "3", "4+"]
    pesos = [max(0.0, float(dist.get(c, 0) or 0)) for c in chaves]
    if sum(pesos) <= 0:
        pesos = [10.0, 25.0, 30.0, 20.0, 15.0]

    escolhido = rng.choices(chaves, weights=pesos, k=1)[0]
    if escolhido == "0":
        k = 0
    elif escolhido == "4+":
        k = rng.choice([4, 5]) if n_pend >= 5 else min(4, n_pend)
    else:
        k = int(escolhido)

    if pressao in ("baixa",):
        k_max = min(3, max(1, n_pend // 3) if n_pend > 6 else min(2, n_pend))
    elif pressao in ("média", "media"):
        k_max = min(4, n_pend)
    elif pressao == "alta":
        k_max = min(5, n_pend)
    else:
        k_max = min(n_pend, max(3, n_pend - 1) if n_pend > 1 else n_pend)

    if n_pend > 3:
        k_max = min(k_max, n_pend - 1)

    return max(0, min(k, k_max, n_pend))


def _peso_pendente(d: int, scores_map: Dict[int, int], faixas_dist: dict) -> float:
    base = float(scores_map.get(d, 50))
    if d <= 10 and faixas_dist.get("baixas", 0) >= faixas_dist.get("medias", 0):
        base += 3
    elif 11 <= d <= 20:
        base += 2
    return base + random.random() * 4


def gerar_apostas_ritmo(
    modality_key: str,
    *,
    quantidade: int = 10,
    pick: Optional[int] = None,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Consome o payload oficial da análise.
    k faltantes ~ cenários semelhantes + teto por pressão;
    restante = dezenas já saídas no ciclo atual.
    """
    spec = get_ciclo_spec(modality_key)
    if not spec.enabled:
        return {"ok": False, "erro": f"Ciclo não habilitado para {spec.nome}."}

    payload = AnaliseCicloCoberturaService.payload_oficial(modality_key)
    if not payload.get("sucesso"):
        return {"ok": False, "erro": payload.get("mensagem") or "Análise indisponível."}

    ciclo = payload["dados"]
    motor = payload.get("motor_ciclo") or CicloInteligenciaService.analisar_ciclo_completo(
        modality_key
    )
    if not motor:
        return {"ok": False, "erro": "Motor de ciclo indisponível."}

    pick_n = int(pick if pick is not None else spec.pick_default)
    pick_n = max(spec.pick_min, min(spec.pick_max, pick_n))
    qtd = max(1, min(int(quantidade or 10), 200))

    pendentes = list(ciclo.get("dezenas_pendentes") or [])
    saidas = list(ciclo.get("dezenas_saidas") or [])
    n_pend = len(pendentes)
    est = motor["estado_atual"]
    dist = (motor.get("historico_semelhante") or {}).get("distribuicao_entrada") or {}
    faixas = (motor.get("faltantes") or {}).get("distribuicao") or {}
    scores_map = {s["dezena"]: s["score"] for s in (motor.get("scores_dezenas") or [])}
    pressao = est.get("pressao") or "baixa"

    rng = random.Random(seed)
    apostas: List[dict] = []
    vistos = set()
    tentativas = 0
    max_tent = qtd * 200
    ks_usados: List[int] = []

    while len(apostas) < qtd and tentativas < max_tent:
        tentativas += 1
        k = _amostrar_k(dist, n_pend, pressao, rng)
        k = min(k, pick_n, n_pend)
        precisamos_saidas = pick_n - k
        if precisamos_saidas > len(saidas):
            k = max(0, pick_n - len(saidas))
            precisamos_saidas = pick_n - k
        if precisamos_saidas > len(saidas):
            continue

        pool_p = sorted(
            pendentes,
            key=lambda d: _peso_pendente(d, scores_map, faixas),
            reverse=True,
        )
        falt: List[int] = []
        if k > 0 and pool_p:
            top = pool_p[: min(len(pool_p), max(k + 4, 8))]
            falt = rng.sample(top, min(k, len(top)))

        resto_pool = [d for d in saidas if d not in falt]
        if len(resto_pool) < precisamos_saidas:
            continue
        resto = rng.sample(resto_pool, precisamos_saidas)
        jogo = sorted(set(falt) | set(resto))
        if len(jogo) != pick_n:
            continue
        chave = tuple(jogo)
        if chave in vistos:
            continue
        vistos.add(chave)
        ks_usados.append(len(falt))
        apostas.append({
            "dezenas": jogo,
            "faltantes": sorted(falt),
            "ja_saidas": sorted(resto),
            "k_faltantes": len(falt),
            "soma": sum(jogo),
            "digitos_distintos": len({d % 10 for d in jogo}),
        })

    return {
        "ok": True,
        "estrategia": "ritmo_evolucao",
        "geradas": len(apostas),
        "apostas": apostas,
        "aviso": (
            None if len(apostas) >= qtd
            else f"Geradas {len(apostas)} de {qtd} (pool limitado)."
        ),
        "indicadores": {
            "ciclo": est.get("numero_ciclo"),
            "classificacao": est.get("classificacao"),
            "pressao": pressao,
            "faltando": n_pend,
            "fechamento_percentual": est.get("fechamento_percentual"),
            "distribuicao_entrada": dist,
            "media_k_gerado": round(sum(ks_usados) / len(ks_usados), 2) if ks_usados else 0,
            "leitura": motor.get("leitura_automatica"),
            "pendentes": pendentes,
            "saidas_count": len(saidas),
        },
    }


def contexto_ritmo(modality_key: str) -> Dict[str, Any]:
    payload = AnaliseCicloCoberturaService.payload_oficial(modality_key)
    if not payload.get("sucesso"):
        return {"ok": False, "erro": payload.get("mensagem") or "Análise indisponível."}
    motor = payload.get("motor_ciclo") or {}
    ciclo = payload["dados"]
    est = motor.get("estado_atual") or {}
    return {
        "ok": True,
        "ciclo": ciclo.get("numero_ciclo"),
        "quantidade_concursos": ciclo.get("quantidade_concursos"),
        "pendentes": ciclo.get("dezenas_pendentes") or [],
        "saidas": ciclo.get("dezenas_saidas") or [],
        "percentual": ciclo.get("percentual_completo"),
        "classificacao": est.get("classificacao"),
        "pressao": est.get("pressao"),
        "distribuicao_entrada": (motor.get("historico_semelhante") or {}).get(
            "distribuicao_entrada"
        ),
        "amostras": (motor.get("historico_semelhante") or {}).get("amostras"),
        "leitura": motor.get("leitura_automatica"),
        "estrategia": motor.get("estrategia") or {},
        "top_3": payload.get("top_3") or [],
    }
