# -*- coding: utf-8 -*-
"""Repetição de dezenas entre concursos consecutivos — serviço genérico."""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Set

from models.shared import db

from analise_comparar.compare_config import get_compare_config
from analise_comparar.compare_service import _dezenas_set, _dezenas_ordered, _load_model
from analise_repeticao.repeticao_config import get_repeticao_config


def _pct(qtd: int, total: int) -> float:
    return round(qtd / total * 100, 1) if total else 0.0


def _ano_de_data(data: str) -> Optional[str]:
    if not data or len(data) < 4:
        return None
    parts = data.split("/")
    if len(parts) == 3:
        return parts[2]
    return data[-4:]


def _decada(ano: str) -> Optional[str]:
    if not ano or not ano.isdigit() or len(ano) < 4:
        return None
    base = (int(ano) // 10) * 10
    return f"{base}s"


def _fmt_dezena(d: int, dezena_min: int) -> str:
    if dezena_min == 0:
        return f"{d:02d}"
    return f"{d:02d}" if d < 100 else str(d)


def _label_repeticoes(k: int) -> str:
    if k == 0:
        return "0 dezenas repetidas"
    if k == 1:
        return "1 dezena repetida"
    return f"{k} dezenas repetidas"


class RepeticaoConsecutivaService:
    def __init__(self, modality_key: str):
        self.modality_key = modality_key
        self.compare_cfg = get_compare_config(modality_key)
        self.rep_cfg = get_repeticao_config(modality_key)
        self.Model = _load_model(self.compare_cfg)
        self.sorteadas = int(self.rep_cfg.get("sorteadas", 6))
        self.dezena_min = int(self.compare_cfg.get("dezena_min", 1))
        self.nome = self.compare_cfg.get("nome", modality_key)

    def _set_dezenas(self, row: Any) -> Set[int]:
        return _dezenas_set(row, self.compare_cfg, int(self.rep_cfg.get("default_sorteio", 1)))

    def _list_dezenas(self, row: Any) -> List[int]:
        return _dezenas_ordered(row, self.compare_cfg, int(self.rep_cfg.get("default_sorteio", 1)))

    def analise_completa(self) -> Optional[Dict[str, Any]]:
        sorteios = (
            db.session.query(self.Model)
            .order_by(self.Model.concurso.asc())
            .all()
        )
        if len(sorteios) < 2:
            return None

        max_k = self.sorteadas + 1
        total_pares = len(sorteios) - 1
        freq_qtd: Counter = Counter()
        exemplos_por_qtd: Dict[int, List[Dict]] = defaultdict(list)
        historico: List[Dict[str, Any]] = []

        por_ano: Dict[str, List[int]] = defaultdict(list)
        por_decada: Dict[str, List[int]] = defaultdict(list)

        streak_sem = streak_com = 0
        max_streak_sem = max_streak_com = 0
        inicio_max_sem = fim_max_sem = None
        inicio_max_com = fim_max_com = None
        cur_inicio_sem = cur_inicio_com = None

        prev = sorteios[0]
        for s in sorteios[1:]:
            atual_dz = self._set_dezenas(s)
            prev_dz = self._set_dezenas(prev)
            rep_set = atual_dz & prev_dz
            qtd = len(rep_set)
            freq_qtd[qtd] += 1

            ex_item = {
                "concurso_anterior": prev.concurso,
                "data_anterior": prev.data,
                "dezenas_anterior": [_fmt_dezena(d, self.dezena_min) for d in sorted(prev_dz)],
                "concurso": s.concurso,
                "data": s.data,
                "dezenas": [_fmt_dezena(d, self.dezena_min) for d in sorted(atual_dz)],
                "repetidas": [_fmt_dezena(d, self.dezena_min) for d in sorted(rep_set)],
                "quantidade": qtd,
            }
            if len(exemplos_por_qtd[qtd]) < 5:
                exemplos_por_qtd[qtd].append(ex_item)

            historico.append({
                "concurso": s.concurso,
                "quantidade": qtd,
                "repetidas": sorted(rep_set),
            })

            ano = _ano_de_data(s.data)
            if ano:
                por_ano[ano].append(qtd)
                dec = _decada(ano)
                if dec:
                    por_decada[dec].append(qtd)

            if qtd == 0:
                if streak_sem == 0:
                    cur_inicio_sem = s.concurso
                streak_sem += 1
                if streak_com > max_streak_com:
                    max_streak_com = streak_com
                    inicio_max_com = cur_inicio_com
                    fim_max_com = s.concurso - 1
                streak_com = 0
                cur_inicio_com = None
                if streak_sem > max_streak_sem:
                    max_streak_sem = streak_sem
                    inicio_max_sem = cur_inicio_sem
                    fim_max_sem = s.concurso
            else:
                if streak_com == 0:
                    cur_inicio_com = s.concurso
                streak_com += 1
                if streak_sem > max_streak_sem:
                    max_streak_sem = streak_sem
                    inicio_max_sem = cur_inicio_sem
                    fim_max_sem = s.concurso - 1
                streak_sem = 0
                cur_inicio_sem = None
                if streak_com > max_streak_com:
                    max_streak_com = streak_com
                    inicio_max_com = cur_inicio_com
                    fim_max_com = s.concurso

            prev = s

        if streak_sem > max_streak_sem:
            max_streak_sem = streak_sem
            inicio_max_sem = cur_inicio_sem
            fim_max_sem = sorteios[-1].concurso
        if streak_com > max_streak_com:
            max_streak_com = streak_com
            inicio_max_com = cur_inicio_com
            fim_max_com = sorteios[-1].concurso

        todas_qtds = [h["quantidade"] for h in historico]
        media_global = round(sum(todas_qtds) / len(todas_qtds), 2) if todas_qtds else 0

        distribuicao = []
        for k in range(max_k):
            qtd_freq = freq_qtd.get(k, 0)
            distribuicao.append({
                "repeticoes": _label_repeticoes(k),
                "quantidade": qtd_freq,
                "porcentagem": _pct(qtd_freq, total_pares),
                "exemplos": exemplos_por_qtd.get(k, []),
            })

        ult = sorteios[-1]
        pen = sorteios[-2]
        ult_rep = self._set_dezenas(ult) & self._set_dezenas(pen)
        ult_qtd = len(ult_rep)
        freq_ult_qtd = freq_qtd.get(ult_qtd, 0)

        ultimo_analise = {
            "concurso": ult.concurso,
            "concurso_anterior": pen.concurso,
            "dezenas_repetidas_qtd": ult_qtd,
            "dezenas_repetidas": [_fmt_dezena(d, self.dezena_min) for d in sorted(ult_rep)],
            "dezenas_atual": [_fmt_dezena(d, self.dezena_min) for d in self._list_dezenas(ult)],
            "dezenas_anterior": [_fmt_dezena(d, self.dezena_min) for d in self._list_dezenas(pen)],
            "freq_historica_estrutura": freq_ult_qtd,
            "pct_historica_estrutura": _pct(freq_ult_qtd, total_pares),
        }

        def _media_lista(vals: List[int]) -> float:
            return round(sum(vals) / len(vals), 2) if vals else 0.0

        media_por_ano = [
            {"ano": ano, "media": _media_lista(vals), "concursos": len(vals)}
            for ano, vals in sorted(por_ano.items())
        ]
        media_por_decada = [
            {"decada": dec, "media": _media_lista(vals), "concursos": len(vals)}
            for dec, vals in sorted(por_decada.items())
        ]

        def _resumo_janela(n: int) -> Dict[str, Any]:
            slice_h = historico[-n:] if len(historico) >= n else historico
            if not slice_h:
                return {}
            dist = Counter(h["quantidade"] for h in slice_h)
            media = round(sum(h["quantidade"] for h in slice_h) / len(slice_h), 2)
            moda = dist.most_common(1)[0][0] if dist else 0
            return {
                "concursos": len(slice_h),
                "media_repeticao": media,
                "moda_repeticao": moda,
                "distribuicao": {str(k): dist.get(k, 0) for k in range(max_k)},
                "acima_media_historica": media > media_global,
            }

        recente_10 = _resumo_janela(10)
        recente_30 = _resumo_janela(30)

        ultimos_100 = historico[-100:] if len(historico) >= 100 else historico
        media_100 = (
            round(sum(h["quantidade"] for h in ultimos_100) / len(ultimos_100), 2)
            if ultimos_100 else 0
        )
        tendencia = "estável"
        limiar = max(0.15, media_global * 0.08)
        if media_100 > media_global + limiar:
            tendencia = "acima da média"
        elif media_100 < media_global - limiar:
            tendencia = "abaixo da média"

        sugestoes = self._sugestoes_estruturais(
            distribuicao, media_global, recente_10, tendencia, ult_qtd
        )

        return {
            "total_concursos": len(sorteios),
            "total_pares_analisados": total_pares,
            "ultimo_concurso": ult.concurso,
            "sorteadas": self.sorteadas,
            "distribuicao": distribuicao,
            "media_historica": media_global,
            "sequencias": {
                "maior_sem_repeticao": {
                    "concursos": max_streak_sem,
                    "de": inicio_max_sem,
                    "ate": fim_max_sem,
                },
                "maior_com_repeticao": {
                    "concursos": max_streak_com,
                    "de": inicio_max_com,
                    "ate": fim_max_com,
                },
            },
            "media_por_ano": media_por_ano,
            "media_por_decada": media_por_decada,
            "tendencia_recente_100": {
                "media": media_100,
                "tendencia": tendencia,
                "media_historica": media_global,
            },
            "ultimos_10": recente_10,
            "ultimos_30": recente_30,
            "ultimo_concurso_analise": ultimo_analise,
            "sugestoes_estruturais": sugestoes,
        }

    def _sugestoes_estruturais(
        self,
        distribuicao: List[Dict],
        media: float,
        recente_10: Dict,
        tendencia: str,
        ult_qtd: int,
    ) -> Dict[str, Any]:
        itens = []
        moda_item = max(distribuicao, key=lambda d: d["quantidade"], default=None)
        if moda_item:
            itens.append(
                f"A faixa mais frequente no histórico da {self.nome} é "
                f"**{moda_item['repeticoes']}** ({moda_item['porcentagem']:.1f}% dos pares consecutivos)."
            )

        itens.append(
            f"Média histórica de repetição entre concursos seguidos: **{media:.2f}** dezenas "
            f"({self.sorteadas} sorteadas por concurso)."
        )

        alto = sum(d["porcentagem"] for k, d in enumerate(distribuicao) if k > 3)
        if alto > 0:
            itens.append(
                f"Repetições acima de 3 dezenas são relativamente raras ({alto:.1f}% do histórico)."
            )

        if tendencia == "acima da média":
            itens.append(
                f"Os últimos 100 concursos estão acima da média histórica ({media:.2f} dezenas por transição)."
            )
        elif tendencia == "abaixo da média":
            itens.append(
                f"Os últimos 100 concursos estão abaixo da média histórica ({media:.2f} dezenas por transição)."
            )
        else:
            itens.append(
                f"Tendência recente (últimos 100) alinhada à média histórica ({media:.2f} dezenas)."
            )

        if recente_10.get("acima_media_historica"):
            itens.append("Os últimos 10 concursos apresentam repetição acima da média histórica.")
        elif recente_10:
            itens.append("Os últimos 10 concursos estão na média ou abaixo em repetição consecutiva.")

        moda_k = moda_item["repeticoes"] if moda_item else _label_repeticoes(round(media))
        estrutura = f"considerar faixa próxima de {moda_k} do último resultado"
        if ult_qtd > media + 1:
            estrutura = (
                f"considerar faixa abaixo de {ult_qtd} repetições "
                "(último concurso teve repetição acima da média)"
            )
        elif ult_qtd == 0:
            estrutura = (
                f"considerar faixa em torno da moda histórica ({moda_k}) "
                "(último concurso não repetiu nenhuma dezena)"
            )

        return {
            "itens": [i.replace("**", "") for i in itens],
            "estrutura_sugerida": estrutura,
            "ultimo_padrao": ult_qtd,
        }
