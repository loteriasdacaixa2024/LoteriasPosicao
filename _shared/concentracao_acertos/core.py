# -*- coding: utf-8 -*-
"""Motor — Concentração de Acertos."""
from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Sequence, Tuple

from geradores_elite.construtor.construcoes_core import (
    distribuicao_historica_moda,
    gerar_construcao,
)
from geradores_elite.otimizador.score import avaliar_conjunto

from .specs import get_concentracao_config

PERFIL_ESTRATEGIA = {
    "equilibrado": "balanceada",
    "frequencia": "automatica",
    "atraso": "conforme_comportamento",
}


def seed_deterministico(
    pool: Sequence[int],
    perfil: str,
    *,
    comportamento_moda: Optional[Dict[str, int]] = None,
    salt: str = "",
) -> int:
    """Seed estável para mesmos pool/parâmetros — evita variação entre execuções."""
    pool_s = ",".join(str(d) for d in sorted(int(x) for x in pool))
    moda_s = ""
    if comportamento_moda:
        moda_s = ",".join(
            f"{k}:{int(v)}" for k, v in sorted(comportamento_moda.items(), key=lambda x: x[0])
        )
    payload = f"conc|{salt}|{perfil}|{pool_s}|{moda_s}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) % (2**31 - 1)


def estrategia_cfg(modality_key: str, estrategia_id: str) -> Dict[str, Any]:
    cfg = get_concentracao_config(modality_key)
    for est in cfg.get("estrategias", []):
        if est["id"] == estrategia_id:
            return est
    raise ValueError(f"Estratégia inválida: {estrategia_id}")


def pool_sugerido(
    dados_dezenas: List[Dict[str, Any]],
    pool_size: int,
    criterio: str = "freq",
    *,
    dezena_min: int = 1,
    dezena_max: int = 31,
) -> List[int]:
    if not dados_dezenas:
        span = list(range(dezena_min, dezena_max + 1))
        return span[: min(pool_size, len(span))]
    chave = "atraso" if criterio == "atraso" else "freq"
    ordenado = sorted(dados_dezenas, key=lambda r: (-int(r.get(chave) or 0), int(r.get("dezena") or 0)))
    pool = [int(r["dezena"]) for r in ordenado[:pool_size]]
    return sorted(set(pool))


def gerar_apostas(
    pool: List[int],
    *,
    perfil: str = "equilibrado",
    quantidade: int = 10,
    comportamento_moda: Optional[Dict[str, int]] = None,
    seed: Optional[int] = None,
    seed_salt: str = "",
    aposta_dezenas: int = 7,
) -> Dict[str, Any]:
    pool = sorted(set(int(d) for d in pool))
    k = int(aposta_dezenas)
    estrategia = PERFIL_ESTRATEGIA.get(perfil, "balanceada")
    if seed is None:
        seed = seed_deterministico(
            pool,
            perfil,
            comportamento_moda=comportamento_moda,
            salt=seed_salt,
        )
    res = gerar_construcao(
        pool,
        k,
        estrategia,
        comportamento_moda=comportamento_moda,
        seed=seed,
        quantidade=max(1, int(quantidade or 10)),
    )
    if not res.get("sucesso"):
        return res
    apostas = res.get("apostas") or []
    qtd = max(1, min(int(quantidade or 10), len(apostas)))
    return {
        "sucesso": True,
        "apostas": apostas[:qtd],
        "quantidade": qtd,
        "distribuicao": res.get("distribuicao"),
        "aviso": res.get("aviso"),
    }


def gerar_apostas_supersete(
    pool: List[int],
    *,
    quantidade: int = 10,
    seed: Optional[int] = None,
    seed_salt: str = "",
) -> Dict[str, Any]:
    """
    Super Sete: pool de dígitos 0–9; cada aposta = 7 colunas com repetição livre.
    """
    import random

    pool_n = sorted(set(int(d) for d in pool if 0 <= int(d) <= 9))
    if not pool_n:
        return {"sucesso": False, "erro": "Pool Super Sete vazio (use dígitos 0–9)."}
    qtd = max(1, min(int(quantidade or 10), 50))
    if seed is None:
        seed = seed_deterministico(pool_n, "ss_posicional", salt=seed_salt)
    rng = random.Random(seed)
    apostas: List[List[int]] = []
    vistos = set()
    tent = 0
    max_tent = max(2000, qtd * 150)
    while len(apostas) < qtd and tent < max_tent:
        tent += 1
        ap = [rng.choice(pool_n) for _ in range(7)]
        chave = tuple(ap)
        if chave in vistos:
            continue
        vistos.add(chave)
        apostas.append(ap)
    if not apostas:
        return {"sucesso": False, "erro": "Não foi possível gerar apostas Super Sete."}
    return {
        "sucesso": True,
        "apostas": apostas,
        "quantidade": len(apostas),
        "distribuicao": None,
        "aviso": (
            "Super Sete posicional: 7 colunas; o mesmo dígito pode repetir "
            "(conforme regulamento Caixa)."
        ),
    }


def _historico_listas_posicional(rows: Sequence[Any]) -> List[List[int]]:
    out: List[List[int]] = []
    for row in rows:
        if hasattr(row, "digitos"):
            out.append(list(row.digitos()))
        elif hasattr(row, "dezenas"):
            dz = row.dezenas()
            out.append(list(dz) if not isinstance(dz, set) else sorted(dz))
        elif isinstance(row, dict):
            out.append(list(row.get("dezenas") or row.get("digitos") or []))
    return out


def backtest_conjunto_posicional(
    apostas: List[List[int]],
    historico_rows: Sequence[Any],
    *,
    max_acertos: int = 7,
    pico_destaque: int = 3,
) -> Dict[str, Any]:
    """Backtest Super Sete — acertos coluna a coluna."""
    if not apostas:
        return {"sucesso": False, "erro": "Nenhuma aposta para backtest."}
    if not historico_rows:
        return {"sucesso": False, "erro": "Histórico vazio no banco."}

    hist = _historico_listas_posicional(historico_rows)
    dist = {i: 0 for i in range(0, max_acertos + 1)}
    linhas: List[Dict[str, Any]] = []
    total_max = 0

    for row, sorteadas in zip(historico_rows, hist):
        hits = [
            sum(
                1
                for i in range(min(len(ap), len(sorteadas), max_acertos))
                if int(ap[i]) == int(sorteadas[i])
            )
            for ap in apostas
        ]
        mx = max(hits) if hits else 0
        idx = hits.index(mx) if hits else 0
        melhor = apostas[idx] if apostas else []
        acertadas = [
            int(melhor[i])
            for i in range(min(len(melhor), len(sorteadas)))
            if int(melhor[i]) == int(sorteadas[i])
        ]
        if mx in dist:
            dist[mx] += 1
        total_max += mx
        concurso = getattr(row, "concurso", None) or (
            row.get("concurso") if isinstance(row, dict) else None
        )
        data = getattr(row, "data", None) or (row.get("data") if isinstance(row, dict) else "")
        linhas.append({
            "concurso": concurso,
            "data": data or "",
            "max_acertos": mx,
            "melhor_aposta": melhor,
            "melhor_aposta_fmt": [str(d) for d in melhor],
            "acertadas": acertadas,
            "acertadas_fmt": [str(d) for d in acertadas],
            "sorteio_dezenas": list(sorteadas),
            "sorteio_dezenas_fmt": [str(d) for d in sorteadas],
            "mes_sorteio": {"mes_num": None, "mes_nome": "", "mes_abrev": ""},
            "mes_aposta": None,
            "mes_acertou": False,
        })

    linhas.sort(key=lambda x: (-x["max_acertos"], -(x["concurso"] or 0)))
    n = len(linhas)
    metricas = {
        "indice_concentracao": round((total_max / n) / 3.5, 3) if n else 0.0,
        "media_max_acertos": round(total_max / n, 2) if n else 0.0,
        **{f"dist_{i}": dist.get(i, 0) for i in range(3, max_acertos + 1)},
    }
    return {
        "sucesso": True,
        "concursos_analisados": n,
        "concurso_de": linhas[-1]["concurso"] if linhas else None,
        "concurso_ate": linhas[0]["concurso"] if linhas else None,
        "metricas": metricas,
        "linhas": linhas,
        "destaques": [l for l in linhas if l["max_acertos"] >= pico_destaque][:12],
        "meses_apostas": None,
    }


def _historico_sets(rows: Sequence[Any]) -> List[set]:
    out: List[set] = []
    for row in rows:
        if hasattr(row, "digitos"):
            # Super Sete / colunas: set só para motores legados — preferir backtest_posicional
            out.append(set(row.digitos()))
        elif hasattr(row, "dezenas"):
            out.append(set(row.dezenas()))
        elif isinstance(row, dict):
            out.append(set(row.get("dezenas") or []))
    return out


def _mes_from_row(row: Any) -> Tuple[int, str, str]:
    if hasattr(row, "mes_num"):
        mn = int(getattr(row, "mes_num", 0) or 0)
        nome = (getattr(row, "mes_nome", None) or "").strip()
        abrev = row.mes_abrev() if hasattr(row, "mes_abrev") else ""
    elif isinstance(row, dict):
        mn = int(row.get("mes_num") or row.get("mes") or 0)
        nome = (row.get("mes_nome") or "").strip()
        abrev = row.get("mes_abrev") or ""
    else:
        return 0, "", ""
    if not (1 <= mn <= 12):
        return 0, nome, abrev
    if not abrev:
        try:
            from models.sorteio_diadesorte import mes_abrev_de

            abrev = mes_abrev_de(mn, nome)
        except Exception:
            abrev = str(mn)
    return mn, nome, abrev


def _linha_backtest(
    row: Any,
    sorteadas: set,
    apostas: List[List[int]],
    meses_apostas: Optional[List[int]],
) -> Dict[str, Any]:
    hits = [len(set(ap) & sorteadas) for ap in apostas]
    mx = max(hits) if hits else 0
    idx = hits.index(mx) if hits else 0
    melhor = apostas[idx] if apostas else []
    acertadas = sorted(set(melhor) & sorteadas)
    concurso = getattr(row, "concurso", None) or (row.get("concurso") if isinstance(row, dict) else None)
    data = getattr(row, "data", None) or (row.get("data") if isinstance(row, dict) else "")
    mes_num, mes_nome, mes_abrev = _mes_from_row(row)
    mes_aposta = None
    mes_acertou = False
    if meses_apostas and idx < len(meses_apostas):
        mes_aposta = int(meses_apostas[idx])
        mes_acertou = bool(mes_num and mes_aposta == mes_num)

    return {
        "concurso": concurso,
        "data": data or "",
        "max_acertos": mx,
        "melhor_aposta": melhor,
        "melhor_aposta_fmt": [f"{d:02d}" for d in melhor],
        "acertadas": acertadas,
        "acertadas_fmt": [f"{d:02d}" for d in acertadas],
        "sorteio_dezenas": sorted(sorteadas),
        "sorteio_dezenas_fmt": [f"{d:02d}" for d in sorted(sorteadas)],
        "mes_sorteio": {
            "mes_num": mes_num or None,
            "mes_nome": mes_nome,
            "mes_abrev": mes_abrev,
        },
        "mes_aposta": mes_aposta,
        "mes_acertou": mes_acertou,
    }


def backtest_conjunto(
    apostas: List[List[int]],
    historico_rows: Sequence[Any],
    *,
    meses_apostas: Optional[List[int]] = None,
    max_acertos: int = 7,
    pico_destaque: int = 4,
) -> Dict[str, Any]:
    if not apostas:
        return {"sucesso": False, "erro": "Nenhuma aposta para backtest."}
    if not historico_rows:
        return {"sucesso": False, "erro": "Histórico vazio no banco."}

    sets_hist = _historico_sets(historico_rows)
    metricas = avaliar_conjunto(apostas, sets_hist, max_acertos=max_acertos)

    linhas: List[Dict[str, Any]] = []
    mes_acertos = 0
    for row, sorteadas in zip(historico_rows, sets_hist):
        linha = _linha_backtest(row, sorteadas, apostas, meses_apostas)
        if linha.get("mes_acertou"):
            mes_acertos += 1
        linhas.append(linha)

    linhas.sort(key=lambda x: (-x["max_acertos"], -(x["concurso"] or 0)))

    n = len(linhas)
    metricas_mes: Dict[str, Any] = {}
    if meses_apostas is not None:
        metricas_mes = {
            "mes_acertos": mes_acertos,
            "mes_taxa": round(100.0 * mes_acertos / n, 2) if n else 0.0,
        }
        metricas = {**metricas, **metricas_mes}

    return {
        "sucesso": True,
        "concursos_analisados": n,
        "concurso_de": linhas[-1]["concurso"] if linhas else None,
        "concurso_ate": linhas[0]["concurso"] if linhas else None,
        "metricas": metricas,
        "linhas": linhas,
        "destaques": [l for l in linhas if l["max_acertos"] >= pico_destaque][:12],
        "meses_apostas": meses_apostas,
    }


def validar_criterios(
    metricas: Dict[str, Any],
    cfg: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Critérios simples de aprovação para o painel de validações."""
    cfg = cfg or {}
    pico_min = int(cfg.get("pico_min") or 6)
    media_min = float(cfg.get("media_min") or 3.0)
    aposta = int(cfg.get("aposta_dezenas") or 7)
    ic = float(metricas.get("indice_concentracao") or 0)
    mm = float(metricas.get("media_max_acertos") or 0)
    picos = 0
    for i in range(pico_min, aposta + 1):
        picos += int(metricas.get(f"dist_{i}") or 0)
    checks = [
        {
            "id": "indice",
            "nome": "Índice de concentração ≥ 1,5",
            "ok": ic >= 1.5,
            "valor": ic,
        },
        {
            "id": "media_max",
            "nome": f"Média máx. acertos ≥ {media_min}",
            "ok": mm >= media_min,
            "valor": mm,
        },
        {
            "id": "picos",
            "nome": f"Ao menos 1 concurso com {pico_min}+ acertos",
            "ok": picos >= 1,
            "valor": picos,
        },
    ]
    aprovados = sum(1 for c in checks if c["ok"])
    return {
        "aprovado": aprovados == len(checks),
        "aprovados": aprovados,
        "total": len(checks),
        "checks": checks,
    }


def _atribuir_posicoes_ranking(ranking: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ok = [r for r in ranking if r.get("sucesso")]
    ordenado = sorted(
        ok,
        key=lambda x: (
            -(float(x.get("score") or 0)),
            -(float(x.get("indice_concentracao") or 0)),
        ),
    )
    medalhas = {1: "🥇 1º", 2: "🥈 2º", 3: "🥉 3º"}
    pos_map: Dict[str, int] = {}
    label_map: Dict[str, str] = {}
    for i, r in enumerate(ordenado, 1):
        r["posicao"] = i
        r["posicao_label"] = medalhas.get(i, f"{i}º")
        pos_map[r["estrategia"]] = i
        label_map[r["estrategia"]] = r["posicao_label"]
    for r in ranking:
        if r.get("sucesso"):
            r["posicao"] = pos_map.get(r["estrategia"])
            r["posicao_label"] = label_map.get(r["estrategia"], "—")
    return ordenado


def comparar_estrategias(
    modality_key: str,
    dados_dezenas: List[Dict[str, Any]],
    historico_rows: Sequence[Any],
    *,
    criterio_pool: str = "freq",
    perfil: str = "equilibrado",
    sorteios_moda: Optional[List[List[int]]] = None,
    meses_apostas: Optional[List[int]] = None,
) -> Dict[str, Any]:
    cfg = get_concentracao_config(modality_key)
    moda = distribuicao_historica_moda(sorteios_moda or [])
    ranking: List[Dict[str, Any]] = []

    for est in cfg.get("estrategias", []):
        pool = pool_sugerido(
            dados_dezenas,
            est["pool_size"],
            criterio_pool,
            dezena_min=int(cfg["dezena_min"]),
            dezena_max=int(cfg["dezena_max"]),
        )
        gen = gerar_apostas(
            pool,
            perfil=perfil,
            comportamento_moda=moda,
            seed_salt=est["id"],
            aposta_dezenas=int(cfg["aposta_dezenas"]),
        )
        if not gen.get("sucesso"):
            ranking.append({
                "estrategia": est["id"],
                "nome": est["nome"],
                "pool_size": est["pool_size"],
                "sucesso": False,
                "erro": gen.get("erro"),
            })
            continue
        bt = backtest_conjunto(
            gen["apostas"],
            historico_rows,
            meses_apostas=meses_apostas if cfg.get("extra_mes") else None,
            max_acertos=int(cfg["aposta_dezenas"]),
            pico_destaque=int(cfg.get("pico_min") or max(2, int(cfg["aposta_dezenas"]) - 1)),
        )
        m = bt.get("metricas") or {}
        ranking.append({
            "estrategia": est["id"],
            "nome": est["nome"],
            "pool_size": est["pool_size"],
            "pool": pool,
            "sucesso": True,
            "metricas": m,
            "indice_concentracao": m.get("indice_concentracao"),
            "media_max_acertos": m.get("media_max_acertos"),
            "score": m.get("score"),
            "mes_acertos": m.get("mes_acertos"),
            "mes_taxa": m.get("mes_taxa"),
        })

    ranking_ordenado = _atribuir_posicoes_ranking(ranking)
    return {
        "sucesso": True,
        "ranking": ranking,
        "ranking_ordenado": ranking_ordenado,
        "lider": ranking_ordenado[0] if ranking_ordenado else None,
    }
