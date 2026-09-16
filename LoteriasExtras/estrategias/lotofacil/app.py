from flask import Flask, render_template, jsonify, request, send_file
from lotofacil.db_manager import DatabaseManager
from lotofacil.analyzer import LotofacilAnalyzer
from lotofacil.strategies import LotofacilStrategies
from lotofacil.ranking import LotofacilRanking
from config.config import *
from config.config import lotofacil_config
from dotenv import load_dotenv
import os
import io
import datetime
import sys

# Add parent directory to sys.path to access central lotteries_config.py
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT_DIR not in sys.path:
    sys.path.append(PARENT_DIR)

load_dotenv()

try:
    from lotteries_config import LOTTERIES
except ImportError:
    LOTTERIES = {}

from remote_wsgi import apply_proxy

app = Flask(__name__)
app.secret_key = SECRET_KEY
apply_proxy(app)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.auto_reload = True
db = DatabaseManager() # Uses default DATABASE_PATH from DatabaseManager

@app.route('/api/config')
def get_config():
    # Adding global colors to the response for the frontend
    # Pulling directly from the central lotteries_config
    loto_colors = LOTTERIES.get("lotofacil", {}).get("colors", {})
    
    res = {
        "colors_global": {
            "pares": loto_colors.get("pares", "#2ecc71"),
            "impares": loto_colors.get("impares", "#f39c12"),
            "repetidos": loto_colors.get("repetidos", "#8e44ad"),
            "sequencias": loto_colors.get("sequencias", "#000000")
        },
        "lotofacil": {
            "cor_modalidade": loto_colors.get("primary", "#7B1FA2")
        }
    }
    
    return jsonify(res)

@app.route('/api/history')
def get_history():
    limit = request.args.get('limit', default=20, type=int)
    results = db.get_all_results()
    if not results:
        return jsonify([])
    # Return sorted by date/ID descending for the history view
    return jsonify(results[-limit:][::-1])

@app.route('/')
def index():
    return render_template('index.html', config=lotofacil_config)

@app.route('/api/stats')
def get_stats():
    results = db.get_all_results()
    if not results:
        return jsonify({"error": "No data in database"}), 400
        
    analyzer = LotofacilAnalyzer()
    strategies = LotofacilStrategies(results)
    
    # Calculate a base ranking for insights (100 games sample)
    ranking_results = {}
    for sid in range(1, 12):
        sample_games = strategies.generate_games(sid, 100)
        ranking_results[f"Estratégia {sid}"] = LotofacilRanking.evaluate_strategy(sample_games, results)
    
    ranked = LotofacilRanking.rank_strategies(ranking_results, 'avg_hits')
    
    return jsonify({
        "frequency": analyzer.analyze_frequency(results),
        "structure": analyzer.analyze_structure(results),
        "composition": analyzer.analyze_composition(results[-50:]),
        "repetition": analyzer.analyze_repetition(results[-50:]),
        "patterns": analyzer.analyze_patterns(results[-50:]),
        "temporal": analyzer.analyze_temporal(results),
        "base_ranking": ranked
    })

@app.route('/api/generate', methods=['POST'])
def generate():
    data = request.json
    count = data.get('count', 10)
    strategy_id = data.get('strategy_id', 1)
    ranking_criterion = data.get('ranking_criterion', 'avg_hits')
    universe = data.get('universe')
    fixed_numbers = data.get('fixed_numbers')
    ranking_sample = data.get('ranking_sample', 500)
    wheeling_numbers = data.get('wheeling_numbers')
    wheeling_type = data.get('wheeling_type')
    
    results = db.get_all_results()
    if not results:
        return jsonify({"error": "No data in database"}), 400
        
    strategies = LotofacilStrategies(results)
    
    # Generate games for the requested strategy
    generated_games = strategies.generate_games(strategy_id, count, universe=universe, fixed_numbers=fixed_numbers, wheeling_numbers=wheeling_numbers, wheeling_type=wheeling_type)
    
    # Also evaluate all active strategies for the ranking
    ranking_results = {}
    for sid in range(1, 12):
        sample_games = strategies.generate_games(sid, ranking_sample, universe=universe if sid == 5 else None, fixed_numbers=fixed_numbers if sid == 7 else None)
        ranking_results[f"Estratégia {sid}"] = LotofacilRanking.evaluate_strategy(sample_games, results)
        
    ranked = LotofacilRanking.rank_strategies(ranking_results, ranking_criterion)
    
    return jsonify({
        "games": generated_games,
        "ranking": ranked,
        "too_many": count > 1000
    })

@app.route('/api/download', methods=['POST'])
def download():
    data = request.json
    count = data.get('count', 10)
    strategy_id = data.get('strategy_id', 1)
    file_format = data.get('format', 'txt') # txt or csv
    universe = data.get('universe')
    fixed_numbers = data.get('fixed_numbers')
    wheeling_numbers = data.get('wheeling_numbers')
    wheeling_type = data.get('wheeling_type')
    
    results = db.get_all_results()
    strategies = LotofacilStrategies(results)
    games = strategies.generate_games(strategy_id, count, universe=universe, fixed_numbers=fixed_numbers, wheeling_numbers=wheeling_numbers, wheeling_type=wheeling_type)
    
    output = io.StringIO()
    if file_format == 'csv':
        output.write("Jogo,D1,D2,D3,D4,D5,D6,D7,D8,D9,D10,D11,D12,D13,D14,D15\n")
        for i, game in enumerate(games, 1):
            output.write(f"{i}," + ",".join(map(str, game)) + "\n")
    else:
        for game in games:
            output.write(" ".join(f"{n:02d}" for n in game) + "\n")
            
    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8'))
    mem.seek(0)
    
    filename = f"lotofacil_jogos_{count}.{file_format}"
    return send_file(mem, as_attachment=True, download_name=filename, mimetype='text/plain')

# Temporary dev route to populate data if empty
@app.route('/api/debug/populate')
def populate():
    # Insert some dummy historical data if the database is empty
    import random
    if not db.get_all_results():
        for i in range(1, 101):
            bolas = random.sample(range(1, 26), 15)
            dezenas = sorted(bolas)
            db.insert_result({
                "concurso": 3000 + i,
                "data": (datetime.datetime.now() - datetime.timedelta(days=101-i)).strftime("%d/%m/%Y"),
                "bolas": bolas,
                "dezenas": dezenas
            })
        return jsonify({"status": "Populated 100 rows"})
    return jsonify({"status": "Already has data"})

if __name__ == '__main__':
    from quiet_terminal import silence_startup
    silence_startup()
    app.run(debug=DEBUG, host=HOST, port=PORT, use_reloader=False)
