# -*- coding: utf-8 -*-
import os
import sqlite3
from typing import List, Tuple

from _shared.analises_gerais.registry import ModalitySpec


def db_path_for(spec: ModalitySpec, base_dir: str) -> str:
    primary = os.path.join(base_dir, spec.app_dir, "instance", spec.db_filename)
    if os.path.isfile(primary):
        return primary
    # Legado: pasta com hífens duplicados incorretos
    if spec.key == "diadesorte":
        legado = os.path.join(
            base_dir, "AnalisePorPosicao---DiaDeSorte-Only", "instance", spec.db_filename
        )
        if os.path.isfile(legado):
            return legado
    return primary


def carregar_sorteios(spec: ModalitySpec, base_dir: str) -> Tuple[List[Tuple[int, str, List[int]]], str]:
    path = db_path_for(spec, base_dir)
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

    out: List[Tuple[int, str, List[int]]] = []
    keys = rows[0].keys()
    num_cols = _colunas_numericas(spec, keys)

    for row in rows:
        dezenas = []
        for c in num_cols:
            v = row[c]
            if v is not None:
                dezenas.append(int(v))
        if spec.layout == "posicional":
            dezenas = dezenas[: spec.sorteadas]
        if len(dezenas) < spec.sorteadas:
            continue
        data = str(row["data"]) if "data" in keys else ""
        out.append((int(row["concurso"]), data, dezenas[: spec.sorteadas]))

    return out, "ok"


def _colunas_numericas(spec: ModalitySpec, keys) -> List[str]:
    if spec.key == "lotofacil":
        return [f"posicao_{i}" for i in range(1, 16) if f"posicao_{i}" in keys]
    if spec.key == "duplasena":
        return [f"s1_d{i}" for i in range(1, 7) if f"s1_d{i}" in keys]
    if spec.key == "supersete":
        return [f"coluna_{i}" for i in range(1, 8) if f"coluna_{i}" in keys]
    if spec.key == "lotomania":
        return [f"d{i:02d}" for i in range(1, 21) if f"d{i:02d}" in keys]
    if spec.key == "timemania":
        return [f"d{i}" for i in range(1, 11) if f"d{i}" in keys]

    cols = []
    for k in keys:
        if k in spec.skip_columns:
            continue
        if k.startswith("s2_"):
            continue
        if k.startswith("trevo"):
            continue
        if k.startswith("d") and len(k) <= 3:
            cols.append(k)
    if not cols and "d1" in keys:
        cols = [f"d{i}" for i in range(1, spec.sorteadas + 1) if f"d{i}" in keys]
    return cols
