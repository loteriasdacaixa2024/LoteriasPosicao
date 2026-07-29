# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Type

from flask import Blueprint, Response, jsonify, render_template, request

from _shared.desdobramento_especial.configs import get_config


def create_desdobramento_especial_blueprint(service_class: Type) -> Blueprint:
    slug = service_class.SLUG
    cfg = get_config(slug)
    bp = Blueprint(f"desdobramento_especial_{slug}", __name__)

    def _ciclo_fallback():
        total = cfg.ciclo_total
        return {
            "ciclo_num": 1,
            "dezenas_sorteadas": [],
            "dezenas_faltantes": list(range(1, total + 1)),
            "total_sorteadas": 0,
            "total_faltantes": total,
            "concursos_no_ciclo": 0,
        }

    @bp.route("/")
    def index():
        try:
            ciclo = service_class.obter_ciclo()
        except Exception:
            ciclo = _ciclo_fallback()
        page = {
            "slug": slug,
            "titulo": cfg.titulo_especial,
            "emoji": cfg.emoji,
            "min_dezenas": cfg.min_dezenas,
            "max_dezenas": cfg.max_dezenas,
            "min_colunas": cfg.min_colunas,
            "volante_linhas": cfg.volante_linhas,
            "colunas_header": cfg.colunas_header,
            "layout": cfg.layout,
            "max_dezena": cfg.max_dezena,
            "ciclo_total": cfg.ciclo_total,
            "nota_aposta": cfg.nota_aposta,
            "sorteio_bolas": cfg.sorteio_bolas,
        }
        return render_template(
            "desdobramento_especial.html",
            ciclo=ciclo,
            page=page,
        )

    @bp.route("/api/config", methods=["GET"])
    def api_config():
        try:
            return jsonify({"status": "success", **service_class.obter_config()})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    @bp.route("/api/ciclo", methods=["GET"])
    def api_ciclo():
        try:
            return jsonify({"status": "success", **service_class.obter_ciclo()})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    @bp.route("/api/ultimos", methods=["GET"])
    def api_ultimos():
        try:
            sorteios = service_class.obter_ultimos_sorteios()
            return jsonify({"status": "success", "sorteios": sorteios})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    @bp.route("/api/sugestoes-colunas", methods=["GET"])
    def api_sugestoes():
        try:
            return jsonify({
                "status": "success",
                "sugestoes": service_class.obter_sugestoes_colunas(),
            })
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    @bp.route("/api/orientacao", methods=["GET", "POST"])
    def api_orientacao():
        try:
            if request.method == "POST":
                data = request.get_json() or {}
                modo = data.get("modo", "par")
                meta = data.get("meta_dezenas")
                colunas = data.get("colunas", [])
            else:
                modo = request.args.get("modo", "par")
                meta = request.args.get("meta_dezenas", type=int)
                colunas = request.args.getlist("colunas") or []
            meta_i = int(meta) if meta is not None else None
            cols = [int(c) for c in colunas] if colunas else None
            return jsonify({
                "status": "success",
                **service_class.orientacao(modo, meta_i, cols),
            })
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    @bp.route("/api/preview-montagem", methods=["POST"])
    def api_preview_montagem():
        try:
            data = request.get_json() or {}
            colunas = [int(c) for c in data.get("colunas", [])]
            modo = data.get("modo", "par")
            col_simples = data.get("coluna_simples")
            col_simples = int(col_simples) if col_simples is not None else None
            return jsonify({
                "status": "success",
                **service_class.preview_montagem(colunas, modo, col_simples),
            })
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    @bp.route("/api/gerar", methods=["POST"])
    def api_gerar():
        try:
            data = request.get_json() or {}
            colunas = [int(c) for c in data.get("colunas", [])]
            modo = (data.get("modo") or "par").lower()
            col_simples = data.get("coluna_simples")
            col_simples = int(col_simples) if col_simples is not None else None
            dezena_s = data.get("dezena_simples")
            dezena_s = int(dezena_s) if dezena_s is not None else None
            garantia = (data.get("garantia") or "diamante").lower()
            resultado = service_class.gerar(
                colunas, modo, col_simples, dezena_s, garantia=garantia
            )
            if data.get("salvar"):
                nome = data.get("nome") or (
                    f"{cfg.titulo_especial} {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                )
                resultado["id_salvo"] = service_class.salvar(nome, resultado)
                resultado["nome"] = nome
            return jsonify({"status": "success", **resultado})
        except ValueError as e:
            return jsonify({"status": "error", "message": str(e)}), 400
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    @bp.route("/api/exportar", methods=["POST"])
    def api_exportar():
        try:
            data = request.get_json() or {}
            resultado = data.get("resultado")
            if not resultado:
                return jsonify({"status": "error", "message": "Resultado ausente."}), 400
            nome = data.get("nome") or cfg.titulo_especial.replace(" ", "_")
            txt = service_class.exportar_txt(resultado, nome)
            return Response(
                txt,
                mimetype="text/plain; charset=utf-8",
                headers={
                    "Content-Disposition": f'attachment; filename="{nome.replace(" ", "_")}.txt"'
                },
            )
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    return bp
