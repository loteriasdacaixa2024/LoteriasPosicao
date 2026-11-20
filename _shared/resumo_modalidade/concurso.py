# -*- coding: utf-8 -*-
"""Retrato de um concurso do Dia de Sorte, na ordem do Resumo dos Resultados.

Reusa 2a, 2a1, gaps, régua, faixas e geometria. Não recalcula essas regras.
"""
from __future__ import annotations

import time
from collections import Counter
from typing import Any, Dict, List, Optional, Sequence

_CACHE: Dict[str, Any] = {"t": 0.0, "rows": None}
_CACHE_S = 45.0
_AMOSTRA_POS = 14
_NOME_POS = (
    "Primeira posição",
    "Segunda posição",
    "Terceira posição",
    "Quarta posição",
    "Quinta posição",
    "Sexta posição",
    "Sétima posição",
)


def _fmt(n: int) -> str:
    return f"{int(n):02d}"


def _juntar(nums: Sequence[int], sep: str = " ") -> str:
    return sep.join(_fmt(n) for n in nums)


def _qtd_linha(qtd: int, nums: Sequence[int]) -> str:
    lista = _juntar(nums)
    n = str(max(0, int(qtd)))
    return f"{n} | {lista}" if lista else n


def _mes_curto(nome: str) -> str:
    abrev = {
        "janeiro": "Jan", "fevereiro": "Fev", "março": "Mar", "marco": "Mar",
        "abril": "Abr", "maio": "Mai", "junho": "Jun", "julho": "Jul",
        "agosto": "Ago", "setembro": "Set", "outubro": "Out",
        "novembro": "Nov", "dezembro": "Dez",
    }
    bruto = (nome or "").strip()
    if not bruto:
        return "—"
    return abrev.get(bruto.lower(), bruto[:3])


def _linhas_sorteio(modality_key: str) -> List[Dict[str, Any]]:
    agora = time.time()
    if _CACHE["rows"] is not None and agora - float(_CACHE["t"]) < _CACHE_S:
        return _CACHE["rows"]
    from analise_escolha_visual.service import AnaliseEscolhaVisualService

    lista = AnaliseEscolhaVisualService.listar_sorteios(
        modality_key, ordem="asc", limite=0, base_estatistica="geral",
    )
    if not lista.get("sucesso"):
        raise RuntimeError(lista.get("erro") or "Sem sorteios.")
    rows = list(lista.get("sorteios") or [])
    _CACHE["t"] = agora
    _CACHE["rows"] = rows
    return rows


def _texto_sequencias(grupos: Sequence[Sequence[int]]) -> str:
    partes = [" ".join(_fmt(n) for n in g) for g in grupos if len(g) >= 2]
    return " · ".join(partes) if partes else "—"


def _texto_finais(grupos: Sequence[Sequence[int]]) -> str:
    partes = [",".join(_fmt(n) for n in g) for g in grupos if len(g) >= 2]
    return " · ".join(partes) if partes else "—"


def _texto_diagonais(grupos: Sequence[Dict[str, Any]]) -> str:
    partes = []
    for g in grupos:
        nums = g.get("nums") or []
        if len(nums) < 2:
            continue
        corpo = "-".join(_fmt(n) for n in nums)
        sim = g.get("dir_sym") or ""
        partes.append(f"{sim} | {corpo}" if sim else corpo)
    return " · ".join(partes) if partes else "—"


def _texto_regua(posicoes: Sequence[Dict[str, Any]]) -> str:
    if not posicoes:
        return "—"
    return " · ".join(
        f"P{p['posicao']} {_fmt(p['dezena'])} {int(p['deslocamento']):+d}"
        for p in posicoes
        if p.get("dezena") is not None and p.get("deslocamento") is not None
    ) or "—"


def _texto_geometria(ind: Dict[str, Any]) -> str:
    conc = ind.get("concentracao") or {}
    faixas = conc.get("faixas") or {}
    linhas_mais = " · ".join(str(x) for x in (conc.get("linhas_mais") or [])) or "—"
    disp = ind.get("dispersao") or {}
    dist = ind.get("distancias") or {}
    par = " – ".join(_fmt(n) for n in (dist.get("par_maior") or []))
    maior = f"{dist.get('maior')}"
    if par:
        maior = f"{maior} ({par})"
    return (
        f"linhas {ind.get('linhas_fmt') or '—'} · "
        f"centro {(ind.get('centro') or {}).get('rotulo') or '—'} · "
        f"linhas {linhas_mais} · faixa {conc.get('faixa_mais') or '—'} "
        f"(esquerda {faixas.get('esquerda', 0)}, centro {faixas.get('centro', 0)}, "
        f"direita {faixas.get('direita', 0)}) · "
        f"índice {disp.get('indice', '—')} · "
        f"desvio linha {disp.get('desvio_linha', '—')} · "
        f"desvio coluna {disp.get('desvio_coluna', '—')} · "
        f"distância média {dist.get('media', '—')} · maior {maior}"
    )


def _posicoes_amostra(rows: Sequence[Dict[str, Any]], idx: int) -> Optional[Dict[str, Any]]:
    """Dezenas que não saíram em cada posição da ordem de sorteio.

    A amostra são os concursos anteriores ao retrato, no máximo 14.
    """
    ini = max(0, idx - _AMOSTRA_POS)
    amostra = list(rows[ini:idx])
    if not amostra:
        return None
    universo = set(range(1, 32))
    itens = []
    for p in range(7):
        seq = []
        for s in amostra:
            nums = s.get("numeros") or []
            if len(nums) > p:
                seq.append(int(nums[p]))
        cont = Counter(seq)
        ausentes = sorted(universo - set(cont))
        vezes = max(cont.values()) if cont else 0
        repetidas = sorted(n for n, k in cont.items() if vezes > 1 and k == vezes)
        itens.append({
            "posicao": p + 1,
            "nome": _NOME_POS[p],
            "ausentes": len(ausentes),
            "dezenas": [_fmt(n) for n in ausentes],
            "repetidas": [_fmt(n) for n in repetidas],
        })
    return {
        "quantidade": len(amostra),
        "de": int(amostra[0]["concurso"]),
        "ate": int(amostra[-1]["concurso"]),
        "itens": itens,
    }


def retrato_concurso(modality_key: str, concurso: Optional[int] = None) -> Dict[str, Any]:
    """Um concurso. A lista `itens` já sai na ordem em que a página mostra."""
    if (modality_key or "").strip().lower() != "diadesorte":
        return {"sucesso": False, "erro": "Resumo do concurso disponível no Dia de Sorte."}
    try:
        rows = _linhas_sorteio(modality_key)
    except Exception as exc:
        return {"sucesso": False, "erro": str(exc)}
    if not rows:
        return {"sucesso": False, "erro": "Sem concursos."}

    idx = len(rows) - 1
    if concurso is not None:
        achou = None
        for i, s in enumerate(rows):
            if int(s["concurso"]) == int(concurso):
                achou = i
                break
        if achou is None:
            return {"sucesso": False, "erro": f"Concurso {concurso} não encontrado."}
        idx = achou

    alvo = rows[idx]
    anterior = rows[idx - 1]["numeros"] if idx else []
    numeros = [int(x) for x in (alvo.get("numeros") or [])]
    crescente = [int(x) for x in (alvo.get("numeros_ordenados") or sorted(numeros))]

    from analise_escolha_visual.enriquecimento.motor import conjuntos_concurso
    from analise_escolha_visual.enriquecimento.regras_2a1 import montar_linha_2a1
    from analise_estudos.specs import get_estudos_config
    from analise_gaps_ciclo.core import (
        analisar_regua_combinacoes,
        gaps_de,
        gaps_sequencia,
        padrao_gaps,
    )
    from analise_gaps_ciclo.geometria import indicadores_de, layout_de

    from diadesorte.meses_cores import cor_do_mes

    cfg = get_estudos_config(modality_key)
    dmin = int(cfg["dezena_min"])
    dmax = int(cfg["dezena_max"])
    cols = int(cfg.get("volante_cols") or 10)
    det = conjuntos_concurso(
        numeros,
        anterior,
        com_cruzamentos=False,
        com_diagonais=True,
        dmin=dmin,
        dmax=dmax,
        cols=cols,
    )
    fora = montar_linha_2a1(numeros, anterior, dmin=dmin, dmax=dmax, cols=cols)
    basicos = det.get("basicos") or {}

    classificado = padrao_gaps(gaps_de(numeros)) or "—"
    ordem_gaps = padrao_gaps(gaps_sequencia(numeros)) or "—"

    ordenados = [list(s.get("numeros_ordenados") or []) for s in rows]
    combos = [crescente] + ordenados[:idx] + ordenados[idx + 1:]
    regua = analisar_regua_combinacoes(combos, limite_linhas=1)
    reg_txt = _texto_regua(((regua.get("ultimo") or {}).get("posicoes") or []))

    pares = (basicos.get("pares") or {}).get("dezenas") or []
    impares = (basicos.get("impares") or {}).get("dezenas") or []
    digitos = det.get("digitos_unicos") or []
    padrao = "-".join(str(int(n) // 10) for n in crescente) or "—"
    geo = _texto_geometria(indicadores_de(crescente, layout_de(modality_key)))

    nome_mes = (alvo.get("mes_nome") or "").strip()
    return {
        "sucesso": True,
        "concurso": int(alvo["concurso"]),
        "concursos": [int(s["concurso"]) for s in rows],
        "resultado_ordem": _juntar(numeros),
        "resultado_crescente": _juntar(crescente),
        "mes": _mes_curto(nome_mes),
        "mes_cor": cor_do_mes(mes_nome=nome_mes) if nome_mes else "",
        "nao_sairam": [
            _qtd_linha(len(fora.get("pares") or []), fora.get("pares") or []),
            _qtd_linha(len(fora.get("impares") or []), fora.get("impares") or []),
        ],
        "pares": _qtd_linha(len(pares), pares),
        "impares": _qtd_linha(len(impares), impares),
        "repetido": _juntar(fora.get("repetidos") or []) or "—",
        "sequencia": _texto_sequencias(fora.get("sequencias") or []),
        "finais": _texto_finais(fora.get("finais") or []),
        "diagonais": _texto_diagonais(fora.get("diagonais") or []),
        "gaps_classificado": classificado.split() if classificado and classificado != "—" else [],
        "gaps_ordem": ordem_gaps.split() if ordem_gaps and ordem_gaps != "—" else [],
        "soma": str(det.get("soma") if det.get("soma") is not None else "—"),
        "padrao": padrao,
        "digitos": " ".join(str(d) for d in digitos) or "—",
        "geometria": geo,
        "regua": reg_txt,
        "posicoes": _posicoes_amostra(rows, idx),
    }
