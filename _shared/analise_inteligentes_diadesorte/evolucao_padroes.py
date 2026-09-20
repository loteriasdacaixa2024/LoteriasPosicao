# -*- coding: utf-8 -*-
"""
Evolução histórica dos padrões iniciais (ABA 4 · Padrões II).

Não regenera as milhares de apostas de cada padrão: o índice da aposta
vencedora usa a mesma ordem de `expandir_jogos_padrao`, via rank no
produto das combinações por dígito.
"""
from __future__ import annotations

import time
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple

from analise_inteligentes_diadesorte.diagonais_volante import diagonais_na_aposta
from analise_inteligentes_diadesorte.service import (
    _gerar_padroes_teoricos,
    descricao_bma_do_padrao,
    indice_aposta_no_padrao,
    jogos_possiveis_padrao,
    padrao_inicial,
    status_padrao,
)

_CACHE: Dict[Tuple[Any, ...], Dict[str, Any]] = {}


def _fmt_diagonais(dezenas, *, dmin: int, dmax: int) -> Tuple[str, List[Dict[str, Any]]]:
    runs = diagonais_na_aposta(dezenas, dmin=dmin, dmax=dmax, cols=10)
    if not runs:
        return "Nenhuma", []
    compacto = [
        {
            "dir": r.get("dir"),
            "dir_sym": r.get("dir_sym"),
            "nums_fmt": r.get("nums_fmt"),
            "len": r.get("len"),
            "tipo": r.get("tipo"),
        }
        for r in runs
    ]
    texto = ", ".join(
        f"{(r.get('dir_sym') or '').strip()} {r.get('nums_fmt') or ''}".strip()
        for r in compacto
    )
    return texto or "Nenhuma", compacto


def _stats_ocorrencias(
    concursos: List[int],
    *,
    total_concursos: int,
    ultimo_concurso: Optional[int],
    atraso: Optional[int],
) -> Dict[str, Any]:
    occ = sorted({int(c) for c in concursos if c})
    n = len(occ)
    intervalos: List[int] = []
    hist: Counter = Counter()
    maior = None
    for i in range(1, n):
        gap = int(occ[i]) - int(occ[i - 1])
        intervalos.append(gap)
        hist[gap] += 1
        if maior is None or gap > maior:
            maior = gap
    return {
        "ocorrencias": n,
        "percentual": round(100.0 * n / max(1, int(total_concursos)), 2),
        "primeiro_concurso": occ[0] if n else None,
        "ultimo_concurso": occ[-1] if n else None,
        "concurso_anterior": occ[-2] if n >= 2 else None,
        "intervalos": intervalos,
        "maior_intervalo": maior,
        "atraso": atraso if n else (None if ultimo_concurso is None else None),
        "histograma_intervalos": [
            {"intervalo": int(k), "vezes": int(v)} for k, v in sorted(hist.items())
        ],
        "concursos": occ,
    }


def montar_evolucao(svc, *, base: str = "geral") -> Dict[str, Any]:
    """Monta o painel histórico. Cache por modalidade + último concurso."""
    t0 = time.perf_counter()
    lim = svc._limites()
    dmin = int(lim["min_dezena"])
    dmax = int(lim["max_dezena"])
    k = int(lim["tamanho_jogo"])

    dados = svc.listar_resultados(janela=0, base=base)
    linhas_src = list(dados.get("linhas") or [])
    total = len(linhas_src)
    primeiro = dados.get("primeiro_concurso")
    ultimo = dados.get("ultimo_concurso")
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
    n_por_padrao = {p: i + 1 for i, p in enumerate(teoricos)}
    jogos_por_padrao = {
        p: jogos_possiveis_padrao(p, min_dezena=dmin, max_dezena=dmax) for p in teoricos
    }

    # listar_resultados vem mais recente primeiro
    atraso_por_padrao: Dict[str, int] = {}
    occ_por_padrao: Dict[str, List[int]] = defaultdict(list)
    crono: List[Dict[str, Any]] = []
    for idx, l in enumerate(linhas_src):
        dez = [int(x) for x in (l.get("dezenas") or []) if str(x).strip() != ""]
        pad = str(l.get("padrao_inicial") or "").strip()
        if not pad and dez:
            pad = padrao_inicial(sorted(dez))
        conc = int(l.get("concurso") or 0)
        if pad:
            occ_por_padrao[pad].append(conc)
            if pad not in atraso_por_padrao:
                atraso_por_padrao[pad] = idx
        crono.append({
            "concurso": conc,
            "data": l.get("data") or "",
            "dezenas": sorted(dez) if dez else [],
            "dezenas_fmt": l.get("dezenas_fmt") or "",
            "padrao": pad,
            "soma": int(l.get("soma") or 0),
        })

    crono.sort(key=lambda r: int(r["concurso"] or 0))
    atrasos_com_freq = list(atraso_por_padrao.values())
    atraso_mediano = 10.0
    if atrasos_com_freq:
        orden = sorted(atrasos_com_freq)
        mid = len(orden) // 2
        atraso_mediano = (
            float(orden[mid]) if len(orden) % 2 else (orden[mid - 1] + orden[mid]) / 2.0
        )

    linhas: List[Dict[str, Any]] = []
    pad_ant = None
    for r in crono:
        pad = r["padrao"]
        dez = r["dezenas"]
        mudou = bool(pad_ant is not None and pad != pad_ant)
        aposta_n = indice_aposta_no_padrao(
            dez, pad, min_dezena=dmin, max_dezena=dmax,
        ) if (dez and pad) else None
        diag_fmt, diags = _fmt_diagonais(dez, dmin=dmin, dmax=dmax) if dez else ("Nenhuma", [])
        n_pad = n_por_padrao.get(pad)
        linhas.append({
            "concurso": r["concurso"],
            "data": r["data"],
            "dezenas_fmt": r["dezenas_fmt"] or " ".join(f"{d:02d}" for d in dez),
            "padrao": pad,
            "n_padrao": n_pad,
            "descricao": descricao_bma_do_padrao(pad) if pad else "",
            "jogos_possiveis": jogos_por_padrao.get(pad) or (
                jogos_possiveis_padrao(pad, min_dezena=dmin, max_dezena=dmax) if pad else 0
            ),
            "aposta_n": aposta_n,
            "soma": r["soma"] or (sum(dez) if dez else 0),
            "diagonal_fmt": diag_fmt,
            "diagonais": diags,
            "mudou": mudou,
            "situacao": "Mudou" if mudou else ("Mantido" if pad_ant is not None else "Início"),
            "padrao_anterior": pad_ant,
            "n_padrao_anterior": n_por_padrao.get(pad_ant) if pad_ant else None,
        })
        pad_ant = pad

    padroes_set = set(teoricos) | set(occ_por_padrao.keys())
    consolidado: List[Dict[str, Any]] = []
    for p in sorted(padroes_set, key=lambda x: n_por_padrao.get(x, 10_000)):
        freq = len(occ_por_padrao.get(p) or [])
        atraso = atraso_por_padrao.get(p) if freq else None
        st = status_padrao(freq, atraso, atraso_mediano)
        stats = _stats_ocorrencias(
            occ_por_padrao.get(p) or [],
            total_concursos=total,
            ultimo_concurso=int(ultimo) if ultimo is not None else None,
            atraso=atraso,
        )
        if freq <= 0:
            stats["atraso"] = None
            st_ui = "ainda_nao_saiu"
        else:
            st_ui = st
        consolidado.append({
            "n_padrao": n_por_padrao.get(p),
            "padrao": p,
            "descricao": descricao_bma_do_padrao(p),
            "jogos_possiveis": jogos_por_padrao.get(p) or jogos_possiveis_padrao(
                p, min_dezena=dmin, max_dezena=dmax,
            ),
            "frequencia": freq,
            "percentual": stats["percentual"],
            "primeiro_concurso": stats["primeiro_concurso"],
            "ultimo_concurso": stats["ultimo_concurso"],
            "concurso_anterior": stats["concurso_anterior"],
            "intervalos": stats["intervalos"],
            "maior_intervalo": stats["maior_intervalo"],
            "atraso": stats["atraso"],
            "histograma_intervalos": stats["histograma_intervalos"],
            "concursos": stats["concursos"],
            "status": st_ui,
            "utilizado": freq > 0,
        })

    n_util = sum(1 for r in consolidado if r["utilizado"])
    n_falt = sum(1 for r in consolidado if not r["utilizado"])
    n_mudancas = sum(1 for r in linhas if r.get("mudou"))
    ultimo_linha = linhas[-1] if linhas else None

    payload = {
        "sucesso": True,
        "base": base,
        "total_concursos": total,
        "primeiro_concurso": primeiro,
        "ultimo_concurso": ultimo,
        "total_padroes": len(consolidado),
        "padroes_utilizados": n_util,
        "padroes_nao_utilizados": n_falt,
        "trocas_padrao": n_mudancas,
        "ultimo": {
            "concurso": (ultimo_linha or {}).get("concurso"),
            "data": (ultimo_linha or {}).get("data") or "",
            "padrao": (ultimo_linha or {}).get("padrao") or "",
            "n_padrao": (ultimo_linha or {}).get("n_padrao"),
            "aposta_n": (ultimo_linha or {}).get("aposta_n"),
            "dezenas_fmt": (ultimo_linha or {}).get("dezenas_fmt") or "",
            "soma": (ultimo_linha or {}).get("soma"),
            "diagonal_fmt": (ultimo_linha or {}).get("diagonal_fmt") or "",
        } if ultimo_linha else None,
        "linhas": linhas,
        "padroes": consolidado,
        "nao_utilizados": [r for r in consolidado if not r["utilizado"]],
        "api": "/analise/api/inteligentes/evolucao-padroes",
    }
    _CACHE[cache_key] = payload
    if len(_CACHE) > 8:
        # mantém só as entradas mais recentes
        for old in list(_CACHE.keys())[:-4]:
            _CACHE.pop(old, None)
    out = dict(payload)
    out["cache_hit"] = False
    out["elapsed_ms"] = int((time.perf_counter() - t0) * 1000)
    return out
