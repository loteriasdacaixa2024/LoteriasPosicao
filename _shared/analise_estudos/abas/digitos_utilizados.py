# -*- coding: utf-8 -*-
"""Aba 2 — Dígitos Utilizados."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Set, Type

from analise_estudos.base_service import AnaliseEstudosBase
from analise_estudos.core.digitos import (
    analisar_digitos_concurso,
    calcular_atraso_digitos,
    calcular_coocorrencia_digitos,
    sobreposicao_digitos_consecutivos,
)
from analise_estudos.service_factory import make_estudos_base
from analise_estudos.specs import BASES_LABEL, links_modalidade


class DigitosUtilizadosAba:
    @classmethod
    def _base_cls(cls, modality_key: str) -> Type[AnaliseEstudosBase]:
        return make_estudos_base(modality_key)

    @classmethod
    def _insights(
        cls,
        painel: List[Dict[str, Any]],
        top_pares: List[Dict[str, Any]],
        sobreposicao: Dict[str, Any],
        atrasos: List[Dict[str, Any]],
    ) -> List[str]:
        insights: List[str] = []
        if painel:
            top = painel[0]
            low = min(painel, key=lambda x: x["concursos_com_digito"])
            insights.append(
                f"Dígito **{top['digito']}** aparece em mais concursos ({top['pct_concursos']}%); "
                f"**{low['digito']}** aparece menos ({low['pct_concursos']}%)."
            )
        if top_pares:
            p = top_pares[0]
            insights.append(
                f"Par mais frequente: **{p['par']}** — {p['ocorrencias']} concursos ({p['pct']}%)."
            )
        if sobreposicao.get("media"):
            insights.append(
                f"Média de **{sobreposicao['media']}** dígitos repetidos entre concursos consecutivos "
                f"(moda {sobreposicao.get('moda', '—')})."
            )
        if atrasos:
            mais_atrasado = atrasos[0]
            if mais_atrasado["atraso"] > 0:
                insights.append(
                    f"Dígito mais atrasado: **{mais_atrasado['digito']}** "
                    f"({mais_atrasado['atraso']} concursos sem aparecer)."
                )
        return insights

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
            return {"sucesso": False, "erro": f"Nenhum sorteio na base «{base}»."}

        linhas_chrono: List[Dict[str, Any]] = []
        conjuntos: List[Set[str]] = []
        freq_global: Counter[str] = Counter()
        presenca_concurso: Counter[str] = Counter()

        for i, s in enumerate(sorteios):
            dz = Base.dezenas_ordem(s)
            dig = analisar_digitos_concurso(dz, modality_key)
            conj = set(dig["digitos_distintos"])
            conjuntos.append(conj)
            overlap_prev = 0
            if i > 0:
                overlap_prev = len(conj & conjuntos[i - 1])
            row = {
                "concurso": s.concurso,
                "data": getattr(s, "data", "") or "",
                "dezenas": dz,
                "digitos_distintos": dig["digitos_distintos"],
                "qtd_digitos_distintos": dig["qtd_digitos_distintos"],
                "digitos_distintos_fmt": dig["digitos_distintos_fmt"],
                "digitos_repetidos_concurso_anterior": overlap_prev,
            }
            linhas_chrono.append(row)
            for d in dig["digitos_distintos"]:
                freq_global[d] += 1
                presenca_concurso[d] += 1

        total = len(linhas_chrono)
        painel_digitos = []
        for dig in [str(i) for i in range(10)]:
            qtd = presenca_concurso.get(dig, 0)
            painel_digitos.append({
                "digito": dig,
                "concursos_com_digito": qtd,
                "pct_concursos": round(qtd / total * 100, 1) if total else 0,
                "freq_aparicoes": freq_global.get(dig, 0),
            })
        painel_digitos.sort(key=lambda x: -x["concursos_com_digito"])

        matriz, top_pares = calcular_coocorrencia_digitos(conjuntos)
        atrasos = calcular_atraso_digitos(conjuntos)
        sobreposicao = sobreposicao_digitos_consecutivos(conjuntos)
        qtds = [r["qtd_digitos_distintos"] for r in linhas_chrono]
        ultimo = sorteios[-1]

        links = links_modalidade(modality_key)
        insights = cls._insights(painel_digitos, top_pares, sobreposicao, atrasos)

        return {
            "sucesso": True,
            "aba_id": "digitos-utilizados",
            "base_estatistica": base,
            "base_label": BASES_LABEL.get(base, base),
            "janela": janela,
            "total_concursos": total,
            "ultimo_concurso": ultimo.concurso,
            "linhas": list(reversed(linhas_chrono)),
            "painel_digitos": painel_digitos,
            "matriz_coocorrencia": matriz,
            "top_pares": top_pares,
            "atraso_digitos": atrasos,
            "sobreposicao_consecutiva": sobreposicao,
            "insights": insights,
            "kpis": [
                {"label": "Concursos", "valor": total},
                {"label": "Média dígitos distintos", "valor": round(sum(qtds) / len(qtds), 2) if qtds else 0},
                {"label": "Moda qtd dígitos", "valor": Counter(qtds).most_common(1)[0][0] if qtds else "—"},
                {"label": "Dígito mais frequente", "valor": painel_digitos[0]["digito"] if painel_digitos else "—"},
            ],
            "evolucao_qtd": [
                {"concurso": r["concurso"], "qtd": r["qtd_digitos_distintos"]}
                for r in linhas_chrono[-50:]
            ],
            "meta_bases": Base.meta_bases(),
            "links": {
                **links,
                "soma_digitos": f"{links.get('analises_gerais', '')}?aba=soma-digitos",
                "classificacao": f"{links.get('analises_gerais', '')}?aba=classificacao-numeros",
            },
        }
