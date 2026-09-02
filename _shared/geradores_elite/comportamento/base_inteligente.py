# -*- coding: utf-8 -*-
"""Adaptador UI/API — Comportamento → Apostas."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Type

from geradores_elite.comportamento.base_service import ComportamentoBaseService
from geradores_elite.comportamento.specs import ComportamentoSpec
from geradores_elite.inteligente.helpers import labels_regras_auto


class ComportamentoBaseInteligente:
    modality_key: str = ""
    motor: str = ""

    @classmethod
    def _svc(cls) -> Type[ComportamentoBaseService]:
        raise NotImplementedError

    @classmethod
    def _spec(cls) -> ComportamentoSpec:
        return cls._svc().SPEC

    @classmethod
    def _indicadores(cls) -> Tuple[str, ...]:
        return cls._spec().indicadores

    @classmethod
    def montar_contexto(
        cls,
        janela: int = 10,
        filtros: Optional[Dict[str, int]] = None,
        base_estatistica: str = "geral",
    ) -> Dict[str, Any]:
        return cls._svc().analisar(
            janela=janela, filtros=filtros, base_estatistica=base_estatistica,
        )

    @classmethod
    def painel_evidencias(cls, ctx: Dict[str, Any]) -> Dict[str, Any]:
        sp = cls._spec()
        resumo = ctx.get("resumo") or {}
        ultimo = ctx.get("ultimo_indicadores") or {}
        total = int(ctx.get("total_janela") or 0)
        alvos = (ctx.get("criterios_sugeridos") or {}).get("alvos") or {}

        indicadores_box = []
        for cod in sp.indicadores:
            r = resumo.get(cod) or {}
            indicadores_box.append({
                "codigo": cod,
                "label": sp.indicador_labels[cod],
                "moda": r.get("moda"),
                "moda_pct": r.get("moda_pct", 0),
                "media": r.get("media"),
                "ultimo": ultimo.get(cod),
                "alvo": alvos.get(cod),
                "distribuicao": r.get("distribuicao") or {},
            })

        return {
            "total_concursos": int(ctx.get("total_concursos") or 0),
            "total_concursos_base": int(ctx.get("total_concursos_base") or ctx.get("total_concursos") or 0),
            "total_concursos_geral": int(ctx.get("total_concursos_geral") or ctx.get("total_concursos") or 0),
            "base_estatistica": ctx.get("base_estatistica", "geral"),
            "base_label": ctx.get("base_label", "Geral"),
            "meta_bases": ctx.get("meta_bases") or {},
            "aviso_base": ctx.get("aviso_base"),
            "total_janela": total,
            "janela": ctx.get("janela"),
            "janela_label": ctx.get("janela_label"),
            "indicadores": indicadores_box,
            "ultimo_concurso": ctx.get("ultimo_concurso"),
            "filtros_ativos": ctx.get("filtros_ativos") or {},
            "linhas_filtradas_count": ctx.get("linhas_filtradas_count", total),
        }

    @classmethod
    def regras_automaticas(cls, evidencias: Dict[str, Any]) -> Dict[str, Any]:
        sp = cls._spec()
        indicadores = evidencias.get("indicadores") or []
        regras: Dict[str, Any] = {"janela": evidencias.get("janela", 10)}
        for item in indicadores:
            cod = item["codigo"]
            moda_pct = float(item.get("moda_pct") or 0)
            ult = item.get("ultimo")
            moda = item.get("moda")
            usar = moda_pct >= 18 or (ult is not None and ult == moda)
            regras[f"usar_{cod}"] = usar
            regras[f"alvo_{cod}"] = moda
        if not any(regras.get(f"usar_{c}") for c in sp.indicadores):
            for cod in sp.regras_fallback:
                regras[f"usar_{cod}"] = True
        return regras

    @classmethod
    def _labels_motor(cls, modo_motor: str, perfis: int) -> List[str]:
        ind_txt = " · ".join(cls._indicadores())
        if modo_motor == "perfil_sorteio":
            return [
                f"Perfil real da tabela ({perfis} sorteios — último concurso ignorado)",
                f"Cada aposta reproduz {ind_txt} de um concurso real (penúltimo em diante)",
                "Rotaciona: 1ª aposta → penúltimo, 2ª → antepenúltimo, …",
            ]
        if modo_motor == "hibrido":
            return [
                f"Alternado: perfil real + moda ({perfis} perfis, sem o último concurso)",
                "Apostas ímpares: comportamento de um concurso da tabela (a partir do penúltimo)",
                "Apostas pares: resumo (moda) dos concursos usados na geração",
            ]
        return ["Resumo (moda): valores mais frequentes na janela"]

    @classmethod
    def _labels_auto(cls, regras: Dict[str, Any]) -> List[str]:
        sp = cls._spec()
        extras = []
        for cod in sp.indicadores:
            if regras.get(f"usar_{cod}"):
                alvo = regras.get(f"alvo_{cod}")
                extras.append((f"usar_{cod}", f"{sp.indicador_labels[cod]} → {alvo}"))
        return labels_regras_auto(regras, extras)

    @classmethod
    def _analisar_aposta(
        cls,
        aposta: Dict[str, Any],
        regras: Dict[str, Any],
    ) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
        sp = cls._spec()
        comp = aposta.get("comportamento") or {}
        alvos = aposta.get("alvos_aposta") or {}
        perfil_ref = aposta.get("perfil_referencia")
        motor = aposta.get("modo_motor_aposta", "moda")
        criterios: List[Dict[str, str]] = []

        if perfil_ref and motor == "perfil_sorteio":
            criterios.append({
                "codigo": "perfil_ref",
                "texto": f"Perfil real da tabela: {perfil_ref.get('texto_curto', '')}",
            })
        elif motor == "panorama_top":
            meta = aposta.get("alvos_panorama_meta") or {}
            base_lbl = aposta.get("panorama_base_label") or "Panorama"
            rank_lbl = aposta.get("rank_escolhido_label") or ""
            criterios.append({
                "codigo": "panorama",
                "texto": f"Panorama — {base_lbl}" + (f" · {rank_lbl}" if rank_lbl else ""),
            })
        elif motor == "moda":
            origem_dna = regras.get("_origem") == "resumo_geral"
            criterios.append({
                "codigo": "moda",
                "texto": "Resumo geral da modalidade"
                if origem_dna else
                "Perfil sintético: moda da janela selecionada",
            })

        ativos = list(sp.indicadores) if motor == "perfil_sorteio" else [
            c for c in sp.indicadores if regras.get(f"usar_{c}")
        ]
        if not ativos:
            ativos = list(sp.indicadores)

        for cod in ativos:
            alvo = alvos.get(cod, comp.get(cod))
            atual = comp.get(cod, 0)
            ok = "✓" if atual == alvo else "~"
            extra = ""
            if motor == "panorama_top":
                pm = (aposta.get("alvos_panorama_meta") or {}).get(cod) or {}
                rank_linha = pm.get("rank_linha") or aposta.get("rank_escolhido")
                if rank_linha:
                    extra = f" ({rank_linha}º ranking)"
                elif pm.get("ranking"):
                    extra = f" (rank {pm['ranking']} no panorama)"
            criterios.append({
                "codigo": cod.lower(),
                "texto": f"{ok} {sp.indicador_labels[cod]}: {atual} (alvo {alvo}){extra}",
            })
        if sp.has_mes and aposta.get("mes_nome"):
            criterios.append({
                "codigo": "mes",
                "texto": f"Mês da sorte: {aposta.get('mes_nome')}",
            })
        if sp.has_time and aposta.get("time_num"):
            criterios.append({
                "codigo": "time",
                "texto": f"Time: #{aposta.get('time_num')}",
            })
        if sp.has_trevos and aposta.get("trevos"):
            criterios.append({
                "codigo": "trevos",
                "texto": f"Trevos: {aposta.get('trevos')}",
            })
        extras = regras.get("_dna_extras") or {}
        if extras:
            dz = aposta.get("dezenas") or []
            sm = sum(int(x) for x in dz)
            lo, hi = extras.get("soma_min"), extras.get("soma_max")
            if lo or hi:
                criterios.append({
                    "codigo": "dna_soma",
                    "texto": f"Soma {sm} (faixa {lo}–{hi})",
                })
            if extras.get("exige_sequencia"):
                criterios.append({
                    "codigo": "dna_seq",
                    "texto": "≥1 sequência consecutiva",
                })
            if extras.get("exige_final_repetido"):
                criterios.append({
                    "codigo": "dna_fin",
                    "texto": "≥1 final repetido",
                })
            if extras.get("bma_2a3"):
                criterios.append({
                    "codigo": "dna_bma",
                    "texto": "2–3 dezenas em cada faixa B / M / A",
                })
        return criterios, {"comportamento": comp}

    @classmethod
    def gerar(
        cls,
        quantidade: int,
        perfil: str,
        modo_geracao: str,
        dezenas_por_jogo: Optional[int] = None,
        janela: int = 10,
        modo_motor: str = "perfil_sorteio",
        regras_manuais: Optional[Dict[str, Any]] = None,
        filtros: Optional[Dict[str, int]] = None,
        base_estatistica: str = "geral",
    ) -> Dict[str, Any]:
        sp = cls._spec()
        if modo_geracao == "resumo_geral":
            from resumo_modalidade.gerador import gerar_apostas_dna
            raw = gerar_apostas_dna(
                cls.modality_key,
                quantidade=quantidade,
                dezenas_por_jogo=dezenas_por_jogo or sp.dezenas_default,
            )
            if not raw.get("sucesso"):
                return raw
            apostas_out = list(raw.get("apostas") or [])
            svc = cls._svc()
            if svc._usa_meses_indicados():
                ms = svc._meses_indicados_analise()
                for i, a in enumerate(apostas_out):
                    svc._aplicar_mes_indicado_aposta(a, i, ms)
            out = {
                "sucesso": True,
                "apostas": apostas_out,
                "total_geradas": len(apostas_out),
                "solicitados": quantidade,
                "aviso": raw.get("aviso"),
                "modo_geracao": "resumo_geral",
                "modo_motor": "resumo_geral",
                "modo_motor_label": raw.get("modo_motor_label") or "Resumo Geral da Modalidade",
                "evidencias": {},
                "regras_aplicadas": raw.get("regras_aplicadas") or {},
                "criterios_modo_auto": raw.get("criterios_modo_auto") or raw.get("criterios_dna") or [],
                "alvos": {},
                "descartadas_historico": raw.get("descartadas_historico", 0),
                "validacao_ineditas": True,
                "base_estatistica": base_estatistica,
                "motor": cls.motor,
                "modality": cls.modality_key,
                "criterios_dna": raw.get("criterios_dna") or [],
                "nota": raw.get("nota"),
                "nucleo_txt": raw.get("nucleo_txt"),
            }
            try:
                from geradores_elite.validacao.validador_global import ValidadorGeradoresElite
                out = ValidadorGeradoresElite.aplicar(
                    out, origem="comportamento_apostas", modality_key=cls.modality_key, campo="apostas",
                )
            except Exception:
                pass
            return out

        ctx = cls.montar_contexto(
            janela=janela, filtros=filtros, base_estatistica=base_estatistica,
        )
        if not ctx.get("sucesso"):
            return ctx

        evidencias = cls.painel_evidencias(ctx)
        if modo_geracao == "automatico":
            regras = cls.regras_automaticas(evidencias)
            regras["janela"] = janela
            criterios_auto = cls._labels_auto(regras)
        else:
            regras = dict(regras_manuais or {})
            regras["janela"] = janela
            criterios_auto = []

        raw = cls._svc().gerar_apostas(
            quantidade=quantidade,
            dezenas_por_jogo=dezenas_por_jogo or sp.dezenas_default,
            janela=janela,
            perfil=perfil,
            modo_geracao=modo_geracao,
            modo_motor=modo_motor,
            regras_manuais=regras,
            filtros=filtros,
            analise=ctx,
            base_estatistica=base_estatistica,
        )
        if not raw.get("sucesso"):
            return raw

        if modo_geracao == "automatico":
            regras = raw.get("regras_aplicadas") or regras

        apostas_out = []
        for a in raw.get("apostas") or []:
            crit, marcas = cls._analisar_aposta(a, regras)
            apostas_out.append({**a, "criterios": crit, "marcas": marcas})

        criterios_auto = cls._labels_motor(modo_motor, raw.get("perfis_disponiveis", 0))

        out = {
            "sucesso": True,
            "apostas": apostas_out,
            "total_geradas": len(apostas_out),
            "solicitados": quantidade,
            "aviso": raw.get("aviso"),
            "modo_geracao": modo_geracao,
            "modo_motor": raw.get("modo_motor", modo_motor),
            "modo_motor_label": raw.get("modo_motor_label"),
            "evidencias": evidencias,
            "regras_aplicadas": regras,
            "criterios_modo_auto": criterios_auto,
            "alvos": raw.get("alvos") or {},
            "perfis_disponiveis": raw.get("perfis_disponiveis", 0),
            "descartadas_historico": raw.get("descartadas_historico", 0),
            "validacao_ineditas": raw.get("validacao_ineditas", True),
            "excluiu_ultimo_concurso": raw.get("excluiu_ultimo_concurso", False),
            "ultimo_concurso_ignorado": raw.get("ultimo_concurso_ignorado"),
            "base_estatistica": ctx.get("base_estatistica", base_estatistica),
            "base_label": ctx.get("base_label"),
            "motor": cls.motor,
            "modality": cls.modality_key,
            "analise": ctx,
        }
        try:
            from geradores_elite.validacao.validador_global import ValidadorGeradoresElite
            out = ValidadorGeradoresElite.aplicar(
                out, origem="comportamento_apostas", modality_key=cls.modality_key, campo="apostas",
            )
        except Exception:
            pass
        return out

    @classmethod
    def gerar_linhas(
        cls,
        quantidade: int = 10,
        dezenas_por_jogo: Optional[int] = None,
        janela: int = 0,
        base_estatistica: str = "geral",
        top_n: int = 3,
        linhas_ids: Optional[List[str]] = None,
        modo_peso: str = "frequencia",
    ) -> Dict[str, Any]:
        """Geração por ranking L1–L10 — reutiliza LinhasUniversoService."""
        raw = cls._svc().gerar_apostas_por_linhas(
            quantidade=quantidade,
            dezenas_por_jogo=dezenas_por_jogo,
            janela=janela,
            base_estatistica=base_estatistica,
            top_n=top_n,
            linhas_ids=linhas_ids,
            modo_peso=modo_peso,
        )
        if not raw.get("sucesso"):
            return raw
        out = {
            **raw,
            "motor": cls.motor,
            "modality": cls.modality_key,
            "criterios_modo_auto": [
                raw.get("modo_motor_label") or "Comportamento das Linhas",
                f"Peso: {raw.get('modo_peso')}",
                "Linhas: " + ", ".join(
                    f"{x.get('linha')}({x.get('posicao')}º)" for x in (raw.get("linhas_usadas") or [])
                ),
            ],
        }
        try:
            from geradores_elite.validacao.validador_global import ValidadorGeradoresElite
            out = ValidadorGeradoresElite.aplicar(
                out, origem="comportamento_linhas", modality_key=cls.modality_key, campo="apostas",
            )
        except Exception:
            pass
        return out

    @classmethod
    def analise_completa_api(
        cls,
        janela: int = 10,
        filtros: Optional[Dict[str, int]] = None,
        base_estatistica: str = "geral",
    ) -> Dict[str, Any]:
        ctx = cls.montar_contexto(
            janela=janela, filtros=filtros, base_estatistica=base_estatistica,
        )
        if not ctx.get("sucesso"):
            return ctx
        ev = cls.painel_evidencias(ctx)
        auto = cls.regras_automaticas(ev)
        perfis = int(ev.get("linhas_filtradas_count") or ev.get("total_janela") or 0)
        return {
            "sucesso": True,
            "evidencias": ev,
            "regras_automaticas": auto,
            "criterios_auto_preview": cls._labels_motor("perfil_sorteio", perfis),
            "analise": ctx,
            "ui": cls.ui_config(),
            "motor": cls.motor,
            "modality": cls.modality_key,
            "base_estatistica": ctx.get("base_estatistica", "geral"),
            "base_label": ctx.get("base_label"),
            "aviso_base": ctx.get("aviso_base"),
        }

    @classmethod
    def analise_comparativo_bases(
        cls,
        janela: int = 10,
        filtros: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        from geradores_elite.comportamento.insights import gerar_insights_comparativo

        analises: Dict[str, Any] = {}
        for base in ("geral", "vencedores", "acumulados"):
            analises[base] = cls.montar_contexto(
                janela=janela, filtros=filtros, base_estatistica=base,
            )
        insights = gerar_insights_comparativo(analises, list(cls._indicadores()))
        return {
            "sucesso": True,
            "janela": janela,
            "analises": {
                b: {
                    "sucesso": analises[b].get("sucesso"),
                    "base_label": analises[b].get("base_label"),
                    "total_concursos_base": analises[b].get("total_concursos_base"),
                    "resumo": analises[b].get("resumo"),
                    "aviso_base": analises[b].get("aviso_base"),
                }
                for b in analises
            },
            "insights": insights,
            "ui": cls.ui_config(),
            "motor": cls.motor,
            "modality": cls.modality_key,
        }

    @classmethod
    def panorama_indicadores_api(
        cls,
        base_estatistica: str = "geral",
    ) -> Dict[str, Any]:
        from geradores_elite.comportamento.panorama_indicadores import calcular_panorama_indicadores

        ctx = cls.montar_contexto(janela=0, base_estatistica=base_estatistica)
        if not ctx.get("sucesso"):
            return ctx

        sp = cls._spec()
        linhas = list(ctx.get("linhas") or [])
        panorama = calcular_panorama_indicadores(
            linhas, sp.indicadores, sp.indicador_labels,
        )
        aviso = ctx.get("aviso_base")
        if panorama.get("aviso_mes"):
            aviso = f"{aviso} {panorama['aviso_mes']}" if aviso else panorama["aviso_mes"]
        return {
            "sucesso": True,
            "base_estatistica": ctx.get("base_estatistica", base_estatistica),
            "base_label": ctx.get("base_label"),
            "total_concursos_base": ctx.get("total_concursos_base"),
            "aviso_base": aviso,
            "panorama": panorama,
            "ui": cls.ui_config(),
            "motor": cls.motor,
            "modality": cls.modality_key,
        }

    @classmethod
    def gerar_panorama_top(
        cls,
        quantidade: int,
        perfil: str,
        dezenas_por_jogo: Optional[int] = None,
        base_estatistica: str = "geral",
        rank_escolhido: int = 1,
        pool_dezenas: Optional[List[int]] = None,
        modo_validacao: str = "estrito",
        modo_panorama: str = "automatico",
        dezenas_manuais: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        sp = cls._spec()
        ctx = cls.montar_contexto(janela=0, base_estatistica=base_estatistica)
        if not ctx.get("sucesso"):
            return ctx

        modo_pan = (modo_panorama or "automatico").strip().lower()

        if modo_pan == "guiado" and dezenas_manuais:
            val = cls._svc().validar_selecao_panorama_api(
                dezenas=dezenas_manuais,
                base_estatistica=base_estatistica,
                rank_escolhido=rank_escolhido,
                modo=modo_validacao,
                dezenas_por_jogo=dezenas_por_jogo,
                analise=ctx,
            )
            if not val.get("valido"):
                return {
                    "sucesso": False,
                    "erro": val.get("motivo") or "Seleção não atende aos alvos do rank.",
                    "validacao": val,
                }
            k = len(val["dezenas"])
            ind = val.get("indicadores") or {}
            ult_info = cls._svc().ultimo_sorteio_info()
            ult_dz = ult_info.get("dezenas") or []
            fmt = (lambda n: f"{n:02d}") if sp.dezena_min == 0 else (lambda n: f"{n:02d}")
            aposta_item: Dict[str, Any] = {
                "numero": 1,
                "dezenas": val["dezenas"],
                "quantidade": k,
                "texto": val.get("texto") or " ".join(fmt(n) for n in val["dezenas"]),
                "comportamento": ind,
                "sobreposicao": len(set(val["dezenas"]) & set(ult_dz)),
                "modo_motor_aposta": "panorama_guiado",
                "alvos_aposta": dict(val.get("alvos") or {}),
                "rank_escolhido": rank_escolhido,
                "rank_escolhido_label": val.get("rank_escolhido_label"),
                "validacao_panorama": val,
            }
            mes_alvo = val.get("mes_alvo")
            if sp.has_mes and mes_alvo:
                aposta_item["mes"] = mes_alvo.get("num")
                aposta_item["mes_nome"] = mes_alvo.get("nome", "")
                aposta_item["mes_abrev"] = mes_alvo.get("abrev", "")
            crit, marcas = cls._analisar_aposta(aposta_item, {"modo": "panorama_guiado"})
            apostas_out = [{**aposta_item, "criterios": crit, "marcas": marcas}]
            base_label = ctx.get("base_label")
            rank_label = val.get("rank_escolhido_label") or f"{rank_escolhido}º ranking"
            return {
                "sucesso": True,
                "apostas": apostas_out,
                "total_geradas": 1,
                "solicitados": 1,
                "modo_geracao": "panorama_guiado",
                "modo_motor": "panorama_guiado",
                "modo_motor_label": f"Panorama guiado — {rank_label}",
                "rank_escolhido": rank_escolhido,
                "rank_escolhido_label": rank_label,
                "base_label": base_label,
                "validacao": val,
            }

        raw = cls._svc().gerar_apostas_panorama_top(
            quantidade=quantidade,
            dezenas_por_jogo=dezenas_por_jogo or sp.dezenas_default,
            perfil=perfil,
            base_estatistica=base_estatistica,
            rank_escolhido=rank_escolhido,
            analise=ctx,
            pool_dezenas=pool_dezenas,
            modo_validacao=modo_validacao,
        )
        if not raw.get("sucesso"):
            return raw

        base_label = ctx.get("base_label") or raw.get("base_label")
        rank_label = raw.get("rank_escolhido_label") or f"{rank_escolhido}º ranking"
        regras = {"modo": "panorama_top", "rank_escolhido": rank_escolhido, "base": base_estatistica}
        apostas_out = []
        for a in raw.get("apostas") or []:
            a2 = {**a, "panorama_base_label": base_label}
            crit, marcas = cls._analisar_aposta(a2, regras)
            apostas_out.append({**a2, "criterios": crit, "marcas": marcas})

        alvos_txt = []
        meta = raw.get("alvos_panorama_meta") or {}
        for cod in cls._indicadores():
            pm = meta.get(cod)
            if pm:
                alvos_txt.append(f"{cod}={pm.get('valor_label')} ({pm.get('percentual')}%)")

        return {
            "sucesso": True,
            "apostas": apostas_out,
            "total_geradas": len(apostas_out),
            "solicitados": quantidade,
            "aviso": raw.get("aviso"),
            "modo_geracao": raw.get("modo_geracao", "panorama_top"),
            "modo_motor": raw.get("modo_motor", "panorama_top"),
            "modo_motor_label": (
                (raw.get("modo_motor_label") or "")
                + (f" · Volante {cls._spec().pool_panorama}" if pool_dezenas else "")
                + (f" · {modo_validacao.capitalize()}" if pool_dezenas and modo_validacao else "")
            ),
            "rank_escolhido": raw.get("rank_escolhido", rank_escolhido),
            "rank_escolhido_label": rank_label,
            "criterios_modo_auto": [
                f"Panorama — {base_label}",
                rank_label,
                f"Alvos: {' · '.join(alvos_txt[:6])}{'…' if len(alvos_txt) > 6 else ''}",
            ],
            "panorama": raw.get("panorama"),
            "alvos_panorama": raw.get("alvos_panorama"),
            "alvos_panorama_meta": raw.get("alvos_panorama_meta"),
            "descartadas_historico": raw.get("descartadas_historico", 0),
            "validacao_ineditas": True,
            "base_estatistica": ctx.get("base_estatistica", base_estatistica),
            "base_label": base_label,
            "motor": cls.motor,
            "modality": cls.modality_key,
            "analise": ctx,
        }

    @classmethod
    def panorama_selecao_contexto_api(
        cls,
        base_estatistica: str = "geral",
        rank_escolhido: int = 1,
    ) -> Dict[str, Any]:
        ctx = cls.montar_contexto(janela=0, base_estatistica=base_estatistica)
        if not ctx.get("sucesso"):
            return ctx
        out = cls._svc().panorama_selecao_contexto(
            base_estatistica=base_estatistica,
            rank_escolhido=rank_escolhido,
            analise=ctx,
        )
        if out.get("sucesso"):
            out["ui"] = cls.ui_config()
        return out

    @classmethod
    def validar_selecao_panorama_api(
        cls,
        dezenas: List[int],
        base_estatistica: str = "geral",
        rank_escolhido: int = 1,
        modo: str = "estrito",
        dezenas_por_jogo: Optional[int] = None,
    ) -> Dict[str, Any]:
        ctx = cls.montar_contexto(janela=0, base_estatistica=base_estatistica)
        if not ctx.get("sucesso"):
            return ctx
        return cls._svc().validar_selecao_panorama_api(
            dezenas=dezenas,
            base_estatistica=base_estatistica,
            rank_escolhido=rank_escolhido,
            modo=modo,
            dezenas_por_jogo=dezenas_por_jogo,
            analise=ctx,
        )

    @classmethod
    def ui_config(cls) -> Dict[str, Any]:
        sp = cls._spec()
        return {
            "layout": "comportamento",
            "show_coluna_rules": False,
            "show_digito_foco": False,
            "show_dezena_foco": False,
            "show_tipo_intrasorte": False,
            "show_extra_mes": sp.has_mes,
            "show_extra_time": sp.has_time,
            "show_extra_trevo": sp.has_trevos,
            "indicadores": list(sp.indicadores),
            "indicador_labels": dict(sp.indicador_labels),
            "janelas": list(sp.janelas_ui),
            "janela_default": sp.janela_default,
            "dezenas_default": sp.dezenas_default,
            "dezenas_min": sp.dezenas_min,
            "dezenas_max": sp.dezenas_max,
            "sorteadas": sp.sorteadas_efetivas(),
            "universo": sp.universo,
            "dezena_min": sp.dezena_min,
            "pool_panorama": sp.pool_panorama,
            "volante_cols": sp.volante_cols,
            "acertos_tiers": list(sp.acertos_tiers()),
            "acertos_min_conferencia": sp.acertos_min_conferencia,
            "motores": [
                {"id": "perfil_sorteio", "label": "Perfil real da tabela"},
                {"id": "hibrido", "label": "Híbrido"},
                {"id": "moda", "label": "Resumo (moda)"},
            ],
            "motor_default": "perfil_sorteio",
            "bases_estatistica": [
                {"id": "geral", "label": "Geral"},
                {"id": "vencedores", "label": "Concursos com Vencedores"},
                {"id": "acumulados", "label": "Concursos Acumulados"},
            ],
            "meta_bases": cls._svc()._meta_bases_dados(),
        }
