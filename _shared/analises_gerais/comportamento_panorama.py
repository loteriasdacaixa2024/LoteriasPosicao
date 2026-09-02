# -*- coding: utf-8 -*-
"""Panorama comportamental das 9 modalidades — leitura direta do SQLite na Central."""
from __future__ import annotations

import importlib.util
import os
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from _shared.analises_gerais.comportamento_loader import SorteioComportamento, carregar_registros
from _shared.analises_gerais.registry import SPECS, SPECS_BY_KEY

if TYPE_CHECKING:
    from _shared.geradores_elite.comportamento.specs import ComportamentoSpec


def _contar_sequencias(dezenas: List[int]) -> int:
    ordenadas = sorted(dezenas)
    grupos = 0
    i = 0
    while i < len(ordenadas):
        j = i
        while j + 1 < len(ordenadas) and ordenadas[j + 1] - ordenadas[j] == 1:
            j += 1
        if j > i:
            grupos += 1
        i = j + 1
    return grupos


def _contar_seq_adjacentes(digitos: List[int]) -> int:
    grupos = 0
    i = 0
    while i < len(digitos) - 1:
        if abs(digitos[i + 1] - digitos[i]) == 1:
            j = i
            while j + 1 < len(digitos) and abs(digitos[j + 1] - digitos[j]) == 1:
                j += 1
            grupos += 1
            i = j + 1
        else:
            i += 1
    return grupos


def _load_comportamento_specs_module():
    import sys

    path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "geradores_elite", "comportamento", "specs.py")
    )
    spec = importlib.util.spec_from_file_location("comportamento_specs_central", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


_COMP_MOD = _load_comportamento_specs_module()
COMP_SPECS = _COMP_MOD.SPECS
COMPORTAMENTO_TITLES = _COMP_MOD.COMPORTAMENTO_TITLES
MESES_NOME = _COMP_MOD.MESES_NOME
MESES_ABREV = _COMP_MOD.MESES_ABREV
ComportamentoSpec = _COMP_MOD.ComportamentoSpec

# Cores oficiais de cada app (base.html de cada modalidade)
MODALITY_THEMES: Dict[str, Dict[str, str]] = {
    "lotofacil": {"primary": "#672666", "dark": "#2d0a2d", "text": "#ffffff"},
    "diadesorte": {"primary": "#c08b00", "dark": "#664a00", "text": "#ffffff"},
    "lotomania": {"primary": "#c45c00", "dark": "#6e3200", "text": "#ffffff"},
    "quina": {"primary": "#6a0dad", "dark": "#350666", "text": "#ffffff"},
    "megasena": {"primary": "#0a6b1a", "dark": "#04350a", "text": "#ffffff"},
    "maismilionaria": {"primary": "#8b6914", "dark": "#4a3508", "text": "#ffffff"},
    "duplasena": {"primary": "#8b0000", "dark": "#450000", "text": "#ffffff"},
    "timemania": {"primary": "#8b3a00", "dark": "#441a00", "text": "#ffffff"},
    "supersete": {"primary": "#708e25", "dark": "#303d10", "text": "#ffffff"},
}


def _build_comparativo_pa_im(cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for m in cards:
        if m.get("erro"):
            continue
        res = m.get("resumo") or {}
        ult = m.get("ultimo_indicadores") or {}
        linhas = list(reversed(m.get("linhas") or []))
        pa_r = res.get("PA") or {}
        im_r = res.get("IM") or {}
        sorteadas = len(linhas[0]["dezenas"]) if linhas else 0
        rows.append({
            "key": m["key"],
            "nome": m["nome"],
            "titulo": m.get("titulo") or m["nome"],
            "theme": m.get("theme") or MODALITY_THEMES.get(m["key"], {}),
            "sorteadas": sorteadas,
            "pa_moda": pa_r.get("moda"),
            "pa_moda_pct": pa_r.get("moda_pct"),
            "pa_media": pa_r.get("media"),
            "pa_ultimo": ult.get("PA"),
            "im_moda": im_r.get("moda"),
            "im_moda_pct": im_r.get("moda_pct"),
            "im_media": im_r.get("media"),
            "im_ultimo": ult.get("IM"),
            "par_impar_moda": f"{pa_r.get('moda', '—')} / {im_r.get('moda', '—')}",
            "ultimos_pa": [l.get("PA") for l in linhas],
            "ultimos_im": [l.get("IM") for l in linhas],
        })
    return rows


def _extras_from_registro(sp: ComportamentoSpec, rec: SorteioComportamento) -> Dict[str, int]:
    out: Dict[str, int] = {}
    if sp.has_mes and rec.mes_num:
        out["MS"] = rec.mes_num
    if sp.has_time and rec.time_num:
        out["TM"] = rec.time_num
    if sp.has_trevos and rec.trevos and len(rec.trevos) >= 2:
        out["T1"], out["T2"] = rec.trevos[0], rec.trevos[1]
    return out


def _calcular_indicadores(
    sp: ComportamentoSpec,
    dezenas: List[int],
    prev_dezenas: Optional[List[int]] = None,
    extras: Optional[Dict[str, int]] = None,
) -> Dict[str, int]:
    if sp.modality_key == "supersete":
        pa = sum(1 for d in dezenas if d % 2 == 0)
        im = len(dezenas) - pa
        pr = sum(1 for d in dezenas if d in sp.primos)
        rp = 0
        if prev_dezenas and len(prev_dezenas) == len(dezenas):
            rp = sum(1 for a, b in zip(dezenas, prev_dezenas) if a == b)
        ex = sum(1 for d in dezenas if d in sp.moldura)
        sq = _contar_seq_adjacentes(dezenas)
        out = {"PA": pa, "IM": im, "PR": pr, "RP": rp, "EX": ex, "SQ": sq}
    else:
        pa = sum(1 for d in dezenas if d % 2 == 0)
        im = len(dezenas) - pa
        pr = sum(1 for d in dezenas if d in sp.primos)
        rt = len(set(dezenas) & set(prev_dezenas)) if prev_dezenas else 0
        mo = sum(1 for d in dezenas if d in sp.moldura)
        sq = _contar_sequencias(dezenas)
        m3 = sum(1 for d in dezenas if d in sp.multiplos_3)
        fb = sum(1 for d in dezenas if d in sp.fibonacci)
        out = {"PA": pa, "IM": im, "PR": pr, "RT": rt, "MO": mo, "SQ": sq, "M3": m3, "FB": fb}

    if extras:
        for k, v in extras.items():
            if k in sp.indicadores:
                out[k] = int(v)
    for cod in sp.indicadores:
        out.setdefault(cod, 0)
    return out


def _resumo_indicadores(sp: ComportamentoSpec, linhas: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(linhas)
    resumo: Dict[str, Any] = {}
    for cod in sp.indicadores:
        vals = [row[cod] for row in linhas if cod in row]
        if not vals:
            resumo[cod] = {"moda": 0, "moda_pct": 0, "media": 0, "ultimo": 0}
            continue
        cnt = Counter(vals)
        moda, moda_freq = cnt.most_common(1)[0]
        resumo[cod] = {
            "moda": moda,
            "moda_pct": round(moda_freq / total * 100, 1) if total else 0,
            "media": round(sum(vals) / len(vals), 2),
            "ultimo": linhas[-1].get(cod, 0) if linhas else 0,
        }
    return resumo


def _resumo_executivo(sp: ComportamentoSpec, resumo: Dict[str, Any], ultimo_ind: Dict[str, int]) -> str:
    destaques = []
    for cod in sp.indicadores_dezena[:4]:
        r = resumo.get(cod, {})
        moda = r.get("moda", 0)
        pct = r.get("moda_pct", 0)
        if pct >= 15:
            destaques.append(f"{cod} moda {moda} ({pct}%)")
    ult_txt = " · ".join(f"{c} {ultimo_ind.get(c, 0)}" for c in sp.indicadores_dezena[:5])
    partes = []
    if ult_txt:
        partes.append(f"Último: {ult_txt}")
    if destaques:
        partes.append("Destaques: " + ", ".join(destaques[:3]))
    return " — ".join(partes) if partes else "Sem dados suficientes."


def analisar_registros(
    sp: ComportamentoSpec,
    registros: List[SorteioComportamento],
    janela: int = 10,
) -> Dict[str, Any]:
    if janela not in sp.janelas_validas:
        janela = sp.janela_default

    if not registros:
        return {"sucesso": False, "erro": "Nenhum sorteio no banco."}

    base = registros if janela == 0 else registros[-janela:]
    linhas: List[Dict[str, Any]] = []
    for i, rec in enumerate(base):
        prev = base[i - 1].dezenas if i > 0 else None
        ex = _extras_from_registro(sp, rec)
        ind = _calcular_indicadores(sp, rec.dezenas, prev, ex or None)
        row: Dict[str, Any] = {
            "concurso": rec.concurso,
            "data": rec.data,
            "dezenas": rec.dezenas,
            **ind,
        }
        if sp.has_mes and "MS" in ex:
            row["mes_num"] = ex["MS"]
            row["mes_nome"] = rec.mes_nome or MESES_NOME.get(ex["MS"], "")
            row["mes_abrev"] = MESES_ABREV.get(ex["MS"], "")
        if sp.has_time and "TM" in ex:
            row["time_num"] = ex["TM"]
            row["time_nome"] = rec.time_nome or ""
        if sp.has_trevos and "T1" in ex:
            row["trevos"] = [ex["T1"], ex["T2"]]
        linhas.append(row)

    resumo = _resumo_indicadores(sp, linhas)
    ultimo = registros[-1]
    ultimo_prev = registros[-2].dezenas if len(registros) > 1 else None
    ultimo_ex = _extras_from_registro(sp, ultimo)
    ultimo_ind = _calcular_indicadores(sp, ultimo.dezenas, ultimo_prev, ultimo_ex or None)

    return {
        "sucesso": True,
        "janela": janela,
        "total_concursos": len(registros),
        "ultimo_concurso": ultimo.concurso,
        "linhas": list(reversed(linhas)),
        "resumo": resumo,
        "ultimo_indicadores": ultimo_ind,
        "resumo_executivo": _resumo_executivo(sp, resumo, ultimo_ind),
        "indicadores": [
            {"codigo": c, "label": sp.indicador_labels[c]} for c in sp.indicadores
        ],
    }


class ComportamentoCentralService:
    JANELA_PADRAO = 10

    @classmethod
    def panorama(cls, janela: int = 10) -> Dict[str, Any]:
        cards: List[Dict[str, Any]] = []
        avisos: List[str] = []

        for spec in SPECS:
            comp_sp = COMP_SPECS.get(spec.key)
            if not comp_sp:
                continue

            registros, msg = carregar_registros(spec)
            titulo = COMPORTAMENTO_TITLES.get(spec.key, spec.nome)
            link = f"http://localhost:{spec.porta}/geradores-elite/comportamento-apostas/"

            if msg != "ok" and not registros:
                cards.append({
                    "key": spec.key,
                    "nome": spec.nome,
                    "titulo": titulo,
                    "porta": spec.porta,
                    "erro": msg,
                    "link_comportamento": link,
                })
                avisos.append(f"{spec.nome}: {msg}")
                continue

            analise = analisar_registros(comp_sp, registros, janela=janela)
            if not analise.get("sucesso"):
                cards.append({
                    "key": spec.key,
                    "nome": spec.nome,
                    "titulo": titulo,
                    "porta": spec.porta,
                    "erro": analise.get("erro", "Erro na análise"),
                    "link_comportamento": link,
                })
                continue

            cards.append({
                "key": spec.key,
                "nome": spec.nome,
                "titulo": titulo,
                "porta": spec.porta,
                "grupo": spec.grupo,
                "theme": MODALITY_THEMES.get(spec.key, {}),
                "janela": analise["janela"],
                "total_concursos": analise["total_concursos"],
                "ultimo_concurso": analise["ultimo_concurso"],
                "resumo_executivo": analise["resumo_executivo"],
                "resumo": analise["resumo"],
                "ultimo_indicadores": analise["ultimo_indicadores"],
                "linhas": analise["linhas"],
                "indicadores": analise["indicadores"],
                "link_comportamento": link,
            })

        return {
            "atualizado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "janela": janela,
            "modalidades": cards,
            "comparativo_pa_im": _build_comparativo_pa_im(cards),
            "avisos": avisos,
        }

    @classmethod
    def panorama_modalidade(cls, key: str, janela: int = 10) -> Dict[str, Any]:
        spec = SPECS_BY_KEY.get(key)
        comp_sp = COMP_SPECS.get(key)
        if not spec or not comp_sp:
            raise KeyError(key)
        registros, msg = carregar_registros(spec)
        if msg != "ok" and not registros:
            return {"sucesso": False, "erro": msg, "key": key}
        analise = analisar_registros(comp_sp, registros, janela=janela)
        analise["key"] = key
        analise["nome"] = spec.nome
        analise["link_comportamento"] = (
            f"http://localhost:{spec.porta}/geradores-elite/comportamento-apostas/"
        )
        return analise
