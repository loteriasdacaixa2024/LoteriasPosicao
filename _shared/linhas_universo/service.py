# -*- coding: utf-8 -*-
"""Estatísticas históricas por Linha (L1–L10) — camada aditiva."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from analise_estudos.service_factory import make_estudos_base
from analise_estudos.specs import BASES_LABEL, get_estudos_config

from linhas_universo.core import classificar_dezenas, linhas_para_modalidade


class LinhasUniversoService:
    @classmethod
    def meta(cls, modality_key: str) -> Dict[str, Any]:
        return {"sucesso": True, **linhas_para_modalidade(modality_key)}

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
        mapa = linhas_para_modalidade(modality_key)

        if not sorteios:
            return {
                "sucesso": False,
                "erro": f"Nenhum sorteio na base «{base}».",
                "modality_key": modality_key,
            }

        freq_linha: Counter = Counter()
        atraso_atual: Dict[str, int] = {L["id"]: 0 for L in mapa["linhas"]}
        visto: Dict[str, bool] = {L["id"]: False for L in mapa["linhas"]}
        # Processar do mais antigo ao mais recente para atraso
        linhas_hist: List[Dict[str, Any]] = []
        overlap_consec: List[Dict[str, Any]] = []
        prev_set = None
        prev_conc = None

        for s in sorteios:
            dz = Base.dezenas_ordem(s)
            cl = classificar_dezenas(dz)
            presentes = set(cl["linhas_presentes"])
            for lid in presentes:
                freq_linha[lid] += 1
            for lid in atraso_atual:
                if lid in presentes:
                    atraso_atual[lid] = 0
                    visto[lid] = True
                else:
                    atraso_atual[lid] += 1
            row = {
                "concurso": s.concurso,
                "data": getattr(s, "data", "") or "",
                "dezenas": dz,
                "linhas_presentes": cl["linhas_presentes"],
                "qtd_linhas": cl["qtd_linhas"],
                "por_linha": cl["por_linha"],
            }
            linhas_hist.append(row)
            if prev_set is not None:
                inter = sorted(
                    presentes & prev_set,
                    key=lambda x: int(x[1:]) if x[1:].isdigit() else 0,
                )
                overlap_consec.append({
                    "concurso": s.concurso,
                    "concurso_anterior": prev_conc,
                    "linhas_repetidas": inter,
                    "qtd": len(inter),
                })
            prev_set = presentes
            prev_conc = s.concurso

        total = len(sorteios)
        freq = []
        for L in mapa["linhas"]:
            lid = L["id"]
            n = int(freq_linha.get(lid, 0))
            freq.append({
                "linha": lid,
                "label": L["label"],
                "ocorrencias": n,
                "pct": round(n / total * 100, 2) if total else 0,
                "atraso": atraso_atual.get(lid, total if not visto.get(lid) else atraso_atual.get(lid, 0)),
                "qtd_dezenas_universo": L["qtd"],
            })

        return {
            "sucesso": True,
            "modality_key": modality_key,
            "modality_nome": cfg.get("nome", modality_key),
            "base": base,
            "base_label": BASES_LABEL.get(base, base),
            "janela": janela,
            "total_concursos": total,
            "primeiro_concurso": sorteios[0].concurso if sorteios else None,
            "ultimo_concurso": sorteios[-1].concurso if sorteios else None,
            "mapa": mapa,
            "frequencia_linhas": freq,
            "repeticoes_consecutivas": overlap_consec,
            "linhas": linhas_hist,
        }
