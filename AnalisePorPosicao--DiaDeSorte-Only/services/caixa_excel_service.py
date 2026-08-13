"""Importa Excel CAIXA (Dia de Sorte) no banco e gera JSON."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from models.caixa_excel_premiacao import (
    CaixaExcelLocalidadeDiaDeSorte,
    CaixaExcelPremiacaoDiaDeSorte,
)
from models.shared import db

import os
import sys

_SHARED = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from caixa_excel.config import DOWNLOADS_DIR, excel_filename, json_filename
from caixa_excel.download import baixar_excel
from caixa_excel.normalize import fmt_reais
from caixa_excel.parse_diadesorte import parse_planilha_diadesorte
from caixa_excel.xlsx_reader import ler_xlsx_dicts
from services.sorteio_premio_diadesorte import extrair_faixa, extrair_localidades_api


def _agora() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def _gravar_premiacao(rec: Dict[str, Any], stamp: str) -> None:
    bolas = (rec.get("bolas") or []) + [None] * 7
    conc = int(rec["concurso"])
    db.session.merge(
        CaixaExcelPremiacaoDiaDeSorte(
            concurso=conc,
            data=rec.get("data") or "",
            mes_sorte=str(rec.get("mes_sorte") or ""),
            bola1=bolas[0],
            bola2=bolas[1],
            bola3=bolas[2],
            bola4=bolas[3],
            bola5=bolas[4],
            bola6=bolas[5],
            bola7=bolas[6],
            ganhadores_7=rec.get("ganhadores_7") or 0,
            rateio_7=rec.get("rateio_7") or 0.0,
            ganhadores_6=rec.get("ganhadores_6") or 0,
            rateio_6=rec.get("rateio_6") or 0.0,
            atualizado_em=stamp,
        )
    )
    db.session.query(CaixaExcelLocalidadeDiaDeSorte).filter_by(concurso=conc).delete()
    for i, loc in enumerate(rec.get("localidades") or []):
        db.session.add(
            CaixaExcelLocalidadeDiaDeSorte(
                concurso=conc,
                cidade=loc.get("cidade") or "",
                uf=(loc.get("uf") or "")[:2],
                ordem=i,
            )
        )


def rec_from_api(concurso: int, dados: Dict[str, Any]) -> Dict[str, Any]:
    f7 = extrair_faixa(dados, 7) or {"ganhadores": 0, "rateio": 0.0}
    f6 = extrair_faixa(dados, 6) or {"ganhadores": 0, "rateio": 0.0}
    raw = dados.get("dezenasSorteadasOrdemSorteio") or dados.get("listaDezenas") or []
    bolas = []
    for x in raw[:7]:
        try:
            bolas.append(int(x))
        except (TypeError, ValueError):
            bolas.append(None)
    mes = (
        dados.get("nomeTimeCoracaoMesSorte")
        or dados.get("nomeMesSorte")
        or dados.get("mesSorte")
        or ""
    )
    return {
        "concurso": int(concurso),
        "data": str(dados.get("dataApuracao") or dados.get("data") or "").strip(),
        "mes_sorte": str(mes).strip(),
        "bolas": bolas,
        "ganhadores_7": f7.get("ganhadores") or 0,
        "rateio_7": f7.get("rateio") or 0.0,
        "ganhadores_6": f6.get("ganhadores") or 0,
        "rateio_6": f6.get("rateio") or 0.0,
        "localidades": extrair_localidades_api(dados),
    }


def upsert_premiacao_from_api(concurso: int, dados: Dict[str, Any]) -> bool:
    """Grava premiação/cidade a partir do JSON da API (sem commit)."""
    if not dados:
        return False
    _gravar_premiacao(rec_from_api(concurso, dados), _agora())
    return True


def _to_json_rec(p: CaixaExcelPremiacaoDiaDeSorte, locs: List[CaixaExcelLocalidadeDiaDeSorte]) -> Dict[str, Any]:
    bolas = [p.bola1, p.bola2, p.bola3, p.bola4, p.bola5, p.bola6, p.bola7]
    return {
        "concurso": p.concurso,
        "data": p.data or "",
        "mes_sorte": p.mes_sorte or "",
        "bolas": [b for b in bolas if b is not None],
        "ganhadores_7": p.ganhadores_7 or 0,
        "rateio_7": p.rateio_7 or 0.0,
        "rateio_7_fmt": fmt_reais(p.rateio_7),
        "ganhadores_6": p.ganhadores_6 or 0,
        "rateio_6": p.rateio_6 or 0.0,
        "rateio_6_fmt": fmt_reais(p.rateio_6),
        "localidades": [
            {"cidade": loc.cidade or "", "uf": loc.uf or ""}
            for loc in sorted(locs, key=lambda x: x.ordem)
        ],
    }


def gravar_json(registros: List[Dict[str, Any]]) -> str:
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    dest = DOWNLOADS_DIR / json_filename("diadesorte")
    payload = {
        "modalidade": "diadesorte",
        "gerado_em": _agora(),
        "total": len(registros),
        "registros": registros,
    }
    dest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(dest)


def importar_arquivo(path: Path | None = None) -> Dict[str, Any]:
    arquivo = Path(path) if path else DOWNLOADS_DIR / excel_filename("diadesorte")
    rows = ler_xlsx_dicts(arquivo)
    parsed = parse_planilha_diadesorte(rows)
    stamp = _agora()
    for rec in parsed:
        _gravar_premiacao(rec, stamp)
    db.session.commit()
    json_path = gravar_json(listar_premiacao_diadesorte(paginar=False)["registros"])
    return {
        "status": "success",
        "arquivo": str(arquivo),
        "json": json_path,
        "importados": len(parsed),
        "atualizado_em": stamp,
    }


def atualizar_diadesorte(*, baixar: bool = True, fonte: str = "api") -> Dict[str, Any]:
    fonte = (fonte or "api").strip().lower()
    if fonte == "excel":
        info: Dict[str, Any] = {}
        if baixar:
            info["download"] = baixar_excel("diadesorte")
        info["importacao"] = importar_arquivo()
        return {"status": "success", "fonte": "excel", **info}
    return backfill_premiacao_api(limite=80, apenas_faltantes=True)


def backfill_premiacao_api(
    *,
    limite: int = 80,
    apenas_faltantes: bool = True,
    pausa_entre: float = 0.25,
) -> Dict[str, Any]:
    """Preenche a tabela de premiação com a API Caixa (mesma fonte das dezenas)."""
    from models.sorteio_diadesorte import SorteioDiaDeSorte
    from services.api_diadesorte_service import ApiDiaDeSorteService

    limite = max(1, min(int(limite or 80), 200))
    todos = [r[0] for r in db.session.query(SorteioDiaDeSorte.concurso).order_by(
        SorteioDiaDeSorte.concurso.desc()
    ).all()]
    ja = {r[0] for r in db.session.query(CaixaExcelPremiacaoDiaDeSorte.concurso).all()}
    pendentes = [c for c in todos if c not in ja] if apenas_faltantes else list(todos)
    if not pendentes:
        json_path = gravar_json(listar_premiacao_diadesorte(paginar=False)["registros"])
        return {
            "status": "success",
            "fonte": "api",
            "message": f"Premiação completa: {len(ja)} concursos (API).",
            "processados": 0,
            "sucessos": 0,
            "falhas": 0,
            "pendentes_restantes": 0,
            "continuar": False,
            "total_premiacao": len(ja),
            "json": json_path,
        }
    lote = pendentes[:limite]
    sucessos = falhas = 0
    pausa = max(0.0, float(pausa_entre or 0))
    for i, concurso in enumerate(lote):
        if i > 0 and pausa:
            import time
            time.sleep(pausa)
        dados = ApiDiaDeSorteService.buscar_concurso_especifico(concurso, tentativas=4, pausa_retry=2.0)
        if dados and upsert_premiacao_from_api(concurso, dados):
            sucessos += 1
        else:
            falhas += 1
    db.session.commit()
    restantes = len(pendentes) - len(lote)
    total_now = db.session.query(CaixaExcelPremiacaoDiaDeSorte).count()
    json_path = ""
    if restantes <= 0:
        json_path = gravar_json(listar_premiacao_diadesorte(paginar=False)["registros"])
    return {
        "status": "progress" if restantes > 0 else "success",
        "fonte": "api",
        "message": (
            f"{sucessos} concurso(s) com premiação da API. Faltam {restantes} de {len(pendentes)}."
            if restantes > 0
            else f"Premiação da API concluída: {sucessos} concurso(s) neste lote. Total {total_now}."
        ),
        "processados": len(lote),
        "sucessos": sucessos,
        "falhas": falhas,
        "pendentes_restantes": restantes,
        "pendentes_total": len(pendentes),
        "continuar": restantes > 0,
        "total_premiacao": total_now,
        "json": json_path,
    }


def _rec_unificado(s, p: CaixaExcelPremiacaoDiaDeSorte | None, locs: List[CaixaExcelLocalidadeDiaDeSorte]) -> Dict[str, Any]:
    """Sorteio (dezenas/mês) + premiação (cidade/rateio) no mesmo registro."""
    if p is not None:
        rec = _to_json_rec(p, locs)
        rec["data"] = s.data or rec.get("data") or ""
        if not rec.get("mes_sorte"):
            rec["mes_sorte"] = s.mes_nome or ""
    else:
        g7 = s.ganhadores_7 if s.ganhadores_7 is not None else 0
        rec = {
            "concurso": s.concurso,
            "data": s.data or "",
            "mes_sorte": s.mes_nome or "",
            "bolas": s.dezenas_ordem_lista(),
            "ganhadores_7": g7,
            "rateio_7": 0.0,
            "rateio_7_fmt": fmt_reais(0),
            "ganhadores_6": 0,
            "rateio_6": 0.0,
            "rateio_6_fmt": fmt_reais(0),
            "localidades": [],
        }
    rec["dezenas"] = s.dezenas_lista()
    rec["dezenas_ordem"] = s.dezenas_ordem_lista()
    rec["mes_num"] = s.mes_num or 0
    rec["mes_nome"] = s.mes_nome or rec.get("mes_sorte") or ""
    rec["mes_abrev"] = s.mes_abrev()
    return rec


def listar_premiacao_diadesorte(
    *,
    page: int = 1,
    size: int = 50,
    paginar: bool = True,
) -> Dict[str, Any]:
    from models.sorteio_diadesorte import SorteioDiaDeSorte

    q = db.session.query(SorteioDiaDeSorte).order_by(SorteioDiaDeSorte.concurso.desc())
    total = q.count()
    if paginar:
        page = max(1, int(page or 1))
        size = min(200, max(10, int(size or 50)))
        sorteios = q.offset((page - 1) * size).limit(size).all()
    else:
        page, size = 1, total or 1
        sorteios = q.all()
    concs = [s.concurso for s in sorteios]
    prems: Dict[int, CaixaExcelPremiacaoDiaDeSorte] = {}
    locs_all: List[CaixaExcelLocalidadeDiaDeSorte] = []
    if concs:
        for p in (
            db.session.query(CaixaExcelPremiacaoDiaDeSorte)
            .filter(CaixaExcelPremiacaoDiaDeSorte.concurso.in_(concs))
            .all()
        ):
            prems[p.concurso] = p
        locs_all = (
            db.session.query(CaixaExcelLocalidadeDiaDeSorte)
            .filter(CaixaExcelLocalidadeDiaDeSorte.concurso.in_(concs))
            .all()
        )
    by_c: Dict[int, List[CaixaExcelLocalidadeDiaDeSorte]] = {}
    for loc in locs_all:
        by_c.setdefault(loc.concurso, []).append(loc)
    registros = [_rec_unificado(s, prems.get(s.concurso), by_c.get(s.concurso) or []) for s in sorteios]
    pages = max(1, (total + size - 1) // size) if paginar else 1
    return {
        "status": "success",
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
        "registros": registros,
    }


def ranking_uf_pagamentos() -> Dict[str, Any]:
    """Ranking de UF nos pagamentos: 1 ocorrência por par (concurso, UF)."""
    from sqlalchemy import func

    qtd = func.count(func.distinct(CaixaExcelLocalidadeDiaDeSorte.concurso))
    rows = (
        db.session.query(CaixaExcelLocalidadeDiaDeSorte.uf, qtd)
        .filter(func.length(func.trim(CaixaExcelLocalidadeDiaDeSorte.uf)) == 2)
        .group_by(CaixaExcelLocalidadeDiaDeSorte.uf)
        .order_by(qtd.desc(), CaixaExcelLocalidadeDiaDeSorte.uf.asc())
        .all()
    )
    ranking = []
    for i, (uf, quantidade) in enumerate(rows, start=1):
        ranking.append({
            "posicao": i,
            "uf": str(uf or "").strip().upper(),
            "quantidade": int(quantidade or 0),
        })
    return {
        "status": "success",
        "total_ufs": len(ranking),
        "total_ocorrencias": sum(x["quantidade"] for x in ranking),
        "ranking": ranking,
    }
