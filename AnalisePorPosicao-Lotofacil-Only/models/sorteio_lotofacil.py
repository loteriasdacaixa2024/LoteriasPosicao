from .shared import db

class SorteioLotofacil(db.Model):
    __tablename__ = 'sorteio_lotofacil'
    concurso = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(20), nullable=False)
    posicao_1 = db.Column(db.Integer, nullable=False)
    posicao_2 = db.Column(db.Integer, nullable=False)
    posicao_3 = db.Column(db.Integer, nullable=False)
    posicao_4 = db.Column(db.Integer, nullable=False)
    posicao_5 = db.Column(db.Integer, nullable=False)
    posicao_6 = db.Column(db.Integer, nullable=False)
    posicao_7 = db.Column(db.Integer, nullable=False)
    posicao_8 = db.Column(db.Integer, nullable=False)
    posicao_9 = db.Column(db.Integer, nullable=False)
    posicao_10 = db.Column(db.Integer, nullable=False)
    posicao_11 = db.Column(db.Integer, nullable=False)
    posicao_12 = db.Column(db.Integer, nullable=False)
    posicao_13 = db.Column(db.Integer, nullable=False)
    posicao_14 = db.Column(db.Integer, nullable=False)
    posicao_15 = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<SorteioLotofacil {self.concurso}>'

    def dezenas(self):
        # -----------------------------------------------------
        # TRAVA DE ESTADO (DO NOT CHANGE) / NÃO ORDENAR NUNCA
        # -----------------------------------------------------
        # A regra de negócios mestre exige que NÃO SEJA FEITO SORT.
        # Os números devem ser listados EXATAMENTE NA MESMA ORDEM em que 
        # caíram do globo ou que vieram da API (posição_1 até a posição_15).
        # Jamais coloque wrap de `sorted(...)` neste return!
        return [getattr(self, f'posicao_{i}') for i in range(1, 16)]

    def dezenas_lista(self):
        return sorted(self.dezenas())

    def dezenas_ordem_lista(self):
        """Ordem original do sorteio (posição_1–15), conforme gravada da API Caixa."""
        return self.dezenas()

    @classmethod
    def filtro_base(cls, query, base: str):
        """Sem campo de ganhadores: apenas base geral."""
        return query
