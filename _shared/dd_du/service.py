# -*- coding: utf-8 -*-
"""Estatísticas históricas DD × DU (fase 1: somente estatísticas)."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Set, Tuple

from analise_estudos.service_factory import make_estudos_base
from analise_estudos.specs import BASES_LABEL, get_estudos_config

from dd_du.core import decompor_dezena, decompor_lista


def _dd_range(dezena_min: int, dezena_max: int, pad_width: int) -> List[int]:
    if pad_width <= 1:
        return [0]
    vals = set()
    for n in range(int(dezena_min), int(dezena_max) + 1):
        dd, _ = decompor_dezena(n, pad_width)
        vals.add(dd)
    return sorted(vals)


def _du_range(dezena_min: int, dezena_max: int, pad_width: int) -> List[int]:
    if pad_width <= 1:
        return list(range(int(dezena_min), int(dezena_max) + 1))
    vals = set()
    for n in range(int(dezena_min), int(dezena_max) + 1):
        _, du = decompor_dezena(n, pad_width)
        vals.add(du)
    return sorted(vals)


class DdDuService:
    """Camada estatística independente — não altera análises existentes."""

    @classmethod
    def analisar(
        cls,
        modality_key: str,
        janela: int = 0,
        base_estatistica: str = "geral",
    ) -> Dict[str, Any]:
        Base = make_estudos_base(modality_key)
        janela = Base._normalizar_janela(janela)
        base = Base._normalizar_base(base_estatistica)
        sorteios = Base.carregar_sorteios_asc(base, janela if janela > 0 else 0)
        cfg = get_estudos_config(modality_key)
        pad = int(cfg.get("pad_width") or 2)
        dmin, dmax = int(cfg["dezena_min"]), int(cfg["dezena_max"])
        dd_vals = _dd_range(dmin, dmax, pad)
        du_vals = _du_range(dmin, dmax, pad)

        if not sorteios:
            return {
                "sucesso": False,
                "erro": f"Nenhum sorteio na base «{base}».",
                "modality_key": modality_key,
            }

        freq_dd: Counter = Counter()
        freq_du: Counter = Counter()
        # Matriz: contagem de aparições do par (DD,DU) = dezena no histórico
        matriz: Dict[Tuple[int, int], int] = Counter()
        # Presença por concurso (para atraso / repetição)
        atraso_dd = {d: 0 for d in dd_vals}
        atraso_du = {u: 0 for u in du_vals}
        visto_dd = {d: False for d in dd_vals}
        visto_du = {u: False for u in du_vals}

        hist: List[Dict[str, Any]] = []
        rep_dd: List[Dict[str, Any]] = []
        rep_du: List[Dict[str, Any]] = []
        prev_dd: Set[int] | None = None
        prev_du: Set[int] | None = None
        prev_conc = None

        for s in sorteios:
            dz = Base.dezenas_ordem(s)
            dec = decompor_lista(dz, pad)
            set_dd = set(dec["dd"])
            set_du = set(dec["du"])

            for d in dec["dd"]:
                freq_dd[d] += 1
            for u in dec["du"]:
                freq_du[u] += 1
            for p in dec["pares"]:
                matriz[(p["dd"], p["du"])] += 1

            for d in dd_vals:
                if d in set_dd:
                    atraso_dd[d] = 0
                    visto_dd[d] = True
                else:
                    atraso_dd[d] += 1
            for u in du_vals:
                if u in set_du:
                    atraso_du[u] = 0
                    visto_du[u] = True
                else:
                    atraso_du[u] += 1

            hist.append({
                "concurso": s.concurso,
                "data": getattr(s, "data", "") or "",
                "dezenas": dz,
                "dd": dec["dd"],
                "du": dec["du"],
                "dd_unicos": dec["dd_unicos"],
                "du_unicos": dec["du_unicos"],
                "qtd_dd_unicos": dec["qtd_dd_unicos"],
                "qtd_du_unicos": dec["qtd_du_unicos"],
                "pares": dec["pares"],
            })

            if prev_dd is not None:
                inter_dd = sorted(set_dd & prev_dd)
                inter_du = sorted(set_du & prev_du) if prev_du is not None else []
                rep_dd.append({
                    "concurso": s.concurso,
                    "concurso_anterior": prev_conc,
                    "dd_repetidos": inter_dd,
                    "qtd": len(inter_dd),
                })
                rep_du.append({
                    "concurso": s.concurso,
                    "concurso_anterior": prev_conc,
                    "du_repetidos": inter_du,
                    "qtd": len(inter_du),
                })

            prev_dd, prev_du, prev_conc = set_dd, set_du, s.concurso

        total = len(sorteios)
        # Ocorrências = aparições com multiplicidade; também presença por concurso
        pres_dd: Counter = Counter()
        pres_du: Counter = Counter()
        for row in hist:
            for d in row["dd_unicos"]:
                pres_dd[d] += 1
            for u in row["du_unicos"]:
                pres_du[u] += 1

        stats_dd = []
        for d in dd_vals:
            n = int(pres_dd.get(d, 0))
            stats_dd.append({
                "dd": d,
                "presencas": n,
                "ocorrencias": int(freq_dd.get(d, 0)),
                "pct_presenca": round(n / total * 100, 2) if total else 0,
                "atraso": atraso_dd[d] if visto_dd[d] else total,
            })

        stats_du = []
        for u in du_vals:
            n = int(pres_du.get(u, 0))
            stats_du.append({
                "du": u,
                "presencas": n,
                "ocorrencias": int(freq_du.get(u, 0)),
                "pct_presenca": round(n / total * 100, 2) if total else 0,
                "atraso": atraso_du[u] if visto_du[u] else total,
            })

        # Matriz DD × DU (linhas = DD, colunas = DU)
        matriz_grid = []
        for d in dd_vals:
            row = []
            for u in du_vals:
                row.append(int(matriz.get((d, u), 0)))
            matriz_grid.append(row)

        return {
            "sucesso": True,
            "modality_key": modality_key,
            "modality_nome": cfg.get("nome", modality_key),
            "base": base,
            "base_label": BASES_LABEL.get(base, base),
            "janela": janela,
            "pad_width": pad,
            "dezena_min": dmin,
            "dezena_max": dmax,
            "total_concursos": total,
            "primeiro_concurso": sorteios[0].concurso if sorteios else None,
            "ultimo_concurso": sorteios[-1].concurso if sorteios else None,
            "dd_dominio": dd_vals,
            "du_dominio": du_vals,
            "frequencia_dd": stats_dd,
            "frequencia_du": stats_du,
            "matriz_dd_du": {
                "dd": dd_vals,
                "du": du_vals,
                "grid": matriz_grid,
            },
            "repeticoes_dd_consecutivas": rep_dd,
            "repeticoes_du_consecutivas": rep_du,
            "linhas": hist,
            "fase": "estatisticas",
            "permutacao_du": False,
        }
