# -*- coding: utf-8 -*-
"""Contagem de cores do Dia de Sorte a partir dos sorteios já gravados.

A cor segue o algarismo final. As 7 dezenas e o mês entram em contas separadas.
O resultado descreve a janela escolhida; não aponta o próximo sorteio.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from simulador_globo.cores import PALETA, cor_da_dezena

MESES = {
    1: ("Janeiro", "Jan"),
    2: ("Fevereiro", "Fev"),
    3: ("Março", "Mar"),
    4: ("Abril", "Abr"),
    5: ("Maio", "Mai"),
    6: ("Junho", "Jun"),
    7: ("Julho", "Jul"),
    8: ("Agosto", "Ago"),
    9: ("Setembro", "Set"),
    10: ("Outubro", "Out"),
    11: ("Novembro", "Nov"),
    12: ("Dezembro", "Dez"),
}

_IDX = {item["id"]: i for i, item in enumerate(PALETA)}
NOTA = (
    "A vermelha tem 4 dezenas (01, 11, 21 e 31). As outras cores têm 3. "
    "Por isso a vermelha aparece mais vezes no histórico. "
    "Esta leitura descreve os concursos já sorteados e não indica o próximo."
)


def bolas_da_cor(final: int, inicio: int = 1, fim: int = 31) -> List[int]:
    inicio, fim, final = int(inicio), int(fim), int(final)
    saida: List[int] = []
    if final == 0 and inicio <= 0 <= fim:
        saida.append(0)
    n = 10 if final == 0 else final
    while n <= fim:
        if n >= inicio:
            saida.append(n)
        n += 10
    return saida


def _cor_pub(cor: dict) -> dict:
    return {
        "id": cor["id"],
        "nome": cor["nome"],
        "hex": cor["hex"],
        "texto": cor["texto"],
        "final": cor["final"],
    }


def _rotulo_numero(numero: int, fim: int = 31) -> str:
    n = int(numero)
    if int(fim) <= 9:
        return str(n)
    return f"{n:02d}"


def _bola(numero: int, fim: int = 31) -> dict:
    cor = cor_da_dezena(numero)
    return {
        "n": int(numero),
        "rotulo": _rotulo_numero(numero, fim),
        **_cor_pub(cor),
    }


def contar(dezenas: Sequence[int]) -> List[int]:
    qtd = [0] * len(PALETA)
    for dezena in dezenas:
        qtd[_IDX[cor_da_dezena(int(dezena))["id"]]] += 1
    return qtd


def _mes(numero: int, nome: str = "") -> Optional[dict]:
    n = int(numero or 0)
    if n < 1 or n > 12:
        return None
    oficial, abrev = MESES[n]
    cor = cor_da_dezena(n)
    return {
        **_cor_pub(cor),
        "n": n,
        "nome": f"{nome or oficial} · {n:02d} · {cor['nome']}",
        "abrev": abrev,
        "rotulo": abrev,
    }


def _vazio(concursos: List[int], tem_mes: bool = True, nota: Optional[str] = None) -> dict:
    return {
        "sucesso": True,
        "vazio": True,
        "total": 0,
        "de": None,
        "ate": None,
        "concursos": concursos,
        "cores": [_cor_pub(c) for c in PALETA],
        "grupos": [],
        "linhas": [],
        "totais": [0] * len(PALETA),
        "medias": [0] * len(PALETA),
        "intervalos": [],
        "repeticao": {
            "comparacoes": 0,
            "media_cores": None,
            "media_bolas": None,
            "distribuicao": [],
        },
        "meses": [],
        "meses_total": 0,
        "tem_mes": bool(tem_mes),
        "nota": nota or NOTA,
    }


def analisar(
    linhas: Sequence[dict],
    de: Optional[int] = None,
    ate: Optional[int] = None,
    ultimos: int = 10,
    inicio: int = 1,
    fim: int = 31,
    tem_mes: bool = True,
    nota: Optional[str] = None,
) -> Dict[str, Any]:
    ordenadas = sorted(linhas, key=lambda r: int(r["concurso"]))
    concursos = [int(r["concurso"]) for r in ordenadas]
    if not ordenadas:
        return _vazio([], tem_mes, nota)

    if de is None and ate is None:
        corte = ordenadas[-max(1, int(ultimos)):]
    else:
        lo = int(de) if de is not None else concursos[0]
        hi = int(ate) if ate is not None else concursos[-1]
        if lo > hi:
            lo, hi = hi, lo
        corte = [r for r in ordenadas if lo <= int(r["concurso"]) <= hi]
    if not corte:
        return _vazio(concursos, tem_mes, nota)

    saida: List[dict] = []
    cores_anteriores: Optional[set] = None
    for registro in corte:
        ordem = [int(x) for x in registro["ordem"]]
        quantidades = contar(ordem)
        cores_agora = {PALETA[i]["id"] for i, n in enumerate(quantidades) if n > 0}
        if cores_anteriores is None:
            repetiu_cores = None
            repetiu_bolas = None
        else:
            repetiu_cores = len(cores_agora & cores_anteriores)
            repetiu_bolas = sum(
                1 for dezena in ordem if cor_da_dezena(dezena)["id"] in cores_anteriores
            )
        saida.append({
            "concurso": int(registro["concurso"]),
            "data": registro.get("data") or "",
            "etiqueta": registro.get("etiqueta") or "",
            "ordem": [_bola(d, fim) for d in ordem],
            "crescente": [_bola(d, fim) for d in sorted(ordem)],
            "quantidades": quantidades,
            "mes": _mes(int(registro.get("mes") or 0), registro.get("mes_nome") or "") if tem_mes else None,
            "repetiu_cores": repetiu_cores,
            "repetiu_bolas": repetiu_bolas,
        })
        cores_anteriores = cores_agora

    total = len(saida)
    totais = [sum(row["quantidades"][i] for row in saida) for i in range(len(PALETA))]
    medias = [round(valor / total, 1) if total else 0 for valor in totais]

    grupos = []
    intervalos = []
    for i, cor in enumerate(PALETA):
        bolas = bolas_da_cor(cor["final"], inicio, fim)
        distribuicao = []
        for quantidade in range(len(bolas) + 1):
            vezes = sum(1 for row in saida if row["quantidades"][i] == quantidade)
            distribuicao.append({
                "quantidade": quantidade,
                "vezes": vezes,
                "pct": round(vezes / total * 100, 1) if total else 0,
            })
        grupos.append({
            **_cor_pub(cor),
            "bolas": [_bola(n, fim) for n in bolas],
            "distribuicao": distribuicao,
        })
        presencas = [j for j, row in enumerate(saida) if row["quantidades"][i] > 0]
        intervalos_idx = [
            presencas[k] - presencas[k - 1] for k in range(1, len(presencas))
        ]
        intervalos.append({
            **_cor_pub(cor),
            "bolas": [_rotulo_numero(n, fim) for n in bolas],
            "presencas": len(presencas),
            "pct": round(len(presencas) / total * 100, 1) if total else 0,
            "intervalo_medio": (
                round(sum(intervalos_idx) / len(intervalos_idx), 1) if intervalos_idx else None
            ),
            "maior_intervalo": max(intervalos_idx) if intervalos_idx else None,
            "atraso": (total - 1 - presencas[-1]) if presencas else total,
        })

    repetidas = [row["repetiu_cores"] for row in saida if row["repetiu_cores"] is not None]
    bolas_repetidas = [row["repetiu_bolas"] for row in saida if row["repetiu_bolas"] is not None]
    dist_rep = []
    if repetidas:
        for quantidade in range(0, 8):
            vezes = sum(1 for valor in repetidas if valor == quantidade)
            dist_rep.append({
                "quantidade": quantidade,
                "vezes": vezes,
                "pct": round(vezes / len(repetidas) * 100, 1),
            })

    if tem_mes:
        meses_qtd = [0] * len(PALETA)
        meses_total = 0
        for row in saida:
            if not row["mes"]:
                continue
            meses_total += 1
            meses_qtd[_IDX[row["mes"]["id"]]] += 1
        meses = []
        for i, cor in enumerate(PALETA):
            meses.append({
                **_cor_pub(cor),
                "vezes": meses_qtd[i],
                "pct": round(meses_qtd[i] / meses_total * 100, 1) if meses_total else 0,
            })
    else:
        meses = []
        meses_total = 0

    return {
        "sucesso": True,
        "vazio": False,
        "total": total,
        "de": saida[0]["concurso"],
        "ate": saida[-1]["concurso"],
        "concursos": concursos,
        "cores": [_cor_pub(c) for c in PALETA],
        "grupos": grupos,
        "linhas": saida,
        "totais": totais,
        "medias": medias,
        "intervalos": intervalos,
        "repeticao": {
            "comparacoes": len(repetidas),
            "media_cores": round(sum(repetidas) / len(repetidas), 1) if repetidas else None,
            "media_bolas": (
                round(sum(bolas_repetidas) / len(bolas_repetidas), 1) if bolas_repetidas else None
            ),
            "distribuicao": dist_rep,
        },
        "meses": meses,
        "meses_total": meses_total,
        "tem_mes": bool(tem_mes),
        "nota": nota or NOTA,
    }


def carregar_linhas(modality_key: str = "diadesorte") -> List[dict]:
    """Lê os concursos oficiais já gravados. Exige contexto da aplicação."""
    from analise_estudos.service_factory import make_estudos_base

    key = (modality_key or "diadesorte").strip().lower()
    base = make_estudos_base(key)
    linhas = []
    for sorteio in base.carregar_sorteios_asc("geral", 0):
        comum = {
            "concurso": int(sorteio.concurso),
            "data": getattr(sorteio, "data", "") or "",
        }
        if key == "duplasena" and hasattr(sorteio, "sorteio2_ordem_lista"):
            linhas.append({
                **comum,
                "ordem": [int(n) for n in sorteio.sorteio1_ordem_lista()],
                "etiqueta": "1º",
                "mes": 0,
                "mes_nome": "",
            })
            linhas.append({
                **comum,
                "ordem": [int(n) for n in sorteio.sorteio2_ordem_lista()],
                "etiqueta": "2º",
                "mes": 0,
                "mes_nome": "",
            })
            continue
        linhas.append({
            **comum,
            "ordem": [int(n) for n in base.dezenas_ordem(sorteio)],
            "mes": int(getattr(sorteio, "mes_num", 0) or 0),
            "mes_nome": getattr(sorteio, "mes_nome", "") or "",
        })
    return linhas


NOTA_GERAL = (
    "A cor da dezena é o algarismo final. "
    "Esta leitura descreve os concursos já sorteados e não indica o próximo."
)
NOTAS_MODALIDADE = {
    "diadesorte": NOTA,
    "duplasena": (
        "A Dupla Sena faz dois sorteios de 6 dezenas no mesmo concurso. "
        "A cor é o algarismo final. Cada sorteio entra numa linha."
    ),
    "maismilionaria": (
        "A cor é o algarismo final das 6 dezenas. Os trevos não entram nesta conta."
    ),
    "timemania": (
        "A cor é o algarismo final das 7 dezenas. O Time do Coração não entra nesta conta."
    ),
    "supersete": (
        "O Super Sete sorteia um dígito de 0 a 9 em cada uma das 7 colunas. A cor é a do dígito."
    ),
}


def analisar_modalidade(
    modality_key: str,
    de: Optional[int] = None,
    ate: Optional[int] = None,
    ultimos: int = 10,
) -> Dict[str, Any]:
    from configuracoes.regras_modalidade import get_regras

    key = (modality_key or "").strip().lower()
    regras = get_regras(key)
    return analisar(
        carregar_linhas(key),
        de=de,
        ate=ate,
        ultimos=ultimos,
        inicio=int(regras["dezena_min"]),
        fim=int(regras["dezena_max"]),
        tem_mes=(key == "diadesorte"),
        nota=NOTAS_MODALIDADE.get(key, NOTA_GERAL),
    )
