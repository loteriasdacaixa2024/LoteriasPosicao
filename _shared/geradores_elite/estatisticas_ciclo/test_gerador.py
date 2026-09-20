# -*- coding: utf-8 -*-
import os
import random
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED = os.path.abspath(os.path.join(_HERE, "..", ".."))
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from gerador import (  # noqa: E402
    distribuir_pendentes,
    gerar_apostas_de_contexto,
    quantidade_minima,
)


def _linha(concurso, nums, ant=None):
    pares = [n for n in nums if n % 2 == 0]
    imp = [n for n in nums if n % 2]
    reps = [n for n in nums if ant and n in ant]
    return {
        "concurso": concurso,
        "data": "",
        "numeros": list(nums),
        "pares": {"quantidade": len(pares), "dezenas": pares},
        "impares": {"quantidade": len(imp), "dezenas": imp},
        "repetidos": {"quantidade": len(reps), "dezenas": reps},
        "sequencias": {"quantidade": 0, "dezenas": []},
        "finais": {"quantidade": 0, "dezenas": []},
    }


class TestQuantidadeMinima(unittest.TestCase):
    def test_nao_sobe_quando_cabe(self):
        self.assertEqual(quantidade_minima(5, 7, 10), 10)

    def test_sobe_para_cobrir_todas(self):
        self.assertEqual(quantidade_minima(20, 7, 2), 3)
        self.assertEqual(quantidade_minima(31, 7, 10), 10)


class TestDistribuirPendentes(unittest.TestCase):
    def test_todas_em_cada_quando_cabe(self):
        blocos = distribuir_pendentes([3, 17, 23], 4, 7)
        self.assertEqual(len(blocos), 4)
        for b in blocos:
            self.assertEqual(b, [3, 17, 23])

    def test_cobertura_quando_passa_de_7(self):
        pends = list(range(1, 16))
        blocos = distribuir_pendentes(pends, 10, 7)
        cobertos = set()
        for b in blocos:
            self.assertLessEqual(len(b), 7)
            cobertos.update(b)
        self.assertEqual(cobertos, set(pends))


class TestGerarContexto(unittest.TestCase):
    def setUp(self):
        self.linhas = [
            _linha(1301, [2, 7, 8, 14, 15, 24, 26], [2, 12, 15, 25, 27, 29, 31]),
            _linha(1300, [2, 12, 15, 25, 27, 29, 31]),
        ]
        self.medias = {
            "pares": 3.5,
            "impares": 3.5,
            "repetidos": 1.6,
            "sequencias": 2.1,
            "finais": 2.4,
        }

    def test_aposta_tem_7_distintas_no_universo(self):
        out = gerar_apostas_de_contexto(
            pendentes=[3, 17],
            linhas_basicas=self.linhas,
            medias=self.medias,
            quantidade=5,
        )
        self.assertTrue(out["sucesso"])
        self.assertEqual(len(out["apostas"]), 5)
        for ap in out["apostas"]:
            dez = ap["dezenas"]
            self.assertEqual(len(dez), 7)
            self.assertEqual(len(set(dez)), 7)
            self.assertTrue(all(1 <= n <= 31 for n in dez))
            self.assertEqual(dez, sorted(dez))
            self.assertIn(3, dez)
            self.assertIn(17, dez)

    def test_mais_de_7_pendentes_todas_no_lote(self):
        pends = [1, 3, 5, 9, 11, 13, 17, 19, 21, 23, 27, 29]
        out = gerar_apostas_de_contexto(
            pendentes=pends,
            linhas_basicas=self.linhas,
            medias=self.medias,
            quantidade=10,
        )
        self.assertTrue(out["sucesso"])
        self.assertEqual(out["modo_ciclo"], "cobertura_do_lote")
        self.assertTrue(out["todas_pendentes_no_lote"])
        self.assertEqual(out["pendentes_faltando"], [])
        cobertos = set()
        for ap in out["apostas"]:
            cobertos.update(n for n in ap["dezenas"] if n in pends)
        self.assertEqual(cobertos, set(pends))

    def test_sete_pendentes_nao_repetem_o_mesmo_volante(self):
        pends = [3, 6, 10, 13, 17, 22, 23]
        out = gerar_apostas_de_contexto(
            pendentes=pends,
            linhas_basicas=self.linhas,
            medias=self.medias,
            quantidade=10,
        )
        self.assertEqual(out["modo_ciclo"], "cobertura_do_lote")
        self.assertTrue(out["todas_pendentes_no_lote"])
        volantes = {tuple(ap["dezenas"]) for ap in out["apostas"]}
        self.assertGreater(len(volantes), 1)
        for ap in out["apostas"]:
            self.assertLess(len(ap["obrigatorias"]), 7)

    def test_aumenta_quantidade_para_caber_pendentes(self):
        pends = list(range(1, 22))  # 21 pendentes
        out = gerar_apostas_de_contexto(
            pendentes=pends,
            linhas_basicas=self.linhas,
            medias=self.medias,
            quantidade=2,
        )
        self.assertGreaterEqual(out["quantidade"], 3)
        self.assertTrue(out["quantidade_ajustada"])
        self.assertTrue(out["todas_pendentes_no_lote"])

    def test_aposta_traz_diagonais(self):
        out = gerar_apostas_de_contexto(
            pendentes=[3, 17],
            linhas_basicas=self.linhas,
            medias=self.medias,
            quantidade=3,
        )
        self.assertIn("diagonais", out)
        for ap in out["apostas"]:
            self.assertIn("diagonais", ap)
            self.assertIsInstance(ap["diagonais"], list)

    def test_evita_combinacao_ja_sorteada(self):
        first = gerar_apostas_de_contexto(
            pendentes=[3, 17],
            linhas_basicas=self.linhas,
            medias=self.medias,
            quantidade=3,
            rng=random.Random(7),
        )
        banned = {frozenset(ap["dezenas"]) for ap in first["apostas"]}
        second = gerar_apostas_de_contexto(
            pendentes=[3, 17],
            linhas_basicas=self.linhas,
            medias=self.medias,
            quantidade=3,
            rng=random.Random(7),
            historico=banned,
        )
        for ap in second["apostas"]:
            self.assertNotIn(frozenset(ap["dezenas"]), banned)

    def test_volantes_unicos_e_padroes_distintos(self):
        out = gerar_apostas_de_contexto(
            pendentes=[3, 6, 10, 13, 17, 22, 23],
            linhas_basicas=self.linhas,
            medias=self.medias,
            quantidade=10,
        )
        volantes = [tuple(ap["dezenas"]) for ap in out["apostas"]]
        self.assertEqual(len(volantes), 10)
        self.assertEqual(len(volantes), len(set(volantes)))
        pads = [ap["padrao_inicial"] for ap in out["apostas"]]
        self.assertEqual(len(pads), len(set(pads)))
        self.assertTrue(out["apostas_unicas"])
        self.assertTrue(any(ap["padrao_inedito"] for ap in out["apostas"]))
        self.assertTrue(out.get("padrao_inedito"))

    def test_usa_padrao_inedito_do_catalogo(self):
        cat = [
            {"padrao": "0 0 1 1 2 2 3", "frequencia": 40, "status": "frequente", "atraso": 2},
            {"padrao": "0 1 1 2 2 2 3", "frequencia": 22, "status": "frequente", "atraso": 5},
            {"padrao": "0 0 0 1 2 3 3", "frequencia": 8, "status": "atrasado", "atraso": 40},
            {"padrao": "0 1 1 1 2 3 3", "frequencia": 6, "status": "atrasado", "atraso": 18},
            {"padrao": "0 0 1 2 2 3 3", "frequencia": 5, "status": "atrasado", "atraso": 12},
            {"padrao": "0 1 2 2 2 3 3", "frequencia": 4, "status": "atrasado", "atraso": 9},
            {"padrao": "0 0 1 1 1 2 3", "frequencia": 3, "status": "atrasado", "atraso": 30},
            {"padrao": "0 0 0 2 2 3 3", "frequencia": 2, "status": "atrasado", "atraso": 50},
            {"padrao": "1 1 1 2 2 3 3", "frequencia": 1, "status": "atrasado", "atraso": 70},
            {"padrao": "0 0 0 0 1 2 3", "frequencia": 0, "status": "faltante", "atraso": None},
            {"padrao": "0 0 0 1 1 3 3", "frequencia": 0, "status": "faltante", "atraso": None},
        ]
        out = gerar_apostas_de_contexto(
            pendentes=[3, 17],
            linhas_basicas=self.linhas,
            medias=self.medias,
            quantidade=10,
            catalogo_padroes=cat,
        )
        pads = [ap["padrao_inicial"] for ap in out["apostas"]]
        self.assertEqual(len(pads), len(set(pads)))
        self.assertTrue(any(ap["padrao_inedito"] for ap in out["apostas"]))
        ineditos_cat = {"0 0 0 0 1 2 3", "0 0 0 1 1 3 3"}
        self.assertTrue(set(pads) & ineditos_cat)


if __name__ == "__main__":
    unittest.main()
