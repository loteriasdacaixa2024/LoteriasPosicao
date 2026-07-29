from models.shared import db
from models.sorteio_lotofacil import SorteioLotofacil
from sqlalchemy import desc
import os
import time

TOTAL_DEZENAS = 25   # 01 a 25
NUM_SORTEADAS = 15


class AnaliseLotofacilService:
    @staticmethod
    def analise_geral():
        """Freq/atraso por dezena (01–25) — formato compatível com concentração / geradores."""
        sorteios = db.session.query(SorteioLotofacil).order_by(
            desc(SorteioLotofacil.concurso)
        ).all()
        if not sorteios:
            return None

        total = len(sorteios)
        ultimo = sorteios[0].concurso
        freq = {d: 0 for d in range(1, TOTAL_DEZENAS + 1)}
        visto = {d: 0 for d in range(1, TOTAL_DEZENAS + 1)}

        for s in sorteios:
            for d in s.dezenas():
                d = int(d)
                if 1 <= d <= TOTAL_DEZENAS:
                    freq[d] += 1
                    if visto[d] == 0:
                        visto[d] = s.concurso

        dados = []
        for d in range(1, TOTAL_DEZENAS + 1):
            atraso = (ultimo - visto[d]) if visto[d] > 0 else total
            pct = round(freq[d] / total * 100, 1) if total > 0 else 0
            dados.append({
                "dezena": d,
                "dezena_fmt": f"{d:02d}",
                "freq": freq[d],
                "atraso": atraso,
                "pct": pct,
            })

        return {
            "dados": dados,
            "total_sorteios": total,
            "ultimo_concurso": ultimo,
            "esperado_pct_dez": round(NUM_SORTEADAS / TOTAL_DEZENAS * 100, 1),
        }

    @staticmethod
    def ultimos_sorteios():
        sorteios = (
            db.session.query(SorteioLotofacil)
            .order_by(desc(SorteioLotofacil.concurso))
            .limit(50)
            .all()
        )
        return [
            {
                "concurso": s.concurso,
                "data": s.data,
                "dezenas": s.dezenas_lista(),
                "dezenas_ordem": s.dezenas_ordem_lista(),
            }
            for s in sorteios
        ]

    @staticmethod
    def calcular_atrasos_absolutos():
        """
        Gera uma lista com as dezenas ranqueadas pelo atraso absoluto em cada uma das 15 posições.
        Itera do concurso mais recente para trás para contar quantos concursos se passaram 
        sem que determinada dezena saísse naquela posição.
        Retorna as 15 posições, cada qual com uma lista de 25 números ordenados pelo maior atraso.
        """
        ultimo_sorteio = db.session.query(SorteioLotofacil).order_by(desc(SorteioLotofacil.concurso)).first()
        if not ultimo_sorteio:
            return {"error": "Não há sorteios no banco de dados."}
        
        teto = ultimo_sorteio.concurso
        vistos = {f'posicao_{i}': {d: 0 for d in range(1, 26)} for i in range(1, 16)}

        sorteios = db.session.query(SorteioLotofacil).order_by(desc(SorteioLotofacil.concurso)).all()
        
        for sorteio in sorteios:
            for i in range(1, 16):
                pos_key = f'posicao_{i}'
                val = getattr(sorteio, pos_key)
                if vistos[pos_key][val] == 0:
                    vistos[pos_key][val] = sorteio.concurso

        rank_matriz = {}
        for i in range(1, 16):
            pos_key = f'posicao_{i}'
            atrasos = []
            for d in range(1, 26):
                concurso_visto = vistos[pos_key][d]
                atraso = teto if concurso_visto == 0 else teto - concurso_visto
                atrasos.append({"numero": f"{d:02d}", "atraso": atraso})
            
            atrasos.sort(key=lambda x: x['atraso'], reverse=True)
            rank_matriz[pos_key] = atrasos
        
        return {
            "ultimo_concurso": teto,
            "matriz_atrasos": rank_matriz
        }

    @staticmethod
    def gerar_matriz_sniper_vertical():
        """
        Gera 24 apostas Sniper Verticais, EXCLUINDO candidatos com atraso=0.
        Lotofácil tem 25 dezenas -> 1 com atraso=0 é descartada -> 24 apostas.
        """
        dados = AnaliseLotofacilService.calcular_atrasos_absolutos()
        if "error" in dados:
            return dados
        
        matriz = dados['matriz_atrasos']
        
        # Pré-filtra: remove candidatos com atraso=0 (cinza = recém saídos)
        matriz_filtrada = {}
        total_descartados = 0
        for pos_key, candidatos in matriz.items():
            filtrados = [c for c in candidatos if c['atraso'] > 0]
            descartados = len(candidatos) - len(filtrados)
            total_descartados = max(total_descartados, descartados)
            matriz_filtrada[pos_key] = filtrados

        min_candidatos = min(len(v) for v in matriz_filtrada.values())
        num_apostas = min(24, min_candidatos)

        linhas_sniper = []
        for rank_idx in range(num_apostas):
            linha = []
            for pos in range(1, 16):
                pos_key = f'posicao_{pos}'
                candidatos = matriz_filtrada[pos_key]
                n = len(candidatos)

                offset = 0
                while offset < n:
                    idx_candidato = (rank_idx + offset) % n
                    dezena_candidata = candidatos[idx_candidato]["numero"]
                    if dezena_candidata not in linha:
                        linha.append(dezena_candidata)
                        break
                    offset += 1
            
            linha_int = sorted([int(x) for x in linha])
            linha_str = [f"{x:02d}" for x in linha_int]
            
            linhas_sniper.append({
                "aposta_num": rank_idx + 1,
                "dezenas_originais_ordem": linha,
                "dezenas_formatadas": linha_str,
                "tamanho": len(set(linha_str))
            })
            
        return {
            "ultimo_concurso": dados["ultimo_concurso"],
            "matrizes": linhas_sniper,
            "total_geradas": len(linhas_sniper),
            "descartadas": total_descartados
        }

    @staticmethod
    def gerar_aposta_por_maior_atraso():
        """
        Para cada uma das 15 posições, seleciona a dezena com MAIOR atraso
        EXCLUINDO dezenas com atraso=0 (recém saídas, mostradas em cinza).
        Retorna uma única aposta de 15 dezenas únicas.
        """
        dados = AnaliseLotofacilService.calcular_atrasos_absolutos()
        if "error" in dados:
            return dados

        matriz = dados['matriz_atrasos']
        ultimo_concurso = dados['ultimo_concurso']

        dezenas_escolhidas = []
        dezenas_set = set()

        for pos in range(1, 16):
            pos_key = f'posicao_{pos}'
            ranking = matriz[pos_key]

            dezena_escolhida = None
            for candidato in ranking:
                # Exclui atraso=0 (saiu no último concurso)
                if candidato['numero'] not in dezenas_set and candidato['atraso'] > 0:
                    dezena_escolhida = candidato
                    break

            if dezena_escolhida:
                dezenas_set.add(dezena_escolhida['numero'])
                dezenas_escolhidas.append({
                    "posicao": pos,
                    "dezena": dezena_escolhida['numero'],
                    "atraso": dezena_escolhida['atraso']
                })

        dezenas_ordenadas = sorted(dezenas_escolhidas, key=lambda x: int(x['dezena']))

        return {
            "ultimo_concurso": ultimo_concurso,
            "aposta": dezenas_escolhidas,
            "aposta_ordenada": dezenas_ordenadas,
            "dezenas": [d['dezena'] for d in dezenas_ordenadas]
        }

    @staticmethod
    def gerar_e_salvar_24_apostas():
        """
        Gera 24 apostas Sniper Vertical, salva em arquivo TXT no diretório docs/
        e retorna o caminho do arquivo e os dados gerados.
        """
        resultado = AnaliseLotofacilService.gerar_matriz_sniper_vertical()
        if "error" in resultado:
            return resultado

        apostas = resultado['matrizes']
        total = resultado['total_geradas']
        descartadas = resultado['descartadas']

        ultimo_concurso = resultado.get('ultimo_concurso', 0)

        # Conteúdo TXT (mesmo formato do Dia de Sorte)
        linhas_txt = [" ".join(a['dezenas_formatadas']) for a in apostas]
        conteudo = "\n".join(linhas_txt)

        # Garantir que docs/ existe
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        docs_dir = os.path.join(base_dir, 'docs')
        os.makedirs(docs_dir, exist_ok=True)

        # Nome padrão com LOTOFACIL + número do concurso
        nome_arquivo = f"[Rank_Vertical_Absoluto_Sniper_LOTOFACIL_SORTEIO]_{ultimo_concurso}.txt"
        caminho_completo = os.path.join(docs_dir, nome_arquivo)

        with open(caminho_completo, 'w', encoding='utf-8') as f:
            f.write(conteudo)

        return {
            "sucesso": True,
            "total_geradas": total,
            "descartadas": descartadas,
            "arquivo": nome_arquivo,
            "caminho": caminho_completo,
            "apostas": apostas,
            "conteudo_txt": conteudo
        }
