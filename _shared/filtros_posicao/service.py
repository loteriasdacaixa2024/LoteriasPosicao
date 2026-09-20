# -*- coding: utf-8 -*-
"""Min/máx e frequência por posição — Excel (crescente) e banco (ordem de sorteio)."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import importlib.util
import sys
from pathlib import Path

from caixa_excel.config import resolve_excel_path
from caixa_excel.parse_modalidades import parse_planilha
from caixa_excel.xlsx_reader import ler_xlsx_dicts


def _load_posicao_specs():
    path = Path(__file__).resolve().parent.parent / "posicao_analise" / "specs.py"
    spec = importlib.util.spec_from_file_location("_fp_posicao_specs", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


_POS_SPECS = _load_posicao_specs()
get_posicao_spec = _POS_SPECS.get_posicao_spec

_EXCEL_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}


def _fmt(spec, valor: int) -> str:
    return spec.fmt(int(valor))


def _pct(n: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(100.0 * n / total, 2)


def _bolas_excel(key: str, rec: Dict[str, Any], sorteio: int = 1) -> List[int]:
    extras = rec.get("extras") or {}
    if key == "duplasena":
        campo = "bolas_excel_s2" if int(sorteio) == 2 else "bolas_excel_s1"
        raw = extras.get(campo) or rec.get("bolas_excel") or []
    elif key == "supersete":
        raw = extras.get("colunas_excel") or rec.get("bolas_excel") or []
    else:
        raw = rec.get("bolas_excel") or rec.get("bolas") or []
    out: List[int] = []
    for v in raw:
        if v is None or v == "":
            continue
        try:
            out.append(int(v))
        except (TypeError, ValueError):
            continue
    return out


def _extra_excel(key: str, rec: Dict[str, Any]) -> Dict[str, Any]:
    extras = rec.get("extras") or {}
    out: Dict[str, Any] = {}
    if key == "diadesorte":
        mes = str(extras.get("mes_sorte") or "").strip()
        if mes:
            out["mes"] = mes
    if key == "timemania":
        time = str(extras.get("time_coracao") or "").strip()
        if time:
            out["time"] = time
    if key == "maismilionaria":
        t1, t2 = extras.get("trevo1"), extras.get("trevo2")
        trevos = [int(t) for t in (t1, t2) if t is not None]
        if trevos:
            out["trevos"] = trevos
    return out


def carregar_excel(key: str, sorteio: int = 1) -> Dict[str, Any]:
    path = resolve_excel_path(key)
    if not path.is_file():
        return {
            "ok": False,
            "arquivo": str(path),
            "erro": f"Excel não encontrado: {path.name}",
            "concursos": [],
        }
    mtime = path.stat().st_mtime
    cache_key = f"{key}:{int(sorteio)}"
    hit = _EXCEL_CACHE.get(cache_key)
    if hit and hit[0] == mtime:
        return hit[1]

    rows = ler_xlsx_dicts(path)
    parsed = parse_planilha(key, rows)
    concursos: List[Dict[str, Any]] = []
    ordenados = 0
    for rec in parsed:
        bolas = _bolas_excel(key, rec, sorteio=sorteio)
        if not bolas:
            continue
        if bolas == sorted(bolas):
            ordenados += 1
        concursos.append({
            "concurso": int(rec["concurso"]),
            "data": rec.get("data") or "",
            "bolas": bolas,
            "extra": _extra_excel(key, rec),
        })
    concursos.sort(key=lambda r: r["concurso"])
    payload = {
        "ok": True,
        "arquivo": str(path),
        "filename": path.name,
        "mtime": mtime,
        "excel_ja_ordenado": bool(concursos) and ordenados >= max(1, int(0.9 * len(concursos))),
        "concursos": concursos,
    }
    _EXCEL_CACHE[cache_key] = (mtime, payload)
    return payload


def carregar_banco(key: str, sorteio: int = 1) -> Dict[str, Any]:
    try:
        from posicao_analise.service import _extrair_ordem, _extras_concurso, _load_model
        from models.shared import db
    except Exception as exc:
        return {"ok": False, "erro": f"Banco indisponível: {exc}", "concursos": []}

    spec = get_posicao_spec(key)
    try:
        Model = _load_model(spec)
        rows = db.session.query(Model).order_by(Model.concurso).all()
    except Exception as exc:
        return {"ok": False, "erro": f"Falha ao ler sorteios: {exc}", "concursos": []}

    concursos: List[Dict[str, Any]] = []
    for row in rows:
        ordem = _extrair_ordem(row, spec, sorteio=sorteio)
        if len(ordem) < spec.num_posicoes:
            continue
        extra = _extras_concurso(row, spec)
        concursos.append({
            "concurso": int(row.concurso),
            "data": getattr(row, "data", "") or "",
            "bolas": [int(x) for x in ordem[: spec.num_posicoes]],
            "extra": extra,
        })
    return {
        "ok": True,
        "concursos": concursos,
        "fonte": "banco",
    }


def _rank_freq(counter: Counter, total: int, spec) -> List[Dict[str, Any]]:
    ranked = []
    for valor, freq in counter.most_common():
        ranked.append({
            "valor": int(valor),
            "label": _fmt(spec, valor),
            "freq": int(freq),
            "pct": _pct(int(freq), total),
        })
    return ranked


def _rotulo_posicao(idx: int, spec) -> str:
    return f"{idx}ª {spec.pos_label.lower()}"


def _montar_matriz(posicoes: List[Dict[str, Any]], spec) -> Dict[str, Any]:
    """Matriz completa: todas as dezenas do universo × todas as posições (zeros inclusos)."""
    n = spec.num_posicoes
    colunas = []
    for i in range(n):
        colunas.append({
            "pos": i + 1,
            "label": _rotulo_posicao(i + 1, spec),
            "label_curto": (
                posicoes[i].get("label")
                if i < len(posicoes)
                else f"{spec.pos_prefix}{i + 1}"
            ),
        })

    freq_maps = []
    for p in posicoes:
        freq_maps.append({
            int(x["valor"]): int(x["freq"])
            for x in (p.get("frequencias") or [])
        })

    linhas = []
    for dez in range(spec.valor_min, spec.valor_max + 1):
        contagens = [m.get(dez, 0) for m in freq_maps]
        linhas.append({
            "dezena": dez,
            "label": _fmt(spec, dez),
            "contagens": contagens,
            "total": sum(contagens),
        })

    return {
        "colunas": colunas,
        "linhas": linhas,
        "valor_min": spec.valor_min,
        "valor_max": spec.valor_max,
        "num_posicoes": n,
    }


def _analisar_posicoes(concursos: List[Dict[str, Any]], spec, *, ordenar: bool) -> List[Dict[str, Any]]:
    n = spec.num_posicoes
    counters = [Counter() for _ in range(n)]
    usados = 0
    for rec in concursos:
        bolas = list(rec.get("bolas") or [])
        if len(bolas) < n:
            continue
        if ordenar:
            bolas = sorted(bolas[:n])
        else:
            bolas = bolas[:n]
        for i, v in enumerate(bolas):
            counters[i][int(v)] += 1
        usados += 1

    posicoes = []
    for i in range(n):
        c = counters[i]
        if not c:
            posicoes.append({
                "pos": i + 1,
                "label": f"{spec.pos_prefix}{i + 1}",
                "min": None,
                "max": None,
                "n": 0,
                "campeao": None,
                "top3": [],
                "raros": [],
                "frequencias": [],
                "sugestao": [],
            })
            continue
        valores = sorted(c)
        ranked = _rank_freq(c, usados, spec)
        campeao = ranked[0]
        media = usados / max(1, len(valores))
        sugestao = [r["valor"] for r in ranked if r["freq"] >= media][:5]
        if campeao["valor"] not in sugestao:
            sugestao.insert(0, campeao["valor"])
        raros = [r for r in ranked if r["freq"] <= 3][-6:]
        posicoes.append({
            "pos": i + 1,
            "label": f"{spec.pos_prefix}{i + 1}",
            "min": valores[0],
            "min_fmt": _fmt(spec, valores[0]),
            "max": valores[-1],
            "max_fmt": _fmt(spec, valores[-1]),
            "n": usados,
            "campeao": campeao,
            "top3": ranked[:3],
            "raros": raros,
            "frequencias": ranked,
            "sugestao": sugestao[:4],
            "sugestao_fmt": [_fmt(spec, v) for v in sugestao[:4]],
            "qtd_distintos": len(valores),
        })
    return posicoes


def _montar_aposta(posicoes: List[Dict[str, Any]], spec) -> Dict[str, Any]:
    escolhidas: List[int] = []
    detalhe = []
    for p in posicoes:
        candidatos = [x["valor"] for x in (p.get("top3") or [])]
        if not candidatos:
            continue
        if spec.distinct_across_positions:
            pick = next((v for v in candidatos if v not in escolhidas), None)
        else:
            pick = candidatos[0]
        if pick is None:
            continue
        escolhidas.append(pick)
        detalhe.append({
            "pos": p["label"],
            "valor": pick,
            "label": _fmt(spec, pick),
            "freq": next((x["freq"] for x in p["top3"] if x["valor"] == pick), 0),
        })
    return {
        "dezenas": escolhidas,
        "dezenas_fmt": [_fmt(spec, v) for v in escolhidas],
        "detalhe": detalhe,
        "completa": len(escolhidas) == spec.num_posicoes,
    }


def _insights(key: str, modo: str, posicoes: List[Dict[str, Any]], spec, excel_info: Dict[str, Any]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    if not posicoes:
        return out

    if modo == "crescente" and key != "supersete" and excel_info.get("excel_ja_ordenado"):
        out.append({
            "tipo": "info",
            "titulo": "Excel = ordem crescente (filtro)",
            "texto": (
                "As colunas Bola1…BolaN do Excel da CAIXA já vêm ordenadas. "
                "O min/máx de cada posição é o filtro real da planilha — não a ordem em que a bola saiu do globo."
            ),
        })

    if modo == "sorteio":
        out.append({
            "tipo": "info",
            "titulo": "Ordem de sorteio (globo)",
            "texto": (
                "Esta visão usa a ordem gravada no banco (API da CAIXA: dezenasSorteadasOrdemSorteio). "
                "Qualquer dezena pode aparecer em qualquer posição."
            ),
        })

    if key == "lotofacil" and modo == "crescente":
        ultima = posicoes[-1] if posicoes else None
        camp = (ultima or {}).get("campeao") or {}
        out.append({
            "tipo": "alerta",
            "titulo": "Lotofácil: 15 posições, 25 dezenas",
            "texto": (
                "Não existe posição 25 — o 25 é uma dezena. Na ordem crescente a última posição (P15) "
                "concentra os maiores números. "
                + (
                    f"Hoje o campeão da P15 é o {camp.get('label', '25')} "
                    f"({camp.get('freq', 0)} vezes, {camp.get('pct', 0)}%). "
                    "Uma dezena como 18 aparecer 1 vez aqui é raro e esperado: 18 quase nunca é a maior bola do concurso."
                    if camp else
                    "Uma dezena baixa (ex.: 18) quase nunca é a maior bola do concurso."
                )
            ),
        })

    if key == "supersete":
        out.append({
            "tipo": "info",
            "titulo": "Super Sete: colunas, não ordem crescente",
            "texto": "Cada posição já é uma coluna (0–9). Crescente e sorteio coincidem — não se ordena o volante.",
        })

    fortes = []
    for p in posicoes:
        camp = p.get("campeao")
        if camp and camp.get("pct", 0) >= 18:
            fortes.append(f"{p['label']}→{camp['label']} ({camp['pct']}%)")
    if fortes:
        out.append({
            "tipo": "aposta",
            "titulo": "Posições mais concentradas — priorize estes números",
            "texto": " · ".join(fortes),
        })

    for p in posicoes:
        camp = p.get("campeao")
        if not camp:
            continue
        top = p.get("top3") or []
        nomes = ", ".join(f"{t['label']} ({t['freq']}×)" for t in top)
        out.append({
            "tipo": "posicao",
            "titulo": f"{p['label']}: mais saiu {camp['label']}",
            "texto": (
                f"Filtro {p.get('min_fmt')}–{p.get('max_fmt')}. "
                f"Campeão: {camp['label']} saiu {camp['freq']} vezes ({camp['pct']}%). "
                f"Top 3: {nomes}."
            ),
        })
    return out


def _extras_freq(concursos: List[Dict[str, Any]], spec) -> Optional[Dict[str, Any]]:
    if spec.extra_mes:
        c = Counter()
        for rec in concursos:
            extra = rec.get("extra") or {}
            mes = extra.get("mes") or extra.get("mes_nome") or extra.get("mes_num")
            if mes not in (None, "", 0):
                c[str(mes)] += 1
        if c:
            ranked = [{"valor": k, "label": k, "freq": v, "pct": _pct(v, sum(c.values()))} for k, v in c.most_common()]
            return {"titulo": "Mês da Sorte", "itens": ranked}
    if spec.extra_time:
        c = Counter()
        for rec in concursos:
            extra = rec.get("extra") or {}
            time = extra.get("time") or extra.get("time_nome")
            if time:
                c[str(time)] += 1
        if c:
            ranked = [{"valor": k, "label": k, "freq": v, "pct": _pct(v, sum(c.values()))} for k, v in c.most_common(12)]
            return {"titulo": "Time do Coração", "itens": ranked}
    if spec.extra_trevo:
        c = Counter()
        for rec in concursos:
            extra = rec.get("extra") or {}
            for t in extra.get("trevos") or []:
                c[int(t)] += 1
        if c:
            ranked = [
                {"valor": k, "label": _fmt(spec, k), "freq": v, "pct": _pct(v, sum(c.values()))}
                for k, v in c.most_common()
            ]
            return {"titulo": "Trevos", "itens": ranked}
    return None


def analisar(key: str, modo: str = "crescente", sorteio: int = 1) -> Dict[str, Any]:
    spec = get_posicao_spec(key)
    modo = (modo or "crescente").strip().lower()
    if modo not in ("crescente", "sorteio"):
        modo = "crescente"
    if key == "supersete":
        modo = "sorteio" if modo == "sorteio" else "crescente"

    excel = carregar_excel(key, sorteio=sorteio)
    banco = carregar_banco(key, sorteio=sorteio)

    if modo == "sorteio":
        fonte = banco if banco.get("ok") and banco.get("concursos") else None
        origem = "banco"
        if fonte is None:
            return {
                "sucesso": False,
                "erro": banco.get("erro") or "Banco sem concursos para ordem de sorteio. Sincronize os dados.",
                "modalidade": spec.to_ui(),
                "modo": modo,
            }
        concursos = fonte["concursos"]
        ordenar = False
    else:
        if not excel.get("ok"):
            return {
                "sucesso": False,
                "erro": excel.get("erro") or "Excel não encontrado.",
                "modalidade": spec.to_ui(),
                "modo": modo,
            }
        concursos = excel["concursos"]
        ordenar = key != "supersete"
        origem = "excel"

    posicoes = _analisar_posicoes(concursos, spec, ordenar=ordenar)
    aposta = _montar_aposta(posicoes, spec)
    primeiro = concursos[0] if concursos else None
    ultimo = concursos[-1] if concursos else None

    return {
        "sucesso": True,
        "modalidade": spec.to_ui(),
        "modo": modo,
        "sorteio": int(sorteio) if spec.duplasena else None,
        "origem": origem,
        "fonte": {
            "excel": {
                "ok": bool(excel.get("ok")),
                "arquivo": excel.get("arquivo"),
                "filename": excel.get("filename"),
                "concursos": len(excel.get("concursos") or []),
                "ja_ordenado": bool(excel.get("excel_ja_ordenado")),
            },
            "banco": {
                "ok": bool(banco.get("ok")),
                "concursos": len(banco.get("concursos") or []),
                "erro": banco.get("erro"),
            },
        },
        "universo": {
            "total": len(concursos),
            "primeiro": primeiro["concurso"] if primeiro else None,
            "primeiro_data": (primeiro or {}).get("data") or "",
            "ultimo": ultimo["concurso"] if ultimo else None,
            "ultimo_data": (ultimo or {}).get("data") or "",
        },
        "posicoes": posicoes,
        "matriz": _montar_matriz(posicoes, spec),
        "aposta_sugerida": aposta,
        "insights": _insights(key, modo, posicoes, spec, excel),
        "extra": _extras_freq(concursos, spec),
        "tem_ordem_sorteio": bool(banco.get("ok") and banco.get("concursos")),
        "excel_igual_sorteio": key == "supersete",
    }
