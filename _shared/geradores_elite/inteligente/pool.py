# -*- coding: utf-8 -*-
"""Gerador inteligente — modalidades em volante (Quina, Mega, Lotomania, etc.)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Type

from analise_repeticao.repeticao_config import get_repeticao_config
from analise_repeticao.repeticao_service import RepeticaoConcursosService

from .faixas_config import (
    contar_faixas_volante,
    high_repeticao_keys,
    tipos_sorteio_from_faixas,
)
from .helpers import labels_regras_auto, pct


class PoolInteligenteService:
    """Evidências + auto/manual para jogos por conjunto de dezenas."""

    modality_key: str = "quina"
    modo_analise: str = "volante"
    ui_extra_box: str = "permanencia"  # permanencia | mes | time | trevo

    @classmethod
    def _svc(cls) -> RepeticaoConcursosService:
        return RepeticaoConcursosService(cls.modality_key)

    @classmethod
    def _faixas_repeticao(cls, svc: RepeticaoConcursosService) -> Dict[str, int]:
        return contar_faixas_volante(svc, cls.modality_key)

    @classmethod
    def montar_contexto(cls) -> Dict[str, Any]:
        svc = cls._svc()
        analise = svc.analisar_completo(cls.modo_analise)
        if not analise.get("sucesso"):
            return analise
        faixas = cls._faixas_repeticao(svc)
        return {
            "sucesso": True,
            "sequencial": analise,
            "analise": analise,
            "faixas": faixas,
        }

    @classmethod
    def painel_evidencias(cls, ctx: Dict[str, Any]) -> Dict[str, Any]:
        a = ctx["analise"]
        total = int(a.get("total_pares_analisados") or 0)
        faixas = ctx.get("faixas") or {}
        resumo = a.get("resumo_ultimo_par") or {}
        vol = resumo.get("volante") or {}
        pos = resumo.get("posicional") or {}

        repeticoes = {
            "ultimo_par_volante": {
                "qtd": int(vol.get("quantidade") or 0),
                "label": "Repetidas no último par (volante)",
                "pct": pct(int(vol.get("quantidade") or 0), max(total, 1)),
            },
            "ultimo_par_posicional": {
                "qtd": int(pos.get("quantidade") or 0),
                "label": "Repetidas no último par (posicional)",
                "pct": pct(int(pos.get("quantidade") or 0), max(total, 1)),
            },
            "media_volante": {
                "qtd": int(round(float(resumo.get("media_historica_quantidade_volante") or 0))),
                "label": "Média histórica (volante)",
                "pct": 0,
            },
            "media_posicional": {
                "qtd": int(round(float(resumo.get("media_historica_posicional") or 0))),
                "label": "Média histórica (posicional)",
                "pct": 0,
            },
        }

        tipos_sorteio = tipos_sorteio_from_faixas(faixas, total, cls.modality_key, pct)

        ranking = a.get("ranking_mais_repetem") or []
        numeros_fortes = [
            {
                "posicao": i + 1,
                "digito": r["dezena"],
                "dezena": r["dezena"],
                "ocorrencias": int(r.get("vezes") or 0),
            }
            for i, r in enumerate(ranking[:3])
        ]

        detalhe = a.get("dezenas") or []
        perm_rank = sorted(
            detalhe,
            key=lambda r: (-int(r.get("permanencia_vezes") or 0), -float(r.get("permanencia_pct") or 0)),
        )[:3]
        colunas_fortes = [
            {
                "coluna": r["dezena"],
                "label": f"Dezena {r['dezena']:02d}" if r["dezena"] >= 10 else f"Dezena {r['dezena']}",
                "vezes": int(r.get("permanencia_vezes") or 0),
                "pct": float(r.get("permanencia_pct") or 0),
            }
            for r in perm_rank
        ]

        ev: Dict[str, Any] = {
            "total_concursos": total + 1 if total else 0,
            "repeticoes": repeticoes,
            "tipos_sorteio": tipos_sorteio,
            "numeros_fortes": numeros_fortes,
            "numeros_frios": [],
            "colunas_fortes": colunas_fortes,
            "colunas_fracas": [],
            "top_pares_colunas": [],
            "extra_linha": cls._evidencia_extra(a),
        }
        return ev

    @classmethod
    def _evidencia_extra(cls, analise: Dict[str, Any]) -> Dict[str, Any]:
        return {"tipo": cls.ui_extra_box, "itens": []}

    @classmethod
    def regras_automaticas(cls, evidencias: Dict[str, Any]) -> Dict[str, Any]:
        """Regras conservadoras — exige evidência clara antes de ativar."""
        rep = evidencias["repeticoes"]
        tipos = evidencias["tipos_sorteio"]
        tipo_dom = tipos[0] if tipos else None
        ult_vol = rep["ultimo_par_volante"]["qtd"]
        media_v = rep["media_volante"]["qtd"]

        regras = {
            "usar_repeticao": ult_vol >= 1 or media_v >= 1,
            "usar_dupla": False,
            "usar_trinca": False,
            "usar_numeros_quentes": bool(evidencias.get("numeros_fortes")),
            "usar_numeros_frios": False,
            "usar_colunas_fortes": False,
            "usar_colunas_fracas": False,
            "usar_posicional": rep["ultimo_par_posicional"]["qtd"] >= rep["ultimo_par_volante"]["qtd"],
            "usar_permanencia": bool(evidencias.get("colunas_fortes")),
            "usar_par_impar": True,
            "usar_sequencial": False,
            "usar_ultimo_par": ult_vol >= 1,
            "usar_pares_colunas": False,
            "usar_atraso": False,
            "usar_ciclo": False,
            "forcar_par_colunas": False,
            "tipo_sorteio_alvo": "",
            "digito_foco": None,
            "dezena_foco": None,
            "par_colunas_idx": 0,
            "so_permanencia": False,
        }

        total_c = max(int(evidencias.get("total_concursos") or 1), 1)
        if tipo_dom and tipo_dom.get("chave") != "0" and int(tipo_dom.get("vezes") or 0) >= max(
            (tipos[1].get("vezes") or 0) if len(tipos) > 1 else 0,
            1,
        ):
            if tipo_dom["chave"] in high_repeticao_keys(cls.modality_key) and (
                tipo_dom.get("vezes") or 0
            ) > total_c * 0.15:
                regras["usar_repeticao"] = True
        tops = evidencias.get("numeros_fortes") or []
        if tops and (tops[0].get("ocorrencias") or 0) >= 3:
            regras["dezena_foco"] = tops[0].get("dezena")
        if evidencias.get("colunas_fortes"):
            top_perm = evidencias["colunas_fortes"][0]
            if (top_perm.get("vezes") or 0) >= 2:
                regras["so_permanencia"] = True

        cls._aplicar_regras_extra(regras, evidencias)
        return regras

    @classmethod
    def _aplicar_regras_extra(cls, regras: Dict[str, Any], evidencias: Dict[str, Any]) -> None:
        pass

    @classmethod
    def _regras_para_opts(cls, regras: Dict[str, Any], evidencias: Dict[str, Any]) -> Dict[str, Any]:
        foco = regras.get("dezena_foco") if regras.get("dezena_foco") is not None else regras.get("digito_foco")
        return {
            "usar_sequencial": bool(regras.get("usar_sequencial")),
            "usar_volante_atraso": bool(regras.get("usar_atraso")),
            "usar_top_digitos": bool(regras.get("usar_numeros_quentes")),
            "usar_numeros_frios": bool(regras.get("usar_numeros_frios")),
            "usar_pares_colunas": False,
            "forcar_par_colunas": False,
            "par_colunas_idx": None,
            "tipo_sorteio_alvo": regras.get("tipo_sorteio_alvo") or "",
            "digito_foco": foco,
            "dezena_foco": foco,
            "usar_colunas_fortes": False,
            "usar_colunas_fracas": False,
            "usar_permanencia": bool(regras.get("usar_permanencia")),
            "usar_par_impar": bool(regras.get("usar_par_impar", True)),
            "so_permanencia": bool(regras.get("so_permanencia")),
            "usar_mes": bool(regras.get("usar_mes")),
            "usar_time": bool(regras.get("usar_time")),
            "usar_trevos": bool(regras.get("usar_trevos")),
            "regras_ativas": regras,
            "evidencias": evidencias,
        }

    @classmethod
    def _analisar_aposta(
        cls,
        dezenas: List[int],
        regras: Dict[str, Any],
        evidencias: Dict[str, Any],
        analise: Dict[str, Any],
        extra_fields: Dict[str, Any],
    ) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
        criterios: List[Dict[str, str]] = []
        marcas: Dict[str, Any] = {"digitos": {}, "colunas": {}}

        rep_vol = set(analise.get("resumo_ultimo_par", {}).get("volante", {}).get("dezenas") or [])
        quentes = {x.get("dezena") for x in evidencias.get("numeros_fortes") or []}

        do_ult = [d for d in dezenas if d in rep_vol]
        if do_ult and regras.get("usar_ultimo_par"):
            criterios.append({
                "codigo": "ultimo_par",
                "texto": f"Último par ({len(do_ult)} dez.): {', '.join(f'{d:02d}' if d < 100 else str(d) for d in sorted(do_ult))}",
            })

        quentes_usados = sorted({d for d in dezenas if d in quentes})
        if quentes_usados and regras.get("usar_numeros_quentes"):
            criterios.append({
                "codigo": "quente",
                "texto": f"Números quentes: {', '.join(f'{d:02d}' if d < 100 else str(d) for d in quentes_usados)}",
            })
            for d in quentes_usados:
                marcas["digitos"][str(d)] = "quente"

        for d in do_ult:
            marcas["digitos"][str(d)] = marcas["digitos"].get(str(d)) or "seq-rep"

        if regras.get("usar_permanencia"):
            criterios.append({"codigo": "permanencia", "texto": "Tendência de permanência"})
        if regras.get("usar_par_impar"):
            p = sum(1 for x in dezenas if x % 2 == 0)
            criterios.append({"codigo": "par_impar", "texto": f"Par/ímpar ({p} pares)"})

        cls._criterios_extra(criterios, marcas, regras, evidencias, extra_fields)
        return criterios, marcas

    @classmethod
    def _criterios_extra(
        cls,
        criterios: List[Dict[str, str]],
        marcas: Dict[str, Any],
        regras: Dict[str, Any],
        evidencias: Dict[str, Any],
        extra_fields: Dict[str, Any],
    ) -> None:
        pass

    @classmethod
    def gerar(
        cls,
        quantidade: int,
        perfil: str,
        modo_geracao: str,
        dezenas_por_jogo: Optional[int] = None,
        regras_manuais: Optional[Dict[str, Any]] = None,
        usar_ultimo_par_chk: bool = True,
    ) -> Dict[str, Any]:
        ctx = cls.montar_contexto()
        if not ctx.get("sucesso"):
            return ctx

        evidencias = cls.painel_evidencias(ctx)
        analise = ctx["analise"]
        from geradores_elite.inteligente_page import repeticao_cfg_for_page

        rep_cfg = repeticao_cfg_for_page(cls.modality_key)

        if modo_geracao == "automatico":
            regras = cls.regras_automaticas(evidencias)
            criterios_auto = labels_regras_auto(regras)
        else:
            regras = dict(regras_manuais or {})
            regras.setdefault("usar_ultimo_par", usar_ultimo_par_chk)
            criterios_auto = []

        opts = cls._regras_para_opts(regras, evidencias)
        k = dezenas_por_jogo or rep_cfg.get("dezenas_default")
        modo = "posicional" if regras.get("usar_posicional") and "posicional" in (rep_cfg.get("modos") or ["volante"]) else cls.modo_analise

        raw = cls._svc().gerar_apostas(
            quantidade=quantidade,
            dezenas_por_jogo=k,
            modo=modo,
            perfil=perfil,
            usar_ultimo_par=bool(regras.get("usar_ultimo_par", True)),
            so_permanencia=bool(regras.get("so_permanencia")),
            respeitar_par_impar=bool(regras.get("usar_par_impar", True)),
            analise=analise,
            sniper_opts=opts,
        )
        if not raw.get("sucesso"):
            return raw

        apostas_out = []
        for a in raw.get("apostas") or []:
            extra = {k: v for k, v in a.items() if k not in ("numero", "dezenas", "texto", "quantidade", "pares", "impares", "do_ultimo_par")}
            crit, marcas = cls._analisar_aposta(a["dezenas"], regras, evidencias, analise, extra)
            apostas_out.append({**a, "criterios": crit, "marcas": marcas})

        out = {
            "sucesso": True,
            "apostas": apostas_out,
            "total_geradas": len(apostas_out),
            "solicitados": quantidade,
            "aviso": raw.get("aviso"),
            "modo_geracao": modo_geracao,
            "evidencias": evidencias,
            "regras_aplicadas": regras,
            "criterios_modo_auto": criterios_auto,
            "motor": "inteligente_pool",
            "modality": cls.modality_key,
        }
        try:
            from geradores_elite.validacao.validador_global import ValidadorGeradoresElite
            out = ValidadorGeradoresElite.aplicar(
                out, origem="sniper_apostas", modality_key=cls.modality_key, campo="apostas",
            )
        except Exception:
            pass
        return out

    @classmethod
    def analise_completa_api(cls) -> Dict[str, Any]:
        ctx = cls.montar_contexto()
        if not ctx.get("sucesso"):
            return ctx
        ev = cls.painel_evidencias(ctx)
        auto = cls.regras_automaticas(ev)
        return {
            "sucesso": True,
            "evidencias": ev,
            "regras_automaticas": auto,
            "criterios_auto_preview": labels_regras_auto(auto),
            "sequencial": ctx["analise"],
            "ui": cls.ui_config(),
            "motor": "inteligente_pool",
            "modality": cls.modality_key,
        }

    @classmethod
    def ui_config(cls) -> Dict[str, Any]:
        return {
            "layout": "pool",
            "show_coluna_rules": False,
            "show_digito_foco": False,
            "show_dezena_foco": True,
            "show_tipo_intrasorte": False,
            "extra_box_title": "Permanência",
            "colunas_box_title": "Maior permanência",
        }


def pool_subclass(key: str, **kwargs: Any) -> Type[PoolInteligenteService]:
    name = f"{key.title()}Inteligente"
    return type(name, (PoolInteligenteService,), {"modality_key": key, **kwargs})


QuinaInteligente = pool_subclass("quina")
MegaSenaInteligente = pool_subclass("megasena")
LotomaniaInteligente = pool_subclass("lotomania", modo_analise="hibrido")
DuplaSenaInteligente = pool_subclass("duplasena")
