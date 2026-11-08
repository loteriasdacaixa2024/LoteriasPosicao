# -*- coding: utf-8 -*-
"""Regras puras do Engine Final: ciclo, hora da recorrência e trava do lote.

Toda análise nova que for entrar no engine precisa de um veredito
cabe, nao_cabe ou nao_opina. O catálogo abaixo é a lista que a tela mostra.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

CATALOGO_ANALISES: Tuple[Tuple[str, str], ...] = (
    ("ciclo", "Ciclo das dezenas"),
    ("recorrencia", "Recorrências"),
    ("padrao_inicial", "Padrão inicial"),
    ("pares", "Pares"),
    ("impares", "Ímpares"),
    ("repetidas", "Repetidas"),
    ("sequencias", "Sequências"),
    ("finais", "Finais iguais"),
    ("soma", "Soma das dezenas"),
    ("linhas", "Linhas"),
    ("diagonal", "Diagonal"),
    ("padrao_final", "Padrão final"),
    ("digitos", "Dígitos utilizados"),
    ("soma_digitos", "Soma dos dígitos"),
    ("gaps", "Gaps"),
    ("sniper", "Sniper"),
    ("posicao", "Posição"),
    ("concentracao", "Concentração"),
    ("modelos", "Central de Modelos"),
)


def digitos_do_padrao(padrao: str) -> List[int]:
    return [int(x) for x in str(padrao or "").replace(",", " ").split() if str(x).strip().isdigit()]


def padrao_cabe_no_pool(padrao: str, numeros: Sequence[int], k: int, travar: bool) -> bool:
    """O padrão comporta o ciclo.

    Com trava, todas as dezenas presas cabem nas casas do padrão.
    Sem trava, o padrão inteiro se monta só com o pool (recorte).
    """
    digs = digitos_do_padrao(padrao)
    if len(digs) != int(k):
        return False
    need = Counter(digs)
    have = Counter(int(n) // 10 for n in numeros)
    if travar:
        return all(need.get(dig, 0) >= q for dig, q in have.items())
    return all(have.get(dig, 0) >= q for dig, q in need.items())


def hora_do_padrao(row: Dict[str, Any], ultimo_geral: Optional[int]) -> Optional[Dict[str, Any]]:
    """Mesma hora da aba Recorrências: última saída + espaço médio, margem de 3."""
    esp = row.get("intervalo_medio")
    ult_p = row.get("ultimo_concurso")
    if esp is None or ult_p is None or ultimo_geral is None:
        return None
    try:
        alvo = int(ult_p) + int(round(float(esp)))
        falta = alvo - int(ultimo_geral)
        desde = row.get("desde_ultima")
        agora = desde is not None and int(desde) == 0
    except (TypeError, ValueError):
        return None
    return {
        "hora_alvo": alvo,
        "hora_falta": falta,
        "hora_abs": abs(falta),
        "na_hora": (not agora) and abs(falta) <= 3,
        "agora": agora,
    }


def resolver_ciclo(
    pendentes: Sequence[int],
    k: int,
    dmin: int,
    dmax: int,
) -> Dict[str, Any]:
    """Livre sem pendentes. Trava quando cabem no jogo. Recorte quando sobram."""
    pend = sorted({int(x) for x in pendentes})
    full = list(range(int(dmin), int(dmax) + 1))
    k = int(k)
    if not pend:
        return {
            "modo": "livre",
            "veredito": "nao_opina",
            "universo": full,
            "locked": [],
            "pool_padrao": full,
            "travar_padrao": False,
            "leitura": "Nenhuma dezena pendente neste ciclo. O ciclo não trava o lote.",
        }
    if len(pend) <= k:
        return {
            "modo": "travar",
            "veredito": "cabe",
            "universo": full,
            "locked": list(pend),
            "pool_padrao": list(pend),
            "travar_padrao": True,
            "leitura": (
                f"{len(pend)} pendente(s) entram em todo jogo. "
                "O complemento sai das dezenas que já fecharam neste ciclo."
            ),
        }
    return {
        "modo": "recorte",
        "veredito": "cabe",
        "universo": list(pend),
        "locked": [],
        "pool_padrao": list(pend),
        "travar_padrao": False,
        "leitura": f"{len(pend)} pendentes. Cada jogo é um recorte só dessas dezenas.",
    }


def _descricao_padrao(padrao: str, pronta: str) -> str:
    if pronta:
        return pronta
    try:
        from analise_inteligentes_diadesorte.service import descricao_bma_do_padrao

        return descricao_bma_do_padrao(padrao)
    except Exception:
        return padrao


def padroes_na_hora(
    padroes: Sequence[Dict[str, Any]],
    ultimo_geral: Optional[int],
    numeros: Sequence[int],
    k: int,
    travar: bool,
    freq: Optional[Counter] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """Padrões na hora cujo dígito cabe no pool do ciclo. Devolve (lista, quantos estavam na hora)."""
    freq = freq or Counter()
    na_hora_total = 0
    out: List[Dict[str, Any]] = []
    for row in padroes or []:
        hora = hora_do_padrao(row, ultimo_geral)
        if not hora or not hora["na_hora"]:
            continue
        na_hora_total += 1
        pad = " ".join(str(d) for d in digitos_do_padrao(str(row.get("padrao") or "")))
        if not pad or not padrao_cabe_no_pool(pad, numeros, k, travar):
            continue
        vezes = int(freq.get(pad, 0))
        out.append({
            "padrao": pad,
            "vezes": vezes,
            "pct": 0.0,
            "bma": _descricao_padrao(pad, str(row.get("descricao") or "")),
            "hora_abs": int(hora["hora_abs"]),
            "hora_alvo": int(hora["hora_alvo"]),
        })
    out.sort(key=lambda r: (int(r["hora_abs"]), -int(r["vezes"]), str(r["padrao"])))
    return out, na_hora_total


def voto_intersecta(votos: Optional[Set[int]], universo: Sequence[int]) -> str:
    if not votos:
        return "nao_opina"
    uni = set(int(n) for n in universo)
    if not uni or not (set(int(n) for n in votos) & uni):
        return "nao_cabe"
    return "cabe"


def diag_alcanca(top_diags: Sequence[Dict[str, Any]], universo: Sequence[int]) -> bool:
    uni = set(int(n) for n in universo)
    if len(uni) < 2:
        return False
    for seg in top_diags or []:
        nums = [int(n) for n in (seg.get("nums") or [])]
        if sum(1 for n in nums if n in uni) >= 2:
            return True
    return False


def aplicar_trava(
    nums: Sequence[int],
    locked: Sequence[int],
    universo: Sequence[int],
    k: int,
) -> List[int]:
    """Garante as dezenas travadas e restringe o resto ao universo do ciclo."""
    k = int(k)
    fixos: List[int] = []
    for n in locked or []:
        n = int(n)
        if n not in fixos:
            fixos.append(n)
    if len(fixos) > k:
        fixos = fixos[:k]
    if len(fixos) == k:
        return sorted(fixos)
    uni: List[int] = []
    for n in universo or []:
        n = int(n)
        if n not in uni:
            uni.append(n)
    uni_set = set(uni)
    fixo_set = set(fixos)
    resto = [int(n) for n in nums if int(n) not in fixo_set and (not uni_set or int(n) in uni_set)]
    precisa = k - len(fixos)
    escolhidos: List[int] = []
    for n in resto:
        if n not in escolhidos:
            escolhidos.append(n)
        if len(escolhidos) >= precisa:
            break
    if len(escolhidos) < precisa:
        for n in uni:
            if n in fixo_set or n in escolhidos:
                continue
            escolhidos.append(n)
            if len(escolhidos) >= precisa:
                break
    return sorted(fixos + escolhidos[:precisa])


def cortar_universo(
    leitura: Dict[str, Any],
    candidatos: Optional[Sequence[int]],
) -> Tuple[List[int], List[int], bool]:
    """Interseção com o conjunto-base. Se a trava não cabe nele, o conjunto sai."""
    universo = [int(n) for n in (leitura.get("universo") or [])]
    locked = [int(n) for n in (leitura.get("locked") or [])]
    if not universo:
        base = [int(n) for n in (candidatos or [])]
        return base, locked, False
    if not candidatos:
        return universo, locked, False
    permitidos = {int(n) for n in candidatos}
    modo = leitura.get("ciclo_modo")
    if locked and any(n not in permitidos for n in locked):
        return universo, locked, True
    cortado = [n for n in universo if n in permitidos]
    k = int(leitura.get("k_historico") or 0)
    if modo == "recorte" and k and len(cortado) < k:
        return universo, locked, True
    if not cortado:
        return universo, locked, True
    return cortado, locked, False
