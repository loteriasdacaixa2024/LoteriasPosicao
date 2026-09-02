# -*- coding: utf-8 -*-
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

_LOTERIAS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _LOTERIAS not in sys.path:
    sys.path.insert(0, _LOTERIAS)

from _shared.desdobramento_especial_quina.constants import (
    COLUNAS_LABEL,
    COLUNAS_VALIDAS_IMPAR,
    COLUNAS_VALIDAS_PAR,
    GARANTIAS_ESPECIAL,
    JOGOS_POR_COLUNA,
    TABELA_PRECOS,
)
from _shared.desdobramento_especial_quina.engine import (
    dezenas_coluna,
    desdobramento_coluna,
    formatar_export_txt,
    gerar_jogos_estruturais,
    orientacao_selecao,
    preview_montagem,
    tabela_colunas_dezenas,
)
from models.desdobramento import ApostaDesdobramento, Desdobramento
from models.shared import db
from services.ciclo_service import CicloQuinaService
from services.desdobramento_service import DesdobramentoQuinaService


class DesdobramentoEspecialQuinaService:
    TIPO_DB = "especial_sao_joao"

    @staticmethod
    def obter_config() -> Dict[str, Any]:
        return {
            "min_colunas": 3,
            "min_dezenas_aposta": 5,
            "max_dezenas_aposta": 15,
            "jogos_por_geracao": JOGOS_POR_COLUNA,
            "pares_por_coluna": JOGOS_POR_COLUNA,
            "tabela_precos": TABELA_PRECOS,
            "colunas_validas_par": sorted(COLUNAS_VALIDAS_PAR),
            "colunas_validas_impar": sorted(COLUNAS_VALIDAS_IMPAR),
            "colunas_volante": {
                str(c): {
                    "id": c,
                    "label": COLUNAS_LABEL.get(c, f"Coluna {c}"),
                    "dezenas": dezenas_coluna(c),
                }
                for c in range(1, 11)
            },
            "garantias": GARANTIAS_ESPECIAL,
            "tabela_par": tabela_colunas_dezenas("par"),
            "tabela_impar": tabela_colunas_dezenas("impar"),
        }

    @classmethod
    def obter_ciclo(cls) -> Dict[str, Any]:
        return CicloQuinaService.obter_ciclo_atual()

    @classmethod
    def obter_sugestoes_colunas(cls) -> Dict[str, Any]:
        return DesdobramentoQuinaService.obter_sugestoes_colunas()

    @classmethod
    def preview_colunas(cls, colunas: List[int]) -> Dict[str, Any]:
        cols = sorted({int(c) for c in colunas if 1 <= int(c) <= 10})
        return {
            "colunas": cols,
            "desdobramento_colunas": [desdobramento_coluna(c) for c in cols],
            "total_pares_por_coluna": JOGOS_POR_COLUNA,
        }

    @classmethod
    def preview_montagem(
        cls,
        colunas: List[int],
        modo: str,
        coluna_simples: Optional[int] = None,
    ) -> Dict[str, Any]:
        return preview_montagem(colunas, modo, coluna_simples)

    @classmethod
    def orientacao(
        cls,
        modo: str,
        meta_dezenas: Optional[int] = None,
        colunas: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        return orientacao_selecao(modo, meta_dezenas, colunas)

    @classmethod
    def gerar(
        cls,
        colunas: List[int],
        modo: str,
        coluna_simples: Optional[int] = None,
        dezena_simples: Optional[int] = None,
        garantia: str = "diamante",
    ) -> Dict[str, Any]:
        ciclo = cls.obter_ciclo()
        faltantes: Set[int] = set(ciclo.get("dezenas_faltantes") or [])
        return gerar_jogos_estruturais(
            colunas,
            modo,
            coluna_simples=coluna_simples,
            dezena_simples=dezena_simples,
            faltantes_ciclo=faltantes,
            garantia=garantia,
        )

    @classmethod
    def salvar(cls, nome: str, resultado: Dict[str, Any]) -> int:
        modo_db = f"{resultado.get('modo', 'par')}"
        if resultado.get("coluna_simples"):
            modo_db = f"{modo_db}:c{resultado['coluna_simples']}"
        desd = Desdobramento(
            nome=nome,
            data_criacao=datetime.now().isoformat(),
            numeros=",".join(str(c) for c in resultado["colunas"]),
            total_apostas=resultado["total_jogos"],
            modo=modo_db,
            tipo=cls.TIPO_DB,
        )
        db.session.add(desd)
        db.session.flush()
        for idx, ap in enumerate(resultado["jogos"]):
            db.session.add(
                ApostaDesdobramento(
                    desdobramento_id=desd.id,
                    linha=(idx // 4) + 1,
                    aposta_numero=(idx % 4) + 1,
                    dezenas=",".join(map(str, ap)),
                )
            )
        db.session.commit()
        return desd.id

    @staticmethod
    def exportar_txt(resultado: Dict[str, Any], nome: str) -> str:
        return formatar_export_txt(resultado, nome)
