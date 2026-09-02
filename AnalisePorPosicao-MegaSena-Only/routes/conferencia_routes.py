import io
import json

from flask import Blueprint, render_template, jsonify, request, send_file
from sqlalchemy import desc, func

from models.shared import db
from models.sorteio_megasena import SorteioMegaSena
from services.analise_megasena_service import AnaliseMegaSenaService
from services.conversor_apostas_service import ConversorApostasService
from services.conferencia_apostas_folder_service import (
    ConferenciaApostasFolderService,
    BASE_DIR as CONFERENCIA_APOSTAS_DIR,
)

conferencia_bp = Blueprint('conferencia', __name__)

@conferencia_bp.route('/')
def conferencia_index():
    return render_template('conferencia.html')

@conferencia_bp.route('/api/conferir', methods=['POST'])
def api_conferir():
    """Confere últimos 200 concursos contra aposta Sniper (top-6 mais frequentes)."""
    try:
        analise = AnaliseMegaSenaService.analise_geral()
        if not analise:
            return jsonify({"status":"error","message":"Sem dados no banco."}), 404

        aposta_sniper = sorted(
            [d["dezena"] for d in sorted(analise["dados"], key=lambda x: -x["freq"])[:6]]
        )
        sniper_set = set(aposta_sniper)

        sorteios = db.session.query(SorteioMegaSena).order_by(
            desc(SorteioMegaSena.concurso)
        ).all()

        resultados = []
        for s in sorteios:
            sorteadas = s.dezenas_lista()
            acertos   = len(sniper_set & set(sorteadas))
            resultados.append({
                "concurso":      s.concurso,
                "data":          s.data,
                "dezenas":       sorteadas,
                "aposta_sniper": aposta_sniper,
                "acertos":       acertos,
            })

        return jsonify({"status":"success","resultados":resultados})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500


@conferencia_bp.route('/api/proximo-concurso', methods=['GET'])
def api_proximo_concurso():
    """Último concurso gravado no banco local + 1 (ex.: 3010 → 3011)."""
    try:
        ultimo_banco = db.session.query(func.max(SorteioMegaSena.concurso)).scalar()
        if ultimo_banco is None:
            return jsonify({
                "sucesso": False,
                "erro": "Nenhum concurso no banco. Sincronize os sorteios na página inicial.",
            }), 404
        ultimo_banco = int(ultimo_banco)
        proximo = ultimo_banco + 1
        return jsonify({
            "sucesso": True,
            "ultimo_concurso_banco": ultimo_banco,
            "proximo_concurso": proximo,
        })
    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 500


@conferencia_bp.route('/api/conversor/upload', methods=['POST'])
def conversor_upload():
    try:
        if 'file' not in request.files:
            return jsonify({'sucesso': False, 'erro': 'Nenhum arquivo enviado'}), 400
        arquivo = request.files['file']
        if not arquivo.filename:
            return jsonify({'sucesso': False, 'erro': 'Arquivo vazio'}), 400

        concurso = int(request.form.get('concurso', 1))
        tipo = 'json' if arquivo.filename.lower().endswith('.json') else 'txt'
        conteudo = arquivo.read().decode('utf-8')
        resultado = ConversorApostasService.processar_arquivo_upload(conteudo, tipo, concurso)
        return jsonify(resultado), (200 if resultado.get('sucesso') else 400)
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@conferencia_bp.route('/api/conversor/texto-para-json', methods=['POST'])
def conversor_texto_para_json():
    try:
        dados = request.get_json() or {}
        texto = dados.get('texto', '').strip()
        if not texto:
            return jsonify({'sucesso': False, 'erro': 'Campo "texto" obrigatório'}), 400
        concurso = int(dados.get('concurso', 1))
        resultado_json = ConversorApostasService.texto_para_json(texto, concurso)
        validacao = ConversorApostasService.validar_apostas(resultado_json)
        return jsonify({'sucesso': True, 'dados': resultado_json, 'validacao': validacao})
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@conferencia_bp.route('/api/conversor/json-para-texto', methods=['POST'])
def conversor_json_para_texto():
    try:
        dados = request.get_json()
        if not dados:
            return jsonify({'sucesso': False, 'erro': 'JSON vazio'}), 400
        dados = ConversorApostasService.normalizar_json(dados)
        texto = ConversorApostasService.json_para_texto(dados)
        return jsonify({'sucesso': True, 'texto': texto})
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@conferencia_bp.route('/api/conversor/download/json', methods=['POST'])
def conversor_download_json():
    try:
        dados = request.get_json()
        if not dados:
            return jsonify({'sucesso': False, 'erro': 'JSON vazio'}), 400
        dados = ConversorApostasService.normalizar_json(dados)
        json_str = ConversorApostasService.formatar_json_download(dados)
        buffer = io.BytesIO(json_str.encode('utf-8'))
        buffer.seek(0)
        return send_file(buffer, mimetype='application/json', as_attachment=True, download_name='apostas.json')
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@conferencia_bp.route('/api/conferencia-apostas/concursos-disponiveis', methods=['GET'])
def listar_concursos_disponiveis_pasta():
    try:
        concursos = ConferenciaApostasFolderService.listar_concursos_disponiveis()
        return jsonify({
            "sucesso": True,
            "total": len(concursos),
            "concursos": concursos,
            "pasta_base": CONFERENCIA_APOSTAS_DIR,
        })
    except Exception as e:
        return jsonify({"sucesso": False, "mensagem": str(e)}), 500


@conferencia_bp.route('/api/conferencia-apostas/historico-aposta', methods=['POST'])
def historico_aposta_volante():
    """
    Histórico de uma combinação (volante completo) no banco Mega-Sena.
    Retorna concursos em que houve ao menos 4 acertos (Quadra+).
    """
    try:
        dados = request.get_json(force=True, silent=True) or {}
        numeros = dados.get("numeros") or []
        if not numeros:
            return jsonify({"sucesso": False, "mensagem": "Nenhum número informado."}), 400

        resultado = ConferenciaApostasFolderService.historico_aposta_volante(numeros, min_acertos=4)
        status = 200 if resultado.get("sucesso") else 400
        return jsonify(resultado), status
    except Exception as e:
        return jsonify({"sucesso": False, "mensagem": str(e)}), 500


@conferencia_bp.route('/api/conferencia-apostas/processar/<int:concurso>', methods=['POST'])
def processar_concurso_pasta(concurso):
    try:
        resultado = ConferenciaApostasFolderService.processar_concurso(concurso)
        status = 200 if resultado.get("sucesso") else 400
        return jsonify(resultado), status
    except Exception as e:
        return jsonify({"sucesso": False, "mensagem": str(e)}), 500


@conferencia_bp.route('/api/conferencia-apostas/exportar/<int:concurso>', methods=['GET'])
def exportar_relatorio_concurso(concurso):
    """Exporta relatório do concurso em CSV ou JSON."""
    formato = (request.args.get("formato") or "json").lower()
    try:
        resultado = ConferenciaApostasFolderService.processar_concurso(concurso)
        if not resultado.get("sucesso"):
            return jsonify(resultado), 400

        if formato == "json":
            buffer = io.BytesIO(
                json.dumps(resultado, ensure_ascii=False, indent=2).encode("utf-8")
            )
            buffer.seek(0)
            return send_file(
                buffer,
                mimetype="application/json",
                as_attachment=True,
                download_name=f"concurso_{concurso}_relatorio.json",
            )

        import csv
        buf = io.StringIO()
        writer = csv.writer(buf, delimiter=";")
        writer.writerow([
            "concurso", "aposta", "numeros", "acertos", "valor_aposta", "valor_ganho", "faixa",
        ])
        for ap in resultado.get("apostas", []):
            writer.writerow([
                concurso,
                ap.get("numero_aposta"),
                " ".join(str(n) for n in (ap.get("numeros_apostados") or [])),
                ap.get("acertos"),
                ap.get("valor_aposta"),
                ap.get("valor_ganho"),
                ap.get("premiacao"),
            ])
        out = io.BytesIO(buf.getvalue().encode("utf-8-sig"))
        out.seek(0)
        return send_file(
            out,
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"concurso_{concurso}_relatorio.csv",
        )
    except Exception as e:
        return jsonify({"sucesso": False, "mensagem": str(e)}), 500


@conferencia_bp.route('/api/conversor/download/txt', methods=['POST'])
def conversor_download_txt():
    try:
        dados = request.get_json()
        if not dados:
            return jsonify({'sucesso': False, 'erro': 'JSON vazio'}), 400
        dados = ConversorApostasService.normalizar_json(dados)
        texto = ConversorApostasService.json_para_texto(dados)
        buffer = io.BytesIO(texto.encode('utf-8'))
        buffer.seek(0)
        return send_file(buffer, mimetype='text/plain', as_attachment=True, download_name='apostas.txt')
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500
