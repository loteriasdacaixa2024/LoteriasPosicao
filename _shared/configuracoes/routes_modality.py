from flask import Blueprint, jsonify, render_template

from configuracoes.caixa_live_service import limpar_cache
from configuracoes.settings_service import (
    buscar_concurso_remoto,
    montar_perfil_completo,
)


def build_config_blueprint(modality_key: str, nome_exibicao=None):
    config_bp = Blueprint("config", __name__)

    @config_bp.route("/")
    def config_index():
        conc = buscar_concurso_remoto(modality_key)
        perfil = montar_perfil_completo(modality_key, conc, incluir_caixa_live=True)
        return render_template(
            "config_local.html",
            perfil=perfil,
            cfg=perfil,
            modality_key=modality_key,
            central_url="http://localhost:8083/configuracoes/",
        )

    @config_bp.route("/api/dados", methods=["GET"])
    def api_dados():
        conc = buscar_concurso_remoto(modality_key)
        return jsonify({"status": "success", "cfg": montar_perfil_completo(modality_key, conc)})

    @config_bp.route("/api/perfil", methods=["GET"])
    def api_perfil():
        conc = buscar_concurso_remoto(modality_key)
        return jsonify({"status": "success", "perfil": montar_perfil_completo(modality_key, conc)})

    @config_bp.route("/api/atualizar-caixa", methods=["POST"])
    def api_atualizar_caixa():
        limpar_cache(modality_key)
        conc = buscar_concurso_remoto(modality_key)
        return jsonify({
            "status": "success",
            "perfil": montar_perfil_completo(modality_key, conc, incluir_caixa_live=True),
        })

    return config_bp
