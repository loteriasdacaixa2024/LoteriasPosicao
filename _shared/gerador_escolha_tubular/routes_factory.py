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
        if not ctx.get("sucesso"):
            from geradores_elite.modality_config import MODALITIES
            mod = MODALITIES.get(modality_key) or {}
            vcols = 10
            try:
                from analise_estudos.specs import get_estudos_config
                vcols = int(get_estudos_config(modality_key).get("volante_cols") or 10)
            except Exception:
                vcols = 5 if modality_key == "lotofacil" else 10
            ctx = {
                "dezena_min": int(mod.get("dezena_min", 1)),
                "dezena_max": int(mod.get("dezena_max", 31)),
                "sorteadas": int(mod.get("sorteadas", mod.get("pick_default", 7))),
                "pick_default": int(mod.get("pick_default", mod.get("sorteadas", 7))),
                "pick_min": int(mod.get("pick_min", mod.get("pick_default", 7))),
                "pick_max": int(mod.get("pick_max", mod.get("pick_default", 7))),
                "extra_mes": mod.get("extra") == "mes" or modality_key == "diadesorte",
                "extra_time": mod.get("extra") == "time" or modality_key == "timemania",
                "extra_trevo": mod.get("extra") == "trevo" or modality_key == "maismilionaria",
                "volante_cols": vcols,
            }
        meses_cores = {}
        if ctx.get("extra_mes"):
            try:
                from services.cores_meses_service import CoresMesesService
                meses_cores = CoresMesesService.obter_cores() or {}
            except Exception:
                meses_cores = {}
        aba_raw = (request.args.get("aba") or "escolha").strip().lower()
        if aba_raw in ("manual", "s10", "secao10", "seção10", "secao-10"):
            aba_inicial = "manual"
        elif aba_raw in ("automatico", "automático", "s11", "secao11", "seção11", "secao-11", "auto"):
            aba_inicial = "automatico"
        elif aba_raw in ("comparador", "s12", "secao12", "seção12", "secao-12", "volante", "volantes"):
            aba_inicial = "comparador"
        elif aba_raw in ("diagonais", "diagonal", "s13", "secao13", "seção13", "secao-13"):
            aba_inicial = "diagonais"
        else:
            aba_inicial = "escolha"
        return render_template(
            "gerador_escolha_tubular.html",
            modality_key=modality_key,
            modality_nome=modality_nome,
            page_title="Escolha/Tubular → Apostas",
            page_subtitle="Escolha Visual · Seção 10 Manual · Seção 11 Automático · Seção 12 Volantes · Seção 13 Diagonais",
            api_base="/geradores-elite/api/escolha-tubular",
            tubular_api_base="/analise/api/inteligentes",
            ctx=ctx,
            meses_cores=meses_cores,
            escolha_url="/analise/escolha-visual/",
            tubular_url="/analise/analise-tubular/",
            sequencias_url="/analise/analises-inteligentes/?aba=tubular",
            dezena_min=int(ctx.get("dezena_min") or 1),
            dezena_max=int(ctx.get("dezena_max") or 31),
            sorteadas=int(ctx.get("sorteadas") or 7),
            extra_mes=bool(ctx.get("extra_mes")),
            extra_time=bool(ctx.get("extra_time")),
            extra_trevo=bool(ctx.get("extra_trevo")),
            aba_inicial=aba_inicial,
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
                mes_num=data.get("mes_num") if data.get("mes_num") not in (None, "", 0, "0") else None,
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
