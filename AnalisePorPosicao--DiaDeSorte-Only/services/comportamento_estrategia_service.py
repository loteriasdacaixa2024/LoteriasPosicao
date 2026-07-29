# -*- coding: utf-8 -*-
"""Service — conferência e panorama das 3 estratégias comportamentais (Dia de Sorte)."""
from __future__ import annotations

from typing import Any, Dict, List

from models.comportamento_estrategia import (
    ComportamentoEstrategiaRegistro,
    ComportamentoEstrategiaRegistroItem,
)
from models.shared import db
from models.sorteio_diadesorte import SorteioDiaDeSorte

from geradores_elite.comportamento.conferencia_estrategias import (
    BASES,
    BASES_LABEL,
    conferir_estrategias_pontual,
    gerar_insights_panorama,
)


class ComportamentoEstrategiaDiaDeSorteService:
    ACERTOS_MAX_POSSIVEL = 7

    @classmethod
    def _sorteio(cls, concurso: int):
        return db.session.get(SorteioDiaDeSorte, concurso)

    @classmethod
    def conferir_estrategias(
        cls,
        concurso: int,
        apostas_por_base: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        sorteio = cls._sorteio(concurso)
        if not sorteio:
            return {"sucesso": False, "erro": f"Concurso {concurso} não encontrado."}
        sorteadas = sorteio.dezenas_lista()
        conf = conferir_estrategias_pontual(
            apostas_por_base, sorteadas, cls.ACERTOS_MAX_POSSIVEL,
        )
        return {
            "sucesso": True,
            "concurso": concurso,
            "data": sorteio.data,
            "sorteadas": sorteadas,
            "sorteadas_ordem": sorteio.dezenas_ordem_lista(),
            "mes_num": sorteio.mes_num,
            "mes_nome": sorteio.mes_nome,
            "mes_abrev": sorteio.mes_abrev(),
            "bases_label": BASES_LABEL,
            **conf,
        }

    @classmethod
    def registrar_conferencia(
        cls,
        concurso: int,
        apostas_por_base: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        pontual = cls.conferir_estrategias(concurso, apostas_por_base)
        if not pontual.get("sucesso"):
            return pontual

        reg = ComportamentoEstrategiaRegistro(
            concurso=concurso,
            resumo_json="{}",
        )
        db.session.add(reg)
        db.session.flush()

        itens_out = {}
        for base in BASES:
            dados = pontual["por_base"][base]
            item = ComportamentoEstrategiaRegistroItem(
                registro_id=reg.id,
                base_estrategia=base,
                qtd_apostas=dados["qtd_apostas"],
                max_acertos=dados["max_acertos"],
                media_acertos=dados["media_acertos"],
                total_acertos=dados["total_acertos"],
                dist_4=dados["dist_4"],
                dist_5=dados["dist_5"],
                dist_6=dados["dist_6"],
                dist_7=dados["dist_7"],
            )
            db.session.add(item)
            itens_out[base] = {
                "base_label": BASES_LABEL[base],
                "qtd_apostas": dados["qtd_apostas"],
                "max_acertos": dados["max_acertos"],
                "media_acertos": dados["media_acertos"],
                "total_acertos": dados["total_acertos"],
                "dist_4": dados["dist_4"],
                "dist_5": dados["dist_5"],
                "dist_6": dados["dist_6"],
                "dist_7": dados["dist_7"],
            }

        reg.resumo_json = __import__("json").dumps({
            "lider": pontual.get("lider"),
            "ranking": pontual.get("ranking"),
        })
        db.session.commit()

        return {
            "sucesso": True,
            "registro_id": reg.id,
            "concurso": concurso,
            "itens": itens_out,
            "lider": pontual.get("lider"),
            "lider_label": BASES_LABEL.get(pontual.get("lider") or "", ""),
            "ranking": pontual.get("ranking"),
            "pontual": pontual,
        }

    @classmethod
    def panorama(cls, limit: int = 50) -> Dict[str, Any]:
        lim = max(1, min(int(limit), 200))
        rows = (
            db.session.query(ComportamentoEstrategiaRegistro)
            .order_by(ComportamentoEstrategiaRegistro.id.desc())
            .limit(lim)
            .all()
        )
        registros: List[Dict[str, Any]] = []
        soma: Dict[str, Dict[str, float]] = {
            b: {"media": 0.0, "max": 0, "total": 0, "n": 0, "d4": 0, "d5": 0, "d6": 0, "d7": 0}
            for b in BASES
        }
        for reg in rows:
            itens = {it.base_estrategia: it for it in reg.itens}
            item_dict = {}
            for base in BASES:
                it = itens.get(base)
                if not it:
                    continue
                item_dict[base] = {
                    "max_acertos": it.max_acertos,
                    "media_acertos": it.media_acertos,
                    "total_acertos": it.total_acertos,
                    "dist_4": it.dist_4,
                    "dist_5": it.dist_5,
                    "dist_6": it.dist_6,
                    "dist_7": it.dist_7,
                    "qtd_apostas": it.qtd_apostas,
                }
                soma[base]["media"] += it.media_acertos
                soma[base]["max"] += it.max_acertos
                soma[base]["total"] += it.total_acertos
                soma[base]["n"] += 1
                soma[base]["d4"] += it.dist_4
                soma[base]["d5"] += it.dist_5
                soma[base]["d6"] += it.dist_6
                soma[base]["d7"] += it.dist_7
            registros.append({
                "id": reg.id,
                "concurso": reg.concurso,
                "data_execucao": reg.data_execucao,
                "itens": item_dict,
            })

        linhas = []
        for base in BASES:
            n = soma[base]["n"]
            if not n:
                continue
            linhas.append({
                "base": base,
                "base_label": BASES_LABEL[base],
                "conferencias": int(n),
                "media_acertos": round(soma[base]["media"] / n, 2),
                "media_max_acertos": round(soma[base]["max"] / n, 2),
                "total_acertos": int(soma[base]["total"]),
                "dist_4": int(soma[base]["d4"]),
                "dist_5": int(soma[base]["d5"]),
                "dist_6": int(soma[base]["d6"]),
                "dist_7": int(soma[base]["d7"]),
            })
        linhas.sort(key=lambda x: (-x["media_acertos"], -x["media_max_acertos"]))

        insights = gerar_insights_panorama(registros)
        return {
            "sucesso": True,
            "total_registros": len(registros),
            "soma_por_estrategia": linhas,
            "registros": registros,
            "insights": insights,
            "lider_geral": linhas[0]["base"] if linhas else None,
            "lider_label": linhas[0]["base_label"] if linhas else None,
        }
