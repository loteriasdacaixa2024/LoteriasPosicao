# -*- coding: utf-8 -*-
"""
Select padronizado — extras de análise (Time do Coração / Trevos).

Espelha diadesorte/mes_sorte_select.py:
  + Atrasado  → o item com maior atraso histórico (empate → menor número)
  + Frequente → o item com maior frequência (empate → menor número)
  + Aleatório → distribuição equilibrada em blocos sem reposição
  fixo        → o valor escolhido em todas as apostas do lote

Trevos (+Milionária): cada aposta leva 2 trevos (01–06).
  atrasado / frequente resolvem para o par (2 trevos) correspondente.
"""
from __future__ import annotations

import itertools
import random
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

CRITERIOS_ESPECIAIS = ("atrasado", "frequente", "aleatorio")
ExtraValor = Union[str, int, None]


def _pick_max(items: Sequence[Dict[str, Any]], key: str, id_key: str) -> Dict[str, Any]:
    if not items:
        return {}
    return max(
        items,
        key=lambda it: (int(it.get(key, 0) or 0), -int(it.get(id_key, 0) or 0)),
    )


def _top_n(items: Sequence[Dict[str, Any]], key: str, id_key: str, n: int) -> List[Dict[str, Any]]:
    ranked = sorted(
        items,
        key=lambda it: (int(it.get(key, 0) or 0), -int(it.get(id_key, 0) or 0)),
        reverse=True,
    )
    return ranked[: max(0, n)]


def _distribuir_bloco(universo: Sequence[Any], quantidade: int, *, rng: Optional[random.Random] = None) -> List[Any]:
    n = max(0, int(quantidade or 0))
    if n == 0 or not universo:
        return []
    r = rng or random
    pool = list(universo)
    out: List[Any] = []
    while len(out) < n:
        bloco = list(pool)
        r.shuffle(bloco)
        out.extend(bloco)
    return out[:n]


def _pares_trevos() -> List[Tuple[int, int]]:
    return list(itertools.combinations(range(1, 7), 2))


def _fmt_par(par: Sequence[int]) -> str:
    nums = sorted(int(x) for x in par)
    return " ".join(f"{n:02d}" for n in nums)


# ---------------------------------------------------------------------------
# Time do Coração (Timemania)
# ---------------------------------------------------------------------------

def estatisticas_times_from_rows(sorteios_desc: Sequence[Any], catalog: Dict[int, str]) -> List[Dict[str, Any]]:
    total = len(sorteios_desc)
    ultimo = int(getattr(sorteios_desc[0], "concurso", 0) or 0) if sorteios_desc else 0
    freq = {t: 0 for t in catalog}
    visto = {t: 0 for t in catalog}
    for s in sorteios_desc:
        tn = getattr(s, "time_num", None)
        try:
            tn = int(tn or 0)
        except (TypeError, ValueError):
            continue
        if tn not in freq:
            continue
        freq[tn] += 1
        if visto[tn] == 0:
            visto[tn] = int(getattr(s, "concurso", 0) or 0)
    out: List[Dict[str, Any]] = []
    for t, nome in catalog.items():
        atraso = (ultimo - visto[t]) if visto[t] > 0 else total
        pct = round(freq[t] / total * 100, 1) if total else 0.0
        out.append({
            "time_num": int(t),
            "time_nome": nome or f"Time {t}",
            "freq": freq[t],
            "atraso": atraso,
            "pct": pct,
        })
    return out


def montar_opcoes_time_coracao(times_stats: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    stats = list(times_stats)
    if not stats:
        return {"sucesso": False, "erro": "Sem estatística de times.", "opcoes": []}
    atrasado = _pick_max(stats, "atraso", "time_num")
    frequente = _pick_max(stats, "freq", "time_num")
    excluir = {
        int(atrasado.get("time_num") or 0),
        int(frequente.get("time_num") or 0),
    }
    opcoes: List[Dict[str, Any]] = [
        {
            "value": "atrasado",
            "label": f"+ Atrasado ({atrasado.get('time_nome')})",
            "time_num": int(atrasado.get("time_num") or 1),
            "time_nome": atrasado.get("time_nome") or "",
            "criterio": "atrasado",
        },
        {
            "value": "frequente",
            "label": f"+ Frequente ({frequente.get('time_nome')})",
            "time_num": int(frequente.get("time_num") or 1),
            "time_nome": frequente.get("time_nome") or "",
            "criterio": "frequente",
        },
    ]
    for t in stats:
        tn = int(t.get("time_num") or 0)
        if tn in excluir:
            continue
        opcoes.append({
            "value": str(tn),
            "label": t.get("time_nome") or f"Time {tn}",
            "time_num": tn,
            "time_nome": t.get("time_nome") or f"Time {tn}",
            "criterio": "fixo",
        })
    opcoes.append({
        "value": "aleatorio",
        "label": "+ Aleatório",
        "time_num": None,
        "criterio": "aleatorio",
    })
    return {
        "sucesso": True,
        "atrasado": atrasado,
        "frequente": frequente,
        "times": stats,
        "opcoes": opcoes,
        "default": "atrasado",
    }


def opcoes_time_coracao() -> Dict[str, Any]:
    from models.sorteio_timemania import TIMES_DO_CORACAO, SorteioTimemania
    from models.shared import db
    from sqlalchemy import desc

    rows = db.session.query(SorteioTimemania).order_by(desc(SorteioTimemania.concurso)).all()
    catalog = {int(k): str(v) for k, v in (TIMES_DO_CORACAO or {}).items()}
    if not catalog:
        catalog = {i: f"Time {i}" for i in range(1, 81)}
    return montar_opcoes_time_coracao(estatisticas_times_from_rows(rows, catalog))


def resolver_time_para_lote(
    valor: ExtraValor,
    quantidade: int,
    *,
    opcoes_payload: Optional[Dict[str, Any]] = None,
    rng: Optional[random.Random] = None,
) -> List[Dict[str, Any]]:
    """Lista de {time_num, time_nome} com `quantidade` itens."""
    n = max(0, int(quantidade or 0))
    if n == 0:
        return []
    payload = opcoes_payload or {}
    times = list(payload.get("times") or [])
    by_num = {int(t.get("time_num") or 0): t for t in times}
    universo = sorted(by_num.keys()) or list(range(1, 81))

    raw = "" if valor is None else str(valor).strip()
    low = raw.lower()

    def _item(tn: int) -> Dict[str, Any]:
        t = by_num.get(int(tn)) or {}
        return {
            "time_num": int(tn),
            "time_nome": t.get("time_nome") or f"Time {tn}",
        }

    if low in ("aleatorio", "aleatório", "random"):
        return [_item(tn) for tn in _distribuir_bloco(universo, n, rng=rng)]
    if low == "atrasado":
        tn = int((payload.get("atrasado") or {}).get("time_num") or universo[0])
        return [_item(tn)] * n
    if low == "frequente":
        tn = int((payload.get("frequente") or {}).get("time_num") or universo[0])
        return [_item(tn)] * n
    if raw.isdigit():
        tn = int(raw)
        if tn in by_num or 1 <= tn <= 80:
            return [_item(tn)] * n
    return []


# ---------------------------------------------------------------------------
# Trevos (+Milionária)
# ---------------------------------------------------------------------------

def estatisticas_trevos_from_rows(sorteios_desc: Sequence[Any]) -> List[Dict[str, Any]]:
    total = len(sorteios_desc)
    ultimo = int(getattr(sorteios_desc[0], "concurso", 0) or 0) if sorteios_desc else 0
    freq = {t: 0 for t in range(1, 7)}
    visto = {t: 0 for t in range(1, 7)}
    for s in sorteios_desc:
        trevos: List[int] = []
        if hasattr(s, "trevos_lista"):
            try:
                trevos = [int(x) for x in (s.trevos_lista() or [])]
            except Exception:
                trevos = []
        if not trevos:
            for attr in ("t1", "t2"):
                v = getattr(s, attr, None)
                try:
                    vi = int(v or 0)
                except (TypeError, ValueError):
                    vi = 0
                if 1 <= vi <= 6:
                    trevos.append(vi)
        for t in trevos:
            if t not in freq:
                continue
            freq[t] += 1
            if visto[t] == 0:
                visto[t] = int(getattr(s, "concurso", 0) or 0)
    out: List[Dict[str, Any]] = []
    for t in range(1, 7):
        atraso = (ultimo - visto[t]) if visto[t] > 0 else total
        pct = round(freq[t] / total * 100, 1) if total else 0.0
        out.append({
            "trevo": t,
            "trevo_fmt": f"{t:02d}",
            "freq": freq[t],
            "atraso": atraso,
            "pct": pct,
        })
    return out


def _par_por_criterio(stats: Sequence[Dict[str, Any]], key: str) -> List[int]:
    top = _top_n(stats, key, "trevo", 2)
    par = sorted(int(t.get("trevo") or 0) for t in top if t.get("trevo"))
    if len(par) < 2:
        faltam = [x for x in range(1, 7) if x not in par]
        par = sorted((par + faltam)[:2])
    return par


def montar_opcoes_trevos(trevos_stats: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    stats = list(trevos_stats) if trevos_stats else [
        {"trevo": t, "trevo_fmt": f"{t:02d}", "freq": 0, "atraso": 0, "pct": 0.0}
        for t in range(1, 7)
    ]
    atrasado_par = _par_por_criterio(stats, "atraso")
    frequente_par = _par_por_criterio(stats, "freq")
    excluir = {_fmt_par(atrasado_par), _fmt_par(frequente_par)}
    atrasado = {"trevos": atrasado_par, "label": _fmt_par(atrasado_par)}
    frequente = {"trevos": frequente_par, "label": _fmt_par(frequente_par)}
    opcoes: List[Dict[str, Any]] = [
        {
            "value": "atrasado",
            "label": f"+ Atrasado ({atrasado['label']})",
            "trevos": atrasado_par,
            "criterio": "atrasado",
        },
        {
            "value": "frequente",
            "label": f"+ Frequente ({frequente['label']})",
            "trevos": frequente_par,
            "criterio": "frequente",
        },
    ]
    for par in _pares_trevos():
        key = _fmt_par(par)
        if key in excluir:
            continue
        opcoes.append({
            "value": key.replace(" ", "-"),
            "label": key,
            "trevos": list(par),
            "criterio": "fixo",
        })
    opcoes.append({
        "value": "aleatorio",
        "label": "+ Aleatório",
        "trevos": None,
        "criterio": "aleatorio",
    })
    return {
        "sucesso": True,
        "atrasado": atrasado,
        "frequente": frequente,
        "trevos": stats,
        "opcoes": opcoes,
        "default": "atrasado",
    }


def opcoes_trevos() -> Dict[str, Any]:
    from models.sorteio_maismilionaria import SorteioMaisMilionaria
    from models.shared import db
    from sqlalchemy import desc

    rows = db.session.query(SorteioMaisMilionaria).order_by(desc(SorteioMaisMilionaria.concurso)).all()
    return montar_opcoes_trevos(estatisticas_trevos_from_rows(rows))


def _parse_par_trevos(valor: ExtraValor) -> Optional[List[int]]:
    if valor is None or valor == "":
        return None
    raw = str(valor).strip().replace(",", " ").replace("-", " ")
    parts = [p for p in raw.split() if p]
    nums: List[int] = []
    for p in parts:
        if not p.isdigit():
            continue
        n = int(p)
        if 1 <= n <= 6 and n not in nums:
            nums.append(n)
        if len(nums) == 2:
            return sorted(nums)
    return None


def resolver_trevos_para_lote(
    valor: ExtraValor,
    quantidade: int,
    *,
    opcoes_payload: Optional[Dict[str, Any]] = None,
    rng: Optional[random.Random] = None,
) -> List[List[int]]:
    """Lista de pares [t1, t2] com `quantidade` apostas."""
    n = max(0, int(quantidade or 0))
    if n == 0:
        return []
    payload = opcoes_payload or {}
    pares = [list(p) for p in _pares_trevos()]
    raw = "" if valor is None else str(valor).strip()
    low = raw.lower()

    if low in ("aleatorio", "aleatório", "random"):
        escolhidos = _distribuir_bloco(pares, n, rng=rng)
        return [sorted(int(x) for x in par) for par in escolhidos]
    if low == "atrasado":
        par = list((payload.get("atrasado") or {}).get("trevos") or pares[0])
        return [sorted(int(x) for x in par)] * n
    if low == "frequente":
        par = list((payload.get("frequente") or {}).get("trevos") or pares[0])
        return [sorted(int(x) for x in par)] * n
    parsed = _parse_par_trevos(raw)
    if parsed:
        return [parsed] * n
    return []
