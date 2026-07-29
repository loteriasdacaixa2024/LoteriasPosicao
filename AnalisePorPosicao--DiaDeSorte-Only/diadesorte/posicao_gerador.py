# -*- coding: utf-8 -*-
"""Gerador por Posição — plugins Repetição, Sniper e Comportamento."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

from diadesorte.posicao_analise import (
    NUM_POSICOES,
    analisar_concurso_geral,
    formatar_aposta_posicional,
    gerar_apostas_posicionais,
    montar_aposta_posicional,
)


@dataclass
class OpcoesGeradorPosicao:
    perfil: str = "equilibrado"
    janela: int = 50
    filtrar_dig_soma: bool = False
    preset: str = "manual"
    usar_repeticao: bool = False
    usar_sniper: bool = False
    usar_comportamento: bool = False
    modo_comportamento: str = "relaxar"

    def normalizar(self) -> "OpcoesGeradorPosicao":
        if self.preset == "leve":
            self.usar_repeticao = True
            self.usar_sniper = False
            self.usar_comportamento = False
        elif self.preset == "integrado":
            self.usar_repeticao = True
            self.usar_sniper = True
            self.usar_comportamento = True
        if self.modo_comportamento not in ("relaxar", "estrito"):
            self.modo_comportamento = "relaxar"
        if self.perfil not in ("equilibrado", "frequencia", "atraso"):
            self.perfil = "equilibrado"
        return self


def _mapa_dezenas_repeticao(analise: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
    return {int(r["dezena"]): r for r in (analise.get("dezenas") or [])}


def _posicional_ultimo_par(analise: Dict[str, Any]) -> Dict[int, int]:
    out: Dict[int, int] = {}
    pos = (analise.get("resumo_ultimo_par") or {}).get("posicional") or {}
    for item in pos.get("itens") or []:
        p = int(item.get("posicao") or 0)
        d = int(item.get("dezena") or 0)
        if 1 <= p <= NUM_POSICOES and d:
            out[p] = d
    return out


def _fortes_sniper(evidencias: Dict[str, Any]) -> Set[int]:
    out: Set[int] = set()
    for item in (evidencias.get("numeros_fortes") or [])[:5]:
        d = item.get("dezena", item.get("digito"))
        if d is not None:
            out.add(int(d))
    for item in (evidencias.get("colunas_fortes") or [])[:5]:
        d = item.get("coluna", item.get("dezena"))
        if d is not None:
            out.add(int(d))
    return out


def carregar_plugins_ctx(opcoes: OpcoesGeradorPosicao) -> Dict[str, Any]:
    ctx: Dict[str, Any] = {}
    opcoes = opcoes.normalizar()

    if opcoes.usar_repeticao or opcoes.usar_sniper:
        from analise_repeticao.repeticao_service import RepeticaoConcursosService

        rep = RepeticaoConcursosService("diadesorte").analisar_completo(modo="posicional")
        ctx["repeticao"] = rep
        ctx["rep_por_pos"] = _posicional_ultimo_par(rep)
        ctx["rep_dezenas"] = _mapa_dezenas_repeticao(rep)

    if opcoes.usar_sniper:
        from geradores_elite.inteligente import get_inteligente_service

        intel = get_inteligente_service("diadesorte")
        montado = intel.montar_contexto()
        ctx["sniper"] = intel.painel_evidencias(montado)
        ctx["sniper_fortes"] = _fortes_sniper(ctx["sniper"])

    if opcoes.usar_comportamento:
        from services.comportamento_diadesorte_service import ComportamentoDiaDeSorteService

        comp = ComportamentoDiaDeSorteService.analisar(janela=10, base_estatistica="geral")
        ctx["comportamento"] = comp
        alvos = (comp.get("criterios_sugeridos") or {}).get("alvos") or {}
        ctx["comp_alvos"] = alvos

    return ctx


def _boost_repeticao(pos_idx: int, dezena: int, ctx: Dict[str, Any]) -> float:
    rep = ctx.get("repeticao")
    if not rep:
        return 0.0
    pos = pos_idx + 1
    rep_pos = ctx.get("rep_por_pos") or {}
    if rep_pos.get(pos) == dezena:
        return 1.0
    row = (ctx.get("rep_dezenas") or {}).get(dezena) or {}
    score = 0.0
    if row.get("repetiu_ultimo_par_posicional"):
        score += 0.55
    perm = float(row.get("permanencia_pct") or 0) / 100.0
    score += perm * 0.35
    if row.get("tendencia") == "permanencia":
        score += 0.15
    return min(score, 1.0)


def _boost_sniper(dezena: int, ctx: Dict[str, Any]) -> float:
    if not ctx.get("sniper"):
        return 0.0
    score = 0.0
    if dezena in (ctx.get("sniper_fortes") or set()):
        score += 0.75
    rep_row = (ctx.get("rep_dezenas") or {}).get(dezena) or {}
    freq_pct = float(rep_row.get("freq_repeticao_pct") or 0) / 100.0
    score += min(freq_pct, 0.25)
    return min(score, 1.0)


def criar_score_boost(opcoes: OpcoesGeradorPosicao, ctx: Dict[str, Any]) -> Optional[Callable[[int, Dict[str, Any], float], float]]:
    opcoes = opcoes.normalizar()
    if not opcoes.usar_repeticao and not opcoes.usar_sniper:
        return None

    w_base = 0.55
    w_rep = 0.25 if opcoes.usar_repeticao else 0.0
    w_sni = 0.20 if opcoes.usar_sniper else 0.0
    total = w_base + w_rep + w_sni

    def boost(pos_idx: int, stat: Dict[str, Any], base: float) -> float:
        dezena = int(stat["dezena"])
        rep = _boost_repeticao(pos_idx, dezena, ctx) if opcoes.usar_repeticao else 0.0
        sni = _boost_sniper(dezena, ctx) if opcoes.usar_sniper else 0.0
        base_n = base / max(base, 0.001) if base > 0 else 0.0
        if base_n > 1:
            base_n = min(base_n / 10.0, 1.0)
        blended = (base * w_base + rep * w_rep * 10 + sni * w_sni * 10) / total
        return blended

    return boost


def criar_validador_comportamento(
    opcoes: OpcoesGeradorPosicao,
    ctx: Dict[str, Any],
) -> Optional[Callable[[List[int], Optional[Dict[str, Any]]], bool]]:
    if not opcoes.usar_comportamento or not ctx.get("comportamento"):
        return None

    from services.comportamento_diadesorte_service import ComportamentoDiaDeSorteService

    modo = opcoes.modo_comportamento

    def validar(dezenas: List[int], extras: Optional[Dict[str, Any]] = None) -> bool:
        try:
            val = ComportamentoDiaDeSorteService.validar_selecao_panorama_api(
                dezenas=dezenas,
                base_estatistica="geral",
                rank_escolhido=1,
                modo=modo,
                dezenas_por_jogo=NUM_POSICOES,
            )
            if modo == "estrito":
                return bool(val.get("valido"))
            score = int(val.get("score") or 0)
            return score >= 55
        except Exception:
            return True

    return validar


def gerar_apostas_com_plugins(
    posicoes_stats: Sequence[Dict[str, Any]],
    quantidade: int,
    opcoes: OpcoesGeradorPosicao,
    alvo_dig_soma: Optional[Tuple[int, int]] = None,
    plugins_ctx: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    opcoes = opcoes.normalizar()
    ctx = plugins_ctx if plugins_ctx is not None else carregar_plugins_ctx(opcoes)
    score_boost = criar_score_boost(opcoes, ctx)
    validar = criar_validador_comportamento(opcoes, ctx)

    qtd = max(1, min(int(quantidade), 100))
    r = random.Random()
    alvo = alvo_dig_soma if opcoes.filtrar_dig_soma else None
    apostas: List[Dict[str, Any]] = []
    vistos: Set[Tuple[int, ...]] = set()
    tentativas = 0
    max_total = qtd * (120 if opcoes.usar_comportamento else 80)

    while len(apostas) < qtd and tentativas < max_total:
        tentativas += 1
        ordem = montar_aposta_posicional(
            posicoes_stats,
            perfil=opcoes.perfil,
            alvo_dig_soma=alvo,
            rng=r,
            score_boost=score_boost,
        )
        if validar and not validar(ordem):
            continue
        chave = tuple(ordem)
        if chave in vistos:
            continue
        vistos.add(chave)
        item = formatar_aposta_posicional(ordem)
        if validar:
            try:
                from services.comportamento_diadesorte_service import ComportamentoDiaDeSorteService

                val = ComportamentoDiaDeSorteService.validar_selecao_panorama_api(
                    dezenas=ordem,
                    base_estatistica="geral",
                    rank_escolhido=1,
                    modo=opcoes.modo_comportamento,
                    dezenas_por_jogo=NUM_POSICOES,
                )
                item["comportamento_score"] = val.get("score")
                item["comportamento_valido"] = val.get("valido")
                item["comportamento_indicadores"] = val.get("indicadores")
            except Exception:
                pass
        apostas.append(item)

    if not apostas and not score_boost and not validar:
        return gerar_apostas_posicionais(
            posicoes_stats,
            quantidade=qtd,
            perfil=opcoes.perfil,
            filtrar_dig_soma=opcoes.filtrar_dig_soma,
            alvo_dig_soma=alvo,
        )

    return apostas
