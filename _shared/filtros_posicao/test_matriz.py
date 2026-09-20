# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sys
import unittest
from types import SimpleNamespace

_SHARED = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from filtros_posicao.service import _analisar_posicoes, _montar_matriz


def _spec_dds():
    return SimpleNamespace(
        num_posicoes=7,
        valor_min=1,
        valor_max=31,
        pos_prefix="P",
        pos_label="Posição",
        fmt=lambda v: f"{int(v):02d}",
    )


class TestMatrizFrequenciaPosicao(unittest.TestCase):
    def test_universo_completo_com_zeros(self):
        spec = _spec_dds()
        posicoes = _analisar_posicoes(
            [{"bolas": [7, 14, 21, 3, 18, 9, 31]}],
            spec,
            ordenar=False,
        )
        matriz = _montar_matriz(posicoes, spec)
        self.assertEqual(len(matriz["linhas"]), 31)
        self.assertEqual(matriz["linhas"][0]["label"], "01")
        self.assertEqual(matriz["linhas"][-1]["label"], "31")
        self.assertEqual(len(matriz["colunas"]), 7)
        self.assertEqual(matriz["colunas"][0]["label"], "1ª posição")
        self.assertEqual(matriz["colunas"][6]["label"], "7ª posição")
        self.assertEqual(matriz["linhas"][0]["contagens"], [0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(matriz["linhas"][6]["contagens"], [1, 0, 0, 0, 0, 0, 0])
        self.assertEqual(matriz["linhas"][30]["contagens"], [0, 0, 0, 0, 0, 0, 1])

    def test_crescente_nao_mistura_com_sorteio(self):
        spec = _spec_dds()
        concursos = [
            {"bolas": [18, 3, 31, 7, 14, 1, 22]},
            {"bolas": [9, 25, 4, 16, 2, 28, 11]},
        ]
        sorteio = _montar_matriz(_analisar_posicoes(concursos, spec, ordenar=False), spec)
        crescente = _montar_matriz(_analisar_posicoes(concursos, spec, ordenar=True), spec)

        self.assertEqual(sorteio["linhas"][17]["contagens"][0], 1)
        self.assertEqual(sorteio["linhas"][0]["contagens"][5], 1)
        self.assertEqual(crescente["linhas"][0]["contagens"][0], 1)
        self.assertEqual(crescente["linhas"][1]["contagens"][0], 1)
        self.assertNotEqual(
            [l["contagens"] for l in sorteio["linhas"]],
            [l["contagens"] for l in crescente["linhas"]],
        )
        tot_s = [sum(l["contagens"]) for l in sorteio["linhas"]]
        tot_c = [sum(l["contagens"]) for l in crescente["linhas"]]
        self.assertEqual(tot_s, tot_c)

    def test_cada_concurso_conta_uma_vez_por_posicao(self):
        spec = _spec_dds()
        concursos = [
            {"bolas": [1, 2, 3, 4, 5, 6, 7]},
            {"bolas": [8, 9, 10, 11, 12, 13, 14]},
            {"bolas": [15, 16, 17, 18, 19, 20, 21]},
        ]
        matriz = _montar_matriz(_analisar_posicoes(concursos, spec, ordenar=False), spec)
        for i in range(7):
            self.assertEqual(sum(l["contagens"][i] for l in matriz["linhas"]), 3)


if __name__ == "__main__":
    unittest.main()
