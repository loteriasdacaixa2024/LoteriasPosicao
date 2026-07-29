import os
import sys

_SHARED = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from flask import Blueprint, render_template, request, jsonify
from services.cores_meses_service import CoresMesesService
from configuracoes.caixa_live_service import limpar_cache
from configuracoes.settings_service import buscar_concurso_remoto, montar_perfil_completo

config_bp = Blueprint('config', __name__)

@config_bp.route('/')
def index():
    cores = CoresMesesService.obter_cores()
    conc = buscar_concurso_remoto('diadesorte')
    perfil = montar_perfil_completo('diadesorte', conc, incluir_caixa_live=True)
    return render_template(
        'configuracao.html',
        cores=cores,
        cfg=perfil,
        perfil=perfil,
        central_url='http://localhost:8083/configuracoes/',
    )

@config_bp.route('/api/atualizar-caixa', methods=['POST'])
def api_atualizar_caixa():
    limpar_cache('diadesorte')
    conc = buscar_concurso_remoto('diadesorte')
    perfil = montar_perfil_completo('diadesorte', conc, incluir_caixa_live=True)
    return jsonify({'status': 'success', 'perfil': perfil})


@config_bp.route('/api/cores', methods=['POST'])
def salvar_cores():
    try:
        dados = request.json
        if not dados:
            return jsonify({"status": "error", "message": "Nenhum dado enviado."}), 400
            
        sucesso = CoresMesesService.salvar_cores(dados)
        if sucesso:
            return jsonify({"status": "success", "message": "Cores salvas com sucesso!"})
        else:
            return jsonify({"status": "error", "message": "Erro ao salvar no arquivo."}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
