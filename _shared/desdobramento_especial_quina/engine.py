# -*- coding: utf-8 -*-
"""
Desdobramento estrutural especial da Quina (sorteios especiais).
PAR: cada coluna selecionada contribui com 1 par (2 dezenas) — total = colunas × 2.
ÍMPAR: uma coluna “simples” (1 dezena) + demais em pares — total = 1 + (colunas − 1) × 2.
Geração alinhada por índice de par (até C(8,2) = 28 jogos), como Des2.
"""
from __future__ import annotations

from itertools import combinations
from typing import Any, Dict, List, Optional, Set, Tuple

from _shared.desdobramento_especial_quina.constants import (
    COLUNAS_LABEL,
    COLUNAS_VALIDAS_IMPAR,
    COLUNAS_VALIDAS_PAR,
    DEZENAS_POR_COLUNA,
    GARANTIAS_ESPECIAL,
    JOGOS_POR_COLUNA,
    MAX_DEZENAS_APOSTA,
    MIN_COLUNAS,
    MIN_DEZENAS_APOSTA,
    TABELA_PRECOS,
)


def dezenas_coluna(coluna: int) -> List[int]:
    if coluna < 1 or coluna > 10:
        raise ValueError(f"Coluna inválida: {coluna}")
    return sorted(coluna + 10 * i for i in range(DEZENAS_POR_COLUNA) if coluna + 10 * i <= 80)


def pares_coluna(coluna: int) -> List[Tuple[int, int]]:
    return [tuple(p) for p in combinations(dezenas_coluna(coluna), 2)]


def total_montagem(n_colunas: int, modo: str) -> int:
    modo = (modo or "par").lower()
    if modo == "par":
        return n_colunas * 2
    return 1 + (n_colunas - 1) * 2


def montagem_valida(total: int) -> bool:
    return MIN_DEZENAS_APOSTA <= total <= MAX_DEZENAS_APOSTA


def colunas_para_dezenas(qtd_dezenas: int, modo: str) -> Optional[int]:
    """Quantas colunas marcar para fechar exatamente `qtd_dezenas` na aposta."""
    modo_l = (modo or "par").lower()
    if not montagem_valida(qtd_dezenas):
        return None
    if modo_l == "par":
        if qtd_dezenas % 2 != 0:
            return None
        n = qtd_dezenas // 2
        return n if n >= MIN_COLUNAS else None
    if (qtd_dezenas - 1) % 2 != 0:
        return None
    n = 1 + (qtd_dezenas - 1) // 2
    return n if n >= MIN_COLUNAS else None


def tabela_colunas_dezenas(modo: str) -> List[Dict[str, Any]]:
    """Todas as combinações válidas colunas → dezenas para o modo."""
    modo_l = (modo or "par").lower()
    validas = sorted(
        COLUNAS_VALIDAS_PAR if modo_l == "par" else COLUNAS_VALIDAS_IMPAR
    )
    linhas = []
    for n in validas:
        dez = total_montagem(n, modo_l)
        if modo_l == "par":
            formula = f"{n} colunas × 2 = {dez} dezenas"
        else:
            formula = f"1 simples + {n - 1} colunas em par = {dez} dezenas"
        linhas.append({
            "colunas": n,
            "dezenas": dez,
            "formula": formula,
            "valor_aposta": TABELA_PRECOS.get(dez, 0.0),
            "jogos_estruturais_max": JOGOS_POR_COLUNA,
        })
    return linhas


def orientacao_selecao(
    modo: str,
    meta_dezenas: Optional[int] = None,
    colunas_selecionadas: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """Guia: quantas colunas marcar para 5–15 dezenas; valida seleção atual."""
    modo_l = (modo or "par").lower()
    tabela = tabela_colunas_dezenas(modo_l)
    cols = sorted({int(c) for c in (colunas_selecionadas or []) if 1 <= int(c) <= 10})
    n_sel = len(cols)
    dez_atual = total_montagem(n_sel, modo_l) if n_sel else 0

    out: Dict[str, Any] = {
        "modo": modo_l,
        "tabela": tabela,
        "min_dezenas": MIN_DEZENAS_APOSTA,
        "max_dezenas": MAX_DEZENAS_APOSTA,
        "jogos_por_coluna_pares": JOGOS_POR_COLUNA,
        "colunas_selecionadas": cols,
        "colunas_marcadas": n_sel,
        "dezenas_atual": dez_atual if n_sel else 0,
        "montagem_valida": bool(n_sel) and montagem_valida(dez_atual),
    }

    if meta_dezenas is not None:
        meta = int(meta_dezenas)
        need = colunas_para_dezenas(meta, modo_l)
        out["meta_dezenas"] = meta
        out["colunas_necessarias"] = need
        out["meta_atingivel"] = need is not None
        if need is not None:
            if modo_l == "par":
                out["instrucao"] = (
                    f"Para apostar com {meta} dezenas (PAR), marque exatamente "
                    f"{need} coluna(s) no volante. Cada coluna entra com 1 par (2 em 2 automático)."
                )
            else:
                out["instrucao"] = (
                    f"Para apostar com {meta} dezenas (ÍMPAR), marque {need} coluna(s): "
                    f"1 fica simples (sem par) e as outras {need - 1} desdobram 2 em 2."
                )
            out["faltam_colunas"] = max(0, need - n_sel)
            out["excesso_colunas"] = max(0, n_sel - need)
            out["meta_ok"] = n_sel == need and montagem_valida(meta)
        else:
            out["instrucao"] = (
                f"{meta} dezenas não é possível no modo {modo_l.upper()} "
                f"(use entre {MIN_DEZENAS_APOSTA} e {MAX_DEZENAS_APOSTA})."
            )
            out["meta_ok"] = False
    elif n_sel == 0:
        out["instrucao"] = (
            f"Escolha quantas dezenas quer na aposta (5 a 15) ou marque colunas no volante. "
            f"1 coluna sozinha não serve (só 2 dezenas)."
        )
    elif n_sel == 1:
        out["instrucao"] = (
            "1 coluna = 2 dezenas apenas — abaixo do mínimo Caixa (5). "
            f"No {modo_l.upper()}, marque mais colunas (veja a tabela abaixo)."
        )
    elif not montagem_valida(dez_atual):
        out["instrucao"] = (
            f"Você marcou {n_sel} coluna(s) = {dez_atual} dezenas — fora da faixa 5 a 15. "
            "Ajuste a quantidade de colunas."
        )
    else:
        out["instrucao"] = (
            f"{n_sel} coluna(s) = {dez_atual} dezenas na aposta. "
            f"Cada coluna gera até {JOGOS_POR_COLUNA} pares (2 em 2); "
            "a garantia abaixo escolhe quantos jogos alinhados usar (7 a 28)."
        )

    return out


def validar_selecao(
    colunas: List[int],
    modo: str,
    coluna_simples: Optional[int] = None,
) -> Optional[str]:
    modo = (modo or "par").lower()
    if modo not in ("par", "impar"):
        return "Modo inválido. Use PAR ou ÍMPAR."

    if not colunas:
        return f"Selecione no mínimo {MIN_COLUNAS} colunas."

    vistos: Set[int] = set()
    for c in colunas:
        if not isinstance(c, int) or c < 1 or c > 10:
            return "Colunas devem ser números de 1 a 10."
        if c in vistos:
            return f"Coluna {c} duplicada."
        vistos.add(c)

    n = len(colunas)
    if n < MIN_COLUNAS:
        return f"Selecione no mínimo {MIN_COLUNAS} colunas (você marcou {n})."

    total = total_montagem(n, modo)
    if not montagem_valida(total):
        validas = sorted(COLUNAS_VALIDAS_PAR if modo == "par" else COLUNAS_VALIDAS_IMPAR)
        return (
            f"Com {n} coluna(s) no modo {modo.upper()}, a aposta teria {total} dezenas — "
            f"fora da faixa oficial da Caixa ({MIN_DEZENAS_APOSTA} a {MAX_DEZENAS_APOSTA}). "
            f"Quantidades de colunas válidas neste modo: {', '.join(str(x) for x in validas)}."
        )

    if modo == "impar":
        if coluna_simples is None:
            return (
                "No modo ÍMPAR, indique qual coluna ficará sem desdobramento "
                "(1 dezena por aposta)."
            )
        if coluna_simples not in vistos:
            return "A coluna simples deve estar entre as colunas selecionadas."

    return None


def escolher_dezena_simples(
    coluna: int,
    faltantes_ciclo: Optional[Set[int]] = None,
    preferida: Optional[int] = None,
) -> int:
    dezs = dezenas_coluna(coluna)
    if preferida is not None and preferida in dezs:
        return preferida
    if faltantes_ciclo:
        prefs = [d for d in dezs if d in faltantes_ciclo]
        if prefs:
            return min(prefs)
    return dezs[0]


def desdobramento_coluna(coluna: int) -> Dict[str, Any]:
    dezenas = dezenas_coluna(coluna)
    pares = pares_coluna(coluna)
    return {
        "coluna": coluna,
        "label": COLUNAS_LABEL.get(coluna, f"Coluna {coluna}"),
        "dezenas": dezenas,
        "dezenas_fmt": [f"{d:02d}" for d in dezenas],
        "total_pares": len(pares),
        "pares": [
            {
                "indice": i + 1,
                "par": list(p),
                "fmt": f"{p[0]:02d}-{p[1]:02d}",
            }
            for i, p in enumerate(pares)
        ],
    }


def preview_montagem(
    colunas: List[int],
    modo: str,
    coluna_simples: Optional[int] = None,
) -> Dict[str, Any]:
    colunas_ord = sorted({int(c) for c in colunas})
    modo_l = (modo or "par").lower()
    total = total_montagem(len(colunas_ord), modo_l)
    erro = validar_selecao(colunas_ord, modo_l, coluna_simples)
    if modo_l == "par":
        formula = f"{len(colunas_ord)} colunas × 2 = {total} dezenas por aposta"
    elif coluna_simples:
        outras = len(colunas_ord) - 1
        formula = f"1 (col. {coluna_simples}) + {outras} × 2 = {total} dezenas por aposta"
    else:
        formula = f"1 + (colunas − 1) × 2 = {total} dezenas por aposta"
    return {
        "colunas": colunas_ord,
        "modo": modo_l,
        "coluna_simples": coluna_simples,
        "total_dezenas_aposta": total,
        "montagem_valida": montagem_valida(total) and erro is None,
        "erro": erro,
        "formula": formula,
        "total_jogos_estruturais": JOGOS_POR_COLUNA,
        "pares_por_coluna": JOGOS_POR_COLUNA,
    }


def aplicar_garantia(resultado: Dict[str, Any], garantia: str) -> Dict[str, Any]:
    """Recorta jogos conforme pacote bronze/prata/ouro/diamante."""
    cfg = GARANTIAS_ESPECIAL.get((garantia or "diamante").lower())
    if not cfg:
        cfg = GARANTIAS_ESPECIAL["diamante"]
    n = min(int(cfg["jogos"]), len(resultado.get("jogos", [])))
    out = dict(resultado)
    out["garantia"] = garantia.lower() if garantia else "diamante"
    out["garantia_label"] = cfg["titulo"]
    out["jogos"] = resultado["jogos"][:n]
    out["jogos_detalhe"] = resultado["jogos_detalhe"][:n]
    out["total_jogos"] = n
    out["valor_total"] = round(out["valor_aposta"] * n, 2)
    return out


def gerar_jogos_estruturais(
    colunas: List[int],
    modo: str,
    coluna_simples: Optional[int] = None,
    dezena_simples: Optional[int] = None,
    faltantes_ciclo: Optional[Set[int]] = None,
    garantia: str = "diamante",
) -> Dict[str, Any]:
    modo_l = (modo or "par").lower()
    colunas_ord = sorted({int(c) for c in colunas})
    erro = validar_selecao(colunas_ord, modo_l, coluna_simples)
    if erro:
        raise ValueError(erro)

    qtd_dezenas = total_montagem(len(colunas_ord), modo_l)
    pares_map = {c: pares_coluna(c) for c in colunas_ord}
    desdobramento_colunas = [desdobramento_coluna(c) for c in colunas_ord]

    dezena_s: Optional[int] = None
    if modo_l == "impar":
        dezena_s = escolher_dezena_simples(
            int(coluna_simples),
            faltantes_ciclo,
            dezena_simples,
        )

    jogos: List[List[int]] = []
    jogos_detalhe: List[Dict[str, Any]] = []

    for idx in range(JOGOS_POR_COLUNA):
        partes_jogo: List[Dict[str, Any]] = []
        dezenas_sequencia: List[int] = []
        for col in colunas_ord:
            if modo_l == "impar" and col == coluna_simples:
                partes_jogo.append({
                    "coluna": col,
                    "tipo": "simples",
                    "dezena": dezena_s,
                    "fmt": f"{dezena_s:02d}",
                    "indice_par": None,
                })
                dezenas_sequencia.append(dezena_s)
            else:
                par = pares_map[col][idx]
                partes_jogo.append({
                    "coluna": col,
                    "tipo": "par",
                    "par": list(par),
                    "fmt": f"{par[0]:02d}-{par[1]:02d}",
                    "indice_par": idx + 1,
                })
                dezenas_sequencia.extend(par)

        dezenas_ordenadas = sorted(dezenas_sequencia)
        jogos.append(dezenas_ordenadas)
        jogos_detalhe.append({
            "numero": idx + 1,
            "indice_par": idx + 1,
            "dezenas": dezenas_ordenadas,
            "dezenas_fmt": [f"{d:02d}" for d in dezenas_ordenadas],
            "dezenas_sequencia": dezenas_sequencia,
            "dezenas_fmt_sequencia": [f"{d:02d}" for d in dezenas_sequencia],
            "partes": partes_jogo,
            "formula": " + ".join(p["fmt"] for p in partes_jogo),
        })

    valor_unit = TABELA_PRECOS.get(qtd_dezenas, 0.0)
    valor_total = round(valor_unit * JOGOS_POR_COLUNA, 2)

    if modo_l == "par":
        resumo = (
            f"{len(colunas_ord)} coluna(s) × 2 dezenas (1 par cada) = "
            f"{qtd_dezenas} dezenas por aposta · {JOGOS_POR_COLUNA} combinações alinhadas"
        )
    else:
        resumo = (
            f"Coluna {coluna_simples} simples (1 dezena) + "
            f"{len(colunas_ord) - 1} coluna(s) em par = {qtd_dezenas} dezenas · "
            f"{JOGOS_POR_COLUNA} combinações"
        )

    base = {
        "modo": modo_l,
        "colunas": colunas_ord,
        "colunas_label": [COLUNAS_LABEL.get(c, str(c)) for c in colunas_ord],
        "coluna_simples": coluna_simples if modo_l == "impar" else None,
        "dezena_simples": dezena_s,
        "qtd_dezenas": qtd_dezenas,
        "total_jogos": JOGOS_POR_COLUNA,
        "total_jogos_max": JOGOS_POR_COLUNA,
        "pares_por_coluna": JOGOS_POR_COLUNA,
        "jogos": jogos,
        "jogos_detalhe": jogos_detalhe,
        "valor_aposta": valor_unit,
        "valor_total": valor_total,
        "desdobramento_colunas": desdobramento_colunas,
        "resumo": resumo,
    }
    return aplicar_garantia(base, garantia)


def formatar_export_txt(resultado: Dict[str, Any], nome: str = "Quina Especial") -> str:
    linhas = [
        f"=== {nome} — Desdobramento Especial Quina ({resultado.get('modo', '').upper()}) ===",
        f"Dezenas por aposta: {resultado['qtd_dezenas']}",
        f"Colunas: {', '.join(str(c) for c in resultado['colunas'])}",
    ]
    if resultado.get("coluna_simples"):
        linhas.append(f"Coluna simples (ímpar): {resultado['coluna_simples']}")
        if resultado.get("dezena_simples"):
            linhas.append(f"Dezena simples fixa: {resultado['dezena_simples']:02d}")
    linhas.extend([
        f"Total de jogos: {resultado['total_jogos']}",
        f"Valor unitário: R$ {resultado['valor_aposta']:.2f}",
        f"Valor total: R$ {resultado['valor_total']:.2f}",
        "",
        f"--- DESDOBRAMENTO POR COLUNA (C(8,2) = {JOGOS_POR_COLUNA} pares) ---",
    ])
    for col in resultado.get("desdobramento_colunas", []):
        linhas.append(f"\n{col['label']} — dezenas: {' '.join(col['dezenas_fmt'])}")
        for p in col["pares"]:
            linhas.append(f"  Par {p['indice']:02d}: {p['fmt']}")
    linhas.append("\n--- JOGOS (alinhamento por índice de par) ---")
    for j in resultado["jogos_detalhe"]:
        linhas.append(
            f"Jogo {j['numero']:02d} (par #{j['indice_par']}): {j['formula']} "
            f"→ {' '.join(j['dezenas_fmt_sequencia'])}"
        )
    return "\n".join(linhas)
