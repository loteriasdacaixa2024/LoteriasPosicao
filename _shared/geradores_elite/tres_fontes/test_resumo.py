# -*- coding: utf-8 -*-
import os
import random
import sys
import unittest

_SHARED = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from geradores_elite.estatisticas_ciclo.gerador_panorama import _sementes_ponderadas  # noqa: E402
from geradores_elite.tres_fontes.service import resumir_sequencias  # noqa: E402


def _row(conc, padrao, status, seq=1):
    return {
        "concurso": conc,
        "padrao": padrao,
        "status_media": status,
        "status_media_label": status,
        "sequencia_n": seq,
        "jogos_possiveis": 10,
        "soma": 100,
        "media": 100,
        "dezenas_fmt": "01 02 03 04 05 06 07",
        "descricao": "teste",
        "n_padrao": 1,
    }


class ResumoSequenciasTest(unittest.TestCase):
    def test_conta_status_e_recentes(self):
        linhas = [
            _row(1, "0 0 1 1 2 2 3", "dentro"),
            _row(2, "0 0 1 1 2 2 3", "fora"),
            _row(3, "1 1 1 2 2 2 3", "proxima", seq=4),
        ]
        out = resumir_sequencias(linhas, recentes=2, top=2)
        self.assertEqual(out["total"], 3)
        self.assertEqual(out["status"]["dentro"], 1)
        self.assertEqual(out["status"]["fora"], 1)
        self.assertEqual(out["top_padroes"][0]["padrao"], "0 0 1 1 2 2 3")
        self.assertEqual(out["top_padroes"][0]["frequencia"], 2)
        self.assertEqual([r["concurso"] for r in out["recentes"]], [3, 2])


class SementesPonderadasTest(unittest.TestCase):
    def test_prefere_padrao_frequente_dentro_da_media(self):
        linhas = []
        for i in range(30):
            linhas.append(_row(i + 1, "0 0 1 1 2 2 3", "dentro", seq=i + 1))
        for i in range(4):
            linhas.append(_row(100 + i, "2 2 2 2 2 2 3", "fora", seq=i + 1))
        rng = random.Random(7)
        seeds = _sementes_ponderadas(linhas, 6, rng)
        pads = [s["padrao"] for s in seeds]
        self.assertGreaterEqual(pads.count("0 0 1 1 2 2 3"), 4)
        self.assertEqual(len({(s["padrao"], s["sequencia_n"]) for s in seeds}), len(seeds))
        self.assertTrue(all(int(s["frequencia"]) >= 4 for s in seeds if s["padrao"].startswith("0")))


if __name__ == "__main__":
    unittest.main()
