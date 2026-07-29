from flask import Blueprint, jsonify, render_template, request

from configuracoes.caixa_live_service import buscar_todos_ao_vivo, limpar_cache
from configuracoes.fmt_utils import parse_preco
from configuracoes.settings_service import (
    listar_perfis_completos,
    listar_todas_modalidades,
    salvar_precos_modalidade,
)


config_central_bp = Blueprint("config_central", __name__)


@config_central_bp.route("/")
def config_central_index():
    perfis = listar_perfis_completos(incluir_caixa_live=False)
    modalidades = listar_todas_modalidades()
    return render_template(
        "config_central.html",
        modalidades=modalidades,
        perfis=perfis,
    )


@config_central_bp.route("/api/modalidades", methods=["GET"])
def api_modalidades():
    return jsonify({"status": "success", "modalidades": listar_todas_modalidades()})


@config_central_bp.route("/api/perfis", methods=["GET"])
def api_perfis():
    refresh = request.args.get("refresh_caixa") == "1"
    return jsonify({"status": "success", "perfis": listar_perfis_completos(refresh_caixa=refresh)})


@config_central_bp.route("/api/preco", methods=["POST"])
def api_salvar_preco():
    data = request.get_json() or {}
    key = data.get("key")
    preco_raw = data.get("preco_simples")
    bolao_raw = data.get("preco_bolao")
    if not key or preco_raw is None:
        return jsonify({"status": "error", "message": "Informe key e preco_simples."}), 400
    try:
        preco_f = parse_preco(preco_raw)
        preco_bolao = parse_preco(bolao_raw) if bolao_raw not in (None, "", "0", "0,00") else None
    except ValueError:
        return jsonify({"status": "error", "message": "Preço inválido."}), 400
    if preco_f <= 0:
        return jsonify({"status": "error", "message": "Preço simples deve ser maior que zero."}), 400
    if not salvar_precos_modalidade(key, preco_f, preco_bolao):
        return jsonify({"status": "error", "message": "Falha ao salvar."}), 500
    return jsonify({
        "status": "success",
        "modalidades": listar_todas_modalidades(),
        "perfis": listar_perfis_completos(),
    })


@config_central_bp.route("/api/atualizar-concursos", methods=["POST"])
def api_atualizar_concursos():
    return jsonify({
        "status": "success",
        "modalidades": listar_todas_modalidades(),
        "perfis": listar_perfis_completos(refresh_caixa=True),
    })


@config_central_bp.route("/api/atualizar-caixa", methods=["POST"])
def api_atualizar_caixa():
    limpar_cache()
    buscar_todos_ao_vivo()
    return jsonify({
        "status": "success",
        "perfis": listar_perfis_completos(refresh_caixa=False, incluir_caixa_live=True),
        "modalidades": listar_todas_modalidades(),
    })
