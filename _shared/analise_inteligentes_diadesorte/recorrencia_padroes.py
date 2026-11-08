# -*- coding: utf-8 -*-
"""
Recorrência dos padrões iniciais (Dia de Sorte).

O intervalo entre duas ocorrências é a diferença dos números de concurso,
na ordem cronológica. Exemplo: 100, 105, 107, 115, 120 → 5, 2, 8, 5.

A classificação não usa a quantidade de ocorrências como critério:
- mais rápidos: menor média, depois menor mediana, depois menor intervalo;
- mais regulares: menor desvio padrão amostral dividido pela média
  (só com dois intervalos ou mais);
- maior intervalo: o maior vão já registrado entre duas saídas seguidas.
"""
from __future__ import annotations

import math
import time
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

from analise_inteligentes_diadesorte.service import (
    _gerar_padroes_teoricos,
    descricao_bma_do_padrao,
    jogos_possiveis_padrao,
    padrao_inicial,
)

_CACHE: Dict[Tuple[Any, ...], Dict[str, Any]] = {}


def _mediana(valores: Sequence[int]) -> Optional[float]:
    if not valores:
        return None
    orden = sorted(int(v) for v in valores)
    meio = len(orden) // 2
    if len(orden) % 2:
        return float(orden[meio])
    return (orden[meio - 1] + orden[meio]) / 2.0


def _desvio_amostral(valores: Sequence[int]) -> Optional[float]:
    n = len(valores)
    if n < 2:
        return None
    media = sum(valores) / n
    var = sum((float(v) - media) ** 2 for v in valores) / (n - 1)
    return math.sqrt(var)


def intervalos_entre(concursos: Sequence[int]) -> List[int]:
    """Diferenças entre concursos consecutivos, já em ordem crescente."""
    occ = sorted({int(c) for c in concursos if int(c) > 0})
    return [occ[i] - occ[i - 1] for i in range(1, len(occ))]


def resumir_intervalos(
    concursos: Sequence[int],
    ultimo_geral: Optional[int],
) -> Dict[str, Any]:
    """Indicadores de um padrão. Sem intervalo, as medidas ficam vazias."""
    occ = sorted({int(c) for c in concursos if int(c) > 0})
    intervalos = [occ[i] - occ[i - 1] for i in range(1, len(occ))]
    hist = Counter(intervalos)
    modas: List[int] = []
    moda = None
    moda_vezes = None
    if hist:
        pico = max(hist.values())
        modas = sorted(int(k) for k, v in hist.items() if v == pico)
        moda = modas[0]
        moda_vezes = int(pico)
    media = (sum(intervalos) / len(intervalos)) if intervalos else None
    mediana = _mediana(intervalos)
    desvio = _desvio_amostral(intervalos)
    regularidade = None
    if desvio is not None and media:
        regularidade = desvio / media
    desde = None
    if occ and ultimo_geral is not None:
        desde = int(ultimo_geral) - occ[-1]
    return {
        "ocorrencias": len(occ),
        "primeiro_concurso": occ[0] if occ else None,
        "ultimo_concurso": occ[-1] if occ else None,
        "desde_ultima": desde,
        "qtd_intervalos": len(intervalos),
        "intervalos": intervalos,
        "intervalo_medio": round(media, 2) if media is not None else None,
        "intervalo_mediano": round(mediana, 2) if mediana is not None else None,
        "menor_intervalo": min(intervalos) if intervalos else None,
        "maior_intervalo": max(intervalos) if intervalos else None,
        "moda_intervalo": moda,
        "moda_vezes": moda_vezes,
        "moda_empate": len(modas) > 1,
        "modas": modas,
        "regularidade": round(regularidade, 3) if regularidade is not None else None,
        "histograma_intervalos": [
            {"intervalo": int(k), "vezes": int(v)} for k, v in sorted(hist.items())
        ],
        "concursos": occ,
    }


def _chave_rapido(row: Dict[str, Any]) -> Tuple:
    return (
        float(row["intervalo_medio"]),
        float(row["intervalo_mediano"]),
        int(row["menor_intervalo"]),
        str(row.get("padrao") or ""),
    )


def _chave_regular(row: Dict[str, Any]) -> Tuple:
    return (
        float(row["regularidade"]),
        float(row["intervalo_medio"]),
        str(row.get("padrao") or ""),
    )


def _chave_longo(row: Dict[str, Any]) -> Tuple:
    media = row.get("intervalo_medio")
    return (
        -int(row["maior_intervalo"]),
        float(media) if media is not None else 10**9,
        str(row.get("padrao") or ""),
    )


def classificar_recorrencia(rows: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Rankings pelo comportamento dos intervalos, não pela contagem de saídas."""
    com_intervalo = [r for r in rows if int(r.get("qtd_intervalos") or 0) >= 1]
    com_regularidade = [r for r in rows if r.get("regularidade") is not None]
    rapidos = sorted(com_intervalo, key=_chave_rapido)
    regulares = sorted(com_regularidade, key=_chave_regular)
    longos = sorted(com_intervalo, key=_chave_longo)
    return {
        "top_mais_rapidos": rapidos[:3],
        "intervalos_curtos": rapidos[:8],
        "top_regulares": regulares[:3],
        "top_maior_intervalo": longos[:3],
    }


def _cartao(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "n_padrao": row.get("n_padrao"),
        "padrao": row.get("padrao"),
        "descricao": row.get("descricao"),
        "ocorrencias": row.get("ocorrencias"),
        "qtd_intervalos": row.get("qtd_intervalos"),
        "intervalo_medio": row.get("intervalo_medio"),
        "intervalo_mediano": row.get("intervalo_mediano"),
        "menor_intervalo": row.get("menor_intervalo"),
        "maior_intervalo": row.get("maior_intervalo"),
        "moda_intervalo": row.get("moda_intervalo"),
        "moda_vezes": row.get("moda_vezes"),
        "moda_empate": row.get("moda_empate"),
        "modas": row.get("modas") or [],
        "regularidade": row.get("regularidade"),
        "desde_ultima": row.get("desde_ultima"),
        "ultimo_concurso": row.get("ultimo_concurso"),
    }


def montar_recorrencia(svc, *, base: str = "geral") -> Dict[str, Any]:
    """Varre o histórico real, em ordem de concurso, para os 85 padrões."""
    t0 = time.perf_counter()
    lim = svc._limites()
    dmin = int(lim["min_dezena"])
    dmax = int(lim["max_dezena"])
    k = int(lim["tamanho_jogo"])

    dados = svc.listar_resultados(janela=0, base=base)
    linhas = list(dados.get("linhas") or [])
    concursos_geral = [int(l.get("concurso") or 0) for l in linhas if int(l.get("concurso") or 0) > 0]
    total = len(concursos_geral)
    primeiro = min(concursos_geral) if concursos_geral else dados.get("primeiro_concurso")
    ultimo = max(concursos_geral) if concursos_geral else dados.get("ultimo_concurso")
    cache_key = (
        getattr(svc, "modality_key", ""),
        str(base or "geral"),
        int(ultimo or 0),
        int(total),
        dmin,
        dmax,
        k,
    )
    hit = _CACHE.get(cache_key)
    if hit:
        out = dict(hit)
        out["cache_hit"] = True
        out["elapsed_ms"] = int((time.perf_counter() - t0) * 1000)
        return out

    teoricos = _gerar_padroes_teoricos(k, min_dezena=dmin, max_dezena=dmax)
    occ: Dict[str, List[int]] = defaultdict(list)
    for l in linhas:
        conc = int(l.get("concurso") or 0)
        if conc <= 0:
            continue
        pad = str(l.get("padrao_inicial") or "").strip()
        if not pad:
            dez = [int(x) for x in (l.get("dezenas") or []) if str(x).strip() != ""]
            if dez:
                pad = padrao_inicial(sorted(dez))
        if pad:
            occ[pad].append(conc)

    padroes_set = list(dict.fromkeys(list(teoricos) + [p for p in occ if p not in teoricos]))
    bruto: List[Dict[str, Any]] = []
    for p in padroes_set:
        stats = resumir_intervalos(occ.get(p) or [], int(ultimo) if ultimo is not None else None)
        bruto.append({
            "padrao": p,
            "descricao": descricao_bma_do_padrao(p),
            "jogos_possiveis": jogos_possiveis_padrao(p, min_dezena=dmin, max_dezena=dmax),
            **stats,
        })

    ordem_num = sorted(
        bruto,
        key=lambda r: (-int(r["ocorrencias"]), -int(r["jogos_possiveis"]), str(r["padrao"])),
    )
    for i, row in enumerate(ordem_num, start=1):
        row["n_padrao"] = i

    ranks = classificar_recorrencia(bruto)
    com_intervalo = sum(1 for r in bruto if int(r["qtd_intervalos"]) >= 1)
    uma_vez = sum(1 for r in bruto if int(r["ocorrencias"]) == 1)
    nunca = sum(1 for r in bruto if int(r["ocorrencias"]) == 0)

    payload = {
        "sucesso": True,
        "base": base,
        "total_concursos": total,
        "primeiro_concurso": primeiro,
        "ultimo_concurso": ultimo,
        "total_padroes": len(bruto),
        "padroes_com_intervalo": com_intervalo,
        "padroes_uma_vez": uma_vez,
        "padroes_nunca": nunca,
        "top_mais_rapidos": [_cartao(r) for r in ranks["top_mais_rapidos"]],
        "intervalos_curtos": [_cartao(r) for r in ranks["intervalos_curtos"]],
        "top_regulares": [_cartao(r) for r in ranks["top_regulares"]],
        "top_maior_intervalo": [_cartao(r) for r in ranks["top_maior_intervalo"]],
        "padroes": sorted(bruto, key=lambda r: int(r["n_padrao"])),
        "criterio": {
            "intervalo": "Diferença entre os números de concursos consecutivos do mesmo padrão.",
            "desde_ultima": "Último concurso do histórico menos o último concurso do padrão.",
            "regularidade": "Desvio padrão amostral dos intervalos dividido pela média. Quanto menor, mais estável. Exige pelo menos dois intervalos.",
            "mais_rapidos": "Menor intervalo médio; empate pela menor mediana; depois pelo menor intervalo.",
            "ocorrencias": "A quantidade de saídas não ordena estes rankings.",
        },
        "api": "/analise/api/inteligentes/recorrencia-padroes",
    }
    _CACHE[cache_key] = payload
    if len(_CACHE) > 8:
        for old in list(_CACHE.keys())[:-4]:
            _CACHE.pop(old, None)
    out = dict(payload)
    out["cache_hit"] = False
    out["elapsed_ms"] = int((time.perf_counter() - t0) * 1000)
    return out
