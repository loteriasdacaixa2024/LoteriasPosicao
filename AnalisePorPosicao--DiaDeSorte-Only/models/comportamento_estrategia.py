# -*- coding: utf-8 -*-
"""Persistência — conferência comparativa das 3 estratégias comportamentais."""
import json
from datetime import datetime

from .shared import db


class ComportamentoEstrategiaRegistro(db.Model):
    """Um registro = conferência de um concurso contra apostas das 3 bases."""
    __tablename__ = "comportamento_estrategia_registros"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    concurso = db.Column(db.Integer, nullable=False, index=True)
    data_execucao = db.Column(db.String(50), nullable=False, default=lambda: datetime.now().isoformat())
    resumo_json = db.Column(db.Text, default="{}")

    itens = db.relationship(
        "ComportamentoEstrategiaRegistroItem",
        backref="registro",
        cascade="all, delete-orphan",
    )

    def resumo_dict(self):
        try:
            return json.loads(self.resumo_json or "{}")
        except json.JSONDecodeError:
            return {}


class ComportamentoEstrategiaRegistroItem(db.Model):
    __tablename__ = "comportamento_estrategia_itens"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    registro_id = db.Column(
        db.Integer,
        db.ForeignKey("comportamento_estrategia_registros.id"),
        nullable=False,
        index=True,
    )
    base_estrategia = db.Column(db.String(20), nullable=False, index=True)
    qtd_apostas = db.Column(db.Integer, nullable=False, default=0)
    max_acertos = db.Column(db.Integer, nullable=False, default=0)
    media_acertos = db.Column(db.Float, nullable=False, default=0.0)
    total_acertos = db.Column(db.Integer, nullable=False, default=0)
    dist_4 = db.Column(db.Integer, nullable=False, default=0)
    dist_5 = db.Column(db.Integer, nullable=False, default=0)
    dist_6 = db.Column(db.Integer, nullable=False, default=0)
    dist_7 = db.Column(db.Integer, nullable=False, default=0)
