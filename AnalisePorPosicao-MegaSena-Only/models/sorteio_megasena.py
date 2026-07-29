from .shared import db

class SorteioMegaSena(db.Model):
    """
    Armazena cada concurso da Mega-Sena.
    Mega-Sena: 6 dezenas sorteadas de 01 a 60.
    Prêmios: sena (6), quina (5), quadra (4).
    """
    __tablename__ = 'sorteio_megasena'

    concurso = db.Column(db.Integer, primary_key=True)
    data     = db.Column(db.String(20), nullable=False)

    d1 = db.Column(db.Integer, nullable=False)
    d2 = db.Column(db.Integer, nullable=False)
    d3 = db.Column(db.Integer, nullable=False)
    d4 = db.Column(db.Integer, nullable=False)
    d5 = db.Column(db.Integer, nullable=False)
    d6 = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<SorteioMegaSena {self.concurso}>'

    def dezenas(self):
        return {self.d1, self.d2, self.d3, self.d4, self.d5, self.d6}

    def dezenas_lista(self):
        return sorted(self.dezenas())

    def dezenas_ordem_lista(self):
        """Ordem original do sorteio (d1–d6), conforme gravada da API Caixa."""
        return [self.d1, self.d2, self.d3, self.d4, self.d5, self.d6]

    @classmethod
    def filtro_base(cls, query, base: str):
        """Sem campo de ganhadores: apenas base geral."""
        return query
