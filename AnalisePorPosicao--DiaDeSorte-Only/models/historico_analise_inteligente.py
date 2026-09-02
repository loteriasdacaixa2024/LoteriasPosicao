# -*- coding: utf-8 -*-
"""Snapshot silencioso por concurso — base do Panorama Histórico (nível 1)."""
from datetime import datetime

from .shared import db


class HistoricoAnaliseInteligente(db.Model):
    """
    Uma linha por concurso do Dia de Sorte.
    Guarda o que a análise inteligente já calcula — sem alterar ABA 4/5.
    """

    __tablename__ = "historico_analise_inteligente"

    concurso = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(20), nullable=False, default="")

    dezenas_fmt = db.Column(db.String(64), nullable=False, default="")
    dezenas_ordem_caixa_fmt = db.Column(db.String(64), nullable=True, default="")

    padrao_inicial = db.Column(db.String(32), nullable=False, default="", index=True)
    padrao_final = db.Column(db.String(32), nullable=True, default="")
    descricao_bma = db.Column(db.String(32), nullable=True, default="")

    soma = db.Column(db.Integer, nullable=False, default=0)
    pares = db.Column(db.Integer, nullable=True)
    impares = db.Column(db.Integer, nullable=True)
    pares_impares_fmt = db.Column(db.String(24), nullable=True, default="")

    digitos_ordenados_fmt = db.Column(db.String(48), nullable=True, default="")
    qtd_digitos = db.Column(db.Integer, nullable=True)
    volume_combinacoes = db.Column(db.Integer, nullable=True)

    mes_num = db.Column(db.Integer, nullable=True)
    mes_nome = db.Column(db.String(20), nullable=True, default="")
    mes_abrev = db.Column(db.String(8), nullable=True, default="")

    atualizado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<HistoricoAnaliseInteligente {self.concurso} {self.padrao_inicial}>"
