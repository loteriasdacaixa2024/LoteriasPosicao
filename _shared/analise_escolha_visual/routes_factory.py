# -*- coding: utf-8 -*-
"""Rotas Flask — Escolha Visual."""
from __future__ import annotations

import logging
import os
from io import BytesIO
from urllib.parse import quote

from flask import Blueprint, jsonify, render_template, request, send_file, send_from_directory

from analise_escolha_visual.service import AnaliseEscolhaVisualService
from analise_estudos.specs import get_estudos_config, tem_analise_estudos

log = logging.getLogger("lp.estatisticas_excel")

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
_STATIC_DIR = os.path.join(_PKG_DIR, "static")


def _page_context(modality_key: str) -> dict:
    cfg = get_estudos_config(modality_key)
    ui = AnaliseEscolhaVisualService.ui_meta(modality_key)
    meses_cores = {}
    if cfg.get("extra_mes"):
        try:
            from services.cores_meses_service import CoresMesesService
            meses_cores = CoresMesesService.obter_cores() or {}
        except Exception:
            meses_cores = {}
    try:
        from analise_escolha_visual.export_estatisticas import caminho_exibicao
        download_relativo = caminho_exibicao(modality_key)
    except Exception:
        log.exception("Caminho de download indisponível para %s.", modality_key)
        download_relativo = ""
    return {
        "modality_key": modality_key,
        "modality_nome": cfg["nome"],
        "download_relativo": download_relativo,
        "page_title": "Escolha Visual",
        "page_subtitle": "Destaques no volante — pares, ímpares, repetidos, sequências e finais",
        "api_base": "/analise/api/escolha-visual",
        "escolha_ui": ui,
        "meses_cores": meses_cores,
        "gerador_elite_url": "/geradores-elite/",
        "gerador_escolha_url": "/geradores-elite/escolha-tubular-apostas/",
        "escolha_tubular_url": "/geradores-elite/escolha-tubular-apostas/",
        "tubular_url": "/analise/analise-tubular/",
        "tubular_api_base": "/analise/api/inteligentes",
        "tubular_root_class": "d-none",
        "dezena_min": ui["dezena_min"],
        "dezena_max": ui["dezena_max"],
        "sorteadas": ui["sorteadas"],
        "extra_mes": bool(ui.get("extra_mes")),
    }


def register_analise_escolha_visual(analise_bp: Blueprint, modality_key: str) -> None:
    if not tem_analise_estudos(modality_key):
        return

    @analise_bp.route("/escolha-visual/")
    def escolha_visual_page():
        return render_template("analise_escolha_visual.html", **_page_context(modality_key))

    @analise_bp.route("/escolha-visual/static/<path:filename>")
    def escolha_visual_static(filename):
        return send_from_directory(_STATIC_DIR, filename)

    @analise_bp.route("/api/escolha-visual/meta")
    def api_escolha_visual_meta():
        try:
            return jsonify({"sucesso": True, **_page_context(modality_key)})
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @analise_bp.route("/api/escolha-visual/sorteios")
    def api_escolha_visual_sorteios():
        try:
            ordem = request.args.get("ordem", "desc")
            limite = request.args.get("limite", 0, type=int) or 0
            base = request.args.get("base", "geral")
            out = AnaliseEscolhaVisualService.listar_sorteios(
                modality_key, ordem=ordem, limite=limite, base_estatistica=base,
            )
            return jsonify(out), (200 if out.get("sucesso") else 400)
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @analise_bp.route("/api/escolha-visual/enriquecimento")
    def api_escolha_visual_enriquecimento():
        try:
            ordem = request.args.get("ordem", "desc")
            limite = request.args.get("limite", 0, type=int) or 0
            base = request.args.get("base", "geral")
            concurso = request.args.get("concurso", type=int)
            out = AnaliseEscolhaVisualService.enriquecimento(
                modality_key,
                ordem=ordem,
                limite=limite,
                base_estatistica=base,
                concurso=concurso,
            )
            return jsonify(out), (200 if out.get("sucesso") else 400)
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @analise_bp.route("/api/escolha-visual/basicas.xlsx")
    def api_escolha_visual_basicas_xlsx():
        from analise_escolha_visual.export_estatisticas import preparar_download_modalidade

        ordem = request.args.get("ordem", "desc")
        limite = request.args.get("limite", 0, type=int) or 0
        base = request.args.get("base", "geral")
        try:
            res = preparar_download_modalidade(
                modality_key, ordem=ordem, limite=limite, base=base,
            )
        except Exception:
            log.exception("Falha ao exportar estatísticas básicas de %s.", modality_key)
            return jsonify({
                "sucesso": False,
                "mensagem": "Não foi possível gerar o arquivo agora.",
            }), 500
        if not res.get("ok") or not res.get("conteudo"):
            codigo = 404 if res.get("vazio") else 400
            return jsonify({
                "sucesso": False,
                "mensagem": res.get("mensagem") or "Não foi possível gerar o arquivo agora.",
            }), codigo
        bio = BytesIO(res["conteudo"])
        bio.seek(0)
        resp = send_file(
            bio,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=res.get("download_name") or "Estatisticas_Basicas.xlsx",
            max_age=0,
        )
        resp.headers["Cache-Control"] = "no-store"
        if res.get("mensagem"):
            resp.headers["X-Estatisticas-Aviso"] = quote(res["mensagem"])
        if res.get("caminho"):
            resp.headers["X-Estatisticas-Caminho"] = quote(res["caminho"])
        return resp
