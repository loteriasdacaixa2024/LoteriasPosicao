from itertools import combinations
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime
from models.shared import db
from models.desdobramento import Desdobramento, GrupoDesdobramento, ApostaDesdobramento
from services.analise_megasena_service import AnaliseMegaSenaService


class DesdobramentoMegaSenaService:
    """
    Serviço central de Desdobramento (Fechamento) da Mega-Sena.
    Implementa as regras de garantia para 16 dezenas divididas em 4 grupos de 4.
    Adiciona a inteligência de sugestão estratégica de colunas a partir do histórico de sorteios.
    """

    @staticmethod
    def organizar_por_coluna(numeros: List[int]) -> List[int]:
        """
        Organiza as 16 dezenas agrupando-as por coluna (1 a 10) em ordem crescente.
        Garante que os 4 grupos de 4 fiquem fiéis às colunas de dezenas selecionadas.
        """
        colunas = {}
        for n in numeros:
            col = 10 if n % 10 == 0 else n % 10
            if col not in colunas:
                colunas[col] = []
            colunas[col].append(n)

        # Ordenar os números dentro de cada coluna
        for col in colunas:
            colunas[col].sort()

        # Concatenar as colunas ordenadas ascendentemente por ID da coluna
        numeros_ordenados = []
        for col in sorted(colunas.keys()):
            numeros_ordenados.extend(colunas[col])

        return numeros_ordenados

    @classmethod
    def gerar_fechamento(cls, numeros: List[int], modo: str = "bronze") -> Dict[str, Any]:
        """
        Gera os grupos, pares e combinações de apostas conforme o nível de garantia.
        """
        if len(numeros) != 16:
            raise ValueError("O desdobramento precisa de exatamente 16 números.")

        # Garantir organização impecável das dezenas
        numeros_organizados = cls.organizar_por_coluna(numeros)

        # Dividir em 4 grupos de 4
        grupos = [
            numeros_organizados[0:4],
            numeros_organizados[4:8],
            numeros_organizados[8:12],
            numeros_organizados[12:16]
        ]

        # Gerar pares possíveis dentro de cada grupo C(4,2) = 6 pares
        pares_por_grupo = []
        for gp in grupos:
            pares = list(combinations(gp, 2))
            pares_por_grupo.append(pares)

        # Funções internas para gerar os trios
        def gerar_apostas_para_parceria(l1: int, l2: int, r1: int, r2: int) -> List[List[int]]:
            apostas = []
            for i in range(6):
                par1 = pares_por_grupo[l1][i]
                par2 = pares_por_grupo[l2][i]
                par3 = pares_por_grupo[r1][i]
                par4 = pares_por_grupo[r2][i]

                combinacoes = [
                    [par1[0], par1[1], par2[0], par3[0], par3[1], par4[0]],
                    [par1[1], par2[0], par2[1], par3[1], par4[0], par4[1]],
                    [par2[0], par2[1], par1[0], par4[0], par4[1], par3[0]],
                    [par2[1], par1[0], par1[1], par4[1], par3[0], par3[1]]
                ]
                for ap in combinacoes:
                    if len(set(ap)) == 6:
                        apostas.append(sorted(ap))
            return apostas

        def gerar_apostas_cartesianas_para_parceria(l1: int, l2: int, r1: int, r2: int) -> List[List[int]]:
            apostas = []
            for i in range(6):
                par1 = pares_por_grupo[l1][i]
                par2 = pares_por_grupo[l2][i]
                par3 = pares_por_grupo[r1][i]
                par4 = pares_por_grupo[r2][i]

                trios_esq = [
                    [par1[0], par1[1], par2[0]],
                    [par1[1], par2[0], par2[1]],
                    [par2[0], par2[1], par1[0]],
                    [par2[1], par1[0], par1[1]]
                ]
                trios_dir = [
                    [par3[0], par3[1], par4[0]],
                    [par3[1], par4[0], par4[1]],
                    [par4[0], par4[1], par3[0]],
                    [par4[1], par3[0], par3[1]]
                ]
                for te in trios_esq:
                    for td in trios_dir:
                        ap = te + td
                        if len(set(ap)) == 6:
                            apostas.append(sorted(ap))
            return apostas

        # Executar geração com base na garantia/modo
        modo = modo.lower()
        if modo == "bronze":
            # Bronze: Parceria Padrão (G1+G2 / G3+G4), trios 1-para-1 = 24 apostas
            apostas = gerar_apostas_para_parceria(0, 1, 2, 3)
        elif modo == "prata":
            # Prata: Rotação das 3 parcerias, trios 1-para-1 = 72 apostas
            p1 = gerar_apostas_para_parceria(0, 1, 2, 3)
            p2 = gerar_apostas_para_parceria(0, 2, 1, 3)
            p3 = gerar_apostas_para_parceria(0, 3, 1, 2)
            apostas = p1 + p2 + p3
        elif modo == "ouro":
            # Ouro: Parceria Padrão, cruzamento cartesiano completo = 96 apostas
            apostas = gerar_apostas_cartesianas_para_parceria(0, 1, 2, 3)
        elif modo == "diamante":
            # Diamante: Rotação de 3 parcerias, cruzamento cartesiano completo = 288 apostas
            p1 = gerar_apostas_cartesianas_para_parceria(0, 1, 2, 3)
            p2 = gerar_apostas_cartesianas_para_parceria(0, 2, 1, 3)
            p3 = gerar_apostas_cartesianas_para_parceria(0, 3, 1, 2)
            apostas = p1 + p2 + p3
        else:
            # Fallback seguro
            modo = "bronze"
            apostas = gerar_apostas_para_parceria(0, 1, 2, 3)

        return {
            "numeros": numeros_organizados,
            "grupos": grupos,
            "pares": [[list(p) for p in gp] for gp in pares_por_grupo],
            "apostas": apostas,
            "total_apostas": len(apostas),
            "modo": modo
        }

    @classmethod
    def salvar_desdobramento(cls, nome: str, numeros: List[int], modo: str = "bronze") -> int:
        """
        Gera e persiste o desdobramento no SQLite usando SQLAlchemy.
        """
        resultado = cls.gerar_fechamento(numeros, modo)

        desd = Desdobramento(
            nome=nome,
            data_criacao=datetime.now().isoformat(),
            numeros=",".join(map(str, resultado["numeros"])),
            total_apostas=resultado["total_apostas"],
            modo=resultado["modo"]
        )
        db.session.add(desd)
        db.session.flush()  # Para preencher desd.id

        # Salvar os 4 grupos
        for idx, gp in enumerate(resultado["grupos"], 1):
            grupo_db = GrupoDesdobramento(
                desdobramento_id=desd.id,
                grupo_numero=idx,
                numeros=",".join(map(str, gp))
            )
            db.session.add(grupo_db)

        # Salvar todas as apostas virtuais
        for idx, ap in enumerate(resultado["apostas"]):
            linha_virtual = (idx // 4) + 1
            aposta_num_virtual = (idx % 4) + 1
            ap_db = ApostaDesdobramento(
                desdobramento_id=desd.id,
                linha=linha_virtual,
                aposta_numero=aposta_num_virtual,
                dezenas=",".join(map(str, ap))
            )
            db.session.add(ap_db)

        db.session.commit()
        return desd.id

    @staticmethod
    def listar_todos() -> List[Dict[str, Any]]:
        """
        Retorna a lista resumida de todos os desdobramentos salvos.
        """
        itens = db.session.query(Desdobramento).order_by(Desdobramento.data_criacao.desc()).all()
        return [{
            "id": d.id,
            "nome": d.nome,
            "data_criacao": d.data_criacao,
            "numeros": d.numeros,
            "total_apostas": d.total_apostas,
            "modo": d.modo
        } for d in itens]

    @staticmethod
    def buscar_por_id(id: int) -> Optional[Dict[str, Any]]:
        """
        Busca um desdobramento completo pelo ID com seus grupos e apostas associados.
        """
        d = db.session.query(Desdobramento).filter(Desdobramento.id == id).first()
        if not d:
            return None

        # Carregar grupos
        grupos_db = db.session.query(GrupoDesdobramento).filter(GrupoDesdobramento.desdobramento_id == id).order_by(GrupoDesdobramento.grupo_numero).all()
        grupos = [[int(x) for x in g.numeros.split(",")] for g in grupos_db]

        # Carregar apostas
        apostas_db = db.session.query(ApostaDesdobramento).filter(ApostaDesdobramento.desdobramento_id == id).order_by(ApostaDesdobramento.id).all()
        apostas = [[int(x) for x in a.dezenas.split(",")] for a in apostas_db]

        # Reconstruir pares
        pares = []
        for gp in grupos:
            pares.append([list(p) for p in combinations(gp, 2)])

        return {
            "id": d.id,
            "nome": d.nome,
            "data_criacao": d.data_criacao,
            "numeros": d.numeros,
            "total_apostas": d.total_apostas,
            "modo": d.modo,
            "grupos": grupos,
            "pares": pares,
            "apostas": apostas
        }

    @staticmethod
    def deletar_por_id(id: int) -> bool:
        """
        Remove um desdobramento (e todos os grupos/apostas devido ao cascade).
        """
        d = db.session.query(Desdobramento).filter(Desdobramento.id == id).first()
        if not d:
            return False
        db.session.delete(d)
        db.session.commit()
        return True

    @staticmethod
    def obter_sugestoes_colunas() -> Dict[str, Any]:
        """
        Analisa as estatísticas históricas de colunas (freq e atraso)
        e sugere as colunas estratégicas ideais de 4 colunas, junto com as
        respectivas 4 melhores dezenas dentro de cada coluna para totalizar 16 números.
        """
        stats_avancada = AnaliseMegaSenaService.analise_avancada()
        dados_geral = AnaliseMegaSenaService.analise_geral()
        
        if not stats_avancada or "colunas" not in stats_avancada or not dados_geral or "dados" not in dados_geral:
            # Fallback seguro caso não tenha dados no banco
            return {
                "quentes": {
                    "colunas": [1, 2, 3, 4],
                    "dezenas": [1, 11, 21, 31, 2, 12, 22, 32, 3, 13, 23, 33, 4, 14, 24, 34]
                },
                "atrasadas": {
                    "colunas": [5, 6, 7, 8],
                    "dezenas": [5, 15, 25, 35, 6, 16, 26, 36, 7, 17, 27, 37, 8, 18, 28, 38]
                },
                "balanceadas": {
                    "colunas": [1, 2, 5, 6],
                    "dezenas": [1, 11, 21, 31, 2, 12, 22, 32, 5, 15, 25, 35, 6, 16, 26, 36]
                }
            }

        colunas_lista = stats_avancada["colunas"]  # Contém {"coluna", "freq", "pct", "atraso"}
        dezenas_stats = {d["dezena"]: d for d in dados_geral["dados"]}

        # 1. Colunas Quentes
        quentes_ordenadas = sorted(colunas_lista, key=lambda x: x["freq"], reverse=True)
        quentes_cols = sorted([c["coluna"] for c in quentes_ordenadas[:4]])

        # 2. Colunas Atrasadas
        atrasadas_ordenadas = sorted(colunas_lista, key=lambda x: x["atraso"], reverse=True)
        atrasadas_cols = sorted([c["coluna"] for c in atrasadas_ordenadas[:4]])

        # 3. Colunas Balanceadas
        balanceadas_cols = []
        balanceadas_cols.append(quentes_cols[0])
        balanceadas_cols.append(quentes_cols[1])
        for c_item in atrasadas_ordenadas:
            c = c_item["coluna"]
            if c not in balanceadas_cols:
                balanceadas_cols.append(c)
            if len(balanceadas_cols) == 4:
                break
        balanceadas_cols = sorted(balanceadas_cols)

        # Helper para escolher 4 dezenas por coluna baseadas em um critério
        def escolher_dezenas(colunas: List[int], criterio: str) -> List[int]:
            selecionadas = []
            for col in colunas:
                # Obter as 6 dezenas da coluna
                dezenas_col = []
                for d in range(1, 61):
                    d_col = 10 if d % 10 == 0 else d % 10
                    if d_col == col:
                        dezenas_col.append(d)
                
                # Sort dezenas inside the column based on criteria
                if criterio == "quentes":
                    # Ordenar por maior frequência
                    dezenas_col_ordenadas = sorted(dezenas_col, key=lambda x: dezenas_stats[x]["freq"], reverse=True)
                elif criterio == "atrasadas":
                    # Ordenar por maior atraso
                    dezenas_col_ordenadas = sorted(dezenas_col, key=lambda x: dezenas_stats[x]["atraso"], reverse=True)
                else:  # balanceadas
                    # 2 mais quentes + 2 mais atrasadas
                    quentes_da_col = sorted(dezenas_col, key=lambda x: dezenas_stats[x]["freq"], reverse=True)[:2]
                    restantes = [x for x in dezenas_col if x not in quentes_da_col]
                    atrasadas_da_col = sorted(restantes, key=lambda x: dezenas_stats[x]["atraso"], reverse=True)[:2]
                    dezenas_col_ordenadas = quentes_da_col + atrasadas_da_col
                
                # Pegar exatamente 4 dezenas
                selecionadas.extend(sorted(dezenas_col_ordenadas[:4]))
            
            return sorted(selecionadas)

        return {
            "quentes": {
                "colunas": quentes_cols,
                "dezenas": escolher_dezenas(quentes_cols, "quentes")
            },
            "atrasadas": {
                "colunas": atrasadas_cols,
                "dezenas": escolher_dezenas(atrasadas_cols, "atrasadas")
            },
            "balanceadas": {
                "colunas": balanceadas_cols,
                "dezenas": escolher_dezenas(balanceadas_cols, "balanceadas")
            }
        }
