from flask import Blueprint, jsonify, render_template, request

from services.analise_repeticao_concursos_service import AnaliseRepeticaoConcursosService

analise_repeticao_bp = Blueprint('analise_repeticao', __name__, url_prefix='/analise/repeticao-concursos')


@analise_repeticao_bp.route('/')
def pagina():
    return render_template('analise_repeticao_concursos.html')


@analise_repeticao_bp.route('/api/analise')
def api_analise():
    modo = request.args.get('modo', 'volante')
    return jsonify(AnaliseRepeticaoConcursosService.analisar_completo(modo))


@analise_repeticao_bp.route('/api/concursos')
def api_concursos():
    limite = request.args.get('limit', 120)
    return jsonify({
        'sucesso': True,
        'concursos': AnaliseRepeticaoConcursosService.listar_concursos(limite),
    })


@analise_repeticao_bp.route('/api/concurso/<int:concurso>')
def api_concurso(concurso):
    row = AnaliseRepeticaoConcursosService.obter_concurso(concurso)
    if not row:
        return jsonify({'sucesso': False, 'erro': 'Concurso não encontrado'}), 404
    return jsonify({'sucesso': True, **row})


@analise_repeticao_bp.route('/api/gerar', methods=['POST'])
def api_gerar():
    data = request.get_json(silent=True) or {}
    modo = data.get('modo', 'volante')
    analise = AnaliseRepeticaoConcursosService.analisar_completo(modo)
    if not analise.get('sucesso'):
        return jsonify(analise), 400
    resultado = AnaliseRepeticaoConcursosService.gerar_apostas(
        quantidade=int(data.get('quantidade', 10)),
        dezenas_por_jogo=int(data.get('dezenas_por_jogo', 15)),
        modo=modo,
        perfil=data.get('perfil', 'equilibrado'),
        usar_ultimo_par=bool(data.get('usar_ultimo_par', True)),
        so_permanencia=bool(data.get('so_permanencia', False)),
        respeitar_par_impar=bool(data.get('respeitar_par_impar', True)),
        analise=analise,
    )
    resultado['analise_resumo'] = {
        'ultimo': analise['ultimo_concurso'],
        'penultimo': analise['penultimo_concurso'],
        'repetidas': analise['resumo_ultimo_par']['volante']['dezenas'],
    }
    return jsonify(resultado)
