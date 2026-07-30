# -*- coding: utf-8 -*-
"""Rotas Flask — Concentração de Acertos."""
from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request

from .service import ConcentracaoAcertosService
from .specs import get_concentracao_config, estrategia_esta_ativa, tem_concentracao_acertos
from .ultimo_sorteio import obter_ultimo_sorteio


def _svc(modality_key: str) -> ConcentracaoAcertosService:
    return ConcentracaoAcertosService(modality_key)


def _page_context(modality_key: str) -> dict:
    cfg = get_concentracao_config(modality_key)
    meses_cores = {}
    if cfg.get("extra_mes"):
        try:
            from services.cores_meses_service import CoresMesesService

            meses_cores = CoresMesesService.obter_cores() or {}
        except Exception:
            meses_cores = {}
    ultimo = obter_ultimo_sorteio(modality_key)
    if ultimo and not ultimo.get("sucesso"):
        ultimo = None
    return {
        "modality_key": modality_key,
        "modality_nome": cfg["nome"],
        "conc_cfg": cfg,
        "meses_cores": meses_cores,
        "ultimo_sorteio": ultimo,
    }


def _json_body() -> dict:
    return request.get_json(silent=True) or {}


def register_concentracao_analise(analise_bp: Blueprint, modality_key: str) -> None:
    if not tem_concentracao_acertos(modality_key):
        return

    @analise_bp.route("/concentracao-acertos/")
    def analise_concentracao_acertos_page():
        return render_template("analise_concentracao_acertos.html", **_page_context(modality_key))

    @analise_bp.route("/api/concentracao-acertos/status")
    def api_concentracao_acertos_status():
        ctx = _page_context(modality_key)
        svc = _svc(modality_key)
        st = svc.status_modulo()
        total = st.get("total_sorteios", 0)
        return jsonify({
            "sucesso": True,
            "modulo": "concentracao_acertos",
            "fase": st["fase"],
            "mensagem": st["mensagem"],
            "total_sorteios": total,
            "janelas_sugeridas": [30, 50, 100, 150, 200, 300, 500, 1000, 0],
            "janela_todos": total,
            "cfg": ctx["conc_cfg"],
        })

    @analise_bp.route("/api/concentracao-acertos/concursos")
    def api_concentracao_concursos():
        limite = request.args.get("limit", 150, type=int)
        return jsonify({
            "sucesso": True,
            "concursos": _svc(modality_key).listar_concursos(limite),
        })

    @analise_bp.route("/api/concentracao-acertos/backtest", methods=["POST"])
    def api_concentracao_backtest():
        data = _json_body()
        try:
            res = _svc(modality_key).executar_backtest(
                data.get("estrategia", "A"),
                pool=data.get("pool"),
                criterio_pool=data.get("criterio_pool", "freq"),
                perfil=data.get("perfil", "equilibrado"),
                limite=int(data.get("limite", 50)),
                quantidade=int(data.get("quantidade", 10)),
            )
        except ValueError as exc:
            return jsonify({"sucesso": False, "erro": str(exc)}), 400
        code = 200 if res.get("sucesso") else 400
        return jsonify(res), code

    @analise_bp.route("/api/concentracao-acertos/indice", methods=["GET", "POST"])
    def api_concentracao_indice():
        if request.method == "POST":
            data = _json_body()
        else:
            data = request.args
        try:
            res = _svc(modality_key).indice_atual(
                data.get("estrategia", "A"),
                pool=data.get("pool") if request.method == "POST" else None,
                criterio_pool=data.get("criterio_pool", "freq"),
                perfil=data.get("perfil", "equilibrado"),
                limite=int(data.get("limite", 50)),
            )
        except ValueError as exc:
            return jsonify({"sucesso": False, "erro": str(exc)}), 400
        code = 200 if res.get("sucesso") else 400
        return jsonify(res), code

    @analise_bp.route("/api/concentracao-acertos/comparar")
    def api_concentracao_comparar():
        res = _svc(modality_key).comparar(
            criterio_pool=request.args.get("criterio_pool", "freq"),
            perfil=request.args.get("perfil", "equilibrado"),
            limite=int(request.args.get("limite", 50)),
        )
        return jsonify(res)


def register_concentracao_gerador(bp: Blueprint, modality_key: str, cfg_nome: str) -> None:
    if not tem_concentracao_acertos(modality_key):
        return

    @bp.route("/gerador-concentracao/")
    def gerador_concentracao_page():
        return render_template("gerador_concentracao_acertos.html", **_page_context(modality_key))

    @bp.route("/api/concentracao/config")
    def api_concentracao_config():
        ctx = _page_context(modality_key)
        return jsonify({"sucesso": True, **ctx["conc_cfg"]})

    @bp.route("/api/concentracao/ultimo-sorteio")
    def api_concentracao_ultimo_sorteio():
        ult = obter_ultimo_sorteio(modality_key)
        if not ult or not ult.get("sucesso"):
            return jsonify({"sucesso": False, "erro": "Sem sorteio no banco."}), 404
        return jsonify(ult)

    @bp.route("/api/concentracao/gerar", methods=["POST"])
    def api_concentracao_gerar():
        data = _json_body()
        estrategia = data.get("estrategia", "A")
        if not estrategia_esta_ativa(modality_key, estrategia):
            cfg = get_concentracao_config(modality_key)
            return jsonify({
                "sucesso": False,
                "erro": cfg.get("msg_estrategia_desativada"),
                "estrategia_desativada": True,
            }), 403
        pool = data.get("pool") or []
        try:
            res = _svc(modality_key).gerar(
                estrategia,
                pool=pool if pool else None,
                criterio_pool=data.get("criterio_pool", "freq"),
                perfil=data.get("perfil", "equilibrado"),
                quantidade=int(data.get("quantidade", 10)),
            )
        except ValueError as exc:
            return jsonify({"sucesso": False, "erro": str(exc)}), 400
        except Exception as exc:
            return jsonify({
                "sucesso": False,
                "erro": f"Falha interna ao gerar: {exc}",
            }), 500
        if not res.get("sucesso"):
            return jsonify(res), 400
        try:
            from geradores_elite.validacao.pipeline import pipeline_from_request
            res = pipeline_from_request(
                res,
                modality_key=modality_key,
                origem="concentracao",
                data=data,
            )
        except Exception:
            pass
        return jsonify(res)
