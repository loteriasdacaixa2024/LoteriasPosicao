from .shared import db

class SorteioSuperSete(db.Model):
    """
    Armazena cada concurso da Super Sete.
    A Super Sete tem 7 colunas, cada uma com um dígito de 0-9.
    Os dígitos são gravados NA ORDEM EXATA DE SORTEIO (coluna 1 a 7).

    TRAVA DE INTEGRIDADE (NÃO ALTERAR):
    Jamais ordenar ou rearranjar os dígitos — a posição é a própria
    identidade analítica do jogo.
    """
    __tablename__ = 'sorteio_supersete'

    concurso  = db.Column(db.Integer, primary_key=True)
    data      = db.Column(db.String(20), nullable=False)

    # 7 colunas, dígitos 0-9
    coluna_1  = db.Column(db.Integer, nullable=False)
    coluna_2  = db.Column(db.Integer, nullable=False)
    coluna_3  = db.Column(db.Integer, nullable=False)
    coluna_4  = db.Column(db.Integer, nullable=False)
    coluna_5  = db.Column(db.Integer, nullable=False)
    coluna_6  = db.Column(db.Integer, nullable=False)
    coluna_7  = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<SorteioSuperSete {self.concurso}>'

    def digitos(self):
        # -------------------------------------------------------
        # TRAVA DE ESTADO — NÃO ORDENAR NUNCA
        # Retorna os 7 dígitos na ordem posicional das colunas.
        # -------------------------------------------------------
        return [getattr(self, f'coluna_{i}') for i in range(1, 8)]

    def digitos_ordem_lista(self):
        """Ordem original do sorteio (coluna_1–7), conforme gravada da API Caixa."""
        return self.digitos()

    def dezenas(self):
        """Lista posicional C1–C7 (repetições preservadas). Preferir digitos()."""
        return list(self.digitos())

    @classmethod
    def filtro_base(cls, query, base: str):
        """Sem campo de ganhadores: apenas base geral."""
        return query
