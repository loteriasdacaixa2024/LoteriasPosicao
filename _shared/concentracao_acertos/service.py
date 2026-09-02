# -*- coding: utf-8 -*-
"""Serviço — Concentração de Acertos (acesso ao banco)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc

from models.shared import db

from .core import (
    backtest_conjunto,
    backtest_conjunto_posicional,
    comparar_estrategias,
    estrategia_cfg,
    gerar_apostas,
    gerar_apostas_supersete,
    pool_sugerido,
    validar_criterios,
)
from .specs import get_concentracao_config


class ConcentracaoAcertosService:
    def __init__(self, modality_key: str):
        from .specs import tem_concentracao_acertos

        if not tem_concentracao_acertos(modality_key):
            raise ValueError(f"Modalidade não suportada: {modality_key}")
        self.modality_key = modality_key
        self.cfg = get_concentracao_config(modality_key)

    def _model(self):
        import importlib

        mod = importlib.import_module(self.cfg["model_module"])
        return getattr(mod, self.cfg["model_class"])

    def _analise_geral(self) -> Optional[Dict[str, Any]]:
        import importlib

        try:
            mod = importlib.import_module(self.cfg["analise_module"])
            cls = getattr(mod, self.cfg["analise_class"])
            if not hasattr(cls, "analise_geral"):
                return None
            return cls.analise_geral()
        except Exception:
            return None

    def _normalizar_limite(self, limite: int) -> Optional[int]:
        """Retorna None para analisar todos os concursos do banco."""
        try:
            v = int(limite)
        except (TypeError, ValueError):
            v = 50
        if v <= 0:
            return None
        return max(10, v)

    def total_concursos_banco(self) -> int:
        ag = self._analise_geral() or {}
        return int(ag.get("total_sorteios") or 0)

    def carregar_historico(self, limite: int = 50) -> List[Any]:
        lim = self._normalizar_limite(limite)
        Model = self._model()
        q = db.session.query(Model).order_by(desc(Model.concurso))
        if lim is not None:
            q = q.limit(lim)
        return q.all()

    def listar_concursos(self, limite: int = 150) -> List[Dict[str, Any]]:
        rows = self.carregar_historico(limite)
        return [
            {"concurso": r.concurso, "data": r.data or ""}
            for r in rows
        ]

    def _meses_apostas(self, quantidade: int) -> Tuple[List[int], Dict[str, Any]]:
        if not self.cfg.get("extra_mes"):
            return [0] * max(1, int(quantidade or 10)), {}
        from diadesorte.meses_indicados import carregar_meses_indicados, extra_mes_ciclo

        analise = carregar_meses_indicados(self._model())
        meses: List[int] = []
        qtd = max(1, int(quantidade or 10))
        for i in range(qtd):
            ciclo = extra_mes_ciclo(analise, i)
            mn = int(ciclo.get("mes_num") or 0) if ciclo else 0
            meses.append(mn if mn else 0)
        return meses, analise

    def _anexar_meses_apostas(
        self,
        apostas: List[List[int]],
        meses: List[int],
    ) -> List[Dict[str, Any]]:
        if not self.cfg.get("extra_mes"):
            return [{"dezenas": ap} for ap in apostas]
        from geradores_elite.comportamento.specs import MESES_ABREV, MESES_NOME

        out: List[Dict[str, Any]] = []
        for i, ap in enumerate(apostas):
            mn = meses[i] if i < len(meses) else 0
            item: Dict[str, Any] = {"dezenas": ap, "mes_num": mn or None}
            if mn:
                nome = MESES_NOME.get(mn, f"Mês {mn}")
                item.update({
                    "mes": mn,
                    "mes_nome": nome,
                    "mes_abrev": MESES_ABREV.get(mn, str(mn)),
                })
            out.append(item)
        return out

    def _pool_resolvido(
        self,
        estrategia_id: str,
        pool: Optional[List[int]],
        criterio: str,
    ) -> Tuple[List[int], Dict[str, Any]]:
        est = estrategia_cfg(self.modality_key, estrategia_id)
        if pool:
            pool_norm = sorted(set(int(d) for d in pool))
            if len(pool_norm) != est["pool_size"]:
                raise ValueError(
                    f"Pool deve ter exatamente {est['pool_size']} dezenas (recebido {len(pool_norm)})."
                )
            return pool_norm, est
        ag = self._analise_geral() or {}
        dados = ag.get("dados") or []
        return pool_sugerido(
            dados,
            est["pool_size"],
            criterio,
            dezena_min=int(self.cfg["dezena_min"]),
            dezena_max=int(self.cfg["dezena_max"]),
        ), est

    def gerar(
        self,
        estrategia_id: str,
        *,
        pool: Optional[List[int]] = None,
        criterio_pool: str = "freq",
        perfil: str = "equilibrado",
        quantidade: int = 10,
    ) -> Dict[str, Any]:
        pool_ok, est = self._pool_resolvido(estrategia_id, pool, criterio_pool)
        historico = self.carregar_historico(80)

        if self.modality_key == "supersete":
            gen = gerar_apostas_supersete(
                pool_ok,
                quantidade=quantidade,
                seed_salt=estrategia_id,
            )
            if not gen.get("sucesso"):
                return gen
            meses, analise_mes = self._meses_apostas(quantidade)
            bt = backtest_conjunto_posicional(
                gen["apostas"],
                historico[:50],
                max_acertos=7,
                pico_destaque=int(self.cfg.get("pico_min") or 3),
            )
            return {
                "sucesso": True,
                "estrategia": estrategia_id,
                "estrategia_nome": est["nome"],
                "pool": pool_ok,
                "apostas": gen["apostas"],
                "apostas_com_mes": self._anexar_meses_apostas(gen["apostas"], meses),
                "quantidade": gen["quantidade"],
                "distribuicao": gen.get("distribuicao"),
                "aviso": gen.get("aviso"),
                "metricas_preview": bt.get("metricas"),
                "meses_indicados": analise_mes,
                "validacoes": validar_criterios(bt.get("metricas") or {}, self.cfg),
            }

        moda_rows = [list(r.dezenas()) for r in historico]
        from geradores_elite.construtor.construcoes_core import distribuicao_historica_moda

        gen = gerar_apostas(
            pool_ok,
            perfil=perfil,
            quantidade=quantidade,
            comportamento_moda=distribuicao_historica_moda(moda_rows),
            seed_salt=estrategia_id,
            aposta_dezenas=int(self.cfg["aposta_dezenas"]),
        )
        if not gen.get("sucesso"):
            return gen
        meses, analise_mes = self._meses_apostas(quantidade)
        bt = backtest_conjunto(
            gen["apostas"],
            historico[:50],
            meses_apostas=meses if self.cfg.get("extra_mes") else None,
            max_acertos=int(self.cfg["aposta_dezenas"]),
            pico_destaque=int(self.cfg.get("pico_min") or max(2, int(self.cfg["aposta_dezenas"]) - 1)),
        )
        out = {
            "sucesso": True,
            "estrategia": estrategia_id,
            "estrategia_nome": est["nome"],
            "pool": pool_ok,
            "apostas": gen["apostas"],
            "apostas_com_mes": self._anexar_meses_apostas(gen["apostas"], meses),
            "quantidade": gen["quantidade"],
            "distribuicao": gen.get("distribuicao"),
            "aviso": gen.get("aviso"),
            "metricas_preview": bt.get("metricas"),
            "meses_indicados": analise_mes,
        }
        try:
            from geradores_elite.validacao.validador_global import ValidadorGeradoresElite
            filtrado = ValidadorGeradoresElite.aplicar_em_listas(
                {
                    "apostas": out["apostas"],
                    "apostas_com_mes": out["apostas_com_mes"],
                },
                origem="concentracao_acertos",
                modality_key=self.modality_key,
                campo_dezenas="dezenas",
            )
            out["apostas"] = filtrado["listas"]["apostas"]
            out["apostas_com_mes"] = filtrado["listas"]["apostas_com_mes"]
            out["quantidade"] = len(out["apostas"])
            out["validacao_global"] = filtrado.get("stats")
            if out["quantidade"] == 0:
                rej = (filtrado.get("stats") or {}).get("rejeitadas") or 0
                return {
                    "sucesso": False,
                    "erro": (
                        f"Nenhuma aposta válida após validação global "
                        f"({rej} rejeitada(s)). Aumente a quantidade ou ajuste o pool."
                    ),
                    "validacao_global": filtrado.get("stats"),
                    "pool": pool_ok,
                    "estrategia": estrategia_id,
                }
            if filtrado.get("stats", {}).get("rejeitadas"):
                extra = (
                    f"Validação global: {filtrado['stats']['rejeitadas']} rejeitada(s) "
                    f"de {filtrado['stats']['analisadas']}."
                )
                out["aviso"] = f"{out['aviso']} {extra}".strip() if out.get("aviso") else extra
        except Exception:
            pass
        return out

    def executar_backtest(
        self,
        estrategia_id: str,
        *,
        pool: Optional[List[int]] = None,
        criterio_pool: str = "freq",
        perfil: str = "equilibrado",
        limite: int = 50,
        quantidade: int = 10,
    ) -> Dict[str, Any]:
        pool_ok, est = self._pool_resolvido(estrategia_id, pool, criterio_pool)
        historico = self.carregar_historico(limite)

        if self.modality_key == "supersete":
            gen = gerar_apostas_supersete(
                pool_ok,
                quantidade=quantidade,
                seed_salt=estrategia_id,
            )
            if not gen.get("sucesso"):
                return gen
            meses, analise_mes = self._meses_apostas(quantidade)
            bt = backtest_conjunto_posicional(
                gen["apostas"],
                historico,
                max_acertos=7,
                pico_destaque=int(self.cfg.get("pico_min") or 3),
            )
            if not bt.get("sucesso"):
                return bt
            metricas = bt.get("metricas") or {}
            return {
                "sucesso": True,
                "estrategia": estrategia_id,
                "estrategia_nome": est["nome"],
                "pool": pool_ok,
                "apostas": gen["apostas"],
                "apostas_com_mes": self._anexar_meses_apostas(gen["apostas"], meses),
                "limite": len(historico),
                "meses_indicados": analise_mes,
                **bt,
                "validacoes": validar_criterios(metricas, self.cfg),
            }

        moda_rows = [list(r.dezenas()) for r in self.carregar_historico(80)]
        from geradores_elite.construtor.construcoes_core import distribuicao_historica_moda

        gen = gerar_apostas(
            pool_ok,
            perfil=perfil,
            quantidade=quantidade,
            comportamento_moda=distribuicao_historica_moda(moda_rows),
            seed_salt=estrategia_id,
            aposta_dezenas=int(self.cfg["aposta_dezenas"]),
        )
        if not gen.get("sucesso"):
            return gen
        meses, analise_mes = self._meses_apostas(quantidade)
        bt = backtest_conjunto(
            gen["apostas"],
            historico,
            meses_apostas=meses if self.cfg.get("extra_mes") else None,
            max_acertos=int(self.cfg["aposta_dezenas"]),
            pico_destaque=int(self.cfg.get("pico_min") or max(2, int(self.cfg["aposta_dezenas"]) - 1)),
        )
        if not bt.get("sucesso"):
            return bt
        metricas = bt.get("metricas") or {}
        return {
            "sucesso": True,
            "estrategia": estrategia_id,
            "estrategia_nome": est["nome"],
            "pool": pool_ok,
            "apostas": gen["apostas"],
            "apostas_com_mes": self._anexar_meses_apostas(gen["apostas"], meses),
            "limite": len(historico),
            "meses_indicados": analise_mes,
            **bt,
            "validacoes": validar_criterios(metricas, self.cfg),
        }

    def indice_atual(
        self,
        estrategia_id: str,
        *,
        pool: Optional[List[int]] = None,
        criterio_pool: str = "freq",
        perfil: str = "equilibrado",
        limite: int = 50,
    ) -> Dict[str, Any]:
        res = self.executar_backtest(
            estrategia_id,
            pool=pool,
            criterio_pool=criterio_pool,
            perfil=perfil,
            limite=limite,
        )
        if not res.get("sucesso"):
            return res
        return {
            "sucesso": True,
            "estrategia": estrategia_id,
            "pool": res.get("pool"),
            "metricas": res.get("metricas"),
            "validacoes": res.get("validacoes"),
        }

    def comparar(
        self,
        *,
        criterio_pool: str = "freq",
        perfil: str = "equilibrado",
        limite: int = 50,
    ) -> Dict[str, Any]:
        ag = self._analise_geral() or {}
        historico = self.carregar_historico(limite)
        moda_src = [list(r.dezenas()) for r in self.carregar_historico(80)]
        meses, analise_mes = self._meses_apostas(10)
        res = comparar_estrategias(
            self.modality_key,
            ag.get("dados") or [],
            historico,
            criterio_pool=criterio_pool,
            perfil=perfil,
            sorteios_moda=moda_src,
            meses_apostas=meses,
        )
        res["meses_indicados"] = analise_mes
        return res

    def status_modulo(self) -> Dict[str, Any]:
        ag = self._analise_geral()
        total = int((ag or {}).get("total_sorteios") or 0)
        return {
            "fase": "beta" if total > 0 else "estrutura",
            "mensagem": (
                "Backtest, índice de concentração e comparação A/B/C ativos."
                if total > 0
                else "Aguardando histórico de sorteios no banco."
            ),
            "total_sorteios": total,
        }
