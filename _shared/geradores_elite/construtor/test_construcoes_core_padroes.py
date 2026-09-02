# -*- coding: utf-8 -*-
"""Testes pontuais: POOL exclusivo, Padrões II, duplicidade e preço."""
from __future__ import annotations

import importlib.util
import os
import random
import sys
import unittest

_DIR = os.path.dirname(os.path.abspath(__file__))
_SHARED = os.path.abspath(os.path.join(_DIR, "..", ".."))
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from configuracoes.regras_modalidade import formatar_brl, preco_lote


def _load_core():
    path = os.path.join(_DIR, "construcoes_core.py")
    spec = importlib.util.spec_from_file_location("construcoes_core_isolado", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


core = _load_core()
aposta_pertence_ao_pool = core.aposta_pertence_ao_pool
gerar_construcao = core.gerar_construcao
padrao_inicial_de = core.padrao_inicial_de
padrao_viavel = core.padrao_viavel
sugerir_ajuste_pool = core.sugerir_ajuste_pool
_montar_por_padrao = core._montar_por_padrao


class TestPrecoBrl(unittest.TestCase):
    def test_formatar_brl(self):
        self.assertEqual(formatar_brl(0), "R$ 0,00")
        self.assertEqual(formatar_brl(2.5), "R$ 2,50")
        self.assertEqual(formatar_brl(25), "R$ 25,00")
        self.assertEqual(formatar_brl(1980), "R$ 1.980,00")

    def test_preco_lote_dia_de_sorte_7x10(self):
        p = preco_lote("diadesorte", 7, 10)
        self.assertEqual(p["unitario"], 2.5)
        self.assertEqual(p["total"], 25.0)
        self.assertEqual(p["total_fmt"], "R$ 25,00")
        self.assertEqual(p["unitario_fmt"], "R$ 2,50")


class TestPoolExclusivo(unittest.TestCase):
    def test_aposta_fora_do_pool_rejeitada(self):
        pool = [1, 3, 5, 7, 9, 12, 15]
        self.assertTrue(aposta_pertence_ao_pool([1, 3, 5, 7, 9, 12, 15], pool))
        self.assertFalse(aposta_pertence_ao_pool([1, 3, 5, 7, 9, 12, 16], pool))

    def test_montar_por_padrao_so_usa_pool(self):
        pool = [1, 2, 3, 4, 5, 6, 7, 11]
        rng = random.Random(7)
        ap = _montar_por_padrao(pool, [0, 0, 0, 0, 0, 0, 1], rng)
        self.assertIsNotNone(ap)
        self.assertTrue(aposta_pertence_ao_pool(ap, pool))
        self.assertEqual(len(ap), 7)

    def test_montar_por_padrao_insuficiente_retorna_none(self):
        pool = [1, 2, 3]
        rng = random.Random(1)
        ap = _montar_por_padrao(pool, [0, 0, 0, 0, 0, 0, 0], rng)
        self.assertIsNone(ap)


class TestPadroesII(unittest.TestCase):
    def test_a_padroes_desligados_nao_ativam(self):
        pool = list(range(1, 17))
        r = gerar_construcao(
            pool, 7, "automatica",
            padroes_selecionados=None,
            quantidade=10,
            max_tentativas=80,
            seed=11,
            historico_sorteados=set(),
        )
        self.assertTrue(r.get("sucesso"), r.get("erro"))
        self.assertFalse(r.get("padroes_ii_ativos"))
        self.assertEqual(r.get("padroes_ii_usados"), [])
        for ap in r["apostas"]:
            self.assertTrue(aposta_pertence_ao_pool(ap, pool))
            self.assertEqual(len(ap), 7)
        chaves = [frozenset(a) for a in r["apostas"]]
        self.assertEqual(len(chaves), len(set(chaves)))

    def test_b_um_padrao_selecionado(self):
        pool = list(range(1, 17))
        padrao = "0 0 0 0 1 1 1"
        self.assertTrue(padrao_viavel([0, 0, 0, 0, 1, 1, 1], pool))
        r = gerar_construcao(
            pool, 7, "automatica",
            padroes_selecionados=[padrao],
            quantidade=10,
            max_tentativas=120,
            seed=21,
            historico_sorteados=set(),
        )
        self.assertTrue(r.get("sucesso"), r.get("erro"))
        self.assertTrue(r.get("padroes_ii_ativos"))
        for ap in r["apostas"]:
            self.assertEqual(padrao_inicial_de(ap), padrao)
            self.assertTrue(aposta_pertence_ao_pool(ap, pool))
            self.assertEqual(len(ap), 7)

    def test_c_varios_padroes(self):
        pool = list(range(1, 21))
        p1 = "0 0 0 0 1 1 1"
        p2 = "0 0 0 1 1 1 1"
        r = gerar_construcao(
            pool, 7, "automatica",
            padroes_selecionados=[p1, p2],
            quantidade=10,
            max_tentativas=120,
            seed=31,
            historico_sorteados=set(),
        )
        self.assertTrue(r.get("sucesso"), r.get("erro"))
        usados = {padrao_inicial_de(a) for a in r["apostas"]}
        self.assertTrue(usados <= {p1, p2})
        self.assertTrue(p1 in usados or p2 in usados)

    def test_d_pool_suficiente(self):
        pool = [1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13]
        r = gerar_construcao(
            pool, 7, "automatica",
            padroes_selecionados=["0 0 0 0 1 1 1"],
            quantidade=4,
            max_tentativas=80,
            seed=41,
            historico_sorteados=set(),
        )
        self.assertTrue(r.get("sucesso"), r.get("erro"))
        for ap in r["apostas"]:
            self.assertTrue(set(ap) <= set(pool))

    def test_e_pool_insuficiente_nao_completa_fora(self):
        pool = [1, 3, 5, 7, 9, 12, 15]
        r = gerar_construcao(
            pool, 7, "automatica",
            padroes_selecionados=["3 3 3 3 3 3 3"],
            quantidade=1,
            max_tentativas=20,
            seed=51,
            historico_sorteados=set(),
        )
        self.assertFalse(r.get("sucesso"))
        self.assertEqual(r.get("erro_codigo"), "pool_insuficiente")
        self.assertTrue(r.get("oferece_sugestao"))
        self.assertTrue(r.get("padroes_problema"))
        self.assertNotIn("apostas", r)
        sug = r["padroes_problema"][0].get("sugestao") or {}
        self.assertTrue(sug.get("nao_altera_pool"))
        cands = sug.get("dezenas_candidatas") or []
        self.assertTrue(all(d not in pool for d in cands))

    def test_f_duplicidade_total_rejeitada(self):
        pool = [1, 2, 3, 4, 5, 6, 7]
        padrao = "0 0 0 0 0 0 0"
        r1 = gerar_construcao(
            pool, 7, "automatica",
            padroes_selecionados=[padrao],
            quantidade=1,
            max_tentativas=40,
            seed=61,
            historico_sorteados=set(),
        )
        self.assertTrue(r1.get("sucesso"), r1.get("erro"))
        unica = r1["apostas"][0]
        r2 = gerar_construcao(
            pool, 7, "automatica",
            padroes_selecionados=[padrao],
            quantidade=1,
            max_tentativas=30,
            seed=62,
            historico_sorteados=set(),
            apostas_excluidas={frozenset(unica)},
        )
        self.assertFalse(r2.get("sucesso"))
        self.assertEqual(r2.get("erro_codigo"), "duplicidade_total")

    def test_g_igualdade_parcial_permitida(self):
        pool = list(range(1, 10))
        r = gerar_construcao(
            pool, 7, "automatica",
            padroes_selecionados=["0 0 0 0 0 0 0"],
            quantidade=3,
            max_tentativas=80,
            seed=71,
            historico_sorteados=set(),
        )
        self.assertTrue(r.get("sucesso"), r.get("erro"))
        sets = [frozenset(a) for a in r["apostas"]]
        self.assertEqual(len(sets), len(set(sets)))
        inter = sets[0] & sets[1]
        self.assertTrue(len(inter) < 7)
        self.assertGreater(len(inter), 0)

    def test_sugestao_nao_altera_pool(self):
        pool = [1, 2, 3, 4, 5, 6, 7]
        sug = sugerir_ajuste_pool(pool, [3, 3, 3, 3, 3, 3, 3], list(range(1, 32)))
        self.assertTrue(sug["nao_altera_pool"])
        self.assertEqual(pool, [1, 2, 3, 4, 5, 6, 7])


if __name__ == "__main__":
    unittest.main()
