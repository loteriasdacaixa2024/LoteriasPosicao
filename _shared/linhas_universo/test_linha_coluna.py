# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sys
import unittest

_SHARED = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from linhas_universo.linha_coluna import calcular_metricas, celulas_volante


class TestVolanteDiaDeSorte(unittest.TestCase):
    def test_mapa_fisico_com_31_isolado(self):
        mapa = celulas_volante("diadesorte")
        self.assertEqual(mapa["volante"][0], list(range(1, 11)))
        self.assertEqual(mapa["volante"][1], list(range(11, 21)))
        self.assertEqual(mapa["volante"][2], list(range(21, 31)))
        self.assertEqual(mapa["volante"][3], [31])
        self.assertEqual(len(mapa["celulas"]), 31)
        self.assertNotIn(32, [c["dezena"] for c in mapa["celulas"]])

        por = {c["dezena"]: c for c in mapa["celulas"]}
        self.assertEqual((por[1]["linha"], por[1]["coluna"]), (1, 1))
        self.assertEqual((por[10]["linha"], por[10]["coluna"]), (1, 10))
        self.assertEqual((por[11]["linha"], por[11]["coluna"]), (2, 1))
        self.assertEqual((por[20]["linha"], por[20]["coluna"]), (2, 10))
        self.assertEqual((por[30]["linha"], por[30]["coluna"]), (3, 10))
        self.assertEqual((por[31]["linha"], por[31]["coluna"]), (4, 1))

    def test_outras_modalidades_nao_copiam_a_grade_do_dia_de_sorte(self):
        loto = celulas_volante("lotofacil")
        self.assertEqual(loto["cols"], 5)
        self.assertEqual(len(loto["celulas"]), 25)
        self.assertEqual(loto["volante"][0], [1, 2, 3, 4, 5])
        self.assertEqual(loto["volante"][-1], [21, 22, 23, 24, 25])


class TestMetricas(unittest.TestCase):
    def test_atrasos_ocorrencia_e_percentual(self):
        celulas = [
            {"dezena": 1, "linha": 1, "coluna": 1},
            {"dezena": 31, "linha": 4, "coluna": 1},
        ]
        # concursos 10..21; dezena 1 sai nos índices 2, 5 e 9 da série de 12
        serie = []
        saidas = {2, 5, 9}
        for i in range(12):
            dezenas = [1] if i in saidas else []
            if i == 0:
                dezenas.append(31)
            serie.append((10 + i, dezenas))

        out = {r["dezena"]: r for r in calcular_metricas(celulas, serie)}
        self.assertEqual(out[1]["ocorrencias"], 3)
        self.assertEqual(out[1]["atraso_atual"], 2)
        self.assertEqual(out[1]["maior_atraso"], 3)
        self.assertEqual(out[1]["ultimo_concurso"], 19)
        self.assertEqual(out[1]["pct"], 25.0)
        self.assertEqual(out[31]["ocorrencias"], 1)
        self.assertEqual(out[31]["atraso_atual"], 11)
        self.assertEqual(out[31]["maior_atraso"], 11)
        self.assertEqual(out[31]["ultimo_concurso"], 10)
        self.assertEqual(out[31]["linha"], 4)
        self.assertEqual(out[31]["coluna"], 1)

    def test_nunca_saiu(self):
        celulas = [{"dezena": 7, "linha": 1, "coluna": 7}]
        serie = [(1, [1]), (2, [2]), (3, [3])]
        row = calcular_metricas(celulas, serie)[0]
        self.assertEqual(row["ocorrencias"], 0)
        self.assertEqual(row["pct"], 0.0)
        self.assertEqual(row["atraso_atual"], 3)
        self.assertEqual(row["maior_atraso"], 3)
        self.assertIsNone(row["ultimo_concurso"])


if __name__ == "__main__":
    unittest.main()
