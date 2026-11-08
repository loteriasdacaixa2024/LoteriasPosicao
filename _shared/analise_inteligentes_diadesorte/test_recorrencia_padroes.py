# -*- coding: utf-8 -*-
"""Testes da recorrência dos padrões iniciais — sem estimar resultado."""
from __future__ import annotations

import math
import os
import sys
import unittest

_SHARED = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_APP = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "AnalisePorPosicao--DiaDeSorte-Only"))
for _p in (_APP, _SHARED):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analise_inteligentes_diadesorte.recorrencia_padroes import (  # noqa: E402
    classificar_recorrencia,
    intervalos_entre,
    montar_recorrencia,
    resumir_intervalos,
)


class TestIntervalos(unittest.TestCase):
    def test_exemplo_100_105_107_115_120(self):
        concursos = [120, 100, 115, 105, 107]
        self.assertEqual(intervalos_entre(concursos), [5, 2, 8, 5])
        r = resumir_intervalos(concursos, ultimo_geral=130)
        self.assertEqual(r["intervalos"], [5, 2, 8, 5])
        self.assertEqual(r["intervalo_medio"], 5.0)
        self.assertEqual(r["intervalo_mediano"], 5.0)
        self.assertEqual(r["menor_intervalo"], 2)
        self.assertEqual(r["maior_intervalo"], 8)
        self.assertEqual(r["moda_intervalo"], 5)
        self.assertEqual(r["moda_vezes"], 2)
        self.assertFalse(r["moda_empate"])
        self.assertEqual(r["histograma_intervalos"], [
            {"intervalo": 2, "vezes": 1},
            {"intervalo": 5, "vezes": 2},
            {"intervalo": 8, "vezes": 1},
        ])
        self.assertEqual(r["desde_ultima"], 10)
        self.assertEqual(r["ocorrencias"], 5)
        self.assertEqual(r["primeiro_concurso"], 100)
        self.assertEqual(r["ultimo_concurso"], 120)
        desvio = math.sqrt(((0 ** 2) + ((-3) ** 2) + (3 ** 2) + (0 ** 2)) / 3)
        self.assertEqual(r["regularidade"], round(desvio / 5.0, 3))

    def test_uma_ocorrencia_nao_tem_intervalo(self):
        r = resumir_intervalos([40], ultimo_geral=50)
        self.assertEqual(r["qtd_intervalos"], 0)
        self.assertIsNone(r["intervalo_medio"])
        self.assertIsNone(r["intervalo_mediano"])
        self.assertIsNone(r["menor_intervalo"])
        self.assertIsNone(r["maior_intervalo"])
        self.assertIsNone(r["moda_intervalo"])
        self.assertIsNone(r["regularidade"])
        self.assertEqual(r["desde_ultima"], 10)

    def test_nunca_saiu(self):
        r = resumir_intervalos([], ultimo_geral=50)
        self.assertEqual(r["ocorrencias"], 0)
        self.assertIsNone(r["desde_ultima"])
        self.assertEqual(r["intervalos"], [])

    def test_empate_de_moda_fica_com_o_menor_intervalo(self):
        r = resumir_intervalos([1, 3, 5, 10, 15], ultimo_geral=15)
        self.assertEqual(r["intervalos"], [2, 2, 5, 5])
        self.assertEqual(r["modas"], [2, 5])
        self.assertEqual(r["moda_intervalo"], 2)
        self.assertTrue(r["moda_empate"])
        self.assertEqual(r["desde_ultima"], 0)

    def test_um_intervalo_nao_tem_regularidade(self):
        r = resumir_intervalos([10, 14], ultimo_geral=14)
        self.assertEqual(r["qtd_intervalos"], 1)
        self.assertEqual(r["intervalo_medio"], 4.0)
        self.assertIsNone(r["regularidade"])


class TestClassificacao(unittest.TestCase):
    def test_mais_rapido_nao_e_quem_mais_saiu(self):
        frequente = resumir_intervalos([1, 21, 41, 61, 81], ultimo_geral=81)
        frequente["padrao"] = "frequente"
        rapido = resumir_intervalos([10, 12, 15], ultimo_geral=81)
        rapido["padrao"] = "rapido"
        ranks = classificar_recorrencia([frequente, rapido])
        self.assertEqual(ranks["top_mais_rapidos"][0]["padrao"], "rapido")
        self.assertEqual(ranks["top_maior_intervalo"][0]["padrao"], "frequente")
        self.assertEqual(ranks["intervalos_curtos"][0]["padrao"], "rapido")

    def test_regularidade_ignora_quem_so_tem_um_intervalo(self):
        estavel = resumir_intervalos([1, 5, 9, 13], ultimo_geral=13)
        estavel["padrao"] = "estavel"
        unico = resumir_intervalos([1, 2], ultimo_geral=13)
        unico["padrao"] = "unico"
        ranks = classificar_recorrencia([unico, estavel])
        self.assertEqual([r["padrao"] for r in ranks["top_regulares"]], ["estavel"])
        self.assertEqual(estavel["regularidade"], 0.0)


class _SvcFake:
    modality_key = "diadesorte"

    def _limites(self):
        return {"min_dezena": 1, "max_dezena": 31, "tamanho_jogo": 7, "pad": 2}

    def listar_resultados(self, janela=0, base="geral"):
        pad_a = "0 0 0 1 1 1 1"
        pad_b = "0 0 0 0 0 0 3"
        linhas = [{"concurso": c, "padrao_inicial": pad_a, "dezenas": []} for c in (100, 105, 107, 115, 120)]
        linhas.append({"concurso": 130, "padrao_inicial": pad_b, "dezenas": []})
        return {"sucesso": True, "linhas": linhas}


class TestMontagem(unittest.TestCase):
    def test_historico_curto_encontra_o_exemplo(self):
        out = montar_recorrencia(_SvcFake(), base="teste-unitario")
        self.assertTrue(out["sucesso"])
        self.assertEqual(out["total_concursos"], 6)
        self.assertEqual(out["ultimo_concurso"], 130)
        self.assertEqual(out["total_padroes"], 85)
        por_padrao = {r["padrao"]: r for r in out["padroes"]}
        a = por_padrao["0 0 0 1 1 1 1"]
        self.assertEqual(a["intervalos"], [5, 2, 8, 5])
        self.assertEqual(a["desde_ultima"], 10)
        self.assertEqual(out["top_mais_rapidos"][0]["padrao"], "0 0 0 1 1 1 1")
        self.assertEqual(out["padroes_com_intervalo"], 1)
        self.assertEqual(out["padroes_uma_vez"], 1)
        self.assertEqual(out["padroes_nunca"], 83)


if __name__ == "__main__":
    unittest.main()
