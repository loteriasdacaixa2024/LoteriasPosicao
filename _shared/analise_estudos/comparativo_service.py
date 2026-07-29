# -*- coding: utf-8 -*-
"""Comparativo vencedores × acumulados — Análises Gerais."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from analise_estudos.registry import get_aba
from analise_estudos.service_factory import make_estudos_base
from analise_estudos.specs import get_estudos_config


def _delta_num(v: Any, a: Any) -> Optional[float]:
    try:
        return round(float(v) - float(a), 2)
    except (TypeError, ValueError):
        return None


def _fmt_delta(d: Optional[float], sufixo: str = "") -> str:
    if d is None:
        return "—"
    sinal = "+" if d > 0 else ""
    return f"{sinal}{d}{sufixo}"


def _linhas_classificacao(v: Dict[str, Any], a: Dict[str, Any]) -> List[Dict[str, Any]]:
    inds = [i["codigo"] for i in (v.get("indicadores") or a.get("indicadores") or [])]
    labels = {
        i["codigo"]: i.get("label", i["codigo"])
        for i in (v.get("indicadores") or a.get("indicadores") or [])
    }
    rv = v.get("resumo") or {}
    ra = a.get("resumo") or {}
    out: List[Dict[str, Any]] = []
    for cod in inds:
        mv = rv.get(cod, {}).get("moda")
        ma = ra.get(cod, {}).get("moda")
        med_v = rv.get(cod, {}).get("media")
        med_a = ra.get(cod, {}).get("media")
        d = _delta_num(med_v, med_a)
        out.append({
            "codigo": cod,
            "label": f"{cod} — moda V:{mv} A:{ma}",
            "vencedores": f"moda {mv} ({rv.get(cod, {}).get('moda_pct', 0)}%) · média {med_v}",
            "acumulados": f"moda {ma} ({ra.get(cod, {}).get('moda_pct', 0)}%) · média {med_a}",
            "delta": _fmt_delta(d),
            "delta_num": d,
        })
    return out


def _linhas_digitos(v: Dict[str, Any], a: Dict[str, Any]) -> List[Dict[str, Any]]:
    pv = {p["digito"]: p for p in (v.get("painel_digitos") or [])}
    pa = {p["digito"]: p for p in (a.get("painel_digitos") or [])}
    out: List[Dict[str, Any]] = []
    for dig in [str(i) for i in range(10)]:
        pct_v = pv.get(dig, {}).get("pct_concursos", 0)
        pct_a = pa.get(dig, {}).get("pct_concursos", 0)
        d = _delta_num(pct_v, pct_a)
        out.append({
            "codigo": dig,
            "label": f"Dígito {dig} — % concursos",
            "vencedores": f"{pct_v}%",
            "acumulados": f"{pct_a}%",
            "delta": _fmt_delta(d, " pp"),
            "delta_num": d,
        })
    media_v = v.get("kpis", [{}])[1].get("valor") if len(v.get("kpis", [])) > 1 else None
    media_a = a.get("kpis", [{}])[1].get("valor") if len(a.get("kpis", [])) > 1 else None
    d_med = _delta_num(media_v, media_a)
    out.insert(0, {
        "codigo": "media_qtd",
        "label": "Média dígitos distintos",
        "vencedores": str(media_v),
        "acumulados": str(media_a),
        "delta": _fmt_delta(d_med),
        "delta_num": d_med,
    })
    sobre_v = (v.get("sobreposicao_consecutiva") or {}).get("media")
    sobre_a = (a.get("sobreposicao_consecutiva") or {}).get("media")
    d_sobre = _delta_num(sobre_v, sobre_a)
    out.append({
        "codigo": "sobreposicao",
        "label": "Sobreposição consecutiva (média)",
        "vencedores": str(sobre_v),
        "acumulados": str(sobre_a),
        "delta": _fmt_delta(d_sobre),
        "delta_num": d_sobre,
    })
    return out


def _linhas_soma(v: Dict[str, Any], a: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for i, label in enumerate(["Concursos", "Moda soma dígitos", "Média soma dígitos", "Min / Max"]):
        kv = (v.get("kpis") or [{}] * 4)[i].get("valor") if i < len(v.get("kpis") or []) else "—"
        ka = (a.get("kpis") or [{}] * 4)[i].get("valor") if i < len(a.get("kpis") or []) else "—"
        d = _delta_num(kv, ka) if label == "Média soma dígitos" else None
        out.append({
            "codigo": label.lower().replace(" ", "_"),
            "label": label,
            "vencedores": str(kv),
            "acumulados": str(ka),
            "delta": _fmt_delta(d) if d is not None else "—",
            "delta_num": d,
        })

    dv = {d["valor"]: d["pct"] for d in (v.get("distribuicao_soma_total") or [])}
    da = {d["valor"]: d["pct"] for d in (a.get("distribuicao_soma_total") or [])}
    todos = sorted(set(dv) | set(da), key=lambda x: int(x))
    for val in todos[:8]:
        pct_v = dv.get(val, 0)
        pct_a = da.get(val, 0)
        d = _delta_num(pct_v, pct_a)
        out.append({
            "codigo": f"soma_{val}",
            "label": f"Soma total {val} — %",
            "vencedores": f"{pct_v}%",
            "acumulados": f"{pct_a}%",
            "delta": _fmt_delta(d, " pp"),
            "delta_num": d,
        })
    return out


_BUILDERS = {
    "classificacao-numeros": _linhas_classificacao,
    "digitos-utilizados": _linhas_digitos,
    "soma-digitos": _linhas_soma,
    "diferencial-cruzado": lambda v, a: [],
}


def analisar_comparativo(
    modality_key: str,
    aba_id: str,
    janela: int = 10,
) -> Dict[str, Any]:
    spec = get_aba(aba_id)
    Base = make_estudos_base(modality_key)
    janela = Base._normalizar_janela(janela)
    cfg = get_estudos_config(modality_key)

    v = spec.service_cls.analisar(modality_key, janela=janela, base_estatistica="vencedores")
    a = spec.service_cls.analisar(modality_key, janela=janela, base_estatistica="acumulados")

    if not v.get("sucesso"):
        return v
    if not a.get("sucesso"):
        return a

    builder = _BUILDERS.get(aba_id)
    linhas = builder(v, a) if builder else []

    return {
        "sucesso": True,
        "comparativo": True,
        "aba_id": aba_id,
        "aba_titulo": spec.titulo,
        "modality_key": modality_key,
        "modality_nome": cfg["nome"],
        "janela": janela,
        "janela_label": "Todos" if janela == 0 else f"Últimos {janela}",
        "total_vencedores": v.get("total_concursos", 0),
        "total_acumulados": a.get("total_concursos", 0),
        "vencedores": v,
        "acumulados": a,
        "linhas_comparativo": linhas,
        "kpis": [
            {"label": "Vencedores", "valor": v.get("total_concursos", 0)},
            {"label": "Acumulados", "valor": a.get("total_concursos", 0)},
            {
                "label": "Maior Δ (abs.)",
                "valor": max(
                    (abs(x["delta_num"]) for x in linhas if x.get("delta_num") is not None),
                    default=0,
                ),
            },
            {"label": "Indicadores", "valor": len(linhas)},
        ],
    }
