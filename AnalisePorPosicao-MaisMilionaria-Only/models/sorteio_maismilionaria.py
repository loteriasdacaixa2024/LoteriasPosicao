from .shared import db

class SorteioMaisMilionaria(db.Model):
    """
    Armazena cada concurso da +Milionária.

    Regras:
      - 50 dezenas (01-50): jogador escolhe 6, sorteiam 6
      - 6 trevos  (01-06): jogador escolhe 2, sorteiam 2

    Tabela de prêmios (combinação dezenas + trevos):
      6 dez + 2 trevos → Prêmio Principal
      6 dez + 1 trevo  → 2º prêmio
      6 dez + 0 trevos → 3º prêmio
      5 dez + 2 trevos → 4º prêmio
      5 dez + 1 trevo  → 5º prêmio
      4 dez + 2 trevos → 6º prêmio
      4 dez + 0 trevos → 7º prêmio (apenas dezenas, sem trevo)
    """
    __tablename__ = 'sorteio_maismilionaria'

    concurso = db.Column(db.Integer, primary_key=True)
    data     = db.Column(db.String(20), nullable=False)

    # 6 dezenas sorteadas (01-50)
    d1 = db.Column(db.Integer, nullable=False)
    d2 = db.Column(db.Integer, nullable=False)
    d3 = db.Column(db.Integer, nullable=False)
    d4 = db.Column(db.Integer, nullable=False)
    d5 = db.Column(db.Integer, nullable=False)
    d6 = db.Column(db.Integer, nullable=False)

    # 2 trevos sorteados (01-06)
    t1 = db.Column(db.Integer, nullable=False)
    t2 = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<SorteioMaisMilionaria {self.concurso}>'

    def dezenas(self):
        """Set das 6 dezenas sorteadas."""
        return {self.d1, self.d2, self.d3, self.d4, self.d5, self.d6}

    def trevos(self):
        """Set dos 2 trevos sorteados."""
        return {self.t1, self.t2}

    def dezenas_lista(self):
        return sorted(self.dezenas())

    def trevos_lista(self):
        return sorted(self.trevos())

    def dezenas_ordem_lista(self):
        """Ordem original do sorteio (d1–d6), conforme gravada da API Caixa."""
        return [self.d1, self.d2, self.d3, self.d4, self.d5, self.d6]

    def trevos_ordem_lista(self):
        """Ordem original dos trevos (t1–t2), conforme gravada da API Caixa."""
        return [self.t1, self.t2]
