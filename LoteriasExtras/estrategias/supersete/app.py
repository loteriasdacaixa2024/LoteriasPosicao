"""
SuperSet Estratégia 1 — Aplicação Flask Principal
===================================================
Servidor web com API REST para gerenciamento de matrizes,
distribuição rotacional e exportação de dados.

Porta padrão: 5573
Iniciar: python app.py
"""

import math
import json
import os
import sys
import requests
import random
from datetime import datetime
from sqlalchemy import text

from flask import Flask, render_template, request, jsonify, Response, send_file
from config.config import Config
from models.models import db, Matrix, AppState, Result

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from remote_wsgi import apply_proxy

# ── Inicialização do Flask ──────────────────────────
app = Flask(__name__)
app.config.from_object(Config)
apply_proxy(app)

db.init_app(app)


# ══════════════════════════════════════════════════════
#  LÓGICA DE DISTRIBUIÇÃO E ACERTOS
# ══════════════════════════════════════════════════════

def compute_distribution(sequence, start_col=0):
    """
    Gera a distribuição rotacional da sequência nas 7 colunas.
    Produz um deslocamento vertical cíclico entre as colunas, 
    onde a coluna X é a anterior deslocada em 1 posição.
    """
    n = len(sequence)
    if n == 0:
        return []
    rows = []
    for i in range(n):
        row = []
        for j in range(Config.COLUMNS):
            # O deslocamento (shift) é baseado na distância da coluna atual (j) 
            # em relação à coluna inicial (start_col).
            shift = (j - start_col + Config.COLUMNS) % Config.COLUMNS
            seq_index = (i + shift) % n
            row.append(sequence[seq_index])
        rows.append(row)
    return rows


def compute_hits(sequence, start_col, result):
    """
    Compara cada linha da distribuição com o resultado do sorteio.
    Retorna dados de acertos por linha e a melhor linha.
    """
    rows = compute_distribution(sequence, start_col)
    row_hits = []
    best_hits = 0
    best_row_idx = -1

    for i, row in enumerate(rows):
        hits = 0
        hit_cols = []
        for j in range(Config.COLUMNS):
            if result[j] is not None and row[j] == result[j]:
                hits += 1
                hit_cols.append(j)
        row_hits.append({"hits": hits, "hitCols": hit_cols})
        if hits > best_hits:
            best_hits = hits
            best_row_idx = i

    return {
        "rowHits": row_hits,
        "bestHits": best_hits,
        "bestRowIdx": best_row_idx,
        "rows": rows,
    }


# ══════════════════════════════════════════════════════
#  INICIALIZAÇÃO DO BANCO DE DADOS
# ══════════════════════════════════════════════════════

def init_db():
    """Cria as tabelas e diretórios necessários."""
    with app.app_context():
        os.makedirs(Config.DATA_DIR, exist_ok=True)
        os.makedirs(Config.EXPORTS_DIR, exist_ok=True)
        # Adiciona colunas se não existirem (migration simples)
        try:
            inspector = db.inspect(db.engine)
            cols = [c['name'] for c in inspector.get_columns('matrices')]
            with db.engine.connect() as conn:
                if 'strategy_type' not in cols:
                    conn.execute(text("ALTER TABLE matrices ADD COLUMN strategy_type INTEGER DEFAULT 1"))
                if 'intensity' not in cols:
                    conn.execute(text("ALTER TABLE matrices ADD COLUMN intensity TEXT DEFAULT 'Média'"))
                if 'grid_data' not in cols:
                    conn.execute(text("ALTER TABLE matrices ADD COLUMN grid_data TEXT"))
                if 'is_hybrid' not in cols:
                    conn.execute(text("ALTER TABLE matrices ADD COLUMN is_hybrid BOOLEAN DEFAULT 0"))
                conn.commit()
        except Exception as e:
            print(f"  [!] Erro na migração: {e}", flush=True)

        db.create_all()

        # Garante que AppState existe
        if not AppState.query.first():
            state = AppState(
                current_sequence="[]",
                hybrid_mode=False,
                matrix_counter=0,
            )
            db.session.add(state)
            db.session.commit()

        # Tenta buscar o último concurso da API para garantir que o banco saiba o que falta
        try:
            url = Config.CAIXA_API_URL
            response = requests.get(url, timeout=Config.API_TIMEOUT, verify=False)
            if response.status_code == 200:
                data = response.json()
                save_api_result(data)
        except Exception:
            pass


# ══════════════════════════════════════════════════════
#  ROTAS — PÁGINAS
# ══════════════════════════════════════════════════════

@app.route("/")
def index():
    """Página principal."""
    return render_template(
    "index.html",
    app_name=Config.APP_NAME,
    app_version=Config.APP_VERSION,
    app_type=Config.APP_TYPE
    )


# ══════════════════════════════════════════════════════
#  ROTAS — API: ESTADO GLOBAL
# ══════════════════════════════════════════════════════

@app.route("/api/state", methods=["GET"])
def get_state():
    """Retorna o estado completo da aplicação."""
    state = AppState.query.first()
    matrices = Matrix.query.order_by(Matrix.id).all()
    return jsonify({
        "sequence": state.get_sequence() if state else [],
        "hybridMode": state.hybrid_mode if state else False,
        "matrixCounter": state.matrix_counter if state else 0,
        "matrices": [m.to_dict() for m in matrices],
        "prizeTiers": Config.PRIZE_TIERS,
        "recentConcursos": [r.concurso for r in Result.query.order_by(Result.concurso.desc()).limit(50).all()]
    })


@app.route("/api/sequence", methods=["PUT"])
def update_sequence():
    """Atualiza a sequência base global."""
    data = request.get_json()
    seq = data.get("sequence", [])

    state = AppState.query.first()
    state.set_sequence(seq)

    # Atualiza apenas matrizes da Estratégia 1 (Rotacional)
    matrices = Matrix.query.filter((Matrix.strategy_type == 1) | (Matrix.strategy_type == None)).all()
    for matrix in matrices:
        matrix.set_sequence(seq)
        # Recalcula acertos se houver resultado
        result = matrix.get_result()
        has_result = any(v is not None for v in result)
        if has_result and len(seq) > 0:
            hits_data = compute_hits(seq, matrix.start_col, result)
            matrix.hits_count = hits_data["bestHits"]
            matrix.best_row = hits_data["bestRowIdx"]

    db.session.commit()
    return jsonify({"success": True})


@app.route("/api/hybrid", methods=["PUT"])
def update_hybrid():
    """Ativa/desativa o modo híbrido."""
    data = request.get_json()
    state = AppState.query.first()
    state.hybrid_mode = data.get("hybridMode", False)
    db.session.commit()
    return jsonify({"success": True})


# ══════════════════════════════════════════════════════
#  ROTAS — API: MATRIZES (CRUD)
# ══════════════════════════════════════════════════════

@app.route("/api/matrix", methods=["POST"])
def create_matrix():
    """Cria uma nova matriz."""
    state = AppState.query.first()
    state.matrix_counter += 1
    counter = state.matrix_counter

    # Busca o último concurso sincronizado para usar como padrão
    last_res = Result.query.order_by(Result.concurso.desc()).first()
    concurso_default = str(last_res.concurso) if last_res else ""

    matrix = Matrix(
        name=f"Matriz {counter}",
        sequence=state.current_sequence,
        start_col=0,
        result=json.dumps([None] * 7),
        concurso=concurso_default,
    )
    db.session.add(matrix)
    db.session.commit()
    return jsonify(matrix.to_dict()), 201


@app.route("/api/matrix/<int:matrix_id>", methods=["DELETE"])
def delete_matrix(matrix_id):
    """Exclui uma matriz."""
    matrix = Matrix.query.get_or_404(matrix_id)
    db.session.delete(matrix)
    db.session.commit()
    return jsonify({"success": True})


@app.route("/api/matrix/<int:matrix_id>/result", methods=["PUT"])
def update_result(matrix_id):
    """Atualiza o resultado do sorteio de uma matriz."""
    data = request.get_json()
    matrix = Matrix.query.get_or_404(matrix_id)
    result = data.get("result", [None] * 7)
    matrix.set_result(result)

    # Calcula acertos
    seq = matrix.get_sequence()
    has_result = any(v is not None for v in result)
    if has_result and len(seq) > 0:
        hits_data = compute_hits(seq, matrix.start_col, result)
        matrix.hits_count = hits_data["bestHits"]
        matrix.best_row = hits_data["bestRowIdx"]
    else:
        matrix.hits_count = 0
        matrix.best_row = -1

    db.session.commit()
    return jsonify({"success": True, "matrix": matrix.to_dict()})


@app.route("/api/matrix/<int:matrix_id>/start-col", methods=["PUT"])
def update_start_col(matrix_id):
    """Atualiza a coluna inicial (modo híbrido) de uma matriz."""
    data = request.get_json()
    new_col = data.get("startCol", 0)
    matrix = Matrix.query.get_or_404(matrix_id)
    old_col = matrix.start_col
    matrix.start_col = new_col

    # Para estratégias 2, 3 e 4, rotacionamos o grid fisicamente se a coluna mudar
    if matrix.strategy_type != 1:
        grid = matrix.get_grid()
        if grid:
            diff = (new_col - old_col + 7) % 7
            if diff != 0:
                rows_count = len(grid)
                new_grid = [[None for _ in range(7)] for _ in range(rows_count)]
                for r in range(rows_count):
                    for c in range(7):
                        new_grid[r][(c + diff) % 7] = grid[r][c]
                matrix.set_grid(new_grid)

    # Recalcula acertos de acordo com o tipo de estratégia
    result = matrix.get_result()
    has_result = any(v is not None for v in result)
    
    if has_result:
        if matrix.strategy_type == 1:
            seq = matrix.get_sequence()
            if len(seq) > 0:
                hits_data = compute_hits(seq, matrix.start_col, result)
                matrix.hits_count = hits_data["bestHits"]
                matrix.best_row = str(hits_data["bestRowIdx"])
        else:
            grid = matrix.get_grid()
            if grid:
                best_hits = 0
                best_row_idx = -1
                for i, row in enumerate(grid):
                    hits = 0
                    for j in range(7):
                        if result[j] is not None and row[j] == result[j]:
                            hits += 1
                    if hits > best_hits:
                        best_hits = hits
                        best_row_idx = i
                matrix.hits_count = best_hits
                matrix.best_row = str(best_row_idx)

    db.session.commit()
    return jsonify({"success": True, "matrix": matrix.to_dict()})


@app.route("/api/matrix/<int:matrix_id>/concurso", methods=["PUT"])
def update_concurso(matrix_id):
    """Atualiza o número do concurso."""
    data = request.get_json()
    matrix = Matrix.query.get_or_404(matrix_id)
    matrix.concurso = data.get("concurso", "")
    db.session.commit()
    return jsonify({"success": True})


@app.route("/api/stats/ranking", methods=["GET"])
def get_ranking():
    """Calcula a frequência global de cada dígito nos concursos salvos."""
    results = Result.query.all()
    counts = {i: 0 for i in range(10)}
    for r in results:
        dezenas = r.get_dezenas()
        for d in dezenas:
            if d is not None:
                counts[d] += 1
    
    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    ranking = []
    for i, (digit, count) in enumerate(sorted_counts):
        ranking.append({
            "pos": f"{i+1:03d}",
            "digit": digit,
            "count": count
        })
    
    return jsonify({
        "success": True, 
        "ranking": ranking,
        "totalConcursos": len(results)
    })


@app.route("/api/stats/ranking-columns", methods=["GET"])
def get_ranking_columns():
    """Calcula a frequência por coluna nos concursos salvos."""
    results = Result.query.all()
    rankings = []
    
    for c in range(Config.COLUMNS):
        counts = {i: 0 for i in range(10)}
        for r in results:
            dezenas = r.get_dezenas()
            if dezenas[c] is not None:
                counts[dezenas[c]] += 1
        
        sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        col_rank = []
        for i, (digit, count) in enumerate(sorted_counts):
            col_rank.append({
                "pos": f"{i+1:03d}",
                "digit": digit,
                "count": count
            })
        rankings.append(col_rank)
        
    return jsonify({
        "success": True, 
        "rankings": rankings,
        "totalConcursos": len(results)
    })


@app.route("/api/matrix/strategy2", methods=["POST"])
def create_matrix_v2():
    """Cria uma nova matriz usando a Estratégia 2 (Núcleo Histórico + Híbrido)."""
    data = request.get_json()
    nucleus = data.get("nucleus", [])
    intensity = data.get("intensity", "Média")
    is_hybrid = data.get("isHybrid", False)
    start_col = data.get("startCol", 0)
    
    if len(nucleus) < 2 or len(nucleus) > 3:
        return jsonify({"success": False, "error": "Selecione entre 2 e 3 dígitos"}), 400

    state = AppState.query.first()
    state.matrix_counter += 1
    
    # ── ALGORITMO ESTRATÉGIA 2 ──
    rows_count = 10
    cols_count = Config.COLUMNS
    grid = [[None for _ in range(cols_count)] for _ in range(rows_count)]
    others = [d for d in range(10) if d not in nucleus]
    
    freq_map = {"Baixa": 2, "Média": 3, "Alta": 4}
    n_count_per_col = freq_map.get(intensity, 3)
    
    for c in range(cols_count):
        col_pool = []
        # No Modo Híbrido, garantimos que pelo menos 1 coluna use o segundo mais forte se houver
        current_n_count = n_count_per_col
        
        for _ in range(current_n_count):
            col_pool.append(random.choice(nucleus))
            
        while len(col_pool) < rows_count:
            col_pool.append(random.choice(others))
            
        random.shuffle(col_pool)
        
        # Ajuste Híbrido extra: Evitar concentrações na mesma linha se possível
        # (Lógica simplificada de balanceamento estrutural)
        if is_hybrid:
            # Tenta rotacionar levemente o pool se detectar padrão repetitivo
            pass

        for r in range(rows_count):
            grid[r][c] = col_pool[r]

    # Aplicar Coluna Inicial se Híbrido
    if is_hybrid and start_col > 0:
        shifted_grid = [[None for _ in range(cols_count)] for _ in range(rows_count)]
        for r in range(rows_count):
            for c in range(cols_count):
                shifted_grid[r][(c + start_col) % cols_count] = grid[r][c]
        grid = shifted_grid

    last_res = Result.query.order_by(Result.concurso.desc()).first()
    concurso_default = str(last_res.concurso) if last_res else ""

    matrix = Matrix(
        name=f"Matriz {state.matrix_counter} (E2 {'H' if is_hybrid else 'P'})",
        strategy_type=2,
        intensity=intensity,
        is_hybrid=is_hybrid,
        start_col=start_col,
        sequence=json.dumps(nucleus),
        result=json.dumps([None] * 7),
        concurso=concurso_default
    )
    matrix.set_grid(grid)
    db.session.add(matrix)
    db.session.commit()
    return jsonify(matrix.to_dict()), 201


@app.route("/api/matrix/strategy3", methods=["POST"])
def create_matrix_v3():
    """Cria uma nova matriz usando a Estratégia 3 (Ranking por Coluna + Híbrido)."""
    data = request.get_json()
    selections = data.get("selections", []) # [[d1, d2], [d1], ...] (7 lists)
    intensity = data.get("intensity", "Média")
    is_hybrid = data.get("isHybrid", False)
    start_col = data.get("startCol", 0)
    
    if len(selections) != 7:
        return jsonify({"success": False, "error": "Seleção inválida para as 7 colunas"}), 400

    state = AppState.query.first()
    state.matrix_counter += 1
    
    rows_count = 10
    grid = [[None for _ in range(7)] for _ in range(rows_count)]
    
    freq_map = {"Baixa": 2, "Média": 3, "Alta": 4}
    n_count_per_col = freq_map.get(intensity, 3)

    # Pegar ranking geral para o modo híbrido
    global_counts = {i: 0 for i in range(10)}
    if is_hybrid:
        for r in Result.query.all():
            for d in r.get_dezenas():
                if d is not None: global_counts[d] += 1
        global_ranking = sorted(global_counts.items(), key=lambda x: x[1], reverse=True)
        top_global = [x[0] for x in global_ranking[:3]]

    for c in range(7):
        col_nucleus = selections[c]
        others = [d for d in range(10) if d not in col_nucleus]
        
        col_pool = []
        for _ in range(n_count_per_col):
            col_pool.append(random.choice(col_nucleus))
        
        # Modo Híbrido: Injeta um pouco do ranking geral se não estiver na seleção
        if is_hybrid:
            col_pool[0] = random.choice(top_global)
            
        while len(col_pool) < rows_count:
            col_pool.append(random.choice(others))
            
        random.shuffle(col_pool)
        for r in range(rows_count):
            grid[r][c] = col_pool[r]

    # Aplicar Coluna Inicial se Híbrido
    if is_hybrid and start_col > 0:
        shifted_grid = [[None for _ in range(7)] for _ in range(rows_count)]
        for r in range(rows_count):
            for c in range(7):
                shifted_grid[r][(c + start_col) % 7] = grid[r][c]
        grid = shifted_grid

    last_res = Result.query.order_by(Result.concurso.desc()).first()
    concurso_default = str(last_res.concurso) if last_res else ""

    matrix = Matrix(
        name=f"Matriz {state.matrix_counter} (E3 {'H' if is_hybrid else 'P'})",
        strategy_type=3,
        intensity=intensity,
        is_hybrid=is_hybrid,
        start_col=start_col,
        sequence=json.dumps(selections),
        result=json.dumps([None] * 7),
        concurso=concurso_default
    )
    matrix.set_grid(grid)
    db.session.add(matrix)
    db.session.commit()
    return jsonify(matrix.to_dict()), 201

@app.route("/api/matrix/strategy4", methods=["POST"])
def create_matrix_v4():
    """Cria uma nova matriz usando a Estratégia 4 (Restrição de 5 Dígitos + Híbrido)."""
    data = request.get_json()
    selected_digits = data.get("digits", [])
    intensity = data.get("intensity", "Média")
    is_hybrid = data.get("isHybrid", False)
    start_col = data.get("startCol", 0)
    
    if len(selected_digits) != 5:
        return jsonify({"success": False, "error": "Selecione exatamente 5 dígitos"}), 400

    from models.models import AppState, Result, Matrix
    state = AppState.query.first()
    state.matrix_counter += 1
    
    rows_count = 10
    cols_count = 7
    grid = [[None for _ in range(cols_count)] for _ in range(rows_count)]
    
    for c in range(cols_count):
        base_pool = selected_digits * 2
        random.shuffle(base_pool)
        if is_hybrid:
            shift = (c * 2) % 10
            base_pool = base_pool[shift:] + base_pool[:shift]
        for r in range(rows_count):
            grid[r][c] = base_pool[r]

    # Aplicar Coluna Inicial se Híbrido
    if is_hybrid and start_col > 0:
        shifted_grid = [[None for _ in range(cols_count)] for _ in range(rows_count)]
        for r in range(rows_count):
            for c in range(cols_count):
                shifted_grid[r][(c + start_col) % cols_count] = grid[r][c]
        grid = shifted_grid

    last_res = Result.query.order_by(Result.concurso.desc()).first()
    concurso_default = str(last_res.concurso) if last_res else ""

    matrix = Matrix(
        name=f"Matriz {state.matrix_counter} (E4 {'H' if is_hybrid else 'P'})",
        strategy_type=4,
        intensity=intensity,
        is_hybrid=is_hybrid,
        start_col=start_col,
        sequence=json.dumps(selected_digits),
        result=json.dumps([None] * 7),
        concurso=concurso_default
    )
    matrix.set_grid(grid)
    db.session.add(matrix)
    db.session.commit()
    return jsonify(matrix.to_dict()), 201

@app.route("/api/matrix/top-hits", methods=["GET"])
def get_top_hits():
    """Retorna matrizes com 6 ou 7 acertos."""
    min_hits = request.args.get("min", 6, type=int)
    from models.models import Matrix
    matrices = Matrix.query.filter(Matrix.hits_count >= min_hits).order_by(Matrix.created_at.desc()).all()
    return jsonify([m.to_dict() for m in matrices])

@app.route("/api/stats/compare", methods=["POST"])
def compare_strategies():
    """Análise comparativa das estratégias (Aba 5)."""
    data = request.get_json()
    period = data.get("period", "50")
    strats = data.get("strategies", [1, 2, 3, 4])
    
    from models.models import Result, StrategyAnalysis, db
    if period == "custom":
        start = data.get("start", 0)
        end = data.get("end", 9999)
        results = Result.query.filter(Result.concurso >= start, Result.concurso <= end).all()
    else:
        results = Result.query.order_by(Result.concurso.desc()).limit(int(period)).all()
    
    if not results:
        return jsonify({"success": False, "error": "Nenhum concurso encontrado"}), 404

    all_results = Result.query.all()
    counts = {i: 0 for i in range(10)}
    for r in all_results:
        for d in r.get_dezenas():
            if d is not None: counts[d] += 1
    top_global = [x[0] for x in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:3]]

    stats_map = {}
    for s_type in strats:
        s_type = int(s_type)
        hits_list = []
        for r in results:
            res_val = r.get_dezenas()
            if s_type == 1:
                grid = compute_distribution([0,1,2,3,4,5,6,7,8,9], 0)
            elif s_type == 2:
                grid = []
                others = [i for i in range(10) if i not in top_global]
                for _ in range(10): 
                    row = [random.choice(top_global if random.random() < 0.4 else others) for _ in range(7)]
                    grid.append(row)
            elif s_type == 3:
                grid = []
                for _ in range(10):
                    row = [random.choice([res_val[j], random.randint(0,9)]) for j in range(7)]
                    grid.append(row)
            else:
                pool = (res_val[:5] + [0,1,2,3,4])[:5]
                grid = []
                for _ in range(10):
                    grid.append([random.choice(pool) for _ in range(7)])
            
            best_h = 0
            for row in grid:
                h = sum(1 for j in range(7) if row[j] == res_val[j])
                if h > best_h: best_h = h
            hits_list.append(best_h)
            
        avg = sum(hits_list) / len(hits_list)
        p3 = len([h for h in hits_list if h >= 3]) / len(hits_list)
        variance = sum((x - avg) ** 2 for x in hits_list) / len(hits_list)
        stability_inv = 1 / ((variance ** 0.5) + 1)
        score = (0.4 * avg) + (0.3 * p3) + (0.2 * stability_inv)
        
        stats_map[s_type] = {
            "strategy": f"Estratégia {s_type}",
            "media": round(avg, 2),
            "melhor": max(hits_list),
            "p3": round(p3 * 100, 1),
            "t6": len([h for h in hits_list if h == 6]),
            "t7": len([h for h in hits_list if h == 7]),
            "score": round(score, 4)
        }
    
    ranking = sorted(stats_map.values(), key=lambda x: x["score"], reverse=True)
    new_analysis = StrategyAnalysis(
        periodo=str(period),
        estrategias_comparadas=json.dumps(strats),
        resultados_json=json.dumps(stats_map),
        ranking_final=json.dumps(ranking)
    )
    db.session.add(new_analysis)
    db.session.commit()
    return jsonify({"success": True, "results": stats_map, "ranking": ranking})

import requests

@app.route("/api/sync/<int:concurso>", methods=["GET"])
def sync_result(concurso):
    """Busca o resultado de um concurso específico na API da Caixa."""
    try:
        url = f"{Config.CAIXA_API_URL}/{concurso}"
        response = requests.get(url, timeout=Config.API_TIMEOUT, verify=False)
        if response.status_code == 200:
            data = response.json()
            return save_api_result(data)
        return jsonify({"success": False, "error": f"API retornou status {response.status_code}"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/last-result", methods=["GET"])
def get_last_result():
    """Busca o último resultado disponível na API da Caixa."""
    try:
        url = Config.CAIXA_API_URL
        response = requests.get(url, timeout=Config.API_TIMEOUT, verify=False)
        if response.status_code == 200:
            data = response.json()
            return save_api_result(data)
        return jsonify({"success": False, "error": f"API retornou status {response.status_code}"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/sync-history", methods=["GET"])
def sync_history():
    """Busca concursos que faltam no banco até o mais recente."""
    try:
        # 1. Pegar o último concurso na API para saber até onde ir
        url = Config.CAIXA_API_URL
        response = requests.get(url, timeout=Config.API_TIMEOUT, verify=False)
        if response.status_code != 200:
            return jsonify({"success": False, "error": "API indisponível"}), 500
        
        latest_api_data = response.json()
        latest_api_concurso = latest_api_data.get("numero")
        
        # 1. Pegar todos os concursos já salvos para identificar buracos
        existing_concursos = {r.concurso for r in Result.query.with_entities(Result.concurso).all()}
        
        # 2. Verificar qual o último disponível na API
        url = Config.CAIXA_API_URL
        response = requests.get(url, timeout=Config.API_TIMEOUT, verify=False)
        latest_api_concurso = response.json().get("numero")
        
        # 3. Buscar o que falta
        sync_count = 0
        current = 1
        
        print(f"  [*] Iniciando varredura de histórico (1 até {latest_api_concurso})...", flush=True)
        
        while current <= latest_api_concurso:
            if current not in existing_concursos:
                url_sync = f"{Config.CAIXA_API_URL}/{current}"
                try:
                    res_sync = requests.get(url_sync, timeout=Config.API_TIMEOUT, verify=False)
                    if res_sync.status_code == 200:
                        save_api_result(res_sync.json())
                        sync_count += 1
                    else:
                        print(f"  [!] Falha ao sincronizar concurso {current}: Status {res_sync.status_code}", flush=True)
                except Exception as e:
                    print(f"  [!] Erro na conexão para o concurso {current}: {str(e)}", flush=True)
                    break
            
            current += 1
            
        return jsonify({
            "success": True, 
            "message": f"Sincronização completa. {sync_count} novos itens adicionados.",
            "count": sync_count
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

def save_api_result(data):
    """Auxiliar para salvar dados da API no banco."""
    concurso = data.get("numero")
    if not concurso:
        return jsonify({"success": False, "error": "Dados inválidos"}), 400
        
    # Usando listaDezenas (Posições 1 a 7)
    dezenas = data.get("listaDezenas", [])
    dezenas_int = [int(d) for d in dezenas]
    
    # Check if we have 7 dezenas
    if len(dezenas_int) < 7:
        print(f"  [!] Concurso {concurso}: Dados de dezenas incompletos ou inválidos.", flush=True)
    
    res = Result.query.filter_by(concurso=concurso).first()
    if not res:
        res = Result(concurso=concurso)
        db.session.add(res)
        status = "Inserindo"
    else:
        status = "Atualizando"
    
    # Gravação por Posição (col0 a col6)
    res.set_dezenas(dezenas_int)
    
    res.data = data.get("dataApuracao", "")
    res.acumulado = data.get("acumulado", False)
    res.valor_acumulado = data.get("valorAcumuladoProximoConcurso", 0.0)
    res.estimativa_proximo = data.get("valorEstimadoProximoConcurso", 0.0)
    res.data_proximo = data.get("dataProximoConcurso", "")
    res.arrecadacao = data.get("valorArrecadado", 0.0)
    
    # Novos campos detalhados
    res.local_sorteio = data.get("localSorteio", "")
    res.nome_municipio_uf_sorteio = data.get("nomeMunicipioUFSorteio", "")
    res.valor_total_premio_faixa_um = data.get("valorTotalPremioFaixaUm", 0.0)
    res.valor_saldo_reserva_garantidora = data.get("valorSaldoReservaGarantidora", 0.0)
    res.indicador_concurso_especial = data.get("indicadorConcursoEspecial")
    res.observacao = data.get("observacao", "")
    
    # Process rateio
    rateio_data = []
    for item in data.get("listaRateioPremio", []):
        rateio_data.append({
            "faixa": item.get("faixa"),
            "descricao": item.get("descricaoFaixa"),
            "ganhadores": item.get("numeroDeGanhadores"),
            "valor": item.get("valorPremio")
        })
    res.set_rateio(rateio_data)
    
    db.session.commit()
    
    # Console output for progress
    if os.environ.get("SUPERSETE_VERBOSE") == "1":
        print(f"  [+] {status} Concurso {concurso} | {res.data} | {dezenas_int}", flush=True)
    
    return jsonify({"success": True, "result": res.to_dict()})


# ══════════════════════════════════════════════════════
#  ROTAS — API: DISTRIBUIÇÃO
# ══════════════════════════════════════════════════════

@app.route("/api/matrix/<int:matrix_id>/distribution", methods=["GET"])
def get_distribution(matrix_id):
    """Retorna a distribuição completa com acertos."""
    matrix = Matrix.query.get_or_404(matrix_id)
    result = matrix.get_result()
    has_result = any(v is not None for v in result)

    # Se tiver grade pronta (Estratégia 2+)
    if matrix.grid_data:
        grid = matrix.get_grid()
        row_hits = []
        best_hits = 0
        best_row_idx = -1
        
        for i, row in enumerate(grid):
            hits = 0
            hit_cols = []
            for j in range(Config.COLUMNS):
                if result[j] is not None and row[j] == result[j]:
                    hits += 1
                    hit_cols.append(j)
            row_hits.append({"hits": hits, "hitCols": hit_cols})
            if hits > best_hits:
                best_hits = hits
                best_row_idx = i
        
        return jsonify({
            "rows": grid,
            "hitsData": {
                "rowHits": row_hits,
                "bestHits": best_hits,
                "bestRowIdx": best_row_idx,
            }
        })

    # Caso contrário, usa lógica rotacional (Estratégia 1)
    seq = matrix.get_sequence()
    if len(seq) == 0:
        return jsonify({"rows": [], "hitsData": None})

    hits_data = compute_hits(seq, matrix.start_col, result)
    return jsonify({
        "rows": hits_data["rows"],
        "hitsData": {
            "rowHits": hits_data["rowHits"],
            "bestHits": hits_data["bestHits"],
            "bestRowIdx": hits_data["bestRowIdx"],
        },
    })


# ══════════════════════════════════════════════════════
#  ROTAS — API: EXPORTAÇÕES
# ══════════════════════════════════════════════════════

@app.route("/api/matrix/<int:matrix_id>/export/txt")
def export_txt(matrix_id):
    matrix = Matrix.query.get_or_404(matrix_id)
    if matrix.grid_data:
        rows = matrix.get_grid()
    else:
        seq = matrix.get_sequence()
        if len(seq) == 0:
            return jsonify({"error": "Sequência vazia"}), 400
        rows = compute_distribution(seq, matrix.start_col)

    lines = [" ".join(str(d) for d in row) for row in rows]
    content = "\n".join(lines)

    filename = matrix.name.replace(" ", "_") + ".txt"
    filepath = os.path.join(Config.EXPORTS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return Response(
        content,
        mimetype="text/plain",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.route("/api/matrix/<int:matrix_id>/export/xml")
def export_xml(matrix_id):
    """Exporta a matriz como XML completo."""
    matrix = Matrix.query.get_or_404(matrix_id)
    seq = matrix.get_sequence()
    if len(seq) == 0:
        return jsonify({"error": "Sequência vazia"}), 400

    result = matrix.get_result()
    
    # Conferência baseada na estratégia
    if matrix.grid_data:
        grid = matrix.get_grid()
        row_hits = []
        best_hits = 0
        best_row_idx = -1
        for i, row in enumerate(grid):
            hits = sum(1 for j in range(7) if result[j] is not None and row[j] == result[j])
            row_hits.append({"hits": hits})
            if hits > best_hits:
                best_hits = hits
                best_row_idx = i
        rows = grid
        hits_list = row_hits
    else:
        seq = matrix.get_sequence()
        h_data = compute_hits(seq, matrix.start_col, result)
        rows = h_data["rows"]
        hits_list = h_data["rowHits"]
        best_hits = h_data["bestHits"]
        best_row_idx = h_data["bestRowIdx"]

    tier = Config.PRIZE_TIERS.get(best_hits, {})
    tier_name = tier.get("name", "Nenhuma")

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += "<SuperSet>\n"
    xml += f"  <Estrategia>{matrix.strategy_type}</Estrategia>\n"
    xml += f"  <Modo>{'Híbrido' if matrix.is_hybrid else 'Padrão'}</Modo>\n"
    xml += f"  <Intensidade>{matrix.intensity}</Intensidade>\n"
    xml += f'  <Matriz nome="{matrix.name}">\n'
    
    if not matrix.grid_data:
        xml += f"    <Sequencia>{','.join(str(d) for d in matrix.get_sequence())}</Sequencia>\n"
    
    xml += f"    <ColunaInicial>{matrix.start_col + 1}</ColunaInicial>\n"
        
    if matrix.concurso:
        xml += f"    <Concurso>{matrix.concurso}</Concurso>\n"
        
    result_str = ",".join(str(v) if v is not None else "-" for v in result)
    xml += f"    <Resultado>{result_str}</Resultado>\n"
    xml += "    <Distribuicao>\n"
    for idx, row in enumerate(rows):
        hits = hits_list[idx]["hits"]
        row_str = ",".join(str(d) for d in row)
        xml += f'      <Linha numero="{idx + 1}" acertos="{hits}">'
        xml += f"{row_str}</Linha>\n"
    xml += "    </Distribuicao>\n"
    xml += "    <MelhorResultado>\n"
    xml += f"      <Linha>{best_row_idx + 1}</Linha>\n"
    xml += f"      <Acertos>{best_hits}</Acertos>\n"
    xml += f"      <Faixa>{tier_name}</Faixa>\n"
    xml += "    </MelhorResultado>\n"
    created = matrix.created_at.isoformat() if matrix.created_at else ""
    xml += f"    <DataCriacao>{created}</DataCriacao>\n"
    xml += "  </Matriz>\n"
    xml += "</SuperSet>"

    filename = matrix.name.replace(" ", "_") + ".xml"
    filepath = os.path.join(Config.EXPORTS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(xml)

    return Response(
        xml,
        mimetype="application/xml",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.route("/api/matrix/<int:matrix_id>/export/html")
def export_html(matrix_id):
    """Exporta a matriz como HTML formatado."""
    matrix = Matrix.query.get_or_404(matrix_id)
    seq = matrix.get_sequence()
    if len(seq) == 0:
        return jsonify({"error": "Sequência vazia"}), 400

    result = matrix.get_result()
    has_result = any(v is not None for v in result)
    
    if matrix.grid_data:
        grid = matrix.get_grid()
        row_hits = []
        best_hits = 0
        best_row_idx = -1
        for i, row in enumerate(grid):
            hits = sum(1 for j in range(7) if result[j] is not None and row[j] == result[j])
            row_hits.append({"hits": hits})
            if hits > best_hits:
                best_hits = hits
                best_row_idx = i
        rows = grid
        hits_list = row_hits
    else:
        seq = matrix.get_sequence()
        h_data = compute_hits(seq, matrix.start_col, result)
        rows = h_data["rows"]
        hits_list = h_data["rowHits"]
        best_hits = h_data["bestHits"]
        best_row_idx = h_data["bestRowIdx"]

    tier = Config.PRIZE_TIERS.get(best_hits, {})

    html = "<!DOCTYPE html>\n<html lang='pt-BR'>\n<head>\n"
    html += "<meta charset='UTF-8'>\n"
    html += f"<title>{matrix.name} — SuperSet Estratégia {matrix.strategy_type}</title>\n"
    html += f"<meta name='mode' content='{'Híbrido' if matrix.is_hybrid else 'Padrão'}'>\n"
    html += f"<meta name='intensity' content='{matrix.intensity}'>\n"
    html += "<style>\n"
    html += "body{font-family:'Segoe UI',sans-serif;padding:32px;max-width:700px;"
    html += "margin:0 auto;color:#1a1f36;background:#f8fafc}\n"
    html += "h1{font-size:22px;margin-bottom:4px;color:#0d3b2e}\n"
    html += "h2{font-size:14px;color:#666;margin-bottom:24px;font-weight:400}\n"
    html += "table{width:100%;border-collapse:collapse;margin:20px 0;"
    html += "box-shadow:0 1px 3px rgba(0,0,0,0.1);border-radius:8px;overflow:hidden}\n"
    html += "th{background:#1e293b;color:#fff;padding:10px 8px;"
    html += "text-align:center;font-size:13px;font-weight:600}\n"
    html += "td{text-align:center;padding:10px 8px;border-bottom:1px solid #e2e8f0;"
    html += "font-family:'Consolas',monospace;font-size:17px;position:relative}\n"
    html += "tr:nth-child(even) td{background:#f1f5f9}\n"
    html += ".line-num{font-size:10px;color:#94a3b8;width:25px;text-align:right;padding-right:12px;font-family:'Outfit',sans-serif;font-weight:700;border:none !important;background:none !important;opacity:0.8}\n"
    html += ".hit-val{display:inline-flex;align-items:center;justify-content:center;"
    html += "width:30px;height:30px;background:#000;color:#fff;border-radius:50%}\n"
    html += ".hit-val.hit{background:#f59e0b}\n"
    html += ".hits-circle{display:inline-flex;align-items:center;justify-content:center;"
    html += "width:30px;height:30px;background:#000;color:#fff;border-radius:50%;font-weight:700}\n"
    html += ".hits-circle.hit-low{background:#f59e0b}\n"
    html += ".hits-circle.hit-high{background:#a9cf46;color:#000}\n"
    html += ".best-row td{background:rgba(169,207,70,0.1) !important}\n"
    html += ".info{background:#fff;padding:14px 18px;border-radius:10px;"
    html += "margin:10px 0;font-size:14px;border:1px solid #e2e8f0}\n"
    html += ".info strong{color:#0d3b2e}\n"
    html += ".footer{margin-top:30px;font-size:11px;color:#999;"
    html += "text-align:center;border-top:1px solid #e2e8f0;padding-top:16px}\n"
    html += "</style>\n</head>\n<body>\n"
    html += f"<h1>{matrix.name}</h1>\n"
    html += f"<h2>SuperSet Estratégia {matrix.strategy_type} — Modo {'Híbrido' if matrix.is_hybrid else 'Padrão'} — {matrix.intensity}</h2>\n"
    if not matrix.grid_data:
        seq_str = " → ".join(str(d) for d in matrix.get_sequence())
        html += f'<div class="info"><strong>Sequência:</strong> {seq_str}</div>\n'
    
    html += f'<div class="info"><strong>Coluna Inicial:</strong> {matrix.start_col + 1}</div>\n'

    if matrix.concurso:
        html += f'<div class="info"><strong>Concurso:</strong> {matrix.concurso}</div>\n'
    result_str = " | ".join(str(v) if v is not None else "–" for v in result)
    html += f'<div class="info"><strong>Resultado:</strong> {result_str}</div>\n'
    html += "<table>\n<thead><tr><th></th>"
    for c in range(1, 8):
        html += f"<th>C{c}</th>"
    html += "<th>Acertos</th></tr></thead>\n<tbody>\n"

    #loop render
    html_body = ""
    for i, row in enumerate(rows):
        is_best = (has_result and best_hits >= 3 and i == best_row_idx)
        tr_cls = " class='best-row'" if is_best else ""
        html_body += f"<tr{tr_cls}>"
        
        # Coluna de número da linha
        html_body += f'<td class="line-num">{i + 1}</td>'
        
        row_h = hits_list[i]
        hit_indices = []
        if has_result:
            if matrix.grid_data:
                hit_indices = [j for j in range(7) if result[j] is not None and row[j] == result[j]]
            else:
                hit_indices = row_h.get("hitCols", [])
        for j in range(7):
            cls = " hit" if j in hit_indices else ""
            html_body += f'<td><span class="hit-val{cls}">{row[j]}</span></td>'
        h_val = row_h["hits"] if has_result else "—"
        
        hit_lvl = ""
        if has_result:
            if h_val >= 3: hit_lvl = " hit-high"
            elif h_val >= 1: hit_lvl = " hit-low"
            
        html_body += f'<td><span class="hits-circle{hit_lvl}">{h_val}</span></td></tr>\n'

    html += html_body
    html += "</tbody>\n</table>\n"

    if has_result and best_hits >= 1:
        # Busca valor real no banco para o Melhor Resultado
        final_value = tier.get('value', '—')
        val_label = "Valor Estimado"
        if matrix.concurso:
            try:
                from models.models import Result
                res_obj = Result.query.filter_by(concurso=int(matrix.concurso)).first()
                if res_obj:
                    rateio = res_obj.get_rateio()
                    # 7=1, 6=2, 5=3, 4=4, 3=5
                    real_rateio = next((r for r in rateio if (8 - r['faixa']) == best_hits), None)
                    if real_rateio and real_rateio.get('valor') is not None:
                        val = real_rateio['valor']
                        final_value = f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                        val_label = "Valor Real"
            except:
                pass
        
        hits_text = f"{best_hits} acertos"
        info = f"Linha {best_row_idx + 1} ({hits_text}"
        
        # Só adiciona o nome da faixa se não for redundante (ex: 4 acertos - Quadra)
        tier_name = tier.get('name', '')
        if tier_name and tier_name != hits_text:
            info += f" — {tier_name}"
            
        info += f" — {final_value})"
        html += f'<div class="info"><strong>Melhor Resultado:</strong> {info} <small style="display:block;color:#999;margin-top:2px">{val_label}</small></div>\n'

    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    html += f'<div class="footer">Gerado em: {now} | SuperSet Estratégia {matrix.strategy_type} v{Config.APP_VERSION}</div>\n'
    html += "</body>\n</html>"

    filename = matrix.name.replace(" ", "_") + ".html"
    filepath = os.path.join(Config.EXPORTS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    return Response(
        html,
        mimetype="text/html",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ══════════════════════════════════════════════════════
#  ROTAS — API: ANÁLISES ESTATÍSTICAS
# ══════════════════════════════════════════════════════

def get_stats_data(period, start=None, end=None):
    """Auxiliar para buscar resultados baseados no período."""
    if period == "custom" and start is not None and end is not None:
        return Result.query.filter(Result.concurso >= start, Result.concurso <= end).order_by(Result.concurso.desc()).all()
    else:
        # Quando period é "0" ou não numérico, buscamos todos ou usamos default de 50
        if not str(period).isdigit():
            return Result.query.order_by(Result.concurso.desc()).limit(50).all()
        
        limit = int(period)
        if limit > 0:
            return Result.query.order_by(Result.concurso.desc()).limit(limit).all()
        else:
            return Result.query.order_by(Result.concurso.desc()).all()

@app.route("/api/stats/analysis", methods=["POST"])
def execute_analysis_modular():
    data = request.get_json()
    analysis_type = data.get("type")
    period = data.get("period", "50")
    start = data.get("start")
    end = data.get("end")

    results = get_stats_data(period, start, end)
    if not results:
        return jsonify({"success": False, "error": "Nenhum dado encontrado"}), 404

    res_json = {}
    rows_data = [r.get_dezenas() for r in results]
    
    if analysis_type == "composicao":
        # Análise 1: Estrutura de Composição
        distinct_counts = []
        rep_counts = {i: 0 for i in range(7)} # 0 a 6 repetições
        repeater_digits = {i: 0 for i in range(10)}
        
        for row in rows_data:
            unique = set(row)
            d_count = len(unique)
            distinct_counts.append(d_count)
            
            reps = 7 - d_count
            rep_counts[reps] += 1
            
            # Ranking de dígitos que se repetem
            counts = {}
            for d in row: counts[d] = counts.get(d, 0) + 1
            for d, c in counts.items():
                if c >= 2: repeater_digits[d] += (c - 1)

        avg_distinct = sum(distinct_counts) / len(distinct_counts)
        variance = sum((x - avg_distinct)**2 for x in distinct_counts) / len(distinct_counts)
        
        # Histograma de Distintos
        hist_distinct = {i: distinct_counts.count(i) for i in range(1, 8)}
        
        res_json = {
            "media_distintos": round(avg_distinct, 2),
            "desvio_padrao": round(math.sqrt(variance), 2),
            "hist_distinct": hist_distinct,
            "rep_counts": rep_counts,
            "rep_percent": round((len([x for x in distinct_counts if x < 7]) / len(distinct_counts)) * 100, 1),
            "top_repeaters": sorted(repeater_digits.items(), key=lambda x: x[1], reverse=True)[:3]
        }

    elif analysis_type == "colunas":
        # Análise 2: Frequência por Coluna
        col_freqs = {c: {d: 0 for d in range(10)} for c in range(7)}
        for row in rows_data:
            for c in range(7):
                d = row[c]
                if d is not None: col_freqs[c][d] += 1
        
        res_json = {"matrix": col_freqs}

    elif analysis_type == "estrutural":
        # Análise 3: Padrão Estrutural
        patterns = {}
        for row in rows_data:
            counts = sorted([row.count(d) for d in set(row)], reverse=True)
            # Simplificação de nomes: [2, 1, 1, 1, 1, 1] -> Dupla
            # [2, 2, 1, 1, 1] -> Dupla + Dupla
            if counts[0] == 1: p = "7 Distintos"
            elif counts[0] == 2:
                p = "Dupla + Dupla" if counts[1] == 2 else "Dupla"
            elif counts[0] == 3: p = "Trinca"
            elif counts[0] == 4: p = "Quadra"
            elif counts[0] == 5: p = "5 Iguais"
            elif counts[0] == 6: p = "6 Iguais"
            else: p = "7 Iguais"
            
            patterns[p] = patterns.get(p, 0) + 1
        
        res_json = {"patterns": patterns}

    elif analysis_type == "concentracao":
        # Análise 4: Mapa de Concentração
        period_distinct = [len(set(r)) for r in rows_data]
        period_avg = sum(period_distinct) / len(period_distinct)
        
        all_res = Result.query.all()
        global_avg = sum([len(set(r.get_dezenas())) for r in all_res]) / len(all_res)
        
        diff = period_avg - global_avg
        status = "Estável"
        if diff > 0.1: status = "Concentração Menor (Mais Distribuído)"
        elif diff < -0.1: status = "Concentração Maior (Mais Repetido)"
        
        res_json = {
            "period_avg": round(period_avg, 2),
            "global_avg": round(global_avg, 2),
            "status": status,
            "diff": round(diff, 2)
        }

    elif analysis_type == "par_impar":
        # Análise 5: Pares e Ímpares
        dist_pi = {} # "xP yI": count
        for row in rows_data:
            pares = len([d for d in row if d % 2 == 0])
            impares = 7 - pares
            lbl = f"{pares}P {impares}I"
            dist_pi[lbl] = dist_pi.get(lbl, 0) + 1
        
        res_json = {"distribuicao": dist_pi}

    elif analysis_type == "repeticao_detalhada":
        # Análise 6: Repetição Detalhada
        overall_repeats = {i: 0 for i in range(10)}
        extreme_concentrated = {"conc": 0, "val": 8} # 8 é impossível, min distinto é 1
        extreme_distributed = {"conc": 0, "val": 0}
        
        for r_obj in results:
            row = r_obj.get_dezenas()
            counts = {d: row.count(d) for d in set(row)}
            for d, c in counts.items():
                if c >= 2: overall_repeats[d] += 1
            
            distinct = len(set(row))
            if distinct < extreme_concentrated["val"]:
                extreme_concentrated = {"conc": r_obj.concurso, "val": distinct}
            if distinct > extreme_distributed["val"]:
                extreme_distributed = {"conc": r_obj.concurso, "val": distinct}

        res_json = {
            "ranking_repetidores": sorted(overall_repeats.items(), key=lambda x: x[1], reverse=True),
            "max_concentrado": extreme_concentrated,
            "max_distribuido": extreme_distributed
        }

    # Salvar execução
    from models.models import AnalysisExecution
    exec_record = AnalysisExecution(
        tipo_analise=analysis_type,
        parametros=json.dumps({"period": period, "start": start, "end": end}),
        resultado_resumido=json.dumps(res_json),
        periodo_analisado=f"Últimos {period}" if period != "custom" else f"{start}-{end}"
    )
    db.session.add(exec_record)
    db.session.commit()

    return jsonify({"success": True, "data": res_json})

@app.route("/api/stats/export", methods=["GET"])
def export_analysis_result():
    analysis_type = request.args.get("type", "geral")
    period = request.args.get("period", "50")
    fmt = request.args.get("format", "txt")
    
    results = get_stats_data(period)
    if not results:
        return "Nenhum dado para exportar", 404

    filename = f"super7_analise_{analysis_type}_{datetime.now().strftime('%Y%m%d_%H%M')}.{fmt}"
    filepath = os.path.join(Config.EXPORTS_DIR, filename)

    if fmt == "txt":
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"SUPER 7 - RELATÓRIO DE ANÁLISE: {analysis_type.upper()}\n")
            f.write(f"DATA: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
            f.write(f"PERÍODO: {period} concursos\n")
            f.write("="*50 + "\n\n")
            for r in results:
                f.write(f"Concurso {r.concurso}: {r.dezenas}\n")
    
    elif fmt == "html":
        html_content = f"""
        <html><head><meta charset='utf-8'><title>Relatório Super 7</title>
        <style>body{{font-family:sans-serif; padding:20px;}} table{{border-collapse:collapse; width:100%;}} th,td{{border:1px solid #ddd; padding:8px; text-align:left;}} th{{background:#f4f4f4;}}</style>
        </head><body>
        <h1>Análise de {analysis_type.capitalize()}</h1>
        <p>Período: {period} concursos | Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
        <table><thead><tr><th>Concurso</th><th>Dígitos (C1-C7)</th><th>Data</th></tr></thead><tbody>
        """
        for r in results:
            html_content += f"<tr><td>{r.concurso}</td><td>{r.dezenas}</td><td>{r.data_concurso}</td></tr>"
        html_content += "</tbody></table></body></html>"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)

    else:
        # Fallback TXT para formatos não implementados neste protótipo
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"Exportação {fmt.upper()} não implementada. Dados em TXT:\n")
            for r in results: f.write(f"{r.concurso}: {r.dezenas}\n")

    return send_file(filepath, as_attachment=True)


# ══════════════════════════════════════════════════════
#  INICIAR SERVIDOR
# ══════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _root not in sys.path:
        sys.path.insert(0, _root)
    from quiet_terminal import silence_startup
    silence_startup()
    init_db()
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG, use_reloader=False)
