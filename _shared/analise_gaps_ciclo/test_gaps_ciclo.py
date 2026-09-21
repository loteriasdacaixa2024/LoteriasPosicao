# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sys
import unittest
import unittest.mock

_SHARED = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from analise_gaps_ciclo.core import (
    analisar_regua_combinacoes,
    combinacoes_regua,
    deslocamentos_regua,
    gaps_de,
    gaps_sequencia,
    montar_por_ciclos,
    montar_ranking_comparativo,
    parse_padrao_gaps,
    viavel,
)
from analise_gaps_ciclo.gerador import gerar_apostas
from analise_gaps_ciclo.specs import get_gaps_ciclo_spec


class TestCoreGaps(unittest.TestCase):
    def test_exemplo_spec(self):
        self.assertEqual(gaps_de([1, 3, 7, 11, 15, 20, 29]), [2, 4, 4, 4, 5, 9])

    def test_ordem_sorteio_com_sinal(self):
        # mesma dezenas, ordem diferente da classificada
        ordem = [20, 7, 11, 29, 15, 22, 23]
        self.assertEqual(gaps_sequencia(ordem), [-13, 4, 18, -14, 7, 1])
        self.assertEqual(gaps_de(ordem), [4, 4, 5, 2, 1, 6])
        self.assertNotEqual(gaps_sequencia(ordem), gaps_de(ordem))

    def test_sorteio_ja_classificado_coincide(self):
        seq = [7, 11, 15, 20, 22, 23, 29]
        self.assertEqual(gaps_sequencia(seq), gaps_de(seq))

    def test_parse_gap_negativo(self):
        self.assertEqual(parse_padrao_gaps("-13 4 18 -14 7 1"), [-13, 4, 18, -14, 7, 1])

    def test_ranking_comparativo_bonus_ambos(self):
        from collections import Counter
        rank = montar_ranking_comparativo(
            Counter({"2 4 4": 3, "1 1 1": 5}),
            Counter({"2 4 4": 2, "9 1 1": 4}),
        )
        self.assertEqual(rank[0]["padrao"], "2 4 4")
        self.assertTrue(rank[0]["em_ambos"])
        self.assertEqual(rank[0]["fonte"], "ambos")
        self.assertEqual(rank[0]["score"], 3 + 2 + 2)

    def test_progressao_posicao_a_posicao(self):
        # 07 11 15 20 22 23 29 → ciclos 4,4,5,2,1,6
        ciclos = gaps_de([7, 11, 15, 20, 22, 23, 29])
        self.assertEqual(ciclos, [4, 4, 5, 2, 1, 6])
        ap = montar_por_ciclos(2, ciclos, dezena_min=1, dezena_max=31)
        self.assertEqual(ap, [2, 6, 10, 15, 17, 18, 24])

    def test_estouro_invalida(self):
        self.assertIsNone(montar_por_ciclos(28, [4, 4, 4, 4, 4, 4], dezena_min=1, dezena_max=31))


class TestRegua(unittest.TestCase):
    def test_exemplo_posicao_1_seis_acima(self):
        jogo = [10, 14, 18, 22, 26, 30, 31]
        self.assertEqual(gaps_de(jogo), [4, 4, 4, 4, 4, 1])
        refs = [4, 8, 12, 16, 20, 24, 25]
        deltas = deslocamentos_regua(jogo, refs)
        self.assertEqual(deltas[0], 6)
        self.assertEqual(deltas, [6, 6, 6, 6, 6, 6, 6])
        self.assertEqual(gaps_de(jogo), gaps_de(refs))

    def test_moda_e_conjunto_deslocado(self):
        ref = [4, 8, 12, 16, 20, 24, 25]
        jogo = [10, 14, 18, 22, 26, 30, 31]
        out = analisar_regua_combinacoes([jogo, ref, ref])
        self.assertEqual(out["referencias"][0]["referencia"], 4)
        self.assertEqual(out["referencias"][0]["vezes"], 2)
        ult = out["ultimo"]
        self.assertEqual(ult["posicoes"][0]["deslocamento"], 6)
        self.assertEqual(ult["posicoes"][0]["sentido"], "acima")
        self.assertTrue(ult["conjunto_uniforme"])
        self.assertEqual(ult["deslocamento_conjunto"], 6)
        self.assertEqual(len(out["linhas"]), 3)

    def test_empate_de_moda_escolhe_menor(self):
        a = [7, 11, 15, 20, 22, 23, 29]
        b = [4, 11, 15, 20, 22, 23, 29]
        out = analisar_regua_combinacoes([a, b])
        self.assertEqual(out["referencias"][0]["referencia"], 4)
        self.assertEqual(out["referencias"][0]["vezes"], 1)

    def test_combinacao_regua_e_a_moda(self):
        ref = [4, 8, 12, 16, 20, 24, 25]
        jogo = [10, 14, 18, 22, 26, 30, 31]
        self.assertEqual(combinacoes_regua([jogo, ref, ref], quantidade=1), [ref])


class TestSpecInicial(unittest.TestCase):
    def test_diadesorte_exclui_27_a_31(self):
        spec = get_gaps_ciclo_spec("diadesorte")
        self.assertEqual(spec["inicial_min"], 1)
        self.assertEqual(spec["inicial_max"], 26)
        self.assertNotIn(27, spec["iniciais_permitidas"])
        self.assertNotIn(31, spec["iniciais_permitidas"])
        self.assertIn(1, spec["iniciais_permitidas"])
        self.assertIn(10, spec["iniciais_permitidas"])
        self.assertIn(26, spec["iniciais_permitidas"])

    def test_viavel_requer_k(self):
        self.assertTrue(viavel(1, [1, 1, 1, 1, 1, 1], dezena_min=1, dezena_max=31, sorteadas=7))


_GAPS_MOCK = {
    "sucesso": True,
    "top_padroes": [
        {"padrao": "1 1 1 1 1 1", "gaps": [1, 1, 1, 1, 1, 1], "frequencia": 10},
        {"padrao": "2 2 2 2 2 2", "gaps": [2, 2, 2, 2, 2, 2], "frequencia": 4},
    ],
    "ultimo": {"gaps": [4, 4, 5, 2, 1, 6]},
    "moda_por_passo": [{"passo": i + 1, "moda": 3, "vezes": 2} for i in range(6)],
    "linhas": [
        {"dezenas_classificado": [4, 8, 12, 16, 20, 24, 25]},
        {"dezenas_classificado": [4, 8, 12, 16, 20, 24, 25]},
    ],
}
_REGUA = [4, 8, 12, 16, 20, 24, 25]


class TestGeradorSessoes(unittest.TestCase):
    def test_nenhuma_sessao(self):
        out = gerar_apostas("diadesorte", sessao1=False, sessao2=False, inicial=2)
        self.assertFalse(out.get("ok"))

    @unittest.mock.patch("analise_gaps_ciclo.gerador._analisar_gaps", return_value=_GAPS_MOCK)
    def test_sessao2_nao_exige_inicial(self, _m):
        out = gerar_apostas("diadesorte", sessao1=False, sessao2=True, inicial=None)
        self.assertTrue(out.get("ok"))
        self.assertEqual(out["apostas"][0]["dezenas"], _REGUA)

    def test_inicial_alta_bloqueada(self):
        out = gerar_apostas(
            "diadesorte", sessao1=True, sessao2=False, inicial=27,
            padrao="1 1 1 1 1 1",
        )
        self.assertFalse(out.get("ok"))

    @unittest.mock.patch("analise_gaps_ciclo.gerador._analisar_gaps", return_value=_GAPS_MOCK)
    def test_somente_sessao1(self, _m):
        out = gerar_apostas("diadesorte", sessao1=True, sessao2=False, inicial=2, quantidade=3)
        self.assertTrue(out.get("ok"))
        self.assertEqual(out["sessoes"], {"gaps": True, "regua": False})
        self.assertEqual(out["apostas"][0]["dezenas"], [2, 3, 4, 5, 6, 7, 8])
        self.assertNotEqual(out["apostas"][0]["dezenas"], [2, 6, 10, 15, 17, 18, 24])

    @unittest.mock.patch("analise_gaps_ciclo.gerador._analisar_gaps", return_value=_GAPS_MOCK)
    def test_somente_sessao2(self, _m):
        out = gerar_apostas(
            "diadesorte", sessao1=False, sessao2=True, inicial=2, perfil="ultimo",
        )
        self.assertTrue(out.get("ok"))
        self.assertEqual(out["sessoes"], {"gaps": False, "regua": True})
        self.assertEqual(out["apostas"][0]["dezenas"], _REGUA)
        self.assertEqual(out["apostas"][0]["origem"], "regua")

    @unittest.mock.patch("analise_gaps_ciclo.gerador._analisar_gaps", return_value=_GAPS_MOCK)
    def test_duas_sessoes(self, _m):
        out = gerar_apostas("diadesorte", sessao1=True, sessao2=True, inicial=2, quantidade=2)
        self.assertTrue(out.get("ok"))
        self.assertEqual(out["sessoes"], {"gaps": True, "regua": True})
        self.assertEqual(out["apostas"][1]["dezenas"], _REGUA)
        self.assertEqual(out["apostas"][0]["inicial"], 2)
        self.assertEqual(out["apostas"][0]["dezenas"], [2, 3, 4, 5, 6, 7, 8])

    @unittest.mock.patch("analise_gaps_ciclo.gerador._analisar_gaps", return_value=_GAPS_MOCK)
    def test_troca_inicial_recalcula(self, _m):
        a = gerar_apostas("diadesorte", sessao1=False, sessao2=True, inicial=2)
        b = gerar_apostas("diadesorte", sessao1=False, sessao2=True, inicial=5)
        self.assertEqual(a["apostas"][0]["dezenas"], _REGUA)
        self.assertEqual(b["apostas"][0]["dezenas"], _REGUA)

    @unittest.mock.patch("analise_gaps_ciclo.gerador._analisar_gaps", return_value=_GAPS_MOCK)
    def test_sessao1_desligada_nao_usa_top_padroes(self, _m):
        out = gerar_apostas("diadesorte", sessao1=False, sessao2=True, inicial=2, perfil="ultimo")
        dezenas = [tuple(a["dezenas"]) for a in out["apostas"]]
        self.assertNotIn((2, 3, 4, 5, 6, 7, 8), dezenas)

    @unittest.mock.patch("analise_gaps_ciclo.gerador._analisar_gaps", return_value=_GAPS_MOCK)
    def test_sessao2_desligada_nao_trava_no_ciclo_ultimo(self, _m):
        out = gerar_apostas("diadesorte", sessao1=True, sessao2=False, inicial=2, quantidade=1)
        self.assertNotEqual(out["apostas"][0]["dezenas"], [2, 6, 10, 15, 17, 18, 24])

    @unittest.mock.patch("analise_gaps_ciclo.gerador._analisar_gaps")
    def test_leitura_escolhe_fonte_dos_padroes(self, mock_ag):
        mock_ag.return_value = {
            "sucesso": True,
            "top_padroes": [{"padrao": "1 1 1 1 1 1", "gaps": [1, 1, 1, 1, 1, 1]}],
            "top_padroes_sorteio": [{"padrao": "2 2 2 2 2 2", "gaps": [2, 2, 2, 2, 2, 2]}],
            "ranking_comparativo": [{"padrao": "3 3 3 3 3 3", "gaps": [3, 3, 3, 3, 3, 3]}],
            "ultimo": {"gaps": [1, 1, 1, 1, 1, 1], "gaps_sorteio": [2, 2, 2, 2, 2, 2]},
        }
        a = gerar_apostas("diadesorte", sessao1=True, sessao2=False, inicial=2, quantidade=1, leitura="classificado")
        b = gerar_apostas("diadesorte", sessao1=True, sessao2=False, inicial=2, quantidade=1, leitura="sorteio")
        c = gerar_apostas("diadesorte", sessao1=True, sessao2=False, inicial=2, quantidade=1, leitura="ambos")
        self.assertEqual(a["apostas"][0]["ciclos"], [1, 1, 1, 1, 1, 1])
        self.assertEqual(b["apostas"][0]["ciclos"], [2, 2, 2, 2, 2, 2])
        self.assertEqual(c["apostas"][0]["ciclos"], [3, 3, 3, 3, 3, 3])


if __name__ == "__main__":
    unittest.main()
