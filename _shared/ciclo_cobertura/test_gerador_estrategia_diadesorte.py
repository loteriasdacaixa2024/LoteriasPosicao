# -*- coding: utf-8 -*-
"""Dia de Sorte — faixa de faltantes e diagonais do gerador de estratégia."""
from __future__ import annotations

import os
import sys
import unittest

_SHARED = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from ciclo_cobertura.gerador_estrategia import (
    _combos_cobertura,
    _k_alvo_diadesorte,
    _plantar_segmento,
)
from analise_inteligentes_diadesorte.diagonais_volante import (
    diagonais_na_aposta,
    resumo_contagem_diagonais,
)


class TestKAlvo(unittest.TestCase):
    def test_automatico_prefere_4(self):
        k, motivo = _k_alvo_diadesorte(12, 7, 20, None)
        self.assertEqual((k, motivo), (4, "auto"))

    def test_cai_para_3_e_2(self):
        self.assertEqual(_k_alvo_diadesorte(3, 7, 20, None), (3, "auto"))
        self.assertEqual(_k_alvo_diadesorte(2, 7, 20, None), (2, "auto"))

    def test_uma_pendente_e_excecao(self):
        k, motivo = _k_alvo_diadesorte(1, 7, 20, None)
        self.assertEqual(k, 1)
        self.assertEqual(motivo, "excecao")

    def test_fixo_respeitado(self):
        self.assertEqual(_k_alvo_diadesorte(12, 7, 20, 2), (2, "fixo"))
        self.assertEqual(_k_alvo_diadesorte(12, 7, 20, 6), (6, "fixo"))

    def test_fixo_sobe_se_nao_fecha(self):
        k, motivo = _k_alvo_diadesorte(10, 7, 2, 2)
        self.assertEqual(k, 5)
        self.assertEqual(motivo, "ajustado")

    def test_inviavel(self):
        self.assertEqual(_k_alvo_diadesorte(1, 7, 2, None)[0], None)


class TestCobertura(unittest.TestCase):
    def test_dez_apostas_cobrem_as_pendentes(self):
        pend = list(range(1, 11))
        scores = {d: float(20 - d) for d in pend}
        combos = _combos_cobertura(pend, 4, scores, 10)
        self.assertGreaterEqual(len(combos), 10)
        usados = set()
        for c in combos:
            self.assertEqual(len(c), 4)
            self.assertEqual(len(set(c)), 4)
            usados.update(c)
        self.assertEqual(usados, set(pend))


class TestDiagonal(unittest.TestCase):
    def test_trinca_conta_uma_vez(self):
        # 02-13-24 é uma trinca ↘ no volante de 10 colunas, não três diagonais.
        diags = diagonais_na_aposta([2, 13, 24, 5, 6, 7, 8])
        chaves = [d["nums"] for d in diags]
        self.assertIn([2, 13, 24], chaves)
        self.assertEqual(len(diags), 1)

    def test_empate_fica_no_mais_baixo(self):
        # 4 sorteios com 1 diagonal e 4 com 2: empate, desempate para 1.
        um = [2, 11, 5, 6, 7, 8, 9]          # uma diagonal: 02-11
        dois = [2, 3, 10, 11, 12, 29, 31]    # duas: 02-11 e 03-12
        res = resumo_contagem_diagonais([um, um, um, um, dois, dois, dois, dois])
        self.assertEqual(res["sugerida"], 1)
        self.assertIn(2, res["empate"])

    def test_planta_sem_tirar_faltante(self):
        jogo = [1, 2, 3, 4, 10, 20, 30]
        novo = _plantar_segmento(jogo, [1, 2, 3, 4], [8, 19], [8, 19, 10, 20, 30], 7)
        self.assertIsNotNone(novo)
        self.assertEqual(len(novo), 7)
        self.assertTrue({1, 2, 3, 4, 8, 19}.issubset(novo))

    def test_nao_planta_pendente_de_fora(self):
        jogo = [1, 2, 3, 4, 10, 20, 30]
        novo = _plantar_segmento(jogo, [1, 2, 3, 4], [8, 19], [10, 20, 30], 7)
        self.assertIsNone(novo)


if __name__ == "__main__":
    unittest.main()
