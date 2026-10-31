# -*- coding: utf-8 -*-
"""Exportação da seção 2 — planilha, pasta e falhas explícitas."""
from __future__ import annotations

import os
import tempfile
import threading
import unittest
from datetime import date
from io import BytesIO
from unittest import mock

from openpyxl import load_workbook

from analise_escolha_visual import export_estatisticas as exp


def _linha():
    return {
        "concurso": 10,
        "data": "26/10/2026",
        "numeros": [1, 2, 3, 4, 5, 6, 7],
        "pares": {"dezenas": [2, 4, 6]},
        "impares": {"dezenas": [1, 3, 5, 7]},
        "repetidos": {"dezenas": []},
        "sequencias": {
            "dezenas": [1, 2, 3, 4, 5, 6, 7],
            "detalhe": {"grupos": [[1, 2, 3, 4, 5, 6, 7]], "qtd_grupos": 1},
        },
        "finais": {"dezenas": [], "detalhe": {"grupos": [], "qtd_grupos": 0}},
    }


class ExportEstatisticasTest(unittest.TestCase):
    def test_caminho_relativo_usa_pasta_oficial(self):
        caminho = exp.caminho_exibicao("diadesorte")
        self.assertEqual(
            caminho,
            "conferencia_apostas/dia-de-sorte/Estatisticas_Basicas.xlsx",
        )
        self.assertNotIn(":\\", caminho)
        self.assertFalse(caminho[:2].isalpha() and caminho[1:2] == ":")

    def test_slug_desconhecido_nao_escapa_da_pasta(self):
        with self.assertRaises(ValueError):
            exp.slug_pasta("../dia-de-sorte")
        with self.assertRaises(ValueError):
            exp.slug_pasta("inexistente")

    def test_planilha_preserva_colunas_da_secao(self):
        blob = exp.bytes_modalidade("Dia de Sorte", [_linha()], 2)
        wb = load_workbook(BytesIO(blob))
        ws = wb.active
        self.assertEqual(ws.title, "Dia de Sorte")
        self.assertEqual(
            [ws.cell(1, c).value for c in range(1, 10)],
            ["Conc.", "Data", "Sorteio", "Pares", "Ímpares", "Repetidos", "Sequências", "Finais Iguais", "Diagonais"],
        )
        self.assertEqual(ws["A2"].value, 10)
        bruto = ws["B2"].value
        if hasattr(bruto, "date"):
            bruto = bruto.date()
        self.assertEqual(bruto, date(2026, 10, 26))
        self.assertEqual(ws["B2"].number_format, "DD/MM/YYYY")
        self.assertEqual(ws["C2"].value, "01 02 03 04 05 06 07")
        self.assertEqual(ws["D2"].value, "02 04 06")
        self.assertEqual(ws["F2"].value, "—")
        self.assertEqual(ws["G2"].value, "01-02-03-04-05-06-07")
        self.assertEqual(ws["H2"].value, "—")
        self.assertEqual(ws["I2"].value, "—")
        self.assertEqual(ws.freeze_panes, "A2")
        self.assertIsNotNone(ws.auto_filter.ref)

    def test_diagonais_do_concurso_1332(self):
        from analise_escolha_visual.enriquecimento.motor import linhas_basicas

        linhas = linhas_basicas([{
            "concurso": 1332,
            "data": "26/10/2026",
            "numeros": [7, 9, 18, 26, 27, 28, 29],
        }], dmin=1, dmax=31, cols=10)
        grupos = linhas[0]["diagonais"]["detalhe"]["grupos"]
        self.assertEqual(
            [(g["dir_sym"], g["nums"]) for g in grupos],
            [("↘", [7, 18, 29]), ("↗", [9, 18, 27])],
        )
        texto = exp.linha_valores(linhas[0], 2)[-1]
        self.assertEqual(texto, "↘ | 07-18-29 · ↗ | 09-18-27")

    def test_nome_de_planilha_remove_caracteres_invalidos(self):
        usados = set()
        self.assertEqual(exp.nome_planilha("A/B:C*?[x]", usados), "A B C x")
        self.assertEqual(exp.nome_planilha("Quina", usados), "Quina")
        self.assertEqual(exp.nome_planilha("Quina", usados), "Quina 2")

    def test_grava_sem_deixar_temporario_e_recusa_fora_da_raiz(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(exp, "raiz_apostas", return_value=tmp):
                destino = os.path.join(tmp, "dia-de-sorte", "Estatisticas_Basicas.xlsx")
                exp.gravar_atomico(destino, b"PK-teste")
                with open(destino, "rb") as handle:
                    self.assertEqual(handle.read(), b"PK-teste")
                nomes = []
                for _raiz, _dirs, arquivos in os.walk(tmp):
                    nomes.extend(arquivos)
                self.assertEqual(nomes, ["Estatisticas_Basicas.xlsx"])
                with self.assertRaises(ValueError):
                    exp.gravar_atomico(os.path.join(tmp, "..", "fora.xlsx"), b"x")

    def test_um_arquivo_com_nove_abas(self):
        nomes = (
            "Lotofácil", "Dia de Sorte", "Lotomania", "Quina", "Mega-Sena",
            "+Milionária", "Dupla Sena", "Timemania", "Super Sete",
        )
        folhas = [{"nome": nome, "linhas": [_linha()], "pad": 2} for nome in nomes]
        blob = exp.bytes_consolidado(folhas, [])
        wb = load_workbook(BytesIO(blob))
        self.assertEqual(wb.sheetnames, list(nomes))
        self.assertEqual(len(wb.worksheets), 9)
        self.assertNotIn("Pendências", wb.sheetnames)

    def test_consolidado_explica_modalidade_ausente_e_grava_na_raiz(self):
        def buscar(key, porta, nome):
            if key == "quina":
                return {"key": key, "nome": "Quina", "linhas": [_linha()], "pad": 2}, None
            return None, "Dados indisponíveis no momento."

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(exp, "raiz_apostas", return_value=tmp):
                res = exp.gerar_consolidado(buscar)
                self.assertTrue(res["ok"])
                self.assertIn("Quina", res["incluidas"])
                self.assertIn("Lotofácil", res["mensagem"])
                self.assertNotIn("Traceback", res["mensagem"])
                self.assertNotIn("D:\\", res["mensagem"])
                caminho = os.path.join(tmp, "Estatisticas_Todas_Modalidades.xlsx")
                self.assertTrue(os.path.isfile(caminho))
                wb = load_workbook(caminho)
                self.assertEqual(wb.sheetnames[0], "Pendências")
                self.assertIn("Quina", wb.sheetnames)
                self.assertNotIn("Lotofácil", wb.sheetnames)
                self.assertEqual(wb["Pendências"]["B2"].value, "Dados indisponíveis no momento.")
                extras = [
                    nome for nome in os.listdir(tmp)
                    if nome != "Estatisticas_Todas_Modalidades.xlsx"
                ]
                self.assertEqual(extras, [])

    def test_gravacao_preserva_apostas_da_modalidade(self):
        with tempfile.TemporaryDirectory() as tmp:
            pasta = os.path.join(tmp, "dia-de-sorte", "1332")
            os.makedirs(pasta)
            aposta = os.path.join(pasta, "apostas.json")
            with open(aposta, "w", encoding="utf-8") as handle:
                handle.write('{"ok": true}')
            with mock.patch.object(exp, "raiz_apostas", return_value=tmp):
                destino = os.path.join(tmp, "dia-de-sorte", "Estatisticas_Basicas.xlsx")
                exp.gravar_atomico(destino, b"PK-novo")
                exp.gravar_atomico(destino, b"PK-atual")
            with open(aposta, encoding="utf-8") as handle:
                self.assertEqual(handle.read(), '{"ok": true}')
            with open(destino, "rb") as handle:
                self.assertEqual(handle.read(), b"PK-atual")
            nomes = os.listdir(os.path.join(tmp, "dia-de-sorte"))
            self.assertEqual(sorted(nomes), ["1332", "Estatisticas_Basicas.xlsx"])

    def test_segunda_consolidacao_avisa_sem_misturar(self):
        entrou = threading.Event()
        segue = threading.Event()

        def buscar(key, porta, nome):
            if key == "quina":
                entrou.set()
                self.assertTrue(segue.wait(3))
                return {"key": key, "nome": "Quina", "linhas": [_linha()], "pad": 2}, None
            return None, "Dados indisponíveis no momento."

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(exp, "raiz_apostas", return_value=tmp):
                primeira = {}

                def rodar():
                    primeira["res"] = exp.gerar_consolidado(buscar)

                worker = threading.Thread(target=rodar)
                worker.start()
                self.assertTrue(entrou.wait(3))
                segunda = exp.gerar_consolidado(buscar)
                segue.set()
                worker.join(5)
        self.assertFalse(worker.is_alive())
        self.assertTrue(primeira["res"]["ok"])
        self.assertFalse(segunda["ok"])
        self.assertIsNone(segunda["conteudo"])
        self.assertIn("andamento", segunda["mensagem"])

    def test_consolidado_totalmente_indisponivel_nao_grava(self):
        def buscar(key, porta, nome):
            return None, "Dados indisponíveis no momento."

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(exp, "raiz_apostas", return_value=tmp):
                res = exp.gerar_consolidado(buscar)
                self.assertFalse(res["ok"])
                self.assertIsNone(res["conteudo"])
                self.assertFalse(os.path.exists(os.path.join(tmp, "Estatisticas_Todas_Modalidades.xlsx")))
                self.assertEqual(os.listdir(tmp), [])


if __name__ == "__main__":
    unittest.main()
