# -*- coding: utf-8 -*-
"""O lote 2A1 nasce do padrão e da sequência, já dentro das restrições."""
from __future__ import annotations

import os
import random
import sys
import unittest

_SHARED = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_APP = os.path.abspath(os.path.join(_SHARED, "..", "AnalisePorPosicao--DiaDeSorte-Only"))
for _p in (_APP, _SHARED):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analise_escolha_visual.enriquecimento.regras_2a1 import viola_restricoes  # noqa: E402
from analise_inteligentes_diadesorte.sequencias_sorteadas import dezenas_na_sequencia  # noqa: E402
from analise_inteligentes_diadesorte.service import (  # noqa: E402
    descricao_bma_do_padrao,
    jogos_possiveis_padrao,
    padrao_inicial,
)
from gerador_2a1 import (  # noqa: E402
    _identidade_valida,
    _resolver_cinco,
    cotas_relevancia,
    fila_intercalada,
    gerar_lote_2a1,
)


class TestGerador2A1(unittest.TestCase):
    def test_cotas_dez_apostas_intercalam_cinco_postos(self):
        self.assertEqual(cotas_relevancia(10, 5), [3, 2, 2, 2, 1])
        self.assertEqual(fila_intercalada([3, 2, 2, 2, 1]), [0, 1, 2, 3, 4, 0, 1, 2, 3, 0])
        self.assertEqual(cotas_relevancia(4, 5), [1, 1, 1, 1, 0])
        self.assertEqual(sum(cotas_relevancia(30, 5)), 30)
        self.assertEqual(cotas_relevancia(4, 1), [4])

    def test_resolver_preserva_ordem_e_ignora_sem_ocorrencia(self):
        cat = [
            {"padrao": "0 0 1 1 2 2 3", "frequencia": 8, "jogos_possiveis": 100, "descricao": "2B + 2M + 3A"},
            {"padrao": "0 0 0 1 1 1 2", "frequencia": 5, "jogos_possiveis": 80, "descricao": "3B + 3M + 1A"},
            {"padrao": "0 0 0 0 1 2 3", "frequencia": 0, "jogos_possiveis": 40, "descricao": "4B + 1M + 2A"},
        ]
        fonte = [
            {"padrao": "0 0 0 0 1 2 3", "frequencia": 0, "descricao": "4B + 1M + 2A"},
            {"padrao": "0 0 0 1 1 1 2", "frequencia": 5, "descricao": "3B + 3M + 1A"},
            {"padrao": "0 0 1 1 2 2 3", "frequencia": 8, "descricao": "2B + 2M + 3A"},
        ]
        out = _resolver_cinco(cat, fonte, set(range(1, 32)), 7, [])
        self.assertEqual([p["padrao"] for p in out], ["0 0 0 1 1 1 2", "0 0 1 1 2 2 3"])
        self.assertEqual([p["posto"] for p in out], [1, 2])

    def test_apostas_respeitam_repetido_sequencia_e_quantidade(self):
        pad = "0 0 1 1 2 2 3"
        faixa = {"media": 90, "tol_dentro": 6, "tol_proxima": 12}
        jogos = jogos_possiveis_padrao(pad, min_dezena=1, max_dezena=31)
        linhas = []
        for i, seq in enumerate((400, 900, 1500, 2200), start=1):
            dez = dezenas_na_sequencia(pad, seq, faixa, min_dezena=1, max_dezena=31)
            self.assertIsNotNone(dez)
            linhas.append({
                "concurso": i,
                "padrao": pad,
                "sequencia_n": seq,
                "jogos_possiveis": jogos,
                "media": 90,
                "soma": sum(dez),
                "dezenas": dez,
                "descricao": descricao_bma_do_padrao(pad),
            })
        ultimo = [2, 5, 14, 19, 22, 28, 31]
        penultimo = [2, 8, 11, 16, 21, 25, 30]
        pendentes = [n for n in range(1, 32) if n != 2]
        out = gerar_lote_2a1(
            catalogo=[{
                "padrao": pad,
                "frequencia": 8,
                "jogos_possiveis": jogos,
                "descricao": descricao_bma_do_padrao(pad),
            }],
            linhas_panorama=linhas,
            ultimo=ultimo,
            penultimo=penultimo,
            pendentes=pendentes,
            historico=[tuple(sorted(row["dezenas"])) for row in linhas],
            quantidade=4,
            repetidos="0",
            rng=random.Random(7),
        )
        self.assertTrue(out.get("sucesso"), out.get("erro"))
        self.assertGreaterEqual(len(out["apostas"]), 1)
        restr = out["restricoes"]
        self.assertEqual(restr["repetidos_proibidos"], [2])
        for ap in out["apostas"]:
            dez = ap["dezenas"]
            self.assertEqual(len(dez), 7)
            self.assertNotIn(2, dez)
            self.assertEqual(padrao_inicial(dez), pad)
            self.assertIsNone(viola_restricoes(dez, restr))
            reps = [n for n in dez if n in set(ultimo)]
            self.assertEqual(reps, [])
            self.assertTrue(set(dez).isdisjoint(set(ultimo)))
            self.assertIn("justificativa", ap)
            self.assertTrue(ap["justificativa"])

    def test_fim_de_ciclo_abre_pool_e_mantem_pendente(self):
        pad = "0 0 1 1 2 2 3"
        faixa = {"media": 90, "tol_dentro": 6, "tol_proxima": 12}
        jogos = jogos_possiveis_padrao(pad, min_dezena=1, max_dezena=31)
        linhas = []
        for i, seq in enumerate((400, 900, 1500, 2200), start=1):
            dez = dezenas_na_sequencia(pad, seq, faixa, min_dezena=1, max_dezena=31)
            linhas.append({
                "concurso": i,
                "padrao": pad,
                "sequencia_n": seq,
                "jogos_possiveis": jogos,
                "media": 90,
                "soma": sum(dez),
                "dezenas": dez,
                "descricao": descricao_bma_do_padrao(pad),
            })
        ultimo = [5, 9, 15, 2, 14, 25, 7]
        out = gerar_lote_2a1(
            catalogo=[{
                "padrao": pad,
                "frequencia": 8,
                "jogos_possiveis": jogos,
                "descricao": descricao_bma_do_padrao(pad),
            }],
            linhas_panorama=linhas,
            ultimo=ultimo,
            penultimo=[4, 5, 6, 16, 19, 27, 28],
            pendentes=[30],
            historico=[tuple(sorted(row["dezenas"])) for row in linhas],
            quantidade=2,
            repetidos="0",
            rng=random.Random(3),
        )
        self.assertTrue(out.get("sucesso"), out.get("erro"))
        self.assertFalse(out.get("pool_ampliado"))
        self.assertTrue(out.get("ciclo_fim"))
        ultimo_set = set(ultimo)
        for ap in out["apostas"]:
            self.assertTrue(set(ap["dezenas"]).isdisjoint(ultimo_set))
            self.assertEqual(ap["repetidos"], [])

    def test_concurso_1348_so_usa_as_que_nao_sairam(self):
        pad = "0 0 1 1 2 2 3"
        faixa = {"media": 90, "tol_dentro": 6, "tol_proxima": 12}
        jogos = jogos_possiveis_padrao(pad, min_dezena=1, max_dezena=31)
        linhas = []
        for i, seq in enumerate((400, 900, 1500, 2200), start=1):
            dez = dezenas_na_sequencia(pad, seq, faixa, min_dezena=1, max_dezena=31)
            linhas.append({
                "concurso": i,
                "padrao": pad,
                "sequencia_n": seq,
                "jogos_possiveis": jogos,
                "media": 90,
                "soma": sum(dez),
                "dezenas": dez,
                "descricao": descricao_bma_do_padrao(pad),
            })
        ultimo = [25, 2, 23, 18, 11, 1, 7]
        fora = {
            4, 6, 8, 10, 12, 14, 16, 20, 22, 24, 26, 28, 30,
            3, 5, 9, 13, 15, 17, 19, 21, 27, 29, 31,
        }
        out = gerar_lote_2a1(
            catalogo=[{
                "padrao": pad,
                "frequencia": 8,
                "jogos_possiveis": jogos,
                "descricao": descricao_bma_do_padrao(pad),
            }],
            linhas_panorama=linhas,
            ultimo=ultimo,
            penultimo=[5, 9, 14, 15, 4, 8, 20],
            pendentes=[14, 31, 3],
            historico=[tuple(sorted(row["dezenas"])) for row in linhas],
            quantidade=2,
            repetidos="0",
            rng=random.Random(11),
        )
        self.assertTrue(out.get("sucesso"), out.get("erro"))
        self.assertGreaterEqual(len(out.get("padroes_cinco") or []), 1)
        for ap in out["apostas"]:
            self.assertTrue(set(ap["dezenas"]).issubset(fora))
            pad_ok, seq_ok = _identidade_valida(
                ap["dezenas"], {"media": ap.get("media_soma")}, dmin=1, dmax=31,
            )
            self.assertEqual(ap["padrao"], pad_ok)
            self.assertEqual(ap["sequencia_n"], seq_ok)

    def test_sequencia_valida_e_a_da_aposta_pronta(self):
        pad = "0 0 1 1 2 2 2"
        faixa = {"media": 100}
        base = dezenas_na_sequencia(pad, 1000, faixa, min_dezena=1, max_dezena=31)
        self.assertEqual(_identidade_valida(base, faixa, dmin=1, dmax=31), (pad, 1000))
        dez = list(base)
        casa = dez[0] // 10
        troca = next(
            n for n in range(max(1, casa * 10), min(31, casa * 10 + 9) + 1)
            if n not in dez
        )
        dez[0] = troca
        dez.sort()
        pad2, seq2 = _identidade_valida(dez, faixa, dmin=1, dmax=31)
        self.assertEqual(pad2, padrao_inicial(dez))
        self.assertNotEqual(seq2, 1000)
        self.assertEqual(seq2, _identidade_valida(dez, faixa, dmin=1, dmax=31)[1])

    def _lote_repetidos(self, modo):
        pad = "0 0 1 1 2 2 3"
        faixa = {"media": 90, "tol_dentro": 6, "tol_proxima": 12}
        jogos = jogos_possiveis_padrao(pad, min_dezena=1, max_dezena=31)
        linhas = []
        for i, seq in enumerate((400, 900, 1500, 2200), start=1):
            dez = dezenas_na_sequencia(pad, seq, faixa, min_dezena=1, max_dezena=31)
            linhas.append({
                "concurso": i,
                "padrao": pad,
                "sequencia_n": seq,
                "jogos_possiveis": jogos,
                "media": 90,
                "soma": sum(dez),
                "dezenas": dez,
                "descricao": descricao_bma_do_padrao(pad),
            })
        ultimo = [25, 2, 23, 18, 11, 1, 7]
        return gerar_lote_2a1(
            catalogo=[{
                "padrao": pad,
                "frequencia": 8,
                "jogos_possiveis": jogos,
                "descricao": descricao_bma_do_padrao(pad),
            }],
            linhas_panorama=linhas,
            ultimo=ultimo,
            penultimo=[5, 9, 14, 15, 4, 8, 20],
            pendentes=[14, 31, 3],
            historico=[tuple(sorted(row["dezenas"])) for row in linhas],
            quantidade=3,
            repetidos=modo,
            rng=random.Random(11),
        ), set(ultimo)

    def test_select_um_e_dois_repetidos(self):
        for modo, qtd in (("1", 1), ("2", 2)):
            out, ultimo = self._lote_repetidos(modo)
            self.assertTrue(out.get("sucesso"), out.get("erro"))
            self.assertEqual(out.get("repetidos_modo"), modo)
            for ap in out["apostas"]:
                reps = [n for n in ap["dezenas"] if n in ultimo]
                self.assertEqual(len(reps), qtd)
                self.assertEqual(ap["repetidos"], sorted(reps))
                self.assertEqual(padrao_inicial(ap["dezenas"]), ap["padrao"])


if __name__ == "__main__":
    unittest.main()
