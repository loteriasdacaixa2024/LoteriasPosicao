# -*- coding: utf-8 -*-
"""
Select padronizado — Mês da Sorte (+ Atrasado / + Frequente / meses / + Aleatório).

Regras de resolução (manutenção)
================================
Cada opção do select é independente; não há pesos cruzados entre critérios.

+ Atrasado
    Resolve para o mês com maior atraso histórico (empate → menor mes_num).
    Todas as apostas do lote recebem o MESMO mês.

+ Frequente
    Resolve para o mês com maior frequência histórica (empate → menor mes_num).
    Todas as apostas do lote recebem o MESMO mês.

mês fixo (1–12 ou nome)
    Usa exatamente o mês escolhido em todas as apostas.

+ Aleatório
    NÃO sorteia um único mês para o lote inteiro.
    Distribui meses 1–12 de forma equilibrada:
      - embaralha blocos de 12 meses sem reposição;
      - repete blocos até cobrir a quantidade de apostas;
      - nenhum mês aparece mais que ceil(n/12) vezes;
      - não favorece Dezembro nem qualquer outro mês.
    Em export de várias construções, a distribuição é contínua
    no total de apostas (não reinicia por construção).

API pública
-----------
- montar_opcoes_mes_sorte / opcoes_mes_sorte_diadesorte  → opções do select
- resolver_mes_sorte(valor)                             → 1 mês (critérios fixos
                                                          ou 1 sorteio aleatório)
- distribuir_meses_aleatorios(n)                        → n meses equilibrados
- resolver_meses_para_lote(valor, n)                    → lista de n meses
- eh_criterio_aleatorio(valor)                          → bool
"""
from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional, Sequence, Union

MESES_NOME = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}
MESES_ABREV = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}

CRITERIOS_ESPECIAIS = ("atrasado", "frequente", "aleatorio")
MesValor = Union[str, int, None]


def _item(mn: int, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    out = {
        "mes_num": int(mn),
        "mes_nome": MESES_NOME.get(int(mn), f"Mês {mn}"),
        "mes_abrev": MESES_ABREV.get(int(mn), str(mn)),
    }
    if extra:
        out.update(extra)
    return out


def estatisticas_meses_from_rows(sorteios_desc: Sequence[Any]) -> List[Dict[str, Any]]:
    """sorteios_desc: mais recente primeiro. Retorna 12 meses com freq/atraso."""
    if not sorteios_desc:
        return [_item(m, {"freq": 0, "atraso": 0, "pct": 0.0}) for m in range(1, 13)]

    total = len(sorteios_desc)
    ultimo = int(getattr(sorteios_desc[0], "concurso", 0) or 0)
    freq = {m: 0 for m in range(1, 13)}
    visto = {m: 0 for m in range(1, 13)}

    for s in sorteios_desc:
        mn = getattr(s, "mes_num", None)
        try:
            mn = int(mn or 0)
        except (TypeError, ValueError):
            continue
        if not (1 <= mn <= 12):
            continue
        freq[mn] += 1
        if visto[mn] == 0:
            visto[mn] = int(getattr(s, "concurso", 0) or 0)

    out: List[Dict[str, Any]] = []
    for m in range(1, 13):
        atraso = (ultimo - visto[m]) if visto[m] > 0 else total
        pct = round(freq[m] / total * 100, 1) if total else 0.0
        out.append(_item(m, {"freq": freq[m], "atraso": atraso, "pct": pct}))
    return out


def carregar_estatisticas_meses(SorteioModel: Any) -> List[Dict[str, Any]]:
    from models.shared import db
    from sqlalchemy import desc

    rows = db.session.query(SorteioModel).order_by(desc(SorteioModel.concurso)).all()
    return estatisticas_meses_from_rows(rows)


def _pick_max(meses: Sequence[Dict[str, Any]], key: str) -> Dict[str, Any]:
    if not meses:
        return _item(1, {"freq": 0, "atraso": 0, "pct": 0.0})
    # Empate: menor mes_num (evita favorecer Dezembro em empates).
    return max(meses, key=lambda m: (int(m.get(key, 0) or 0), -int(m.get("mes_num", 0) or 0)))


def montar_opcoes_mes_sorte(meses_stats: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Ordem do select (modelo de referência):
      1) + Atrasado (Nome)
      2) + Frequente (Nome)
      3) meses restantes (1–12, excluindo os dois acima)
      4) + Aleatório
    """
    stats = list(meses_stats) if meses_stats else [_item(m) for m in range(1, 13)]
    atrasado = _pick_max(stats, "atraso")
    frequente = _pick_max(stats, "freq")
    excluir = {int(atrasado["mes_num"]), int(frequente["mes_num"])}

    opcoes: List[Dict[str, Any]] = [
        {
            "value": "atrasado",
            "label": f"+ Atrasado ({atrasado['mes_nome']})",
            "mes_num": int(atrasado["mes_num"]),
            "criterio": "atrasado",
        },
        {
            "value": "frequente",
            "label": f"+ Frequente ({frequente['mes_nome']})",
            "mes_num": int(frequente["mes_num"]),
            "criterio": "frequente",
        },
    ]
    for m in stats:
        mn = int(m["mes_num"])
        if mn in excluir:
            continue
        opcoes.append({
            "value": str(mn),
            "label": m.get("mes_nome") or MESES_NOME.get(mn, str(mn)),
            "mes_num": mn,
            "criterio": "fixo",
        })
    opcoes.append({
        "value": "aleatorio",
        "label": "+ Aleatório",
        "mes_num": None,
        "criterio": "aleatorio",
    })

    return {
        "sucesso": True,
        "atrasado": atrasado,
        "frequente": frequente,
        "meses": stats,
        "opcoes": opcoes,
        "default": "atrasado",
    }


def opcoes_mes_sorte_diadesorte() -> Dict[str, Any]:
    from models.sorteio_diadesorte import SorteioDiaDeSorte

    return montar_opcoes_mes_sorte(carregar_estatisticas_meses(SorteioDiaDeSorte))


def eh_criterio_aleatorio(valor: MesValor) -> bool:
    if valor is None or valor == "":
        return False
    return str(valor).strip().lower() in ("aleatorio", "aleatório", "random")


def distribuir_meses_aleatorios(quantidade: int, *, rng: Optional[random.Random] = None) -> List[int]:
    """
    Distribuição equilibrada de meses 1–12 para `quantidade` apostas.

    Usa blocos embaralhados sem reposição: em cada bloco de 12, cada mês
    aparece no máximo 1 vez. Assim, para n apostas, a frequência máxima
    de qualquer mês é ceil(n/12) e a mínima é floor(n/12).
    """
    n = max(0, int(quantidade or 0))
    if n == 0:
        return []
    r = rng or random
    out: List[int] = []
    while len(out) < n:
        bloco = list(range(1, 13))
        r.shuffle(bloco)
        out.extend(bloco)
    return out[:n]


def _payload_opcoes(
    opcoes_payload: Optional[Dict[str, Any]] = None,
    SorteioModel: Any = None,
) -> Dict[str, Any]:
    if opcoes_payload is not None:
        return opcoes_payload
    if SorteioModel is not None:
        return montar_opcoes_mes_sorte(carregar_estatisticas_meses(SorteioModel))
    try:
        return opcoes_mes_sorte_diadesorte()
    except Exception:
        return montar_opcoes_mes_sorte([])


def resolver_mes_sorte(
    valor: MesValor,
    *,
    opcoes_payload: Optional[Dict[str, Any]] = None,
    SorteioModel: Any = None,
) -> Optional[int]:
    """
    Converte valor do select em um único mes_num (1–12).

    Aceita: atrasado | frequente | aleatorio | 1..12 | nome do mês.
    Para lotes (export/TXT), prefira resolver_meses_para_lote — em
    aleatorio um único sorteio NÃO deve ser reutilizado em todas as linhas.
    """
    if valor is None or valor == "":
        return None

    raw = str(valor).strip()
    low = raw.lower()

    if low.isdigit():
        n = int(low)
        return n if 1 <= n <= 12 else None

    payload = _payload_opcoes(opcoes_payload, SorteioModel)

    if low == "atrasado":
        return int((payload.get("atrasado") or {}).get("mes_num") or 1)
    if low == "frequente":
        return int((payload.get("frequente") or {}).get("mes_num") or 1)
    if eh_criterio_aleatorio(low):
        return random.randint(1, 12)

    for m in range(1, 13):
        if MESES_NOME.get(m, "").lower() == low:
            return m
        if MESES_ABREV.get(m, "").lower() == low:
            return m

    return None


def resolver_meses_para_lote(
    valor: MesValor,
    quantidade: int,
    *,
    opcoes_payload: Optional[Dict[str, Any]] = None,
    SorteioModel: Any = None,
    rng: Optional[random.Random] = None,
) -> List[int]:
    """
    Resolve o critério do select em uma lista com `quantidade` meses (1–12).

    - atrasado / frequente / fixo → mesmo mês repetido
    - aleatorio → distribuição equilibrada (ver distribuir_meses_aleatorios)
    """
    n = max(0, int(quantidade or 0))
    if n == 0:
        return []

    if eh_criterio_aleatorio(valor):
        return distribuir_meses_aleatorios(n, rng=rng)

    mn = resolver_mes_sorte(valor, opcoes_payload=opcoes_payload, SorteioModel=SorteioModel)
    if mn is None:
        return []
    return [int(mn)] * n


def max_freq_esperada(quantidade: int) -> int:
    """Teto teórico de frequência de um mês em distribuição equilibrada."""
    n = max(0, int(quantidade or 0))
    if n <= 0:
        return 0
    return int(math.ceil(n / 12.0))
