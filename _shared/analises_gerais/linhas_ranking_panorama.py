# -*- coding: utf-8 -*-
"""
Ranking comportamental das Linhas L1–L10 — panorama Central (todas as modalidades).

Reutiliza:
  - carregar_registros (SQLite da Central)
  - linhas_universo.core (classificação oficial L1–L10)
Mesma regra de presença por concurso usada em LinhasUniversoService.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional

from _shared.analises_gerais.comportamento_loader import carregar_registros
from _shared.analises_gerais.comportamento_panorama import MODALITY_THEMES
from _shared.analises_gerais.registry import SPECS, SPECS_BY_KEY
from linhas_universo.core import classificar_dezenas, linhas_para_modalidade


class LinhasRankingCentralService:
    @classmethod
    def panorama(
        cls,
        janela: int = 0,
        modality_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        if modality_key:
            if modality_key not in SPECS_BY_KEY:
                raise KeyError(modality_key)
            specs = [SPECS_BY_KEY[modality_key]]
        else:
            specs = list(SPECS)

        modalidades = [cls._analisar_mod(sp, janela) for sp in specs]
        return {
            "janela": int(janela or 0),
            "filtro_modalidade": modality_key,
            "total_modalidades": len(modalidades),
            "modalidades": modalidades,
        }

    @classmethod
    def _analisar_mod(cls, spec, janela: int) -> Dict[str, Any]:
        theme = MODALITY_THEMES.get(spec.key, {})
        link = f"http://localhost:{spec.porta}/analise/linhas-dd-du/"
        base = {
            "key": spec.key,
            "nome": spec.nome,
            "porta": spec.porta,
            "theme": theme,
            "link_linhas": link,
        }

        try:
            mapa = linhas_para_modalidade(spec.key)
        except Exception as e:
            return {**base, "erro": f"Mapa de linhas indisponível: {e}"}

        regs, status = carregar_registros(spec)
        if not regs:
            return {
                **base,
                "erro": status if status != "ok" else "Sem sorteios no banco.",
                "mapa": mapa,
            }

        j = int(janela or 0)
        if j > 0:
            regs = regs[-j:]

        freq: Counter = Counter()
        atraso: Dict[str, int] = {L["id"]: 0 for L in mapa["linhas"]}
        visto: Dict[str, bool] = {L["id"]: False for L in mapa["linhas"]}

        for rec in regs:
            cl = classificar_dezenas(rec.dezenas)
            presentes = set(cl["linhas_presentes"])
            for lid in presentes:
                freq[lid] += 1
            for lid in atraso:
                if lid in presentes:
                    atraso[lid] = 0
                    visto[lid] = True
                else:
                    atraso[lid] += 1

        total = len(regs)
        ranking: List[Dict[str, Any]] = []
        for L in mapa["linhas"]:
            lid = L["id"]
            n = int(freq.get(lid, 0))
            ranking.append({
                "linha": lid,
                "label": L["label"],
                "ocorrencias": n,
                "pct": round(n / total * 100, 2) if total else 0,
                "atraso": atraso[lid] if visto[lid] else total,
                "qtd_dezenas_universo": L["qtd"],
            })

        ranking.sort(
            key=lambda x: (-x["ocorrencias"], str(x["linha"])),
        )
        for i, row in enumerate(ranking, start=1):
            row["posicao"] = i

        top3 = ranking[:3]
        return {
            **base,
            "erro": None,
            "janela": j,
            "total_concursos": total,
            "primeiro_concurso": regs[0].concurso,
            "ultimo_concurso": regs[-1].concurso,
            "qtd_linhas": mapa["qtd_linhas"],
            "mapa": mapa,
            "ranking": ranking,
            "top3": top3,
        }
