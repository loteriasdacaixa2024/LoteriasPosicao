from .shared import db

class SorteioLotomania(db.Model):
    """
    Armazena cada concurso da Lotomania.
    Lotomania: sorteiam 20 dezenas de 00 a 99.
    Armazenamos as 20 dezenas sorteadas em ordem de sorteio.

    REGRA: dezenas gravadas conforme API (sem reordenação).
    Prêmios: 20, 19, 18, 17, 16, 15 acertos ou 0 acertos (quina).
    """
    __tablename__ = 'sorteio_lotomania'

    concurso = db.Column(db.Integer, primary_key=True)
    data     = db.Column(db.String(20), nullable=False)

    # 20 dezenas sorteadas (00-99)
    d01 = db.Column(db.Integer, nullable=False)
    d02 = db.Column(db.Integer, nullable=False)
    d03 = db.Column(db.Integer, nullable=False)
    d04 = db.Column(db.Integer, nullable=False)
    d05 = db.Column(db.Integer, nullable=False)
    d06 = db.Column(db.Integer, nullable=False)
    d07 = db.Column(db.Integer, nullable=False)
    d08 = db.Column(db.Integer, nullable=False)
    d09 = db.Column(db.Integer, nullable=False)
    d10 = db.Column(db.Integer, nullable=False)
    d11 = db.Column(db.Integer, nullable=False)
    d12 = db.Column(db.Integer, nullable=False)
    d13 = db.Column(db.Integer, nullable=False)
    d14 = db.Column(db.Integer, nullable=False)
    d15 = db.Column(db.Integer, nullable=False)
    d16 = db.Column(db.Integer, nullable=False)
    d17 = db.Column(db.Integer, nullable=False)
    d18 = db.Column(db.Integer, nullable=False)
    d19 = db.Column(db.Integer, nullable=False)
    d20 = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<SorteioLotomania {self.concurso}>'

    def dezenas(self):
        """Retorna as 20 dezenas como set para comparação rápida."""
        return {getattr(self, f'd{i:02d}') for i in range(1, 21)}

    def dezenas_lista(self):
        """Retorna as 20 dezenas como lista ordenada."""
        return sorted(self.dezenas())

    def dezenas_ordem_lista(self):
        """Ordem original do sorteio (d01–d20), conforme gravada da API Caixa."""
        return [getattr(self, f'd{i:02d}') for i in range(1, 21)]

    @classmethod
    def filtro_base(cls, query, base: str):
        """Sem campo de ganhadores: apenas base geral."""
        return query
