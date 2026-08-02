from .shared import db

class SorteiosDuplaSena(db.Model):
    """
    Armazena cada concurso da Dupla Sena.

    ⚠️ MECÂNICA ESPECIAL: UMA APOSTA → DOIS SORTEIOS
    ─────────────────────────────────────────────────
    Ao fazer uma aposta de 6 dezenas (01–50), ela concorre
    automaticamente a DOIS sorteios distintos no mesmo concurso:

      • 1º Sorteio (s1_d1 … s1_d6): primeiras 6 dezenas sorteadas
      • 2º Sorteio (s2_d1 … s2_d6): segundas 6 dezenas sorteadas

    A mesma aposta pode ganhar em um ou nos dois sorteios.

    Tabela de prêmios (por sorteio):
      Sena  → 6 acertos
      Quina → 5 acertos
      Quadra→ 4 acertos
    """
    __tablename__ = 'sorteio_duplasena'

    concurso = db.Column(db.Integer, primary_key=True)
    data     = db.Column(db.String(20), nullable=False)

    # 1º Sorteio — 6 dezenas (01-50)
    s1_d1 = db.Column(db.Integer, nullable=False)
    s1_d2 = db.Column(db.Integer, nullable=False)
    s1_d3 = db.Column(db.Integer, nullable=False)
    s1_d4 = db.Column(db.Integer, nullable=False)
    s1_d5 = db.Column(db.Integer, nullable=False)
    s1_d6 = db.Column(db.Integer, nullable=False)

    # 2º Sorteio — 6 dezenas (01-50)
    s2_d1 = db.Column(db.Integer, nullable=False)
    s2_d2 = db.Column(db.Integer, nullable=False)
    s2_d3 = db.Column(db.Integer, nullable=False)
    s2_d4 = db.Column(db.Integer, nullable=False)
    s2_d5 = db.Column(db.Integer, nullable=False)
    s2_d6 = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<SorteiosDuplaSena {self.concurso}>'

    def sorteio1(self):
        """Set das 6 dezenas do 1º sorteio."""
        return {self.s1_d1, self.s1_d2, self.s1_d3, self.s1_d4, self.s1_d5, self.s1_d6}

    def sorteio2(self):
        """Set das 6 dezenas do 2º sorteio."""
        return {self.s2_d1, self.s2_d2, self.s2_d3, self.s2_d4, self.s2_d5, self.s2_d6}

    def sorteio1_lista(self):
        return sorted(self.sorteio1())

    def sorteio2_lista(self):
        return sorted(self.sorteio2())

    def sorteio1_ordem_lista(self):
        """Ordem original do 1º sorteio (s1_d1–s1_d6)."""
        return [self.s1_d1, self.s1_d2, self.s1_d3, self.s1_d4, self.s1_d5, self.s1_d6]

    def sorteio2_ordem_lista(self):
        """Ordem original do 2º sorteio (s2_d1–s2_d6)."""
        return [self.s2_d1, self.s2_d2, self.s2_d3, self.s2_d4, self.s2_d5, self.s2_d6]

    def dezenas(self):
        """Compatível com análises genéricas — usa o 1º sorteio."""
        return self.sorteio1()

    def dezenas_lista(self):
        return self.sorteio1_lista()

    def dezenas_ordem_lista(self):
        """Perfil Escolha/Tubular e estudos — 1º sorteio (ordem oficial)."""
        return self.sorteio1_ordem_lista()

    def todas_dezenas(self):
        """Union de ambos os sorteios (para análise de frequência combinada)."""
        return self.sorteio1() | self.sorteio2()
