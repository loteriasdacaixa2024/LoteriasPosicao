import os
import sys

from flask import Blueprint, render_template, jsonify, request
from services.analise_supersete_service import AnaliseSuperSeteService

_SHARED = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

analise_bp = Blueprint('analise', __name__)


def _repeticao_sequencial():
    from analise_repeticao.repeticao_service import RepeticaoConcursosService
    return RepeticaoConcursosService("supersete").analisar_completo("posicional")


@analise_bp.route('/')
def analise_index():
    analise = AnaliseSuperSeteService.analise_por_coluna()
    historico = AnaliseSuperSeteService.ultimos_sorteios()
    repeticoes = AnaliseSuperSeteService.analise_repeticoes()
    seq = None
    if historico and len(historico) >= 2:
        try:
            seq = _repeticao_sequencial()
            if not seq.get("sucesso"):
                seq = None
        except Exception:
            seq = None
    return render_template(
        'analise.html',
        analise=analise,
        historico=historico,
        repeticoes=repeticoes,
        seq=seq,
        last_draw=historico[0]['digitos'] if historico else [],
        frequent_numbers=[item['digito'] for item in repeticoes.get('top_3_repetidos', [])] if repeticoes else [],
    )


@analise_bp.route('/api/repeticao-sequencial')
def api_repeticao_sequencial():
    try:
        data = _repeticao_sequencial()
        if not data.get("sucesso"):
            return jsonify(data), 400
        return jsonify(data)
    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 500

@analise_bp.route('/api/dados')
def api_dados():
    try:
        analise = AnaliseSuperSeteService.analise_por_coluna()
        if analise is None:
            return jsonify({"status": "error", "message": "Sem dados no banco."}), 404
        # Get stats
        from services.analise_supersete_service import obter_conexao
        conn = obter_conexao()
        c = conn.cursor()
        c.execute("SELECT COUNT(*), MAX(concurso) FROM sorteios_supersete")
        row = c.fetchone()
        conn.close()
        
        return jsonify({
            "status": "success",
            "total_sorteios": row[0] if row else 0,
            "ultimo_concurso": row[1] if row else None,
            "analise": analise
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@analise_bp.route('/api/ultimos', methods=['GET'])
def api_ultimos():
    try:
        sorteios = AnaliseSuperSeteService.ultimos_sorteios()
        return jsonify({"status": "success", "sorteios": sorteios})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@analise_bp.route('/gerar_apostas', methods=['POST'])
def gerar_apostas():
    """Gera apostas inteligentes baseadas na análise existente."""
    from services.bet_generator_service import BetGeneratorSuperSete
    data = request.get_json() or {}

    analise = AnaliseSuperSeteService.analise_por_coluna()
    historico = AnaliseSuperSeteService.ultimos_sorteios()
    last_draw = historico[0]['digitos'] if historico else [0]*7

    # Parâmetros do usuário
    qty_games = int(data.get('qty_games', 5))
    strategy = data.get('strategy', 'balanced')
    min_reps = int(data.get('min_repetitions', 0))
    max_reps = int(data.get('max_repetitions', 7))

    # Fixed: {"1": 5, "3": 2} => {1: 5, 3: 2}
    fixed_raw = data.get('fixed', {})
    fixed = {int(k): int(v) for k, v in fixed_raw.items()} if fixed_raw else {}

    # Excluded: {"1": [0,1], "5": [9]} => {1: [0,1], 5: [9]}
    excl_raw = data.get('excluded', {})
    excluded = {int(k): [int(x) for x in v] for k, v in excl_raw.items()} if excl_raw else {}

    try:
        bets = BetGeneratorSuperSete.generate(
            analise=analise,
            last_draw=last_draw,
            qty_games=qty_games,
            fixed=fixed,
            excluded=excluded,
            min_repetitions=min_reps,
            max_repetitions=max_reps,
            strategy=strategy,
        )
        return jsonify({
            "status": "success",
            "bets": bets,
            "last_draw": last_draw,
            "qty_generated": len(bets),
            "strategy": strategy,
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@analise_bp.route('/exportar_apostas', methods=['POST'])
def exportar_apostas():
    """Exporta apostas como .txt (só números separados por espaço)."""
    from flask import Response
    data = request.get_json() or {}
    bets = data.get('bets', [])
    lines = []
    for bet in bets:
        nums = bet.get('numbers', [])
        lines.append(' '.join(str(n) for n in nums))
    content = '\n'.join(lines)
    return Response(
        content,
        mimetype='text/plain',
        headers={'Content-Disposition': 'attachment; filename=apostas_supersete.txt'}
    )

# POSICAO_ANALISE_WIRED
from posicao_analise.app_integration import wire_posicao_analise
wire_posicao_analise(analise_bp, "supersete")
from concentracao_acertos.app_integration import wire_concentracao_analise
wire_concentracao_analise(analise_bp, "supersete")
from analise_estudos.app_integration import wire_analise_estudos
wire_analise_estudos(analise_bp, "supersete")
from analise_inteligentes_diadesorte.app_integration import wire_analise_inteligentes
wire_analise_inteligentes(analise_bp, "supersete")
from geradores_elite.comportamento_analise_integration import wire_analise_comportamento
wire_analise_comportamento(analise_bp, "supersete")
from analise_somas_digitos.app_integration import wire_analise_somas_digitos
wire_analise_somas_digitos(analise_bp, "supersete")
