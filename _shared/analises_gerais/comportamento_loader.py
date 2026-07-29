# -*- coding: utf-8 -*-
"""Carrega sorteios do SQLite para análise comportamental na Central (sem Flask por modalidade)."""
from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from _shared.analises_gerais.loader import db_path_for
from _shared.analises_gerais.registry import ModalitySpec


@dataclass
class SorteioComportamento:
    concurso: int
    data: str
    dezenas: List[int]
    mes_num: Optional[int] = None
    mes_nome: Optional[str] = None
    time_num: Optional[int] = None
    time_nome: Optional[str] = None
    trevos: Optional[List[int]] = field(default=None)


def _base_dir() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def carregar_registros(
    spec: ModalitySpec,
    base_dir: Optional[str] = None,
) -> Tuple[List[SorteioComportamento], str]:
    root = base_dir or _base_dir()
    path = db_path_for(spec, root)
    if not os.path.isfile(path):
        return [], f"Banco não encontrado: {path}"

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(f"SELECT * FROM {spec.table} ORDER BY concurso ASC")
        rows = cur.fetchall()
    except sqlite3.Error as e:
        return [], str(e)
    finally:
        conn.close()

    if not rows:
        return [], "ok"

    keys = rows[0].keys()
    out: List[SorteioComportamento] = []

    for row in rows:
        rec = _row_to_registro(spec, row, keys)
        if rec:
            out.append(rec)

    return out, "ok"


def _row_to_registro(spec: ModalitySpec, row: sqlite3.Row, keys) -> Optional[SorteioComportamento]:
    data = str(row["data"]) if "data" in keys else ""
    concurso = int(row["concurso"])

    if spec.key == "lotofacil":
        dz = [int(row[f"posicao_{i}"]) for i in range(1, 16) if f"posicao_{i}" in keys]
    elif spec.key == "duplasena":
        dz = [int(row[f"s1_d{i}"]) for i in range(1, 7) if f"s1_d{i}" in keys]
    elif spec.key == "supersete":
        dz = [int(row[f"coluna_{i}"]) for i in range(1, 8) if f"coluna_{i}" in keys]
    elif spec.key == "lotomania":
        dz = sorted(int(row[f"d{i:02d}"]) for i in range(1, 21) if f"d{i:02d}" in keys)
    elif spec.key == "timemania":
        dz = sorted(int(row[f"d{i}"]) for i in range(1, 11) if f"d{i}" in keys)
    else:
        cols = []
        for k in keys:
            if k in spec.skip_columns or k.startswith("s2_") or k.startswith("trevo"):
                continue
            if k.startswith("d") and len(k) <= 3:
                cols.append(k)
        if not cols and "d1" in keys:
            cols = [f"d{i}" for i in range(1, spec.sorteadas + 1) if f"d{i}" in keys]
        dz = sorted(int(row[c]) for c in cols)

    need = spec.sorteadas
    if len(dz) < need:
        return None

    rec = SorteioComportamento(
        concurso=concurso,
        data=data,
        dezenas=dz[:need],
    )

    if spec.key == "diadesorte" and "mes_num" in keys and row["mes_num"] is not None:
        rec.mes_num = int(row["mes_num"])
        rec.mes_nome = str(row["mes_nome"]) if "mes_nome" in keys and row["mes_nome"] else None
    if spec.key == "timemania" and "time_num" in keys and row["time_num"] is not None:
        rec.time_num = int(row["time_num"])
        rec.time_nome = str(row["time_nome"]) if "time_nome" in keys and row["time_nome"] else None
    if spec.key == "maismilionaria":
        tv = []
        for c in ("trevo1", "trevo2"):
            if c in keys and row[c] is not None:
                tv.append(int(row[c]))
        if len(tv) == 2:
            rec.trevos = sorted(tv)

    return rec
