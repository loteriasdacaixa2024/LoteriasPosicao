# -*- coding: utf-8 -*-
"""Rotas Flask — Análise Gaps/Ciclo e Gerador de Apostas."""
from __future__ import annotations

import os

from flask import Blueprint, jsonify, render_template, request, send_from_directory

from analise_gaps_ciclo.gerador import gerar_apostas
from analise_gaps_ciclo.service import contexto_analise, projetar_ciclo
from analise_gaps_ciclo.specs import get_gaps_ciclo_spec, tem_gaps_ciclo

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
_STATIC_DIR = os.path.join(_PKG_DIR, "static")


def _meses_cores(spec: dict) -> dict:
    if not spec.get("extra_mes"):
        return {}
    try:
        from services.cores_meses_service import CoresMesesService
        return CoresMesesService.obter_cores() or {}
    except Exception:
        return {}


def _page_analise(modality_key: str) -> dict:
    spec = get_gaps_ciclo_spec(modality_key)
    return {
        "modality_key": modality_key,
        "modality_nome": spec["nome"],
        "page_title": "Análise por Gaps e Ciclo",
        "page_subtitle": "Sessão 1 · Gaps  ·  Sessão 2 · Inicial + Ciclo",
        "api_base": "/analise/api/gaps-ciclo",
        "gerador_url": spec["gerador_url"],
        "gc_spec": spec,
        "meses_cores": _meses_cores(spec),
    }


def _page_gerador(modality_key: str) -> dict:
    spec = get_gaps_ciclo_spec(modality_key)
    return {
        "modality_key": modality_key,
        "modality_nome": spec["nome"],
        "page_title": "Gaps e Ciclo → Apostas",
        "page_subtitle": "Fonte das análises · Sessão 1 e/ou Sessão 2",
        "api_base": "/geradores-elite/api/gaps-ciclo",
        "analise_url": spec["analise_url"],
        "gc_spec": spec,
        "meses_cores": _meses_cores(spec),
        "has_mes": bool(spec.get("extra_mes")),
    }


def register_analise_gaps_ciclo(analise_bp: Blueprint, modality_key: str) -> None:
    if not tem_gaps_ciclo(modality_key):
        return

    @analise_bp.route("/gaps-ciclo/")
    def gaps_ciclo_page():
        return render_template("analise_gaps_ciclo.html", **_page_analise(modality_key))

    @analise_bp.route("/gaps-ciclo/static/<path:filename>")
    def gaps_ciclo_static(filename):
        return send_from_directory(_STATIC_DIR, filename)

    @analise_bp.route("/api/gaps-ciclo/contexto")
    def api_gaps_ciclo_contexto():
        janela = request.args.get("janela", 0, type=int) or 0
        base = request.args.get("base", "geral")
        inicial = request.args.get("inicial", type=int)
        perfil = request.args.get("perfil", "ultimo")
        padrao = request.args.get("padrao") or None
        leitura = request.args.get("leitura") or "ambos"
        out = contexto_analise(
            modality_key, janela=janela, base=base,
            inicial=inicial, perfil=perfil, padrao=padrao, leitura=leitura,
        )
        return jsonify(out), (200 if out.get("sucesso") else 400)

    @analise_bp.route("/api/gaps-ciclo/projetar")
    def api_gaps_ciclo_projetar():
        inicial = request.args.get("inicial", type=int)
        if inicial is None:
            return jsonify({"sucesso": False, "erro": "Informe o número inicial."}), 400
        out = projetar_ciclo(
            modality_key,
            inicial,
            janela=request.args.get("janela", 0, type=int) or 0,
            base=request.args.get("base", "geral"),
            perfil=request.args.get("perfil", "ultimo"),
            padrao=request.args.get("padrao") or None,
            leitura=request.args.get("leitura") or "classificado",
        )
        return jsonify(out), (200 if out.get("sucesso") else 400)


def register_gerador_gaps_ciclo(bp: Blueprint, modality_key: str, modality_nome: str) -> None:
    if not tem_gaps_ciclo(modality_key):
        return

    @bp.route("/gaps-ciclo-apostas/")
    def gaps_ciclo_apostas_page():
        return render_template("gerador_gaps_ciclo.html", **_page_gerador(modality_key))

    @bp.route("/gaps-ciclo-apostas/static/<path:filename>")
    def gaps_ciclo_apostas_static(filename):
        return send_from_directory(_STATIC_DIR, filename)

    @bp.route("/api/gaps-ciclo/contexto")
    def api_ge_gaps_ciclo_contexto():
        janela = request.args.get("janela", 0, type=int) or 0
        base = request.args.get("base", "geral")
        inicial = request.args.get("inicial", type=int)
        out = contexto_analise(
            modality_key, janela=janela, base=base, inicial=inicial,
            leitura=request.args.get("leitura") or "ambos",
        )
        return jsonify(out), (200 if out.get("sucesso") else 400)

    @bp.route("/api/gaps-ciclo/gerar", methods=["POST"])
    def api_ge_gaps_ciclo_gerar():
        data = request.get_json(silent=True) or {}
        try:
            out = gerar_apostas(
                modality_key,
                sessao1=bool(data.get("sessao1", True)),
                sessao2=bool(data.get("sessao2", True)),
                inicial=data.get("inicial"),
                perfil=data.get("perfil") or "ultimo",
                padrao=data.get("padrao"),
                padroes=data.get("padroes"),
                janela=int(data.get("janela") or 0),
                base=data.get("base") or "geral",
                quantidade=int(data.get("quantidade") or 10),
                mes_num=data.get("mes_num") or data.get("mes"),
                leitura=data.get("leitura") or "ambos",
            )
            from geradores_elite.validacao.pipeline import pipeline_from_request
            out = pipeline_from_request(
                out, modality_key=modality_key, origem="gaps_ciclo", data=data,
            )
            return jsonify(out), (200 if out.get("ok") or out.get("sucesso") else 400)
        except Exception as e:
            return jsonify({"sucesso": False, "ok": False, "erro": str(e)}), 500
