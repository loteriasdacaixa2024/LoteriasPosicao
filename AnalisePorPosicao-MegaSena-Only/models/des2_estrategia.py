"""Modelo exclusivo do módulo Des2 — não altera tabelas do Des1."""
from .shared import db


class Des2Estrategia(db.Model):
    __tablename__ = 'des2_estrategia'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    data_criacao = db.Column(db.String(30), nullable=False)
    colunas = db.Column(db.String(50), nullable=False)
    qtd_dezenas = db.Column(db.Integer, nullable=False)
    total_jogos = db.Column(db.Integer, default=15)
    valor_total = db.Column(db.Float, default=0)
    jogos_json = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f'<Des2Estrategia {self.id} {self.nome}>'
