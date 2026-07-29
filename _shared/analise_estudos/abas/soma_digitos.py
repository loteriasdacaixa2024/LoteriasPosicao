# -*- coding: utf-8 -*-
"""Aba 1 — Soma dos Dígitos das Dezenas."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Type

from analise_estudos.base_service import AnaliseEstudosBase
from analise_estudos.core.digitos import analisar_digitos_concurso, mapa_soma_por_dezena
from analise_estudos.service_factory import make_estudos_base
from analise_estudos.specs import BASES_LABEL, links_modalidade


class SomaDigitosAba:
    @classmethod
    def _base_cls(cls, modality_key: str) -> Type[AnaliseEstudosBase]:
        return make_estudos_base(modality_key)

    @classmethod
    def _insights(
        cls,
        somas_totais: List[int],
        distribuicao: List[Dict[str, Any]],
        ultimo_soma: int,
        media: float,
    ) -> List[str]:
        insights: List[str] = []
        if distribuicao:
            top = max(distribuicao, key=lambda x: x["ocorrencias"])
            insights.append(
                f"Soma total de dígitos mais frequente: **{top['valor']}** "
                f"({top['ocorrencias']}×, {top['pct']}%)."
            )
        if somas_totais:
            pares = sum(1 for s in somas_totais if s % 2 == 0)
            pct_p = round(pares / len(somas_totais) * 100, 1)
            insights.append(f"Somas totais **pares** em {pct_p}% dos concursos da janela.")
            delta = ultimo_soma - media
            tend = "acima" if delta > 0.5 else ("abaixo" if delta < -0.5 else "na")
            insights.append(
                f"Último concurso: soma **{ultimo_soma}** ({tend} média {round(media, 1)})."
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
        cfg = Base._cfg()
        janela = Base._normalizar_janela(janela)
        base = Base._normalizar_base(base_estatistica)
        sorteios = Base.carregar_sorteios_asc(base, janela if janela > 0 else 0)

        if not sorteios:
            return {"sucesso": False, "erro": f"Nenhum sorteio na base «{base}»."}

        linhas_chrono: List[Dict[str, Any]] = []
        somas_totais: List[int] = []

        for s in sorteios:
            dz = Base.dezenas_ordem(s)
            dig = analisar_digitos_concurso(dz, modality_key)
            soma_tot = dig["soma_total_digitos"]
            somas_totais.append(soma_tot)
            linhas_chrono.append({
                "concurso": s.concurso,
                "data": getattr(s, "data", "") or "",
                "dezenas": dz,
                "soma_total_digitos": soma_tot,
                "media_soma_digitos": dig["media_soma_digitos"],
                "soma_dezenas": dig["soma_dezenas"],
                "soma_par": soma_tot % 2 == 0,
                "somas_por_dezena": dig["somas_por_dezena"],
            })

        cnt = Counter(somas_totais)
        moda, moda_n = cnt.most_common(1)[0] if cnt else (0, 0)
        total = len(linhas_chrono)
        media = sum(somas_totais) / total if total else 0
        ultimo = sorteios[-1]
        ultimo_soma = somas_totais[-1] if somas_totais else 0

        distribuicao = [
            {"valor": k, "ocorrencias": v, "pct": round(v / total * 100, 1)}
            for k, v in sorted(cnt.items())
        ]

        # Frequência de soma fixa por dezena sorteada (agregado na janela)
        freq_soma_dezena: Counter[int] = Counter()
        for row in linhas_chrono:
            for item in row.get("somas_por_dezena") or []:
                freq_soma_dezena[int(item["soma_digitos"])] += 1

        mapa_dezena = mapa_soma_por_dezena(
            cfg["dezena_min"], cfg["dezena_max"], cfg.get("pad_width", 2),
        )

        links = links_modalidade(modality_key)
        insights = cls._insights(somas_totais, distribuicao, ultimo_soma, media)

        return {
            "sucesso": True,
            "aba_id": "soma-digitos",
            "base_estatistica": base,
            "base_label": BASES_LABEL.get(base, base),
            "janela": janela,
            "total_concursos": total,
            "ultimo_concurso": ultimo.concurso,
            "linhas": list(reversed(linhas_chrono)),
            "distribuicao_soma_total": distribuicao,
            "freq_soma_por_dezena_sorteada": [
                {"soma_digitos": k, "ocorrencias": v}
                for k, v in sorted(freq_soma_dezena.items())
            ],
            "mapa_dezena_soma": mapa_dezena,
            "insights": insights,
            "kpis": [
                {"label": "Concursos", "valor": total},
                {"label": "Moda soma dígitos", "valor": f"{moda} ({round(moda_n / total * 100, 1) if total else 0}%)"},
                {"label": "Média soma dígitos", "valor": round(media, 2)},
                {"label": "Min / Max", "valor": f"{min(somas_totais) if somas_totais else '—'} / {max(somas_totais) if somas_totais else '—'}"},
            ],
            "evolucao": [
                {"concurso": r["concurso"], "soma_total_digitos": r["soma_total_digitos"]}
                for r in linhas_chrono[-50:]
            ],
            "meta_bases": Base.meta_bases(),
            "links": {
                **links,
                "digitos_utilizados": f"{links.get('analises_gerais', '')}?aba=digitos-utilizados",
                "classificacao": f"{links.get('analises_gerais', '')}?aba=classificacao-numeros",
            },
        }
