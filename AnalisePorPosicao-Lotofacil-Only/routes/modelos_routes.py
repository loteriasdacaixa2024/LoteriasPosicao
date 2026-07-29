from flask import Blueprint, render_template, jsonify, request, send_file, make_response
from services.modelos_service import ModelosService
import os
import io

modelos_bp = Blueprint('modelos', __name__)


@modelos_bp.route('/')
def modelos_index():
    modelos = ModelosService.listar_modelos()
    return render_template('modelos.html', modelos=modelos)


@modelos_bp.route('/api/gerar/<int:modelo_id>', methods=['POST'])
def api_gerar_modelo(modelo_id: int):
    """Gera 24 apostas para o modelo especificado (1-6)."""
    if modelo_id not in range(1, 7):
        return jsonify({"error": "Modelo inválido. Use 1-6."}), 400
    try:
        resultado = ModelosService.gerar_apostas_modelo(modelo_id)
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@modelos_bp.route('/api/download/<int:modelo_id>', methods=['POST'])
def api_download_modelo(modelo_id: int):
    """
    Gera 24 apostas e retorna um arquivo .TXT para download,
    no mesmo formato compatível com outros apps (1 aposta por linha).
    """
    if modelo_id not in range(1, 7):
        return jsonify({"error": "Modelo inválido."}), 400
    try:
        resultado = ModelosService.gerar_apostas_modelo(modelo_id)
        if "error" in resultado:
            return jsonify(resultado), 500

        linhas = [" ".join(a["dezenas_formatadas"]) for a in resultado["apostas"]]
        conteudo = "\n".join(linhas)

        nome_arquivo = (
            f"[Modelo{modelo_id}_{resultado['modelo_nome'].replace(' ','_')}]"
            f"_LOTOFACIL_{resultado['ultimo_concurso']}.txt"
        )

        # Salva em docs/ para referência e também envia pro browser
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        docs_dir = os.path.join(base_dir, 'docs')
        os.makedirs(docs_dir, exist_ok=True)
        caminho = os.path.join(docs_dir, nome_arquivo)
        with open(caminho, 'w', encoding='utf-8') as f:
            f.write(conteudo)

        return jsonify({
            "sucesso":      True,
            "arquivo":      nome_arquivo,
            "caminho":      caminho,
            "conteudo_txt": conteudo,
            "apostas":      resultado["apostas"],
            "ultimo_concurso": resultado["ultimo_concurso"],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@modelos_bp.route('/api/backtesting', methods=['POST'])
def api_backtesting():
    """Executa o backtesting histórico para todos os 6 modelos."""
    try:
        resultado = ModelosService.backtesting_modelos()
        res = jsonify(resultado)
        import gc
        gc.collect()
        return res
    except Exception as e:
        return jsonify({"error": str(e)}), 500
