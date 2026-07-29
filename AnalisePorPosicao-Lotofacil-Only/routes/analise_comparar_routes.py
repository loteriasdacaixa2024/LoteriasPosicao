from flask import Blueprint, jsonify, render_template, request

from services.analise_repeticao_concursos_service import AnaliseRepeticaoConcursosService

analise_comparar_bp = Blueprint('analise_comparar', __name__, url_prefix='/analise/comparar-concursos')


@analise_comparar_bp.route('/')
def pagina():
    return render_template('analise_comparar_concursos.html')


@analise_comparar_bp.route('/api/comparar')
def api_comparar():
    modo = request.args.get('modo', 'volante')
    ca = request.args.get('concurso_a', type=int)
    cb = request.args.get('concurso_b', type=int)
    return jsonify(AnaliseRepeticaoConcursosService.comparar_concursos(ca, cb, modo))


@analise_comparar_bp.route('/api/concursos')
def api_concursos():
    limite = request.args.get('limit', 150)
    return jsonify({
        'sucesso': True,
        'concursos': AnaliseRepeticaoConcursosService.listar_concursos(limite),
    })
