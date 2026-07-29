"""Fechamento 16 dezenas → apostas de N números (padrão Mega-Sena)."""
from itertools import combinations
from typing import List, Dict, Any


def final_coluna(numero: int) -> int:
    return 10 if numero % 10 == 0 else numero % 10


def organizar_por_coluna(numeros: List[int]) -> List[int]:
    colunas = {}
    for n in numeros:
        col = final_coluna(n)
        colunas.setdefault(col, []).append(n)
    for col in colunas:
        colunas[col].sort()
    numeros_ordenados = []
    for col in sorted(colunas.keys()):
        numeros_ordenados.extend(colunas[col])
    return numeros_ordenados


def gerar_fechamento(
    numeros: List[int],
    modo: str = "bronze",
    tamanho_aposta: int = 6,
) -> Dict[str, Any]:
    if len(numeros) != 16:
        raise ValueError("O desdobramento precisa de exatamente 16 números.")
    if tamanho_aposta != 6:
        raise ValueError("Fechamento padrão suporta apostas de 6 dezenas.")

    numeros_organizados = organizar_por_coluna(numeros)
    grupos = [
        numeros_organizados[0:4],
        numeros_organizados[4:8],
        numeros_organizados[8:12],
        numeros_organizados[12:16],
    ]
    pares_por_grupo = [list(combinations(gp, 2)) for gp in grupos]

    def gerar_apostas_para_parceria(l1: int, l2: int, r1: int, r2: int) -> List[List[int]]:
        apostas = []
        for i in range(6):
            par1 = pares_por_grupo[l1][i]
            par2 = pares_por_grupo[l2][i]
            par3 = pares_por_grupo[r1][i]
            par4 = pares_por_grupo[r2][i]
            combinacoes = [
                [par1[0], par1[1], par2[0], par3[0], par3[1], par4[0]],
                [par1[1], par2[0], par2[1], par3[1], par4[0], par4[1]],
                [par2[0], par2[1], par1[0], par4[0], par4[1], par3[0]],
                [par2[1], par1[0], par1[1], par4[1], par3[0], par3[1]],
            ]
            for ap in combinacoes:
                if len(set(ap)) == 6:
                    apostas.append(sorted(ap))
        return apostas

    def gerar_apostas_cartesianas_para_parceria(l1: int, l2: int, r1: int, r2: int) -> List[List[int]]:
        apostas = []
        for i in range(6):
            par1 = pares_por_grupo[l1][i]
            par2 = pares_por_grupo[l2][i]
            par3 = pares_por_grupo[r1][i]
            par4 = pares_por_grupo[r2][i]
            trios_esq = [
                [par1[0], par1[1], par2[0]],
                [par1[1], par2[0], par2[1]],
                [par2[0], par2[1], par1[0]],
                [par2[1], par1[0], par1[1]],
            ]
            trios_dir = [
                [par3[0], par3[1], par4[0]],
                [par3[1], par4[0], par4[1]],
                [par4[0], par4[1], par3[0]],
                [par4[1], par3[0], par3[1]],
            ]
            for te in trios_esq:
                for td in trios_dir:
                    ap = te + td
                    if len(set(ap)) == 6:
                        apostas.append(sorted(ap))
        return apostas

    modo = (modo or "bronze").lower()
    if modo == "bronze":
        apostas = gerar_apostas_para_parceria(0, 1, 2, 3)
    elif modo == "prata":
        apostas = (
            gerar_apostas_para_parceria(0, 1, 2, 3)
            + gerar_apostas_para_parceria(0, 2, 1, 3)
            + gerar_apostas_para_parceria(0, 3, 1, 2)
        )
    elif modo == "ouro":
        apostas = gerar_apostas_cartesianas_para_parceria(0, 1, 2, 3)
    elif modo == "diamante":
        apostas = (
            gerar_apostas_cartesianas_para_parceria(0, 1, 2, 3)
            + gerar_apostas_cartesianas_para_parceria(0, 2, 1, 3)
            + gerar_apostas_cartesianas_para_parceria(0, 3, 1, 2)
        )
    else:
        modo = "bronze"
        apostas = gerar_apostas_para_parceria(0, 1, 2, 3)

    return {
        "numeros": numeros_organizados,
        "grupos": grupos,
        "pares": [[list(p) for p in gp] for gp in pares_por_grupo],
        "apostas": apostas,
        "total_apostas": len(apostas),
        "modo": modo,
    }


def gerar_fechamento_trevos(trevos: List[int]) -> Dict[str, Any]:
    """4 trevos (1-6) → 6 apostas de 2 trevos (fechamento da +Milionária)."""
    if len(trevos) != 4:
        raise ValueError("Selecione exatamente 4 trevos (de 1 a 6).")
    for t in trevos:
        if t < 1 or t > 6:
            raise ValueError("Trevos devem estar entre 1 e 6.")
    if len(set(trevos)) != 4:
        raise ValueError("Os 4 trevos devem ser distintos.")
    trevos_ord = sorted(trevos)
    grupos = [trevos_ord[0:2], trevos_ord[2:4]]
    pares = [list(combinations(trevos_ord, 2))]
    apostas = [list(p) for p in combinations(trevos_ord, 2)]
    return {
        "numeros": trevos_ord,
        "grupos": grupos,
        "pares": pares,
        "apostas": apostas,
        "total_apostas": len(apostas),
        "modo": "trevo",
    }
