# -*- coding: utf-8 -*-
"""Gerador Ciclo → Fechamento — foca nas pendentes quando o ciclo está crítico/curto."""
from __future__ import annotations

import itertools
import random
from typing import Any, Dict, List, Optional

from .analise_service import AnaliseCicloCoberturaService
from .inteligencia_service import CicloInteligenciaService
from .specs import get_ciclo_spec


def _elegivel(est: dict, estr: dict, vale_fech) -> Dict[str, Any]:
    n = int(est.get("faltando") or 0)
    pressao = (est.get("pressao") or "").lower()
    classificacao = est.get("classificacao") or ""
    parcial = bool(estr.get("fechamento_parcial"))

    ok = (
        n <= 6
        or pressao in ("alta", "extrema")
        or classificacao in ("Avançado", "Crítico")
        or vale_fech is True
        or vale_fech == "sim"
    )
    # "parcial" sozinho não libera — só reforça quando já há sinal de fim de ciclo
    if not ok and vale_fech == "parcial" and n <= 8 and (
        classificacao in ("Médio", "Avançado", "Crítico")
        or pressao in ("média", "media", "alta", "extrema")
    ):
        ok = True
    motivo = []
    if n <= 6:
        motivo.append(f"faltam {n}")
    if pressao in ("alta", "extrema"):
        motivo.append(f"pressão {pressao}")
    if classificacao in ("Avançado", "Crítico"):
        motivo.append(classificacao)
    if vale_fech is True or vale_fech == "sim":
        motivo.append("vale fechamento: sim")
    elif vale_fech == "parcial" and ok:
        motivo.append("fechamento parcial viável")
    if not ok:
        motivo = [f"ciclo ainda distante (faltam {n}, {classificacao or '—'}, pressão {pressao or '—'})"]
    return {
        "elegivel": ok,
        "parcial": parcial or n > 4 or vale_fech == "parcial",
        "motivo": " · ".join(motivo) if motivo else "—",
    }


def _tamanhos_cobertura(n_pend: int, pick_n: int, parcial: bool, rng: random.Random) -> int:
    """Quantas pendentes cobrir neste jogo (nunca todas se parcial e n>3)."""
    if n_pend <= 0:
        return 0
    if n_pend <= 3 and not parcial:
        return min(n_pend, pick_n)
    if parcial or n_pend > 3:
        # cobre subconjunto; deixa pelo menos 1 de fora se possível
        max_k = min(pick_n, n_pend - 1 if n_pend > 1 else n_pend)
        min_k = min(2, max_k) if n_pend >= 2 else max_k
        if max_k < min_k:
            return max_k
        # favorece 2–4
        prefer = [k for k in range(min_k, max_k + 1) if 2 <= k <= 4]
        if not prefer:
            prefer = list(range(min_k, max_k + 1))
        return rng.choice(prefer)
    return min(n_pend, pick_n, 4)


def gerar_apostas_fechamento(
    modality_key: str,
    *,
    quantidade: int = 10,
    pick: Optional[int] = None,
    forcar: bool = False,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Cobre subconjuntos das pendentes (fechamento parcial/endgame).
    Preenche o restante com já saídas. Não joga todas as pendentes se parcial.
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
    vale = (op.get("operacional") or {}).get("respostas", {}).get("vale_fechamento")
    est = motor.get("estado_atual") or {}
    estr = motor.get("estrategia") or {}
    gate = _elegivel(est, estr, vale)

    if not gate["elegivel"] and not forcar:
        return {
            "ok": False,
            "erro": (
                "Fechamento não recomendado neste momento "
                f"({gate['motivo']}). Ative 'Forçar mesmo assim' se desejar."
            ),
            "indicadores": {
                "elegivel": False,
                "motivo": gate["motivo"],
                "faltando": est.get("faltando"),
                "pressao": est.get("pressao"),
                "classificacao": est.get("classificacao"),
                "vale_fechamento": vale,
            },
        }

    pick_n = int(pick if pick is not None else spec.pick_default)
    pick_n = max(spec.pick_min, min(spec.pick_max, pick_n))
    qtd = max(1, min(int(quantidade or 10), 200))

    pendentes = list(ciclo.get("dezenas_pendentes") or [])
    saidas = list(ciclo.get("dezenas_saidas") or [])
    n_pend = len(pendentes)
    scores_map = {s["dezena"]: s["score"] for s in (motor.get("scores_dezenas") or [])}
    parcial = gate["parcial"]

    if n_pend == 0:
        return {"ok": False, "erro": "Não há pendentes — ciclo já fechado."}
    if len(saidas) + n_pend < pick_n:
        return {"ok": False, "erro": "Universo insuficiente para montar o jogo."}

    rng = random.Random(seed)
    apostas: List[dict] = []
    vistos = set()
    tentativas = 0
    max_tent = qtd * 300
    # pré-rank pendentes por score
    pend_ord = sorted(pendentes, key=lambda d: scores_map.get(d, 50), reverse=True)

    while len(apostas) < qtd and tentativas < max_tent:
        tentativas += 1
        k = _tamanhos_cobertura(n_pend, pick_n, parcial, rng)
        k = min(k, pick_n, n_pend)
        precisamos = pick_n - k
        if precisamos > len(saidas):
            k = max(0, pick_n - len(saidas))
            precisamos = pick_n - k
        if precisamos > len(saidas) or k <= 0:
            continue

        # amostra no topo ranqueado + um pouco de cauda
        top_n = min(len(pend_ord), max(k + 3, 6))
        pool = pend_ord[:top_n]
        if len(pool) < k:
            continue
        # se poucas combinações, enumera; senão sample
        if len(pool) <= 8 and k <= 4:
            combos = list(itertools.combinations(pool, k))
            rng.shuffle(combos)
            falt = list(combos[0]) if combos else []
        else:
            falt = rng.sample(pool, k)

        resto_pool = [d for d in saidas if d not in falt]
        if len(resto_pool) < precisamos:
            continue
        resto = rng.sample(resto_pool, precisamos)
        jogo = sorted(set(falt) | set(resto))
        if len(jogo) != pick_n:
            continue
        chave = tuple(jogo)
        if chave in vistos:
            continue
        vistos.add(chave)
        cobertos = set(falt)
        deixadas = [d for d in pendentes if d not in cobertos]
        apostas.append({
            "dezenas": jogo,
            "faltantes": sorted(falt),
            "ja_saidas": sorted(resto),
            "k_faltantes": len(falt),
            "pendentes_fora": sorted(deixadas),
            "cobertura_pendentes": round(100.0 * len(falt) / n_pend, 1) if n_pend else 0,
            "soma": sum(jogo),
            "digitos_distintos": len({d % 10 for d in jogo}),
        })

    aviso_parts = []
    if not gate["elegivel"] and forcar:
        aviso_parts.append("Gerado com forçar — análise não recomendava fechamento.")
    if parcial:
        aviso_parts.append("Fechamento parcial: nenhuma aposta cobre todas as pendentes.")
    if len(apostas) < qtd:
        aviso_parts.append(f"Geradas {len(apostas)} de {qtd} (pool limitado).")

    return {
        "ok": True,
        "estrategia": "fechamento",
        "geradas": len(apostas),
        "apostas": apostas,
        "aviso": " ".join(aviso_parts) if aviso_parts else None,
        "indicadores": {
            "ciclo": est.get("numero_ciclo"),
            "classificacao": est.get("classificacao"),
            "pressao": est.get("pressao"),
            "faltando": n_pend,
            "elegivel": gate["elegivel"],
            "parcial": parcial,
            "motivo": gate["motivo"],
            "vale_fechamento": vale,
            "fechamento_tipo": (motor.get("fechamento") or {}).get("tipo"),
            "leitura": motor.get("leitura_automatica"),
            "pendentes": pendentes,
            "saidas_count": len(saidas),
            "forcado": bool(forcar and not gate["elegivel"]),
        },
    }


def contexto_fechamento(modality_key: str) -> Dict[str, Any]:
    payload = AnaliseCicloCoberturaService.payload_oficial(modality_key)
    if not payload.get("sucesso"):
        return {"ok": False, "erro": payload.get("mensagem") or "Análise indisponível."}
    motor = payload.get("motor_ciclo") or {}
    ciclo = payload["dados"]
    est = motor.get("estado_atual") or {}
    estr = motor.get("estrategia") or {}
    op = CicloInteligenciaService.obter_inteligencia_operacional(modality_key) or {}
    vale = (op.get("operacional") or {}).get("respostas", {}).get("vale_fechamento")
    gate = _elegivel(est, estr, vale)
    return {
        "ok": True,
        "ciclo": ciclo.get("numero_ciclo"),
        "quantidade_concursos": ciclo.get("quantidade_concursos"),
        "pendentes": ciclo.get("dezenas_pendentes") or [],
        "saidas": ciclo.get("dezenas_saidas") or [],
        "percentual": ciclo.get("percentual_completo"),
        "classificacao": est.get("classificacao"),
        "pressao": est.get("pressao"),
        "elegivel": gate["elegivel"],
        "parcial": gate["parcial"],
        "motivo": gate["motivo"],
        "vale_fechamento": vale,
        "fechamento_tipo": (motor.get("fechamento") or {}).get("tipo"),
        "fechamento_texto": (motor.get("fechamento") or {}).get("interpretacao"),
        "leitura": motor.get("leitura_automatica"),
        "top_3": payload.get("top_3") or [],
        "estrategia": estr,
    }
