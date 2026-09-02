from flask import Blueprint, render_template, jsonify, request
from models import db

conferencia_bp = Blueprint('conferencia', __name__)

@conferencia_bp.route('/')
def conferencia_index():
    return render_template('conferencia.html')

@conferencia_bp.route('/listar-sessoes', methods=['GET'])
def listar_sessoes():
    return jsonify({"sessoes": []})

@conferencia_bp.route('/api/conferir', methods=['POST', 'GET'])
def conferir_sniper():
    try:
        from services.analise_lotofacil_service import AnaliseLotofacilService
        from models.sorteio_lotofacil import SorteioLotofacil
        
        # Gera o sniper na mosca
        sniper_data = AnaliseLotofacilService.gerar_matriz_sniper_vertical()
        if "error" in sniper_data:
            return jsonify(sniper_data)
            
        matrizes = sniper_data["matrizes"]
        sorteios = db.session.query(SorteioLotofacil).all()
        
        # Prepara a estrutura de resultados
        resultados = []
        
        for matriz in matrizes:
            # Pegamos os números únicos da matriz para a conferência
            # A matriz crua pode ter repetidos, então transformamos em set
            dezenas_set = set([int(x) for x in matriz["dezenas_formatadas"]])
            
            hits_15 = 0
            hits_14 = 0
            hits_13 = 0
            hits_12 = 0
            hits_11 = 0
            detalhes = []
            
            for sorteio in sorteios:
                sorteio_dezenas = set(sorteio.dezenas())
                acertos = len(dezenas_set.intersection(sorteio_dezenas))
                
                if acertos >= 11:
                    if acertos == 15: hits_15 += 1
                    elif acertos == 14: hits_14 += 1
                    elif acertos == 13: hits_13 += 1
                    elif acertos == 12: hits_12 += 1
                    elif acertos == 11: hits_11 += 1
                    
                    detalhes.append({
                        "concurso": sorteio.concurso,
                        "data": sorteio.data,
                        "acertos": acertos
                    })
                
            total_premios = hits_15 + hits_14 + hits_13 + hits_12 + hits_11
            
            # Ordena os detalhes para mostrar os maiores prêmios primeiro
            detalhes.sort(key=lambda x: (x["acertos"], x["concurso"]), reverse=True)
            
            resultados.append({
                "rank": matriz["aposta_num"],
                "dezenas": matriz["dezenas_formatadas"],
                "total_premios": total_premios,
                "hits_15": hits_15,
                "hits_14": hits_14,
                "hits_13": hits_13,
                "hits_12": hits_12,
                "hits_11": hits_11,
                "detalhes": detalhes
            })
            
        return jsonify({"status": "success", "resultados": resultados})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
