"""
Serviço orquestrador do módulo Des2.
Independente do Des1 (desdobramento_service).
"""
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

from models.shared import db
from models.sorteio_megasena import SorteioMegaSena
from models.des2_estrategia import Des2Estrategia
from services.des2_engine import (
    gerar_jogos_estruturais,
    validar_entrada,
    dezenas_da_coluna,
    colunas_necessarias,
    formatar_export_txt,
    desdobramento_colunas_selecionadas,
)
from services.des2_constants import DEZENAS_PERMITIDAS, TABELA_PRECOS, COLUNAS_LABEL
from services.des2_sugestoes_service import Des2SugestoesService


class Des2MegaSenaService:

    @staticmethod
    def obter_config() -> Dict[str, Any]:
        return {
            "dezenas_permitidas": DEZENAS_PERMITIDAS,
            "tabela_precos": TABELA_PRECOS,
            "jogos_por_geracao": 15,
            "colunas_volante": {
                str(c): {
                    "id": c,
                    "label": COLUNAS_LABEL.get(c, f"Coluna {c}"),
                    "dezenas": dezenas_da_coluna(c),
                }
                for c in range(1, 11)
            },
        }

    @classmethod
    def gerar(cls, colunas: List[int], qtd_dezenas: int) -> Dict[str, Any]:
        return gerar_jogos_estruturais(colunas, qtd_dezenas)

    @staticmethod
    def preview_desdobramento_colunas(colunas: List[int]) -> Dict[str, Any]:
        """Mostra os 15 pares (dois em dois) de cada coluna já selecionada."""
        cols = sorted({int(c) for c in colunas if 1 <= int(c) <= 10})
        return {
            "colunas": cols,
            "desdobramento_colunas": desdobramento_colunas_selecionadas(cols),
            "total_pares_por_coluna": 15,
            "dezenas_por_coluna": 2,
        }

    @classmethod
    def obter_sugestoes(cls, qtd_dezenas: int) -> Dict[str, Any]:
        """Sugere colunas distintas (quentes / atrasadas / balanceadas) pelo volante."""
        return Des2SugestoesService.obter_sugestoes(qtd_dezenas)

    @classmethod
    def conferir_historico(cls, jogos: List[List[int]]) -> Dict[str, Any]:
        """Confere jogos em todos os concursos históricos."""
        sorteios = SorteioMegaSena.query.order_by(SorteioMegaSena.concurso.asc()).all()
        if not sorteios:
            return {"erro": "Sem sorteios no banco. Sincronize os dados primeiro."}

        total_quadra = total_quina = total_sena = 0
        melhor_sequencia = 0
        sequencia_atual = 0
        por_jogo = []
        por_concurso_resumo = []
        freq_colunas_premio = {c: 0 for c in range(1, 11)}

        for jogo in jogos:
            jq = {"jogo": jogo, "quadra": 0, "quina": 0, "sena": 0, "melhor_acerto": 0}
            por_jogo.append(jq)

        for s in sorteios:
            sorteadas = set(s.dezenas_lista())
            max_acertos_concurso = 0
            teve_premio = False

            for idx, jogo in enumerate(jogos):
                acertos = len(set(jogo) & sorteadas)
                max_acertos_concurso = max(max_acertos_concurso, acertos)
                por_jogo[idx]["melhor_acerto"] = max(por_jogo[idx]["melhor_acerto"], acertos)

                if acertos >= 4:
                    por_jogo[idx]["quadra"] += 1
                    total_quadra += 1
                    teve_premio = True
                    for d in jogo:
                        if d in sorteadas:
                            freq_colunas_premio[10 if d % 10 == 0 else d % 10] += 1
                if acertos >= 5:
                    por_jogo[idx]["quina"] += 1
                    total_quina += 1
                if acertos == 6:
                    por_jogo[idx]["sena"] += 1
                    total_sena += 1

            if teve_premio:
                sequencia_atual += 1
                melhor_sequencia = max(melhor_sequencia, sequencia_atual)
            else:
                sequencia_atual = 0

            por_concurso_resumo.append({
                "concurso": s.concurso,
                "data": s.data,
                "dezenas": s.dezenas_lista(),
                "max_acertos": max_acertos_concurso,
            })

        total_concursos = len(sorteios)
        taxa_quadra = round(total_quadra / (len(jogos) * total_concursos) * 100, 4) if total_concursos else 0

        ranking_colunas = sorted(
            [{"coluna": c, "premios": freq_colunas_premio[c]} for c in range(1, 11)],
            key=lambda x: -x["premios"],
        )

        return {
            "total_concursos": total_concursos,
            "total_jogos": len(jogos),
            "quadra": total_quadra,
            "quina": total_quina,
            "sena": total_sena,
            "taxa_quadra_pct": taxa_quadra,
            "melhor_sequencia_premiada": melhor_sequencia,
            "por_jogo": por_jogo,
            "ranking_colunas": ranking_colunas,
            "ultimos_50": por_concurso_resumo[-50:],
        }

    @classmethod
    def salvar_estrategia(
        cls,
        nome: str,
        colunas: List[int],
        qtd_dezenas: int,
        resultado: Dict[str, Any],
    ) -> int:
        reg = Des2Estrategia(
            nome=nome,
            data_criacao=datetime.now().isoformat(),
            colunas=",".join(map(str, sorted(colunas))),
            qtd_dezenas=qtd_dezenas,
            total_jogos=resultado["total_jogos"],
            valor_total=resultado["valor_total"],
            jogos_json=json.dumps(resultado["jogos"]),
        )
        db.session.add(reg)
        db.session.commit()
        return reg.id

    @staticmethod
    def listar_estrategias() -> List[Dict[str, Any]]:
        itens = Des2Estrategia.query.order_by(Des2Estrategia.data_criacao.desc()).all()
        return [
            {
                "id": e.id,
                "nome": e.nome,
                "data_criacao": e.data_criacao,
                "colunas": e.colunas,
                "qtd_dezenas": e.qtd_dezenas,
                "total_jogos": e.total_jogos,
                "valor_total": e.valor_total,
            }
            for e in itens
        ]

    @classmethod
    def buscar_estrategia(cls, id_: int) -> Optional[Dict[str, Any]]:
        e = Des2Estrategia.query.get(id_)
        if not e:
            return None
        return {
            "id": e.id,
            "nome": e.nome,
            "data_criacao": e.data_criacao,
            "colunas": [int(x) for x in e.colunas.split(",")],
            "qtd_dezenas": e.qtd_dezenas,
            "total_jogos": e.total_jogos,
            "valor_total": e.valor_total,
            "jogos": json.loads(e.jogos_json),
        }

    @staticmethod
    def deletar_estrategia(id_: int) -> bool:
        e = Des2Estrategia.query.get(id_)
        if not e:
            return False
        db.session.delete(e)
        db.session.commit()
        return True

    @staticmethod
    def exportar_txt(resultado: Dict[str, Any], nome: str = "Des2") -> str:
        return formatar_export_txt(resultado, nome)

    @staticmethod
    def exportar_csv(resultado: Dict[str, Any]) -> str:
        linhas = ["Jogo;" + ";".join(f"D{i}" for i in range(1, resultado["qtd_dezenas"] + 1))]
        for j in resultado["jogos_detalhe"]:
            linhas.append(f"{j['numero']};" + ";".join(j["dezenas_fmt"]))
        return "\n".join(linhas)
