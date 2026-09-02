# -*- coding: utf-8 -*-
"""Aba 3 — Classificação dos Números."""
from __future__ import annotations

from typing import Any, Dict, List, Type

from geradores_elite.comportamento.panorama_indicadores import calcular_panorama_indicadores

from analise_estudos.base_service import AnaliseEstudosBase
from analise_estudos.core.classificacoes import (
    calcular_classificacoes_concurso,
    indicador_labels,
    indicadores_aba3,
    intersecoes_destaque,
    listar_classificacoes_ui,
)
from analise_estudos.service_factory import make_estudos_base
from analise_estudos.specs import BASES_LABEL, links_modalidade


class ClassificacaoNumerosAba:
    @classmethod
    def _base_cls(cls, modality_key: str) -> Type[AnaliseEstudosBase]:
        return make_estudos_base(modality_key)

    @classmethod
    def analisar(
        cls,
        modality_key: str,
        janela: int = 10,
        base_estatistica: str = "geral",
    ) -> Dict[str, Any]:
        Base = cls._base_cls(modality_key)
        janela = Base._normalizar_janela(janela)
        base = Base._normalizar_base(base_estatistica)
        sorteios = Base.carregar_sorteios_asc(base, janela if janela > 0 else 0)

        if not sorteios:
            return {
                "sucesso": False,
                "erro": f"Nenhum sorteio na base «{base}».",
            }

        linhas_chrono: List[Dict[str, Any]] = []
        for i, s in enumerate(sorteios):
            dz = Base.dezenas_ordem(s)
            prev = Base.dezenas_ordem(sorteios[i - 1]) if i > 0 else None
            mes = int(getattr(s, "mes_num", 0) or 0)
            ind = calcular_classificacoes_concurso(
                dz, prev, mes, modality_key=modality_key,
            )
            row: Dict[str, Any] = {
                "concurso": s.concurso,
                "data": getattr(s, "data", "") or "",
                "dezenas": dz,
                **ind,
            }
            if Base._cfg().get("extra_mes") and mes:
                row["mes_num"] = mes
                row["mes_nome"] = getattr(s, "mes_nome", "") or ""
            linhas_chrono.append(row)

        linhas = list(reversed(linhas_chrono))
        labels = indicador_labels(modality_key)
        indicadores = list(indicadores_aba3(modality_key))
        resumo = Base.resumo_indicadores(linhas_chrono, indicadores)
        panorama = calcular_panorama_indicadores(
            linhas_chrono, indicadores, labels,
        )

        ultimo = sorteios[-1]
        ultimo_dz = Base.dezenas_ordem(ultimo)
        ultimo_prev = Base.dezenas_ordem(sorteios[-2]) if len(sorteios) > 1 else None
        ultimo_ind = calcular_classificacoes_concurso(
            ultimo_dz,
            ultimo_prev,
            int(getattr(ultimo, "mes_num", 0) or 0),
            modality_key=modality_key,
        )

        kpis = [
            {
                "codigo": "total",
                "label": "Concursos na janela",
                "valor": len(linhas_chrono),
            },
            {
                "codigo": "ultimo",
                "label": f"Último #{ultimo.concurso}",
                "valor": f"PA {ultimo_ind.get('PA', 0)} · PR {ultimo_ind.get('PR', 0)}",
            },
            {
                "codigo": "moda_pa",
                "label": "Moda PA",
                "valor": f"{resumo.get('PA', {}).get('moda', '—')} ({resumo.get('PA', {}).get('moda_pct', 0)}%)",
            },
            {
                "codigo": "moda_pr",
                "label": "Moda PR",
                "valor": f"{resumo.get('PR', {}).get('moda', '—')} ({resumo.get('PR', {}).get('moda_pct', 0)}%)",
            },
        ]

        lk = links_modalidade(modality_key)
        return {
            "sucesso": True,
            "aba_id": "classificacao-numeros",
            "base_estatistica": base,
            "base_label": BASES_LABEL.get(base, base),
            "janela": janela,
            "janela_label": "Todos" if janela == 0 else f"Últimos {janela}",
            "total_concursos": len(linhas_chrono),
            "ultimo_concurso": ultimo.concurso,
            "ultimo_indicadores": ultimo_ind,
            "linhas": linhas,
            "resumo": resumo,
            "panorama": panorama,
            "kpis": kpis,
            "classificacoes": listar_classificacoes_ui(modality_key),
            "intersecoes": intersecoes_destaque(modality_key),
            "indicadores": [
                {"codigo": c, "label": labels.get(c, c)} for c in indicadores
            ],
            "meta_bases": Base.meta_bases(),
            "links": {
                **lk,
                "soma_digitos": f"{lk.get('analises_gerais', '')}?aba=soma-digitos",
                "digitos_utilizados": f"{lk.get('analises_gerais', '')}?aba=digitos-utilizados",
                "comportamento": lk.get("comportamento", "/analise/comportamento/"),
                "comportamento_apostas": lk.get(
                    "comportamento_apostas", "/geradores-elite/comportamento-apostas/",
                ),
            },
        }
