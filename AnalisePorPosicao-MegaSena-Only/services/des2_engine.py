"""
Engine de geração estrutural Des2.
Cada coluna possui 6 dezenas e C(6,2)=15 pares.
Os jogos alinham horizontalmente o índice do par entre colunas selecionadas.
"""
from itertools import combinations
from typing import List, Dict, Any, Tuple, Optional

from services.des2_constants import (
    DEZENAS_PERMITIDAS,
    JOGOS_POR_COLUNA,
    TABELA_PRECOS,
    COLUNAS_LABEL,
)


def final_dezena(numero: int) -> int:
    """Retorna o final/coluna (1-10) de uma dezena."""
    return 10 if numero % 10 == 0 else numero % 10


def dezenas_da_coluna(coluna: int) -> List[int]:
    """Retorna as 6 dezenas de uma coluna (1-10). Coluna 10 = finais 0."""
    if coluna < 1 or coluna > 10:
        raise ValueError(f"Coluna inválida: {coluna}")
    return sorted(coluna + 10 * i for i in range(6) if coluna + 10 * i <= 60)


def pares_da_coluna(coluna: int) -> List[Tuple[int, int]]:
    """Gera os 15 pares estruturais C(6,2) de uma coluna."""
    dezenas = dezenas_da_coluna(coluna)
    return [tuple(p) for p in combinations(dezenas, 2)]


def desdobramento_coluna(coluna: int) -> Dict[str, Any]:
    """Desdobra uma coluna de 6 dezenas em 15 pares (dois em dois)."""
    dezenas = dezenas_da_coluna(coluna)
    pares = pares_da_coluna(coluna)
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


def desdobramento_colunas_selecionadas(colunas: List[int]) -> List[Dict[str, Any]]:
    """Retorna o desdobramento (15 pares) de cada coluna escolhida."""
    return [desdobramento_coluna(c) for c in sorted(colunas)]


def colunas_necessarias(qtd_dezenas: int) -> int:
    """Quantidade de colunas = metade das dezenas (lógica de pares)."""
    return qtd_dezenas // 2


def validar_entrada(colunas: List[int], qtd_dezenas: int) -> Optional[str]:
    """Retorna mensagem de erro ou None se válido."""
    if qtd_dezenas not in DEZENAS_PERMITIDAS:
        return f"Quantidade de dezenas inválida. Use: {DEZENAS_PERMITIDAS}"

    necessarias = colunas_necessarias(qtd_dezenas)
    if not colunas:
        return f"Selecione {necessarias} coluna(s)."

    if len(colunas) != necessarias:
        return (
            f"Para {qtd_dezenas} dezenas, selecione exatamente {necessarias} coluna(s). "
            f"Você selecionou {len(colunas)}."
        )

    vistos = set()
    for c in colunas:
        if not isinstance(c, int) or c < 1 or c > 10:
            return "Colunas devem ser números de 1 a 10."
        if c in vistos:
            return f"Coluna {c} duplicada. Não é permitida duplicidade."
        vistos.add(c)

    return None


def gerar_jogos_estruturais(
    colunas: List[int],
    qtd_dezenas: int,
) -> Dict[str, Any]:
    """
    Gera 15 jogos com alinhamento horizontal dos pares.
    Cada jogo combina o par de índice i de cada coluna selecionada.
    """
    erro = validar_entrada(colunas, qtd_dezenas)
    if erro:
        raise ValueError(erro)

    colunas_ord = sorted(colunas)
    pares_map = {c: pares_da_coluna(c) for c in colunas_ord}

    jogos = []
    jogos_detalhe = []

    desdobramento_colunas = desdobramento_colunas_selecionadas(colunas_ord)

    for idx in range(JOGOS_POR_COLUNA):
        dezenas_jogo = []
        pares_jogo = []
        for col in colunas_ord:
            par = pares_map[col][idx]
            pares_jogo.append({
                "coluna": col,
                "par": list(par),
                "fmt": f"{par[0]:02d}-{par[1]:02d}",
                "indice_par": idx + 1,
            })
            dezenas_jogo.extend(par)
        dezenas_ordenadas = sorted(dezenas_jogo)
        jogos.append(dezenas_ordenadas)
        jogos_detalhe.append({
            "numero": idx + 1,
            "indice_par": idx + 1,
            "dezenas": dezenas_ordenadas,
            "dezenas_fmt": [f"{d:02d}" for d in dezenas_ordenadas],
            "dezenas_sequencia": dezenas_jogo,
            "dezenas_fmt_sequencia": [f"{d:02d}" for d in dezenas_jogo],
            "pares": pares_jogo,
            "formula": " + ".join(p["fmt"] for p in pares_jogo),
        })

    valor_unit = TABELA_PRECOS.get(qtd_dezenas, 0)
    valor_total = round(valor_unit * JOGOS_POR_COLUNA, 2)

    return {
        "colunas": colunas_ord,
        "colunas_label": [COLUNAS_LABEL.get(c, str(c)) for c in colunas_ord],
        "qtd_dezenas": qtd_dezenas,
        "colunas_necessarias": colunas_necessarias(qtd_dezenas),
        "total_jogos": JOGOS_POR_COLUNA,
        "pares_por_coluna": JOGOS_POR_COLUNA,
        "jogos": jogos,
        "jogos_detalhe": jogos_detalhe,
        "valor_aposta": valor_unit,
        "valor_total": valor_total,
        "pares_colunas": {
            str(c): [list(p) for p in pares_map[c]]
            for c in colunas_ord
        },
        "desdobramento_colunas": desdobramento_colunas,
        "resumo": (
            f"{len(colunas_ord)} coluna(s) × 2 dezenas (1 par cada) = "
            f"{qtd_dezenas} dezenas por jogo · 15 combinações alinhadas"
        ),
    }


def formatar_export_txt(resultado: Dict[str, Any], nome: str = "Des2") -> str:
    """Formata jogos para exportação TXT."""
    linhas = [
        f"=== {nome} — Desdobramento Estrutural Des2 ===",
        f"Dezenas por jogo: {resultado['qtd_dezenas']}",
        f"Colunas: {', '.join(str(c) for c in resultado['colunas'])}",
        f"Total de jogos: {resultado['total_jogos']}",
        f"Valor unitário: R$ {resultado['valor_aposta']:.2f}",
        f"Valor total: R$ {resultado['valor_total']:.2f}",
        "",
    ]
    linhas.append("--- DESDOBRAMENTO DE CADA COLUNA (C(6,2) = 15 pares) ---")
    for col in resultado.get("desdobramento_colunas", []):
        linhas.append(f"\n{col['label']} — dezenas: {' '.join(col['dezenas_fmt'])}")
        for p in col["pares"]:
            linhas.append(f"  Par {p['indice']:02d}: {p['fmt']}")
    linhas.append("\n--- JOGOS (par #{n} de cada coluna alinhado horizontalmente) ---")
    for j in resultado["jogos_detalhe"]:
        linhas.append(
            f"Jogo {j['numero']:02d} (par #{j['indice_par']}): {j['formula']} "
            f"→ {' '.join(j['dezenas_fmt_sequencia'])}"
        )
    return "\n".join(linhas)
