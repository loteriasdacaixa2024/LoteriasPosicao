# -*- coding: utf-8 -*-
"""
Diferencial Cruzado — regra de negócio (Mega-Sena → adaptável por modalidade).

1. Subtrair penúltimo do último (posição a posição): sub = último[i] − penúltimo[i]
2. Somar último com a subtração assinada: resultado[i] = último[i] + sub[i]
3. Normalizar para o pool da modalidade e montar «números à apostar» (ordenados).

Tratamento de negativos: valor absoluto (configurável).
Fora do pool: soma dos dígitos; se repetir na sequência, substituir por candidato frequente/atrasado.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Sequence, Tuple


def soma_digitos(n: int) -> int:
    return sum(int(c) for c in str(abs(int(n))))


def calcular_diferencial(
    ultimo: Sequence[int],
    penultimo: Sequence[int],
) -> Dict[str, Any]:
    """Calcula subtração e resultado posição a posição."""
    n = min(len(ultimo), len(penultimo))
    if n == 0:
        return {
            "subtracao_signed": [],
            "subtracao_abs": [],
            "resultado": [],
            "tem_negativos": False,
        }
    sub_signed = [int(ultimo[i]) - int(penultimo[i]) for i in range(n)]
    sub_abs = [abs(x) for x in sub_signed]
    resultado = [int(ultimo[i]) + sub_signed[i] for i in range(n)]
    return {
        "subtracao_signed": sub_signed,
        "subtracao_abs": sub_abs,
        "resultado": resultado,
        "tem_negativos": any(x < 0 for x in sub_signed),
    }


def _candidatos_substituicao(
    usados: set,
    dmin: int,
    dmax: int,
    freq_rank: Optional[List[int]] = None,
    atraso_rank: Optional[List[int]] = None,
) -> List[int]:
    out: List[int] = []
    for src in (freq_rank or [], atraso_rank or [], list(range(dmin, dmax + 1))):
        for c in src:
            c = int(c)
            if dmin <= c <= dmax and c not in usados and c not in out:
                out.append(c)
    return out


def normalizar_sequencia_aposta(
    valores: Sequence[int],
    dmin: int,
    dmax: int,
    negativos_modo: str = "abs",
    freq_rank: Optional[List[int]] = None,
    atraso_rank: Optional[List[int]] = None,
    pad_width: int = 2,
) -> Dict[str, Any]:
    """
    Converte resultado bruto em dezenas válidas para aposta.
    negativos_modo: 'abs' | 'zero' (descarta negativo → usa |v|)
    """
    usados: set = set()
    normalizados: List[int] = []
    avisos: List[str] = []
    detalhes: List[Dict[str, Any]] = []
    subs = _candidatos_substituicao(usados, dmin, dmax, freq_rank, atraso_rank)
    pad = max(1, int(pad_width))

    def fdez(n: int) -> str:
        return f"{int(n):0{pad}d}"

    for idx, bruto in enumerate(valores):
        v = int(bruto)
        passos: List[str] = []
        original = v

        if v < 0:
            if negativos_modo == "abs":
                passos.append(f"negativo {fdez(v)} → {fdez(abs(v))}")
                v = abs(v)
            else:
                passos.append(f"negativo {fdez(v)} → {fdez(abs(v))}")
                v = abs(v)

        tentativas = 0
        while tentativas < 12:
            tentativas += 1
            if v < dmin or v > dmax:
                nv = soma_digitos(v)
                passos.append(f"fora do pool ({fdez(v)}) → soma dígitos {fdez(nv)}")
                v = nv
                if v < dmin or v > dmax:
                    nv2 = max(dmin, min(dmax, v))
                    passos.append(f"ajuste limite pool → {fdez(nv2)}")
                    v = nv2

            if v in usados:
                rep = next((c for c in subs if c not in usados), None)
                if rep is None:
                    rep = next((c for c in range(dmin, dmax + 1) if c not in usados), v)
                passos.append(f"duplicata {fdez(v)} → {fdez(rep)}")
                v = rep

            if dmin <= v <= dmax and v not in usados:
                break

        usados.add(v)
        normalizados.append(v)
        if passos:
            avisos.append(f"Pos. {idx + 1}: {fdez(original)} → {fdez(v)} ({'; '.join(passos)})")
        detalhes.append({"posicao": idx + 1, "bruto": original, "final": v, "passos": passos})

    return {
        "bruto": list(valores),
        "normalizados": normalizados,
        "aposta_ordenada": sorted(normalizados),
        "avisos": avisos,
        "detalhes": detalhes,
        "teve_ajuste": bool(avisos),
    }


def ranking_frequencia(dezenas_por_concurso: List[List[int]], dmin: int, dmax: int) -> List[int]:
    cnt: Counter[int] = Counter()
    for dz in dezenas_por_concurso:
        for d in dz:
            if dmin <= int(d) <= dmax:
                cnt[int(d)] += 1
    todos = list(range(dmin, dmax + 1))
    return sorted(todos, key=lambda d: (-cnt.get(d, 0), d))


def ranking_atraso(
    sorteios_asc: Sequence[Any],
    dezenas_fn,
    dmin: int,
    dmax: int,
) -> List[int]:
    """Maior atraso primeiro (último concurso no fim da lista)."""
    ultimo_conc = sorteios_asc[-1].concurso if sorteios_asc else 0
    visto = {d: 0 for d in range(dmin, dmax + 1)}
    for s in sorteios_asc:
        for d in dezenas_fn(s):
            d = int(d)
            if dmin <= d <= dmax:
                visto[d] = s.concurso
    atrasos = []
    for d in range(dmin, dmax + 1):
        atraso = (ultimo_conc - visto[d]) if visto[d] else ultimo_conc
        atrasos.append((atraso, d))
    atrasos.sort(key=lambda x: (-x[0], x[1]))
    return [d for _, d in atrasos]


def analisar_par(
    ultimo: Sequence[int],
    penultimo: Sequence[int],
    dmin: int,
    dmax: int,
    negativos_modo: str = "abs",
    freq_rank: Optional[List[int]] = None,
    atraso_rank: Optional[List[int]] = None,
    pad_width: int = 2,
) -> Dict[str, Any]:
    diff = calcular_diferencial(ultimo, penultimo)
    aposta = normalizar_sequencia_aposta(
        diff["resultado"],
        dmin,
        dmax,
        negativos_modo=negativos_modo,
        freq_rank=freq_rank,
        atraso_rank=atraso_rank,
        pad_width=pad_width,
    )
    return {
        **diff,
        **aposta,
    }
