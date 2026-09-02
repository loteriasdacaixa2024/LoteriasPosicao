# -*- coding: utf-8 -*-
"""Rotas Flask — Análises Gerais."""
from __future__ import annotations

import os

from flask import Blueprint, Response, jsonify, render_template, request, send_from_directory

from analise_estudos.comparativo_service import analisar_comparativo
from analise_estudos.export_formatters import formatar_export
from analise_estudos.registry import abas_para_modalidade, get_aba
from analise_estudos.service_factory import make_estudos_base
from analise_estudos.specs import get_estudos_config, tem_analise_estudos

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
_STATIC_DIR = os.path.join(_PKG_DIR, "static")


def _page_context(modality_key: str) -> dict:
    cfg = get_estudos_config(modality_key)
    meses_cores = {}
    if cfg.get("extra_mes"):
        try:
            from services.cores_meses_service import CoresMesesService
            meses_cores = CoresMesesService.obter_cores() or {}
        except Exception:
            try:
                from _shared.diadesorte.meses_cores import obter_meses_cores
                meses_cores = obter_meses_cores() or {}
            except Exception:
                meses_cores = {}
    Base = make_estudos_base(modality_key)
    abas = [
        {
            "id": a.id,
            "titulo": a.titulo,
            "descricao": a.descricao,
            "icone": a.icone,
            "ordem": a.ordem,
        }
        for a in abas_para_modalidade(modality_key)
    ]
    construtor_habilitado = False
    try:
        from geradores_elite.construtor import tem_construtor

        construtor_habilitado = tem_construtor(modality_key)
    except Exception:
        construtor_habilitado = False

    return {
        "modality_key": modality_key,
        "modality_nome": cfg["nome"],
        "estudos_cfg": cfg,
        "estudos_ui": Base.ui_config(),
        "abas": abas,
        "api_base": "/analise/api/analises-gerais",
        "meses_cores": meses_cores,
        "page_title": "Análises Gerais",
        "page_subtitle": cfg.get("page_subtitle", ""),
        "construtor_habilitado": construtor_habilitado,
        "construtor_url": "/geradores-elite/construtor-construcoes/",
    }


def register_analise_estudos(analise_bp: Blueprint, modality_key: str) -> None:
    if not tem_analise_estudos(modality_key):
        return

    @analise_bp.route("/analises-gerais/")
    def analises_gerais_page():
        return render_template("analise_estudos.html", **_page_context(modality_key))

    @analise_bp.route("/analises-gerais/static/<path:filename>")
    def analises_gerais_static(filename):
        return send_from_directory(_STATIC_DIR, filename)

    @analise_bp.route("/api/analises-gerais/meta")
    def api_analises_gerais_meta():
        try:
            ctx = _page_context(modality_key)
            return jsonify({"sucesso": True, **ctx})
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @analise_bp.route("/api/analises-gerais/<aba_id>")
    def api_analises_gerais_aba(aba_id):
        try:
            spec = get_aba(aba_id)
            if modality_key not in spec.modalidades:
                return jsonify({"sucesso": False, "erro": "Aba indisponível nesta modalidade."}), 404
            janela = request.args.get("janela", type=int)
            if janela is None:
                janela = make_estudos_base(modality_key).ui_config()["janela_default"]
            base = request.args.get("base", "geral")
            negativos = request.args.get("negativos", "abs")
            out = spec.service_cls.analisar(
                modality_key, janela=janela, base_estatistica=base,
                **({"negativos_modo": negativos} if aba_id == "diferencial-cruzado" else {}),
            )
            status = 200 if out.get("sucesso") else 400
            return jsonify(out), status
        except KeyError:
            return jsonify({"sucesso": False, "erro": "Aba desconhecida."}), 404
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @analise_bp.route("/api/analises-gerais/<aba_id>/comparativo")
    def api_analises_gerais_comparativo(aba_id):
        try:
            get_aba(aba_id)
            janela = request.args.get("janela", type=int)
            if janela is None:
                janela = make_estudos_base(modality_key).ui_config()["janela_default"]
            out = analisar_comparativo(modality_key, aba_id, janela=janela)
            status = 200 if out.get("sucesso") else 400
            return jsonify(out), status
        except KeyError:
            return jsonify({"sucesso": False, "erro": "Aba desconhecida."}), 404
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @analise_bp.route("/api/analises-gerais/<aba_id>/export")
    def api_analises_gerais_export(aba_id):
        try:
            spec = get_aba(aba_id)
            if modality_key not in spec.modalidades:
                return jsonify({"sucesso": False, "erro": "Aba indisponível nesta modalidade."}), 404
            janela = request.args.get("janela", type=int)
            if janela is None:
                janela = make_estudos_base(modality_key).ui_config()["janela_default"]
            base = request.args.get("base", "geral")
            formato = request.args.get("formato", "txt")
            comparar = request.args.get("comparativo", "").lower() in ("1", "true", "sim", "yes")

            if comparar:
                data = analisar_comparativo(modality_key, aba_id, janela=janela)
            else:
                data = spec.service_cls.analisar(
                    modality_key, janela=janela, base_estatistica=base,
                )
                cfg = get_estudos_config(modality_key)
                data["modality_nome"] = cfg["nome"]
                data["janela_label"] = "Todos" if janela == 0 else f"Últimos {janela}"

            if not data.get("sucesso"):
                return jsonify(data), 400

            tipo = request.args.get("tipo", "completo")
            content, filename, mimetype = formatar_export(aba_id, data, formato, tipo=tipo)
            return Response(
                content,
                mimetype=mimetype,
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
        except ValueError as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 400
        except KeyError:
            return jsonify({"sucesso": False, "erro": "Aba desconhecida."}), 404
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @analise_bp.route("/api/analises-gerais/<aba_id>/concursos")
    def api_analises_gerais_concursos(aba_id):
        try:
            get_aba(aba_id)
            limite = request.args.get("limit", 150, type=int)
            base = request.args.get("base", "geral")
            Base = make_estudos_base(modality_key)
            return jsonify({
                "sucesso": True,
                "concursos": Base.listar_concursos(limite, base),
            })
        except KeyError:
            return jsonify({"sucesso": False, "erro": "Aba desconhecida."}), 404
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500
