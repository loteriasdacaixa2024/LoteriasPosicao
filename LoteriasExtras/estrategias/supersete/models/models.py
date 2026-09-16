"""
SuperSet Estratégia 1 — Modelos do Banco de Dados
===================================================
Define as tabelas SQLAlchemy para persistência.
Banco: SQLite (data/superset.db)
"""

import json
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class AppState(db.Model):
    """
    Estado global da aplicação.
    Armazena a sequência atual, modo híbrido e contador de matrizes.
    """
    __tablename__ = "app_state"

    id = db.Column(db.Integer, primary_key=True)
    current_sequence = db.Column(db.Text, default="[]")
    hybrid_mode = db.Column(db.Boolean, default=False)
    matrix_counter = db.Column(db.Integer, default=0)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def get_sequence(self):
        """Retorna a sequência como lista Python."""
        if self.current_sequence:
            return json.loads(self.current_sequence)
        return []

    def set_sequence(self, seq):
        """Define a sequência a partir de uma lista Python."""
        self.current_sequence = json.dumps(seq)

    def to_dict(self):
        return {
            "sequence": self.get_sequence(),
            "hybridMode": self.hybrid_mode,
            "matrixCounter": self.matrix_counter,
        }


class Matrix(db.Model):
    """
    Representa uma matriz de análise estratégica.
    Cada matriz é independente, com seu próprio resultado e configuração.
    """
    __tablename__ = "matrices"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    strategy_type = db.Column(db.Integer, default=1) # 1 = Rotacional, 2 = Núcleo Histórico
    sequence = db.Column(db.Text, default="[]")
    start_col = db.Column(db.Integer, default=0)
    result = db.Column(db.Text, default='[null,null,null,null,null,null,null]')
    concurso = db.Column(db.String(20), default="")
    hits_count = db.Column(db.Integer, default=0)
    best_row = db.Column(db.Integer, default=-1)
    intensity = db.Column(db.String(20), default="Média")
    is_hybrid = db.Column(db.Boolean, default=False)
    grid_data = db.Column(db.Text, nullable=True) # JSON da matriz completa para estratégias não-calculadas
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_sequence(self):
        """Retorna a sequência como lista Python."""
        if self.sequence:
            return json.loads(self.sequence)
        return []

    def set_sequence(self, seq):
        """Define a sequência a partir de uma lista Python."""
        self.sequence = json.dumps(seq)

    def get_result(self):
        """Retorna o resultado como lista Python (pode conter None)."""
        if self.result:
            return json.loads(self.result)
        return [None] * 7

    def set_result(self, res):
        """Define o resultado a partir de uma lista Python."""
        self.result = json.dumps(res)

    def get_grid(self):
        """Retorna a grade completa se existir (Estratégia 2+)."""
        if self.grid_data:
            return json.loads(self.grid_data)
        return None

    def set_grid(self, grid):
        """Define a grade completa."""
        self.grid_data = json.dumps(grid)

    def to_dict(self):
        data = {
            "id": self.id,
            "name": self.name,
            "strategy_type": self.strategy_type,
            "intensity": self.intensity,
            "isHybrid": self.is_hybrid,
            "sequence": self.get_sequence(),
            "startCol": self.start_col,
            "result": self.get_result(),
            "concurso": self.concurso,
            "hitsCount": self.hits_count,
            "bestRow": self.best_row,
            "grid": self.get_grid(),
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "hasGrid": self.grid_data is not None
        }
        
        # Tenta buscar o rateio real se houver concurso vinculado
        if self.concurso:
            try:
                # Import sub-local to avoid potential circular issues if any
                from models.models import Result
                res_obj = Result.query.filter_by(concurso=int(self.concurso)).first()
                if res_obj:
                    data["rateioDetail"] = res_obj.get_rateio()
            except:
                pass
        
        return data


class Result(db.Model):
    """
    Resultados reais dos sorteios da Caixa.
    """
    __tablename__ = "results"

    id = db.Column(db.Integer, primary_key=True)
    concurso = db.Column(db.Integer, unique=True, nullable=False)
    data = db.Column(db.String(20))
    
    # 7 colunas separadas para os resultados
    col0 = db.Column(db.Integer)
    col1 = db.Column(db.Integer)
    col2 = db.Column(db.Integer)
    col3 = db.Column(db.Integer)
    col4 = db.Column(db.Integer)
    col5 = db.Column(db.Integer)
    col6 = db.Column(db.Integer)

    acumulado = db.Column(db.Boolean, default=False)
    valor_acumulado = db.Column(db.Float, default=0.0)
    estimativa_proximo = db.Column(db.Float, default=0.0)
    data_proximo = db.Column(db.String(20))
    rateio = db.Column(db.Text) # JSON list of prize tiers
    arrecadacao = db.Column(db.Float, default=0.0)
    
    # Novos campos detalhados
    local_sorteio = db.Column(db.String(100))
    nome_municipio_uf_sorteio = db.Column(db.String(100))
    valor_total_premio_faixa_um = db.Column(db.Float, default=0.0)
    valor_saldo_reserva_garantidora = db.Column(db.Float, default=0.0)
    indicador_concurso_especial = db.Column(db.Integer)
    observacao = db.Column(db.Text)

    def get_dezenas(self):
        return [self.col0, self.col1, self.col2, self.col3, self.col4, self.col5, self.col6]

    def set_dezenas(self, dezenas_list):
        if len(dezenas_list) >= 7:
            self.col0 = dezenas_list[0]
            self.col1 = dezenas_list[1]
            self.col2 = dezenas_list[2]
            self.col3 = dezenas_list[3]
            self.col4 = dezenas_list[4]
            self.col5 = dezenas_list[5]
            self.col6 = dezenas_list[6]

    def get_rateio(self):
        return json.loads(self.rateio) if self.rateio else []

    def set_rateio(self, rateio_list):
        self.rateio = json.dumps(rateio_list)

    def to_dict(self):
        return {
            "concurso": self.concurso,
            "data": self.data,
            "dezenas": self.get_dezenas(),
            "acumulado": self.acumulado,
            "valorAcumulado": self.valor_acumulado,
            "estimativaProximo": self.estimativa_proximo,
            "dataProximo": self.data_proximo,
            "rateio": self.get_rateio(),
            "arrecadacao": self.arrecadacao,
            "localSorteio": self.local_sorteio,
            "municipio": self.nome_municipio_uf_sorteio,
            "premioFaixa1": self.valor_total_premio_faixa_um
        }

class AnalysisExecution(db.Model):
    """
    Tabela para salvar as execuções de análises estatísticas (Módulo de Análises).
    """
    __tablename__ = "super7_analises_execucoes"

    id = db.Column(db.Integer, primary_key=True)
    tipo_analise = db.Column(db.String(50)) # ex: 'composicao', 'colunas', 'repeticao'
    parametros = db.Column(db.Text) # JSON params
    data_execucao = db.Column(db.DateTime, default=datetime.utcnow)
    resultado_resumido = db.Column(db.Text) # JSON results
    periodo_analisado = db.Column(db.String(100)) # ex: 'Últimos 100' ou '1-500'

    def to_dict(self):
        return {
            "id": self.id,
            "tipoAnalise": self.tipo_analise,
            "dataExecucao": self.data_execucao.isoformat() if self.data_execucao else None,
            "resultado": json.loads(self.resultado_resumido) if self.resultado_resumido else {},
            "periodo": self.periodo_analisado
        }
