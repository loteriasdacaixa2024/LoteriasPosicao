# -*- coding: utf-8 -*-
"""Comportamento SS — Super Sete (dígitos por coluna C1–C7)."""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Set, Tuple

from geradores_elite.comportamento.base_service import ComportamentoBaseService
from geradores_elite.comportamento.specs import SUPERSETE_SPEC


def _contar_seq_adjacentes(digitos: List[int]) -> int:
    grupos = 0
    i = 0
    while i < len(digitos) - 1:
        if abs(digitos[i + 1] - digitos[i]) == 1:
            j = i
            while j + 1 < len(digitos) and abs(digitos[j + 1] - digitos[j]) == 1:
                j += 1
            grupos += 1
            i = j + 1
        else:
            i += 1
    return grupos


class ComportamentoSuperSeteService(ComportamentoBaseService):
    SPEC = SUPERSETE_SPEC
    SorteioModel: Any = None

    @classmethod
    def _dezenas_from_sorteio(cls, s: Any) -> List[int]:
        return list(s.digitos())

    @classmethod
    def _calcular_indicadores(
        cls,
        dezenas: List[int],
        prev_dezenas: Optional[List[int]] = None,
        extras: Optional[Dict[str, int]] = None,
    ) -> Dict[str, int]:
        sp = cls._spec()
        pa = sum(1 for d in dezenas if d % 2 == 0)
        im = len(dezenas) - pa
        pr = sum(1 for d in dezenas if d in sp.primos)
        rp = 0
        if prev_dezenas and len(prev_dezenas) == len(dezenas):
            rp = sum(1 for a, b in zip(dezenas, prev_dezenas) if a == b)
        ex = sum(1 for d in dezenas if d in sp.moldura)
        sq = _contar_seq_adjacentes(dezenas)
        return {"PA": pa, "IM": im, "PR": pr, "RP": rp, "EX": ex, "SQ": sq}

    @classmethod
    def _ajustar_coluna(
        cls,
        digitos: List[int],
        col: int,
        codigo: str,
        alvo: int,
        prev: Optional[List[int]],
    ) -> List[int]:
        out = list(digitos)
        sp = cls._spec()
        tent = 0
        while tent < 40:
            tent += 1
            ind = cls._calcular_indicadores(out, prev)
            atual = ind[codigo]
            if atual == alvo:
                break
            precisa = atual < alvo
            if codigo == "RP" and prev and len(prev) == len(out):
                if precisa and out[col] != prev[col]:
                    out[col] = prev[col]
                    continue
                if not precisa and out[col] == prev[col]:
                    out[col] = random.choice([d for d in range(10) if d != prev[col]])
                    continue
            if codigo == "EX":
                extremos = [0, 9]
                if precisa and out[col] not in extremos:
                    out[col] = random.choice(extremos)
                    continue
                if not precisa and out[col] in extremos:
                    out[col] = random.choice([d for d in range(1, 9)])
                    continue
            if codigo in ("PA", "IM"):
                pares = [0, 2, 4, 6, 8]
                impares = [1, 3, 5, 7, 9]
                if codigo == "PA":
                    pool = pares if precisa else impares
                else:
                    pool = impares if precisa else pares
                out[col] = random.choice(pool)
                continue
            if codigo == "PR":
                primos = list(sp.primos)
                nao = [d for d in range(10) if d not in primos]
                out[col] = random.choice(primos if precisa else nao)
                continue
            if codigo == "SQ" and col < len(out) - 1:
                out[col] = random.randint(0, 8)
                out[col + 1] = out[col] + 1
                continue
            break
        return out

    @classmethod
    def _tentar_montar_aposta(
        cls,
        k: int,
        alvos: Dict[str, int],
        ativos: List[str],
        pesos_base: List[Tuple[int, float]],
        ultimo_prev: Optional[List[int]],
        perfil: str,
        score_min: int,
        candidatos: List[int],
        extras_alvo: Optional[Dict[str, int]] = None,
    ) -> Optional[Dict[str, Any]]:
        sp = cls._spec()
        pick = [random.randint(0, 9) for _ in range(k)]
        for cod in ativos:
            if cod not in sp.indicadores:
                continue
            for col in range(k):
                pick = cls._ajustar_coluna(pick, col, cod, alvos.get(cod, 0), ultimo_prev)
        score = cls._score_aposta(pick, alvos, ativos, ultimo_prev)
        if score < score_min:
            return None
        ind = cls._calcular_indicadores(pick, ultimo_prev)
        rp = ind.get("RP", 0)
        return {
            "dezenas": pick,
            "comportamento": ind,
            "sobreposicao": rp,
            "score_comportamento": score,
            "alvos_aposta": dict(alvos),
        }

    @classmethod
    def gerar_apostas(
        cls,
        quantidade: int = 10,
        dezenas_por_jogo: Optional[int] = None,
        janela: int = 10,
        perfil: str = "equilibrado",
        modo_geracao: str = "automatico",
        modo_motor: str = "perfil_sorteio",
        regras_manuais: Optional[Dict[str, Any]] = None,
        filtros: Optional[Dict[str, int]] = None,
        analise: Optional[Dict[str, Any]] = None,
        base_estatistica: str = "geral",
    ) -> Dict[str, Any]:
        raw = super().gerar_apostas(
            quantidade,
            dezenas_por_jogo,
            janela,
            perfil,
            modo_geracao,
            modo_motor,
            regras_manuais,
            filtros,
            analise,
            base_estatistica,
        )
        if not raw.get("sucesso"):
            return raw
        for a in raw.get("apostas") or []:
            dz = a.get("dezenas") or []
            a["texto"] = "-".join(str(d) for d in dz)
        return raw
