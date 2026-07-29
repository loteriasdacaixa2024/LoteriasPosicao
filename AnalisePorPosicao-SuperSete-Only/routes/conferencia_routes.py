from flask import Blueprint, render_template, jsonify
from models.shared import db
from models.sorteio_supersete import SorteioSuperSete
from services.analise_supersete_service import AnaliseSuperSeteService
from sqlalchemy import desc

conferencia_bp = Blueprint('conferencia', __name__)

@conferencia_bp.route('/')
def conferencia_index():
    return render_template('conferencia.html')

@conferencia_bp.route('/api/conferir', methods=['POST'])
def api_conferir():
    """
    Confere todos os concursos do banco contra o padrão posicional:
    retorna quantas vezes cada dígito acertou em cada coluna por concurso.
    """
    try:
        analise = AnaliseSuperSeteService.analise_por_coluna()
        if not analise:
            return jsonify({"status": "error", "message": "Sem dados no banco."}), 404

        # Top-1 dígito por coluna (mais frequente = "aposta sniper")
        aposta_sniper = [
            analise[col]["rank_freq"][0]
            for col in range(1, 8)
        ]

        sorteios = db.session.query(SorteioSuperSete).order_by(
            desc(SorteioSuperSete.concurso)
        ).all()

        resultados = []
        for s in sorteios:
            digitos = s.digitos()
            acertos = sum(
                1 for col_idx in range(7)
                if aposta_sniper[col_idx] == digitos[col_idx]
            )
            resultados.append({
                "concurso":       s.concurso,
                "data":           s.data,
                "digitos":        digitos,
                "aposta_sniper":  aposta_sniper,
                "acertos":        acertos,
            })

        return jsonify({"status": "success", "resultados": resultados})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
