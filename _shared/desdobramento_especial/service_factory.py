# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Type

from _shared.desdobramento_especial.configs import get_config
from _shared.desdobramento_especial.engine import (
    desdobramento_coluna,
    formatar_export_txt,
    gerar_jogos_estruturais,
    orientacao_selecao,
    preview_montagem,
    tabela_colunas_dezenas,
)
from models.desdobramento import ApostaDesdobramento, Desdobramento
from models.shared import db


def _dezenas_ultimo_sorteio(item: Dict[str, Any]) -> List[int]:
    if item.get("dezenas"):
        return [int(x) for x in item["dezenas"]]
    if item.get("sorteio1"):
        return [int(x) for x in item["sorteio1"]]
    if item.get("sorteio_1"):
        return [int(x) for x in item["sorteio_1"]]
    return []


def build_desdobramento_especial_service(
    slug: str,
    ciclo_service_class: Type,
    desdobramento_service_class: Type,
    analise_service_class: Optional[Type] = None,
):
    cfg = get_config(slug)

    class DesdobramentoEspecialService:
        SLUG = slug
        TIPO_DB = f"especial_{slug}"

        @classmethod
        def obter_config(cls) -> Dict[str, Any]:
            return {
                "slug": slug,
                "titulo": cfg.titulo_especial,
                "min_colunas": cfg.min_colunas,
                "min_dezenas_aposta": cfg.min_dezenas,
                "max_dezenas_aposta": cfg.max_dezenas,
                "volante_linhas": cfg.volante_linhas,
                "colunas_header": cfg.colunas_header,
                "layout": cfg.layout,
                "max_dezena": cfg.max_dezena,
                "ciclo_total": cfg.ciclo_total,
                "sorteio_bolas": cfg.sorteio_bolas,
                "nota_aposta": cfg.nota_aposta,
                "tabela_precos": cfg.tabela_precos,
                "garantias": cfg.garantias,
                "tabela_par": tabela_colunas_dezenas(cfg, "par"),
                "tabela_impar": tabela_colunas_dezenas(cfg, "impar"),
                "colunas_volante": {
                    str(c): {
                        "id": c,
                        "label": cfg.label_coluna(c),
                        "dezenas": __import__(
                            "_shared.desdobramento_especial.engine",
                            fromlist=["dezenas_coluna"],
                        ).dezenas_coluna(cfg, c),
                    }
                    for c in range(1, cfg.colunas_header + 1)
                },
            }

        @classmethod
        def obter_ciclo(cls) -> Dict[str, Any]:
            return ciclo_service_class.obter_ciclo_atual()

        @classmethod
        def obter_sugestoes_colunas(cls) -> Dict[str, Any]:
            return desdobramento_service_class.obter_sugestoes_colunas()

        @classmethod
        def obter_ultimos_sorteios(cls) -> List[Dict[str, Any]]:
            if analise_service_class is None or not hasattr(
                analise_service_class, "ultimos_sorteios"
            ):
                return []
            raw = analise_service_class.ultimos_sorteios() or []
            out: List[Dict[str, Any]] = []
            for item in raw[:30]:
                if not isinstance(item, dict):
                    continue
                dezenas = _dezenas_ultimo_sorteio(item)
                out.append({
                    "concurso": item.get("concurso"),
                    "data": item.get("data"),
                    "dezenas": dezenas,
                    "sorteio2": item.get("sorteio2") or item.get("sorteio_2"),
                })
            return out

        @classmethod
        def preview_colunas(cls, colunas: List[int]) -> Dict[str, Any]:
            cols = sorted({int(c) for c in colunas if 1 <= int(c) <= cfg.colunas_header})
            return {
                "colunas": cols,
                "desdobramento_colunas": [desdobramento_coluna(cfg, c) for c in cols],
            }

        @classmethod
        def preview_montagem(
            cls,
            colunas: List[int],
            modo: str,
            coluna_simples: Optional[int] = None,
        ) -> Dict[str, Any]:
            return preview_montagem(slug, colunas, modo, coluna_simples)

        @classmethod
        def orientacao(
            cls,
            modo: str,
            meta_dezenas: Optional[int] = None,
            colunas: Optional[List[int]] = None,
        ) -> Dict[str, Any]:
            return orientacao_selecao(slug, modo, meta_dezenas, colunas)

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
                slug,
                colunas,
                modo,
                coluna_simples=coluna_simples,
                dezena_simples=dezena_simples,
                faltantes_ciclo=faltantes,
                garantia=garantia,
            )

        @classmethod
        def salvar(cls, nome: str, resultado: Dict[str, Any]) -> int:
            modo_db = resultado.get("modo", "par")
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
            return formatar_export_txt(resultado, nome, cfg.titulo_especial)

    return DesdobramentoEspecialService
