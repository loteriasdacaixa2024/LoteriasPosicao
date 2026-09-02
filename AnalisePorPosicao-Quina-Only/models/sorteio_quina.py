from .shared import db

class SorteioQuina(db.Model):
    """
    Armazena cada concurso da Quina.
    Quina: 5 dezenas sorteadas de 01 a 80.
    Prêmios: quina (5), quadra (4), terno (3), duque (2).
    """
    __tablename__ = 'sorteio_quina'

    concurso = db.Column(db.Integer, primary_key=True)
    data     = db.Column(db.String(20), nullable=False)

    d1 = db.Column(db.Integer, nullable=False)
    d2 = db.Column(db.Integer, nullable=False)
    d3 = db.Column(db.Integer, nullable=False)
    d4 = db.Column(db.Integer, nullable=False)
    d5 = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<SorteioQuina {self.concurso}>'

    def dezenas(self):
        """Retorna as 5 dezenas como set."""
        return {self.d1, self.d2, self.d3, self.d4, self.d5}

    def dezenas_lista(self):
        """Retorna as 5 dezenas ordenadas."""
        return sorted(self.dezenas())

    def dezenas_ordem_lista(self):
        """Ordem original do sorteio (d1–d5), conforme gravada da API Caixa."""
        return [self.d1, self.d2, self.d3, self.d4, self.d5]

    @classmethod
    def filtro_base(cls, query, base: str):
        """Sem campo de ganhadores: apenas base geral."""
        return query
