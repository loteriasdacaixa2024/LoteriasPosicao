# -*- coding: utf-8 -*-
"""Agregação da análise de sequências — faixas, repetição e top padrões."""
from __future__ import annotations

import os
import sys
import unittest

_SHARED = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_APP = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "AnalisePorPosicao--DiaDeSorte-Only"))
for _p in (_APP, _SHARED):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analise_inteligentes_diadesorte.analise_sequencias import (  # noqa: E402
    agregar_sequencias,
    avaliar_predominancia,
    classificar_faixa_sequencia,
)
from geradores_elite.otimizador.restricoes import _faixa_limites  # noqa: E402


def _linha(padrao, sequencia, jogos, descricao="2B + 2M + 3A", concurso=1):
    return {
        "concurso": concurso,
        "padrao": padrao,
        "descricao": descricao,
        "sequencia_n": sequencia,
        "jogos_possiveis": jogos,
    }


class TestFaixaSequencia(unittest.TestCase):
    def test_ate_31_segue_dezenas(self):
        self.assertEqual(classificar_faixa_sequencia(10, 31), "baixa")
        self.assertEqual(classificar_faixa_sequencia(11, 31), "media")
        self.assertEqual(classificar_faixa_sequencia(20, 31), "media")
        self.assertEqual(classificar_faixa_sequencia(21, 31), "alta")
        self.assertEqual(classificar_faixa_sequencia(31, 31), "alta")

    def test_acima_de_31_usa_tercos_da_funcao_existente(self):
        lim = _faixa_limites(90)
        self.assertEqual(classificar_faixa_sequencia(lim["baixas"][1], 90), "baixa")
        self.assertEqual(classificar_faixa_sequencia(lim["baixas"][1] + 1, 90), "media")
        self.assertEqual(classificar_faixa_sequencia(lim["medias"][1], 90), "media")
        self.assertEqual(classificar_faixa_sequencia(lim["medias"][1] + 1, 90), "alta")
        self.assertEqual((lim["baixas"], lim["medias"], lim["altas"]), ((1, 30), (31, 60), (61, 90)))


class TestPredominancia(unittest.TestCase):
    def test_lider_com_40_e_10_pontos(self):
        out = avaliar_predominancia({"baixa": 50, "media": 30, "alta": 20})
        self.assertTrue(out["significativa"])
        self.assertEqual(out["faixa"], "baixa")
        self.assertEqual(out["rotulo"], "BAIXA")

    def test_empate_ou_vantagem_curta_nao_predomina(self):
        curto = avaliar_predominancia({"baixa": 40, "media": 35, "alta": 25})
        self.assertFalse(curto["significativa"])
        self.assertEqual(curto["rotulo"], "Não existe predominância significativa.")
        empate = avaliar_predominancia({"baixa": 40, "media": 40, "alta": 20})
        self.assertFalse(empate["significativa"])

    def test_distribuicao_equilibrada(self):
        out = avaliar_predominancia({"baixa": 34, "media": 33, "alta": 33})
        self.assertFalse(out["significativa"])
        self.assertTrue(out["equilibrada"])


class TestAgregacao(unittest.TestCase):
    def test_vazio(self):
        out = agregar_sequencias([])
        self.assertTrue(out["sucesso"])
        self.assertEqual(out["total_ocorrencias"], 0)
        self.assertEqual(out["ranking"], [])
        self.assertEqual(out["top_padroes"], [])
        self.assertIn("Ainda não há sequências", out["insights"][0])

    def test_ignora_linha_sem_sequencia(self):
        out = agregar_sequencias([
            _linha("0 0 1 1 2 2 2", None, 90),
            _linha("0 0 1 1 2 2 2", 10, 90),
        ])
        self.assertEqual(out["total_ocorrencias"], 1)
        self.assertEqual(out["linhas_ignoradas"], 1)

    def test_ranking_repeticao_e_faixa_modal(self):
        # seq 25: 3x baixa no universo 90 (1–30) e 2x alta no universo 31 (21–31) → moda baixa
        # seq 25 empate seria outro caso; aqui 3 contra 2.
        linhas = []
        for i in range(3):
            linhas.append(_linha("0 0 1 1 2 2 2", 25, 90, concurso=i + 1))
        for i in range(2):
            linhas.append(_linha("0 1 1 1 2 2 3", 25, 31, concurso=10 + i))
        # seq 40 só no padrão grande: média (31–60), duas vezes → concentrada
        linhas.append(_linha("0 0 1 1 2 2 2", 40, 90, concurso=20))
        linhas.append(_linha("0 0 1 1 2 2 2", 40, 90, concurso=21))
        # seq 80 alta, uma vez
        linhas.append(_linha("0 0 1 1 2 2 2", 80, 90, concurso=22))
        out = agregar_sequencias(linhas)
        ind = out["indicadores"]
        self.assertEqual(ind["sequencias_diferentes"], 3)
        self.assertEqual(ind["sequencias_unicas"], 1)
        self.assertEqual(ind["sequencias_repetidas"], 2)
        por_seq = {r["sequencia"]: r for r in out["ranking"]}
        self.assertEqual(por_seq[25]["ocorrencias"], 5)
        self.assertEqual(por_seq[25]["padroes_diferentes"], 2)
        self.assertEqual(por_seq[25]["faixa"], "baixa")
        self.assertEqual(por_seq[40]["faixa"], "media")
        self.assertEqual(por_seq[40]["padroes_diferentes"], 1)
        self.assertEqual(por_seq[80]["faixa"], "alta")
        self.assertEqual(ind["em_multiplos_padroes"], 1)
        self.assertEqual(ind["concentradas_um_padrao"], 1)
        self.assertEqual(ind["maior_qtd_padroes"], 2)
        self.assertIn(25, ind["maior_diversidade"])
        texto = " ".join(out["insights"])
        self.assertIn("sequência 25 é a mais frequente", texto)
        self.assertIn("aparecem em padrões diferentes", texto)

    def test_empate_de_faixa_nao_escolhe_lado(self):
        linhas = [
            _linha("0 0 1 1 2 2 2", 25, 90),  # baixa
            _linha("0 1 1 1 2 2 3", 25, 31),  # alta
        ]
        out = agregar_sequencias(linhas)
        row = out["ranking"][0]
        self.assertEqual(row["sequencia"], 25)
        self.assertTrue(row["faixa_empate"])
        self.assertEqual(row["faixa"], "")
        self.assertEqual(row["faixa_rotulo"], "Sem predominância")

    def test_top5_ordem_da_aba_padroes_ii(self):
        linhas = []
        n = 1
        # C mais frequente; A e B empatam em 4, B tem mais jogos
        planos = [
            ("1 1 1 1 1 1 1", 4, 100),
            ("2 2 2 2 2 2 2", 4, 200),
            ("0 0 0 0 0 0 3", 5, 10),
            ("0 0 1 1 2 2 3", 3, 50),
            ("0 1 1 2 2 2 3", 2, 40),
            ("0 0 0 1 1 2 2", 1, 80),
        ]
        for pad, freq, jogos in planos:
            for k in range(freq):
                linhas.append(_linha(pad, k + 1, jogos, concurso=n))
                n += 1
        out = agregar_sequencias(linhas)
        ordem = [p["padrao"] for p in out["top_padroes"]]
        self.assertEqual(ordem, [
            "0 0 0 0 0 0 3",
            "2 2 2 2 2 2 2",
            "1 1 1 1 1 1 1",
            "0 0 1 1 2 2 3",
            "0 1 1 2 2 2 3",
        ])
        self.assertEqual(len(out["top_padroes"]), 5)
        self.assertNotIn("0 0 0 1 1 2 2", ordem)

    def test_destaque_e_recorrencia_extrema(self):
        linhas = []
        n = 1
        # Seq 7 dez vezes e seq 8 quatro vezes: a primeira tem mais que o dobro da segunda.
        # Dez sequências com 2 ocorrências puxam a média para baixo e deixam o 7 acima do limiar.
        for _ in range(10):
            linhas.append(_linha("0 0 1 1 2 2 2", 7, 90, concurso=n))
            n += 1
        for _ in range(4):
            linhas.append(_linha("0 0 1 1 2 2 2", 8, 90, concurso=n))
            n += 1
        for s in range(10):
            for _ in range(2):
                linhas.append(_linha("0 0 1 1 2 2 2", 100 + s, 90, concurso=n))
                n += 1
        out = agregar_sequencias(linhas)
        pad = out["top_padroes"][0]
        self.assertEqual(pad["padrao"], "0 0 1 1 2 2 2")
        self.assertTrue(pad["destaque"]["forte"])
        self.assertEqual(pad["destaque"]["sequencia"], 7)
        self.assertEqual(pad["top3"][0]["sequencia"], 7)
        self.assertEqual(pad["top3"][0]["faixa"], "baixa")
        texto_p = " ".join(pad["conclusoes"])
        self.assertIn("se destaca neste padrão", texto_p)
        extremas = {e["sequencia"] for e in out["indicadores"]["extremamente_recorrentes"]}
        self.assertIn(7, extremas)
        self.assertTrue(any("extremamente recorrente" in s for s in out["insights"]))

    def test_sem_destaque_quando_empate_no_topo(self):
        linhas = []
        for seq in (3, 4):
            for k in range(4):
                linhas.append(_linha("0 0 1 1 2 2 2", seq, 90, concurso=seq * 10 + k))
        out = agregar_sequencias(linhas)
        self.assertFalse(out["top_padroes"][0]["destaque"]["forte"])

    def test_aviso_pede_sequencias_diferentes_quando_nao_repete(self):
        seqs = [10, 20, 15, 40, 50, 45, 70, 80]
        linhas = [
            _linha("0 0 1 1 2 2 2", seq, 90, concurso=i + 1)
            for i, seq in enumerate(seqs)
        ]
        out = agregar_sequencias(linhas)
        frases = " ".join(out["aviso_apostas"]["frases"])
        self.assertEqual(out["aviso_apostas"]["titulo"], "Para criar apostas")
        self.assertIn("sequência diferente", frases)
        self.assertIn("Nenhuma sequência voltou dentro do mesmo padrão", frases)
        self.assertIn("cada sequência sorteada saiu uma vez", frases)
        self.assertIn("Não fixe a faixa", frases)
        self.assertIn("sem garantia de resultado futuro", frases)

    def test_apoio_cita_o_padrao_mais_frequente(self):
        linhas = [_linha("0 0 1 1 2 2 2", 80, 90, concurso=i) for i in range(6)]
        linhas += [_linha("1 1 1 1 2 2 2", 5, 90, concurso=20 + i) for i in range(2)]
        out = agregar_sequencias(linhas)
        texto = out["apoio_escolha"]["texto"]
        self.assertIn("sem garantia de resultado futuro", texto)
        self.assertIn("0 0 1 1 2 2 2", texto)
        self.assertIn("sequência 80", texto)
        self.assertIn("Alta", texto)


if __name__ == "__main__":
    unittest.main()
