# -*- coding: utf-8 -*-
"""Testes — gerador de 10 apostas por Padrões II no universo de 16."""
from __future__ import annotations

import os
import sys
import unittest

_SHARED = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from ciclo_cobertura.gerador_padroes_recorrencia import (
    classificar_iniciais,
    completar_universo,
    gerar_apostas_padroes_recorrencia,
    montar_lote_padroes,
    padrao_cabe,
    padrao_inicial_de,
    validar_universo,
)


UNIVERSO_OK = [1, 5, 7, 8, 9, 12, 14, 15, 18, 21, 22, 25, 27, 28, 30, 31]
# 0: 5 · 1: 4 · 2: 5 · 3: 2
PADRAO_A = "0 2 2 2 2 3 3"  # need 1/0/4/2
PADRAO_B = "0 0 1 1 2 2 3"  # need 2/2/2/1
PAD10 = [PADRAO_A] * 5 + [PADRAO_B] * 5

REC_FAKE = {
    "ok": True,
    "dezena_min": 1,
    "dezena_max": 31,
    "grupos": {
        "nucleo_forte": [7, 21, 22, 30],
        "repetido": [25, 27],
        "baixa_presenca": [1, 5, 12, 14, 15, 18],
        "ausentes": [2, 3, 4, 6, 10, 11, 13, 16, 17, 19, 20, 23, 24, 26, 29],
    },
    "pool": {
        "nucleo_x_baixa": [1, 5, 7, 12, 14, 15, 18, 21, 22, 25, 27, 30],
    },
    "tabela": [{"dezena": n, "vezes": 2 if n in (7, 21, 22) else 1} for n in UNIVERSO_OK],
    "ciclo": {"pendentes": [31], "scores_faltantes": [{"dezena": 31, "score": 9}]},
}


class TestClassificacao(unittest.TestCase):
    def test_contagem_iniciais(self):
        clf = classificar_iniciais(UNIVERSO_OK)
        self.assertEqual(clf["total"], 16)
        self.assertEqual(clf["contagem"][0], 5)
        self.assertEqual(clf["contagem"][1], 4)
        self.assertEqual(clf["contagem"][2], 5)
        self.assertEqual(clf["contagem"][3], 2)


class TestValidacao(unittest.TestCase):
    def test_universo_valido(self):
        val = validar_universo(UNIVERSO_OK, PAD10)
        self.assertTrue(val["gerar_liberado"])
        self.assertFalse(val["faltas"])

    def test_inicial_insuficiente(self):
        curto = [d for d in UNIVERSO_OK if d < 10 or d >= 20]  # sem inicial 1
        curto = curto[:16] if len(curto) >= 16 else curto + [2, 3, 4, 6]
        val = validar_universo(curto[:16], [PADRAO_B] * 10)
        self.assertFalse(val["gerar_liberado"])
        inits = {f["inicial"] for f in val["faltas"]}
        self.assertIn(1, inits)


class TestComplementacao(unittest.TestCase):
    def test_sugere_inicial_faltante(self):
        sem_1 = [1, 5, 7, 8, 9, 21, 22, 23, 25, 27, 28, 24, 26, 30, 31, 2]
        # inicial 1 = só se 1 está... 1 é inicial 0. Zero inicial 1.
        sem_1 = [d for d in sem_1 if d // 10 != 1]
        while len(sem_1) < 16:
            for n in range(1, 10):
                if n not in sem_1:
                    sem_1.append(n)
                if len(sem_1) >= 16:
                    break
        out = completar_universo(sem_1[:16], [PADRAO_B] * 10, REC_FAKE)
        clf = classificar_iniciais(out["dezenas"])
        self.assertGreaterEqual(clf["contagem"][1], 2)
        self.assertEqual(len(out["dezenas"]), 16)
        self.assertTrue(any(s.get("sugestao") for s in out["sugestoes"]))


# Print do usuário: 5 / 3 / 6 / 2 — padrões com 4+ na inicial 1 não cabem.
UNIVERSO_PRINT = [1, 2, 3, 4, 5, 10, 17, 18, 20, 21, 22, 25, 27, 28, 30, 31]
CATALOGO_PRINT = [
    "0 0 1 1 1 1 2",
    "1 1 1 2 2 2 2",
    "0 1 1 1 1 1 2",
    "0 1 2 2 2 2 2",
    "0 0 1 2 2 2 3",
    "0 0 0 1 2 2 3",
]


class TestViabilidadePrint(unittest.TestCase):
    def test_nao_cabe_quatro_na_inicial_1(self):
        self.assertFalse(padrao_cabe(UNIVERSO_PRINT, "0 0 1 1 1 1 2"))
        self.assertFalse(padrao_cabe(UNIVERSO_PRINT, "0 1 1 1 1 1 2"))

    def test_cabe_os_marcados_como_ok(self):
        self.assertTrue(padrao_cabe(UNIVERSO_PRINT, "1 1 1 2 2 2 2"))
        self.assertTrue(padrao_cabe(UNIVERSO_PRINT, "0 1 2 2 2 2 2"))

    def test_lote_prioriza_escolhido_e_diferenciados(self):
        lote = montar_lote_padroes(
            UNIVERSO_PRINT, CATALOGO_PRINT, ultimo="0 0 1 2 2 2 3",
        )
        self.assertEqual(len(lote), 10)
        self.assertEqual(lote[0], "0 0 1 2 2 2 3")
        self.assertNotIn("0 0 1 1 1 1 2", lote)
        self.assertNotIn("0 1 1 1 1 1 2", lote)
        self.assertIn("1 1 1 2 2 2 2", lote)
        self.assertIn("0 1 2 2 2 2 2", lote)
        self.assertGreaterEqual(len(set(lote)), 4)


class TestFaltantesNoPadrao(unittest.TestCase):
    def test_27_em_toda_aposta_com_inicial_2(self):
        rec = {
            "ok": True,
            "dezena_min": 1,
            "dezena_max": 31,
            "ciclo": {
                "pendentes": [27],
                "scores_faltantes": [{"dezena": 27, "score": 12}],
            },
            "conjunto_construtor": {"faltantes_ciclo": [27]},
            "grupos": REC_FAKE["grupos"],
            "pool": REC_FAKE["pool"],
            "tabela": [{"dezena": n, "vezes": 1} for n in UNIVERSO_PRINT],
        }
        padroes = ["0 0 1 2 2 2 3"] * 9 + ["0 0 0 0 1 1 3"]
        out = gerar_apostas_padroes_recorrencia(
            "diadesorte", dezenas=UNIVERSO_PRINT, padroes=padroes, seed=3, rec=rec,
        )
        self.assertTrue(out.get("ok"), out.get("erro"))
        com_2 = 0
        for a in out["apostas"]:
            tem_2 = "2" in a["padrao"].split()
            if tem_2:
                com_2 += 1
                self.assertIn(27, a["dezenas"], a)
            else:
                self.assertNotIn(27, a["dezenas"], a)
        self.assertEqual(com_2, 9)


class TestGeracao(unittest.TestCase):
    def test_dez_apostas_validas(self):
        out = gerar_apostas_padroes_recorrencia(
            "diadesorte", dezenas=UNIVERSO_OK, padroes=PAD10, seed=7,
        )
        self.assertTrue(out.get("ok"), out.get("erro"))
        self.assertEqual(out["geradas"], 10)
        pool = set(UNIVERSO_OK)
        seen_nums = []
        for a in out["apostas"]:
            dez = a["dezenas"]
            self.assertEqual(len(dez), 7)
            self.assertEqual(len(set(dez)), 7)
            self.assertTrue(set(dez) <= pool)
            self.assertEqual(padrao_inicial_de(dez), a["padrao"])
            seen_nums.extend(dez)
        # reutilização entre apostas: alguma dezena em mais de uma
        from collections import Counter
        cnt = Counter(seen_nums)
        self.assertTrue(any(v > 1 for v in cnt.values()))

    def test_nao_gera_invalido(self):
        curto = [1, 5, 7, 8, 9, 21, 22, 25, 27, 28, 30, 31, 2, 3, 4, 6]
        out = gerar_apostas_padroes_recorrencia(
            "diadesorte", dezenas=curto, padroes=[PADRAO_B] * 10, seed=1,
        )
        self.assertFalse(out.get("ok"))
        self.assertFalse(out.get("apostas"))

    def test_regenerar_mesmo_universo(self):
        a = gerar_apostas_padroes_recorrencia(
            "diadesorte", dezenas=UNIVERSO_OK, padroes=PAD10, seed=1,
        )
        b = gerar_apostas_padroes_recorrencia(
            "diadesorte", dezenas=UNIVERSO_OK, padroes=PAD10, seed=99,
        )
        self.assertTrue(a.get("ok") and b.get("ok"))
        self.assertEqual(a["universo"], b["universo"])
        self.assertEqual(a["padroes"], b["padroes"])
        combos_a = [tuple(x["dezenas"]) for x in a["apostas"]]
        combos_b = [tuple(x["dezenas"]) for x in b["apostas"]]
        self.assertNotEqual(combos_a, combos_b)


if __name__ == "__main__":
    unittest.main()
