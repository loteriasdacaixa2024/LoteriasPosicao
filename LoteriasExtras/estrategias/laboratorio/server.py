import os
import sys
import io
import datetime
import random
from flask import Flask, render_template, jsonify, request, send_file

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from laboratorio.config import (
    SLUG, SECRET_KEY, HOST, PORT, DEBUG, DRAW_NUMBERS,
    NUMBER_MIN, NUMBER_MAX, TEMPLATE_CONFIG,
)
from laboratorio.db_manager import DatabaseManager
from laboratorio.analyzer import LotteryAnalyzer
from laboratorio.strategies import LotteryStrategies
from laboratorio.ranking import LotteryRanking
from lotteries_config import LOTTERIES

HERE = os.path.dirname(os.path.abspath(__file__))
LOTO_DIR = os.path.join(ROOT, "lotofacil")
app = Flask(
    __name__,
    template_folder=os.path.join(LOTO_DIR, "templates"),
    static_folder=os.path.join(LOTO_DIR, "static"),
)
app.secret_key = SECRET_KEY
apply_proxy(app)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.auto_reload = True
db = DatabaseManager()


def seed_if_empty():
    if db.get_all_results():
        return
    pool = list(range(NUMBER_MIN, NUMBER_MAX + 1))
    for i in range(1, 81):
        bolas = random.sample(pool, DRAW_NUMBERS)
        db.insert_result({
            "concurso": 1000 + i,
            "data": (datetime.datetime.now() - datetime.timedelta(days=81 - i)).strftime("%d/%m/%Y"),
            "bolas": bolas,
            "dezenas": sorted(bolas),
        })
    print(f"  [{SLUG}] dados de exemplo inseridos", flush=True)


seed_if_empty()


@app.route("/api/config")
def get_config():
    colors = LOTTERIES.get(SLUG, {}).get("colors", {})
    return jsonify({
        "colors_global": {
            "pares": colors.get("pares", "#2ecc71"),
            "impares": colors.get("impares", "#f39c12"),
            "repetidos": colors.get("repetidos", "#8e44ad"),
            "sequencias": colors.get("sequencias", "#000000"),
        },
        "modality": {"cor_modalidade": colors.get("primary", "#7B1FA2")},
        SLUG: {"cor_modalidade": colors.get("primary", "#7B1FA2")},
        "lotofacil": {"cor_modalidade": colors.get("primary", "#7B1FA2")},
    })


@app.route("/api/history")
def get_history():
    limit = request.args.get("limit", default=20, type=int)
    results = db.get_all_results()
    if not results:
        return jsonify([])
    return jsonify(results[-limit:][::-1])


@app.route("/")
def index():
    return render_template("index.html", config=TEMPLATE_CONFIG)


@app.route("/api/stats")
def get_stats():
    results = db.get_all_results()
    if not results:
        return jsonify({"error": "No data in database"}), 400
    analyzer = LotteryAnalyzer()
    strategies = LotteryStrategies(results)
    ranking_results = {}
    for sid in range(1, 12):
        sample_games = strategies.generate_games(sid, 40)
        ranking_results[f"Estratégia {sid}"] = LotteryRanking.evaluate_strategy(sample_games, results)
    ranked = LotteryRanking.rank_strategies(ranking_results, "avg_hits")
    return jsonify({
        "frequency": analyzer.analyze_frequency(results),
        "structure": analyzer.analyze_structure(results),
        "composition": analyzer.analyze_composition(results[-50:]),
        "repetition": analyzer.analyze_repetition(results[-50:]),
        "patterns": analyzer.analyze_patterns(results[-50:]),
        "temporal": analyzer.analyze_temporal(results),
        "base_ranking": ranked,
    })


@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.json or {}
    count = data.get("count", 10)
    strategy_id = data.get("strategy_id", 1)
    ranking_criterion = data.get("ranking_criterion", "avg_hits")
    universe = data.get("universe")
    fixed_numbers = data.get("fixed_numbers")
    ranking_sample = min(int(data.get("ranking_sample", 80)), 120)
    wheeling_numbers = data.get("wheeling_numbers")
    wheeling_type = data.get("wheeling_type")
    results = db.get_all_results()
    if not results:
        return jsonify({"error": "No data in database"}), 400
    strategies = LotteryStrategies(results)
    generated_games = strategies.generate_games(
        strategy_id, count, universe=universe, fixed_numbers=fixed_numbers,
        wheeling_numbers=wheeling_numbers, wheeling_type=wheeling_type,
    )
    ranking_results = {}
    for sid in range(1, 12):
        sample_games = strategies.generate_games(
            sid, ranking_sample,
            universe=universe if sid == 5 else None,
            fixed_numbers=fixed_numbers if sid == 7 else None,
        )
        ranking_results[f"Estratégia {sid}"] = LotteryRanking.evaluate_strategy(sample_games, results)
    ranked = LotteryRanking.rank_strategies(ranking_results, ranking_criterion)
    return jsonify({"games": generated_games, "ranking": ranked, "too_many": count > 1000})


@app.route("/api/download", methods=["POST"])
def download():
    data = request.json or {}
    count = data.get("count", 10)
    strategy_id = data.get("strategy_id", 1)
    file_format = data.get("format", "txt")
    results = db.get_all_results()
    strategies = LotteryStrategies(results)
    games = strategies.generate_games(
        strategy_id, count,
        universe=data.get("universe"),
        fixed_numbers=data.get("fixed_numbers"),
        wheeling_numbers=data.get("wheeling_numbers"),
        wheeling_type=data.get("wheeling_type"),
    )
    output = io.StringIO()
    if file_format == "csv":
        headers = ["Jogo"] + [f"D{i}" for i in range(1, DRAW_NUMBERS + 1)]
        output.write(",".join(headers) + "\n")
        for i, game in enumerate(games, 1):
            output.write(f"{i}," + ",".join(map(str, game)) + "\n")
    else:
        for game in games:
            output.write(" ".join(f"{n:02d}" for n in game) + "\n")
    mem = io.BytesIO(output.getvalue().encode("utf-8"))
    mem.seek(0)
    filename = f"{SLUG}_jogos_{count}.{file_format}"
    return send_file(mem, as_attachment=True, download_name=filename, mimetype="text/plain")


if __name__ == "__main__":
    app.run(debug=DEBUG, host=HOST, port=PORT)
