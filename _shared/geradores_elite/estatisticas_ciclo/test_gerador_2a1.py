# -*- coding: utf-8 -*-
"""O lote 2A1 nasce do padrão e da sequência, já dentro das restrições."""
from __future__ import annotations

import os
import random
import sys
import unittest

_SHARED = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_APP = os.path.abspath(os.path.join(_SHARED, "..", "AnalisePorPosicao--DiaDeSorte-Only"))
for _p in (_APP, _SHARED):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analise_escolha_visual.enriquecimento.regras_2a1 import viola_restricoes  # noqa: E402
from analise_inteligentes_diadesorte.sequencias_sorteadas import dezenas_na_sequencia  # noqa: E402
from analise_inteligentes_diadesorte.service import (  # noqa: E402
    descricao_bma_do_padrao,
    jogos_possiveis_padrao,
    padrao_inicial,
)
from gerador_2a1 import gerar_lote_2a1  # noqa: E402


class TestGerador2A1(unittest.TestCase):
    def test_apostas_respeitam_repetido_sequencia_e_quantidade(self):
        pad = "0 0 1 1 2 2 3"
        faixa = {"media": 90, "tol_dentro": 6, "tol_proxima": 12}
        jogos = jogos_possiveis_padrao(pad, min_dezena=1, max_dezena=31)
        linhas = []
        for i, seq in enumerate((400, 900, 1500, 2200), start=1):
            dez = dezenas_na_sequencia(pad, seq, faixa, min_dezena=1, max_dezena=31)
            self.assertIsNotNone(dez)
            linhas.append({
                "concurso": i,
                "padrao": pad,
                "sequencia_n": seq,
                "jogos_possiveis": jogos,
                "media": 90,
                "soma": sum(dez),
                "dezenas": dez,
                "descricao": descricao_bma_do_padrao(pad),
            })
        ultimo = [2, 5, 14, 19, 22, 28, 31]
        penultimo = [2, 8, 11, 16, 21, 25, 30]
        pendentes = [n for n in range(1, 32) if n != 2]
        out = gerar_lote_2a1(
            catalogo=[{
                "padrao": pad,
                "frequencia": 8,
                "jogos_possiveis": jogos,
                "descricao": descricao_bma_do_padrao(pad),
            }],
            linhas_panorama=linhas,
            ultimo=ultimo,
            penultimo=penultimo,
            pendentes=pendentes,
            historico=[tuple(sorted(row["dezenas"])) for row in linhas],
            quantidade=4,
            repetidos="1-2",
            rng=random.Random(7),
        )
        self.assertTrue(out.get("sucesso"), out.get("erro"))
        self.assertGreaterEqual(len(out["apostas"]), 1)
        restr = out["restricoes"]
        self.assertEqual(restr["repetidos_proibidos"], [2])
        for ap in out["apostas"]:
            dez = ap["dezenas"]
            self.assertEqual(len(dez), 7)
            self.assertNotIn(2, dez)
            self.assertEqual(padrao_inicial(dez), pad)
            self.assertIsNone(viola_restricoes(dez, restr))
            reps = [n for n in dez if n in set(ultimo)]
            self.assertLessEqual(len(reps), 2)
            self.assertIn("justificativa", ap)
            self.assertTrue(ap["justificativa"])

    def test_fim_de_ciclo_abre_pool_e_mantem_pendente(self):
        pad = "0 0 1 1 2 2 3"
        faixa = {"media": 90, "tol_dentro": 6, "tol_proxima": 12}
        jogos = jogos_possiveis_padrao(pad, min_dezena=1, max_dezena=31)
        linhas = []
        for i, seq in enumerate((400, 900, 1500, 2200), start=1):
            dez = dezenas_na_sequencia(pad, seq, faixa, min_dezena=1, max_dezena=31)
            linhas.append({
                "concurso": i,
                "padrao": pad,
                "sequencia_n": seq,
                "jogos_possiveis": jogos,
                "media": 90,
                "soma": sum(dez),
                "dezenas": dez,
                "descricao": descricao_bma_do_padrao(pad),
            })
        ultimo = [5, 9, 15, 2, 14, 25, 7]
        out = gerar_lote_2a1(
            catalogo=[{
                "padrao": pad,
                "frequencia": 8,
                "jogos_possiveis": jogos,
                "descricao": descricao_bma_do_padrao(pad),
            }],
            linhas_panorama=linhas,
            ultimo=ultimo,
            penultimo=[4, 5, 6, 16, 19, 27, 28],
            pendentes=[30],
            historico=[tuple(sorted(row["dezenas"])) for row in linhas],
            quantidade=2,
            repetidos="1-2",
            rng=random.Random(3),
        )
        self.assertTrue(out.get("sucesso"), out.get("erro"))
        self.assertTrue(out.get("pool_ampliado"))
        self.assertTrue(out.get("ciclo_fim"))
        for ap in out["apostas"]:
            self.assertIn(30, ap["dezenas"])
            self.assertNotIn(5, ap["dezenas"])
            reps = [n for n in ap["dezenas"] if n in set(ultimo)]
            self.assertGreaterEqual(len(reps), 1)
            self.assertLessEqual(len(reps), 2)


if __name__ == "__main__":
    unittest.main()
