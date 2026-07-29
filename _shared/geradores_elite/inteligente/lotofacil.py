# -*- coding: utf-8 -*-
"""Gerador inteligente Lotofácil — posição P1–P15 + repetição entre concursos."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .faixas_config import contar_faixas_volante, high_repeticao_keys, tipos_sorteio_from_faixas
from .helpers import pct
from .pool import PoolInteligenteService


class _RepSvcAdapter:
    """Adapta AnaliseRepeticaoConcursosService (Lotofácil) à interface do pool."""

    modality_key = "lotofacil"

    def analisar_completo(self, modo: str = "volante"):
        return LotofacilInteligente._rep_svc().analisar_completo(modo)

    def gerar_apostas(self, **kwargs):
        kwargs.pop("sniper_opts", None)
        kwargs.pop("volante_colunas", None)
        kwargs.pop("intrasorte", None)
        return LotofacilInteligente._rep_svc().gerar_apostas(**kwargs)

    def listar_concursos(self, limit: int = 150):
        return LotofacilInteligente._rep_svc().listar_concursos(limit)

    def _carregar_sorteios_asc(self):
        return LotofacilInteligente._rep_svc()._carregar_sorteios_asc()

    def _set_dezenas(self, row):
        return set(row.dezenas())


class LotofacilInteligente(PoolInteligenteService):
    modality_key = "lotofacil"
    modo_analise = "posicional"
    _RepSvcAdapter = _RepSvcAdapter

    @classmethod
    def _rep_svc(cls):
        from services.analise_repeticao_concursos_service import AnaliseRepeticaoConcursosService

        return AnaliseRepeticaoConcursosService

    @classmethod
    def _svc(cls):
        return cls._RepSvcAdapter()

    @classmethod
    def _faixas_repeticao(cls, svc) -> Dict[str, int]:
        return contar_faixas_volante(svc, cls.modality_key)

    @classmethod
    def painel_evidencias(cls, ctx: Dict[str, Any]) -> Dict[str, Any]:
        ev = super().painel_evidencias(ctx)
        total = int(ctx["analise"].get("total_pares_analisados") or 0)
        ev["tipos_sorteio"] = tipos_sorteio_from_faixas(
            ctx.get("faixas") or {}, total, cls.modality_key, pct
        )
        try:
            from services.analise_lotofacil_service import AnaliseLotofacilService

            atrasos = AnaliseLotofacilService.calcular_atrasos_absolutos()
            if "error" not in atrasos:
                tops = []
                for i in range(1, 16):
                    pos_key = f"posicao_{i}"
                    cand = (atrasos.get("matriz_atrasos") or {}).get(pos_key) or []
                    if cand:
                        tops.append({
                            "posicao": i,
                            "digito": int(cand[0]["numero"]),
                            "dezena": int(cand[0]["numero"]),
                            "ocorrencias": int(cand[0].get("atraso") or 0),
                            "label": f"P{i}",
                        })
                if tops:
                    ev["colunas_fortes"] = [
                        {
                            "coluna": t["posicao"],
                            "label": t["label"],
                            "vezes": t["ocorrencias"],
                            "pct": 0,
                        }
                        for t in tops[:3]
                    ]
        except Exception:
            pass
        return ev

    @classmethod
    def regras_automaticas(cls, evidencias: Dict[str, Any]) -> Dict[str, Any]:
        regras = super().regras_automaticas(evidencias)
        regras["usar_posicional"] = True
        regras["usar_atraso"] = True
        tipos = evidencias.get("tipos_sorteio") or []
        tipo_dom = tipos[0] if tipos else None
        total_c = max(int(evidencias.get("total_concursos") or 1), 1)
        if tipo_dom and tipo_dom.get("chave") in high_repeticao_keys(cls.modality_key):
            if (tipo_dom.get("vezes") or 0) > total_c * 0.15:
                regras["usar_repeticao"] = True
        return regras

    @classmethod
    def _analisar_aposta(
        cls,
        dezenas: List[int],
        regras: Dict[str, Any],
        evidencias: Dict[str, Any],
        analise: Dict[str, Any],
        extra_fields: Dict[str, Any],
    ) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
        crit, marcas = super()._analisar_aposta(dezenas, regras, evidencias, analise, extra_fields)
        if regras.get("usar_posicional"):
            crit.insert(0, {"codigo": "posicional", "texto": "Sniper por posição P1–P15"})
        if regras.get("usar_atraso"):
            crit.append({"codigo": "atraso", "texto": "Maior atraso por posição"})
        return crit, marcas

    @classmethod
    def ui_config(cls) -> Dict[str, Any]:
        cfg = super().ui_config()
        cfg.update({
            "layout": "posicional",
            "colunas_box_title": "Maior atraso por posição",
            "tipos_box_title": "Faixas de repetição",
        })
        return cfg
