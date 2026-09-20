# -*- coding: utf-8 -*-
"""Testes — Checagem de Sequências (parse, prefixo, sugestão)."""
from __future__ import annotations

import os
import sys
import unittest

_SHARED = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from analise_inteligentes_diadesorte.checagem_sequencias import (  # noqa: E402
    expandir_jogos_contendo,
    montar_resultado_linha,
    padrao_inicial,
    parse_linha_aposta,
    parse_lote_apostas,
    sugerir_proxima,
)
from analise_inteligentes_diadesorte.diagonais_volante import diagonais_na_aposta  # noqa: E402
from analise_inteligentes_diadesorte.soma_media import classificar_soma  # noqa: E402


class TestParseAposta(unittest.TestCase):
    def test_linha_com_mes_dez(self):
        r = parse_linha_aposta("02 05 07 08 21 22 24 Dez")
        self.assertTrue(r["ok"])
        self.assertEqual(r["dezenas"], [2, 5, 7, 8, 21, 22, 24])
        self.assertEqual(r["dezenas_fmt"], "02 05 07 08 21 22 24")
        self.assertEqual(r["padrao"], "0 0 0 0 2 2 2")
        self.assertEqual(r["mes_num"], 12)
        self.assertEqual(r["mes_colado"].lower()[:3], "dez")

    def test_linha_sem_mes(self):
        r = parse_linha_aposta("02 05 07 08 21 22 24")
        self.assertTrue(r["ok"])
        self.assertIsNone(r["mes_num"])

    def test_dezena_repetida(self):
        r = parse_linha_aposta("02 05 07 08 21 21 24")
        self.assertFalse(r["ok"])

    def test_lote_duas_linhas(self):
        txt = "02 05 07 08 21 22 24 Dez\n01 03 06 09 20 23 25 Jan"
        r = parse_lote_apostas(txt)
        self.assertTrue(r["ok"])
        self.assertEqual(len(r["apostas"]), 2)
        self.assertEqual(r["apostas"][1]["mes_num"], 1)


class TestPrefixoESugestao(unittest.TestCase):
    def test_padrao_do_exemplo(self):
        self.assertEqual(padrao_inicial([2, 5, 7, 8, 21, 22, 24]), "0 0 0 0 2 2 2")

    def test_expandir_contem_exata(self):
        jogos = expandir_jogos_contendo(
            "0 0 0 0 2 2 2", [2, 5, 7, 8, 21],
            min_dezena=1, max_dezena=31, tamanho_jogo=7,
        )
        fmts = {j["dezenas_fmt"] for j in jogos}
        self.assertIn("02 05 07 08 21 22 24", fmts)
        self.assertIn("02 05 07 08 21 22 23", fmts)

    def test_sugere_mais_proxima(self):
        alvo = [2, 5, 7, 8, 21, 22, 23]
        cands = [
            {"dezenas": [2, 5, 7, 8, 21, 22, 27], "dezenas_fmt": "02 05 07 08 21 22 27", "soma": 92},
            {"dezenas": [2, 5, 7, 8, 21, 22, 24], "dezenas_fmt": "02 05 07 08 21 22 24", "soma": 89},
            {"dezenas": [2, 5, 7, 8, 21, 22, 29], "dezenas_fmt": "02 05 07 08 21 22 29", "soma": 94},
        ]
        sug = sugerir_proxima(alvo, cands, 5)
        self.assertIsNotNone(sug)
        self.assertEqual(sug["dezenas_fmt"], "02 05 07 08 21 22 24")

    def test_resultado_exata_existe(self):
        aposta = parse_linha_aposta("02 05 07 08 21 22 24 Dez")
        aposta["linha"] = 1
        jogos = [
            {
                "dezenas": [2, 5, 7, 8, 21, 22, 24],
                "dezenas_fmt": "02 05 07 08 21 22 24",
                "soma": 89,
                "status_media": "dentro",
                "status_media_label": "Dentro da média",
            },
            {
                "dezenas": [2, 5, 7, 8, 21, 22, 27],
                "dezenas_fmt": "02 05 07 08 21 22 27",
                "soma": 92,
                "status_media": "dentro",
                "status_media_label": "Dentro da média",
            },
        ]
        out = montar_resultado_linha(
            aposta, prefixo_n=5, filtro="dentro_novos",
            jogos_enriquecidos=jogos, historico_keys=set(),
        )
        self.assertTrue(out["existe_exata"])
        self.assertIsNone(out["sugestao"])
        self.assertTrue(all(u["existe"] for u in out["ultimas"]))

    def test_resultado_sugere_quando_falta(self):
        aposta = parse_linha_aposta("02 05 07 08 21 22 23")
        aposta["linha"] = 1
        jogos = [
            {
                "dezenas": [2, 5, 7, 8, 21, 22, 24],
                "dezenas_fmt": "02 05 07 08 21 22 24",
                "soma": 89,
                "status_media": "dentro",
                "status_media_label": "Dentro da média",
            },
        ]
        out = montar_resultado_linha(
            aposta, prefixo_n=5, filtro="dentro_novos",
            jogos_enriquecidos=jogos, historico_keys=set(),
        )
        self.assertFalse(out["existe_exata"])
        self.assertEqual(out["sugestao"]["dezenas_fmt"], "02 05 07 08 21 22 24")
        ult = {u["dezena"]: u["existe"] for u in out["ultimas"]}
        self.assertTrue(ult[22])
        self.assertFalse(ult[23])

    def test_soma_e_diagonais_na_linha(self):
        aposta = parse_linha_aposta("01 04 12 15 23 26 31")
        aposta["linha"] = 1
        faixa = {"media": 112, "tol_dentro": 4, "tol_proxima": 8}
        out = montar_resultado_linha(
            aposta, prefixo_n=5, filtro="dentro_novos",
            jogos_enriquecidos=[], historico_keys=set(), faixa=faixa,
        )
        self.assertEqual(out["soma"], 112)
        self.assertEqual(out["status_media"], "dentro")
        self.assertGreaterEqual(out["n_diagonais"], 2)
        fmts = {d["nums_fmt"] for d in out["diagonais"]}
        self.assertTrue({"01-12-23", "04-15-26"} <= fmts)

    def test_diagonais_duas_no_volante(self):
        diags = diagonais_na_aposta([1, 4, 12, 15, 23, 26, 31])
        fmts = {d["nums_fmt"] for d in diags}
        self.assertGreaterEqual(len(diags), 2)
        self.assertIn("01-12-23", fmts)
        self.assertIn("04-15-26", fmts)
        cls = classificar_soma(112, {"media": 112, "tol_dentro": 4, "tol_proxima": 8})
        self.assertEqual(cls["status_media"], "dentro")


if __name__ == "__main__":
    unittest.main()
