# -*- coding: utf-8 -*-
from flask import Blueprint, jsonify, render_template, request

from _shared.analises_gerais.service import AnalisesGeraisService
from _shared.analises_gerais.sync_all import sincronizar_todas_modalidades
from _shared.analises_gerais.comportamento_panorama import ComportamentoCentralService
from _shared.diadesorte.meses_cores import obter_meses_cores

analises_gerais_bp = Blueprint("analises_gerais", __name__)


@analises_gerais_bp.route("/")
def index():
    return render_template("analises_gerais.html", meses_cores=obter_meses_cores())


@analises_gerais_bp.route("/api/sincronizar-todas", methods=["POST"])
def api_sincronizar_todas():
    try:
        body = request.get_json(silent=True) or {}
        keys = body.get("modalidades")
        sync = sincronizar_todas_modalidades(keys=keys)
        return jsonify({"status": "success", **sync})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@analises_gerais_bp.route("/api/atualizar", methods=["POST"])
def api_atualizar():
    """Sincroniza todas as modalidades na Caixa e devolve o comparativo recalculado."""
    try:
        body = request.get_json(silent=True) or {}
        keys = body.get("modalidades")
        sync = sincronizar_todas_modalidades(keys=keys)
        resumo = AnalisesGeraisService.resumo_completo()
        return jsonify({
            "status": "success",
            "sincronizacao": sync,
            **resumo,
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@analises_gerais_bp.route("/api/resumo", methods=["GET"])
def api_resumo():
    try:
        return jsonify({"status": "success", **AnalisesGeraisService.resumo_completo()})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@analises_gerais_bp.route("/api/comportamento-panorama", methods=["GET"])
def api_comportamento_panorama():
    try:
        janela = request.args.get("janela", 10, type=int)
        return jsonify({
            "status": "success",
            "meses_cores": obter_meses_cores(),
            **ComportamentoCentralService.panorama(janela=janela),
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@analises_gerais_bp.route("/api/comportamento-panorama/<key>", methods=["GET"])
def api_comportamento_panorama_mod(key):
    try:
        janela = request.args.get("janela", 10, type=int)
        return jsonify({
            "status": "success",
            "modalidade": ComportamentoCentralService.panorama_modalidade(key, janela=janela),
        })
    except KeyError:
        return jsonify({"status": "error", "message": "Modalidade inválida."}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@analises_gerais_bp.route("/api/resumo/<key>", methods=["GET"])
def api_resumo_mod(key):
    try:
        return jsonify({
            "status": "success",
            "modalidade": AnalisesGeraisService.resumo_modalidade(key),
        })
    except KeyError:
        return jsonify({"status": "error", "message": "Modalidade inválida."}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
