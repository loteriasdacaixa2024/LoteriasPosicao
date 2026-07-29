from .shared import db

MESES_DO_ANO = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

MESES_ABREV = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}


def mes_abrev_de(mes_num=None, mes_nome=None) -> str:
    if mes_num and 1 <= int(mes_num) <= 12:
        return MESES_ABREV[int(mes_num)]
    if mes_nome:
        for num, nome in MESES_DO_ANO.items():
            if nome == mes_nome:
                return MESES_ABREV[num]
    return (mes_nome or "?")[:3]

class SorteioDiaDeSorte(db.Model):
    """
    Armazena cada concurso do Dia de Sorte.

    📅 MECÂNICA: 31 DEZENAS + 1 MÊS DA SORTE
    ─────────────────────────────────────────────────
    O jogador escolhe 7 dezenas (01-31) e 1 Mês (1-12).
    Sorteiam 7 dezenas e 1 Mês.

    Prêmios:
    - 7 acertos (prêmio principal)
    - 6 acertos
    - 5 acertos
    - 4 acertos
    - Mês de Sorte (prêmio fixo, acumula com acertos nas dezenas)
    """
    __tablename__ = 'sorteio_diadesorte'

    concurso = db.Column(db.Integer, primary_key=True)
    data     = db.Column(db.String(20), nullable=False)

    # 7 dezenas sorteadas (01-31)
    d1 = db.Column(db.Integer, nullable=False)
    d2 = db.Column(db.Integer, nullable=False)
    d3 = db.Column(db.Integer, nullable=False)
    d4 = db.Column(db.Integer, nullable=False)
    d5 = db.Column(db.Integer, nullable=False)
    d6 = db.Column(db.Integer, nullable=False)
    d7 = db.Column(db.Integer, nullable=False)

    # Mês da Sorte (1-12)
    mes_num  = db.Column(db.Integer, nullable=False, default=0)
    mes_nome = db.Column(db.String(20), nullable=True, default='')

    # Faixa principal: quantidade de ganhadores com 7 acertos (API Caixa).
    # NULL = ainda não preenchido (backfill pendente).
    # 0 = concurso acumulado (sem ganhador na faixa principal).
    # >= 1 = concurso com pelo menos um ganhador na faixa principal.
    ganhadores_7 = db.Column(db.Integer, nullable=True, index=True)

    def __repr__(self):
        return f'<SorteioDiaDeSorte {self.concurso}>'

    def teve_ganhador_7(self) -> bool:
        return self.ganhadores_7 is not None and self.ganhadores_7 >= 1

    def eh_acumulado_7(self) -> bool:
        return self.ganhadores_7 is not None and self.ganhadores_7 == 0

    def base_comportamento(self):
        """Classificação para análise: geral usa todos; demais exigem ganhadores_7 preenchido."""
        if self.ganhadores_7 is None:
            return None
        return "vencedores" if self.ganhadores_7 >= 1 else "acumulados"

    @classmethod
    def filtro_base(cls, query, base: str):
        """Filtra query por base estatística (geral | vencedores | acumulados)."""
        base = (base or "geral").strip().lower()
        if base == "vencedores":
            return query.filter(cls.ganhadores_7 >= 1)
        if base == "acumulados":
            return query.filter(cls.ganhadores_7 == 0)
        return query

    def dezenas(self):
        return {self.d1, self.d2, self.d3, self.d4, self.d5, self.d6, self.d7}

    def dezenas_lista(self):
        return sorted(self.dezenas())

    def dezenas_ordem_lista(self):
        """Ordem original do sorteio (d1–d7), conforme gravada da API Caixa."""
        return [self.d1, self.d2, self.d3, self.d4, self.d5, self.d6, self.d7]

    def mes_abrev(self) -> str:
        return mes_abrev_de(self.mes_num, self.mes_nome)
