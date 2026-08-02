# -*- coding: utf-8 -*-
"""Testes — Mês da Sorte (atrasado / frequente / aleatório)."""
from __future__ import annotations

import os
import sys
import unittest
from collections import Counter
from random import Random
from types import SimpleNamespace

_SHARED = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from diadesorte.mes_sorte_select import (  # noqa: E402
    distribuir_meses_aleatorios,
    eh_criterio_aleatorio,
    estatisticas_meses_from_rows,
    max_freq_esperada,
    montar_opcoes_mes_sorte,
    resolver_mes_sorte,
    resolver_meses_para_lote,
)


def _rows_fake():
    """Histórico sintético: Novembro frequente; só Janeiro nunca saiu → mais atrasado."""
    # Cobre 2–12; omite Janeiro. Mais recente primeiro.
    return [
        SimpleNamespace(concurso=100, mes_num=11),
        SimpleNamespace(concurso=99, mes_num=11),
        SimpleNamespace(concurso=98, mes_num=11),
        SimpleNamespace(concurso=97, mes_num=12),
        SimpleNamespace(concurso=96, mes_num=3),
        SimpleNamespace(concurso=95, mes_num=2),
        SimpleNamespace(concurso=94, mes_num=4),
        SimpleNamespace(concurso=93, mes_num=5),
        SimpleNamespace(concurso=92, mes_num=6),
        SimpleNamespace(concurso=91, mes_num=7),
        SimpleNamespace(concurso=90, mes_num=8),
        SimpleNamespace(concurso=89, mes_num=9),
        SimpleNamespace(concurso=88, mes_num=10),
    ]


class TestMesSorteSelect(unittest.TestCase):
    def setUp(self):
        self.stats = estatisticas_meses_from_rows(_rows_fake())
        self.payload = montar_opcoes_mes_sorte(self.stats)

    def test_atrasado_e_frequente_independentes(self):
        atrasado = resolver_mes_sorte("atrasado", opcoes_payload=self.payload)
        frequente = resolver_mes_sorte("frequente", opcoes_payload=self.payload)
        self.assertEqual(atrasado, 1)  # Janeiro — único nunca sorteado
        self.assertEqual(frequente, 11)  # Novembro — maior freq
        self.assertNotEqual(atrasado, frequente)

    def test_fixo_respeitado(self):
        self.assertEqual(resolver_mes_sorte(7, opcoes_payload=self.payload), 7)
        self.assertEqual(resolver_mes_sorte("Dezembro", opcoes_payload=self.payload), 12)

    def test_lote_atrasado_mesmo_mes(self):
        meses = resolver_meses_para_lote("atrasado", 10, opcoes_payload=self.payload)
        self.assertEqual(len(meses), 10)
        self.assertEqual(set(meses), {1})

    def test_lote_frequente_mesmo_mes(self):
        meses = resolver_meses_para_lote("frequente", 10, opcoes_payload=self.payload)
        self.assertEqual(len(meses), 10)
        self.assertEqual(set(meses), {11})

    def test_aleatorio_distribuicao_equilibrada_10(self):
        rng = Random(42)
        meses = distribuir_meses_aleatorios(10, rng=rng)
        self.assertEqual(len(meses), 10)
        self.assertTrue(all(1 <= m <= 12 for m in meses))
        # 10 apostas → no máx. 1 ocorrência por mês (sem repetição)
        counts = Counter(meses)
        self.assertEqual(max(counts.values()), 1)
        self.assertEqual(len(counts), 10)

    def test_aleatorio_nao_concentra_dezembro(self):
        """Múltiplas simulações: Dezembro não deve dominar como no bug antigo."""
        total_dez = 0
        n_sims = 200
        n_apostas = 10
        for seed in range(n_sims):
            meses = distribuir_meses_aleatorios(n_apostas, rng=Random(seed))
            total_dez += meses.count(12)
            # Em cada lote de 10, Dezembro aparece no máximo 1 vez
            self.assertLessEqual(meses.count(12), 1)
        # Esperado ≈ 200 * (10/12) ≈ 166.7 — longe de 2000 (concentração total)
        self.assertLess(total_dez, n_sims * 3)  # margem folgada vs concentração
        self.assertGreater(total_dez, n_sims // 3)

    def test_aleatorio_teto_ceil_n_sobre_12(self):
        for n in (1, 10, 12, 13, 24, 25, 100):
            meses = distribuir_meses_aleatorios(n, rng=Random(n * 17))
            teto = max_freq_esperada(n)
            counts = Counter(meses)
            self.assertLessEqual(max(counts.values()), teto, f"n={n}")
            piso = n // 12
            self.assertTrue(all(c >= piso for c in counts.values()) or n < 12)

    def test_aleatorio_diferente_de_frequente_e_atrasado(self):
        atr = resolver_meses_para_lote("atrasado", 12, opcoes_payload=self.payload)
        freq = resolver_meses_para_lote("frequente", 12, opcoes_payload=self.payload)
        alea = resolver_meses_para_lote("aleatorio", 12, opcoes_payload=self.payload, rng=Random(7))
        self.assertEqual(len(set(atr)), 1)
        self.assertEqual(len(set(freq)), 1)
        self.assertEqual(len(set(alea)), 12)  # bloco completo embaralhado

    def test_eh_criterio_aleatorio(self):
        self.assertTrue(eh_criterio_aleatorio("aleatorio"))
        self.assertTrue(eh_criterio_aleatorio("Aleatório"))
        self.assertFalse(eh_criterio_aleatorio("atrasado"))
        self.assertFalse(eh_criterio_aleatorio(12))

    def test_opcoes_ordem_e_exclusao(self):
        vals = [o["value"] for o in self.payload["opcoes"]]
        self.assertEqual(vals[0], "atrasado")
        self.assertEqual(vals[1], "frequente")
        self.assertEqual(vals[-1], "aleatorio")
        # Janeiro e Novembro não aparecem como fixos (já estão em especiais)
        fixos = {o["mes_num"] for o in self.payload["opcoes"] if o["criterio"] == "fixo"}
        self.assertNotIn(1, fixos)
        self.assertNotIn(11, fixos)


if __name__ == "__main__":
    unittest.main()
