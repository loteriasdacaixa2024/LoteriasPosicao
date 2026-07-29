# -*- coding: utf-8 -*-
"""Rotas extras da Central de Conferências (conversor + pasta) — aditivas ao blueprint existente."""
import io
import json

from flask import jsonify, request, send_file

from .conversor_service import ConversorApostasService
from .folder_service import ConferenciaApostasFolderService, proximo_concurso, _base_dir
from .config import get_conf


def register_central_conferencias_extras(bp, modality_key: str) -> None:
    """Registra rotas no blueprint `conferencia` já existente do app."""
    if getattr(bp, "_cc_extras_registered", False):
        return
    bp._cc_extras_registered = True
    cfg = get_conf(modality_key)

    def _conversor():
        return ConversorApostasService(modality_key)

    def _folder():
        return ConferenciaApostasFolderService(modality_key)

    @bp.route("/api/proximo-concurso", methods=["GET"])
    def api_proximo_concurso():
        try:
            return jsonify(proximo_concurso(modality_key))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/conversor/upload", methods=["POST"])
    def conversor_upload():
        try:
            if "file" not in request.files:
                return jsonify({"sucesso": False, "erro": "Nenhum arquivo enviado"}), 400
            arquivo = request.files["file"]
            if not arquivo.filename:
                return jsonify({"sucesso": False, "erro": "Arquivo vazio"}), 400
            concurso = int(request.form.get("concurso", 1))
            tipo = "json" if arquivo.filename.lower().endswith(".json") else "txt"
            conteudo = arquivo.read().decode("utf-8")
            resultado = _conversor().processar_arquivo_upload(conteudo, tipo, concurso)
            return jsonify(resultado), (200 if resultado.get("sucesso") else 400)
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/conversor/texto-para-json", methods=["POST"])
    def conversor_texto_para_json():
        try:
            dados = request.get_json() or {}
            texto = dados.get("texto", "").strip()
            if not texto:
                return jsonify({"sucesso": False, "erro": 'Campo "texto" obrigatório'}), 400
            concurso = int(dados.get("concurso", 1))
            svc = _conversor()
            resultado_json = svc.texto_para_json(texto, concurso)
            validacao = svc.validar_apostas(resultado_json)
            return jsonify({"sucesso": True, "dados": resultado_json, "validacao": validacao})
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/conversor/json-para-texto", methods=["POST"])
    def conversor_json_para_texto():
        try:
            dados = request.get_json()
            if not dados:
                return jsonify({"sucesso": False, "erro": "JSON vazio"}), 400
            texto = _conversor().json_para_texto(_conversor().normalizar_json(dados))
            return jsonify({"sucesso": True, "texto": texto})
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/conversor/download/json", methods=["POST"])
    def conversor_download_json():
        try:
            dados = request.get_json()
            if not dados:
                return jsonify({"sucesso": False, "erro": "JSON vazio"}), 400
            json_str = _conversor().formatar_json_download(dados)
            buffer = io.BytesIO(json_str.encode("utf-8"))
            buffer.seek(0)
            return send_file(
                buffer,
                mimetype="application/json",
                as_attachment=True,
                download_name="apostas.json",
            )
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/conversor/download/txt", methods=["POST"])
    def conversor_download_txt():
        try:
            dados = request.get_json()
            if not dados:
                return jsonify({"sucesso": False, "erro": "JSON vazio"}), 400
            texto = _conversor().json_para_texto(_conversor().normalizar_json(dados))
            buffer = io.BytesIO(texto.encode("utf-8"))
            buffer.seek(0)
            return send_file(
                buffer,
                mimetype="text/plain",
                as_attachment=True,
                download_name="apostas.txt",
            )
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/conferencia-apostas/concursos-disponiveis", methods=["GET"])
    def listar_concursos_disponiveis_pasta():
        try:
            concursos = _folder().listar_concursos_disponiveis()
            return jsonify({
                "sucesso": True,
                "total": len(concursos),
                "concursos": concursos,
                "pasta_base": _base_dir(),
                "modalidade": cfg["nome"],
            })
        except Exception as e:
            return jsonify({"sucesso": False, "mensagem": str(e)}), 500

    @bp.route("/api/conferir-txt-historico", methods=["POST"])
    def api_conferir_txt_historico():
        try:
            data = request.get_json(silent=True) or {}
            texto = (data.get("texto") or "").strip()
            if not texto and "file" in request.files:
                arq = request.files["file"]
                texto = arq.read().decode("utf-8", errors="replace").strip()
            min_ac = int(data.get("min_acertos", 11))
            resultado = _folder().conferir_txt_historico(texto, min_acertos=min_ac)
            status = 200 if resultado.get("sucesso") else 400
            return jsonify(resultado), status
        except Exception as e:
            return jsonify({"sucesso": False, "mensagem": str(e)}), 500

    @bp.route("/api/conferencia-apostas/historico-aposta", methods=["POST"])
    def historico_aposta_volante():
        try:
            dados = request.get_json(force=True, silent=True) or {}
            numeros = dados.get("numeros") or []
            min_ac = dados.get("min_acertos")
            resultado = _folder().historico_aposta_volante(numeros, min_acertos=min_ac)
            status = 200 if resultado.get("sucesso") else 400
            return jsonify(resultado), status
        except Exception as e:
            return jsonify({"sucesso": False, "mensagem": str(e)}), 500

    @bp.route("/api/conferencia-apostas/processar/<int:concurso>", methods=["POST"])
    def processar_concurso_pasta(concurso):
        try:
            resultado = _folder().processar_concurso(concurso)
            status = 200 if resultado.get("sucesso") else 400
            return jsonify(resultado), status
        except Exception as e:
            return jsonify({"sucesso": False, "mensagem": str(e)}), 500
