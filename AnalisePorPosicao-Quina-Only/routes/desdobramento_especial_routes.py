# -*- coding: utf-8 -*-
from datetime import datetime

from flask import Blueprint, Response, jsonify, render_template, request

from services.desdobramento_especial_service import DesdobramentoEspecialQuinaService

desdobramento_especial_bp = Blueprint("desdobramento_especial", __name__)


@desdobramento_especial_bp.route("/")
def index():
    try:
        ciclo = DesdobramentoEspecialQuinaService.obter_ciclo()
    except Exception:
        ciclo = {
            "ciclo_num": 1,
            "dezenas_sorteadas": [],
            "dezenas_faltantes": list(range(1, 81)),
            "total_sorteadas": 0,
            "total_faltantes": 80,
            "concursos_no_ciclo": 0,
        }
    return render_template(
        "desdobramento_especial.html",
        ciclo=ciclo,
        modalidade="Quina",
    )


@desdobramento_especial_bp.route("/api/config", methods=["GET"])
def api_config():
    try:
        return jsonify({"status": "success", **DesdobramentoEspecialQuinaService.obter_config()})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@desdobramento_especial_bp.route("/api/ciclo", methods=["GET"])
def api_ciclo():
    try:
        return jsonify({"status": "success", **DesdobramentoEspecialQuinaService.obter_ciclo()})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@desdobramento_especial_bp.route("/api/sugestoes-colunas", methods=["GET"])
def api_sugestoes():
    try:
        return jsonify({
            "status": "success",
            "sugestoes": DesdobramentoEspecialQuinaService.obter_sugestoes_colunas(),
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@desdobramento_especial_bp.route("/api/orientacao", methods=["GET", "POST"])
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
            **DesdobramentoEspecialQuinaService.orientacao(modo, meta_i, cols),
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@desdobramento_especial_bp.route("/api/preview-montagem", methods=["POST"])
def api_preview_montagem():
    try:
        data = request.get_json() or {}
        colunas = [int(c) for c in data.get("colunas", [])]
        modo = data.get("modo", "par")
        col_simples = data.get("coluna_simples")
        col_simples = int(col_simples) if col_simples is not None else None
        preview = DesdobramentoEspecialQuinaService.preview_montagem(
            colunas, modo, col_simples
        )
        return jsonify({"status": "success", **preview})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@desdobramento_especial_bp.route("/api/desdobrar-colunas", methods=["POST"])
def api_desdobrar_colunas():
    try:
        data = request.get_json() or {}
        colunas = [int(c) for c in data.get("colunas", [])]
        if not colunas:
            return jsonify({"status": "error", "message": "Selecione ao menos uma coluna."}), 400
        return jsonify({
            "status": "success",
            **DesdobramentoEspecialQuinaService.preview_colunas(colunas),
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@desdobramento_especial_bp.route("/api/gerar", methods=["POST"])
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

        resultado = DesdobramentoEspecialQuinaService.gerar(
            colunas, modo, col_simples, dezena_s, garantia=garantia
        )

        if data.get("salvar"):
            nome = data.get("nome") or f"Quina Especial {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            resultado["id_salvo"] = DesdobramentoEspecialQuinaService.salvar(nome, resultado)
            resultado["nome"] = nome

        return jsonify({"status": "success", **resultado})
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@desdobramento_especial_bp.route("/api/exportar", methods=["POST"])
def api_exportar():
    try:
        data = request.get_json() or {}
        resultado = data.get("resultado")
        if not resultado:
            return jsonify({"status": "error", "message": "Resultado ausente."}), 400
        nome = data.get("nome") or "Quina_Especial"
        txt = DesdobramentoEspecialQuinaService.exportar_txt(resultado, nome)
        return Response(
            txt,
            mimetype="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{nome.replace(" ", "_")}.txt"'
            },
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
