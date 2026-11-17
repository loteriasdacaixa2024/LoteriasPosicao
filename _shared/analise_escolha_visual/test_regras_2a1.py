# -*- coding: utf-8 -*-
"""Regras da 2A1 e o endereço da sequência no Panorama."""
from __future__ import annotations

import os
import sys
import unittest

_SHARED = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_APP = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "AnalisePorPosicao--DiaDeSorte-Only"))
for _p in (_APP, _SHARED):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analise_escolha_visual.enriquecimento.regras_2a1 import (  # noqa: E402
    montar_linha_2a1,
    montar_restricoes,
    viola_restricoes,
)
from analise_inteligentes_diadesorte.sequencias_sorteadas import (  # noqa: E402
    dezenas_na_sequencia,
    mapa_sequencia_no_padrao,
)
from analise_inteligentes_diadesorte.service import expandir_jogos_padrao  # noqa: E402
from analise_inteligentes_diadesorte.soma_media import calcular_faixa_soma  # noqa: E402


class TestLinha2A1(unittest.TestCase):
    def test_pares_e_impares_sao_os_que_nao_sairam_neste_concurso(self):
        anterior = [16, 6, 19, 27, 4, 5, 28]
        atual = [5, 9, 15, 2, 14, 25, 7]
        linha = montar_linha_2a1(atual, anterior)
        self.assertEqual(linha["pares"], [4, 6, 8, 10, 12, 16, 18, 20, 22, 24, 26, 28, 30])
        self.assertEqual(linha["impares"], [1, 3, 11, 13, 17, 19, 21, 23, 27, 29, 31])

    def test_concurso_1348_mantem_par_e_impar_que_so_sairam_antes(self):
        # 25 02 23 18 11 01 07. 05, 09, 14 e 15 não saíram neste sorteio.
        atual = [25, 2, 23, 18, 11, 1, 7]
        anterior = [5, 9, 14, 15, 4, 8, 20]
        linha = montar_linha_2a1(atual, anterior)
        self.assertEqual(
            linha["pares"],
            [4, 6, 8, 10, 12, 14, 16, 20, 22, 24, 26, 28, 30],
        )
        self.assertEqual(
            linha["impares"],
            [3, 5, 9, 13, 15, 17, 19, 21, 27, 29, 31],
        )

    def test_repetidos_continuam_os_do_proprio_concurso(self):
        linha = montar_linha_2a1([6, 8, 10, 12, 14, 18, 20], [4, 6, 9, 16, 27, 28, 5])
        self.assertEqual(linha["repetidos"], [6])

    def test_sequencia_final_e_diagonal_vem_do_anterior(self):
        anterior = [4, 5, 6, 9, 16, 27, 28]
        linha = montar_linha_2a1([1, 2, 3, 8, 10, 12, 14], anterior)
        self.assertIn([4, 5, 6], linha["sequencias"])
        self.assertIn([27, 28], linha["sequencias"])
        self.assertIn([6, 16], linha["finais"])

    def test_gerador_bloqueia_repetido_e_sequencia_exata(self):
        restr = montar_restricoes([4, 5, 6, 9, 16, 27, 28], [6, 8, 10, 12, 14, 18, 20])
        self.assertEqual(restr["repetidos_proibidos"], [6])
        self.assertIn(4, restr["pode_repetir"])
        self.assertIsNotNone(viola_restricoes([2, 3, 6, 8, 10, 12, 14], restr))
        self.assertIsNotNone(viola_restricoes([4, 5, 6, 8, 10, 12, 14], restr))
        self.assertIsNone(viola_restricoes([2, 3, 4, 8, 10, 12, 14], restr))
        self.assertIsNone(viola_restricoes([5, 7, 8, 10, 12, 14, 15], restr))


class TestEnderecoSequencia(unittest.TestCase):
    def test_numero_da_sequencia_volta_para_as_mesmas_dezenas(self):
        pad = "0 0 0 0 0 0 3"
        jogos = expandir_jogos_padrao(pad, min_dezena=1, max_dezena=31)["jogos"]
        faixa = calcular_faixa_soma([j["soma"] for j in jogos[::5]], fonte="historico")
        alvos = [j["dezenas"] for j in jogos[::9]]
        ranks = mapa_sequencia_no_padrao(pad, alvos, faixa, min_dezena=1, max_dezena=31)
        for dez in alvos:
            n = ranks[tuple(dez)]
            got = dezenas_na_sequencia(pad, n, faixa, min_dezena=1, max_dezena=31)
            self.assertEqual(got, list(dez))


if __name__ == "__main__":
    unittest.main()
