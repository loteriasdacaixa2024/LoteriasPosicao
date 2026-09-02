# -*- coding: utf-8 -*-
"""Modelos SQLAlchemy — Construtor de Construções (compartilhado)."""
from __future__ import annotations

import json
from datetime import datetime

from models.shared import db


class ConstrutorSessao(db.Model):
    __tablename__ = "construtor_sessoes"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(120), nullable=False)
    data_criacao = db.Column(db.String(50), nullable=False, default=lambda: datetime.now().isoformat())
    conjunto_base = db.Column(db.String(400), nullable=False)
    dezenas_por_aposta = db.Column(db.Integer, nullable=False, default=7)
    origem_conjunto = db.Column(db.String(30), default="manual")
    concurso_referencia = db.Column(db.Integer, nullable=True)
    # dezenas (padrão / legado) | digitos (Aba 2/3)
    tipo_universo = db.Column(db.String(20), nullable=False, default="dezenas")
    meta_json = db.Column(db.Text, default="{}")

    construcoes = db.relationship(
        "ConstrutorConstrucao",
        backref="sessao",
        cascade="all, delete-orphan",
        order_by="ConstrutorConstrucao.numero",
    )

    def conjunto_lista(self):
        if not self.conjunto_base:
            return []
        raw = self.conjunto_base.strip()
        if raw.startswith("{"):
            try:
                data = json.loads(raw)
                flat = []
                for key in sorted(data.keys(), key=lambda x: int(x)):
                    flat.extend(int(x) for x in (data[key] or []))
                return sorted(set(flat))
            except (json.JSONDecodeError, ValueError, TypeError):
                return []
        return sorted(int(x.strip()) for x in self.conjunto_base.split(",") if x.strip())


class ConstrutorConstrucao(db.Model):
    __tablename__ = "construtor_construcoes"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sessao_id = db.Column(db.Integer, db.ForeignKey("construtor_sessoes.id"), nullable=False)
    numero = db.Column(db.Integer, nullable=False)
    estrategia = db.Column(db.String(40), nullable=False)
    estrategia_params = db.Column(db.Text, default="{}")
    distribuicao = db.Column(db.String(80), default="")
    similaridade_anterior = db.Column(db.Float, nullable=True)
    diferenca_pct = db.Column(db.Float, nullable=True)
    mes_num = db.Column(db.Integer, nullable=True)
    extra_json = db.Column(db.Text, default="{}")
    data_criacao = db.Column(db.String(50), nullable=False, default=lambda: datetime.now().isoformat())

    apostas = db.relationship(
        "ConstrutorAposta",
        backref="construcao",
        cascade="all, delete-orphan",
        order_by="ConstrutorAposta.linha",
    )
    conferencias_historico = db.relationship(
        "ConstrutorConferenciaHistorico",
        backref="construcao",
        cascade="all, delete-orphan",
        order_by="ConstrutorConferenciaHistorico.data_execucao.desc()",
    )

    def params_dict(self):
        try:
            return json.loads(self.estrategia_params or "{}")
        except json.JSONDecodeError:
            return {}

    def extra_dict(self):
        try:
            return json.loads(self.extra_json or "{}")
        except json.JSONDecodeError:
            return {}


class ConstrutorAposta(db.Model):
    __tablename__ = "construtor_apostas"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    construcao_id = db.Column(db.Integer, db.ForeignKey("construtor_construcoes.id"), nullable=False)
    linha = db.Column(db.Integer, nullable=False)
    dezenas = db.Column(db.String(200), nullable=False)

    def dezenas_lista(self):
        return sorted(int(x.strip()) for x in self.dezenas.split(",") if x.strip())


class ConstrutorConferenciaHistorico(db.Model):
    __tablename__ = "construtor_conferencias_hist"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    construcao_id = db.Column(
        db.Integer, db.ForeignKey("construtor_construcoes.id"), nullable=False, index=True
    )
    sessao_id = db.Column(
        db.Integer, db.ForeignKey("construtor_sessoes.id"), nullable=False, index=True
    )
    data_execucao = db.Column(db.String(50), nullable=False, default=lambda: datetime.now().isoformat())
    modo = db.Column(db.String(20), default="completo")
    concurso_min = db.Column(db.Integer, nullable=False)
    concurso_max = db.Column(db.Integer, nullable=False)
    total_concursos = db.Column(db.Integer, nullable=False, default=0)
    resumo_json = db.Column(db.Text, default="{}")

    itens = db.relationship(
        "ConstrutorConferenciaHistoricoItem",
        backref="conferencia",
        cascade="all, delete-orphan",
        order_by="ConstrutorConferenciaHistoricoItem.concurso",
    )

    def resumo_dict(self):
        try:
            return json.loads(self.resumo_json or "{}")
        except json.JSONDecodeError:
            return {}


class ConstrutorConferenciaHistoricoItem(db.Model):
    __tablename__ = "construtor_conferencia_hist_itens"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    conferencia_id = db.Column(
        db.Integer, db.ForeignKey("construtor_conferencias_hist.id"), nullable=False, index=True
    )
    concurso = db.Column(db.Integer, nullable=False)
    data_sorteio = db.Column(db.String(30), default="")
    max_acertos = db.Column(db.Integer, nullable=False, default=0)
    media_acertos = db.Column(db.Float, nullable=False, default=0.0)
    total_acertos = db.Column(db.Integer, nullable=False, default=0)
    melhor_linha = db.Column(db.Integer, nullable=True)
