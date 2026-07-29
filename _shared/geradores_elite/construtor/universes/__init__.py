# -*- coding: utf-8 -*-
"""Utilitários — universo de dígitos → dezenas elegíveis."""
from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Optional, Set


POOL_MIN_RECOMENDADO = 4
# Universo canônico do Gerador por Dígitos — idêntico em todas as modalidades.
DIGITOS_UNIVERSO = tuple(range(10))  # 0..9


def normalizar_pool_digitos(raw: Iterable[Any]) -> List[int]:
    out: List[int] = []
    vistos: Set[int] = set()
    for x in raw:
        try:
            d = int(x)
        except (TypeError, ValueError):
            continue
        if d < 0 or d > 9 or d in vistos:
            continue
        if d not in DIGITOS_UNIVERSO:
            continue
        vistos.add(d)
        out.append(d)
    return sorted(out)


def digitos_da_dezena(n: int, pad_width: int = 2) -> List[int]:
    """Extrai dígitos de um valor. pad_width<=1 = valor já é um dígito (ex.: Super Sete)."""
    if pad_width <= 1:
        return [int(n)]
    s = f"{int(n):0{pad_width}d}"
    return [int(ch) for ch in s if ch.isdigit()]


def dezena_compativel(n: int, pool: Iterable[int], pad_width: int = 2) -> bool:
    """Estrito: todos os dígitos da dezena ∈ pool."""
    allowed = set(int(d) for d in pool)
    if not allowed:
        return False
    return all(d in allowed for d in digitos_da_dezena(n, pad_width))


def expandir_elegiveis(
    pool: Iterable[int],
    dezena_min: int,
    dezena_max: int,
    pad_width: int = 2,
) -> List[int]:
    pool_n = normalizar_pool_digitos(pool)
    if not pool_n:
        return []
    return [
        n for n in range(dezena_min, dezena_max + 1)
        if dezena_compativel(n, pool_n, pad_width)
    ]


def combinacoes_possiveis(n_elegiveis: int, k: int) -> int:
    if k <= 0 or n_elegiveis < k:
        return 0
    return int(math.comb(n_elegiveis, k))


def qtd_digitos_distintos_aposta(apostas_dezenas: Iterable[int], pad_width: int = 2) -> int:
    digs: Set[int] = set()
    for n in apostas_dezenas:
        digs.update(digitos_da_dezena(int(n), pad_width))
    return len(digs)


def max_digitos_teorico(pool_size: int, k: int, pad_width: int = 2) -> int:
    """Teto absoluto de dígitos distintos numa aposta restrita ao pool."""
    return max(0, min(10, int(pool_size), int(k) * max(1, int(pad_width))))


def diagnosticar_filtros_digitos(
    pool: Iterable[Any],
    dezena_min: int,
    dezena_max: int,
    k: int,
    pad_width: int = 2,
    *,
    exigir_qtd_digitos: Optional[int] = None,
    qtd_apostas: int = 1,
    max_enum: int = 5000,
) -> Dict[str, Any]:
    """
    Detecta conflitos entre pool / tamanho da aposta / exigir qtd de dígitos
    antes (ou após) a geração. Retorna motivos e sugestões acionáveis.
    """
    from itertools import combinations

    pool_n = normalizar_pool_digitos(pool)
    k = int(k)
    aval = resumo_pool(pool_n, dezena_min, dezena_max, k, pad_width)
    conflitos: List[Dict[str, Any]] = []
    sugestoes: List[str] = []

    def _add(
        codigo: str,
        mensagem: str,
        filtros: List[str],
        hints: Optional[List[str]] = None,
    ) -> None:
        conflitos.append({
            "codigo": codigo,
            "mensagem": mensagem,
            "filtros": filtros,
            "sugestoes": list(hints or []),
        })
        for h in (hints or []):
            if h not in sugestoes:
                sugestoes.append(h)

    if not pool_n:
        _add(
            "pool_vazio",
            "Nenhum dígito selecionado no pool.",
            ["pool"],
            ["Selecione ao menos 1 dígito (recomendado: 4 ou mais)."],
        )
        return _pacote_diagnostico(False, aval, conflitos, sugestoes)

    if k < 1:
        _add(
            "pick_invalido",
            "Quantidade de dezenas por aposta inválida.",
            ["dezenas_por_aposta"],
            ["Escolha um valor dentro do permitido pela modalidade."],
        )

    if not aval["pode_gerar"]:
        _add(
            "elegiveis_insuficientes",
            (
                f"Há apenas {aval['qtd_elegiveis']} dezena(s) elegível(is) no pool "
                f"[{aval['pool_fmt']}] para apostas de {k} dezenas "
                f"(C({aval['qtd_elegiveis']},{k})=0)."
            ),
            ["pool", "dezenas_por_aposta"],
            [
                "Amplie o pool de dígitos para aumentar as dezenas elegíveis.",
                "Ou reduza a quantidade de dezenas por aposta (se a modalidade permitir).",
            ],
        )

    exigir = None
    if exigir_qtd_digitos is not None and str(exigir_qtd_digitos).strip() != "":
        try:
            exigir = int(exigir_qtd_digitos)
        except (TypeError, ValueError):
            _add(
                "exigir_invalido",
                "Valor inválido em «Exigir qtd dígitos».",
                ["exigir_qtd_digitos"],
                ["Escolha um número entre 0 e 9, ou «Não exigir»."],
            )
            exigir = None

    if exigir is not None:
        if exigir < 0 or exigir > 9:
            _add(
                "exigir_fora_faixa",
                f"«Exigir qtd dígitos» = {exigir} está fora da faixa válida (0–9).",
                ["exigir_qtd_digitos"],
                ["Ajuste para um valor entre 0 e 9, ou desmarque a exigência."],
            )
        elif exigir == 0:
            _add(
                "exigir_zero",
                (
                    "Exigir 0 dígitos distintos é impossível: toda aposta usa ao menos "
                    "um dígito do universo 0–9. Use «Não exigir» ou um valor de 1 a 9."
                ),
                ["exigir_qtd_digitos"],
                ["Selecione «Não exigir» ou um valor de 1 a 9."],
            )
        else:
            teto_pool = len(pool_n)
            teto_teorico = max_digitos_teorico(teto_pool, k, pad_width)
            if exigir > teto_pool:
                _add(
                    "exigir_maior_que_pool",
                    (
                        f"Distribuição de dígitos impossível: exige {exigir} dígitos distintos, "
                        f"mas o pool tem apenas {teto_pool} "
                        f"({aval['pool_fmt']}). "
                        "Pela regra estrita, a aposta só pode usar dígitos do pool."
                    ),
                    ["pool", "exigir_qtd_digitos"],
                    [
                        f"Reduza «Exigir qtd dígitos» para no máximo {teto_pool}.",
                        f"Ou amplie o pool para pelo menos {exigir} dígitos.",
                        "Ou selecione «Não exigir».",
                    ],
                )
            elif exigir > teto_teorico:
                _add(
                    "exigir_maior_que_capacidade",
                    (
                        f"Impossível obter {exigir} dígitos distintos em apostas de {k} "
                        f"dezena(s) (teto teórico com este pool: {teto_teorico})."
                    ),
                    ["dezenas_por_aposta", "exigir_qtd_digitos", "pool"],
                    [
                        f"Reduza a exigência para ≤ {teto_teorico}.",
                        "Ou aumente dezenas/aposta / amplie o pool.",
                    ],
                )
            elif aval["pode_gerar"] and aval["combinacoes_possiveis"] <= max_enum:
                match = 0
                dist_obs: Set[int] = set()
                for combo in combinations(aval["elegiveis"], k):
                    qd = qtd_digitos_distintos_aposta(combo, pad_width)
                    dist_obs.add(qd)
                    if qd == exigir:
                        match += 1
                if match == 0:
                    poss = ", ".join(str(x) for x in sorted(dist_obs)) or "—"
                    _add(
                        "exigir_sem_combinacao",
                        (
                            f"Nenhuma das {aval['combinacoes_possiveis']} combinação(ões) "
                            f"do pool resulta em exatamente {exigir} dígito(s) distinto(s). "
                            f"Quantidades possíveis neste pool: {poss}."
                        ),
                        ["pool", "exigir_qtd_digitos", "dezenas_por_aposta"],
                        [
                            f"Escolha «Exigir qtd dígitos» entre: {poss}.",
                            "Ou amplie/altere o pool.",
                            "Ou selecione «Não exigir».",
                        ],
                    )
                elif match < max(1, int(qtd_apostas or 1)) and aval["combinacoes_possiveis"] < int(qtd_apostas or 1):
                    # poucas combinações totais — aviso informativo, não bloqueia se match>=1
                    pass

    ok = len(conflitos) == 0
    return _pacote_diagnostico(ok, aval, conflitos, sugestoes)


def _pacote_diagnostico(
    ok: bool,
    aval: Dict[str, Any],
    conflitos: List[Dict[str, Any]],
    sugestoes: List[str],
) -> Dict[str, Any]:
    if ok:
        mensagem = "Filtros compatíveis."
    elif len(conflitos) == 1:
        mensagem = conflitos[0]["mensagem"]
    else:
        mensagem = (
            "Filtros incompatíveis: "
            + " | ".join(c["mensagem"] for c in conflitos)
        )
    return {
        "ok": ok,
        "avaliacao": aval,
        "conflitos": conflitos,
        "sugestoes": sugestoes,
        "mensagem": mensagem,
        "filtros_em_conflito": sorted({
            f for c in conflitos for f in (c.get("filtros") or [])
        }),
    }


def resumo_pool(
    pool: Iterable[int],
    dezena_min: int,
    dezena_max: int,
    k: int,
    pad_width: int = 2,
) -> Dict[str, Any]:
    pool_n = normalizar_pool_digitos(pool)
    elegiveis = expandir_elegiveis(pool_n, dezena_min, dezena_max, pad_width)
    n = len(elegiveis)
    combos = combinacoes_possiveis(n, k)
    abaixo_rec = len(pool_n) < POOL_MIN_RECOMENDADO
    return {
        "pool": pool_n,
        "pool_fmt": ",".join(str(d) for d in pool_n),
        "qtd_pool": len(pool_n),
        "min_recomendado": POOL_MIN_RECOMENDADO,
        "abaixo_recomendado": abaixo_rec,
        "elegiveis": elegiveis,
        "qtd_elegiveis": n,
        "dezenas_por_aposta": k,
        "combinacoes_possiveis": combos,
        "pode_gerar": combos > 0,
        "aviso": (
            f"Pool com {len(pool_n)} dígito(s) — abaixo do mínimo recomendado ({POOL_MIN_RECOMENDADO})."
            if abaixo_rec and pool_n else None
        ),
    }
