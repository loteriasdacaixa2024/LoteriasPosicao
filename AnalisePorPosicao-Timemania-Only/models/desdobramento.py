from datetime import datetime

from .shared import db


class Desdobramento(db.Model):
    __tablename__ = 'desdobramentos'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(100), nullable=False)
    data_criacao = db.Column(db.String(50), nullable=False, default=lambda: datetime.now().isoformat())
    numeros = db.Column(db.String(100), nullable=False)
    total_apostas = db.Column(db.Integer, default=0)
    modo = db.Column(db.String(20), default='bronze')
    tipo = db.Column(db.String(20), default='dezenas')

    grupos = db.relationship('GrupoDesdobramento', backref='desdobramento', cascade='all, delete-orphan')
    apostas = db.relationship('ApostaDesdobramento', backref='desdobramento', cascade='all, delete-orphan')


class GrupoDesdobramento(db.Model):
    __tablename__ = 'grupos_desdobramento'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    desdobramento_id = db.Column(db.Integer, db.ForeignKey('desdobramentos.id'), nullable=False)
    grupo_numero = db.Column(db.Integer, nullable=False)
    numeros = db.Column(db.String(100), nullable=False)


class ApostaDesdobramento(db.Model):
    __tablename__ = 'apostas_desdobramento'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    desdobramento_id = db.Column(db.Integer, db.ForeignKey('desdobramentos.id'), nullable=False)
    linha = db.Column(db.Integer, nullable=False)
    aposta_numero = db.Column(db.Integer, nullable=False)
    dezenas = db.Column(db.String(100), nullable=False)
