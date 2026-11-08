# -*- coding: utf-8 -*-
"""Ciclo, recorrência e veredito do Engine Final — sem gerar contra o banco."""
from __future__ import annotations

import importlib.util
import os
import unittest

_AQUI = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "engine_final_sintonia",
    os.path.join(_AQUI, "engine_final_sintonia.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

_cortar_universo = _mod.cortar_universo
_padrao_cabe_no_pool = _mod.padrao_cabe_no_pool
aplicar_trava = _mod.aplicar_trava
hora_do_padrao = _mod.hora_do_padrao
padroes_na_hora = _mod.padroes_na_hora
resolver_ciclo = _mod.resolver_ciclo


class TestCiclo(unittest.TestCase):
    def test_sem_pendente_nao_opina(self):
        info = resolver_ciclo([], 7, 1, 31)
        self.assertEqual(info["modo"], "livre")
        self.assertEqual(info["veredito"], "nao_opina")
        self.assertEqual(info["locked"], [])
        self.assertEqual(len(info["universo"]), 31)

    def test_fim_de_ciclo_trava_todas(self):
        info = resolver_ciclo([2, 7, 11, 30], 7, 1, 31)
        self.assertEqual(info["modo"], "travar")
        self.assertEqual(info["veredito"], "cabe")
        self.assertEqual(info["locked"], [2, 7, 11, 30])
        self.assertEqual(info["universo"], list(range(1, 32)))

    def test_comeco_de_ciclo_recorte(self):
        pend = list(range(1, 15))
        info = resolver_ciclo(pend, 7, 1, 31)
        self.assertEqual(info["modo"], "recorte")
        self.assertEqual(info["veredito"], "cabe")
        self.assertEqual(info["locked"], [])
        self.assertEqual(info["universo"], pend)


class TestRecorrencia(unittest.TestCase):
    def test_na_hora_exclui_quem_acabou_de_sair(self):
        agora = hora_do_padrao(
            {"intervalo_medio": 10, "ultimo_concurso": 90, "desde_ultima": 0},
            100,
        )
        self.assertFalse(agora["na_hora"])
        self.assertTrue(agora["agora"])

    def test_na_hora_dentro_da_margem(self):
        hora = hora_do_padrao(
            {"intervalo_medio": 10.2, "ultimo_concurso": 90, "desde_ultima": 10},
            100,
        )
        self.assertEqual(hora["hora_alvo"], 100)
        self.assertTrue(hora["na_hora"])

    def test_fora_da_margem(self):
        hora = hora_do_padrao(
            {"intervalo_medio": 20, "ultimo_concurso": 70, "desde_ultima": 30},
            100,
        )
        self.assertEqual(hora["hora_falta"], -10)
        self.assertFalse(hora["na_hora"])

    def test_trava_exige_casa_para_cada_pendente(self):
        self.assertTrue(_padrao_cabe_no_pool("0 0 1 1 2 2 3", [1, 2, 11], 7, True))
        self.assertFalse(_padrao_cabe_no_pool("0 0 1 1 2 2 3", [1, 2, 3], 7, True))

    def test_recorte_so_monta_com_o_pool(self):
        self.assertFalse(_padrao_cabe_no_pool("0 0 1 1 2 2 3", [1, 11, 21, 31], 7, False))
        pool = [1, 2, 3, 11, 12, 21, 22, 31]
        self.assertTrue(_padrao_cabe_no_pool("0 0 1 1 2 2 3", pool, 7, False))

    def test_filtra_hora_e_ciclo(self):
        padroes = [
            {"padrao": "0 0 1 1 2 2 3", "intervalo_medio": 10, "ultimo_concurso": 90, "desde_ultima": 10, "descricao": "cabe"},
            {"padrao": "0 0 0 1 1 2 2", "intervalo_medio": 10, "ultimo_concurso": 90, "desde_ultima": 10, "descricao": "tres zeros"},
            {"padrao": "1 1 1 2 2 2 3", "intervalo_medio": 10, "ultimo_concurso": 90, "desde_ultima": 0, "descricao": "acabou de sair"},
        ]
        # duas pendentes na casa 0: o segundo padrão cabe na trava, o primeiro também
        # o terceiro está na hora matemática, mas desde_ultima 0
        escolhidos, n_hora = padroes_na_hora(padroes, 100, [1, 2], 7, True)
        self.assertEqual(n_hora, 2)
        self.assertEqual(
            sorted(p["padrao"] for p in escolhidos),
            ["0 0 0 1 1 2 2", "0 0 1 1 2 2 3"],
        )


class TestTrava(unittest.TestCase):
    def test_aplica_pendentes_e_completa(self):
        jogo = aplicar_trava([8, 9, 10, 11, 12, 13, 14], [2, 7], list(range(1, 32)), 7)
        self.assertEqual(len(jogo), 7)
        self.assertIn(2, jogo)
        self.assertIn(7, jogo)

    def test_recorte_nao_sai_do_universo(self):
        universo = [1, 2, 3, 4, 5, 6, 7, 8, 9]
        jogo = aplicar_trava([1, 2, 20, 21, 22, 23, 24], [], universo, 7)
        self.assertEqual(len(jogo), 7)
        self.assertTrue(all(n in universo for n in jogo))

    def test_conjunto_que_nao_tem_a_trava_sai(self):
        leitura = {
            "universo": list(range(1, 32)),
            "locked": [2, 7],
            "ciclo_modo": "travar",
            "k_historico": 7,
        }
        universo, locked, rejeitado = _cortar_universo(leitura, [10, 11, 12, 13, 14, 15, 16])
        self.assertTrue(rejeitado)
        self.assertEqual(locked, [2, 7])
        self.assertEqual(universo, list(range(1, 32)))

    def test_conjunto_que_cabe_entra_na_intersecao(self):
        leitura = {
            "universo": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "locked": [],
            "ciclo_modo": "recorte",
            "k_historico": 7,
        }
        universo, _locked, rejeitado = _cortar_universo(leitura, [1, 2, 3, 4, 5, 6, 7, 30])
        self.assertFalse(rejeitado)
        self.assertEqual(universo, [1, 2, 3, 4, 5, 6, 7])


if __name__ == "__main__":
    unittest.main()
