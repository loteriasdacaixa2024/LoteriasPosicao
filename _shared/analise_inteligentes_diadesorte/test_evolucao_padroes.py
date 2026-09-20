# -*- coding: utf-8 -*-
"""Testes — índice da aposta vencedora (mesma ordem de expandir_jogos_padrao)."""
from __future__ import annotations

import os
import sys
import unittest

_SHARED = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_APP = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "AnalisePorPosicao--DiaDeSorte-Only"))
for _p in (_APP, _SHARED):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analise_inteligentes_diadesorte.service import (  # noqa: E402
    expandir_jogos_padrao,
    indice_aposta_no_padrao,
    padrao_inicial,
)


class TestIndiceApostaNoPadrao(unittest.TestCase):
    def test_coincide_com_expandir_offset(self):
        pad = "0 0 0 1 1 1 1"
        out = expandir_jogos_padrao(pad, limite=8, offset=120)
        self.assertTrue(out.get("sucesso"))
        self.assertGreaterEqual(len(out["jogos"]), 1)
        for j in out["jogos"]:
            got = indice_aposta_no_padrao(j["dezenas"], pad)
            self.assertEqual(got, j["id"], msg=j["dezenas_fmt"])

    def test_primeiro_e_padrao_derivado(self):
        pad = "0 0 0 0 0 0 3"
        out = expandir_jogos_padrao(pad, limite=3, offset=0)
        j = out["jogos"][0]
        self.assertEqual(indice_aposta_no_padrao(j["dezenas"], pad), 1)
        self.assertEqual(indice_aposta_no_padrao(j["dezenas"]), 1)

    def test_exemplo_conhecido(self):
        dez = [4, 5, 8, 20, 25, 27, 31]
        pad = padrao_inicial(sorted(dez))
        self.assertEqual(pad, "0 0 0 2 2 2 3")
        n = indice_aposta_no_padrao(dez, pad)
        self.assertIsNotNone(n)
        self.assertGreaterEqual(int(n), 1)
        out = expandir_jogos_padrao(pad, limite=1, offset=int(n) - 1)
        self.assertEqual(out["jogos"][0]["dezenas"], sorted(dez))
        self.assertEqual(out["jogos"][0]["id"], n)


if __name__ == "__main__":
    unittest.main()
