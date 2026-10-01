# -*- coding: utf-8 -*-
"""Confronto Linha × Coluna — posição física da dezena no volante.

A linha e a coluna vêm do layout já usado pela geometria do volante
(`analise_gaps_ciclo.geometria.layout_de`). No Dia de Sorte isso é:

    linha 1: 01–10
    linha 2: 11–20
    linha 3: 21–30
    linha 4: somente 31 (coluna 1)

Não há células para dezenas fora do volante. O cálculo histórico usa os
mesmos sorteios da página Linhas & DD × DU (base + janela).
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Sequence, Tuple

Serie = Sequence[Tuple[int, Iterable[int]]]


def celulas_volante(modality_key: str) -> Dict[str, Any]:
    """Células reais do volante. Linha e coluna são 1-based."""
    from analise_gaps_ciclo.geometria import layout_de

    layout = layout_de(modality_key)
    if layout.posicional:
        raise ValueError(
            "Confronto linha × coluna não se aplica a volante posicional."
        )
    celulas: List[Dict[str, int]] = []
    for r, row in enumerate(layout.volante):
        for c, dez in enumerate(row):
            celulas.append({
                "dezena": int(dez),
                "linha": r + 1,
                "coluna": c + 1,
            })
    return {
        "volante": [list(row) for row in layout.volante],
        "cols": int(layout.cols),
        "celulas": celulas,
        "isolado": layout.isolado,
    }


def calcular_metricas(celulas: Sequence[Dict[str, int]], serie: Serie) -> List[Dict[str, Any]]:
    """Ocorrência, percentual, atraso atual, maior atraso e último concurso.

    A série entra do concurso mais antigo para o mais recente.
    Cada dezena conta no máximo uma vez por concurso.
    O maior atraso inclui o intervalo antes da primeira saída, os intervalos
    entre saídas e o intervalo ainda aberto depois da última saída.
    """
    estado: Dict[int, Dict[str, Any]] = {}
    for cell in celulas:
        dez = int(cell["dezena"])
        estado[dez] = {
            "dezena": dez,
            "linha": int(cell["linha"]),
            "coluna": int(cell["coluna"]),
            "ocorrencias": 0,
            "ultimo_concurso": None,
            "atraso_atual": 0,
            "maior_atraso": 0,
            "_gap": 0,
        }

    for concurso, dezenas in serie:
        presentes = {int(d) for d in dezenas}
        conc = int(concurso)
        for dez, st in estado.items():
            if dez in presentes:
                if st["_gap"] > st["maior_atraso"]:
                    st["maior_atraso"] = st["_gap"]
                st["_gap"] = 0
                st["ocorrencias"] += 1
                st["ultimo_concurso"] = conc
            else:
                st["_gap"] += 1

    total = len(serie)
    saida: List[Dict[str, Any]] = []
    for dez in sorted(estado):
        st = estado[dez]
        if st["_gap"] > st["maior_atraso"]:
            st["maior_atraso"] = st["_gap"]
        st["atraso_atual"] = int(st["_gap"])
        st["pct"] = round(st["ocorrencias"] / total * 100, 2) if total else 0.0
        st["ultimo_concurso"] = (
            int(st["ultimo_concurso"]) if st["ultimo_concurso"] is not None else None
        )
        del st["_gap"]
        saida.append(st)
    return saida


class LinhaColunaService:
    """Camada aditiva. Não altera Linhas L1–L10 nem DD × DU."""

    @classmethod
    def analisar(
        cls,
        modality_key: str,
        janela: int = 0,
        base_estatistica: str = "geral",
    ) -> Dict[str, Any]:
        from analise_estudos.service_factory import make_estudos_base
        from analise_estudos.specs import BASES_LABEL, get_estudos_config

        mapa = celulas_volante(modality_key)
        Base = make_estudos_base(modality_key)
        janela = Base._normalizar_janela(janela)
        base = Base._normalizar_base(base_estatistica)
        sorteios = Base.carregar_sorteios_asc(base, janela if janela > 0 else 0)
        cfg = get_estudos_config(modality_key)

        if not sorteios:
            return {
                "sucesso": False,
                "erro": f"Nenhum sorteio na base «{base}».",
                "modality_key": modality_key,
            }

        serie = [
            (int(s.concurso), Base.dezenas_ordem(s))
            for s in sorteios
        ]
        dezenas = calcular_metricas(mapa["celulas"], serie)
        total = len(sorteios)
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
            "volante": mapa["volante"],
            "cols": mapa["cols"],
            "isolado": mapa["isolado"],
            "dezenas": dezenas,
        }
