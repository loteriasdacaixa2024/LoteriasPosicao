# -*- coding: utf-8 -*-
from __future__ import annotations

from itertools import combinations
from typing import Any, Dict, List, Optional, Set, Tuple

from _shared.desdobramento_especial.configs import ModalidadeConfig, get_config


def dezenas_coluna(cfg: ModalidadeConfig, coluna: int) -> List[int]:
    if coluna < 1 or coluna > cfg.colunas_header:
        raise ValueError(f"Coluna inválida: {coluna}")
    if cfg.layout == "bloco5":
        start = (coluna - 1) * 5 + 1
        return list(range(start, min(start + 5, cfg.max_dezena + 1)))
    return sorted(
        coluna + 10 * i
        for i in range(cfg.volante_linhas)
        if coluna + 10 * i <= cfg.max_dezena
    )


def pares_coluna(cfg: ModalidadeConfig, coluna: int) -> List[Tuple[int, int]]:
    dezs = dezenas_coluna(cfg, coluna)
    return [tuple(p) for p in combinations(dezs, 2)]


def jogos_alinhados_max(cfg: ModalidadeConfig, colunas: List[int]) -> int:
    if not colunas:
        return cfg.garantias["diamante"]["jogos"]
    return min(len(pares_coluna(cfg, c)) for c in colunas)


def total_montagem(n_colunas: int, modo: str) -> int:
    modo = (modo or "par").lower()
    if modo == "par":
        return n_colunas * 2
    return 1 + (n_colunas - 1) * 2


def montagem_valida(cfg: ModalidadeConfig, total: int) -> bool:
    return cfg.min_dezenas <= total <= cfg.max_dezenas


def validar_selecao(
    cfg: ModalidadeConfig,
    colunas: List[int],
    modo: str,
    coluna_simples: Optional[int] = None,
) -> Optional[str]:
    modo = (modo or "par").lower()
    if modo not in ("par", "impar"):
        return "Modo inválido. Use PAR ou ÍMPAR."
    if not colunas:
        return f"Selecione no mínimo {cfg.min_colunas} colunas."
    vistos: Set[int] = set()
    for c in colunas:
        if not isinstance(c, int) or c < 1 or c > cfg.colunas_header:
            return f"Colunas devem ser de 1 a {cfg.colunas_header}."
        if c in vistos:
            return f"Coluna {c} duplicada."
        vistos.add(c)
    n = len(colunas)
    if n < cfg.min_colunas:
        return f"Selecione no mínimo {cfg.min_colunas} colunas (marcou {n})."
    total = total_montagem(n, modo)
    if not montagem_valida(cfg, total):
        validas = sorted(
            cfg.colunas_validas_par if modo == "par" else cfg.colunas_validas_impar
        )
        return (
            f"Com {n} coluna(s) no modo {modo.upper()}, a aposta teria {total} dezenas — "
            f"fora da faixa deste especial ({cfg.min_dezenas} a {cfg.max_dezenas}). "
            f"Colunas válidas: {', '.join(str(x) for x in validas)}."
        )
    if modo == "impar":
        if coluna_simples is None:
            return "No modo ÍMPAR, marque a coluna simples (2º clique no cabeçalho)."
        if coluna_simples not in vistos:
            return "A coluna simples deve estar entre as colunas marcadas."
    return None


def colunas_para_dezenas(cfg: ModalidadeConfig, qtd_dezenas: int, modo: str) -> Optional[int]:
    modo_l = (modo or "par").lower()
    if not montagem_valida(cfg, qtd_dezenas):
        return None
    if modo_l == "par":
        if qtd_dezenas % 2 != 0:
            return None
        n = qtd_dezenas // 2
        return n if n >= cfg.min_colunas else None
    if (qtd_dezenas - 1) % 2 != 0:
        return None
    n = 1 + (qtd_dezenas - 1) // 2
    return n if n >= cfg.min_colunas else None


def tabela_colunas_dezenas(cfg: ModalidadeConfig, modo: str) -> List[Dict[str, Any]]:
    modo_l = (modo or "par").lower()
    validas = sorted(
        cfg.colunas_validas_par if modo_l == "par" else cfg.colunas_validas_impar
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
            "valor_aposta": cfg.tabela_precos.get(dez, 0.0),
            "pares_por_coluna": jogos_alinhados_max(cfg, list(range(1, n + 1))),
        })
    return linhas


def orientacao_selecao(
    slug: str,
    modo: str,
    meta_dezenas: Optional[int] = None,
    colunas_selecionadas: Optional[List[int]] = None,
) -> Dict[str, Any]:
    cfg = get_config(slug)
    modo_l = (modo or "par").lower()
    tabela = tabela_colunas_dezenas(cfg, modo_l)
    cols = sorted({int(c) for c in (colunas_selecionadas or []) if 1 <= int(c) <= cfg.colunas_header})
    n_sel = len(cols)
    dez_atual = total_montagem(n_sel, modo_l) if n_sel else 0
    jmax = jogos_alinhados_max(cfg, cols) if cols else cfg.garantias["diamante"]["jogos"]

    out: Dict[str, Any] = {
        "modo": modo_l,
        "tabela": tabela,
        "min_dezenas": cfg.min_dezenas,
        "max_dezenas": cfg.max_dezenas,
        "jogos_por_coluna_pares": jmax,
        "colunas_selecionadas": cols,
        "colunas_marcadas": n_sel,
        "dezenas_atual": dez_atual if n_sel else 0,
        "montagem_valida": bool(n_sel) and montagem_valida(cfg, dez_atual),
        "nota_aposta": cfg.nota_aposta,
    }

    if meta_dezenas is not None:
        meta = int(meta_dezenas)
        need = colunas_para_dezenas(cfg, meta, modo_l)
        out["meta_dezenas"] = meta
        out["colunas_necessarias"] = need
        out["meta_atingivel"] = need is not None
        if need is not None:
            out["instrucao"] = (
                f"Para {meta} dezenas ({modo_l.upper()}), marque exatamente {need} coluna(s) no volante."
            )
            out["meta_ok"] = n_sel == need and montagem_valida(cfg, meta)
        else:
            out["instrucao"] = (
                f"{meta} dezenas não cabe no modo {modo_l.upper()} "
                f"(faixa {cfg.min_dezenas}–{cfg.max_dezenas} neste especial)."
            )
            out["meta_ok"] = False
    elif n_sel == 0:
        out["instrucao"] = (
            f"Marque colunas no volante (cabeçalhos). Mínimo {cfg.min_colunas} colunas; "
            f"resultado entre {cfg.min_dezenas} e {cfg.max_dezenas} dezenas na aposta."
        )
    elif n_sel == 1:
        out["instrucao"] = "1 coluna = 2 dezenas — marque mais colunas (veja a tabela)."
    elif not montagem_valida(cfg, dez_atual):
        out["instrucao"] = (
            f"{n_sel} coluna(s) = {dez_atual} dezenas — fora da faixa {cfg.min_dezenas}–{cfg.max_dezenas}."
        )
    else:
        out["instrucao"] = (
            f"{n_sel} coluna(s) = {dez_atual} dezenas. Até {jmax} jogos alinhados (2 em 2 por coluna)."
        )
    return out


def escolher_dezena_simples(
    cfg: ModalidadeConfig,
    coluna: int,
    faltantes_ciclo: Optional[Set[int]] = None,
    preferida: Optional[int] = None,
) -> int:
    dezs = dezenas_coluna(cfg, coluna)
    if preferida is not None and preferida in dezs:
        return preferida
    if faltantes_ciclo:
        prefs = [d for d in dezs if d in faltantes_ciclo]
        if prefs:
            return min(prefs)
    return dezs[0]


def desdobramento_coluna(cfg: ModalidadeConfig, coluna: int) -> Dict[str, Any]:
    dezenas = dezenas_coluna(cfg, coluna)
    pares = pares_coluna(cfg, coluna)
    return {
        "coluna": coluna,
        "label": cfg.label_coluna(coluna),
        "dezenas": dezenas,
        "dezenas_fmt": [f"{d:02d}" for d in dezenas],
        "total_pares": len(pares),
        "pares": [
            {"indice": i + 1, "par": list(p), "fmt": f"{p[0]:02d}-{p[1]:02d}"}
            for i, p in enumerate(pares)
        ],
    }


def preview_montagem(
    slug: str,
    colunas: List[int],
    modo: str,
    coluna_simples: Optional[int] = None,
) -> Dict[str, Any]:
    cfg = get_config(slug)
    colunas_ord = sorted({int(c) for c in colunas})
    modo_l = (modo or "par").lower()
    total = total_montagem(len(colunas_ord), modo_l)
    erro = validar_selecao(cfg, colunas_ord, modo_l, coluna_simples)
    jmax = jogos_alinhados_max(cfg, colunas_ord) if colunas_ord else 0
    if modo_l == "par":
        formula = f"{len(colunas_ord)} colunas × 2 = {total} dezenas"
    elif coluna_simples:
        outras = len(colunas_ord) - 1
        formula = f"1 (col. {coluna_simples}) + {outras} × 2 = {total} dezenas"
    else:
        formula = f"1 + (colunas − 1) × 2 = {total} dezenas"
    return {
        "colunas": colunas_ord,
        "modo": modo_l,
        "coluna_simples": coluna_simples,
        "total_dezenas_aposta": total,
        "montagem_valida": montagem_valida(cfg, total) and erro is None,
        "erro": erro,
        "formula": formula,
        "total_jogos_estruturais": jmax,
        "pares_por_coluna": jmax,
    }


def aplicar_garantia(cfg: ModalidadeConfig, resultado: Dict[str, Any], garantia: str) -> Dict[str, Any]:
    gcfg = cfg.garantias.get((garantia or "diamante").lower()) or cfg.garantias["diamante"]
    n = min(int(gcfg["jogos"]), len(resultado.get("jogos", [])))
    out = dict(resultado)
    out["garantia"] = garantia.lower() if garantia else "diamante"
    out["garantia_label"] = gcfg["titulo"]
    out["jogos"] = resultado["jogos"][:n]
    out["jogos_detalhe"] = resultado["jogos_detalhe"][:n]
    out["total_jogos"] = n
    out["valor_total"] = round(out["valor_aposta"] * n, 2)
    return out


def gerar_jogos_estruturais(
    slug: str,
    colunas: List[int],
    modo: str,
    coluna_simples: Optional[int] = None,
    dezena_simples: Optional[int] = None,
    faltantes_ciclo: Optional[Set[int]] = None,
    garantia: str = "diamante",
) -> Dict[str, Any]:
    cfg = get_config(slug)
    modo_l = (modo or "par").lower()
    colunas_ord = sorted({int(c) for c in colunas})
    erro = validar_selecao(cfg, colunas_ord, modo_l, coluna_simples)
    if erro:
        raise ValueError(erro)

    qtd_dezenas = total_montagem(len(colunas_ord), modo_l)
    pares_map = {c: pares_coluna(cfg, c) for c in colunas_ord}
    n_jogos = jogos_alinhados_max(cfg, colunas_ord)

    dezena_s: Optional[int] = None
    if modo_l == "impar":
        dezena_s = escolher_dezena_simples(
            cfg, int(coluna_simples), faltantes_ciclo, dezena_simples
        )

    jogos: List[List[int]] = []
    jogos_detalhe: List[Dict[str, Any]] = []

    for idx in range(n_jogos):
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

    valor_unit = cfg.tabela_precos.get(qtd_dezenas, 0.0)
    base = {
        "modo": modo_l,
        "colunas": colunas_ord,
        "colunas_label": [cfg.label_coluna(c) for c in colunas_ord],
        "coluna_simples": coluna_simples if modo_l == "impar" else None,
        "dezena_simples": dezena_s,
        "qtd_dezenas": qtd_dezenas,
        "total_jogos": n_jogos,
        "total_jogos_max": n_jogos,
        "pares_por_coluna": n_jogos,
        "jogos": jogos,
        "jogos_detalhe": jogos_detalhe,
        "valor_aposta": valor_unit,
        "valor_total": round(valor_unit * n_jogos, 2),
        "desdobramento_colunas": [desdobramento_coluna(cfg, c) for c in colunas_ord],
        "resumo": (
            f"{len(colunas_ord)} coluna(s) = {qtd_dezenas} dezenas · {n_jogos} jogos alinhados"
        ),
    }
    return aplicar_garantia(cfg, base, garantia)


def formatar_export_txt(resultado: Dict[str, Any], nome: str, titulo: str) -> str:
    linhas = [
        f"=== {nome} — {titulo} ({resultado.get('modo', '').upper()}) ===",
        f"Dezenas por aposta: {resultado['qtd_dezenas']}",
        f"Colunas: {', '.join(str(c) for c in resultado['colunas'])}",
        f"Total de jogos: {resultado['total_jogos']}",
        f"Valor unitário: R$ {resultado['valor_aposta']:.2f}",
        f"Valor total: R$ {resultado['valor_total']:.2f}",
        "",
    ]
    for j in resultado.get("jogos_detalhe", []):
        linhas.append(
            f"Jogo {j['numero']:02d}: {j['formula']} → {' '.join(j['dezenas_fmt_sequencia'])}"
        )
    return "\n".join(linhas)
