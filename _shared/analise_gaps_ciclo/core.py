# -*- coding: utf-8 -*-
"""Cálculo puro de gaps e progressão por ciclo (sem Flask/DB)."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Sequence


def dezenas_ordenadas(nums: Iterable[int]) -> List[int]:
    """Classificado: ordem crescente, como a Caixa divulga o resultado."""
    return sorted({int(x) for x in nums})


def dezenas_sequencia(nums: Iterable[int]) -> List[int]:
    """Ordem de sorteio: posições na sequência em que saíram (d1, d2, …)."""
    return [int(x) for x in nums]


def gaps_de(dezenas: Sequence[int]) -> List[int]:
    """Gaps na leitura classificada (sempre positivos)."""
    dz = dezenas_ordenadas(dezenas)
    if len(dz) < 2:
        return []
    return [dz[i] - dz[i - 1] for i in range(1, len(dz))]


def gaps_sequencia(dezenas: Sequence[int]) -> List[int]:
    """Gaps na ordem de sorteio (com sinal: sobe +, desce −)."""
    dz = dezenas_sequencia(dezenas)
    if len(dz) < 2:
        return []
    return [dz[i] - dz[i - 1] for i in range(1, len(dz))]


def padrao_gaps(gaps: Sequence[int]) -> str:
    return " ".join(str(int(g)) for g in gaps)


def parse_padrao_gaps(raw: str) -> List[int]:
    out: List[int] = []
    for tok in str(raw or "").replace(",", " ").split():
        if not tok.lstrip("-").isdigit():
            continue
        n = int(tok)
        if n != 0:
            out.append(n)
    return out


def montar_ranking_comparativo(
    freq_classificado: Counter,
    freq_sorteio: Counter,
    *,
    limite: int = 20,
) -> List[Dict[str, Any]]:
    """Ranking único: padrões das duas leituras, com bônus se aparecerem nas duas."""
    chaves = set(freq_classificado) | set(freq_sorteio)
    rows: List[Dict[str, Any]] = []
    for p in chaves:
        if not p:
            continue
        fc = int(freq_classificado.get(p, 0))
        fs = int(freq_sorteio.get(p, 0))
        ambos = fc > 0 and fs > 0
        score = fc + fs + (min(fc, fs) if ambos else 0)
        fonte = "ambos" if ambos else ("classificado" if fc else "sorteio")
        rows.append({
            "padrao": p,
            "gaps": parse_padrao_gaps(p),
            "freq_classificado": fc,
            "freq_sorteio": fs,
            "em_ambos": ambos,
            "fonte": fonte,
            "score": score,
        })
    rows.sort(key=lambda r: (-r["score"], -r["freq_classificado"], -r["freq_sorteio"], r["padrao"]))
    for i, r in enumerate(rows[:limite], start=1):
        r["rank"] = i
        r["recomendado"] = i <= 8
    return rows[:limite]


def montar_por_ciclos(
    inicial: int,
    ciclos: Sequence[int],
    *,
    dezena_min: int,
    dezena_max: int,
) -> Optional[List[int]]:
    """POS1 = inicial; POSn = anterior + ciclo. Falha se sair do universo ou repetir."""
    start = int(inicial)
    if start < int(dezena_min) or start > int(dezena_max):
        return None
    pos = [start]
    seen = {start}
    for c in ciclos:
        nxt = pos[-1] + int(c)
        if nxt < int(dezena_min) or nxt > int(dezena_max) or nxt in seen:
            return None
        pos.append(nxt)
        seen.add(nxt)
    return pos


def viavel(
    inicial: int,
    ciclos: Sequence[int],
    *,
    dezena_min: int,
    dezena_max: int,
    sorteadas: int,
) -> bool:
    ap = montar_por_ciclos(inicial, ciclos, dezena_min=dezena_min, dezena_max=dezena_max)
    return bool(ap) and len(ap) == int(sorteadas)


def ciclos_entre(dezenas: Sequence[int]) -> List[int]:
    """Alias explícito: o ciclo entre posições consecutivas é o gap."""
    return gaps_de(dezenas)


def ciclos_perfil(
    analise: Dict[str, Any],
    perfil: str = "ultimo",
    padrao: Optional[str] = None,
    leitura: str = "classificado",
) -> List[int]:
    perfil = (perfil or "ultimo").strip().lower()
    leitura = norm_leitura(leitura)
    if padrao:
        return parse_padrao_gaps(padrao)
    if perfil == "moda_posicao":
        chave = "moda_por_passo_sorteio" if leitura == "sorteio" else "moda_por_passo"
        out = []
        for p in analise.get(chave) or analise.get("moda_por_passo") or []:
            g = p.get("moda")
            if g is None:
                return []
            out.append(int(g))
        return out
    if perfil in ("frequente", "top"):
        if leitura == "sorteio":
            tops = analise.get("top_padroes_sorteio") or []
        elif leitura == "ambos":
            tops = analise.get("ranking_comparativo") or analise.get("top_padroes") or []
        else:
            tops = analise.get("top_padroes") or []
        if tops:
            return list(tops[0].get("gaps") or parse_padrao_gaps(tops[0].get("padrao") or ""))
    ultimo = analise.get("ultimo") or {}
    if leitura == "sorteio":
        return list(ultimo.get("gaps_sorteio") or ultimo.get("gaps") or [])
    return list(ultimo.get("gaps_classificado") or ultimo.get("gaps") or [])


def norm_leitura(leitura: Optional[str]) -> str:
    v = (leitura or "classificado").strip().lower()
    if v in ("sorteio", "ordem", "ordem_sorteio"):
        return "sorteio"
    if v in ("ambos", "comparativo", "ranking"):
        return "ambos"
    return "classificado"
