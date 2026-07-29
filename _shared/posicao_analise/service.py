# -*- coding: utf-8 -*-
"""Camada de dados — Análise por Posição (multi-modalidade)."""
from __future__ import annotations

import importlib
from typing import Any, Dict, List, Optional

from sqlalchemy import desc

from models.shared import db

from .core import analisar_concurso_geral, analisar_por_posicao, analise_agregada_posicional
from .gerador import OpcoesGeradorPosicao, carregar_plugins_ctx, gerar_apostas_com_plugins
from .specs import PosicaoSpec, get_posicao_spec


def _load_model(spec: PosicaoSpec):
    from analise_comparar.compare_config import get_compare_config

    try:
        cfg = get_compare_config(spec.key)
    except ValueError:
        cfg = {
            "model_module": f"models.sorteio_{spec.key.replace('diadesorte', 'diadesorte')}",
            "model_class": None,
        }
        if spec.key == "diadesorte":
            cfg = {
                "model_module": "models.sorteio_diadesorte",
                "model_class": "SorteioDiaDeSorte",
            }
        elif spec.key == "lotofacil":
            cfg = {
                "model_module": "models.sorteio_lotofacil",
                "model_class": "SorteioLotofacil",
            }
        elif spec.key == "duplasena":
            cfg = {
                "model_module": "models.sorteio_duplasena",
                "model_class": "SorteiosDuplaSena",
            }

    mod = importlib.import_module(cfg["model_module"])
    cls = getattr(mod, cfg["model_class"])
    return cls


def _extrair_ordem(row: Any, spec: PosicaoSpec, sorteio: int = 1) -> List[int]:
    fields = spec.ordered_fields_for(sorteio)
    return [int(getattr(row, f)) for f in fields]


def _extras_concurso(row: Any, spec: PosicaoSpec) -> Dict[str, Any]:
    extra: Dict[str, Any] = {}
    if spec.extra_mes:
        extra["mes_num"] = getattr(row, "mes_num", None)
        extra["mes_nome"] = getattr(row, "mes_nome", None)
        if hasattr(row, "mes_abrev"):
            extra["mes_abrev"] = row.mes_abrev()
    if spec.extra_time:
        extra["time_num"] = getattr(row, "time_num", None)
        extra["time_nome"] = getattr(row, "time_nome", None) or ""
    if spec.extra_trevo:
        t1 = getattr(row, "t1", None)
        t2 = getattr(row, "t2", None)
        if t1 is not None and t2 is not None:
            extra["trevos"] = sorted([int(t1), int(t2)])
            extra["trevos_fmt"] = [spec.fmt(t) for t in extra["trevos"]]
    return extra


def _extras_aposta(spec: PosicaoSpec, agreg: Dict[str, Any], idx: int) -> Dict[str, Any]:
    extra: Dict[str, Any] = {}
    if spec.extra_mes and spec.key == "diadesorte":
        meses = agreg.get("meses_indicados") or {}
        if meses.get("sucesso") and not meses.get("sem_indicados"):
            try:
                from diadesorte.meses_indicados import extra_mes_ciclo

                extra.update(extra_mes_ciclo(meses, idx))
            except Exception:
                pass
    if spec.extra_time:
        ult = agreg.get("ultimo_time") or {}
        if ult.get("time_num"):
            extra["time_num"] = ult["time_num"]
            extra["time_nome"] = ult.get("time_nome") or ""
    if spec.extra_trevo:
        trevos = agreg.get("trevos_sugeridos") or []
        if trevos:
            par = trevos[idx % len(trevos)]
            extra["trevos"] = par
            extra["trevos_fmt"] = [spec.fmt(t) for t in par]
    return extra


class AnalisePosicaoService:
    """Serviço genérico — instanciado via make_service(modality_key)."""

    modality_key: str = ""
    spec: PosicaoSpec

    @classmethod
    def _model_cls(cls):
        return _load_model(cls.spec)

    @classmethod
    def listar_concursos(
        cls,
        limit: Optional[int] = None,
        sorteio: int = 1,
    ) -> List[Dict[str, Any]]:
        Model = cls._model_cls()
        q = db.session.query(Model).order_by(desc(Model.concurso))
        if limit is not None and limit > 0:
            q = q.limit(int(limit))
        rows = q.all()
        out: List[Dict[str, Any]] = []
        n = cls.spec.num_posicoes
        for s in rows:
            ordem = _extrair_ordem(s, cls.spec, sorteio=sorteio)
            item: Dict[str, Any] = {
                "concurso": s.concurso,
                "data": s.data,
                "dezenas_ordem": ordem,
                "dezenas_ordem_fmt": [cls.spec.fmt(d) for d in ordem],
                **(_extras_concurso(s, cls.spec)),
            }
            if len(ordem) >= n and cls.spec.show_dig_soma:
                geral = analisar_concurso_geral(ordem, cls.spec)
                item["resumo_dig_soma"] = geral["resumo_dig_soma"]
                item["qtd_digitos_distintos"] = geral["qtd_digitos_distintos"]
                item["soma_dezenas"] = geral["soma_dezenas"]
            out.append(item)
        return out

    @classmethod
    def analisar_concurso(cls, concurso: int, sorteio: int = 1) -> Optional[Dict[str, Any]]:
        Model = cls._model_cls()
        sorteio_row = db.session.get(Model, int(concurso))
        if not sorteio_row:
            return None

        ordem = _extrair_ordem(sorteio_row, cls.spec, sorteio=sorteio)
        if len(ordem) < cls.spec.num_posicoes:
            return None

        analise = analisar_por_posicao(ordem, cls.spec)
        return {
            "concurso": sorteio_row.concurso,
            "data": sorteio_row.data,
            "sorteio": int(sorteio) if cls.spec.duplasena else None,
            **(_extras_concurso(sorteio_row, cls.spec)),
            **analise,
        }

    @classmethod
    def analise_agregada(cls, janela: int = 50, sorteio: int = 1) -> Dict[str, Any]:
        janela = max(5, min(int(janela), 500))
        Model = cls._model_cls()
        rows = (
            db.session.query(Model)
            .order_by(desc(Model.concurso))
            .limit(janela)
            .all()
        )
        historico = [_extrair_ordem(s, cls.spec, sorteio=sorteio) for s in rows]
        agreg = analise_agregada_posicional(historico, cls.spec, janela=janela)
        ultimo = rows[0] if rows else None

        meses: Dict[str, Any] = {}
        if cls.spec.extra_mes and cls.spec.key == "diadesorte":
            try:
                from diadesorte.meses_indicados import carregar_meses_indicados

                meses = carregar_meses_indicados(Model, janela=10)
            except Exception:
                meses = {}

        ultimo_time: Dict[str, Any] = {}
        if cls.spec.extra_time and ultimo:
            ultimo_time = {
                "time_num": getattr(ultimo, "time_num", None),
                "time_nome": getattr(ultimo, "time_nome", None) or "",
            }

        trevos_sugeridos: List[List[int]] = []
        if cls.spec.extra_trevo and rows:
            from collections import Counter

            pares: Counter[tuple] = Counter()
            for s in rows[:30]:
                t1, t2 = int(s.t1), int(s.t2)
                pares[tuple(sorted([t1, t2]))] += 1
            trevos_sugeridos = [list(p) for p, _ in pares.most_common(6)]
            if not trevos_sugeridos:
                trevos_sugeridos = [[1, 2]]

        plugins_resumo: Dict[str, Any] = {}
        try:
            op_preview = OpcoesGeradorPosicao(preset="integrado", janela=janela, sorteio=sorteio).normalizar()
            ctx = carregar_plugins_ctx(op_preview, cls.modality_key, cls.spec)
            rep = ctx.get("repeticao") or {}
            pos = ((rep.get("resumo_ultimo_par") or {}).get("posicional") or {})
            plugins_resumo = {
                "repeticao_ultimo_par_posicional": pos.get("quantidade"),
                "sniper_fortes": list(ctx.get("sniper_fortes") or [])[:5],
                "comportamento_alvos": (ctx.get("comp_alvos") or {}),
            }
        except Exception:
            plugins_resumo = {}

        return {
            "sucesso": True,
            "janela": janela,
            "sorteio": int(sorteio) if cls.spec.duplasena else None,
            "ultimo_concurso": ultimo.concurso if ultimo else None,
            "ultimo_data": ultimo.data if ultimo else None,
            "meses_indicados": meses,
            "ultimo_time": ultimo_time,
            "trevos_sugeridos": trevos_sugeridos,
            "plugins_resumo": plugins_resumo,
            "pos_cfg": cls.spec.to_ui(),
            **(_extras_concurso(ultimo, cls.spec) if ultimo else {}),
            **agreg,
        }

    @classmethod
    def gerar_apostas(
        cls,
        quantidade: int = 10,
        perfil: str = "equilibrado",
        janela: int = 50,
        filtrar_dig_soma: bool = False,
        preset: str = "manual",
        usar_repeticao: bool = False,
        usar_sniper: bool = False,
        usar_comportamento: bool = False,
        modo_comportamento: str = "relaxar",
        sorteio: int = 1,
    ) -> Dict[str, Any]:
        janela = max(5, min(int(janela), 500))
        qtd = max(1, min(int(quantidade), 100))
        opcoes = OpcoesGeradorPosicao(
            perfil=perfil,
            janela=janela,
            filtrar_dig_soma=filtrar_dig_soma,
            preset=preset,
            usar_repeticao=usar_repeticao,
            usar_sniper=usar_sniper,
            usar_comportamento=usar_comportamento,
            modo_comportamento=modo_comportamento,
            sorteio=sorteio,
        ).normalizar()

        agreg = cls.analise_agregada(janela=janela, sorteio=sorteio)
        pos_stats = agreg.get("posicoes") or []
        if not pos_stats:
            return {"sucesso": False, "erro": "Histórico insuficiente para gerar apostas."}

        alvo: Optional[tuple[int, int]] = None
        if opcoes.filtrar_dig_soma and cls.spec.show_dig_soma:
            if agreg.get("ultimo_qtd_digitos") is not None and agreg.get("ultimo_soma") is not None:
                alvo = (int(agreg["ultimo_qtd_digitos"]), int(agreg["ultimo_soma"]))

        plugins_ctx = carregar_plugins_ctx(opcoes, cls.modality_key, cls.spec)
        apostas_raw = gerar_apostas_com_plugins(
            pos_stats,
            cls.spec,
            cls.modality_key,
            quantidade=qtd,
            opcoes=opcoes,
            alvo_dig_soma=alvo,
            plugins_ctx=plugins_ctx,
        )

        apostas: List[Dict[str, Any]] = []
        for i, ap in enumerate(apostas_raw):
            item = dict(ap)
            item.update(_extras_aposta(cls.spec, agreg, i))
            apostas.append(item)

        out = {
            "sucesso": True,
            "quantidade": len(apostas),
            "perfil": opcoes.perfil,
            "janela": janela,
            "sorteio": int(sorteio) if cls.spec.duplasena else None,
            "preset": opcoes.preset,
            "plugins": {
                "repeticao": opcoes.usar_repeticao,
                "sniper": opcoes.usar_sniper,
                "comportamento": opcoes.usar_comportamento,
                "modo_comportamento": opcoes.modo_comportamento,
            },
            "filtrar_dig_soma": opcoes.filtrar_dig_soma,
            "alvo_dig_soma": f"{alvo[0]}/{alvo[1]}" if alvo else None,
            "ultimo_resumo_dig_soma": agreg.get("ultimo_resumo_dig_soma"),
            "pos_cfg": cls.spec.to_ui(),
            "apostas": apostas,
        }
        try:
            from geradores_elite.validacao.validador_global import ValidadorGeradoresElite
            # Preferir dezenas_ordem; fallback dezenas no extrator
            out = ValidadorGeradoresElite.aplicar(
                out,
                origem="analise_posicao",
                modality_key=cls.modality_key,
                campo="apostas",
                campo_dezenas="dezenas_ordem",
            )
        except Exception:
            pass
        return out
