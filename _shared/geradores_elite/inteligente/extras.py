# -*- coding: utf-8 -*-
"""Gerador inteligente — modalidades com linha extra (mês, time, trevos)."""
from __future__ import annotations

from typing import Any, Dict, List

from .pool import PoolInteligenteService


class DiaDeSorteInteligente(PoolInteligenteService):
    modality_key = "diadesorte"
    ui_extra_box = "mes"

    @classmethod
    def _evidencia_extra(cls, analise: Dict[str, Any]) -> Dict[str, Any]:
        extra = analise.get("extra") or {}
        if extra.get("tipo") != "mes":
            return {"tipo": "mes", "itens": []}
        itens = [
            {
                "label": "Repetiu mês no último par",
                "vezes": 1 if extra.get("repetiu_ultimo_par") else 0,
            },
            {
                "label": "Pares com mesmo mês (histórico)",
                "vezes": int(extra.get("pares_com_repeticao_historica") or 0),
            },
        ]
        for r in (extra.get("ranking") or [])[:3]:
            itens.append({
                "label": r.get("nome") or str(r.get("valor")),
                "vezes": int(r.get("vezes") or 0),
            })
        return {"tipo": "mes", "titulo": "Mês da Sorte", "itens": itens}

    @classmethod
    def _aplicar_regras_extra(cls, regras: Dict[str, Any], evidencias: Dict[str, Any]) -> None:
        linha = evidencias.get("extra_linha") or {}
        rep_ult = next((x for x in linha.get("itens") or [] if "último par" in x.get("label", "").lower()), None)
        if rep_ult and rep_ult.get("vezes"):
            regras["usar_mes"] = True
        hist = next((x for x in linha.get("itens") or [] if "histórico" in x.get("label", "").lower()), None)
        if hist and (hist.get("vezes") or 0) >= 3:
            regras["usar_mes"] = True

    @classmethod
    def _criterios_extra(
        cls,
        criterios: List[Dict[str, str]],
        marcas: Dict[str, Any],
        regras: Dict[str, Any],
        evidencias: Dict[str, Any],
        extra_fields: Dict[str, Any],
    ) -> None:
        mn = extra_fields.get("mes") or extra_fields.get("mes_num")
        if mn:
            abrev = extra_fields.get("mes_abrev") or extra_fields.get("mes_nome") or str(mn)
            criterios.append({
                "codigo": "mes",
                "texto": f"Mês da Sorte: {abrev}",
            })

    @classmethod
    def ui_config(cls) -> Dict[str, Any]:
        cfg = super().ui_config()
        cfg.update({
            "extra_box_title": "Mês da Sorte",
            "show_mes_rule": True,
        })
        return cfg


class TimemaniaInteligente(PoolInteligenteService):
    modality_key = "timemania"
    ui_extra_box = "time"

    @classmethod
    def _evidencia_extra(cls, analise: Dict[str, Any]) -> Dict[str, Any]:
        extra = analise.get("extra") or {}
        if extra.get("tipo") != "time":
            return {"tipo": "time", "itens": []}
        itens = [
            {
                "label": "Repetiu time no último par",
                "vezes": 1 if extra.get("repetiu_ultimo_par") else 0,
            },
            {
                "label": "Pares com mesmo time (histórico)",
                "vezes": int(extra.get("pares_com_repeticao_historica") or 0),
            },
        ]
        for r in (extra.get("ranking") or [])[:3]:
            nome = r.get("nome") or f"Time {r.get('valor')}"
            itens.append({"label": str(nome)[:40], "vezes": int(r.get("vezes") or 0)})
        return {"tipo": "time", "titulo": "Time do Coração", "itens": itens}

    @classmethod
    def _aplicar_regras_extra(cls, regras: Dict[str, Any], evidencias: Dict[str, Any]) -> None:
        linha = evidencias.get("extra_linha") or {}
        for it in linha.get("itens") or []:
            if "último par" in (it.get("label") or "").lower() and it.get("vezes"):
                regras["usar_time"] = True
            if "histórico" in (it.get("label") or "").lower() and (it.get("vezes") or 0) >= 2:
                regras["usar_time"] = True

    @classmethod
    def _criterios_extra(
        cls,
        criterios: List[Dict[str, str]],
        marcas: Dict[str, Any],
        regras: Dict[str, Any],
        evidencias: Dict[str, Any],
        extra_fields: Dict[str, Any],
    ) -> None:
        if regras.get("usar_time") and extra_fields.get("time_nome"):
            criterios.append({
                "codigo": "time",
                "texto": f"Time: {extra_fields.get('time_nome')}",
            })

    @classmethod
    def ui_config(cls) -> Dict[str, Any]:
        cfg = super().ui_config()
        cfg.update({"extra_box_title": "Time do Coração", "show_time_rule": True})
        return cfg


class MaisMilionariaInteligente(PoolInteligenteService):
    modality_key = "maismilionaria"
    ui_extra_box = "trevo"

    @classmethod
    def _evidencia_extra(cls, analise: Dict[str, Any]) -> Dict[str, Any]:
        extra = analise.get("extra") or {}
        if extra.get("tipo") not in ("trevo", "trevos"):
            return {"tipo": "trevo", "itens": []}
        itens = [
            {
                "label": "Trevos repetidos (último par)",
                "vezes": int(extra.get("quantidade_ultimo_par") or len(extra.get("repetidos_ultimo_par") or [])),
            },
            {
                "label": "Pares com trevos iguais (hist.)",
                "vezes": int(extra.get("pares_com_repeticao_historica") or 0),
            },
        ]
        for r in (extra.get("ranking") or [])[:3]:
            itens.append({
                "label": f"Trevo {r.get('valor', r.get('trevo'))}",
                "vezes": int(r.get("vezes") or 0),
            })
        return {"tipo": "trevo", "titulo": "Trevos", "itens": itens}

    @classmethod
    def _aplicar_regras_extra(cls, regras: Dict[str, Any], evidencias: Dict[str, Any]) -> None:
        linha = evidencias.get("extra_linha") or {}
        for it in linha.get("itens") or []:
            if "último" in (it.get("label") or "").lower() and (it.get("vezes") or 0) >= 1:
                regras["usar_trevos"] = True

    @classmethod
    def _criterios_extra(
        cls,
        criterios: List[Dict[str, str]],
        marcas: Dict[str, Any],
        regras: Dict[str, Any],
        evidencias: Dict[str, Any],
        extra_fields: Dict[str, Any],
    ) -> None:
        trevos = extra_fields.get("trevos") or extra_fields.get("trevos_lista")
        if regras.get("usar_trevos") and trevos:
            t = trevos if isinstance(trevos, list) else list(trevos)
            criterios.append({"codigo": "trevo", "texto": f"Trevos: {'-'.join(str(x) for x in sorted(t))}"})

    @classmethod
    def ui_config(cls) -> Dict[str, Any]:
        cfg = super().ui_config()
        cfg.update({"extra_box_title": "Trevos", "show_trevo_rule": True})
        return cfg
