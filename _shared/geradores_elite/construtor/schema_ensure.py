# -*- coding: utf-8 -*-
"""Migrações leves do Construtor (SQLite legado sem create_all incremental)."""
from __future__ import annotations

from models.shared import db

_DONE = False

_ALTERS = (
    "ALTER TABLE construtor_construcoes ADD COLUMN extra_json TEXT DEFAULT '{}'",
    "ALTER TABLE construtor_construcoes ADD COLUMN mes_num INTEGER",
    "ALTER TABLE construtor_sessoes ADD COLUMN tipo_universo VARCHAR(20) DEFAULT 'dezenas'",
    "ALTER TABLE construtor_sessoes ADD COLUMN meta_json TEXT DEFAULT '{}'",
)


def ensure_construtor_schema() -> None:
    """Idempotente: adiciona colunas novas se a tabela já existia sem elas."""
    global _DONE
    if _DONE:
        return
    for sql in _ALTERS:
        try:
            db.session.execute(db.text(sql))
            db.session.commit()
        except Exception:
            db.session.rollback()
    _DONE = True
