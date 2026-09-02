# -*- coding: utf-8 -*-
"""Análise de gaps e perfil de ciclos a partir do histórico oficial."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional

from analise_estudos.service_factory import make_estudos_base
from analise_gaps_ciclo.core import (
    ciclos_perfil,
    dezenas_ordenadas,
    dezenas_sequencia,
    gaps_de,
    gaps_sequencia,
    montar_por_ciclos,
    montar_ranking_comparativo,
    norm_leitura,
    padrao_gaps,
    parse_padrao_gaps,
)
from analise_gaps_ciclo.specs import get_gaps_ciclo_spec, tem_gaps_ciclo


def _fmt(n: int, pad: int) -> str:
    return str(int(n)).zfill(int(pad))


def _fmt_lista(nums, pad: int) -> str:
    return " ".join(_fmt(d, pad) for d in (nums or []))


def _moda_passos(por_passo: List[Counter]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for i, cnt in enumerate(por_passo):
        if not cnt:
            out.append({"passo": i + 1, "moda": None, "vezes": 0})
            continue
        g, v = cnt.most_common(1)[0]
        out.append({"passo": i + 1, "moda": int(g), "vezes": int(v)})
    return out


def _top_padroes(freq: Counter, limite: int = 20) -> List[Dict[str, Any]]:
    return [
        {"padrao": p, "gaps": parse_padrao_gaps(p), "frequencia": int(c)}
        for p, c in freq.most_common(limite)
        if p
    ]


def _agregar(linhas: List[Dict[str, Any]], gaps_key: str, padrao_key: str, passos: int):
    freq_valor: Counter = Counter()
    freq_padrao: Counter = Counter()
    por_passo: List[Counter] = [Counter() for _ in range(passos)]
    for row in linhas:
        gaps = row.get(gaps_key) or []
        freq_padrao[row.get(padrao_key) or ""] += 1
        for i, g in enumerate(gaps):
            freq_valor[int(g)] += 1
            if i < passos:
                por_passo[i][int(g)] += 1
    return freq_valor, freq_padrao, por_passo


def _linhas(modality_key: str, janela: int, base: str) -> List[Dict[str, Any]]:
    Base = make_estudos_base(modality_key)
    rows = Base.carregar_sorteios_asc(base_estatistica=base or "geral", janela=int(janela or 0))
    pad = int(get_gaps_ciclo_spec(modality_key)["pad_width"])
    out: List[Dict[str, Any]] = []
    for s in reversed(rows):  # mais recente primeiro
        sorteio = dezenas_sequencia(Base.dezenas_ordem(s))
        clas = dezenas_ordenadas(sorteio)
        gaps_c = gaps_de(clas)
        gaps_s = gaps_sequencia(sorteio)
        pad_c = padrao_gaps(gaps_c)
        pad_s = padrao_gaps(gaps_s)
        iguais = pad_c == pad_s
        out.append({
            "concurso": getattr(s, "concurso", None),
            "data": getattr(s, "data", "") or "",
            "dezenas": clas,
            "dezenas_fmt": _fmt_lista(clas, pad),
            "dezenas_classificado": clas,
            "dezenas_classificado_fmt": _fmt_lista(clas, pad),
            "dezenas_sorteio": sorteio,
            "dezenas_sorteio_fmt": _fmt_lista(sorteio, pad),
            "gaps": gaps_c,
            "gaps_classificado": gaps_c,
            "gaps_sorteio": gaps_s,
            "padrao": pad_c,
            "padrao_classificado": pad_c,
            "padrao_sorteio": pad_s,
            "padroes_iguais": iguais,
        })
    return out


def analisar_gaps(modality_key: str, *, janela: int = 0, base: str = "geral") -> Dict[str, Any]:
    if not tem_gaps_ciclo(modality_key):
        return {"sucesso": False, "erro": "Modalidade sem análise de gaps."}
    spec = get_gaps_ciclo_spec(modality_key)
    linhas = _linhas(modality_key, janela, base)
    k = int(spec["sorteadas"])
    passos = max(0, k - 1)
    freq_c, pad_c, passo_c = _agregar(linhas, "gaps_classificado", "padrao_classificado", passos)
    freq_s, pad_s, passo_s = _agregar(linhas, "gaps_sorteio", "padrao_sorteio", passos)
    ranking = montar_ranking_comparativo(pad_c, pad_s, limite=20)
    coincidem = sum(1 for r in linhas if r.get("padroes_iguais"))
    ultimo = linhas[0] if linhas else None
    return {
        "sucesso": True,
        "sessao": "gaps",
        "spec": spec,
        "janela": int(janela or 0),
        "base": base or "geral",
        "total_concursos": len(linhas),
        "coincidem": coincidem,
        "divergem": max(0, len(linhas) - coincidem),
        "ultimo": ultimo,
        "top_padroes": _top_padroes(pad_c),
        "top_padroes_sorteio": _top_padroes(pad_s),
        "top_valores": [
            {"gap": int(g), "frequencia": int(c)}
            for g, c in freq_c.most_common(15)
        ],
        "top_valores_sorteio": [
            {"gap": int(g), "frequencia": int(c)}
            for g, c in freq_s.most_common(15)
        ],
        "moda_por_passo": _moda_passos(passo_c),
        "moda_por_passo_sorteio": _moda_passos(passo_s),
        "ranking_comparativo": ranking,
        "confronto": linhas[:80],
        "linhas": linhas[:80],
    }


def _passos_aposta(aposta, ciclos, pad: int) -> List[Dict[str, Any]]:
    passos = []
    if not aposta:
        return passos
    prev = aposta[0]
    passos.append({"posicao": 1, "dezena": prev, "ciclo": None, "origem": "inicial"})
    for i, c in enumerate(ciclos, start=2):
        if i - 1 >= len(aposta):
            break
        nxt = aposta[i - 1]
        passos.append({
            "posicao": i,
            "dezena": nxt,
            "ciclo": int(c),
            "origem": f"{_fmt(prev, pad)} + {c}",
        })
        prev = nxt
    return passos


def projetar_ciclo(
    modality_key: str,
    inicial: int,
    *,
    janela: int = 0,
    base: str = "geral",
    perfil: str = "ultimo",
    padrao: Optional[str] = None,
    leitura: str = "classificado",
    gaps_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    spec = get_gaps_ciclo_spec(modality_key)
    permitidas = set(spec["iniciais_permitidas"])
    ini = int(inicial)
    pad = int(spec["pad_width"])
    if ini not in permitidas:
        return {
            "sucesso": False,
            "erro": (
                f"Inicial {_fmt(ini, pad)} fora da faixa "
                f"{_fmt(spec['inicial_min'], pad)}–"
                f"{_fmt(spec['inicial_max'], pad)}."
            ),
            "spec": spec,
        }
    if not gaps_info:
        gaps_info = analisar_gaps(modality_key, janela=janela, base=base)
    if not gaps_info.get("sucesso"):
        return gaps_info
    leitura_n = norm_leitura(leitura)
    k = int(spec["sorteadas"])

    def _uma(lei: str) -> Dict[str, Any]:
        ciclos = ciclos_perfil(gaps_info, perfil=perfil, padrao=padrao, leitura=lei)
        if len(ciclos) != k - 1:
            return {
                "sucesso": False,
                "leitura": lei,
                "erro": f"O perfil de ciclo tem {len(ciclos)} passo(s); a aposta exige {k - 1}.",
                "ciclos": ciclos,
                "aposta": None,
                "viavel": False,
            }
        aposta = montar_por_ciclos(
            ini, ciclos, dezena_min=spec["dezena_min"], dezena_max=spec["dezena_max"],
        )
        return {
            "sucesso": True,
            "leitura": lei,
            "ciclos": ciclos,
            "padrao": padrao_gaps(ciclos),
            "aposta": aposta,
            "aposta_fmt": _fmt_lista(aposta, pad),
            "viavel": bool(aposta) and len(aposta) == k,
            "passos": _passos_aposta(aposta, ciclos, pad),
        }

    principal = _uma("sorteio" if leitura_n == "sorteio" else "classificado")
    outra = _uma("classificado" if leitura_n == "sorteio" else "sorteio")
    out = {
        "sucesso": bool(principal.get("sucesso")),
        "sessao": "inicial_ciclo",
        "spec": spec,
        "inicial": ini,
        "perfil": perfil,
        "leitura": leitura_n,
        "ultimo_concurso": (gaps_info.get("ultimo") or {}).get("concurso"),
        "classificado": principal if leitura_n != "sorteio" else outra,
        "sorteio": principal if leitura_n == "sorteio" else outra,
    }
    out.update({k: principal.get(k) for k in (
        "ciclos", "padrao", "aposta", "aposta_fmt", "viavel", "passos", "erro",
    )})
    if not principal.get("sucesso"):
        out["sucesso"] = False
    return out


def contexto_analise(
    modality_key: str,
    *,
    janela: int = 0,
    base: str = "geral",
    inicial: Optional[int] = None,
    perfil: str = "ultimo",
    padrao: Optional[str] = None,
    leitura: str = "ambos",
) -> Dict[str, Any]:
    spec = get_gaps_ciclo_spec(modality_key)
    s1 = analisar_gaps(modality_key, janela=janela, base=base)
    ini = int(inicial) if inicial not in (None, "") else spec["inicial_min"]
    s2 = projetar_ciclo(
        modality_key, ini, janela=janela, base=base, perfil=perfil, padrao=padrao,
        leitura=leitura, gaps_info=s1 if s1.get("sucesso") else None,
    )
    return {
        "sucesso": True,
        "spec": spec,
        "sessao1": s1,
        "sessao2": s2,
    }
