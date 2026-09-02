from .shared import db
from datetime import datetime

class Desdobramento(db.Model):
    """
    Armazena a configuração principal do desdobramento de 16 números.
    """
    __tablename__ = 'desdobramentos'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(100), nullable=False)
    data_criacao = db.Column(db.String(50), nullable=False, default=lambda: datetime.now().isoformat())
    numeros = db.Column(db.String(100), nullable=False)  # CSV "1,2,3,..."
    total_apostas = db.Column(db.Integer, default=0)
    modo = db.Column(db.String(20), default='bronze')

    # Relacionamentos com remoção em cascata
    grupos = db.relationship('GrupoDesdobramento', backref='desdobramento', cascade='all, delete-orphan')
    apostas = db.relationship('ApostaDesdobramento', backref='desdobramento', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Desdobramento {self.nome} ({self.modo})>'


class GrupoDesdobramento(db.Model):
    """
    Armazena os 4 grupos de 4 números criados no desdobramento.
    """
    __tablename__ = 'grupos_desdobramento'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    desdobramento_id = db.Column(db.Integer, db.ForeignKey('desdobramentos.id'), nullable=False)
    grupo_numero = db.Column(db.Integer, nullable=False)  # 1, 2, 3, 4
    numeros = db.Column(db.String(100), nullable=False)  # CSV "1,2,3,4"

    def __repr__(self):
        return f'<GrupoDesdobramento {self.grupo_numero} - Desdobramento {self.desdobramento_id}>'


class ApostaDesdobramento(db.Model):
    """
    Armazena as apostas de 6 dezenas geradas a partir das junções do desdobramento.
    """
    __tablename__ = 'apostas_desdobramento'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    desdobramento_id = db.Column(db.Integer, db.ForeignKey('desdobramentos.id'), nullable=False)
    linha = db.Column(db.Integer, nullable=False)  # Linha virtual do desdobramento
    aposta_numero = db.Column(db.Integer, nullable=False)  # Índice da aposta dentro da linha (1 a 4)
    dezenas = db.Column(db.String(100), nullable=False)  # CSV "1,2,3,4,5,6"

    def __repr__(self):
        return f'<ApostaDesdobramento Linha {self.linha} - Aposta {self.aposta_numero}>'
