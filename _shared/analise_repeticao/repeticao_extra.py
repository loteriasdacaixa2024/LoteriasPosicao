# -*- coding: utf-8 -*-
"""Análise e geração de extras — mês, trevos, time."""
from __future__ import annotations

import random
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

MESES_NOMES = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}


def _mes_row(row: Any, cfg: dict) -> Tuple[int, str]:
    num = getattr(row, cfg.get("mes_field", "mes_num"), None) or 0
    try:
        num = int(num)
    except (TypeError, ValueError):
        num = 0
    nome = getattr(row, cfg.get("mes_label_field", "mes_nome"), None) or ""
    if num and not nome:
        nome = MESES_NOMES.get(num, "")
    return num, nome


def _time_row(row: Any) -> Tuple[int, str]:
    num = getattr(row, "time_num", None) or 0
    try:
        num = int(num)
    except (TypeError, ValueError):
        num = 0
    nome = getattr(row, "time_nome", None) or ""
    return num, nome


def _trevos_row(row: Any, cfg: dict) -> List[int]:
    method = cfg.get("trevo_list_method") or cfg.get("trevo_set_method")
    if not method:
        return []
    val = getattr(row, method)()
    return sorted(val) if not isinstance(val, list) else sorted(val)


def enrich_concurso_payload(row: Any, cfg: dict, payload: Dict[str, Any]) -> None:
    if cfg.get("extra_mes"):
        n, nome = _mes_row(row, cfg)
        payload["mes_num"] = n
        payload["mes_nome"] = nome
    if cfg.get("extra_time"):
        n, nome = _time_row(row)
        payload["time_num"] = n
        payload["time_nome"] = nome
    if cfg.get("extra_trevos"):
        payload["trevos"] = _trevos_row(row, cfg)


def _time_label(cfg: dict, num: int, time_names: Optional[Dict[int, str]] = None) -> str:
    if time_names and num in time_names:
        return time_names[num]
    return f"Time {num}"


def analisar_extra(
    cfg: dict,
    sorteios: List[Any],
    ult: Any,
    pen: Any,
    total_pares: int,
    time_names: Optional[Dict[int, str]] = None,
) -> Optional[Dict[str, Any]]:
    if cfg.get("extra_mes"):
        rep_pares = 0
        contagem = Counter()
        for i in range(1, len(sorteios)):
            ma, _ = _mes_row(sorteios[i - 1], cfg)
            mb, _ = _mes_row(sorteios[i], cfg)
            if ma and mb and ma == mb:
                rep_pares += 1
                contagem[ma] += 1
        pa, na = _mes_row(pen, cfg)
        ua, uan = _mes_row(ult, cfg)
        taxa = round(rep_pares / total_pares * 100, 2) if total_pares else 0
        return {
            "tipo": "mes",
            "titulo": "Mês da Sorte",
            "penultimo": {"num": pa, "nome": na},
            "ultimo": {"num": ua, "nome": uan},
            "repetiu_ultimo_par": bool(pa and ua and pa == ua),
            "pares_com_repeticao_historica": rep_pares,
            "taxa_repeticao_pct": taxa,
            "media_historica": round(rep_pares / total_pares, 2) if total_pares else 0,
            "ranking": [
                {"valor": m, "nome": MESES_NOMES.get(m, str(m)), "vezes": v}
                for m, v in contagem.most_common(5)
            ],
        }

    if cfg.get("extra_time"):
        rep_pares = 0
        contagem = Counter()
        for i in range(1, len(sorteios)):
            ta, _ = _time_row(sorteios[i - 1])
            tb, _ = _time_row(sorteios[i])
            if ta and tb and ta == tb:
                rep_pares += 1
                contagem[ta] += 1
        pa, na = _time_row(pen)
        ua, uan = _time_row(ult)
        taxa = round(rep_pares / total_pares * 100, 2) if total_pares else 0
        top = contagem.most_common(5)
        return {
            "tipo": "time",
            "titulo": "Time do Coração",
            "penultimo": {"num": pa, "nome": na},
            "ultimo": {"num": ua, "nome": uan},
            "repetiu_ultimo_par": bool(pa and ua and pa == ua),
            "pares_com_repeticao_historica": rep_pares,
            "taxa_repeticao_pct": taxa,
            "media_historica": round(rep_pares / total_pares, 2) if total_pares else 0,
            "ranking": [
                {"valor": t, "nome": _time_label(cfg, t, time_names), "vezes": v}
                for t, v in top
            ],
        }

    if cfg.get("extra_trevos"):
        qtd_rep: List[int] = []
        contagem = Counter()
        for i in range(1, len(sorteios)):
            sa = set(_trevos_row(sorteios[i - 1], cfg))
            sb = set(_trevos_row(sorteios[i], cfg))
            rep = sa & sb
            qtd_rep.append(len(rep))
            for t in rep:
                contagem[t] += 1
        ta = _trevos_row(pen, cfg)
        tb = _trevos_row(ult, cfg)
        rep_ult = sorted(set(ta) & set(tb))
        media = round(sum(qtd_rep) / len(qtd_rep), 2) if qtd_rep else 0
        return {
            "tipo": "trevos",
            "titulo": "Trevos",
            "penultimo": ta,
            "ultimo": tb,
            "repetidos_ultimo_par": rep_ult,
            "quantidade_ultimo_par": len(rep_ult),
            "pares_com_repeticao_historica": sum(1 for q in qtd_rep if q > 0),
            "media_trevos_repetidos_por_par": media,
            "ranking": [
                {"valor": t, "nome": str(t), "vezes": v}
                for t, v in contagem.most_common(6)
            ],
        }

    return None


def _pesos_escalar(
    vmin: int,
    vmax: int,
    ranking: List[Dict[str, Any]],
    ultimo_val: int,
    repetiu: bool,
    usar_ultimo_par: bool,
    perfil: str,
) -> List[Tuple[int, float]]:
    base = {i: 1.0 for i in range(vmin, vmax + 1)}
    for item in ranking:
        v = int(item.get("valor", 0))
        if vmin <= v <= vmax:
            base[v] += float(item.get("vezes", 0)) * 2.5
    if usar_ultimo_par and ultimo_val and vmin <= ultimo_val <= vmax:
        base[ultimo_val] += 35 if repetiu else 18
    pesos = list(base.items())
    if perfil == "agressivo":
        pesos = [(v, w + random.random() * 20) for v, w in pesos]
    elif perfil == "conservador":
        pesos = sorted(pesos, key=lambda x: -x[1])
    else:
        random.shuffle(pesos)
    return pesos


def _pick_um(pesos: List[Tuple[int, float]]) -> int:
    total = sum(w for _, w in pesos)
    r = random.random() * total
    acc = 0.0
    for v, w in pesos:
        acc += w
        if r <= acc:
            return v
    return pesos[-1][0]


def gerar_extra(
    cfg: dict,
    analise: Dict[str, Any],
    usar_ultimo_par: bool,
    perfil: str,
    time_names: Optional[Dict[int, str]] = None,
    aposta_idx: int = 0,
) -> Dict[str, Any]:
    extra_an = analise.get("extra") or {}
    out: Dict[str, Any] = {}

    if cfg.get("extra_mes"):
        if cfg.get("key") == "diadesorte":
            from diadesorte.meses_indicados import carregar_meses_indicados, extra_mes_ciclo
            from models.sorteio_diadesorte import SorteioDiaDeSorte

            analise_ms = carregar_meses_indicados(SorteioDiaDeSorte)
            ciclo = extra_mes_ciclo(analise_ms, aposta_idx)
            if ciclo:
                out.update(ciclo)
            return out

        ranking = extra_an.get("ranking") or []
        ult = extra_an.get("ultimo") or {}
        num = _pick_um(_pesos_escalar(
            1, 12, ranking,
            int(ult.get("num") or 0),
            bool(extra_an.get("repetiu_ultimo_par")),
            usar_ultimo_par, perfil,
        ))
        out["mes"] = num
        out["mes_nome"] = MESES_NOMES.get(num, str(num))

    if cfg.get("extra_time"):
        ranking = extra_an.get("ranking") or []
        ult = extra_an.get("ultimo") or {}
        tmax = int(cfg.get("time_max", 80))
        num = _pick_um(_pesos_escalar(
            1, tmax, ranking,
            int(ult.get("num") or 0),
            bool(extra_an.get("repetiu_ultimo_par")),
            usar_ultimo_par, perfil,
        ))
        out["time_num"] = num
        out["time_nome"] = _time_label(cfg, num, time_names)

    if cfg.get("extra_trevos"):
        pick = int(cfg.get("trevo_pick", 2))
        tmin = int(cfg.get("trevo_min", 1))
        tmax = int(cfg.get("trevo_max", 6))
        ranking = extra_an.get("ranking") or []
        rep_ult = set(extra_an.get("repetidos_ultimo_par") or [])
        pesos = {t: 1.0 for t in range(tmin, tmax + 1)}
        for item in ranking:
            t = int(item.get("valor", 0))
            if tmin <= t <= tmax:
                pesos[t] += float(item.get("vezes", 0)) * 3
        if usar_ultimo_par:
            for t in rep_ult:
                if tmin <= t <= tmax:
                    pesos[t] += 40
            for t in extra_an.get("ultimo") or []:
                if tmin <= t <= tmax:
                    pesos[t] += 15
        lista = list(pesos.items())
        if perfil == "agressivo":
            lista = [(t, w + random.random() * 15) for t, w in lista]
        random.shuffle(lista)
        escolhidos: List[int] = []
        pool = list(lista)
        while len(escolhidos) < pick and pool:
            total = sum(w for _, w in pool)
            r = random.random() * total
            acc = 0.0
            idx = len(pool) - 1
            for i, (t, w) in enumerate(pool):
                acc += w
                if r <= acc:
                    idx = i
                    break
            t, _ = pool.pop(idx)
            if t not in escolhidos:
                escolhidos.append(t)
        out["trevos"] = sorted(escolhidos)

    return out


def formatar_texto_aposta(cfg: dict, dezenas: List[int], extra: Dict[str, Any]) -> str:
    join = cfg.get("export_join", " ")
    pad = 2 if cfg.get("dezena_min", 1) >= 0 else 2
    base = join.join(f"{n:0{pad}d}" for n in dezenas)
    if cfg.get("extra_mes") and extra.get("mes"):
        abrev = extra.get("mes_abrev")
        if not abrev:
            from geradores_elite.comportamento.specs import MESES_ABREV
            abrev = MESES_ABREV.get(int(extra["mes"]), "")
        nome = abrev or extra.get("mes_nome") or str(extra["mes"])
        return f"{base} {nome}"
    if cfg.get("extra_time") and extra.get("time_num"):
        nome = extra.get("time_nome") or str(extra["time_num"])
        return f"{base} + {nome}"
    if cfg.get("extra_trevos") and extra.get("trevos"):
        tr = join.join(str(t) for t in extra["trevos"])
        return f"{base} {tr}"
    return base


def explicacao_extra(cfg: dict, extra: Dict[str, Any]) -> str:
    if cfg.get("extra_mes") and extra.get("mes"):
        return extra.get("mes_nome") or str(extra["mes"])
    if cfg.get("extra_time") and extra.get("time_num"):
        return extra.get("time_nome") or str(extra["time_num"])
    if cfg.get("extra_trevos") and extra.get("trevos"):
        return " ".join(str(t) for t in extra["trevos"])
    return ""
