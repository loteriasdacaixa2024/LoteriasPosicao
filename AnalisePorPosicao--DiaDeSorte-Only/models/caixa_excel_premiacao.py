from .shared import db


class CaixaExcelPremiacaoDiaDeSorte(db.Model):
    """Premiação oficial (Excel CAIXA) até a 2ª faixa — 7 e 6 acertos."""

    __tablename__ = "caixa_excel_premiacao_diadesorte"

    concurso = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(20), nullable=False, default="")
    mes_sorte = db.Column(db.String(20), default="")
    bola1 = db.Column(db.Integer)
    bola2 = db.Column(db.Integer)
    bola3 = db.Column(db.Integer)
    bola4 = db.Column(db.Integer)
    bola5 = db.Column(db.Integer)
    bola6 = db.Column(db.Integer)
    bola7 = db.Column(db.Integer)
    ganhadores_7 = db.Column(db.Integer, default=0)
    rateio_7 = db.Column(db.Float, default=0.0)
    ganhadores_6 = db.Column(db.Integer, default=0)
    rateio_6 = db.Column(db.Float, default=0.0)
    atualizado_em = db.Column(db.String(32), default="")


class CaixaExcelLocalidadeDiaDeSorte(db.Model):
    """Cidade e UF separados (faixa de 7 acertos)."""

    __tablename__ = "caixa_excel_localidade_diadesorte"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    concurso = db.Column(db.Integer, nullable=False, index=True)
    cidade = db.Column(db.String(80), default="")
    uf = db.Column(db.String(2), default="")
    ordem = db.Column(db.Integer, default=0)
