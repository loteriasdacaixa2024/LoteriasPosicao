# -*- coding: utf-8 -*-
"""Serviço — listagem de sorteios para Escolha Visual."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from analise_estudos.service_factory import make_estudos_base
from analise_estudos.specs import get_estudos_config, tem_analise_estudos

LIMITES_UI = (50, 100, 200, 500, 0)


class AnaliseEscolhaVisualService:
    @classmethod
    def listar_sorteios(
        cls,
        modality_key: str,
        *,
        ordem: str = "desc",
        limite: int = 0,
        base_estatistica: str = "geral",
    ) -> Dict[str, Any]:
        if not tem_analise_estudos(modality_key):
            return {"sucesso": False, "erro": "Modalidade não suportada."}

        Base = make_estudos_base(modality_key)
        cfg = get_estudos_config(modality_key)
        rows = Base.carregar_sorteios_asc(base_estatistica=base_estatistica, janela=0)

        sorteios: List[Dict[str, Any]] = []
        for r in rows:
            numeros = [int(x) for x in Base.dezenas_ordem(r)]
            item: Dict[str, Any] = {
                "concurso": int(r.concurso),
                "data": getattr(r, "data", "") or "",
                "numeros": numeros,
                "numeros_ordenados": sorted(numeros),
            }
            mes_num = getattr(r, "mes_num", None)
            if mes_num:
                item["mes_num"] = int(mes_num)
                item["mes_nome"] = getattr(r, "mes_nome", "") or ""
            sorteios.append(item)

        ordem_n = (ordem or "desc").strip().lower()
        if ordem_n == "asc":
            sorteios.sort(key=lambda s: s["concurso"])
        else:
            sorteios.sort(key=lambda s: s["concurso"], reverse=True)
            ordem_n = "desc"

        total = len(sorteios)
        lim = int(limite or 0)
        if lim > 0:
            sorteios = sorteios[:lim]

        return {
            "sucesso": True,
            "modality_key": modality_key,
            "modality_nome": cfg["nome"],
            "dezena_min": cfg["dezena_min"],
            "dezena_max": cfg["dezena_max"],
            "sorteadas": cfg["sorteadas"],
            "pad_width": cfg["pad_width"],
            "extra_mes": bool(cfg.get("extra_mes")),
            "ordem": ordem_n,
            "limite": lim,
            "total_disponivel": total,
            "total": len(sorteios),
            "sorteios": sorteios,
        }

    @classmethod
    def ui_meta(cls, modality_key: str) -> Dict[str, Any]:
        cfg = get_estudos_config(modality_key)
        return {
            "limites": list(LIMITES_UI),
            "dezena_min": cfg["dezena_min"],
            "dezena_max": cfg["dezena_max"],
            "sorteadas": cfg["sorteadas"],
            "pad_width": cfg["pad_width"],
            "extra_mes": bool(cfg.get("extra_mes")),
            "nome": cfg["nome"],
        }
