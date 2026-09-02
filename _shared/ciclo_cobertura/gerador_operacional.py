# -*- coding: utf-8 -*-
"""Gerador Ciclo → Modo Operacional — segue a receita da Inteligência Operacional."""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

from .analise_service import AnaliseCicloCoberturaService
from .inteligencia_service import CicloInteligenciaService
from .specs import get_ciclo_spec


def _faixa_dezena(d: int) -> str:
    if d <= 10:
        return "baixa"
    if d <= 20:
        return "media"
    return "alta"


def _peso(d: int, scores_map: Dict[int, float], faixa_prior: str) -> float:
    base = float(scores_map.get(d, 50))
    if _faixa_dezena(d) == faixa_prior or (
        faixa_prior == "media" and _faixa_dezena(d) == "media"
    ):
        base += 8
    return base + random.random() * 3


def _ajustar_k(k_base: int, modo: str, n_pend: int, pick_n: int) -> int:
    k = int(k_base or 2)
    if modo == "conservador":
        k = max(1, k - 1) if n_pend > 2 else k
    elif modo in ("agressivo", "fechamento"):
        k = min(n_pend, k + 1, pick_n - 1 if pick_n > 1 else pick_n)
    return max(0, min(k, n_pend, pick_n))


def gerar_apostas_operacional(
    modality_key: str,
    *,
    quantidade: int = 10,
    pick: Optional[int] = None,
    modo: Optional[str] = None,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """
    k fixo = estrategia.faltantes_por_jogo (ajustado pelo modo).
    1 repetente do último concurso + restante das já saídas.
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

    op = CicloInteligenciaService.obter_inteligencia_operacional(modality_key) or {}
    estr = (motor.get("estrategia") or {})
    est = motor.get("estado_atual") or {}

    pick_n = int(pick if pick is not None else spec.pick_default)
    pick_n = max(spec.pick_min, min(spec.pick_max, pick_n))
    qtd = max(1, min(int(quantidade or 10), 200))

    modo_rec = (estr.get("modo_recomendado") or "equilibrado").lower()
    modo_uso = (modo or "auto").strip().lower()
    if modo_uso in ("", "auto", "recomendado"):
        modo_uso = modo_rec

    pendentes = list(ciclo.get("dezenas_pendentes") or [])
    saidas = list(ciclo.get("dezenas_saidas") or [])
    n_pend = len(pendentes)
    k_base = int(estr.get("faltantes_por_jogo") or 2)
    faixa_prior = estr.get("priorizar_faixa") or "media"
    scores_map = {s["dezena"]: s["score"] for s in (motor.get("scores_dezenas") or [])}
    ultimo = CicloInteligenciaService._ultimo_sorteio_dezenas(modality_key) or []
    repetentes_pool = [d for d in ultimo if d in saidas]
    if not repetentes_pool:
        repetentes_pool = list(saidas)

    rng = random.Random(seed)
    apostas: List[dict] = []
    vistos = set()
    tentativas = 0
    max_tent = qtd * 250
    ks: List[int] = []

    while len(apostas) < qtd and tentativas < max_tent:
        tentativas += 1
        k = _ajustar_k(k_base, modo_uso, n_pend, pick_n)
        # micro-variação ±0/1 ocasional para diversidade
        if n_pend >= 2 and rng.random() < 0.35:
            k = max(0, min(n_pend, pick_n, k + rng.choice([-1, 0, 1])))

        n_rep = 1 if repetentes_pool and pick_n - k >= 1 else 0
        precisamos_saidas = pick_n - k - n_rep
        if precisamos_saidas < 0:
            k = max(0, pick_n - n_rep)
            precisamos_saidas = pick_n - k - n_rep
        if precisamos_saidas > len(saidas):
            continue

        pool_p = sorted(
            pendentes,
            key=lambda d: _peso(d, scores_map, faixa_prior),
            reverse=True,
        )
        falt: List[int] = []
        if k > 0 and pool_p:
            top = pool_p[: min(len(pool_p), max(k + 5, 9))]
            falt = rng.sample(top, min(k, len(top)))

        rep: List[int] = []
        if n_rep:
            cand_rep = [d for d in repetentes_pool if d not in falt]
            if not cand_rep:
                continue
            rep = [rng.choice(cand_rep)]

        resto_pool = [d for d in saidas if d not in falt and d not in rep]
        if len(resto_pool) < precisamos_saidas:
            continue
        resto = rng.sample(resto_pool, precisamos_saidas) if precisamos_saidas else []
        jogo = sorted(set(falt) | set(rep) | set(resto))
        if len(jogo) != pick_n:
            continue
        chave = tuple(jogo)
        if chave in vistos:
            continue
        vistos.add(chave)
        ks.append(len(falt))
        apostas.append({
            "dezenas": jogo,
            "faltantes": sorted(falt),
            "repetentes": sorted(rep),
            "ja_saidas": sorted(resto),
            "k_faltantes": len(falt),
            "modo": modo_uso,
            "soma": sum(jogo),
            "digitos_distintos": len({d % 10 for d in jogo}),
        })

    return {
        "ok": True,
        "estrategia": "modo_operacional",
        "geradas": len(apostas),
        "apostas": apostas,
        "aviso": (
            None if len(apostas) >= qtd
            else f"Geradas {len(apostas)} de {qtd} (pool limitado)."
        ),
        "indicadores": {
            "ciclo": est.get("numero_ciclo"),
            "classificacao": est.get("classificacao"),
            "pressao": est.get("pressao"),
            "faltando": n_pend,
            "modo_recomendado": modo_rec,
            "modo_usado": modo_uso,
            "k_base": k_base,
            "media_k_gerado": round(sum(ks) / len(ks), 2) if ks else 0,
            "priorizar_faixa": faixa_prior,
            "fechamento_parcial": estr.get("fechamento_parcial"),
            "alertas": estr.get("alertas") or [],
            "leitura": motor.get("leitura_automatica"),
            "vale_fechamento": (op.get("operacional") or {}).get("respostas", {}).get(
                "vale_fechamento"
            ),
            "pendentes": pendentes,
            "saidas_count": len(saidas),
        },
    }


def contexto_operacional(modality_key: str) -> Dict[str, Any]:
    payload = AnaliseCicloCoberturaService.payload_oficial(modality_key)
    if not payload.get("sucesso"):
        return {"ok": False, "erro": payload.get("mensagem") or "Análise indisponível."}
    motor = payload.get("motor_ciclo") or {}
    ciclo = payload["dados"]
    est = motor.get("estado_atual") or {}
    estr = motor.get("estrategia") or {}
    op = CicloInteligenciaService.obter_inteligencia_operacional(modality_key) or {}
    return {
        "ok": True,
        "ciclo": ciclo.get("numero_ciclo"),
        "quantidade_concursos": ciclo.get("quantidade_concursos"),
        "pendentes": ciclo.get("dezenas_pendentes") or [],
        "saidas": ciclo.get("dezenas_saidas") or [],
        "percentual": ciclo.get("percentual_completo"),
        "classificacao": est.get("classificacao"),
        "pressao": est.get("pressao"),
        "modo_recomendado": estr.get("modo_recomendado"),
        "faltantes_por_jogo": estr.get("faltantes_por_jogo"),
        "priorizar_faixa": estr.get("priorizar_faixa"),
        "fechamento_parcial": estr.get("fechamento_parcial"),
        "alertas": estr.get("alertas") or [],
        "leitura": motor.get("leitura_automatica"),
        "vale_fechamento": (op.get("operacional") or {}).get("respostas", {}).get(
            "vale_fechamento"
        ),
        "top_3": payload.get("top_3") or [],
        "estrategia": estr,
    }
