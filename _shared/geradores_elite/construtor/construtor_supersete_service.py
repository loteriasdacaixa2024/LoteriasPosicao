# -*- coding: utf-8 -*-
"""Serviço Construtor — Super Sete (posicional C1–C7)."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from geradores_elite.construtor.construcoes_core import QTD_APOSTAS_FIXA, estrategias_ui
from geradores_elite.construtor.construcoes_core_ss import (
    ESTRATEGIAS_SS,
    NUM_COLUNAS,
    calcular_similaridade_ss,
    decode_pool_colunas,
    distribuicao_historica_moda_ss,
    encode_pool_colunas,
    gerar_construcao_ss,
    pool_por_faixa_colunas,
)
from geradores_elite.construtor.construtor_base_service import ConstrutorBaseService
from geradores_elite.construtor.construtor_specs import SUPERSETE_CONSTRUTOR
from geradores_elite.construtor.models import ConstrutorAposta, ConstrutorConstrucao, ConstrutorSessao
from geradores_elite.engine_final_core import formatar_export_txt
from models.shared import db


class ConstrutorSuperSeteService(ConstrutorBaseService):
    SPEC = SUPERSETE_CONSTRUTOR
    _sorteio_model_path = ("models.sorteio_supersete", "SorteioSuperSete")

    @classmethod
    def ui_config(cls) -> Dict[str, Any]:
        sp = cls._spec()
        faixas = {"baixas": "0–3", "medias": "4–6", "altas": "7–9"}
        tiers = sp.acertos_tiers()
        return {
            "modality_key": sp.modality_key,
            "positional": True,
            "num_colunas": sp.num_colunas,
            "max_digitos_por_coluna": sp.max_digitos_por_coluna,
            "qtd_apostas_fixa": QTD_APOSTAS_FIXA,
            "pick_min": sp.pick_min,
            "pick_max": sp.pick_max,
            "pick_default": sp.pick_default,
            "total_dezenas": sp.universo,
            "dezena_min": sp.dezena_min,
            "max_conjunto_base": sp.max_conjunto_base,
            "volante_cols": sp.volante_cols,
            "acertos_por_sorteio": sp.acertos_por_sorteio,
            "acertos_min_relevante": sp.acertos_min_relevante,
            "acertos_max_possivel": sp.acertos_max_possivel,
            "acertos_tiers": list(tiers),
            "estrategias": ESTRATEGIAS_SS,
            "similaridade_min_default": 80,
            "faixas": faixas,
            "faixa_limites": {"baixas": [0, 3], "medias": [4, 6], "altas": [7, 9]},
            "colinha": sp.colinha(),
            "has_mes": False,
            "has_time": False,
            "has_trevos": False,
            "pad_width": sp.dezena_fmt_width,
            "export_is_columns": True,
            "unidade_aposta": "colunas",
            "unidade_label_singular": "coluna",
            "unidade_label_plural": "colunas",
        }

    @classmethod
    def _fmt_digito(cls, n: int) -> str:
        return str(int(n))

    @classmethod
    def _aposta_lista(cls, aposta: ConstrutorAposta) -> List[int]:
        if not aposta.dezenas:
            return []
        return [int(x.strip()) for x in aposta.dezenas.split(",") if x.strip() != ""]

    @classmethod
    def _dezenas_from_sorteio(cls, s: Any) -> List[int]:
        return list(s.digitos())

    @classmethod
    def _parse_pool(cls, data) -> Dict[int, List[int]]:
        sp = cls._spec()
        if isinstance(data, str):
            if data.strip().startswith("{"):
                pool = decode_pool_colunas(data)
            else:
                pool = {c: [] for c in range(1, NUM_COLUNAS + 1)}
        elif isinstance(data, dict):
            pool = {}
            for c in range(1, NUM_COLUNAS + 1):
                raw = data.get(c) or data.get(str(c)) or []
                pool[c] = sorted(set(int(x) for x in raw))
        else:
            pool = {c: [] for c in range(1, NUM_COLUNAS + 1)}
        for col in range(1, NUM_COLUNAS + 1):
            digits = pool.get(col, [])
            for d in digits:
                if d < 0 or d > 9:
                    raise ValueError(f"Dígito {d} inválido na coluna C{col} (use 0–9).")
            if len(digits) > sp.max_digitos_por_coluna:
                raise ValueError(
                    f"Coluna C{col}: máximo {sp.max_digitos_por_coluna} dígitos "
                    f"(selecionados: {len(digits)})."
                )
        return pool

    @classmethod
    def _validar_pool(cls, pool: Dict[int, List[int]]) -> Optional[str]:
        sp = cls._spec()
        total = sum(len(pool.get(c, [])) for c in range(1, NUM_COLUNAS + 1))
        if total > sp.max_conjunto_base:
            return f"Total de dígitos no conjunto-base limitado a {sp.max_conjunto_base}."
        for col in range(1, NUM_COLUNAS + 1):
            if not pool.get(col):
                return f"Coluna C{col} precisa de ao menos 1 dígito."
        return None

    @classmethod
    def _ciclo_service(cls):
        return None

    @classmethod
    def _analise_service(cls):
        from services.analise_supersete_service import AnaliseSuperSeteService
        return AnaliseSuperSeteService

    @classmethod
    def _comportamento_service(cls):
        from services.comportamento_supersete_service import ComportamentoSuperSeteService
        return ComportamentoSuperSeteService

    @classmethod
    def importar_ciclo(cls, tipo: str = "sorteadas") -> Dict[str, Any]:
        return {
            "sucesso": False,
            "erro": "Super Sete não usa ciclo de dezenas. Use importação por coluna (atraso/freq.) ou último sorteio.",
        }

    @classmethod
    def importar_analise(cls, quantidade: int = 5, criterio: str = "atraso") -> Dict[str, Any]:
        sp = cls._spec()
        analise = cls._analise_service().analise_por_coluna()
        if not analise:
            return {"sucesso": False, "erro": "Sem dados de análise por coluna."}
        qtd = max(1, min(int(quantidade), sp.max_digitos_por_coluna))
        pool: Dict[int, List[int]] = {}
        for col in range(1, NUM_COLUNAS + 1):
            col_data = analise.get(col) or analise.get(str(col)) or {}
            if criterio == "frequencia":
                digits = list(col_data.get("rank_freq") or [])[:qtd]
            else:
                digits = list(col_data.get("rank_atraso") or [])[:qtd]
            if not digits:
                digits = list(range(10))[:qtd]
            pool[col] = sorted(set(int(d) for d in digits))
        return {
            "sucesso": True,
            "pool_colunas": pool,
            "conjunto_base": pool,
            "origem": f"analise_colunas_{criterio}",
            "total": sum(len(pool[c]) for c in pool),
        }

    @classmethod
    def importar_ultimo_sorteio_pool(cls) -> Dict[str, Any]:
        ult = cls.obter_ultimo_sorteio()
        if not ult.get("sucesso"):
            return ult
        dz = ult.get("dezenas") or []
        pool = {col: [dz[col - 1]] for col in range(1, NUM_COLUNAS + 1) if col - 1 < len(dz)}
        return {
            "sucesso": True,
            "pool_colunas": pool,
            "conjunto_base": pool,
            "origem": "ultimo_sorteio",
            "concurso": ult.get("concurso"),
        }

    @classmethod
    def comportamento_resumo(cls, janela: int = 10) -> Dict[str, Any]:
        analise = cls._comportamento_service().analisar(janela=janela)
        if not analise.get("sucesso"):
            return analise
        q = db.session.query(cls._model()).order_by(cls._model().concurso.desc())
        if janela > 0:
            sorteios = list(reversed(q.limit(janela).all()))
        else:
            sorteios = db.session.query(cls._model()).order_by(cls._model().concurso.asc()).all()
        hist = [cls._dezenas_from_sorteio(s) for s in sorteios]
        moda_bma = distribuicao_historica_moda_ss(hist)
        resumo = analise.get("resumo") or {}
        return {
            "sucesso": True,
            "janela": janela,
            "moda_bma": moda_bma,
            "criterios_sugeridos": analise.get("criterios_sugeridos") or {},
            "resumo_indicadores": {
                cod: {"moda": info.get("moda"), "moda_pct": info.get("moda_pct")}
                for cod, info in resumo.items()
                if isinstance(info, dict)
            },
        }

    @classmethod
    def salvar_sessao(
        cls,
        nome: str,
        conjunto_base,
        dezenas_por_aposta: int,
        origem_conjunto: str = "manual",
        sessao_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        pool = cls._parse_pool(conjunto_base)
        err = cls._validar_pool(pool)
        if err:
            return {"sucesso": False, "erro": err}
        k = NUM_COLUNAS
        encoded = encode_pool_colunas(pool)
        if sessao_id:
            sessao = db.session.get(ConstrutorSessao, sessao_id)
            if not sessao:
                return {"sucesso": False, "erro": "Sessão não encontrada."}
            sessao.nome = nome.strip() or sessao.nome
            sessao.conjunto_base = encoded
            sessao.dezenas_por_aposta = k
            sessao.origem_conjunto = origem_conjunto
        else:
            sessao = ConstrutorSessao(
                nome=nome.strip() or f"Super Sete {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                conjunto_base=encoded,
                dezenas_por_aposta=k,
                origem_conjunto=origem_conjunto,
            )
            db.session.add(sessao)
        db.session.commit()
        return {"sucesso": True, "sessao": cls._serializar_sessao(sessao, incluir_construcoes=True)}

    @classmethod
    def gerar_construcao(
        cls,
        sessao_id: int,
        estrategia: str,
        *,
        personalizada: Optional[Dict[str, int]] = None,
        janela_comportamento: int = 10,
        similaridade_min_pct: Optional[float] = None,
    ) -> Dict[str, Any]:
        sessao = db.session.get(ConstrutorSessao, sessao_id)
        if not sessao:
            return {"sucesso": False, "erro": "Sessão não encontrada."}
        pool = decode_pool_colunas(sessao.conjunto_base)
        comportamento_moda = None
        if estrategia == "conforme_comportamento":
            comp = cls.comportamento_resumo(janela_comportamento)
            if not comp.get("sucesso"):
                return comp
            comportamento_moda = comp.get("moda_bma")
        anteriores = [[cls._aposta_lista(a) for a in c.apostas] for c in sessao.construcoes]
        sim_min = similaridade_min_pct if similaridade_min_pct is not None else 80.0
        sim_max = 1.0 - (sim_min / 100.0)
        resultado = gerar_construcao_ss(
            pool,
            estrategia,
            personalizada=personalizada,
            comportamento_moda=comportamento_moda,
            construcoes_anteriores=anteriores,
            similaridade_max=sim_max,
        )
        if not resultado.get("sucesso"):
            return resultado
        numero = len(sessao.construcoes) + 1
        params = {
            "personalizada": personalizada,
            "janela_comportamento": janela_comportamento,
            "similaridade_min_pct": sim_min,
            "comportamento_moda": comportamento_moda,
        }
        dist = resultado.get("distribuicao") or {}
        construcao = ConstrutorConstrucao(
            sessao_id=sessao.id,
            numero=numero,
            estrategia=estrategia,
            estrategia_params=json.dumps(params, ensure_ascii=False),
            distribuicao=",".join(f"{dist.get(f, 0)}" for f in ("baixas", "medias", "altas")),
            similaridade_anterior=resultado.get("similaridade_max_anterior"),
            diferenca_pct=resultado.get("diferenca_min_pct"),
        )
        db.session.add(construcao)
        db.session.flush()
        for i, ap in enumerate(resultado["apostas"], start=1):
            db.session.add(ConstrutorAposta(
                construcao_id=construcao.id,
                linha=i,
                dezenas=",".join(cls._fmt_digito(d) for d in ap),
            ))
        db.session.commit()
        return {
            "sucesso": True,
            "construcao": cls._serializar_construcao(construcao),
            "aviso": resultado.get("aviso"),
            "distribuicao": dist,
            "pool_faixas": pool_por_faixa_colunas(pool),
            "matriz_similaridade": cls._matriz_similaridade(sessao),
        }

    @classmethod
    def _matriz_similaridade(cls, sessao: ConstrutorSessao) -> List[Dict[str, Any]]:
        matrix = []
        construcoes = sessao.construcoes
        for i, ca in enumerate(construcoes):
            apostas_a = [cls._aposta_lista(a) for a in ca.apostas]
            for j, cb in enumerate(construcoes):
                if j >= i:
                    continue
                sim = calcular_similaridade_ss(apostas_a, [cls._aposta_lista(a) for a in cb.apostas])
                matrix.append({"de": ca.numero, "para": cb.numero, **sim})
        return matrix

    @classmethod
    def _validar_apostas_edicao(
        cls, pool: Dict[int, List[int]], apostas: List[Dict[str, Any]]
    ) -> Optional[str]:
        if len(apostas) != QTD_APOSTAS_FIXA:
            return f"Cada construção deve ter exatamente {QTD_APOSTAS_FIXA} apostas."
        vistos: set = set()
        for ap in apostas:
            dz = [int(d) for d in (ap.get("dezenas") or [])]
            if len(dz) != NUM_COLUNAS:
                return f"Aposta {ap.get('linha', '?')}: esperado {NUM_COLUNAS} dígitos (C1–C7)."
            for col, d in enumerate(dz, start=1):
                if d < 0 or d > 9:
                    return f"Aposta {ap.get('linha')}: dígito {d} inválido em C{col}."
                if d not in pool.get(col, []):
                    return f"Aposta {ap.get('linha')}: dígito {d} fora do pool da coluna C{col}."
            chave = tuple(dz)
            if chave in vistos:
                return f"Apostas duplicadas (linha {ap.get('linha')})."
            vistos.add(chave)
        return None

    @classmethod
    def atualizar_construcao(
        cls,
        construcao_id: int,
        apostas: List[Dict[str, Any]],
        mes_num: Optional[int] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        construcao = db.session.get(ConstrutorConstrucao, construcao_id)
        if not construcao:
            return {"sucesso": False, "erro": "Construção não encontrada."}
        pool = decode_pool_colunas(construcao.sessao.conjunto_base)
        err = cls._validar_apostas_edicao(pool, apostas)
        if err:
            return {"sucesso": False, "erro": err}
        for ap in construcao.apostas:
            db.session.delete(ap)
        db.session.flush()
        for i, ap in enumerate(sorted(apostas, key=lambda x: int(x.get("linha", 0))), start=1):
            dz = [int(d) for d in ap["dezenas"]]
            db.session.add(ConstrutorAposta(
                construcao_id=construcao.id,
                linha=i,
                dezenas=",".join(cls._fmt_digito(d) for d in dz),
            ))
        db.session.commit()
        return {
            "sucesso": True,
            "construcao": cls._serializar_construcao(construcao),
            "sessao": cls.buscar_sessao(construcao.sessao_id),
        }

    @classmethod
    def exportar_txt(
        cls,
        construcao_id: int,
        mes_num: Optional[int] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        construcao = db.session.get(ConstrutorConstrucao, construcao_id)
        if not construcao:
            return {"sucesso": False, "erro": "Construção não encontrada."}
        apostas = [{"dezenas": cls._aposta_lista(a)} for a in construcao.apostas]
        texto = formatar_export_txt("supersete", apostas, {})
        sessao = construcao.sessao
        nome_arq = f"construcao_{construcao.numero}_{sessao.nome[:30].replace(' ', '_')}.txt"
        return {
            "sucesso": True,
            "texto": texto,
            "nome_arquivo": nome_arq,
            "construcao_numero": construcao.numero,
        }

    @classmethod
    def _contar_acertos(cls, dezenas: List[int], sorteadas: List[int]) -> int:
        # Nunca aceitar set: Super Sete exige ordem e permite repetição.
        if isinstance(sorteadas, set):
            raise TypeError("sorteadas deve ser lista posicional (não set) no Super Sete.")
        if len(dezenas) != len(sorteadas):
            n = min(len(dezenas), len(sorteadas), cls._spec().acertos_max_possivel)
            return sum(1 for i in range(n) if dezenas[i] == sorteadas[i])
        return sum(1 for i in range(len(dezenas)) if dezenas[i] == sorteadas[i])

    @classmethod
    def _acertos_linha_sorteio(cls, dezenas: List[int], sorteio: Any) -> int:
        return cls._contar_acertos(dezenas, cls._dezenas_from_sorteio(sorteio))

    @classmethod
    def conferir_sessao(cls, sessao_id: int, concurso: int) -> Dict[str, Any]:
        sessao = db.session.get(ConstrutorSessao, sessao_id)
        if not sessao:
            return {"sucesso": False, "erro": "Sessão não encontrada."}
        sorteio = db.session.get(cls._model(), concurso)
        if not sorteio:
            return {"sucesso": False, "erro": f"Concurso {concurso} não encontrado."}
        sorteadas = cls._dezenas_from_sorteio(sorteio)
        ranking = []
        for construcao in sessao.construcoes:
            apostas_scores = []
            for aposta in construcao.apostas:
                dz = cls._aposta_lista(aposta)
                acertos = cls._contar_acertos(dz, sorteadas)
                acertadas = [
                    {"coluna": i + 1, "digito": dz[i]}
                    for i in range(min(len(dz), len(sorteadas)))
                    if dz[i] == sorteadas[i]
                ]
                apostas_scores.append({
                    "linha": aposta.linha,
                    "dezenas": dz,
                    "acertos": acertos,
                    "acertadas": acertadas,
                })
            max_acertos = max((a["acertos"] for a in apostas_scores), default=0)
            total_acertos = sum(a["acertos"] for a in apostas_scores)
            media_acertos = round(total_acertos / len(apostas_scores), 2) if apostas_scores else 0
            ranking.append({
                "construcao_numero": construcao.numero,
                "construcao_id": construcao.id,
                "estrategia": construcao.estrategia,
                "estrategia_params": construcao.params_dict(),
                "distribuicao": cls._distribuicao_dict(construcao),
                "max_acertos": max_acertos,
                "total_acertos": total_acertos,
                "media_acertos": media_acertos,
                "apostas": apostas_scores,
            })
        ranking.sort(key=lambda x: (-x["max_acertos"], -x["total_acertos"], -x["media_acertos"]))
        return {
            "sucesso": True,
            "concurso": concurso,
            "data": getattr(sorteio, "data", ""),
            "sorteadas": sorteadas,
            "ranking": ranking,
            "melhor_construcao": ranking[0]["construcao_numero"] if ranking else None,
        }

    @classmethod
    def _serializar_construcao(cls, c: ConstrutorConstrucao) -> Dict[str, Any]:
        out = super()._serializar_construcao(c)
        out["apostas"] = [{"linha": a.linha, "dezenas": cls._aposta_lista(a)} for a in c.apostas]
        out["texto_apostas"] = ["-".join(str(d) for d in cls._aposta_lista(a)) for a in c.apostas]
        return out

    @classmethod
    def analisar_comparativo_sessao(cls, sessao_id: int) -> Dict[str, Any]:
        out = super().analisar_comparativo_sessao(sessao_id)
        if out.get("sucesso") and out.get("analise"):
            sessao = db.session.get(ConstrutorSessao, sessao_id)
            if sessao:
                pool = decode_pool_colunas(sessao.conjunto_base)
                out["analise"]["pool_colunas"] = pool
                out["analise"]["conjunto_base"] = pool
                out["analise"]["total_digitos"] = sum(len(pool[c]) for c in pool)
        return out

    @classmethod
    def _serializar_sessao(cls, s: ConstrutorSessao, incluir_construcoes: bool) -> Dict[str, Any]:
        pool = decode_pool_colunas(s.conjunto_base)
        out = {
            "id": s.id,
            "nome": s.nome,
            "data_criacao": s.data_criacao,
            "conjunto_base": pool,
            "pool_colunas": pool,
            "dezenas_por_aposta": s.dezenas_por_aposta,
            "origem_conjunto": s.origem_conjunto,
            "total_construcoes": len(s.construcoes),
            "pool_faixas": pool_por_faixa_colunas(pool),
            "total_digitos": sum(len(pool[c]) for c in pool),
        }
        if incluir_construcoes:
            out["construcoes"] = [cls._serializar_construcao(c) for c in s.construcoes]
        return out
