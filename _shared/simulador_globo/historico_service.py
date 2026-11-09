# -*- coding: utf-8 -*-
"""Histórico das simulações no SQLite já usado pela modalidade."""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from typing import Callable, Optional

_LOCK = threading.Lock()


def caminho_sqlite(uri: str) -> str:
    if not uri or not str(uri).startswith("sqlite:"):
        raise ValueError("A aplicação não está usando SQLite.")
    resto = str(uri)[len("sqlite:"):]
    if resto.startswith("///"):
        resto = resto[3:]
    elif resto.startswith("//"):
        resto = resto[2:]
    return resto


def _agora() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema(path: str) -> None:
    with _LOCK:
        conn = _connect(path)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS simulacao_globo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    modalidade TEXT NOT NULL,
                    criado_em TEXT NOT NULL,
                    atualizado_em TEXT NOT NULL,
                    universo INTEGER NOT NULL,
                    sorteadas_previstas INTEGER NOT NULL,
                    velocidade_ms INTEGER NOT NULL DEFAULT 5000,
                    status TEXT NOT NULL,
                    sequencia_json TEXT NOT NULL DEFAULT '[]',
                    estado_json TEXT NOT NULL DEFAULT '{}',
                    bolas_restantes INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_simulacao_globo_mod "
                "ON simulacao_globo (modalidade, id DESC)"
            )
            conn.commit()
        finally:
            conn.close()


def _row_para_dict(row: sqlite3.Row) -> dict:
    data = dict(row)
    data["sequencia"] = json.loads(data.pop("sequencia_json") or "[]")
    data["estado"] = json.loads(data.pop("estado_json") or "{}")
    return data


def criar(path: str, modalidade: str, estado: dict, velocidade_ms: int, previstas: int, restantes: int) -> dict:
    with _LOCK:
        conn = _connect(path)
        try:
            agora = _agora()
            conn.execute(
                """
                UPDATE simulacao_globo
                   SET status = 'interrompida', atualizado_em = ?
                 WHERE modalidade = ?
                   AND status IN ('preparada', 'em_andamento')
                """,
                (agora, modalidade),
            )
            cur = conn.execute(
                """
                INSERT INTO simulacao_globo (
                    modalidade, criado_em, atualizado_em, universo, sorteadas_previstas,
                    velocidade_ms, status, sequencia_json, estado_json, bolas_restantes
                ) VALUES (?, ?, ?, ?, ?, ?, 'preparada', '[]', ?, ?)
                """,
                (
                    modalidade,
                    agora,
                    agora,
                    int(estado.get("universo") or 0),
                    int(previstas),
                    int(velocidade_ms),
                    json.dumps(estado, ensure_ascii=False),
                    int(restantes),
                ),
            )
            conn.commit()
            sim_id = int(cur.lastrowid)
        finally:
            conn.close()
    return obter(path, sim_id, modalidade)


def obter(path: str, sim_id: int, modalidade: str) -> Optional[dict]:
    with _LOCK:
        conn = _connect(path)
        try:
            row = conn.execute(
                "SELECT * FROM simulacao_globo WHERE id = ? AND modalidade = ?",
                (int(sim_id), modalidade),
            ).fetchone()
        finally:
            conn.close()
    if row is None:
        return None
    return _row_para_dict(row)


def atualizar(path: str, sim_id: int, modalidade: str, mutator: Callable[[dict], dict]) -> Optional[dict]:
    with _LOCK:
        conn = _connect(path)
        try:
            row = conn.execute(
                "SELECT * FROM simulacao_globo WHERE id = ? AND modalidade = ?",
                (int(sim_id), modalidade),
            ).fetchone()
            if row is None:
                return None
            data = _row_para_dict(row)
            data = mutator(data)
            conn.execute(
                """
                UPDATE simulacao_globo
                   SET atualizado_em = ?, velocidade_ms = ?, status = ?,
                       sequencia_json = ?, estado_json = ?, bolas_restantes = ?
                 WHERE id = ?
                """,
                (
                    _agora(),
                    int(data["velocidade_ms"]),
                    data["status"],
                    json.dumps(data["sequencia"], ensure_ascii=False),
                    json.dumps(data["estado"], ensure_ascii=False),
                    int(data["bolas_restantes"]),
                    int(sim_id),
                ),
            )
            conn.commit()
            return data
        finally:
            conn.close()


def listar(path: str, modalidade: str, limite: int = 50) -> list:
    with _LOCK:
        conn = _connect(path)
        try:
            rows = conn.execute(
                """
                SELECT id, modalidade, criado_em, atualizado_em, universo,
                       sorteadas_previstas, velocidade_ms, status, bolas_restantes,
                       sequencia_json
                  FROM simulacao_globo
                 WHERE modalidade = ?
                   AND sequencia_json != '[]'
                 ORDER BY id DESC
                 LIMIT ?
                """,
                (modalidade, int(limite)),
            ).fetchall()
        finally:
            conn.close()
    saida = []
    for row in rows:
        item = dict(row)
        seq = json.loads(item.pop("sequencia_json") or "[]")
        item["quantidade_sorteada"] = len(seq)
        item["resumo"] = " ".join(str(b.get("rotulo") or "") for b in seq[:24])
        saida.append(item)
    return saida


def velocidade_valida(valor, padrao: int = 5000) -> int:
    try:
        n = int(valor)
    except (TypeError, ValueError):
        return padrao
    return max(1000, min(10000, n))
