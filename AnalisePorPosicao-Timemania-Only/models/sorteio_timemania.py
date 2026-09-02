from .shared import db

# Lista oficial dos 80 times do coração (numeração 1-80)
TIMES_DO_CORACAO = {
    1: "ABC", 2: "ABC-PE", 3: "Aimoré", 4: "América-MG", 5: "América-RN",
    6: "ASA", 7: "Athletico-PR", 8: "Atlético-GO", 9: "Atlético-MG", 10: "Atlético-PA",
    11: "Avaí", 12: "Bahia", 13: "Bangu", 14: "Barcelona-EC", 15: "Botafogo-PB",
    16: "Botafogo-RJ", 17: "Bragantino", 18: "Brasil de Pelotas", 19: "Brasileirinho",
    20: "Campinense", 21: "Ceará", 22: "Central-PE", 23: "Chapecoense", 24: "CRB",
    25: "Criciúma", 26: "Cruzeiro", 27: "CSA", 28: "Coritiba", 29: "Cuiabá",
    30: "Democracia", 31: "Desportiva-ES", 32: "Duque de Caxias", 33: "Ferroviário-CE",
    34: "Ferroviária-SP", 35: "Figueirense", 36: "Flamengo", 37: "Fluminense",
    38: "Fortaleza", 39: "Goiás", 40: "Guarani", 41: "Grêmio", 42: "Grêmio-PA",
    43: "Internacional", 44: "Ituano", 45: "Joinville", 46: "Juventude", 47: "Juazeirense",
    48: "Londrina", 49: "Mirassol", 50: "Mixto", 51: "Náutico", 52: "Novorizontino",
    53: "Operário-PR", 54: "Paysandu", 55: "Palmeiras", 56: "Paraná Clube",
    57: "Ponte Preta", 58: "Porto Alegrense", 59: "Portuguesa", 60: "Portuguesa-RN",
    61: "Remo", 62: "River-PI", 63: "Sampaio Corrêa", 64: "Santa Cruz", 65: "Santos",
    66: "São Paulo", 67: "São Raimundo-RR", 68: "Serrano-PB", 69: "Sobradinho-DF",
    70: "Sociedade Esportiva do Gama", 71: "Sport", 72: "Tombense", 73: "Treze",
    74: "Tupi", 75: "União-MT", 76: "Vascos da Gama", 77: "Vila Nova",
    78: "Vitória", 79: "Volta Redonda", 80: "03 de Agosto",
}


class SorteioTimemania(db.Model):
    """
    Armazena cada concurso da Timemania.

    ⚽ MECÂNICA ESPECIAL: DEZENAS + TIME DO CORAÇÃO
    ─────────────────────────────────────────────────
    O jogador escolhe:
      • 10 dezenas   de 01 a 80
      • 1 Time do Coração  (1 dos 80 times registrados)

    Sorteiam:
      • 10 dezenas
      • 1 Time do Coração

    Tabela de prêmios:
      10 dez + Time  → Prêmio Principal
      10 dez          → 2º prêmio
       9 dez + Time  → 3º prêmio
       9 dez          → 4º prêmio
       8 dez + Time  → 5º prêmio
       8 dez          → 6º prêmio
       7 dez          → 7º prêmio
       Time (só)      → 8º prêmio
    """
    __tablename__ = 'sorteio_timemania'

    concurso = db.Column(db.Integer, primary_key=True)
    data     = db.Column(db.String(20), nullable=False)

    # Dezenas sorteadas (01-80) — a API Caixa envia 7 (raro: 8); d8–d10 só se vierem na API
    d1  = db.Column(db.Integer, nullable=False)
    d2  = db.Column(db.Integer, nullable=False)
    d3  = db.Column(db.Integer, nullable=False)
    d4  = db.Column(db.Integer, nullable=False)
    d5  = db.Column(db.Integer, nullable=False)
    d6  = db.Column(db.Integer, nullable=False)
    d7  = db.Column(db.Integer, nullable=False)
    d8  = db.Column(db.Integer, nullable=True, default=0)
    d9  = db.Column(db.Integer, nullable=True, default=0)
    d10 = db.Column(db.Integer, nullable=True, default=0)
            
    # Time do Coração sorteado (número 1-80)
    time_num  = db.Column(db.Integer, nullable=False, default=0)
    time_nome = db.Column(db.String(100), nullable=True, default='')

    def __repr__(self):
        return f'<SorteioTimemania {self.concurso}>'

    def dezenas_ordem_lista(self):
        """Ordem original do sorteio (d1–d7+), ignorando zeros/nulos do padding."""
        vals = []
        for i in range(1, 11):
            d = getattr(self, f"d{i}", None)
            if d is not None and 1 <= int(d) <= 80:
                vals.append(int(d))
        return vals

    def dezenas(self):
        return set(self.dezenas_ordem_lista())

    def dezenas_lista(self):
        return sorted(self.dezenas())

    @classmethod
    def filtro_base(cls, query, base: str):
        """Sem campo de ganhadores: apenas base geral."""
        return query
