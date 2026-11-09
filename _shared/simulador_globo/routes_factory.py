# -*- coding: utf-8 -*-
"""Rotas do painel de cores e do simulador de globo."""
from __future__ import annotations

import os

from flask import Blueprint, jsonify, render_template, request, send_from_directory

from simulador_globo.historico_service import (
    atualizar,
    caminho_sqlite,
    criar,
    listar,
    obter,
    velocidade_valida,
)
from simulador_globo.regras_globo import (
    AVISO,
    ORDEM_MODALIDADES,
    SorteioEncerrado,
    aplicar_finalizar,
    aplicar_proxima,
    fases_publicas,
    listar_modalidades,
    montar_painel,
    novo_estado,
    previstas_de,
    restantes_globo,
    serializar_fase,
)

_PKG = os.path.dirname(os.path.abspath(__file__))
_STATIC = os.path.join(_PKG, "static")


def _db_path() -> str:
    from flask import current_app

    return caminho_sqlite(current_app.config["SQLALCHEMY_DATABASE_URI"])


def _url_modalidade(key: str) -> str:
    try:
        from configuracoes.public_urls import modality_public_url

        return modality_public_url(
            key,
            "/simulador-globo/",
            request_host=request.host,
            request_scheme=request.scheme,
            request_prefix=request.headers.get("X-Forwarded-Prefix", ""),
        )
    except Exception:
        try:
            from configuracoes.config import MODALITIES
            porta = int((MODALITIES.get(key) or {}).get("porta") or 0)
        except Exception:
            porta = 0
        if not porta:
            return "/simulador-globo/"
        return f"http://127.0.0.1:{porta}/simulador-globo/"


def _publico(registro: dict, evento: dict | None = None) -> dict:
    corpo = {
        "id": registro["id"],
        "modalidade": registro["modalidade"],
        "status": registro["status"],
        "universo": registro["universo"],
        "previstas": registro["sorteadas_previstas"],
        "sorteadas": len(registro["sequencia"]),
        "faltam": max(0, int(registro["sorteadas_previstas"]) - len(registro["sequencia"])),
        "restantes_globo": registro["bolas_restantes"],
        "velocidade_ms": registro["velocidade_ms"],
        "criado_em": registro["criado_em"],
        "sequencia": registro["sequencia"],
        "aviso": AVISO,
    }
    if evento:
        corpo.update({
            "bola": evento["bola"],
            "fase_encerrada": evento["fase_encerrada"],
            "proxima_fase": evento["proxima_fase"],
            "concluida": evento["concluida"],
            "fase_titulo": evento["fase_titulo"],
            "sorteadas": evento["sorteadas"],
            "faltam": evento["faltam"],
            "restantes_globo": evento["restantes_globo"],
        })
    return corpo


def register_simulador_globo(app, modality_key: str) -> None:
    bp = Blueprint("simulador_globo", __name__)

    @bp.route("/")
    def pagina():
        from configuracoes.regras_modalidade import get_regras

        painel = montar_painel(modality_key)
        mods = []
        for item in listar_modalidades():
            item = dict(item)
            item["url"] = _url_modalidade(item["key"])
            item["atual"] = item["key"] == modality_key
            mods.append(item)
        boot = {
            "modalidade": modality_key,
            "nome": get_regras(modality_key)["nome"],
            "aviso": AVISO,
            "painel": painel,
            "modalidades": mods,
            "fases": fases_publicas(modality_key),
            "ordem": list(ORDEM_MODALIDADES),
        }
        return render_template(
            "simulador_globo.html",
            page_title="Painel de Cores",
            modality_key=modality_key,
            modality_nome=boot["nome"],
            boot=boot,
        )

    @bp.route("/static/<path:filename>")
    def estatico(filename):
        return send_from_directory(_STATIC, filename)

    @bp.route("/api/painel/<key>")
    def api_painel(key):
        key = (key or "").strip().lower()
        if key not in ORDEM_MODALIDADES:
            return jsonify({"erro": "Modalidade desconhecida."}), 404
        painel = montar_painel(key)
        painel["url"] = _url_modalidade(key)
        painel["atual"] = key == modality_key
        return jsonify(painel)

    @bp.route("/api/catalogo")
    def api_catalogo():
        mods = []
        for item in listar_modalidades():
            item = dict(item)
            item["url"] = _url_modalidade(item["key"])
            item["atual"] = item["key"] == modality_key
            mods.append(item)
        return jsonify({"modalidades": mods, "aviso": AVISO})

    @bp.route("/api/preparar", methods=["POST"])
    def api_preparar():
        body = request.get_json(silent=True) or {}
        vel = velocidade_valida(body.get("velocidade_ms"))
        estado = novo_estado(modality_key)
        registro = criar(
            _db_path(),
            modality_key,
            estado,
            vel,
            previstas_de(estado),
            restantes_globo(estado),
        )
        corpo = _publico(registro)
        corpo["fase"] = serializar_fase(registro["estado"]["fases"][0])
        return jsonify(corpo)

    @bp.route("/api/proxima", methods=["POST"])
    def api_proxima():
        body = request.get_json(silent=True) or {}
        try:
            sim_id = int(body.get("id"))
        except (TypeError, ValueError):
            return jsonify({"erro": "Simulação inválida."}), 400
        vel = velocidade_valida(body.get("velocidade_ms"), padrao=0)

        def _mut(registro):
            return aplicar_proxima(registro, vel or None)

        try:
            registro = atualizar(_db_path(), sim_id, modality_key, _mut)
        except SorteioEncerrado as exc:
            return jsonify({"erro": str(exc)}), 409
        if registro is None:
            return jsonify({"erro": "Simulação não encontrada."}), 404
        return jsonify(_publico(registro, registro.get("evento")))

    @bp.route("/api/finalizar", methods=["POST"])
    def api_finalizar():
        body = request.get_json(silent=True) or {}
        try:
            sim_id = int(body.get("id"))
        except (TypeError, ValueError):
            return jsonify({"erro": "Simulação inválida."}), 400
        registro = atualizar(_db_path(), sim_id, modality_key, aplicar_finalizar)
        if registro is None:
            return jsonify({"erro": "Simulação não encontrada."}), 404
        corpo = _publico(registro)
        corpo["concluida"] = registro["status"] == "completa"
        return jsonify(corpo)

    @bp.route("/api/velocidade", methods=["POST"])
    def api_velocidade():
        body = request.get_json(silent=True) or {}
        try:
            sim_id = int(body.get("id"))
        except (TypeError, ValueError):
            return jsonify({"erro": "Simulação inválida."}), 400
        vel = velocidade_valida(body.get("velocidade_ms"))

        def _mut(registro):
            registro["velocidade_ms"] = vel
            return registro

        registro = atualizar(_db_path(), sim_id, modality_key, _mut)
        if registro is None:
            return jsonify({"erro": "Simulação não encontrada."}), 404
        return jsonify({"id": sim_id, "velocidade_ms": vel})

    @bp.route("/api/historico")
    def api_historico():
        return jsonify({"itens": listar(_db_path(), modality_key)})

    @bp.route("/api/historico/<int:sim_id>")
    def api_historico_detalhe(sim_id):
        registro = obter(_db_path(), sim_id, modality_key)
        if registro is None:
            return jsonify({"erro": "Simulação não encontrada."}), 404
        corpo = _publico(registro)
        corpo.pop("estado", None)
        return jsonify(corpo)

    app.register_blueprint(bp, url_prefix="/simulador-globo")
