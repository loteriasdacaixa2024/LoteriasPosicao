# -*- coding: utf-8 -*-
"""Aba — Diferencial Cruzado (Subtração + Soma entre último e penúltimo sorteio)."""
from __future__ import annotations

from typing import Any, Dict, List, Type

from analise_estudos.base_service import AnaliseEstudosBase
from analise_estudos.core.diferencial_cruzado import (
    analisar_par,
    ranking_atraso,
    ranking_frequencia,
)
from analise_estudos.service_factory import make_estudos_base
from analise_estudos.specs import BASES_LABEL, links_modalidade


class DiferencialCruzadoAba:
    @classmethod
    def _base_cls(cls, modality_key: str) -> Type[AnaliseEstudosBase]:
        return make_estudos_base(modality_key)

    @classmethod
    def _fmt_dezenas(cls, dz: List[int], pad: int = 2) -> str:
        p = max(1, int(pad))
        return " ".join(f"{int(d):0{p}d}" for d in (dz or []))

    @classmethod
    def _bloco(
        cls,
        titulo: str,
        ultimo: List[int],
        penultimo: List[int],
        dmin: int,
        dmax: int,
        negativos_modo: str,
        freq_rank: List[int],
        atraso_rank: List[int],
        pad: int,
        ultimo_concurso: int,
        penultimo_concurso: int,
        ultimo_data: str = "",
        penultimo_data: str = "",
    ) -> Dict[str, Any]:
        calc = analisar_par(
            ultimo, penultimo, dmin, dmax,
            negativos_modo=negativos_modo,
            freq_rank=freq_rank,
            atraso_rank=atraso_rank,
            pad_width=pad,
        )
        return {
            "titulo": titulo,
            "ultimo_concurso": ultimo_concurso,
            "penultimo_concurso": penultimo_concurso,
            "ultimo_data": ultimo_data,
            "penultimo_data": penultimo_data,
            "ultimo": ultimo,
            "penultimo": penultimo,
            "subtracao_signed": calc["subtracao_signed"],
            "subtracao_abs": calc["subtracao_abs"],
            "resultado": calc["resultado"],
            "numeros_apostar_ordenados": calc["aposta_ordenada"],
            "numeros_apostar_posicional": calc["normalizados"],
            "avisos": calc["avisos"],
            "teve_ajuste": calc["teve_ajuste"],
            "tem_negativos": calc["tem_negativos"],
        }

    @classmethod
    def analisar(
        cls,
        modality_key: str,
        janela: int = 10,
        base_estatistica: str = "geral",
        negativos_modo: str = "abs",
    ) -> Dict[str, Any]:
        Base = cls._base_cls(modality_key)
        cfg = Base._cfg()
        janela = Base._normalizar_janela(janela)
        base = Base._normalizar_base(base_estatistica)
        sorteios = Base.carregar_sorteios_asc(base, 0)

        if len(sorteios) < 2:
            return {
                "sucesso": False,
                "erro": "São necessários pelo menos 2 concursos para o Diferencial Cruzado.",
            }

        dmin = int(cfg["dezena_min"])
        dmax = int(cfg["dezena_max"])
        pad = int(cfg.get("pad_width", 2))

        ultimo_s = sorteios[-1]
        penultimo_s = sorteios[-2]

        ultimo_ordem = Base.dezenas_ordem(ultimo_s)
        penultimo_ordem = Base.dezenas_ordem(penultimo_s)
        ultimo_sorted = sorted(ultimo_ordem)
        penultimo_sorted = sorted(penultimo_ordem)

        janela_hist = sorteios[-janela:] if janela > 0 else sorteios
        hist_dez = [Base.dezenas_ordem(s) for s in janela_hist]
        freq_rank = ranking_frequencia(hist_dez, dmin, dmax)
        atraso_rank = ranking_atraso(janela_hist, Base.dezenas_ordem, dmin, dmax)

        modo = (negativos_modo or "abs").strip().lower()
        if modo not in ("abs",):
            modo = "abs"

        bloco_ord = cls._bloco(
            "Dezenas ordenadas",
            ultimo_sorted,
            penultimo_sorted,
            dmin,
            dmax,
            modo,
            freq_rank,
            atraso_rank,
            pad,
            ultimo_s.concurso,
            penultimo_s.concurso,
            getattr(ultimo_s, "data", "") or "",
            getattr(penultimo_s, "data", "") or "",
        )
        bloco_pos = cls._bloco(
            "Ordem posicional (sorteio)",
            ultimo_ordem,
            penultimo_ordem,
            dmin,
            dmax,
            modo,
            freq_rank,
            atraso_rank,
            pad,
            ultimo_s.concurso,
            penultimo_s.concurso,
            getattr(ultimo_s, "data", "") or "",
            getattr(penultimo_s, "data", "") or "",
        )

        historico: List[Dict[str, Any]] = []
        pares = sorteios[-janela:] if janela > 0 else sorteios
        for i in range(1, len(pares)):
            u = pares[i]
            p = pares[i - 1]
            uo = Base.dezenas_ordem(u)
            po = Base.dezenas_ordem(p)
            calc = analisar_par(
                uo, po, dmin, dmax,
                negativos_modo=modo,
                freq_rank=freq_rank,
                atraso_rank=atraso_rank,
                pad_width=pad,
            )
            historico.append({
                "concurso": u.concurso,
                "data": getattr(u, "data", "") or "",
                "penultimo_concurso": p.concurso,
                "ultimo_fmt": cls._fmt_dezenas(uo, pad),
                "penultimo_fmt": cls._fmt_dezenas(po, pad),
                "aposta_ordenada": calc["aposta_ordenada"],
                "aposta_ordenada_fmt": cls._fmt_dezenas(calc["aposta_ordenada"], pad),
                "teve_ajuste": calc["teve_ajuste"],
            })

        avisos_global = list(dict.fromkeys(
            bloco_ord["avisos"] + bloco_pos["avisos"]
        ))
        insights = [
            f"**Diferencial Cruzado** — último #{ultimo_s.concurso} vs penúltimo #{penultimo_s.concurso}.",
            "Subtração: `último[i] − penúltimo[i]` · Resultado: `último[i] + subtração[i]`.",
            f"Pool válido: **{dmin:02d}–{dmax:02d}** · Negativos convertidos em positivo (|valor|).",
        ]
        if avisos_global:
            insights.append(
                f"**{len(avisos_global)} ajuste(s)** na normalização (fora do pool, soma de dígitos ou duplicata)."
            )
        if bloco_ord["tem_negativos"] or bloco_pos["tem_negativos"]:
            insights.append("Há **subtrações negativas** em pelo menos um dos modos (ordenado ou posicional).")

        links = links_modalidade(modality_key)
        return {
            "sucesso": True,
            "aba_id": "diferencial-cruzado",
            "modality_nome": cfg["nome"],
            "base_estatistica": base,
            "base_label": BASES_LABEL.get(base, base),
            "janela": janela,
            "negativos_modo": modo,
            "ultimo_concurso": ultimo_s.concurso,
            "penultimo_concurso": penultimo_s.concurso,
            "ultimo_data": getattr(ultimo_s, "data", "") or "",
            "penultimo_data": getattr(penultimo_s, "data", "") or "",
            "dezena_min": dmin,
            "dezena_max": dmax,
            "pad_width": pad,
            "bloco_ordenado": bloco_ord,
            "bloco_posicional": bloco_pos,
            "historico": list(reversed(historico)),
            "avisos": avisos_global,
            "insights": insights,
            "kpis": [
                {"label": "Último concurso", "valor": f"#{ultimo_s.concurso}"},
                {"label": "Penúltimo", "valor": f"#{penultimo_s.concurso}"},
                {
                    "label": "Aposta (ordenada)",
                    "valor": cls._fmt_dezenas(bloco_ord["numeros_apostar_ordenados"], pad),
                },
                {
                    "label": "Aposta (posicional)",
                    "valor": cls._fmt_dezenas(bloco_pos["numeros_apostar_ordenados"], pad),
                },
            ],
            "meta_bases": Base.meta_bases(),
            "links": links,
        }
