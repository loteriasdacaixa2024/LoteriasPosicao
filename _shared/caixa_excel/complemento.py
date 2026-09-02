# -*- coding: utf-8 -*-
"""Premiação complementar (Excel CAIXA) — nunca grava em sorteio_*.

Hierarquia: se o concurso já existe em caixa_excel_complemento, o banco prevalece
(a linha não é atualizada). Só insere o que falta. Dezenas oficiais continuam
exclusivas da tabela sorteio_*.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import text

from .config import DOWNLOADS_DIR, excel_filename
from .download import baixar_excel
from .normalize import fmt_reais
from .parse_modalidades import parse_planilha
from .xlsx_reader import ler_xlsx_dicts

DDL = """
CREATE TABLE IF NOT EXISTS caixa_excel_complemento (
    concurso INTEGER PRIMARY KEY,
    data TEXT NOT NULL DEFAULT '',
    payload_json TEXT NOT NULL DEFAULT '{}',
    origem TEXT NOT NULL DEFAULT 'excel',
    atualizado_em TEXT NOT NULL DEFAULT ''
)
"""


def _agora() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def _sql(db, sql: str):
    fn = getattr(db, "text", None)
    return db.session.execute(fn(sql) if callable(fn) else text(sql))


def ensure_schema(db) -> None:
    _sql(db, DDL)
    db.session.commit()


def _sorteio_concursos(db, sorteio_model) -> Set[int]:
    return {int(r[0]) for r in db.session.query(sorteio_model.concurso).all()}


def _ja_complemento(db) -> Set[int]:
    rows = _sql(db, "SELECT concurso FROM caixa_excel_complemento").fetchall()
    return {int(r[0]) for r in rows}


def importar_excel_complemento(
    db,
    *,
    modality_key: str,
    sorteio_model,
    baixar: bool = False,
    path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Insere premiação só para concursos que já existem em sorteio_* e ainda
    não têm linha em caixa_excel_complemento. Não altera sorteio_*."""
    ensure_schema(db)
    info: Dict[str, Any] = {"fonte": "excel", "tabela_sorteio_alterada": False}
    if baixar:
        info["download"] = baixar_excel(modality_key)
    arquivo = Path(path) if path else DOWNLOADS_DIR / excel_filename(modality_key)
    rows = ler_xlsx_dicts(arquivo)
    parsed = parse_planilha(modality_key, rows)
    no_sorteio = _sorteio_concursos(db, sorteio_model)
    ja = _ja_complemento(db)
    stamp = _agora()
    inseridos = 0
    pulados_existentes = 0
    pulados_sem_sorteio = 0
    for rec in parsed:
        conc = int(rec["concurso"])
        if conc not in no_sorteio:
            pulados_sem_sorteio += 1
            continue
        if conc in ja:
            pulados_existentes += 1
            continue
        stmt = text(
            "INSERT INTO caixa_excel_complemento "
            "(concurso, data, payload_json, origem, atualizado_em) "
            "VALUES (:c, :d, :p, 'excel', :a)"
        )
        db.session.execute(
            stmt,
            {
                "c": conc,
                "d": rec.get("data") or "",
                "p": json.dumps(rec, ensure_ascii=False),
                "a": stamp,
            },
        )
        ja.add(conc)
        inseridos += 1
    db.session.commit()
    info.update({
        "status": "success",
        "arquivo": str(arquivo),
        "linhas_xlsx": len(parsed),
        "inseridos": inseridos,
        "pulados_ja_no_banco": pulados_existentes,
        "pulados_sem_sorteio": pulados_sem_sorteio,
        "atualizado_em": stamp,
        "message": (
            f"Excel complementar: {inseridos} inserido(s), "
            f"{pulados_existentes} já no banco (prevalecem), "
            f"{pulados_sem_sorteio} sem sorteio no banco (ignorados)."
        ),
    })
    return info


def _dezenas_de(s) -> tuple:
    if hasattr(s, "dezenas_lista"):
        dez = list(s.dezenas_lista())
    elif hasattr(s, "digitos"):
        dez = list(s.digitos())
    else:
        dez = list(s.dezenas()) if hasattr(s, "dezenas") else []
    if hasattr(s, "dezenas_ordem_lista"):
        ordem = list(s.dezenas_ordem_lista())
    elif hasattr(s, "digitos_ordem_lista"):
        ordem = list(s.digitos_ordem_lista())
    else:
        ordem = list(dez)
    extras: Dict[str, Any] = {}
    if hasattr(s, "trevos_lista"):
        extras["trevos"] = list(s.trevos_lista())
    if hasattr(s, "sorteio2_lista"):
        extras["sorteio1"] = list(s.sorteio1_lista())
        extras["sorteio2"] = list(s.sorteio2_lista())
    if hasattr(s, "mes_nome"):
        extras["mes_nome"] = s.mes_nome or ""
        extras["mes_num"] = s.mes_num or 0
    if hasattr(s, "time_nome"):
        extras["time_nome"] = s.time_nome or ""
        extras["time_num"] = s.time_num or 0
    return dez, ordem, extras


def listar_complemento(
    db,
    sorteio_model,
    *,
    modality_key: Optional[str] = None,
    page: int = 1,
    size: int = 50,
    paginar: bool = True,
) -> Dict[str, Any]:
    ensure_schema(db)
    if modality_key and not _ja_complemento(db):
        try:
            importar_excel_complemento(
                db,
                modality_key=modality_key,
                sorteio_model=sorteio_model,
                baixar=False,
            )
        except FileNotFoundError:
            pass
    q = db.session.query(sorteio_model).order_by(sorteio_model.concurso.desc())
    total = q.count()
    if paginar:
        page = max(1, int(page or 1))
        size = min(200, max(10, int(size or 50)))
        sorteios = q.offset((page - 1) * size).limit(size).all()
    else:
        page, size = 1, total or 1
        sorteios = q.all()
    concs = [int(s.concurso) for s in sorteios]
    prems: Dict[int, Dict[str, Any]] = {}
    if concs:
        ph = ",".join(str(int(c)) for c in concs)
        rows = _sql(
            db,
            f"SELECT concurso, payload_json FROM caixa_excel_complemento WHERE concurso IN ({ph})",
        ).fetchall()
        for conc, raw in rows:
            try:
                prems[int(conc)] = json.loads(raw or "{}")
            except json.JSONDecodeError:
                prems[int(conc)] = {}
    registros = []
    for s in sorteios:
        dez, ordem, extras_s = _dezenas_de(s)
        payload = prems.get(int(s.concurso)) or {}
        extras = {**extras_s, **(payload.get("extras") or {})}
        faixas = []
        for f in payload.get("faixas") or []:
            rateio = f.get("rateio")
            faixas.append({
                "nome": f.get("nome") or "",
                "ganhadores": int(f.get("ganhadores") or 0),
                "rateio": float(rateio or 0),
                "rateio_fmt": fmt_reais(rateio) if rateio else "—",
            })
        rec = {
            "concurso": s.concurso,
            "data": s.data or payload.get("data") or "",
            "dezenas": dez,
            "dezenas_ordem": ordem,
            "localidades": payload.get("localidades") or [],
            "faixas": faixas,
            "extras": extras,
            **extras_s,
        }
        registros.append(rec)
    pages = max(1, (total + size - 1) // size) if paginar else 1
    ja = _ja_complemento(db)
    excel_max = max(ja) if ja else 0
    return {
        "status": "success",
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
        "registros": registros,
        "fonte_dezenas": "sorteio",
        "excel_concursos": len(ja),
        "excel_concurso_maximo": excel_max,
    }


def ranking_uf_complemento(db) -> Dict[str, Any]:
    """1 ocorrência por par (concurso, UF) a partir do Excel complementar."""
    ensure_schema(db)
    rows = _sql(db, "SELECT concurso, payload_json FROM caixa_excel_complemento").fetchall()
    counts: Dict[str, int] = {}
    seen = set()
    for conc, raw in rows:
        try:
            payload = json.loads(raw or "{}")
        except json.JSONDecodeError:
            continue
        ufs = set()
        for loc in payload.get("localidades") or []:
            uf = str((loc or {}).get("uf") or "").strip().upper()
            if len(uf) == 2:
                ufs.add(uf)
        for uf in ufs:
            key = (int(conc), uf)
            if key in seen:
                continue
            seen.add(key)
            counts[uf] = counts.get(uf, 0) + 1
    ranking = []
    for i, (uf, qtd) in enumerate(sorted(counts.items(), key=lambda x: (-x[1], x[0])), start=1):
        ranking.append({"posicao": i, "uf": uf, "quantidade": int(qtd)})
    return {
        "status": "success",
        "total_ufs": len(ranking),
        "total_ocorrencias": sum(x["quantidade"] for x in ranking),
        "ranking": ranking,
    }
