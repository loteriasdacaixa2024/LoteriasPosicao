# -*- coding: utf-8 -*-
"""Rotas — Gerador Escolha/Tubular no blueprint Geradores Elite."""
from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request

from gerador_escolha_tubular.service import (
    contexto_gerador,
    gerar_apostas,
    tem_gerador_escolha_tubular,
)


def register_gerador_escolha_tubular(bp: Blueprint, modality_key: str, modality_nome: str) -> None:
    if not tem_gerador_escolha_tubular(modality_key):
        return

    @bp.route("/escolha-tubular-apostas/")
    def escolha_tubular_apostas_page():
        ctx = contexto_gerador(modality_key, janela=0, base="geral")
        meses_cores = {}
        if ctx.get("extra_mes"):
            try:
                from services.cores_meses_service import CoresMesesService
                meses_cores = CoresMesesService.obter_cores() or {}
            except Exception:
                meses_cores = {}
        return render_template(
            "gerador_escolha_tubular.html",
            modality_key=modality_key,
            modality_nome=modality_nome,
            page_title="Escolha/Tubular → Apostas",
            page_subtitle="Cada aposta reproduz o perfil completo de um concurso (pares, sequência, finais, repetidos…)",
            api_base="/geradores-elite/api/escolha-tubular",
            ctx=ctx if ctx.get("sucesso") else {},
            meses_cores=meses_cores,
            escolha_url="/analise/escolha-visual/",
            tubular_url="/analise/analise-tubular/",
        )

    @bp.route("/api/escolha-tubular/contexto")
    def api_escolha_tubular_contexto():
        janela = request.args.get("janela", 0, type=int) or 0
        base = request.args.get("base", "geral")
        concurso = request.args.get("concurso", type=int)
        out = contexto_gerador(
            modality_key, janela=janela, base=base, concurso_ref=concurso,
        )
        return jsonify(out), (200 if out.get("sucesso") else 400)

    @bp.route("/api/escolha-tubular/gerar", methods=["POST"])
    def api_escolha_tubular_gerar():
        data = request.get_json(silent=True) or {}
        try:
            out = gerar_apostas(
                modality_key,
                quantidade=int(data.get("quantidade") or 10),
                pick=int(data["pick"]) if data.get("pick") is not None else None,
                janela=int(data.get("janela") or 0),
                base=data.get("base") or "geral",
                concurso_ref=int(data["concurso_ref"]) if data.get("concurso_ref") not in (None, "", 0, "0") else None,
                usar_pares_impares=bool(data.get("usar_pares_impares", True)),
                usar_soma=bool(data.get("usar_soma", False)),
                usar_sequencia=bool(data.get("usar_sequencia", True)),
                usar_finais=bool(data.get("usar_finais", True)),
                usar_repetidos=bool(data.get("usar_repetidos", True)),
                usar_digitos=bool(data.get("usar_digitos", True)),
                mes_num=int(data["mes_num"]) if data.get("mes_num") not in (None, "", 0, "0") else None,
                ancora_padrao=str(data.get("ancora_padrao") or "").strip().lower() or None,
                dezenas_altas=bool(data.get("dezenas_altas", False)),
            )
        except Exception as e:
            return jsonify({"sucesso": False, "ok": False, "erro": str(e)}), 500

        if out.get("sucesso"):
            try:
                from geradores_elite.validacao.pipeline import pipeline_from_request
                out = pipeline_from_request(
                    out,
                    modality_key=modality_key,
                    origem="escolha_tubular",
                    data=data,
                )
            except Exception:
                pass
        return jsonify(out), (200 if out.get("sucesso") else 400)
